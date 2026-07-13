import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.test import Client
from django.utils.translation import gettext, override
from wagtail.admin.localization import get_available_admin_languages
from wagtail.admin.panels import FieldPanel, HelpPanel, InlinePanel
from wagtail.models import Locale

from apps.news.models import (
    ContributorGroup,
    MinorContributor,
    NewsPage,
    NewsSection,
    School,
)


def test_primary_language_settings_are_spanish_only() -> None:
    assert settings.LANGUAGE_CODE == "es"
    assert settings.USE_I18N is True
    assert settings.LANGUAGES == [("es", "Español")]
    assert settings.WAGTAILADMIN_PERMITTED_LANGUAGES == [("es", "Español")]
    assert get_available_admin_languages() == [("es", "Español")]
    assert "en" not in dict(settings.WAGTAILADMIN_PERMITTED_LANGUAGES)
    assert settings.WAGTAIL_CONTENT_LANGUAGES == [("es", "Español")]
    assert not getattr(settings, "WAGTAIL_I18N_ENABLED", False)


def test_wagtail_page_validation_messages_are_spanish() -> None:
    with override("es"):
        assert (
            gettext("The page could not be saved due to validation errors.")
            == "No se pudo guardar la página debido a errores de validación."
        )
        assert gettext("Go to the first error") == "Ir al primer error"


@pytest.mark.django_db
def test_wagtail_default_content_locale_is_spanish() -> None:
    assert Locale.get_default().language_code == "es"
    assert list(Locale.all_objects.values_list("language_code", flat=True)) == ["es"]


@pytest.mark.django_db
def test_wagtail_admin_request_uses_spanish() -> None:
    user_model = get_user_model()
    user = user_model.objects.create_superuser(
        username="editor",
        email="editor@example.com",
        password="test-password",
    )
    client = Client()
    client.force_login(user)

    response = client.get("/admin/")

    assert response.status_code == 200
    assert b'<html lang="es"' in response.content


def test_custom_editor_visible_labels_are_spanish() -> None:
    assert NewsPage._meta.verbose_name == "Noticia"
    assert NewsPage._meta.verbose_name_plural == "Noticias"
    assert NewsSection._meta.verbose_name == "Sección editorial"
    assert NewsSection._meta.verbose_name_plural == "Secciones editoriales"
    assert School._meta.verbose_name == "Colegio"
    assert School._meta.verbose_name_plural == "Colegios"
    assert ContributorGroup._meta.verbose_name == "Grupo de colaboradores"
    assert ContributorGroup._meta.verbose_name_plural == "Grupos de colaboradores"
    assert MinorContributor._meta.verbose_name == "Colaborador menor"
    assert MinorContributor._meta.verbose_name_plural == "Colaboradores menores"

    assert NewsPage._meta.get_field("publication_date").verbose_name == (
        "Fecha de publicación"
    )
    assert NewsPage._meta.get_field("summary").verbose_name == "Resumen"
    assert NewsPage._meta.get_field("body").verbose_name == "Contenido"
    assert NewsPage._meta.get_field("section").verbose_name == "Sección"
    assert NewsPage._meta.get_field("school").verbose_name == "Colegio"
    assert NewsPage._meta.get_field("coverage_province").verbose_name == (
        "Provincia de cobertura"
    )
    assert NewsPage._meta.get_field("coverage_district").verbose_name == (
        "Distrito de cobertura"
    )
    assert NewsPage._meta.get_field("featured_image").verbose_name == (
        "Imagen destacada"
    )
    assert NewsPage._meta.get_field("focus_keyphrase").verbose_name == (
        "Frase clave objetivo"
    )
    assert NewsPage._meta.get_field("og_title").verbose_name == (
        "Título para redes sociales"
    )
    assert NewsPage._meta.get_field("og_description").verbose_name == (
        "Descripción para redes sociales"
    )
    assert NewsPage._meta.get_field("og_image").verbose_name == (
        "Imagen para redes sociales"
    )
    assert NewsPage._meta.get_field("canonical_url").verbose_name == "URL canonical"
    assert NewsPage._meta.get_field("seo_noindex").verbose_name == (
        "Excluir de los resultados de búsqueda"
    )
    assert NewsPage._meta.get_field("tags").verbose_name == "Etiquetas"
    assert NewsPage._meta.get_field("contains_identifiable_minors").verbose_name == (
        "Contiene menores identificables"
    )
    assert NewsPage._meta.get_field(
        "minor_publication_authorizations_verified",
    ).verbose_name == (
        "Confirmo que se verificaron las autorizaciones requeridas para "
        "exponer públicamente a los menores identificables de esta noticia"
    )
    assert NewsPage._meta.get_field("sensitive_content").verbose_name == (
        "Contenido sensible"
    )
    assert ContributorGroup._meta.get_field("name").verbose_name == "Nombre"
    assert ContributorGroup._meta.get_field("school").verbose_name == "Colegio"
    assert MinorContributor._meta.get_field("full_name").verbose_name == (
        "Nombre interno"
    )
    assert MinorContributor._meta.get_field("group").verbose_name == "Grupo"
    assert MinorContributor._meta.get_field("age_band").verbose_name == (
        "Franja de edad"
    )
    assert MinorContributor.AgeBand.choices == [
        ("under_14", "Menor de 14 años"),
        ("14_to_17", "De 14 a 17 años"),
    ]

    body = NewsPage._meta.get_field("body")
    assert body.stream_block.child_blocks["paragraph"].label == "Párrafo"
    assert body.stream_block.child_blocks["article_image"].label == "Imagen"
    assert body.stream_block.child_blocks["youtube"].label == "Video de YouTube"
    assert body.stream_block.child_blocks["spotify"].label == (
        "Audio o pódcast de Spotify"
    )


def test_news_admin_panels_explain_content_authoring_and_public_credit() -> None:
    body_panel_index = next(
        index
        for index, panel in enumerate(NewsPage.content_panels)
        if isinstance(panel, FieldPanel) and panel.field_name == "body"
    )
    content_help = NewsPage.content_panels[body_panel_index - 1]
    public_credit_panel = next(
        panel
        for panel in NewsPage.content_panels
        if isinstance(panel, InlinePanel) and panel.relation_name == "public_credits"
    )

    assert isinstance(content_help, HelpPanel)
    assert "Cómo editar el contenido" in content_help.content
    assert "Selecciona texto" in content_help.content
    assert 'Pulsa "/"' in content_help.content
    assert "tipo Markdown" in content_help.content
    assert "Draftail" not in content_help.content
    assert "StreamBlock" not in content_help.content
    assert public_credit_panel.help_text == (
        "Obligatoria para publicar. Puedes dejarla vacía mientras trabajas en un "
        "borrador."
    )


def test_tag_help_text_resolves_to_spanish() -> None:
    with override("es"):
        assert str(NewsPage._meta.get_field("tags").help_text) == (
            "Una lista de etiquetas separadas por coma."
        )


def test_error_templates_use_spanish_project_copy() -> None:
    not_found = render_to_string("404.html")
    server_error = render_to_string("500.html")

    assert '<html lang="es">' in not_found
    assert "Página no encontrada" in not_found
    assert "Page not found" not in not_found
    assert '<html lang="es">' in server_error
    assert "Error del servidor" in server_error
    assert "Server error" not in server_error
