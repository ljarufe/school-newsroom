from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import NewsPage, NewsSection


def _section_order(section: NewsSection) -> tuple:
    root = section.parent if section.parent_id else section
    return (
        root.sort_order,
        root.name.casefold(),
        root.pk,
        0 if section.parent_id is None else 1,
        section.sort_order,
        section.name.casefold(),
        section.pk,
    )


@dataclass(frozen=True)
class NewsTaxonomy:
    """Expose every derived classification view from one ordered boundary."""

    explicit_sections: tuple[NewsSection, ...]

    @classmethod
    def from_page(cls, page: NewsPage) -> NewsTaxonomy:
        assignments = cls._assignments_for_page(page)
        sections = cls._sections_for_assignments(assignments)
        return cls.from_sections(sections)

    @classmethod
    def from_sections(cls, sections: Iterable[NewsSection]) -> NewsTaxonomy:
        unique_sections = {section.pk: section for section in sections if section.pk}
        return cls(tuple(sorted(unique_sections.values(), key=_section_order)))

    @staticmethod
    def _assignments_for_page(page: NewsPage) -> list:
        prefetched = getattr(page, "_prefetched_objects_cache", {}).get(
            "section_assignments"
        )
        if prefetched is not None:
            return list(prefetched)

        manager = page.section_assignments
        cluster_relations = getattr(page, "_cluster_related_objects", {})
        if "section_assignments" in cluster_relations:
            return list(manager.all())
        if page.pk:
            return list(manager.select_related("section__parent"))
        return list(manager.all())

    @staticmethod
    def _sections_for_assignments(assignments: list) -> list[NewsSection]:
        cached_sections: dict[int, NewsSection] = {}
        missing_ids: set[int] = set()
        for assignment in assignments:
            section_id = assignment.section_id
            if not section_id:
                continue
            if "section" in assignment._state.fields_cache:
                section = assignment.section
                if section.parent_id is None or "parent" in section._state.fields_cache:
                    cached_sections[section_id] = section
                else:
                    missing_ids.add(section_id)
            else:
                missing_ids.add(section_id)

        if missing_ids:
            from .models import NewsSection

            cached_sections.update(
                NewsSection.objects.select_related("parent").in_bulk(missing_ids)
            )
        return [
            cached_sections[assignment.section_id]
            for assignment in assignments
            if assignment.section_id in cached_sections
        ]

    @property
    def effective_main_sections(self) -> tuple[NewsSection, ...]:
        roots = {
            (section.parent_id or section.pk): (
                section.parent if section.parent_id else section
            )
            for section in self.explicit_sections
        }
        return tuple(sorted(roots.values(), key=_section_order))

    @property
    def visible_paths(self) -> tuple[str, ...]:
        branches_with_children = {
            section.parent_id
            for section in self.explicit_sections
            if section.parent_id is not None
        }
        paths = []
        for section in self.explicit_sections:
            if section.parent_id is None:
                if section.pk not in branches_with_children:
                    paths.append(section.name)
                continue
            paths.append(f"{section.parent.name} › {section.name}")
        return tuple(paths)

    @property
    def article_section_values(self) -> tuple[str, ...]:
        values_by_key: dict[tuple, str] = {}
        for root in self.effective_main_sections:
            values_by_key[_section_order(root)] = root.name
        for section in self.explicit_sections:
            if section.parent_id:
                values_by_key[_section_order(section)] = (
                    f"{section.parent.name} > {section.name}"
                )
        return tuple(values_by_key[key] for key in sorted(values_by_key))

    @property
    def compact_main_names(self) -> str:
        return ", ".join(section.name for section in self.effective_main_sections)


def revision_content_references_section(content: dict, section_ids: set[int]) -> bool:
    """Recognize both migrated child rows and fail-safe legacy revision data."""

    if content.get("section") in section_ids:
        return True
    return any(
        isinstance(assignment, dict) and assignment.get("section") in section_ids
        for assignment in content.get("section_assignments", [])
    )
