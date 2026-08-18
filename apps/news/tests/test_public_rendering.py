import datetime as dt
import re

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import connection
from django.test import Client, RequestFactory
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from wagtail.embeds.exceptions import EmbedNotFoundException
from wagtail.images import get_image_model
from wagtail.models import Page, PageViewRestriction, Site
from wagtail.search.models import IndexEntry

from apps.home.models import HomePage
from apps.news.models import (
    AuthorProfile,
    ContributorGroup,
    MinorContributor,
    NewsPage,
    NewsPageAttribution,
    NewsPageSection,
    NewsSection,
    School,
)
from apps.news.smart_paste import normalize_paste

GIF_BYTES = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!"
    b"\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01"
    b"\x00\x00\x02\x02D\x01\x00;"
)


@pytest.fixture
def public_site():
    root = Page.get_first_root_node()
    home = HomePage(title="School Newsroom", slug="school-newsroom")
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


@pytest.fixture
def section():
    return NewsSection.objects.get(slug="politica")


def create_news_page(
    home_page,
    section,
    *,
    title,
    slug,
    publication_date,
    live=True,
    first_published_at=None,
    school=None,
    featured_image=None,
    featured_image_caption="",
    featured_image_alt_text="",
    featured_image_credit="",
    body=None,
    tags=None,
    coverage_department_id="04",
    coverage_district_id="040101",
):
    page = NewsPage(
        title=title,
        slug=slug,
        live=live,
        publication_date=publication_date,
        body=body
        or [
            (
                "paragraph",
                "<h2>Story background</h2><p>Detailed public body text.</p>",
            ),
        ],
        school=school,
        coverage_department_id=coverage_department_id,
        coverage_district_id=coverage_district_id,
        featured_image=featured_image,
        featured_image_caption=featured_image_caption,
        featured_image_alt_text=featured_image_alt_text,
        featured_image_credit=featured_image_credit,
    )
    home_page.add_child(instance=page)
    NewsPageSection.objects.create(page=page, section=section)
    if first_published_at is not None:
        Page.objects.filter(pk=page.pk).update(first_published_at=first_published_at)
        page.refresh_from_db()
    if tags:
        page.tags.add(*tags)
        page.save()
    return page


def create_uploaded_image():
    image_model = get_image_model()
    return image_model.objects.create(
        title="Imagen editorial genérica",
        description="Descripción significativa de imagen",
        file=SimpleUploadedFile(
            "featured.gif",
            GIF_BYTES,
            content_type="image/gif",
        ),
    )


@pytest.mark.django_db
def test_update_index_rebuilds_existing_public_news_search_content(
    public_site,
    section,
) -> None:
    page = create_news_page(
        public_site,
        section,
        title="Archivo reconstruido de festival",
        slug="archivo-reconstruido-de-festival",
        publication_date=dt.date(2026, 7, 1),
    )
    IndexEntry.objects.filter(object_id=page.pk).delete()

    call_command("update_index", backend_name="default", verbosity=0)

    assert page in NewsPage.objects.search("reconstruido", operator="or")


@pytest.mark.django_db
def test_home_renders_without_news(public_site) -> None:
    response = Client().get("/")

    assert response.status_code == 200
    assert "Aún no hay noticias publicadas.".encode() in response.content


@pytest.mark.django_db
def test_home_context_excludes_drafts_and_restricted_pages(
    public_site,
    section,
) -> None:
    draft = create_news_page(
        public_site,
        section,
        title="Draft News",
        slug="draft-news",
        publication_date=dt.date(2026, 7, 2),
        live=False,
    )
    live_page = create_news_page(
        public_site,
        section,
        title="Live News",
        slug="live-news",
        publication_date=dt.date(2026, 7, 1),
        live=True,
    )
    restricted_page = create_news_page(
        public_site,
        section,
        title="Restricted News",
        slug="restricted-news",
        publication_date=dt.date(2026, 7, 3),
        live=True,
    )
    PageViewRestriction.objects.create(
        page=restricted_page,
        restriction_type=PageViewRestriction.LOGIN,
    )
    request = RequestFactory().get("/")

    latest_news = list(public_site.get_context(request)["latest_news"])

    assert live_page in latest_news
    assert draft not in latest_news
    assert restricted_page not in latest_news


@pytest.mark.django_db
def test_home_limits_latest_news_to_12(public_site, section) -> None:
    for index in range(13):
        create_news_page(
            public_site,
            section,
            title=f"Live News {index}",
            slug=f"live-news-{index}",
            publication_date=dt.date(2026, 7, index + 1),
        )

    request = RequestFactory().get("/")
    latest_news = list(public_site.get_context(request)["latest_news"])

    assert len(latest_news) == 12
    assert latest_news[0].title == "Live News 12"
    assert latest_news[-1].title == "Live News 1"


@pytest.mark.django_db
def test_home_orders_by_publication_date_then_first_published_at(
    public_site,
    section,
) -> None:
    older_publication_date = create_news_page(
        public_site,
        section,
        title="Older Publication Date",
        slug="older-publication-date",
        publication_date=dt.date(2026, 7, 1),
        first_published_at=timezone.datetime(2026, 7, 1, 10, tzinfo=dt.UTC),
    )
    first_same_day = create_news_page(
        public_site,
        section,
        title="First Same Day",
        slug="first-same-day",
        publication_date=dt.date(2026, 7, 2),
        first_published_at=timezone.datetime(2026, 7, 1, 11, tzinfo=dt.UTC),
    )
    latest_same_day = create_news_page(
        public_site,
        section,
        title="Latest Same Day",
        slug="latest-same-day",
        publication_date=dt.date(2026, 7, 2),
        first_published_at=timezone.datetime(2026, 7, 1, 12, tzinfo=dt.UTC),
    )
    request = RequestFactory().get("/")

    assert list(public_site.get_context(request)["latest_news"]) == [
        latest_same_day,
        first_same_day,
        older_publication_date,
    ]


@pytest.mark.django_db
def test_home_renders_published_news_metadata(public_site, section) -> None:
    school = School.objects.create(
        name="Fictional School",
        department_id="04",
        district_id="040101",
    )
    create_news_page(
        public_site,
        section,
        title="Published News",
        slug="published-news",
        publication_date=dt.date(2026, 7, 1),
        school=school,
    )

    response = Client().get("/")

    assert response.status_code == 200
    assert b'<html lang="es">' in response.content
    assert b"\xc3\x9altimas noticias" in response.content
    assert b"Fecha de publicaci\xc3\xb3n" in response.content
    assert b"julio" in response.content
    assert b"July" not in response.content
    assert b"Secciones" in response.content
    assert b"Published News" in response.content
    assert b"Detailed public body text." not in response.content
    assert "Política".encode() in response.content
    assert b"Fictional School" in response.content
    assert b"Colegio" in response.content
    assert b"Cobertura" in response.content
    assert b"Arequipa" in response.content
    assert response.content.count(b"Arequipa") >= 2


@pytest.mark.django_db
def test_home_renders_public_credits_without_internal_contributor_data(
    public_site,
    section,
) -> None:
    school = School.objects.create(
        name="Fictional School",
        department_id="04",
        district_id="040101",
    )
    group = ContributorGroup.objects.create(
        name="Fictional Reporting Workshop",
        school=school,
    )
    contributor = MinorContributor.objects.create(
        full_name="Fictional Contributor One",
        group=group,
        age_band=MinorContributor.AgeBand.UNDER_14,
    )
    page = create_news_page(
        public_site,
        section,
        title="Public Credit News",
        slug="public-credit-news",
        publication_date=dt.date(2026, 7, 1),
    )
    NewsPageAttribution.objects.create(
        page=page,
        kind=NewsPageAttribution.Kind.INTERNAL_CONTRIBUTOR,
        minor_contributor=contributor,
    )
    NewsPageAttribution.objects.create(
        page=page,
        kind=NewsPageAttribution.Kind.PUBLIC_CREDIT,
        display_name="Second fictional public credit",
        sort_order=2,
    )
    NewsPageAttribution.objects.create(
        page=page,
        kind=NewsPageAttribution.Kind.PUBLIC_CREDIT,
        display_name="First fictional public credit",
        sort_order=1,
    )

    response = Client().get("/")
    content = response.content.decode()

    assert response.status_code == 200
    assert content.index("First fictional public credit") < content.index(
        "Second fictional public credit",
    )
    assert "Fictional Contributor One" not in content
    assert "under_14" not in content
    assert "contains_identifiable_minors" not in content
    assert "minor_publication_authorizations_verified" not in content
    assert "sensitive_content" not in content


@pytest.mark.django_db
def test_news_detail_renders_required_content(public_site, section) -> None:
    school = School.objects.create(
        name="Fictional School",
        department_id="04",
        district_id="040101",
    )
    page = create_news_page(
        public_site,
        section,
        title="Detail News",
        slug="detail-news",
        publication_date=dt.date(2026, 7, 1),
        school=school,
        tags=["student-reporting", "local-news"],
    )

    response = Client().get(page.url)

    assert response.status_code == 200
    assert b'<html lang="es">' in response.content
    assert b"<article" in response.content
    assert b"Detail News" in response.content
    assert b"Fecha de publicaci\xc3\xb3n" in response.content
    assert b"julio" in response.content
    assert b"July" not in response.content
    assert b"Secciones" in response.content
    assert b"Fictional School" in response.content
    assert b"Colegio" in response.content
    assert b"Cobertura" in response.content
    assert b"<h2>Story background</h2>" in response.content
    assert b"Detailed public body text." in response.content
    assert b"Etiquetas" in response.content
    assert b"student-reporting" in response.content
    assert b"local-news" in response.content
    assert b"/noticias/?etiqueta=student-reporting" in response.content
    assert b'/noticias/?departamento=04"' in response.content
    assert b"/noticias/?departamento=04&amp;distrito=040101" in response.content
    assert b'/noticias/?seccion=politica"' in response.content


@pytest.mark.django_db
def test_news_detail_renders_explicit_taxonomy_paths_without_parent_duplication(
    public_site,
    section,
) -> None:
    page = create_news_page(
        public_site,
        section,
        title="Taxonomy detail news",
        slug="taxonomy-detail-news",
        publication_date=dt.date(2026, 7, 1),
    )
    culture = NewsSection.objects.get(slug="cultura")
    music = NewsSection.objects.get(slug="musica")
    interviews = NewsSection.objects.get(slug="entrevistas")
    community = NewsSection.objects.get(slug="comunidad")
    page.section_assignments.set(
        [
            NewsPageSection(page=page, section=culture),
            NewsPageSection(page=page, section=music),
            NewsPageSection(page=page, section=interviews),
            NewsPageSection(page=page, section=community),
        ]
    )
    page.save()

    content = Client().get(page.url).content.decode()

    assert (
        '<p class="eyebrow"><a href="/noticias/?seccion=cultura">Cultura</a>' in content
    )
    assert (
        '› <a href="/noticias/?seccion=cultura&amp;subseccion=musica">Música</a>'
        in content
    )
    assert '<a href="/noticias/?seccion=entrevistas">Entrevistas</a>' in content
    assert (
        '› <a href="/noticias/?seccion=entrevistas&amp;subseccion=comunidad">'
        "Comunidad</a>" in content
    )
    assert "<dt>Secciones y subsecciones</dt>" not in content
    assert "Cultura; Cultura › Música" not in content
    assert "Entrevistas; Entrevistas › Comunidad" not in content


@pytest.mark.django_db
def test_news_detail_renders_normalized_paste_and_accessible_table(
    public_site,
    section,
) -> None:
    normalized = normalize_paste(
        html_source=(
            "<h1>Contexto importado</h1>"
            "<p>Texto <strong>normalizado</strong>.</p>"
            "<table><caption>Resultados del taller</caption>"
            "<thead><tr><th>Zona</th><th>Total</th></tr></thead>"
            "<tbody><tr><th scope='row'>Norte</th><td>4</td></tr></tbody>"
            "</table>"
        ),
    )
    page = create_news_page(
        public_site,
        section,
        title="Noticia importada",
        slug="noticia-importada",
        publication_date=dt.date(2026, 7, 28),
        body=[(block.block_type, block.value) for block in normalized.blocks],
    )

    response = Client().get(page.url)
    content = response.content.decode()

    assert response.status_code == 200
    assert "<h2>Contexto importado</h2>" in content
    assert "<strong>normalizado</strong>" in content
    assert '<div class="w-block-table block-table">' in content
    assert "<caption>Resultados del taller</caption>" in content
    assert "<thead>" in content
    assert 'scope="col"' in content
    assert 'scope="row"' in content
    assert "<td" in content
    assert "alert(" not in content
    assert 'name="summary"' not in content
    assert '<meta name="description"' not in content


@pytest.mark.django_db
def test_news_detail_renders_public_credits_without_internal_privacy_data(
    public_site,
    section,
) -> None:
    school = School.objects.create(
        name="Fictional School",
        department_id="04",
        district_id="040101",
    )
    group = ContributorGroup.objects.create(
        name="Fictional Reporting Workshop",
        school=school,
    )
    contributor = MinorContributor.objects.create(
        full_name="Fictional Contributor Two",
        group=group,
        age_band=MinorContributor.AgeBand.FROM_14_TO_17,
    )
    page = create_news_page(
        public_site,
        section,
        title="Detail Public Credit News",
        slug="detail-public-credit-news",
        publication_date=dt.date(2026, 7, 1),
    )
    page.contains_identifiable_minors = True
    page.minor_publication_authorizations_verified = True
    page.sensitive_content = True
    page.save()
    NewsPageAttribution.objects.create(
        page=page,
        kind=NewsPageAttribution.Kind.INTERNAL_CONTRIBUTOR,
        minor_contributor=contributor,
    )
    NewsPageAttribution.objects.create(
        page=page,
        kind=NewsPageAttribution.Kind.PUBLIC_CREDIT,
        display_name="Second fictional detail credit",
        sort_order=2,
    )
    NewsPageAttribution.objects.create(
        page=page,
        kind=NewsPageAttribution.Kind.PUBLIC_CREDIT,
        display_name="First fictional detail credit",
        sort_order=1,
    )

    response = Client().get(page.url)
    content = response.content.decode()

    assert response.status_code == 200
    assert content.index("First fictional detail credit") < content.index(
        "Second fictional detail credit",
    )
    assert "Fictional Contributor Two" not in content
    assert "14_to_17" not in content
    assert "contains_identifiable_minors" not in content
    assert "minor_publication_authorizations_verified" not in content
    assert "sensitive_content" not in content


@pytest.mark.django_db
def test_news_detail_renders_without_optional_metadata(public_site, section) -> None:
    page = create_news_page(
        public_site,
        section,
        title="No Optional Metadata",
        slug="no-optional-metadata",
        publication_date=dt.date(2026, 7, 1),
    )

    response = Client().get(page.url)

    assert response.status_code == 200
    assert b"No Optional Metadata" in response.content
    assert b"Colegio" not in response.content
    assert b"Etiquetas" not in response.content


@pytest.mark.django_db
def test_historical_featured_image_does_not_use_global_asset_metadata(
    public_site,
    section,
    settings,
    tmp_path,
) -> None:
    settings.MEDIA_ROOT = tmp_path
    image = create_uploaded_image()
    page = create_news_page(
        public_site,
        section,
        title="Image News",
        slug="image-news",
        publication_date=dt.date(2026, 7, 1),
        featured_image=image,
    )

    response = Client().get(page.url)

    assert response.status_code == 200
    assert b"<img" in response.content
    assert b'alt=""' in response.content
    assert "Descripción significativa de imagen".encode() not in response.content
    assert b"<figcaption>" not in response.content


@pytest.mark.django_db
def test_news_detail_renders_contextual_featured_image_metadata(
    public_site,
    section,
    settings,
    tmp_path,
) -> None:
    settings.MEDIA_ROOT = tmp_path
    image = create_uploaded_image()
    page = create_news_page(
        public_site,
        section,
        title="Contextual Featured Image News",
        slug="contextual-featured-image-news",
        publication_date=dt.date(2026, 7, 1),
        featured_image=image,
        featured_image_caption="Taller ficticio preparando una noticia.",
        featured_image_alt_text="Cuadernos y grabadoras sobre una mesa.",
        featured_image_credit="Archivo escolar ficticio",
    )

    response = Client().get(page.url)
    content = response.content.decode()

    assert response.status_code == 200
    assert 'alt="Cuadernos y grabadoras sobre una mesa."' in content
    assert "Taller ficticio preparando una noticia." in content
    assert "Crédito: Archivo escolar ficticio" in content
    assert "Descripción significativa de imagen" not in content


@pytest.mark.django_db
def test_home_and_news_list_use_contextual_featured_alt_without_visible_caption(
    public_site,
    section,
    settings,
    tmp_path,
) -> None:
    settings.MEDIA_ROOT = tmp_path
    image = create_uploaded_image()
    create_news_page(
        public_site,
        section,
        title="Contextual Card Image News",
        slug="contextual-card-image-news",
        publication_date=dt.date(2026, 7, 1),
        featured_image=image,
        featured_image_caption="Pie visible sólo en el detalle.",
        featured_image_alt_text="Mesa de redacción escolar ficticia.",
    )

    for url in ["/", "/noticias/"]:
        content = Client().get(url).content.decode()
        assert 'alt="Mesa de redacción escolar ficticia."' in content
        assert "Pie visible sólo en el detalle." not in content
        assert "Detailed public body text." not in content


@pytest.mark.django_db
def test_news_detail_renders_article_image_semantically(
    public_site,
    section,
    settings,
    tmp_path,
) -> None:
    settings.MEDIA_ROOT = tmp_path
    image = create_uploaded_image()
    page = create_news_page(
        public_site,
        section,
        title="Article Image News",
        slug="article-image-news",
        publication_date=dt.date(2026, 7, 1),
        body=[
            ("paragraph", "<h2>Preparación</h2><p>Antes de la imagen.</p>"),
            (
                "article_image",
                {
                    "image": image,
                    "caption": "Estudiantes ficticios preparan una entrevista.",
                    "alt_text": "Mesa con materiales de entrevista escolar.",
                    "credit": "Archivo escolar ficticio",
                },
            ),
            ("paragraph", "<p>Después de la imagen.</p>"),
        ],
    )

    response = Client().get(page.url)
    content = response.content.decode()

    assert response.status_code == 200
    assert "<figure>" in content
    assert 'alt="Mesa con materiales de entrevista escolar."' in content
    assert "Estudiantes ficticios preparan una entrevista." in content
    assert "Crédito: Archivo escolar ficticio" in content
    assert "Mesa con materiales de entrevista escolar.</figcaption>" not in content
    assert "<h2>Preparación</h2>" in content
    assert content.index("Antes de la imagen.") < content.index("<figure>")
    assert content.index("<figure>") < content.index("Después de la imagen.")


@pytest.mark.django_db
def test_news_detail_omits_article_image_credit_when_blank(
    public_site,
    section,
    settings,
    tmp_path,
) -> None:
    settings.MEDIA_ROOT = tmp_path
    image = create_uploaded_image()
    page = create_news_page(
        public_site,
        section,
        title="Article Image Without Credit",
        slug="article-image-without-credit",
        publication_date=dt.date(2026, 7, 1),
        body=[
            (
                "article_image",
                {
                    "image": image,
                    "caption": "Imagen genérica de trabajo editorial.",
                    "alt_text": "Cuaderno y grabadora sobre una mesa.",
                    "credit": "",
                },
            ),
        ],
    )

    response = Client().get(page.url)
    content = response.content.decode()

    assert response.status_code == 200
    assert "Imagen genérica de trabajo editorial." in content
    assert "Crédito:" not in content


@pytest.mark.django_db
def test_news_detail_youtube_fallback_preserves_original_url(
    public_site,
    section,
    monkeypatch,
) -> None:
    original_url = "https://www.youtube.com/watch?v=fictionalVideo01"

    def fail_embed_lookup(url, max_width=None, max_height=None):
        raise EmbedNotFoundException("controlled test failure")

    monkeypatch.setattr("wagtail.embeds.embeds.get_embed", fail_embed_lookup)
    page = create_news_page(
        public_site,
        section,
        title="YouTube Fallback News",
        slug="youtube-fallback-news",
        publication_date=dt.date(2026, 7, 1),
        body=[("youtube", original_url)],
    )

    response = Client().get(page.url)
    content = response.content.decode()

    assert response.status_code == 200
    assert "Ver contenido en YouTube" in content
    assert f'href="{original_url}"' in content


@pytest.mark.django_db
def test_news_detail_spotify_fallback_preserves_original_url(
    public_site,
    section,
    monkeypatch,
) -> None:
    original_url = "https://open.spotify.com/episode/fictionalEpisode01"

    def fail_embed_lookup(url, max_width=None, max_height=None):
        raise EmbedNotFoundException("controlled test failure")

    monkeypatch.setattr("wagtail.embeds.embeds.get_embed", fail_embed_lookup)
    page = create_news_page(
        public_site,
        section,
        title="Spotify Fallback News",
        slug="spotify-fallback-news",
        publication_date=dt.date(2026, 7, 1),
        body=[("spotify", original_url)],
    )

    response = Client().get(page.url)
    content = response.content.decode()

    assert response.status_code == 200
    assert "Escuchar en Spotify" in content
    assert f'href="{original_url}"' in content


@pytest.mark.django_db
def test_home_thumbnail_uses_decorative_empty_alt(
    public_site,
    section,
    settings,
    tmp_path,
) -> None:
    settings.MEDIA_ROOT = tmp_path
    image = create_uploaded_image()
    create_news_page(
        public_site,
        section,
        title="Thumbnail News",
        slug="thumbnail-news",
        publication_date=dt.date(2026, 7, 1),
        featured_image=image,
    )

    response = Client().get("/")

    assert response.status_code == 200
    assert b"<img" in response.content
    assert b'alt=""' in response.content


@pytest.mark.django_db
def test_home_separates_featured_story_from_secondary_stories(
    public_site,
    section,
) -> None:
    older = create_news_page(
        public_site,
        section,
        title="Older secondary story",
        slug="older-secondary-story",
        publication_date=dt.date(2026, 7, 1),
    )
    featured = create_news_page(
        public_site,
        section,
        title="Newest featured story",
        slug="newest-featured-story",
        publication_date=dt.date(2026, 7, 2),
    )

    context = public_site.get_context(RequestFactory().get("/"))

    assert context["featured_news"] == featured
    assert context["secondary_news"] == [older]
    assert featured not in context["secondary_news"]


@pytest.mark.django_db
def test_news_list_without_filter_uses_editorial_order(
    public_site,
    section,
) -> None:
    create_news_page(
        public_site,
        section,
        title="Older listed story",
        slug="older-listed-story",
        publication_date=dt.date(2026, 7, 1),
    )
    create_news_page(
        public_site,
        section,
        title="Newest listed story",
        slug="newest-listed-story",
        publication_date=dt.date(2026, 7, 2),
    )

    response = Client().get("/noticias/")
    content = response.content.decode()

    assert response.status_code == 200
    assert content.index("Newest listed story") < content.index("Older listed story")
    assert "Detailed public body text." not in content


@pytest.mark.django_db
def test_news_list_filters_coverage_department_and_exact_district(
    public_site,
    section,
) -> None:
    department_only = create_news_page(
        public_site,
        section,
        title="Cobertura Arequipa departamental",
        slug="cobertura-arequipa-departamental",
        publication_date=dt.date(2026, 7, 3),
        coverage_district_id=None,
    )
    district_coverage = create_news_page(
        public_site,
        section,
        title="Cobertura distrito Arequipa",
        slug="cobertura-distrito-arequipa",
        publication_date=dt.date(2026, 7, 2),
    )
    lima_coverage = create_news_page(
        public_site,
        section,
        title="Cobertura distrito Lima",
        slug="cobertura-distrito-lima",
        publication_date=dt.date(2026, 7, 1),
        coverage_department_id="15",
        coverage_district_id="150101",
    )

    department_content = (
        Client().get("/noticias/", {"departamento": "04"}).content.decode()
    )
    district_content = (
        Client()
        .get("/noticias/", {"departamento": "04", "distrito": "040101"})
        .content.decode()
    )

    assert department_only.title in department_content
    assert district_coverage.title in department_content
    assert lima_coverage.title not in department_content
    assert district_coverage.title in district_content
    assert department_only.title not in district_content
    assert lima_coverage.title not in district_content


@pytest.mark.django_db
def test_news_list_rejects_invalid_or_incompatible_geography(
    public_site,
    section,
) -> None:
    create_news_page(
        public_site,
        section,
        title="Geography validation story",
        slug="geography-validation-story",
        publication_date=dt.date(2026, 7, 1),
    )

    invalid_department = (
        Client().get("/noticias/", {"departamento": "99"}).content.decode()
    )
    invalid_district = (
        Client()
        .get("/noticias/", {"departamento": "04", "distrito": "999999"})
        .content.decode()
    )
    incompatible = (
        Client()
        .get("/noticias/", {"departamento": "04", "distrito": "150101"})
        .content.decode()
    )

    assert "El departamento solicitado no existe." in invalid_department
    assert "El distrito solicitado no existe." in invalid_district
    assert "Los filtros solicitados no son compatibles." in incompatible


@pytest.mark.django_db
def test_geography_combines_with_taxonomy_tag_order_and_pagination(
    public_site,
) -> None:
    music = NewsSection.objects.get(slug="musica")
    for index in range(11):
        create_news_page(
            public_site,
            music,
            title=f"Archivo territorial {index}",
            slug=f"archivo-territorial-{index}",
            publication_date=dt.date(2026, 7, index + 1),
            tags=["territorio"],
        )
    create_news_page(
        public_site,
        music,
        title="Archivo territorial fuera de cobertura",
        slug="archivo-territorial-fuera-de-cobertura",
        publication_date=dt.date(2026, 6, 1),
        tags=["territorio"],
        coverage_department_id="15",
        coverage_district_id="150101",
    )

    response = Client().get(
        "/noticias/",
        {
            "buscar": "territorial",
            "seccion": "cultura",
            "subseccion": "musica",
            "etiqueta": "territorio",
            "departamento": "04",
            "distrito": "040101",
            "orden": "asc",
        },
    )
    content = response.content.decode()

    assert response.status_code == 200
    assert content.count('class="card news-card') == 10
    assert "fuera de cobertura" not in content
    assert "departamento=04" in content
    assert "distrito=040101" in content
    assert "pagina=2" in content


@pytest.mark.django_db
def test_archive_initial_html_does_not_enumerate_all_districts(public_site) -> None:
    content = Client().get("/noticias/").content.decode()

    assert "data-dependent-district" in content
    assert 'data-lookup-url="/geografia/distritos/"' in content
    assert "Chachapoyas" not in content


@pytest.mark.django_db
def test_news_list_filters_by_matching_real_section(public_site, section) -> None:
    other_section = NewsSection.objects.create(
        name="Sección ficticia",
        slug="seccion-ficticia",
    )
    create_news_page(
        public_site,
        section,
        title="Matching section story",
        slug="matching-section-story",
        publication_date=dt.date(2026, 7, 2),
    )
    create_news_page(
        public_site,
        other_section,
        title="Other section story",
        slug="other-section-story",
        publication_date=dt.date(2026, 7, 1),
    )

    response = Client().get("/noticias/", {"seccion": section.slug})
    content = response.content.decode()

    assert response.status_code == 200
    assert f"Noticias de {section.name}" in content
    assert "Matching section story" in content
    assert "Other section story" not in content


@pytest.mark.django_db
def test_main_section_filter_includes_descendants_without_duplicates(
    public_site,
) -> None:
    culture = NewsSection.objects.get(slug="cultura")
    music = NewsSection.objects.get(slug="musica")
    traditions = NewsSection.objects.get(slug="tradiciones")
    page = create_news_page(
        public_site,
        music,
        title="Descendant filter story",
        slug="descendant-filter-story",
        publication_date=dt.date(2026, 7, 2),
    )
    NewsPageSection.objects.create(page=page, section=traditions)

    response = Client().get("/noticias/", {"seccion": culture.slug})
    content = response.content.decode()

    assert response.status_code == 200
    assert content.count("Descendant filter story") == 1


@pytest.mark.django_db
def test_news_list_supports_standalone_subsection_filter(public_site) -> None:
    music = NewsSection.objects.get(slug="musica")
    page = create_news_page(
        public_site,
        music,
        title="Standalone subsection archive story",
        slug="standalone-subsection-archive-story",
        publication_date=dt.date(2026, 7, 1),
    )

    response = Client().get("/noticias/", {"subseccion": music.slug})

    assert response.status_code == 200
    assert page.title in response.content.decode()


@pytest.mark.django_db
def test_news_list_groups_subsections_by_parent_with_plain_option_labels(
    public_site,
) -> None:
    content = Client().get("/noticias/").content.decode()

    assert '<optgroup label="Cultura" data-parent-section="cultura">' in content
    assert (
        '<option value="musica" data-parent-section="cultura">Música</option>'
        in content
    )
    assert "Cultura › Música" not in content


@pytest.mark.django_db
def test_news_list_keeps_forced_incompatible_section_subsection_error(
    public_site,
) -> None:
    response = Client().get(
        "/noticias/",
        {"seccion": "cultura", "subseccion": "politica-local"},
    )

    assert response.status_code == 200
    assert "Los filtros solicitados no son compatibles." in response.content.decode()


@pytest.mark.django_db
def test_news_list_supports_chronological_ordering_and_safe_invalid_order(
    public_site,
    section,
) -> None:
    create_news_page(
        public_site,
        section,
        title="Older archive story",
        slug="older-archive-story",
        publication_date=dt.date(2026, 7, 1),
    )
    create_news_page(
        public_site,
        section,
        title="Newest archive story",
        slug="newest-archive-story",
        publication_date=dt.date(2026, 7, 2),
    )

    ascending = Client().get("/noticias/", {"orden": "asc"}).content.decode()
    descending = Client().get("/noticias/", {"orden": "desc"}).content.decode()
    invalid = Client().get("/noticias/", {"orden": "unexpected"}).content.decode()

    assert ascending.index("Older archive story") < ascending.index(
        "Newest archive story"
    )
    assert descending.index("Newest archive story") < descending.index(
        "Older archive story"
    )
    assert invalid.index("Newest archive story") < invalid.index("Older archive story")
    assert "orden=asc" in descending


@pytest.mark.django_db
def test_news_list_filters_exact_subsection_tag_and_combinations(public_site) -> None:
    culture = NewsSection.objects.get(slug="cultura")
    music = NewsSection.objects.get(slug="musica")
    matching = create_news_page(
        public_site,
        music,
        title="Matching archive combination",
        slug="matching-archive-combination",
        publication_date=dt.date(2026, 7, 2),
        tags=["podcast"],
    )
    create_news_page(
        public_site,
        music,
        title="Wrong tag archive combination",
        slug="wrong-tag-archive-combination",
        publication_date=dt.date(2026, 7, 1),
        tags=["entrevista"],
    )

    response = Client().get(
        "/noticias/",
        {
            "buscar": "matching",
            "seccion": culture.slug,
            "subseccion": music.slug,
            "etiqueta": "podcast",
        },
    )
    content = response.content.decode()

    assert matching.title in content
    assert "Wrong tag archive combination" not in content


@pytest.mark.django_db
def test_news_list_paginates_ten_items_and_preserves_active_criteria(
    public_site,
    section,
) -> None:
    for index in range(11):
        create_news_page(
            public_site,
            section,
            title=f"Pagination archive story {index}",
            slug=f"pagination-archive-story-{index}",
            publication_date=dt.date(2026, 7, index + 1),
            tags=["archivo"],
        )

    first = Client().get("/noticias/", {"etiqueta": "archivo"}).content.decode()
    second = (
        Client()
        .get("/noticias/", {"etiqueta": "archivo", "pagina": "2"})
        .content.decode()
    )

    assert first.count('class="card news-card') == 10
    assert "etiqueta=archivo&amp;pagina=2" in first
    assert second.count('class="card news-card') == 1
    assert "Pagination archive story 0" in second


@pytest.mark.django_db
def test_news_list_uses_fts_then_native_fuzzy_fallback(public_site, section) -> None:
    title_match = create_news_page(
        public_site,
        section,
        title="Festival de educación",
        slug="festival-educacion",
        publication_date=dt.date(2026, 7, 3),
        tags=["radioescolar"],
    )
    body_match = create_news_page(
        public_site,
        section,
        title="Crónica del aula",
        slug="cronica-aula",
        publication_date=dt.date(2026, 7, 2),
        body=[("paragraph", "<p>Festival de ciencia escolar.</p>")],
    )
    tag_match = create_news_page(
        public_site,
        section,
        title="Otra crónica",
        slug="otra-cronica",
        publication_date=dt.date(2026, 7, 1),
        tags=["festival"],
    )

    fts = Client().get("/noticias/", {"buscar": "festival"}).content.decode()
    accentless = Client().get("/noticias/", {"buscar": "educacion"}).content.decode()
    fuzzy_title = Client().get("/noticias/", {"buscar": "festivla"}).content.decode()
    fuzzy_tag = Client().get("/noticias/", {"buscar": "radioescoalr"}).content.decode()
    negative = (
        Client().get("/noticias/", {"buscar": "xilofonoimprobable"}).content.decode()
    )

    assert (
        fts.index(title_match.title)
        < fts.index(tag_match.title)
        < fts.index(body_match.title)
    )
    assert title_match.title in accentless
    assert title_match.title in fuzzy_title
    assert title_match.title in fuzzy_tag
    assert "No encontramos noticias" in negative


@pytest.mark.django_db
def test_search_order_override_keeps_matching_but_uses_chronology(
    public_site,
    section,
) -> None:
    older = create_news_page(
        public_site,
        section,
        title="Festival antiguo",
        slug="festival-antiguo",
        publication_date=dt.date(2026, 7, 1),
    )
    newer = create_news_page(
        public_site,
        section,
        title="Festival nuevo",
        slug="festival-nuevo",
        publication_date=dt.date(2026, 7, 2),
    )

    response = Client().get("/noticias/", {"buscar": "festival", "orden": "asc"})
    content = response.content.decode()

    assert content.index(older.title) < content.index(newer.title)
    assert '<meta name="robots" content="noindex, follow">' in content


@pytest.mark.django_db
def test_news_list_taxonomy_queries_have_constant_growth(public_site, section) -> None:
    client = Client()
    create_news_page(
        public_site,
        section,
        title="Query budget story 0",
        slug="query-budget-story-0",
        publication_date=dt.date(2026, 7, 1),
    )
    client.get("/noticias/")
    with CaptureQueriesContext(connection) as one_page_queries:
        response = client.get("/noticias/")
    assert response.status_code == 200

    for index in range(1, 6):
        page = create_news_page(
            public_site,
            section,
            title=f"Query budget story {index}",
            slug=f"query-budget-story-{index}",
            publication_date=dt.date(2026, 7, index + 1),
        )
        NewsPageSection.objects.create(
            page=page,
            section=NewsSection.objects.get(slug="politica-local"),
        )

    with CaptureQueriesContext(connection) as six_page_queries:
        response = client.get("/noticias/")

    assert response.status_code == 200
    assert len(six_page_queries) == len(one_page_queries)


@pytest.mark.django_db
def test_public_author_attribution_queries_have_constant_growth(
    public_site,
    section,
) -> None:
    image = create_uploaded_image()
    first_page = create_news_page(
        public_site,
        section,
        title="One author query budget",
        slug="one-author-query-budget",
        publication_date=dt.date(2026, 7, 1),
    )
    first_profile = AuthorProfile.objects.create(
        display_name="First query author",
        slug="first-query-author",
        photo=image,
    )
    NewsPageAttribution.objects.create(
        page=first_page,
        kind=NewsPageAttribution.Kind.AUTHOR,
        author_profile=first_profile,
    )
    client = Client()
    client.get(first_page.url)
    with CaptureQueriesContext(connection) as one_author_detail_queries:
        detail_response = client.get(first_page.url)
    with CaptureQueriesContext(connection) as one_author_archive_queries:
        archive_response = client.get("/noticias/")
    assert detail_response.status_code == 200
    assert archive_response.status_code == 200

    for index in range(1, 4):
        profile = AuthorProfile.objects.create(
            display_name=f"Query author {index}",
            slug=f"query-author-{index}",
            photo=image,
        )
        NewsPageAttribution.objects.create(
            page=first_page,
            kind=NewsPageAttribution.Kind.AUTHOR,
            author_profile=profile,
            sort_order=index,
        )
    for index in range(1, 4):
        page = create_news_page(
            public_site,
            section,
            title=f"Archive author query budget {index}",
            slug=f"archive-author-query-budget-{index}",
            publication_date=dt.date(2026, 7, index + 1),
        )
        NewsPageAttribution.objects.create(
            page=page,
            kind=NewsPageAttribution.Kind.AUTHOR,
            author_profile=AuthorProfile.objects.create(
                display_name=f"Archive query author {index}",
                slug=f"archive-query-author-{index}",
                photo=image,
            ),
        )
    with CaptureQueriesContext(connection) as many_author_detail_queries:
        detail_response = client.get(first_page.url)
    with CaptureQueriesContext(connection) as many_author_archive_queries:
        archive_response = client.get("/noticias/")

    assert detail_response.status_code == 200
    assert archive_response.status_code == 200
    assert len(many_author_detail_queries) == len(one_author_detail_queries)
    assert len(many_author_archive_queries) == len(one_author_archive_queries)


@pytest.mark.django_db
def test_public_author_cards_and_structured_archive_filter_are_privacy_safe(
    public_site,
    section,
) -> None:
    profile = AuthorProfile.objects.create(
        display_name="Autora pública ficticia",
        slug="autora-publica-ficticia",
        bio="Biografía pública ficticia.",
        position="Periodista",
        work_url="https://example.invalid/portafolio",
    )
    authored = create_news_page(
        public_site,
        section,
        title="Noticia de autora pública",
        slug="noticia-de-autora-publica",
        publication_date=dt.date(2026, 7, 1),
    )
    other = create_news_page(
        public_site,
        section,
        title="Noticia de otra firma",
        slug="noticia-de-otra-firma",
        publication_date=dt.date(2026, 7, 2),
    )
    NewsPageAttribution.objects.create(
        page=authored,
        kind=NewsPageAttribution.Kind.AUTHOR,
        author_profile=profile,
        sort_order=0,
    )
    NewsPageAttribution.objects.create(
        page=authored,
        kind=NewsPageAttribution.Kind.PUBLIC_CREDIT,
        display_name="Redacción ficticia",
        sort_order=1,
    )
    NewsPageAttribution.objects.create(
        page=other,
        kind=NewsPageAttribution.Kind.PUBLIC_CREDIT,
        display_name="Otra firma ficticia",
    )
    profile.is_active = False
    profile.save(update_fields=["is_active"])

    detail = Client().get(authored.url).content.decode()
    archive = Client().get("/noticias/", {"autor": profile.slug}).content.decode()
    invalid = Client().get("/noticias/", {"autor": "no-existe"}).content.decode()

    assert detail.index("Autora pública ficticia") < detail.index("Redacción ficticia")
    assert detail.index("Biografía pública ficticia.") < detail.index(
        "Compartir esta noticia"
    )
    assert 'href="/noticias/?autor=autora-publica-ficticia"' in detail
    assert "Noticias de Autora pública ficticia" in archive
    assert authored.title in archive
    assert other.title not in archive
    assert 'for="news-author"' not in archive
    assert "La autora solicitada no existe." not in invalid
    assert "El autor solicitado no existe." in invalid


@pytest.mark.django_db
def test_author_archive_criterion_intersects_and_preserves_all_public_filters(
    public_site,
    section,
) -> None:
    """The structured author criterion composes without changing public search."""
    subsection = NewsSection.objects.get(slug="politica-local")
    profile = AuthorProfile.objects.create(
        display_name="Autora histórica de matriz",
        slug="autora-historica-matriz",
    )
    for index in range(11):
        page = create_news_page(
            public_site,
            section,
            title=f"Festival de archivo con autora {index}",
            slug=f"matriz-autora-archivada-{index}",
            publication_date=dt.date(2026, 7, index + 1),
            tags=["matriz-autora"],
        )
        NewsPageSection.objects.create(page=page, section=subsection)
        NewsPageAttribution.objects.create(
            page=page,
            kind=NewsPageAttribution.Kind.AUTHOR,
            author_profile=profile,
        )
    non_matching = create_news_page(
        public_site,
        section,
        title="Festival de archivo sin la firma solicitada",
        slug="matriz-sin-firma-solicitada",
        publication_date=dt.date(2026, 7, 20),
        tags=["matriz-autora"],
    )
    NewsPageSection.objects.create(page=non_matching, section=subsection)
    profile.is_active = False
    profile.save(update_fields=["is_active"])
    call_command("update_index", backend_name="default", verbosity=0)
    client = Client()
    target_title = "Festival de archivo con autora 0"

    for criterion in (
        {"buscar": "festival"},
        {"seccion": section.slug},
        {"subseccion": subsection.slug},
        {"etiqueta": "matriz-autora"},
        {"departamento": "04"},
        {"departamento": "04", "distrito": "040101"},
        {"orden": "asc"},
    ):
        response = client.get("/noticias/", {"autor": profile.slug, **criterion})
        content = response.content.decode()

        assert response.status_code == 200
        assert "Noticias de Autora histórica de matriz" in content
        assert content.count('class="card news-card') == 10, criterion
        assert non_matching.title not in content

    paginated = client.get(
        "/noticias/",
        {"autor": profile.slug, "orden": "asc", "pagina": "2"},
    )
    paginated_content = paginated.content.decode()
    assert paginated.status_code == 200
    assert "Festival de archivo con autora 10" in paginated_content
    assert paginated_content.count('class="card news-card') == 1

    combined = client.get(
        "/noticias/",
        {
            "autor": profile.slug,
            "buscar": "festival",
            "seccion": section.slug,
            "subseccion": subsection.slug,
            "etiqueta": "matriz-autora",
            "departamento": "04",
            "distrito": "040101",
            "orden": "asc",
        },
    )
    combined_content = combined.content.decode()
    chip_match = re.search(
        r'href="([^"]+)" aria-label="Quitar filtro de autor"', combined_content
    )

    assert combined.status_code == 200
    assert target_title in combined_content
    assert combined_content.count(target_title) == 1
    assert f'name="autor" value="{profile.slug}"' in combined_content
    assert f"autor={profile.slug}" in combined_content
    assert "orden=desc" in combined_content
    assert 'for="news-author"' not in combined_content
    assert 'id="news-author"' not in combined_content
    assert chip_match is not None
    chip_href = chip_match.group(1)
    assert "autor=" not in chip_href
    for value in (
        "buscar=festival",
        f"seccion={section.slug}",
        f"subseccion={subsection.slug}",
        "etiqueta=matriz-autora",
        "departamento=04",
        "distrito=040101",
        "orden=asc",
    ):
        assert value in chip_href
    assert (
        '<a class="btn btn-outline-secondary" href="/noticias/">Limpiar filtros</a>'
        in combined_content
    )

    invalid = client.get("/noticias/", {"autor": "autora-no-existe"})
    assert invalid.status_code == 200
    assert "El autor solicitado no existe." in invalid.content.decode()


@pytest.mark.django_db
def test_news_list_renders_empty_state_for_real_section_without_results(
    public_site,
) -> None:
    empty_section = NewsSection.objects.create(
        name="Sección sin noticias",
        slug="seccion-sin-noticias",
    )

    response = Client().get("/noticias/", {"seccion": empty_section.slug})

    assert response.status_code == 200
    assert "Aún no hay noticias publicadas en esta sección.".encode() in (
        response.content
    )


@pytest.mark.django_db
def test_news_list_handles_unknown_section_slug_safely(public_site) -> None:
    response = Client().get("/noticias/", {"seccion": "does-not-exist"})

    assert response.status_code == 200
    assert "La sección solicitada no existe.".encode() in response.content


@pytest.mark.django_db
def test_news_list_excludes_drafts_and_restricted_pages(
    public_site,
    section,
) -> None:
    create_news_page(
        public_site,
        section,
        title="Invisible draft story",
        slug="invisible-draft-story",
        publication_date=dt.date(2026, 7, 1),
        live=False,
    )
    restricted = create_news_page(
        public_site,
        section,
        title="Invisible restricted story",
        slug="invisible-restricted-story",
        publication_date=dt.date(2026, 7, 2),
    )
    PageViewRestriction.objects.create(
        page=restricted,
        restriction_type=PageViewRestriction.LOGIN,
    )
    create_news_page(
        public_site,
        section,
        title="Visible listed story",
        slug="visible-listed-story",
        publication_date=dt.date(2026, 7, 3),
    )

    content = Client().get("/noticias/").content.decode()

    assert "Visible listed story" in content
    assert "Invisible draft story" not in content
    assert "Invisible restricted story" not in content


@pytest.mark.django_db
def test_news_list_does_not_expose_internal_minor_or_privacy_data(
    public_site,
    section,
) -> None:
    school = School.objects.create(
        name="Fictional privacy school",
        department_id="04",
        district_id="040101",
    )
    group = ContributorGroup.objects.create(
        name="Fictional privacy group",
        school=school,
    )
    contributor = MinorContributor.objects.create(
        full_name="Private fictional minor name",
        group=group,
        age_band=MinorContributor.AgeBand.UNDER_14,
    )
    page = create_news_page(
        public_site,
        section,
        title="Public privacy-safe listing story",
        slug="public-privacy-safe-listing-story",
        publication_date=dt.date(2026, 7, 1),
    )
    page.contains_identifiable_minors = True
    page.minor_publication_authorizations_verified = True
    page.sensitive_content = True
    page.save()
    NewsPageAttribution.objects.create(
        page=page,
        kind=NewsPageAttribution.Kind.INTERNAL_CONTRIBUTOR,
        minor_contributor=contributor,
    )
    NewsPageAttribution.objects.create(
        page=page,
        kind=NewsPageAttribution.Kind.PUBLIC_CREDIT,
        display_name="Safe fictional public byline",
    )

    content = Client().get("/noticias/").content.decode()
    searched_content = (
        Client().get("/noticias/", {"buscar": contributor.full_name}).content.decode()
    )

    assert "Safe fictional public byline" in content
    assert "Private fictional minor name" not in content
    assert "under_14" not in content
    assert "internal_contributors" not in content
    assert "contains_identifiable_minors" not in content
    assert "minor_publication_authorizations_verified" not in content
    assert "sensitive_content" not in content
    assert page.title not in searched_content


@pytest.mark.django_db
def test_shared_public_layout_renders_landmarks_and_navigation(
    public_site,
    section,
) -> None:
    page = create_news_page(
        public_site,
        section,
        title="Shared layout detail story",
        slug="shared-layout-detail-story",
        publication_date=dt.date(2026, 7, 1),
    )

    for url in ["/", "/noticias/", page.url]:
        response = Client().get(url)
        content = response.content.decode()

        assert response.status_code == 200
        assert '<html lang="es">' in content
        assert "Navegación principal" in content
        assert 'href="/noticias/#buscar-noticias"' in content
        assert 'aria-label="Buscar noticias"' in content
        assert "Saltar al contenido principal" in content
        assert "<header" in content
        assert "<nav" in content
        assert '<main id="main-content"' in content
        assert "<footer" in content
