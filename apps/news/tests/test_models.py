import datetime as dt

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import ProtectedError
from wagtail.images import get_image_model
from wagtail.models import Page

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

INITIAL_SECTION_SLUGS = [
    "politica",
    "cultura",
    "medio-ambiente",
    "problematicas-sociales",
    "columnas",
    "entrevistas",
]


@pytest.fixture
def home_page():
    home = HomePage.objects.first()
    if home is not None:
        return home

    root = Page.get_first_root_node()
    home = HomePage(title="School Newsroom", slug="school-newsroom")
    root.add_child(instance=home)
    return home


@pytest.fixture
def section():
    return NewsSection.objects.get(slug="politica")


def create_news_page(
    home_page,
    section,
    *,
    title="Test News",
    slug="test-news",
    publication_date=dt.date(2026, 7, 1),
    live=True,
    school=None,
    featured_image=None,
):
    page = NewsPage(
        title=title,
        slug=slug,
        live=live,
        publication_date=publication_date,
        summary="A concise public summary for a fictional news item.",
        body=[
            ("paragraph", "<p>Reported context</p>"),
            ("paragraph", "<p>Structured body paragraph.</p>"),
        ],
        section=section,
        school=school,
        coverage_province="Arequipa",
        coverage_district="Cercado",
        featured_image=featured_image,
    )
    home_page.add_child(instance=page)
    return page


def create_test_image():
    image_model = get_image_model()
    return image_model.objects.create(
        title="Generic test image",
        file="original_images/generic-test.gif",
        width=1,
        height=1,
    )


@pytest.mark.django_db
def test_contextual_image_metadata_fields_are_blank_safe() -> None:
    page = NewsPage()

    assert page.featured_image_caption == ""
    assert page.featured_image_alt_text == ""
    assert page.featured_image_credit == ""
    assert page.og_image_caption == ""
    assert page.og_image_alt_text == ""
    assert page.og_image_credit == ""
    assert NewsPage._meta.get_field("featured_image_caption").max_length == 500
    assert NewsPage._meta.get_field("featured_image_alt_text").max_length == 500
    assert NewsPage._meta.get_field("featured_image_credit").max_length == 255


@pytest.mark.django_db
def test_initial_news_sections_are_seeded() -> None:
    assert list(NewsSection.objects.values_list("slug", flat=True)) == (
        INITIAL_SECTION_SLUGS
    )


@pytest.mark.django_db
def test_news_section_slug_is_unique() -> None:
    with pytest.raises(IntegrityError):
        NewsSection.objects.create(
            name="Duplicate Politics",
            slug="politica",
            sort_order=999,
        )


@pytest.mark.django_db
def test_news_section_ordering_and_string_representation() -> None:
    NewsSection.objects.create(name="Later", slug="later", sort_order=200)
    NewsSection.objects.create(name="Earlier", slug="earlier", sort_order=5)

    sections = list(NewsSection.objects.values_list("name", flat=True))

    assert sections[:2] == ["Earlier", "Política"]
    assert str(NewsSection.objects.get(slug="cultura")) == "Cultura"


@pytest.mark.django_db
def test_school_ordering_and_string_representation() -> None:
    School.objects.create(
        name="Second Fictional School",
        province="Arequipa",
        district="Cercado",
    )
    School.objects.create(
        name="First Fictional School",
        province="Arequipa",
        district="Yanahuara",
    )

    assert list(School.objects.values_list("name", flat=True)) == [
        "First Fictional School",
        "Second Fictional School",
    ]
    assert str(School.objects.first()) == "First Fictional School"


@pytest.mark.django_db
def test_section_is_required_by_model_validation() -> None:
    page = NewsPage(
        title="Missing Section",
        slug="missing-section",
        publication_date=dt.date(2026, 7, 1),
        summary="A concise public summary for a fictional news item.",
        body=[("paragraph", "<p>Body.</p>")],
        coverage_province="Arequipa",
    )

    with pytest.raises(ValidationError) as exc_info:
        page.full_clean(exclude=["path", "depth"])

    assert "section" in exc_info.value.message_dict


@pytest.mark.django_db
def test_used_section_is_protected(home_page, section) -> None:
    create_news_page(home_page, section)

    with pytest.raises(ProtectedError):
        section.delete()


@pytest.mark.django_db
def test_school_is_set_null_when_deleted(home_page, section) -> None:
    school = School.objects.create(
        name="Fictional School",
        province="Arequipa",
        district="Cercado",
    )
    news_page = create_news_page(home_page, section, school=school)

    school.delete()
    news_page.refresh_from_db()

    assert news_page.school is None


@pytest.mark.django_db
def test_contributor_group_string_representation_and_school_protection() -> None:
    school = School.objects.create(
        name="Fictional School",
        province="Arequipa",
        district="Cercado",
    )
    group = ContributorGroup.objects.create(
        name="Fictional Reporting Workshop",
        school=school,
    )

    assert str(group) == "Fictional Reporting Workshop (Fictional School)"

    with pytest.raises(ProtectedError):
        school.delete()


@pytest.mark.django_db
def test_minor_contributor_age_band_and_derived_school() -> None:
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

    assert contributor.school == school
    assert str(contributor) == "Fictional Contributor One"
    assert MinorContributor.AgeBand.values == ["under_14", "14_to_17"]


@pytest.mark.django_db
def test_minor_contributors_order_by_internal_name() -> None:
    school = School.objects.create(
        name="Fictional School",
        province="Arequipa",
        district="Cercado",
    )
    group = ContributorGroup.objects.create(
        name="Fictional Reporting Workshop",
        school=school,
    )
    MinorContributor.objects.create(
        full_name="Fictional Contributor Two",
        group=group,
        age_band=MinorContributor.AgeBand.FROM_14_TO_17,
    )
    MinorContributor.objects.create(
        full_name="Fictional Contributor One",
        group=group,
        age_band=MinorContributor.AgeBand.UNDER_14,
    )

    assert list(MinorContributor.objects.values_list("full_name", flat=True)) == [
        "Fictional Contributor One",
        "Fictional Contributor Two",
    ]


@pytest.mark.django_db
def test_news_page_accepts_multiple_internal_contributors(home_page, section) -> None:
    school = School.objects.create(
        name="Fictional School",
        province="Arequipa",
        district="Cercado",
    )
    group = ContributorGroup.objects.create(
        name="Fictional Reporting Workshop",
        school=school,
    )
    first_contributor = MinorContributor.objects.create(
        full_name="Fictional Contributor One",
        group=group,
        age_band=MinorContributor.AgeBand.UNDER_14,
    )
    second_contributor = MinorContributor.objects.create(
        full_name="Fictional Contributor Two",
        group=group,
        age_band=MinorContributor.AgeBand.FROM_14_TO_17,
    )
    news_page = create_news_page(home_page, section)

    NewsPageContributor.objects.create(
        page=news_page,
        contributor=first_contributor,
        sort_order=0,
    )
    NewsPageContributor.objects.create(
        page=news_page,
        contributor=second_contributor,
        sort_order=1,
    )

    assert list(
        news_page.internal_contributors.values_list(
            "contributor__full_name",
            flat=True,
        ),
    ) == ["Fictional Contributor One", "Fictional Contributor Two"]


@pytest.mark.django_db
def test_news_page_rejects_duplicate_internal_contributor(home_page, section) -> None:
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
    news_page = create_news_page(home_page, section)

    NewsPageContributor.objects.create(page=news_page, contributor=contributor)

    with pytest.raises(IntegrityError):
        NewsPageContributor.objects.create(page=news_page, contributor=contributor)


@pytest.mark.django_db
def test_public_credits_keep_editorial_order(home_page, section) -> None:
    news_page = create_news_page(home_page, section)
    NewsPagePublicCredit.objects.create(
        page=news_page,
        display_name="Second public credit",
        sort_order=2,
    )
    NewsPagePublicCredit.objects.create(
        page=news_page,
        display_name="First public credit",
        sort_order=1,
    )

    assert list(news_page.public_credits.values_list("display_name", flat=True)) == [
        "First public credit",
        "Second public credit",
    ]


@pytest.mark.django_db
def test_featured_image_is_set_null_when_deleted(home_page, section) -> None:
    image = create_test_image()
    news_page = create_news_page(home_page, section, featured_image=image)

    image.delete()
    news_page.refresh_from_db()

    assert news_page.featured_image is None


@pytest.mark.django_db
def test_tags_are_associated_with_news_page(home_page, section) -> None:
    news_page = create_news_page(home_page, section)

    news_page.tags.add("student-reporting", "local-news")

    assert sorted(news_page.tags.names()) == ["local-news", "student-reporting"]


@pytest.mark.django_db
def test_page_tree_constraints(home_page, section) -> None:
    news_page = create_news_page(home_page, section)

    assert NewsPage.can_create_at(home_page)
    assert not NewsPage.can_create_at(news_page)
    assert NewsPage.allowed_subpage_models() == []
