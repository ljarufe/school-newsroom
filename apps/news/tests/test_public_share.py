import datetime as dt
from html import escape
from urllib.parse import parse_qs, urlsplit

import pytest
from django.test import Client, RequestFactory
from wagtail.models import Page, Site

from apps.home.models import HomePage
from apps.news.models import (
    NewsPage,
    NewsPagePublicCredit,
    NewsPageSection,
    NewsSection,
)
from apps.news.seo_metadata import (
    PublicMetadata,
    build_public_share_links,
)


@pytest.fixture
def public_site(settings):
    settings.ALLOWED_HOSTS = [*settings.ALLOWED_HOSTS, "school.test"]
    root = Page.get_first_root_node()
    home = HomePage(title="School Newsroom", slug="school-newsroom-share")
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


@pytest.fixture
def section():
    return NewsSection.objects.get(slug="politica")


def create_news_page(home, section, *, live=True):
    page = NewsPage(
        title="Noticia pública ficticia",
        slug="noticia-publica-ficticia",
        live=live,
        publication_date=dt.date(2026, 8, 4),
        body=[
            (
                "paragraph",
                "<h2>Contexto público</h2><p>Contenido ficticio del cuerpo.</p>",
            )
        ],
        coverage_province="Arequipa",
    )
    home.add_child(instance=page)
    NewsPageSection.objects.create(page=page, section=section)
    NewsPagePublicCredit.objects.create(
        page=page,
        display_name="Redacción ficticia",
        sort_order=0,
    )
    return page


def public_metadata(**overrides) -> PublicMetadata:
    values = {
        "title": "Título SEO",
        "description": "Descripción meta",
        "canonical_url": "https://school.test/noticia/",
        "robots": "index, follow",
        "og_title": "Título social",
        "og_description": "Descripción social",
        "og_image_url": "",
        "og_image_alt_text": "",
        "og_type": "article",
        "site_name": "School Newsroom",
        "twitter_card": "summary",
    }
    values.update(overrides)
    return PublicMetadata(**values)


def test_share_link_builder_uses_effective_social_metadata_and_encodes_channels():
    title = 'Título social + 50% & "especial"\nsegunda línea'
    description = 'Descripción <ficticia> & "segura"\nsegunda línea'
    canonical = (
        "https://external.example/noticia-ficticia"
        "?origen=school%20newsroom&grupo=A%20%26%20B"
    )

    links = build_public_share_links(
        public_metadata(
            og_title=title,
            og_description=description,
            canonical_url=canonical,
        )
    )

    assert links.title == title
    assert links.description == description
    assert links.canonical_url == canonical

    whatsapp = urlsplit(links.whatsapp_url)
    assert (whatsapp.scheme, whatsapp.netloc, whatsapp.path) == (
        "https",
        "wa.me",
        "/",
    )
    assert parse_qs(whatsapp.query) == {"text": [f"{title}\n{canonical}"]}

    x_url = urlsplit(links.x_url)
    assert (x_url.scheme, x_url.netloc, x_url.path) == (
        "https",
        "x.com",
        "/intent/tweet",
    )
    assert parse_qs(x_url.query) == {"text": [title], "url": [canonical]}

    facebook = urlsplit(links.facebook_url)
    assert (facebook.scheme, facebook.netloc, facebook.path) == (
        "https",
        "www.facebook.com",
        "/sharer/sharer.php",
    )
    assert parse_qs(facebook.query) == {"u": [canonical]}

    email = urlsplit(links.email_url)
    assert email.scheme == "mailto"
    assert parse_qs(email.query) == {
        "subject": [title],
        "body": [f"{description}\r\n\r\n{canonical}"],
    }
    assert "%20" in links.email_url
    assert "%2B" in links.email_url
    assert "%0D%0A%0D%0A" in links.email_url


def test_share_link_builder_omits_email_description_when_empty():
    canonical = "https://school.test/noticia/?origen=portada"

    links = build_public_share_links(
        public_metadata(og_description="", canonical_url=canonical)
    )

    email = parse_qs(urlsplit(links.email_url).query)
    assert email == {"subject": ["Título social"], "body": [canonical]}


@pytest.mark.django_db
def test_live_noindex_detail_escapes_server_rendered_share_metadata(
    public_site,
    section,
    settings,
) -> None:
    settings.SEO_DEFAULT_NOINDEX = False
    page = create_news_page(public_site, section)
    title = 'Aprendizajes <ficticios> "A & B"><script>window.shareInjected=1</script>'
    description = 'Descripción "segura" & <img src=x onerror="window.shareInjected=2">'
    canonical = (
        "https://external.example/noticia-ficticia"
        "?origen=school-newsroom&grupo=A%20%26%20B"
    )
    page.og_title = title
    page.og_description = description
    page.canonical_url = canonical
    page.seo_noindex = True
    page.tags.add("etiqueta-ficticia")
    page.save()

    response = Client(HTTP_HOST="school.test").get(page.url)
    html = response.content.decode()

    assert response.status_code == 200
    assert '<meta name="robots" content="noindex, follow">' in html
    assert "data-public-share" in html
    assert f'data-share-title="{escape(title, quote=True)}"' in html
    assert f'data-share-description="{escape(description, quote=True)}"' in html
    assert f'data-share-url="{escape(canonical, quote=True)}"' in html
    assert page.full_url not in html
    assert "contains_identifiable_minors" not in html
    assert "minor_publication_authorizations_verified" not in html
    assert "sensitive_content" not in html
    assert "window.shareInjected=1</script>" not in html
    assert '<img src=x onerror="window.shareInjected=2">' not in html
    assert "<iframe" not in html
    assert 'src="/static/public/js/share.js"' in html


@pytest.mark.django_db
def test_real_wagtail_preview_path_hides_share_actions(
    public_site,
    section,
) -> None:
    page = create_news_page(public_site, section)
    normal_response = Client(HTTP_HOST="school.test").get(page.url)
    preview_request = RequestFactory().get(page.url, HTTP_HOST="school.test")

    preview_response = page.make_preview_request(original_request=preview_request)

    assert "Compartir esta noticia" in normal_response.content.decode()
    assert preview_response.status_code == 200
    assert "Compartir esta noticia" not in preview_response.content.decode()
    assert "public/js/share.js" not in preview_response.content.decode()
