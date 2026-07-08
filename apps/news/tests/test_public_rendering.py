import datetime as dt

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, RequestFactory
from django.utils import timezone
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
    tags=None,
):
    page = NewsPage(
        title=title,
        slug=slug,
        live=live,
        publication_date=publication_date,
        summary=f"Summary for {title}.",
        body=[
            ("heading", "Story background"),
            ("paragraph", "<p>Detailed public body text.</p>"),
        ],
        section=section,
        school=school,
        coverage_province="Arequipa",
        coverage_district="Cercado",
        featured_image=featured_image,
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
    assert b"Story background" in response.content
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
def test_news_detail_renders_featured_image_with_default_alt(
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
    assert 'alt="Descripción significativa de imagen"'.encode() in response.content


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
