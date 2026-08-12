from django.shortcuts import get_object_or_404
from django.urls import reverse
from wagtail import hooks
from wagtail.admin.admin_url_finder import ModelAdminURLFinder
from wagtail.admin.panels import FieldPanel
from wagtail.admin.views import generic
from wagtail.admin.views.generic import history, usage
from wagtail.admin.viewsets.model import ModelViewSet
from wagtail.permission_policies import ModelPermissionPolicy
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views import snippets as snippet_views
from wagtail.snippets.views.snippets import SnippetViewSet, SnippetViewSetGroup

from . import wagtail_hook_handlers
from .models import ContributorGroup, MinorContributor, NewsSection, School
from .taxonomy_forms import NewsSubsectionAdminForm


class MainSectionObjectQuerySetMixin:
    def get_base_object_queryset(self):
        return super().get_base_object_queryset().filter(parent__isnull=True)


class MainSectionSingleObjectQuerySetMixin:
    def get_queryset(self):
        return super().get_queryset().filter(parent__isnull=True)


class SubsectionObjectQuerySetMixin:
    def get_base_object_queryset(self):
        return super().get_base_object_queryset().filter(parent__isnull=False)


class SubsectionSingleObjectQuerySetMixin:
    def get_queryset(self):
        return super().get_queryset().filter(parent__isnull=False)


class MainSectionIndexView(snippet_views.IndexView):
    page_title = "Secciones"
    add_item_label = "Añadir sección"


class MainSectionCreateView(snippet_views.CreateView):
    page_title = "Crear sección"
    page_subtitle = "Sección"
    success_message = "Sección '%(object)s' creada."
    error_message = "No se pudo crear la sección debido a errores."

    def get_breadcrumbs_items(self):
        return [
            *self.breadcrumbs_items,
            {
                "url": reverse(self.index_url_name),
                "label": "Secciones",
            },
            {"url": "", "label": "Nueva: Sección"},
        ]


class MainSectionEditView(
    MainSectionSingleObjectQuerySetMixin,
    snippet_views.EditView,
):
    page_title = "Editar sección"


class MainSectionDeleteView(
    MainSectionSingleObjectQuerySetMixin,
    snippet_views.DeleteView,
):
    pass


class MainSectionCopyView(
    MainSectionSingleObjectQuerySetMixin,
    snippet_views.CopyView,
):
    def get_object(self, queryset=None):
        return get_object_or_404(
            NewsSection.objects.filter(parent__isnull=True),
            pk=self.kwargs[self.pk_url_kwarg],
        )


class MainSectionHistoryView(MainSectionObjectQuerySetMixin, snippet_views.HistoryView):
    pass


class MainSectionUsageView(MainSectionObjectQuerySetMixin, snippet_views.UsageView):
    pass


class SubsectionIndexView(generic.IndexView):
    page_title = "Subsecciones"
    add_item_label = "Añadir subsección"


class SubsectionCreateView(generic.CreateView):
    page_title = "Crear subsección"
    page_subtitle = "Subsección"
    success_message = "Subsección '%(object)s' creada."
    error_message = "No se pudo crear la subsección debido a errores."

    def get_breadcrumbs_items(self):
        return [
            *self.breadcrumbs_items,
            {
                "url": reverse(self.index_url_name),
                "label": "Subsecciones",
            },
            {"url": "", "label": "Nueva: Subsección"},
        ]


class SubsectionEditView(SubsectionSingleObjectQuerySetMixin, generic.EditView):
    page_title = "Editar subsección"


class SubsectionDeleteView(SubsectionSingleObjectQuerySetMixin, generic.DeleteView):
    def run_before_hook(self):
        return _news_section_deletion_protection_response(
            self.request,
            [self.object],
            redirect_name="news_subsections:index",
        )


class SubsectionCopyView(SubsectionSingleObjectQuerySetMixin, generic.CopyView):
    def get_object(self, queryset=None):
        return get_object_or_404(
            NewsSection.objects.filter(parent__isnull=False),
            pk=self.kwargs[self.pk_url_kwarg],
        )


class SubsectionHistoryView(SubsectionObjectQuerySetMixin, history.HistoryView):
    pass


class SubsectionUsageView(SubsectionObjectQuerySetMixin, usage.UsageView):
    pass


class NewsSectionAdminURLFinder(ModelAdminURLFinder):
    permission_policy = ModelPermissionPolicy(NewsSection)

    def construct_edit_url(self, instance):
        queryset = NewsSection.objects
        if instance._state.db:
            queryset = queryset.using(instance._state.db)
        try:
            parent_id = queryset.values_list("parent_id", flat=True).get(pk=instance.pk)
        except NewsSection.DoesNotExist:
            return None

        if parent_id is None:
            url_name = "wagtailsnippets_news_newssection:edit"
        else:
            url_name = "news_subsections:edit"
        return reverse(url_name, args=(instance.pk,))


class NewsSectionViewSet(SnippetViewSet):
    model = NewsSection
    menu_label = "Secciones"
    menu_name = "news-sections"
    icon = "folder-open-inverse"
    list_display = ("name", "slug", "sort_order")
    ordering = ("sort_order", "name", "pk")
    search_fields = ("name", "slug")
    list_per_page = 100
    panels = [
        FieldPanel("name"),
        FieldPanel("slug"),
        FieldPanel("sort_order"),
    ]
    index_view_class = MainSectionIndexView
    add_view_class = MainSectionCreateView
    edit_view_class = MainSectionEditView
    delete_view_class = MainSectionDeleteView
    copy_view_class = MainSectionCopyView
    history_view_class = MainSectionHistoryView
    usage_view_class = MainSectionUsageView
    url_finder_class = NewsSectionAdminURLFinder

    def get_queryset(self, request):
        return NewsSection.objects.filter(parent__isnull=True)


class NewsSubsectionViewSet(ModelViewSet):
    model = NewsSection
    name = "news_subsections"
    url_prefix = "news/subsections"
    menu_label = "Subsecciones"
    menu_name = "news-subsections"
    icon = "list-ul"
    list_display = ("name", "parent", "slug", "sort_order")
    ordering = (
        "parent__sort_order",
        "parent__name",
        "parent_id",
        "sort_order",
        "name",
        "pk",
    )
    search_fields = ("name", "slug", "parent__name")
    list_per_page = 100
    panels = [
        FieldPanel("name"),
        FieldPanel("slug"),
        FieldPanel("parent"),
        FieldPanel("sort_order"),
    ]
    index_view_class = SubsectionIndexView
    add_view_class = SubsectionCreateView
    edit_view_class = SubsectionEditView
    delete_view_class = SubsectionDeleteView
    copy_view_class = SubsectionCopyView
    history_view_class = SubsectionHistoryView
    usage_view_class = SubsectionUsageView

    def get_form_class(self, for_update=False):
        return NewsSubsectionAdminForm

    def get_index_view_kwargs(self, **kwargs):
        return super().get_index_view_kwargs(
            queryset=NewsSection.objects.filter(parent__isnull=False),
            **kwargs,
        )

    def register_admin_url_finder(self):
        # Keep the snippet registration as the canonical URL finder for the
        # shared model. This second supported surface owns its own view URLs.
        return None


class SchoolViewSet(SnippetViewSet):
    model = School
    menu_label = "Colegios"
    menu_name = "schools"
    icon = "site"


class ContributorGroupViewSet(SnippetViewSet):
    model = ContributorGroup
    menu_label = "Grupos de colaboradores"
    menu_name = "contributor-groups"
    icon = "group"


class MinorContributorViewSet(SnippetViewSet):
    model = MinorContributor
    menu_label = "Colaboradores menores"
    menu_name = "minor-contributors"
    icon = "user"


class EditorialViewSetGroup(SnippetViewSetGroup):
    items = (
        NewsSectionViewSet,
        NewsSubsectionViewSet,
        SchoolViewSet,
        ContributorGroupViewSet,
        MinorContributorViewSet,
    )
    menu_label = "Editorial"
    menu_icon = "doc-full-inverse"
    menu_order = 250


register_snippet(EditorialViewSetGroup)


_news_section_deletion_is_protected = (
    wagtail_hook_handlers.news_section_deletion_is_protected
)
_news_section_deletion_protection_response = (
    wagtail_hook_handlers.news_section_deletion_protection_response
)


@hooks.register("before_delete_snippet")
def protect_news_section_deletion(request, snippets):
    return wagtail_hook_handlers.protect_news_section_deletion(request, snippets)


@hooks.register("register_admin_urls")
def register_news_admin_urls():
    return wagtail_hook_handlers.register_news_admin_urls()


@hooks.register("after_edit_page")
def redirect_after_workflow_action_when_edit_access_ends(request, page):
    return wagtail_hook_handlers.redirect_after_workflow_action_when_edit_access_ends(
        request,
        page,
    )
