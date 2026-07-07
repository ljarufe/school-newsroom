from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet, SnippetViewSetGroup

from .models import NewsSection, School


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


class EditorialViewSetGroup(SnippetViewSetGroup):
    items = (NewsSectionViewSet, SchoolViewSet)
    menu_label = "Editorial"
    menu_icon = "doc-full-inverse"
    menu_order = 250


register_snippet(EditorialViewSetGroup)
