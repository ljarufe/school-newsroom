import pytest
from django.conf import settings
from django.test import Client, override_settings
from wagtail.models import Page, PageViewRestriction, Site

from apps.home.models import HomePage, InstitutionalPage


def test_django_settings_load() -> None:
    assert settings.WAGTAIL_SITE_NAME == "School Newsroom"


@pytest.mark.django_db
def test_wagtail_admin_login_loads() -> None:
    response = Client().get("/admin/", follow=True)
    assert response.status_code == 200
    assert response.redirect_chain == [("/admin/login/?next=/admin/", 302)]


@pytest.fixture
def public_home():
    root = Page.get_first_root_node()
    home = HomePage(title="School Newsroom", slug="institutional-test-home")
    root.add_child(instance=home)
    Site.objects.update_or_create(
        hostname="testserver",
        defaults={
            "port": 80,
            "site_name": "School Newsroom",
            "root_page": home,
            "is_default_site": True,
        },
    )
    return home


@pytest.mark.django_db
def test_institutional_page_tree_constraints(public_home) -> None:
    assert InstitutionalPage.can_create_at(public_home)
    assert InstitutionalPage in HomePage.allowed_subpage_models()
    assert InstitutionalPage.allowed_subpage_models() == []


@pytest.mark.django_db
def test_institutional_page_renders_with_shared_layout(public_home) -> None:
    page = InstitutionalPage(
        title="Sobre el proyecto",
        slug="sobre-el-proyecto",
        introduction="Una introducción institucional ficticia.",
        body="<h2>Propósito</h2><p>Contenido institucional ficticio.</p>",
        show_in_menus=True,
    )
    public_home.add_child(instance=page)

    response = Client().get(page.url)
    content = response.content.decode()

    assert response.status_code == 200
    assert "Sobre el proyecto" in content
    assert "Una introducción institucional ficticia." in content
    assert "<h2>Propósito</h2>" in content
    assert "Navegación principal" in content
    assert '<main id="main-content"' in content
    assert "<footer" in content


@pytest.mark.django_db
def test_navigation_only_includes_public_menu_institutional_pages(
    public_home,
) -> None:
    menu_page = InstitutionalPage(
        title="Página visible en menú",
        slug="pagina-visible-en-menu",
        introduction="Introducción ficticia.",
        body="<p>Contenido ficticio.</p>",
        show_in_menus=True,
    )
    public_home.add_child(instance=menu_page)
    hidden_page = InstitutionalPage(
        title="Página fuera del menú",
        slug="pagina-fuera-del-menu",
        introduction="Introducción ficticia.",
        body="<p>Contenido ficticio.</p>",
        show_in_menus=False,
    )
    public_home.add_child(instance=hidden_page)
    draft_page = InstitutionalPage(
        title="Borrador fuera del menú público",
        slug="borrador-fuera-del-menu-publico",
        introduction="Introducción ficticia.",
        body="<p>Contenido ficticio.</p>",
        show_in_menus=True,
        live=False,
    )
    public_home.add_child(instance=draft_page)
    restricted_page = InstitutionalPage(
        title="Página restringida fuera del menú público",
        slug="pagina-restringida-fuera-del-menu-publico",
        introduction="Introducción ficticia.",
        body="<p>Contenido ficticio.</p>",
        show_in_menus=True,
    )
    public_home.add_child(instance=restricted_page)
    PageViewRestriction.objects.create(
        page=restricted_page,
        restriction_type=PageViewRestriction.LOGIN,
    )

    content = Client().get("/").content.decode()

    assert "Página visible en menú" in content
    assert "Página fuera del menú" not in content
    assert "Borrador fuera del menú público" not in content
    assert "Página restringida fuera del menú público" not in content


def test_institutional_page_uses_spanish_field_labels_and_help_text() -> None:
    introduction = InstitutionalPage._meta.get_field("introduction")
    body = InstitutionalPage._meta.get_field("body")

    assert introduction.verbose_name == "Introducción"
    assert "Resume el propósito" in introduction.help_text
    assert body.verbose_name == "Contenido"
    assert "contenido institucional sencillo" in body.help_text
    assert body.features == [
        "bold",
        "italic",
        "link",
        "h2",
        "h3",
        "ul",
        "ol",
        "blockquote",
    ]


@pytest.mark.django_db
@override_settings(SEO_DEFAULT_NOINDEX=True)
def test_institutional_page_is_excluded_from_sitemap_when_environment_noindex(
    public_home,
) -> None:
    page = InstitutionalPage(
        title="Página institucional no indexable",
        slug="pagina-institucional-no-indexable",
        introduction="Introducción institucional ficticia.",
        body="<p>Contenido institucional ficticio.</p>",
    )
    public_home.add_child(instance=page)

    assert page.get_sitemap_urls() == []


@pytest.mark.django_db
@override_settings(SEO_DEFAULT_NOINDEX=False)
def test_institutional_page_is_included_in_sitemap_when_environment_is_indexable(
    public_home,
) -> None:
    page = InstitutionalPage(
        title="Página institucional indexable",
        slug="pagina-institucional-indexable",
        introduction="Introducción institucional ficticia.",
        body="<p>Contenido institucional ficticio.</p>",
    )
    public_home.add_child(instance=page)

    sitemap_urls = page.get_sitemap_urls()

    assert len(sitemap_urls) == 1
    assert sitemap_urls[0]["location"] == page.get_full_url()
