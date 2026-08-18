from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.urls import reverse
from wagtail import hooks
from wagtail.admin.admin_url_finder import ModelAdminURLFinder
from wagtail.admin.forms import WagtailAdminModelForm
from wagtail.admin.panels import FieldPanel
from wagtail.admin.ui.tables import TitleColumn
from wagtail.admin.views import generic
from wagtail.admin.views.generic import chooser as generic_chooser
from wagtail.admin.views.generic import history, usage
from wagtail.admin.views.generic.chooser import BaseFilterForm
from wagtail.admin.viewsets.chooser import ChooserViewSet
from wagtail.admin.viewsets.model import ModelViewSet
from wagtail.admin.widgets import BaseChooser
from wagtail.images.widgets import AdminImageChooser
from wagtail.permission_policies import ModelPermissionPolicy
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views import chooser as snippet_chooser
from wagtail.snippets.views import snippets as snippet_views
from wagtail.snippets.views.snippets import (
    SnippetChooserViewSet,
    SnippetViewSet,
    SnippetViewSetGroup,
)

from . import wagtail_hook_handlers
from .access import FULL_EDITOR_PERMISSION
from .models import (
    AuthorProfile,
    ContributorGroup,
    MinorContributor,
    NewsSection,
    School,
)
from .school_forms import SchoolAdminForm
from .taxonomy_forms import NewsSubsectionAdminForm


def author_profile_user_label(user):
    full_name = user.get_full_name().strip()
    if full_name:
        return f"{full_name} (@{user.get_username()})"
    return f"@{user.get_username()}"


class AuthorProfileUserChooserWidget(BaseChooser):
    model = get_user_model()
    icon = "user"
    show_edit_link = False
    link_to_chosen_text = ""

    def get_display_title(self, instance):
        return author_profile_user_label(instance)


class AuthorProfileUserChooserFilterForm(BaseFilterForm):
    q = forms.CharField(label="Buscar", required=False)

    def filter(self, objects):
        query = self.cleaned_data["q"].strip()
        self.search_query = query
        self.is_searching = bool(query)
        if not query:
            return objects
        for term in query.split():
            objects = objects.filter(
                Q(first_name__icontains=term)
                | Q(last_name__icontains=term)
                | Q(username__icontains=term)
            )
        return objects


class AuthorProfileUserChooserPermissionMixin:
    def dispatch(self, request, *args, **kwargs):
        if not request.user.has_perm(FULL_EDITOR_PERMISSION):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class AuthorProfileUserChooseView(
    AuthorProfileUserChooserPermissionMixin,
    generic_chooser.ChooseView,
):
    filter_form_class = AuthorProfileUserChooserFilterForm

    def get_object_list(self):
        return get_user_model().objects.exclude(author_profile__isnull=False)

    @property
    def title_column(self):
        return TitleColumn(
            "title",
            label="Usuario interno",
            accessor=author_profile_user_label,
            get_url=lambda user: self.append_preserved_url_parameters(
                reverse(self.chosen_url_name, args=(user.pk,))
            ),
            link_attrs={"data-chooser-modal-choice": True},
        )


class AuthorProfileUserChooseResultsView(
    AuthorProfileUserChooserPermissionMixin,
    generic_chooser.ChooseResultsView,
):
    filter_form_class = AuthorProfileUserChooserFilterForm

    def get_object_list(self):
        return get_user_model().objects.exclude(author_profile__isnull=False)

    @property
    def title_column(self):
        return TitleColumn(
            "title",
            label="Usuario interno",
            accessor=author_profile_user_label,
            get_url=lambda user: self.append_preserved_url_parameters(
                reverse(self.chosen_url_name, args=(user.pk,))
            ),
            link_attrs={"data-chooser-modal-choice": True},
        )


class AuthorProfileUserChosenView(
    AuthorProfileUserChooserPermissionMixin,
    generic_chooser.ChosenView,
):
    def get_display_title(self, instance):
        return author_profile_user_label(instance)

    def get_edit_item_url(self, instance):
        return None


class AuthorProfileUserChooserViewSet(ChooserViewSet):
    model = get_user_model()
    icon = "user"
    choose_one_text = "Seleccionar usuario interno"
    choose_another_text = "Seleccionar otro usuario interno"
    edit_item_text = ""
    base_widget_class = AuthorProfileUserChooserWidget
    choose_view_class = AuthorProfileUserChooseView
    choose_results_view_class = AuthorProfileUserChooseResultsView
    chosen_view_class = AuthorProfileUserChosenView


author_profile_user_chooser = AuthorProfileUserChooserViewSet(
    "author_profile_user_chooser"
)


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
    form_class = SchoolAdminForm
    menu_label = "Colegios"
    menu_name = "schools"
    icon = "site"

    def get_form_class(self, for_update=False):
        return self.form_class


class AuthorProfileAdminForm(WagtailAdminModelForm):
    """Keep public slugs stable while using native Wagtail chooser widgets."""

    class Meta:
        model = AuthorProfile
        fields = (
            "display_name",
            "photo",
            "bio",
            "email",
            "position",
            "work_url",
            "user",
            "minor_contributor",
            "is_active",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["photo"].widget = AdminImageChooser()
        field = self.fields["user"]
        field.widget = author_profile_user_chooser.widget_class()
        queryset = get_user_model().objects.exclude(author_profile__isnull=False)
        if self.instance.user_id:
            queryset = queryset | get_user_model().objects.filter(
                pk=self.instance.user_id
            )
        field.queryset = queryset
        self.fields[
            "minor_contributor"
        ].widget = MinorContributorViewSet().chooser_viewset.widget_class


class AuthorProfileChooserForm(AuthorProfileAdminForm):
    class Meta:
        model = AuthorProfile
        fields = (
            "display_name",
            "photo",
            "bio",
            "email",
            "position",
            "work_url",
            "user",
            "minor_contributor",
            "is_active",
        )


class AuthorProfileChooserFilterForm(BaseFilterForm):
    q = forms.CharField(label="Buscar", required=False)

    def filter(self, objects):
        query = self.cleaned_data["q"].strip()
        self.search_query = query
        self.is_searching = bool(query)
        if not query:
            return objects
        return objects.filter(
            Q(display_name__icontains=query) | Q(slug__icontains=query)
        )


class ViewPermissionChooserMixin:
    """Require view permission before exposing a contextual chooser response."""

    def dispatch(self, request, *args, **kwargs):
        permission_policy = getattr(self, "permission_policy", None) or (
            ModelPermissionPolicy(self.model)
        )
        if not permission_policy.user_has_permission(request.user, "view"):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class ViewPermissionSnippetChooseView(
    ViewPermissionChooserMixin, snippet_chooser.ChooseView
):
    pass


class ViewPermissionSnippetChooseResultsView(
    ViewPermissionChooserMixin, snippet_chooser.ChooseResultsView
):
    pass


class ViewPermissionSnippetChosenView(
    ViewPermissionChooserMixin, snippet_chooser.SnippetChosenView
):
    pass


class ViewPermissionSnippetChosenMultipleView(
    ViewPermissionChooserMixin, snippet_chooser.SnippetChosenMultipleView
):
    pass


class ViewPermissionSnippetChooserViewSet(SnippetChooserViewSet):
    choose_view_class = ViewPermissionSnippetChooseView
    choose_results_view_class = ViewPermissionSnippetChooseResultsView
    chosen_view_class = ViewPermissionSnippetChosenView
    chosen_multiple_view_class = ViewPermissionSnippetChosenMultipleView


class SchoolChooserViewSet(ViewPermissionSnippetChooserViewSet):
    creation_form_class = SchoolAdminForm


class ContributorGroupChooserViewSet(ViewPermissionSnippetChooserViewSet):
    form_fields = ("name", "school")


class MinorContributorChooserFilterForm(BaseFilterForm):
    q = forms.CharField(label="Buscar", required=False)

    def filter(self, objects):
        query = self.cleaned_data["q"].strip()
        self.search_query = query
        self.is_searching = bool(query)
        if not query:
            return objects
        return objects.filter(full_name__icontains=query)


class MinorContributorChooseView(ViewPermissionSnippetChooseView):
    filter_form_class = MinorContributorChooserFilterForm


class MinorContributorChooseResultsView(ViewPermissionSnippetChooseResultsView):
    filter_form_class = MinorContributorChooserFilterForm


class MinorContributorChooserViewSet(ViewPermissionSnippetChooserViewSet):
    form_fields = ("full_name", "group", "age_band")
    choose_view_class = MinorContributorChooseView
    choose_results_view_class = MinorContributorChooseResultsView


class ContributorGroupViewSet(SnippetViewSet):
    model = ContributorGroup
    menu_label = "Grupos de colaboradores"
    menu_name = "contributor-groups"
    icon = "group"
    chooser_viewset_class = ContributorGroupChooserViewSet


class MinorContributorViewSet(SnippetViewSet):
    model = MinorContributor
    menu_label = "Colaboradores menores"
    menu_name = "minor-contributors"
    icon = "user"
    chooser_viewset_class = MinorContributorChooserViewSet


class ActiveAuthorProfileChooserMixin:
    def get_object_list(self):
        return super().get_object_list().filter(is_active=True)


class ActiveAuthorProfileChooseView(
    ActiveAuthorProfileChooserMixin,
    ViewPermissionSnippetChooseView,
):
    filter_form_class = AuthorProfileChooserFilterForm


class ActiveAuthorProfileChooseResultsView(
    ActiveAuthorProfileChooserMixin,
    ViewPermissionSnippetChooseResultsView,
):
    filter_form_class = AuthorProfileChooserFilterForm


class AuthorProfileChooserViewSet(ViewPermissionSnippetChooserViewSet):
    choose_view_class = ActiveAuthorProfileChooseView
    choose_results_view_class = ActiveAuthorProfileChooseResultsView
    creation_form_class = AuthorProfileChooserForm


class AuthorProfileViewSet(SnippetViewSet):
    model = AuthorProfile
    menu_label = "Perfiles públicos de autor"
    menu_name = "author-profiles"
    icon = "user"
    list_display = ("display_name", "slug", "position", "is_active")
    search_fields = ("display_name", "slug", "position")
    form_class = AuthorProfileAdminForm
    chooser_viewset_class = AuthorProfileChooserViewSet

    def get_form_class(self, for_update=False):
        return self.form_class


SchoolViewSet.chooser_viewset_class = SchoolChooserViewSet


class EditorialViewSetGroup(SnippetViewSetGroup):
    items = (
        NewsSectionViewSet,
        NewsSubsectionViewSet,
        SchoolViewSet,
        ContributorGroupViewSet,
        MinorContributorViewSet,
        AuthorProfileViewSet,
    )
    menu_label = "Editorial"
    menu_icon = "doc-full-inverse"
    menu_order = 250


register_snippet(EditorialViewSetGroup)


@hooks.register("register_admin_viewset")
def register_author_profile_user_chooser():
    return author_profile_user_chooser


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
