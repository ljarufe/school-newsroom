import datetime as dt
import json
import re
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from wagtail.models import Page, Site

from apps.home.models import HomePage
from apps.news.models import NewsPage, NewsPageSection, NewsSection
from apps.news.taxonomy_forms import NewsSubsectionAdminForm


@pytest.fixture
def admin_client():
    user = get_user_model().objects.create_superuser(
        username="admin-uat",
        email="admin-uat@example.com",
        password="test-password",
    )
    client = Client()
    client.force_login(user)
    return client


def assert_contains_text(response, text: str) -> None:
    assert text in response.content.decode()


def assert_not_contains_text(response, text: str) -> None:
    assert text not in response.content.decode()


def assert_contains_telepath_text(response, text: str) -> None:
    content = response.content.decode()
    json_encoded = json.dumps(text, ensure_ascii=True)[1:-1]
    assert text in content or json_encoded in content


def test_seo_assistant_javascript_restores_served_url_after_canonical_clear() -> None:
    source = Path("static/news/js/seo_assistant.js").read_text()

    assert "const servedPublicUrl = root.dataset.publicUrl;" in source
    assert "let previewUrl = canonical;" in source
    assert "if (!previewUrl && servedPublicUrl && currentSlug && slug)" in source
    assert "servedPublicUrl.endsWith(currentSuffix)" in source


def test_seo_assistant_javascript_persists_tab_only_after_successful_draft_save() -> (
    None
):
    source = Path("static/news/js/seo_assistant.js").read_text()

    assert 'const storageKey = "news:seo-assistant:active-tab";' in source
    assert "const storageMaxAgeMs = 60 * 1000;" in source
    assert 'currentPath.includes("/pages/add/")' in source
    assert r"/\/pages\/\d+\/edit\/?$/.test(currentPath)" in source
    assert "parsedState.wasCreatePage === true && isEditPage" in source
    assert "parsedState.pathname === currentPath" in source
    assert "ageMs <= storageMaxAgeMs" in source
    assert "JSON.stringify({" in source
    assert "wasCreatePage: isCreatePage" in source
    assert "savedAt: Date.now()" in source
    assert "active-tab:${window.location.pathname}" not in source

    assert 'event.submitter?.classList.contains("action-save")' in source
    assert "if (!isDraftSave || panel.hidden)" in source
    assert "window.sessionStorage.setItem(" in source
    assert "window.sessionStorage.removeItem(storageKey)" in source

    assert 'data-w-messages-target="container"] > li.success' in source
    assert '[aria-invalid="true"], .error-message, .w-field--error' in source
    assert "!hasValidationErrors" in source
    assert "!anotherPanelWasRequested" in source
    assert (
        "tabs.querySelector(\n"
        '        `[role="tab"][aria-controls="${panel.id}"]`,' in source
    )
    assert "trigger.click()" in source


@pytest.mark.django_db
def test_seo_assistant_keeps_served_url_separate_from_external_canonical(
    admin_client,
) -> None:
    home = HomePage.objects.first()
    if home is None:
        root = Page.get_first_root_node()
        home = HomePage(title="Inicio", slug="inicio-canonical-preview")
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
    page = NewsPage(
        title="Canonical Preview News",
        slug="canonical-preview-news",
        publication_date=dt.date(2026, 7, 12),
        body=[("paragraph", "<p>Contenido ficticio.</p>")],
        coverage_province="Arequipa",
        canonical_url="https://canonical.example.org/original",
    )
    home.add_child(instance=page)
    NewsPageSection.objects.create(
        page=page,
        section=NewsSection.objects.get(slug="politica"),
    )

    response = admin_client.get(
        reverse("wagtailadmin_pages:edit", args=(page.pk,)),
    )
    content = response.content.decode()

    assert response.status_code == 200
    assert 'data-public-url="http://testserver/canonical-preview-news/"' in content
    assert (
        '<p class="seo-assistant__preview-url" data-seo-preview-url>'
        "https://canonical.example.org/original</p>" in content
    )


@pytest.mark.django_db
def test_wagtail_dashboard_uses_spanish_search_and_editorial_menu(admin_client):
    response = admin_client.get(reverse("wagtailadmin_home"))

    assert response.status_code == 200
    assert_contains_text(response, "Buscar en todas las páginas...")
    assert_contains_text(response, "Editorial")
    assert_contains_text(response, "Secciones")
    assert_contains_text(response, "Subsecciones")
    assert_contains_text(response, "Colegios")
    assert_contains_text(response, "Grupos de colaboradores")
    assert_contains_text(response, "Colaboradores menores")
    assert_not_contains_text(response, "Search all pages")


@pytest.mark.django_db
def test_editorial_snippet_destinations_are_available(admin_client):
    section_response = admin_client.get(
        reverse("wagtailsnippets_news_newssection:list"),
    )
    subsection_response = admin_client.get(reverse("news_subsections:index"))
    school_response = admin_client.get(reverse("wagtailsnippets_news_school:list"))
    group_response = admin_client.get(
        reverse("wagtailsnippets_news_contributorgroup:list"),
    )
    contributor_response = admin_client.get(
        reverse("wagtailsnippets_news_minorcontributor:list"),
    )

    assert section_response.status_code == 200
    assert subsection_response.status_code == 200
    assert school_response.status_code == 200
    assert group_response.status_code == 200
    assert contributor_response.status_code == 200
    culture = NewsSection.objects.get(slug="cultura")
    music = NewsSection.objects.get(slug="musica")
    assert_contains_text(section_response, "Secciones")
    assert_contains_text(section_response, "Añadir sección")
    assert_not_contains_text(section_response, "Añadir Sección editorial")
    assert_contains_text(
        section_response,
        reverse("wagtailsnippets_news_newssection:edit", args=(culture.pk,)),
    )
    assert_not_contains_text(
        section_response,
        reverse("wagtailsnippets_news_newssection:edit", args=(music.pk,)),
    )
    assert_contains_text(subsection_response, "Subsecciones")
    assert_contains_text(subsection_response, "Añadir subsección")
    assert_not_contains_text(subsection_response, "Añadir Sección editorial")
    assert_contains_text(
        subsection_response, reverse("news_subsections:edit", args=(music.pk,))
    )
    assert_not_contains_text(
        subsection_response, reverse("news_subsections:edit", args=(culture.pk,))
    )
    assert_contains_text(subsection_response, "Cultura")
    assert_contains_text(school_response, "Colegios")
    assert_contains_text(group_response, "Grupos de colaboradores")
    assert_contains_text(contributor_response, "Colaboradores menores")


@pytest.mark.django_db
def test_taxonomy_management_forms_keep_types_fixed_and_parent_choices_root_only(
    admin_client,
) -> None:
    culture = NewsSection.objects.get(slug="cultura")
    politics = NewsSection.objects.get(slug="politica")
    music = NewsSection.objects.get(slug="musica")

    section_add_response = admin_client.get(
        reverse("wagtailsnippets_news_newssection:add")
    )
    subsection_add_response = admin_client.get(reverse("news_subsections:add"))

    assert section_add_response.status_code == 200
    assert subsection_add_response.status_code == 200
    section_add_content = section_add_response.content.decode()
    subsection_add_content = subsection_add_response.content.decode()
    assert re.search(
        r'<h2[^>]+id="header-title"[^>]*>.*?<span>Sección</span>.*?</h2>',
        section_add_content,
        flags=re.DOTALL,
    )
    assert re.search(
        r'<h2[^>]+id="header-title"[^>]*>.*?<span>Subsección</span>.*?</h2>',
        subsection_add_content,
        flags=re.DOTALL,
    )
    assert "Crear sección: Sección" in section_add_content
    assert "Crear subsección: Subsección" in subsection_add_content
    assert "Nueva: Sección" in section_add_content
    assert "Nueva: Subsección" in subsection_add_content
    assert 'name="parent"' not in section_add_response.content.decode()
    assert 'name="parent"' in subsection_add_response.content.decode()
    assert_contains_text(subsection_add_response, "Sección principal")

    subsection_form = NewsSubsectionAdminForm()
    parent_slugs = list(
        subsection_form.fields["parent"].queryset.values_list("slug", flat=True)
    )
    assert subsection_form.fields["parent"].required
    assert "cultura" in parent_slugs
    assert "politica" in parent_slugs
    assert "musica" not in parent_slugs
    assert not NewsSubsectionAdminForm(
        data={
            "name": "Subsección manipulada",
            "slug": "subseccion-manipulada",
            "parent": music.pk,
            "sort_order": 100,
        }
    ).is_valid()

    section_create_response = admin_client.post(
        reverse("wagtailsnippets_news_newssection:add"),
        {
            "name": "Sección creada",
            "slug": "seccion-creada",
            "sort_order": 70,
            "parent": culture.pk,
        },
    )
    assert section_create_response.status_code == 302
    assert section_create_response.url == reverse(
        "wagtailsnippets_news_newssection:list"
    )
    assert NewsSection.objects.get(slug="seccion-creada").parent_id is None

    crafted_section_edit_response = admin_client.post(
        reverse(
            "wagtailsnippets_news_newssection:edit",
            args=(culture.pk,),
        ),
        {
            "name": culture.name,
            "slug": culture.slug,
            "sort_order": culture.sort_order,
            "parent": politics.pk,
        },
    )
    assert crafted_section_edit_response.status_code == 302
    culture.refresh_from_db()
    assert culture.parent_id is None

    missing_parent_response = admin_client.post(
        reverse("news_subsections:add"),
        {
            "name": "Subsección sin padre",
            "slug": "subseccion-sin-padre",
            "sort_order": 80,
        },
    )
    assert missing_parent_response.status_code == 200
    assert_contains_text(
        missing_parent_response,
        "Selecciona una sección principal.",
    )

    cleared_parent_response = admin_client.post(
        reverse("news_subsections:edit", args=(music.pk,)),
        {
            "name": music.name,
            "slug": music.slug,
            "sort_order": music.sort_order,
        },
    )
    assert cleared_parent_response.status_code == 200
    assert_contains_text(
        cleared_parent_response,
        "Selecciona una sección principal.",
    )
    music.refresh_from_db()
    assert music.parent == culture

    move_response = admin_client.post(
        reverse("news_subsections:edit", args=(music.pk,)),
        {
            "name": music.name,
            "slug": music.slug,
            "parent": politics.pk,
            "sort_order": music.sort_order,
        },
    )
    assert move_response.status_code == 302
    assert move_response.url == reverse("news_subsections:index")
    music.refresh_from_db()
    assert music.parent == politics


@pytest.mark.django_db
def test_taxonomy_cross_surface_object_urls_return_not_found(admin_client) -> None:
    culture = NewsSection.objects.get(slug="cultura")
    music = NewsSection.objects.get(slug="musica")

    assert (
        admin_client.get(
            reverse("wagtailsnippets_news_newssection:edit", args=(music.pk,))
        ).status_code
        == 404
    )
    assert (
        admin_client.get(
            reverse("wagtailsnippets_news_newssection:delete", args=(music.pk,))
        ).status_code
        == 404
    )
    assert (
        admin_client.get(
            reverse("news_subsections:edit", args=(culture.pk,))
        ).status_code
        == 404
    )
    assert (
        admin_client.get(
            reverse("news_subsections:delete", args=(culture.pk,))
        ).status_code
        == 404
    )
    for view_name in ("copy", "history", "usage"):
        assert (
            admin_client.get(
                reverse(
                    f"wagtailsnippets_news_newssection:{view_name}",
                    args=(music.pk,),
                )
            ).status_code
            == 404
        )
        assert (
            admin_client.get(
                reverse(f"news_subsections:{view_name}", args=(culture.pk,))
            ).status_code
            == 404
        )


@pytest.mark.django_db
def test_protected_taxonomy_delete_paths_redirect_with_spanish_error(
    admin_client,
) -> None:
    section = NewsSection.objects.get(slug="cultura")
    subsection = NewsSection.objects.get(slug="musica")
    home = HomePage.objects.first()
    if home is None:
        root = Page.get_first_root_node()
        home = HomePage(title="Inicio", slug="inicio-taxonomy-delete")
        root.add_child(instance=home)
    page = NewsPage(
        title="Taxonomy delete protection",
        slug="taxonomy-delete-protection",
        publication_date=dt.date(2026, 7, 31),
        body=[("paragraph", "<p>Contenido ficticio.</p>")],
        coverage_province="Arequipa",
    )
    home.add_child(instance=page)
    NewsPageSection.objects.create(page=page, section=subsection)
    expected_error = (
        "No puedes eliminar esta clasificación porque contiene subsecciones o "
        "está asociada a noticias."
    )

    individual_response = admin_client.get(
        reverse("wagtailsnippets_news_newssection:delete", args=(section.pk,)),
        follow=True,
    )
    bulk_response = admin_client.get(
        reverse(
            "wagtail_bulk_action",
            args=("news", "newssection", "delete"),
        ),
        {"id": [str(section.pk)]},
        follow=True,
    )
    subsection_response = admin_client.get(
        reverse("news_subsections:delete", args=(subsection.pk,)),
        follow=True,
    )
    crafted_bulk_response = admin_client.get(
        reverse(
            "wagtail_bulk_action",
            args=("news", "newssection", "delete"),
        ),
        {"id": [str(subsection.pk)]},
        follow=True,
    )

    assert individual_response.status_code == 200
    assert bulk_response.status_code == 200
    assert subsection_response.status_code == 200
    assert crafted_bulk_response.status_code == 200
    assert_contains_text(individual_response, expected_error)
    assert_contains_text(bulk_response, expected_error)
    assert_contains_text(subsection_response, expected_error)
    assert_contains_text(
        crafted_bulk_response,
        "La clasificación solicitada no está disponible en Secciones.",
    )
    assert NewsSection.objects.filter(pk=subsection.pk).exists()


@pytest.mark.django_db
def test_news_page_create_surface_contains_contributor_and_privacy_copy(
    admin_client,
):
    home = HomePage.objects.first()
    if home is None:
        root = Page.get_first_root_node()
        home = HomePage(title="Inicio", slug="inicio-news-admin")
        root.add_child(instance=home)

    response = admin_client.get(
        reverse(
            "wagtailadmin_pages:add",
            args=("news", "newspage", home.pk),
        ),
    )

    assert response.status_code == 200
    assert NewsPage._meta.verbose_name == "Noticia"
    assert_contains_text(response, "Firma pública")
    assert_contains_text(response, "Colaboradores internos")
    assert_contains_text(response, "Privacidad de menores")
    assert_contains_text(response, "Contiene menores identificables")
    assert_contains_text(
        response,
        "Confirmo que se verificaron las autorizaciones requeridas",
    )
    assert_contains_text(response, "Contenido sensible")
    assert_contains_text(response, "Edición de la noticia")
    assert_contains_text(response, "Abrir modo redacción")
    assert_contains_text(response, "Sin contenido")
    assert_contains_text(response, "Modo redacción")
    assert_contains_text(response, "Volver")
    assert_contains_text(response, "Volver a la edición de la noticia")
    assert_contains_text(response, "Secciones y subsecciones")
    assert_contains_text(
        response,
        (
            "Selecciona una o varias secciones o subsecciones. Puedes elegir una "
            "subsección sin seleccionar también su sección principal."
        ),
    )
    assert 'name="taxonomy_sections"' in response.content.decode()
    assert 'aria-label="Mostrar subsecciones de Cultura"' in response.content.decode()
    assert_contains_telepath_text(response, "Encabezados de tabla")
    assert_contains_telepath_text(
        response,
        "¿Qué celdas deben mostrarse como encabezados?",
    )
    assert_contains_telepath_text(response, "Descripción de la tabla")
    assert_contains_telepath_text(
        response,
        (
            "Un texto que identifica el tema general de la tabla y facilita "
            "su comprensión a quienes utilizan lectores de pantalla."
        ),
    )
    assert_contains_telepath_text(
        response,
        "Selecciona una opción de encabezado",
    )
    assert_contains_telepath_text(
        response,
        "Mostrar la primera fila como encabezado",
    )
    assert_contains_telepath_text(
        response,
        "Mostrar la primera columna como encabezado",
    )
    assert_contains_telepath_text(
        response,
        "Mostrar la primera fila y la primera columna como encabezados",
    )
    assert_contains_telepath_text(response, "Sin encabezados")
    assert_not_contains_text(response, "Pegar nota como bloques")
    assert_not_contains_text(response, "Revisar importación")
    assert_not_contains_text(response, "Insertar bloques")
    assert 'data-controller="w-dialog"' in response.content.decode()
    assert 'data-w-dialog-target="body"' in response.content.decode()
    assert 'class="w-dialog news-writing-dialog"' in response.content.decode()
    assert 'data-controller="w-teleport"' in response.content.decode()
    assert (
        'data-w-teleport-target-value="[data-edit-form]"' in response.content.decode()
    )
    assert_not_contains_text(response, "Vista de contenido")
    assert_not_contains_text(response, "Modo normal")
    assert 'name="summary"' not in response.content.decode()
    assert "news/js/writing_mode.js" in response.content.decode()
    assert "news/js/smart_paste.js" in response.content.decode()
    assert "news/css/writing_mode.css" in response.content.decode()
    assert "news/css/smart_paste.css" not in response.content.decode()
    assert_contains_text(response, "Reglamento de la Ley N.º 29733")
    assert_contains_text(
        response,
        'href="https://diariooficial.elperuano.pe/Normas/obtenerDocumento?idNorma=23"',
    )
    assert_contains_text(response, 'target="_blank"')
    assert_contains_text(response, 'rel="noopener noreferrer"')
    assert_not_contains_text(response, "Public credit")
    assert_not_contains_text(response, "Internal contributors")


@pytest.mark.django_db
def test_news_page_create_surface_transforms_promote_tab_into_seo_assistant(
    admin_client,
):
    home = HomePage.objects.first()
    if home is None:
        root = Page.get_first_root_node()
        home = HomePage(title="Inicio", slug="inicio-seo-admin")
        root.add_child(instance=home)

    response = admin_client.get(
        reverse(
            "wagtailadmin_pages:add",
            args=("news", "newspage", home.pk),
        ),
    )
    content = response.content.decode()
    visible_tabs = [
        label.strip()
        for label in re.findall(
            r'<a id="tab-label-[^"]+"[^>]*role="tab"[^>]*>\s*([^<]+)',
            content,
        )
    ]

    assert response.status_code == 200
    assert visible_tabs == ["Edición de la noticia", "Asistente SEO"]
    assert_contains_text(response, "Asistente SEO")
    assert_contains_text(response, "Configuración SEO")
    assert_contains_text(response, "Vista previa en buscador")
    assert_contains_text(response, "Vista previa social")
    assert_contains_text(response, "Análisis SEO")
    assert_contains_text(response, "Legibilidad")
    assert_contains_text(response, "Estado general")
    assert_contains_text(response, "Indexación y canonical")
    assert_contains_text(response, "Navegación y menús")
    assert_contains_text(response, "no afecta el análisis ni el estado SEO")
    assert "news/js/seo_assistant.js" in content
    assert "news/css/seo_assistant.css" in content
    assert content.count('name="slug"') == 1
    assert content.count('name="seo_title"') == 1
    assert content.count('name="search_description"') == 1
    assert content.count('name="show_in_menus"') == 1
    assert "Promocionar" not in content
    settings_panel = NewsPage.edit_handler.children[2]
    assert settings_panel.children == Page.settings_panels


@pytest.mark.django_db
def test_wagtail_account_preferences_use_spanish_admin_copy(admin_client):
    response = admin_client.get(reverse("wagtailadmin_account"))

    assert response.status_code == 200
    assert_contains_text(response, "Usar zona horaria del servidor")
    assert_contains_text(response, "Tema del administrador")
    assert_contains_text(response, "Predeterminado del sistema")
    assert_contains_text(response, "Contraste")
    assert_contains_text(response, "Densidad")
    assert_contains_text(response, "Atajos de teclado")
    assert_contains_text(
        response,
        "Activar atajos de teclado personalizados específicos de Wagtail.",
    )
    assert_not_contains_text(response, "Use server time zone")
    assert_not_contains_text(response, "Admin theme")
    assert_not_contains_text(response, "Keyboard shortcuts")


@pytest.mark.django_db
def test_wagtail_workflow_reports_use_spanish_observed_copy(admin_client):
    workflow_response = admin_client.get("/admin/reports/workflow/")
    task_response = admin_client.get("/admin/reports/workflow_tasks/")

    assert workflow_response.status_code == 200
    assert task_response.status_code == 200
    assert_contains_text(workflow_response, "Por tarea")
    assert_contains_text(
        workflow_response,
        "Aún no se han enviado páginas ni fragmentos para moderación",
    )
    assert_contains_text(task_response, "Por flujo de trabajo")
    assert_not_contains_text(workflow_response, "By task")
    assert_not_contains_text(workflow_response, "No pages/snippets")
    assert_not_contains_text(task_response, "By workflow")


@pytest.mark.django_db
def test_page_types_usage_uses_spanish_labels_and_homepage_type(admin_client):
    if not HomePage.objects.exists():
        root = Page.get_first_root_node()
        home = HomePage(title="Inicio", slug="inicio-reporte-tipos")
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

    response = admin_client.get("/admin/reports/page-types-usage/")

    assert response.status_code == 200
    assert HomePage._meta.verbose_name == "Página de inicio"
    assert_contains_text(response, "Uso de tipos de página")
    assert_contains_text(response, "Aplicación")
    assert_contains_text(response, "Última página editada")
    assert_contains_text(response, "Última edición")
    assert_contains_text(response, "Página De Inicio")
    assert_contains_text(response, "home.homepage")
    assert_not_contains_text(response, "Page types usage")
    assert_not_contains_text(response, "Home Page")
