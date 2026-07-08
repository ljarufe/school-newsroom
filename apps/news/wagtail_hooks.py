from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet, SnippetViewSetGroup

from .models import ContributorGroup, MinorContributor, NewsSection, School


class NewsSectionViewSet(SnippetViewSet):
    model = NewsSection
    menu_label = "Secciones editoriales"
    menu_name = "news-sections"
    icon = "folder-open-inverse"


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
        SchoolViewSet,
        ContributorGroupViewSet,
        MinorContributorViewSet,
    )
    menu_label = "Editorial"
    menu_icon = "doc-full-inverse"
    menu_order = 250


register_snippet(EditorialViewSetGroup)
