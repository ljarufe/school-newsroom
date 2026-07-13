import datetime as dt
import json
import re

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, RequestFactory
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
def public_site(settings):
    settings.ALLOWED_HOSTS = [*settings.ALLOWED_HOSTS, "school.test"]
    home = HomePage.objects.first()
    if home is None:
        root = Page.get_first_root_node()
        home = HomePage(title="School Newsroom", slug="school-newsroom-seo")
        root.add_child(instance=home)
    Site.objects.update_or_create(
        hostname="school.test",
        defaults={
            "port": 80,
            "site_name": "School Newsroom",
            "root_page": home,
            "is_default_site": True,
        },
    )
    return home


def site_client():
    return Client(HTTP_HOST="school.test")


@pytest.fixture
def section():
    return NewsSection.objects.get(slug="politica")


def create_news_page(
    home,
    section,
    *,
    title="SEO Test News",
    slug="seo-test-news",
    live=True,
    featured_image=None,
    summary="Resumen público ficticio para comprobar metadata SEO.",
):
    page = NewsPage(
        title=title,
        slug=slug,
        live=live,
        publication_date=dt.date(2026, 7, 12),
        summary=summary,
        body=[
            (
                "paragraph",
                "<h2>Contexto ficticio</h2>"
                "<p>Contenido público ficticio para la noticia.</p>",
            ),
        ],
        section=section,
        coverage_province="Arequipa",
        featured_image=featured_image,
    )
    home.add_child(instance=page)
    return page


def create_image(filename="seo.gif"):
    return get_image_model().objects.create(
        title=f"Imagen SEO ficticia {filename}",
        file=SimpleUploadedFile(filename, GIF_BYTES, content_type="image/gif"),
    )


def json_ld_from_response(response):
    match = re.search(
        rb'<script type="application/ld\+json">(.*?)</script>',
        response.content,
        re.DOTALL,
    )
    assert match is not None
    return json.loads(match.group(1))


@pytest.mark.django_db
def test_news_public_metadata_uses_native_and_summary_fallbacks(
    public_site,
    section,
    settings,
) -> None:
    settings.SEO_DEFAULT_NOINDEX = False
    page = create_news_page(public_site, section)

    response = site_client().get(page.url)
    content = response.content.decode()
    page_path = f"/{page.slug}/"

    assert response.status_code == 200
    assert "<title>SEO Test News</title>" in content
    assert (
        '<meta name="description" content="Resumen público ficticio para '
        'comprobar metadata SEO.">' in content
    )
    assert f'<link rel="canonical" href="http://school.test{page_path}">' in content
    assert '<meta name="robots" content="index, follow">' in content
    assert '<meta property="og:title" content="SEO Test News">' in content
    assert (
        f'<meta property="og:url" content="http://school.test{page_path}">' in content
    )
    assert '<meta name="twitter:card" content="summary">' in content
    assert json_ld_from_response(response)["description"] == page.summary


@pytest.mark.django_db
def test_news_public_metadata_omits_empty_optional_descriptions(
    public_site,
    section,
    settings,
) -> None:
    settings.SEO_DEFAULT_NOINDEX = False
    page = create_news_page(
        public_site,
        section,
        title="News Without Description",
        slug="news-without-description",
        summary="   ",
    )

    response = site_client().get(page.url)
    content = response.content.decode()
    data = json_ld_from_response(response)

    assert response.status_code == 200
    assert '<meta name="description"' not in content
    assert '<meta property="og:description"' not in content
    assert '<meta name="twitter:description"' not in content
    assert "description" not in data


@pytest.mark.django_db
def test_incomplete_draft_json_ld_omits_missing_publication_date(
    public_site,
    section,
    settings,
) -> None:
    settings.SEO_DEFAULT_NOINDEX = False
    page = create_news_page(
        public_site,
        section,
        title="Incomplete Draft News",
        slug="incomplete-draft-news",
        live=False,
    )
    page.publication_date = None
    request = RequestFactory().get(page.url, HTTP_HOST="school.test")

    context = page.get_context(request)
    data = json.loads(context["seo_json_ld"])

    assert "datePublished" not in data


@pytest.mark.django_db
def test_news_public_metadata_uses_configured_social_and_canonical_values(
    public_site,
    section,
    settings,
    tmp_path,
) -> None:
    settings.SEO_DEFAULT_NOINDEX = False
    settings.MEDIA_ROOT = tmp_path
    image = create_image()
    page = create_news_page(public_site, section, featured_image=image)
    page.seo_title = "Título SEO configurado"
    page.search_description = "Descripción meta configurada."
    page.og_title = "Título social configurado"
    page.og_description = "Descripción social configurada."
    page.canonical_url = "https://canonical.example.org/original"
    page.save()

    response = site_client().get(page.url)
    content = response.content.decode()

    assert "<title>Título SEO configurado</title>" in content
    assert 'content="Descripción meta configurada."' in content
    assert (
        '<link rel="canonical" href="https://canonical.example.org/original">'
        in content
    )
    assert 'property="og:title" content="Título social configurado"' in content
    assert (
        'property="og:description" content="Descripción social configurada."' in content
    )
    assert 'property="og:image" content="http://school.test/media/' in content
    assert 'name="twitter:card" content="summary_large_image"' in content
    assert 'name="twitter:image" content="http://school.test/media/' in content


@pytest.mark.django_db
def test_explicit_og_image_precedes_featured_image(
    public_site,
    section,
    settings,
    tmp_path,
) -> None:
    settings.SEO_DEFAULT_NOINDEX = False
    settings.MEDIA_ROOT = tmp_path
    featured_image = create_image("featured.gif")
    og_image = create_image("open-graph.gif")
    page = create_news_page(
        public_site,
        section,
        title="Explicit OG Image News",
        slug="explicit-og-image-news",
        featured_image=featured_image,
    )
    page.og_image = og_image
    page.save()

    response = site_client().get(page.url)
    content = response.content.decode()
    og_rendition_url = og_image.get_rendition("fill-1200x630").url
    featured_rendition_url = featured_image.get_rendition("fill-1200x630").url

    assert (
        f'<meta property="og:image" '
        f'content="http://school.test{og_rendition_url}">' in content
    )
    assert (
        f'<meta property="og:image" '
        f'content="http://school.test{featured_rendition_url}">' not in content
    )


@pytest.mark.django_db
def test_cleared_or_deleted_og_image_restores_featured_image_fallback(
    public_site,
    section,
    settings,
    tmp_path,
) -> None:
    settings.SEO_DEFAULT_NOINDEX = False
    settings.MEDIA_ROOT = tmp_path
    featured_image = create_image("featured-fallback.gif")
    og_image = create_image("clearable-open-graph.gif")
    page = create_news_page(
        public_site,
        section,
        title="OG Image Fallback News",
        slug="og-image-fallback-news",
        featured_image=featured_image,
    )
    page.og_image = og_image
    page.save()
    featured_rendition_url = featured_image.get_rendition("fill-1200x630").url

    page.og_image = None
    page.save(update_fields=["og_image"])
    cleared_content = site_client().get(page.url).content.decode()

    assert page.og_image_id is None
    assert (
        f'<meta property="og:image" '
        f'content="http://school.test{featured_rendition_url}">' in cleared_content
    )

    page.og_image = og_image
    page.save(update_fields=["og_image"])
    og_image.delete()
    page.refresh_from_db()
    deleted_content = site_client().get(page.url).content.decode()

    assert page.og_image_id is None
    assert (
        f'<meta property="og:image" '
        f'content="http://school.test{featured_rendition_url}">' in deleted_content
    )


@pytest.mark.django_db
def test_global_and_page_noindex_apply_to_public_html(
    public_site,
    section,
    settings,
) -> None:
    page = create_news_page(public_site, section)
    client = site_client()

    settings.SEO_DEFAULT_NOINDEX = True
    assert (
        b'<meta name="robots" content="noindex, follow">'
        in client.get(
            "/",
        ).content
    )
    assert (
        b'<meta name="robots" content="noindex, follow">'
        in client.get(
            page.url,
        ).content
    )

    settings.SEO_DEFAULT_NOINDEX = False
    assert b'<meta name="robots" content="index, follow">' in client.get("/").content
    assert (
        b'<meta name="robots" content="index, follow">'
        in client.get(
            page.url,
        ).content
    )

    page.seo_noindex = True
    page.save(update_fields=["seo_noindex"])
    assert (
        b'<meta name="robots" content="noindex, follow">'
        in client.get(
            page.url,
        ).content
    )


@pytest.mark.django_db
def test_json_ld_is_safe_and_uses_only_ordered_public_credits(
    public_site,
    section,
    settings,
) -> None:
    settings.SEO_DEFAULT_NOINDEX = False
    school = School.objects.create(
        name="Fictional School",
        province="Arequipa",
        district="Cercado",
    )
    group = ContributorGroup.objects.create(
        name="Internal Fictional Group",
        school=school,
    )
    contributor = MinorContributor.objects.create(
        full_name="Private Fictional Minor",
        group=group,
        age_band=MinorContributor.AgeBand.UNDER_14,
    )
    title = "Noticia </script><script>alert('x')</script> ficticia"
    page = create_news_page(
        public_site,
        section,
        title=title,
        slug="safe-json-ld",
    )
    NewsPageContributor.objects.create(page=page, contributor=contributor)
    NewsPagePublicCredit.objects.create(
        page=page,
        display_name="Segunda firma pública",
        sort_order=2,
    )
    NewsPagePublicCredit.objects.create(
        page=page,
        display_name="Primera firma pública",
        sort_order=1,
    )
    NewsPagePublicCredit.objects.create(page=page, display_name="   ", sort_order=3)

    response = site_client().get(page.url)
    data = json_ld_from_response(response)
    content = response.content.decode()

    assert data["@type"] == "NewsArticle"
    assert data["headline"] == title
    assert data["mainEntityOfPage"] == f"http://school.test/{page.slug}/"
    assert data["author"] == [
        {"name": "Primera firma pública"},
        {"name": "Segunda firma pública"},
    ]
    assert all("@type" not in author for author in data["author"])
    assert "Private Fictional Minor" not in content
    assert "under_14" not in content
    assert "contains_identifiable_minors" not in content
    assert "</script><script>alert('x')</script>" not in content
    assert "\\u003C/script\\u003E" in content


@pytest.mark.django_db
def test_sitemap_uses_native_visibility_and_ticket_indexation_rules(
    public_site,
    section,
    settings,
) -> None:
    settings.SEO_DEFAULT_NOINDEX = False
    included = create_news_page(
        public_site,
        section,
        title="Included News",
        slug="included-news",
    )
    draft = create_news_page(
        public_site,
        section,
        title="Draft News",
        slug="draft-news-seo",
        live=False,
    )
    restricted = create_news_page(
        public_site,
        section,
        title="Restricted News",
        slug="restricted-news-seo",
    )
    PageViewRestriction.objects.create(
        page=restricted,
        restriction_type=PageViewRestriction.LOGIN,
    )
    noindex = create_news_page(
        public_site,
        section,
        title="Noindex News",
        slug="noindex-news",
    )
    noindex.seo_noindex = True
    noindex.save(update_fields=["seo_noindex"])
    external_canonical = create_news_page(
        public_site,
        section,
        title="External Canonical News",
        slug="external-canonical-news",
    )
    external_canonical.canonical_url = "https://example.org/original"
    external_canonical.save(update_fields=["canonical_url"])
    self_canonical = create_news_page(
        public_site,
        section,
        title="Self Canonical News",
        slug="self-canonical-news",
    )
    self_canonical.canonical_url = f"http://school.test/{self_canonical.slug}/"
    self_canonical.save(update_fields=["canonical_url"])

    content = site_client().get("/sitemap.xml").content.decode()

    assert f"http://school.test/{included.slug}/" in content
    assert f"http://school.test/{self_canonical.slug}/" in content
    assert draft.slug not in content
    assert restricted.slug not in content
    assert noindex.slug not in content
    assert external_canonical.slug not in content
    assert "https://example.org/original" not in content

    settings.SEO_DEFAULT_NOINDEX = True
    globally_noindexed_content = site_client().get("/sitemap.xml").content.decode()
    assert "<loc>" not in globally_noindexed_content


@pytest.mark.django_db
def test_robots_txt_allows_crawling_and_advertises_native_sitemap(
    public_site,
    settings,
) -> None:
    settings.SEO_DEFAULT_NOINDEX = True

    response = site_client().get("/robots.txt")

    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/plain")
    assert response.content.decode() == (
        "User-agent: *\nDisallow:\nSitemap: http://school.test/sitemap.xml\n"
    )
