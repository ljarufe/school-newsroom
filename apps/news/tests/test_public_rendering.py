import datetime as dt

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, RequestFactory
from django.utils import timezone
from wagtail.embeds.exceptions import EmbedNotFoundException
from wagtail.images import get_image_model
from wagtail.models import Page, PageViewRestriction, Site

from apps.home.models import HomePage
from apps.news.models import (
    ContributorGroup,
    MinorContributor,
    NewsPage,
    NewsPageContributor,
    NewsPagePublicCredit,
    NewsSection,
    School,
)

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
):
    page = NewsPage(
        title=title,
        slug=slug,
        live=live,
        publication_date=publication_date,
        summary=f"Summary for {title}.",
        body=body
        or [
            (
                "paragraph",
                "<h2>Story background</h2><p>Detailed public body text.</p>",
            ),
        ],
        section=section,
        school=school,
        coverage_province="Arequipa",
        coverage_district="Cercado",
        featured_image=featured_image,
        featured_image_caption=featured_image_caption,
        featured_image_alt_text=featured_image_alt_text,
        featured_image_credit=featured_image_credit,
    )
    home_page.add_child(instance=page)
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
        province="Arequipa",
        district="Cercado",
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
    assert b"Secci\xc3\xb3n" in response.content
    assert b"Published News" in response.content
    assert b"Summary for Published News." in response.content
    assert "Política".encode() in response.content
    assert b"Fictional School" in response.content
    assert b"Colegio" in response.content
    assert b"Cobertura" in response.content
    assert b"Arequipa" in response.content
    assert b"Cercado" in response.content


@pytest.mark.django_db
def test_home_renders_public_credits_without_internal_contributor_data(
    public_site,
    section,
) -> None:
    school = School.objects.create(
        name="Fictional School",
        province="Arequipa",
        district="Cercado",
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
    NewsPageContributor.objects.create(page=page, contributor=contributor)
    NewsPagePublicCredit.objects.create(
        page=page,
        display_name="Second fictional public credit",
        sort_order=2,
    )
    NewsPagePublicCredit.objects.create(
        page=page,
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
        province="Arequipa",
        district="Cercado",
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
    assert b"Summary for Detail News." in response.content
    assert b"Fecha de publicaci\xc3\xb3n" in response.content
    assert b"julio" in response.content
    assert b"July" not in response.content
    assert b"Secci\xc3\xb3n" in response.content
    assert b"Fictional School" in response.content
    assert b"Colegio" in response.content
    assert b"Cobertura" in response.content
    assert b"<h2>Story background</h2>" in response.content
    assert b"Detailed public body text." in response.content
    assert b"Etiquetas" in response.content
    assert b"student-reporting" in response.content
    assert b"local-news" in response.content


@pytest.mark.django_db
def test_news_detail_renders_public_credits_without_internal_privacy_data(
    public_site,
    section,
) -> None:
    school = School.objects.create(
        name="Fictional School",
        province="Arequipa",
        district="Cercado",
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
    NewsPageContributor.objects.create(page=page, contributor=contributor)
    NewsPagePublicCredit.objects.create(
        page=page,
        display_name="Second fictional detail credit",
        sort_order=2,
    )
    NewsPagePublicCredit.objects.create(
        page=page,
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
        province="Arequipa",
        district="Cercado",
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
    NewsPageContributor.objects.create(page=page, contributor=contributor)
    NewsPagePublicCredit.objects.create(
        page=page,
        display_name="Safe fictional public byline",
    )

    content = Client().get("/noticias/").content.decode()

    assert "Safe fictional public byline" in content
    assert "Private fictional minor name" not in content
    assert "under_14" not in content
    assert "internal_contributors" not in content
    assert "contains_identifiable_minors" not in content
    assert "minor_publication_authorizations_verified" not in content
    assert "sensitive_content" not in content


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
        assert "Saltar al contenido principal" in content
        assert "<header" in content
        assert "<nav" in content
        assert '<main id="main-content"' in content
        assert "<footer" in content
