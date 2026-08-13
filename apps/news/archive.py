"""Public-news archive parsing and querying boundary."""

from dataclasses import dataclass

from django import forms
from django.db.models import Q
from taggit.models import Tag
from wagtail.models import Site
from wagtail.search.query import Fuzzy

from .models import NewsSection
from .selectors import PUBLIC_NEWS_ORDERING, public_news_pages

ASCENDING_ORDERING = ("publication_date", "first_published_at")
DESCENDING_ORDERING = PUBLIC_NEWS_ORDERING


class NewsArchiveFilterForm(forms.Form):
    """Normalize the stable, public query-string contract exactly once."""

    buscar = forms.CharField(required=False)
    seccion = forms.CharField(required=False)
    subseccion = forms.CharField(required=False)
    etiqueta = forms.CharField(required=False)
    orden = forms.CharField(required=False)
    pagina = forms.CharField(required=False)

    def clean_orden(self) -> str:
        value = self.cleaned_data["orden"].strip().lower()
        return value if value in {"asc", "desc"} else ""


@dataclass(frozen=True)
class NewsArchiveCriteria:
    search: str = ""
    section_slug: str = ""
    subsection_slug: str = ""
    tag_slug: str = ""
    order: str = ""
    page_number: int = 1

    @classmethod
    def from_querydict(cls, querydict) -> "NewsArchiveCriteria":
        form = NewsArchiveFilterForm(querydict)
        form.is_valid()
        values = form.cleaned_data
        try:
            page_number = int(values["pagina"].strip())
        except (TypeError, ValueError):
            page_number = 1

        return cls(
            search=values["buscar"].strip(),
            section_slug=values["seccion"].strip(),
            subsection_slug=values["subseccion"].strip(),
            tag_slug=values["etiqueta"].strip(),
            order=values["orden"],
            page_number=max(page_number, 1),
        )

    @property
    def chronological_ordering(self) -> tuple[str, str]:
        return ASCENDING_ORDERING if self.order == "asc" else DESCENDING_ORDERING

    @property
    def has_effective_search(self) -> bool:
        return bool(self.search)

    def query_parameters(self, *, page_number: int | None = None) -> dict[str, str]:
        values = {
            "buscar": self.search,
            "seccion": self.section_slug,
            "subseccion": self.subsection_slug,
            "etiqueta": self.tag_slug,
            "orden": self.order,
        }
        if page_number and page_number > 1:
            values["pagina"] = str(page_number)
        return {key: value for key, value in values.items() if value}


@dataclass(frozen=True)
class NewsArchiveQuery:
    results: object
    criteria: NewsArchiveCriteria
    selected_section: NewsSection | None
    selected_subsection: NewsSection | None
    selected_tag: Tag | None
    invalid_criterion: str = ""


class NewsArchiveQueryService:
    """Apply explicit archive criteria to the existing public selector."""

    def __init__(self, criteria: NewsArchiveCriteria, request):
        self.criteria = criteria
        self.request = request
        self.sections = list(NewsSection.objects.select_related("parent"))
        self.sections_by_slug = {section.slug: section for section in self.sections}

    def execute(self) -> NewsArchiveQuery:
        queryset = public_news_pages()
        site = Site.find_for_request(self.request)
        if site is not None:
            queryset = queryset.descendant_of(site.root_page)

        selected_section, selected_subsection, invalid = self._resolve_sections()
        selected_tag = self._selected_tag()
        if invalid:
            return NewsArchiveQuery(
                queryset.none(),
                self.criteria,
                selected_section,
                selected_subsection,
                selected_tag,
                invalid,
            )
        if self.criteria.tag_slug and selected_tag is None:
            return NewsArchiveQuery(
                queryset.none(),
                self.criteria,
                selected_section,
                selected_subsection,
                None,
                "tag",
            )

        results = self._apply_search(
            queryset,
            selected_section,
            selected_subsection,
            selected_tag,
        )
        return NewsArchiveQuery(
            results,
            self.criteria,
            selected_section,
            selected_subsection,
            selected_tag,
        )

    def _resolve_sections(self):
        section = self.sections_by_slug.get(self.criteria.section_slug)
        subsection = self.sections_by_slug.get(self.criteria.subsection_slug)
        if self.criteria.section_slug and (
            section is None or section.parent_id is not None
        ):
            return None, subsection, "section"
        if self.criteria.subsection_slug and (
            subsection is None or subsection.parent_id is None
        ):
            return section, None, "subsection"
        if section and subsection and subsection.parent_id != section.pk:
            return section, subsection, "section_subsection"
        return section, subsection, ""

    def _selected_tag(self) -> Tag | None:
        if not self.criteria.tag_slug:
            return None
        return Tag.objects.filter(slug=self.criteria.tag_slug).first()

    @staticmethod
    def _apply_sections(queryset, section, subsection):
        if section is not None:
            queryset = queryset.filter(
                Q(section_assignments__section=section)
                | Q(section_assignments__section__parent=section)
            ).distinct()
        if subsection is not None:
            queryset = queryset.filter(
                section_assignments__section=subsection
            ).distinct()
        return queryset

    def _apply_search(self, queryset, section, subsection, tag):
        if not self.criteria.has_effective_search:
            queryset = self._apply_sections(queryset, section, subsection)
            if tag is not None:
                queryset = queryset.filter(tags=tag).distinct()
            return queryset.order_by(*self.criteria.chronological_ordering)

        chronological = bool(self.criteria.order)
        search_queryset = queryset.order_by(*self.criteria.chronological_ordering)
        fts_results = search_queryset.search(
            self.criteria.search,
            operator="or",
            order_by_relevance=not chronological,
        )
        fts_queryset = self._apply_structured_filters(
            fts_results.get_queryset(), section, subsection, tag
        )
        if fts_queryset.count():
            return self._order_search_results(fts_queryset, chronological)
        fuzzy_queryset = search_queryset.search(
            Fuzzy(self.criteria.search, unaccent=True),
            order_by_relevance=not chronological,
        ).get_queryset()
        fuzzy_queryset = self._apply_structured_filters(
            fuzzy_queryset, section, subsection, tag
        )
        return self._order_search_results(fuzzy_queryset, chronological)

    def _apply_structured_filters(self, queryset, section, subsection, tag):
        """Apply archive-only joins after ModelSearch compiles the text query."""
        queryset = self._apply_sections(queryset, section, subsection)
        if tag is not None:
            queryset = queryset.filter(tags=tag).distinct()
        return queryset

    def _order_search_results(self, queryset, chronological):
        if chronological:
            return queryset.order_by(*self.criteria.chronological_ordering)
        return queryset
