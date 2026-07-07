import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from wagtail.models import Page, Site

from apps.home.models import HomePage


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


@pytest.mark.django_db
def test_wagtail_dashboard_uses_spanish_search_and_editorial_menu(admin_client):
    response = admin_client.get(reverse("wagtailadmin_home"))

    assert response.status_code == 200
    assert_contains_text(response, "Buscar en todas las páginas...")
    assert_contains_text(response, "Editorial")
    assert_contains_text(response, "Secciones editoriales")
    assert_contains_text(response, "Colegios")
    assert_not_contains_text(response, "Search all pages")


@pytest.mark.django_db
def test_editorial_snippet_destinations_are_available(admin_client):
    section_response = admin_client.get(
        reverse("wagtailsnippets_news_newssection:list"),
    )
    school_response = admin_client.get(reverse("wagtailsnippets_news_school:list"))

    assert section_response.status_code == 200
    assert school_response.status_code == 200
    assert_contains_text(section_response, "Secciones editoriales")
    assert_contains_text(school_response, "Colegios")


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
