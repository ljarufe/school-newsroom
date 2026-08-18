import datetime as dt
import importlib.metadata

import pytest
from django.contrib.auth import get_user_model
from django.core.checks import run_checks
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from wagtail.images import get_image_model
from wagtail.models import Collection, Page

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
        body=[
            ("paragraph", "<p>Reported context</p>"),
            ("paragraph", "<p>Structured body paragraph.</p>"),
        ],
        school=school,
        coverage_department_id="04",
        coverage_district_id="040101",
        featured_image=featured_image,
    )
    home_page.add_child(instance=page)
    NewsPageSection.objects.create(page=page, section=section)
    return page


def create_test_image():
    image_model = get_image_model()
    return image_model.objects.create(
        title="Generic test image",
        file="original_images/generic-test.gif",
        width=1,
        height=1,
    )


def test_treebeard_resolution_preserves_wagtail_manager_behavior() -> None:
    assert importlib.metadata.version("django-treebeard").startswith("5.2.")
    assert Page.objects.all().query.order_by == ("path",)
    assert Collection.objects.all().query.order_by == ("path",)
    assert hasattr(Page.objects, "specific")
    assert not [issue for issue in run_checks() if issue.id == "treebeard.E001"]


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
    assert (
        list(
            NewsSection.objects.filter(parent__isnull=True).values_list(
                "slug", flat=True
            )
        )
        == INITIAL_SECTION_SLUGS
    )


@pytest.mark.django_db
def test_provisional_subsections_have_expected_variable_branch_sizes() -> None:
    counts = {
        section.slug: section.subsections.count()
        for section in NewsSection.objects.filter(parent__isnull=True)
    }

    assert counts == {
        "politica": 3,
        "cultura": 5,
        "medio-ambiente": 4,
        "problematicas-sociales": 2,
        "columnas": 1,
        "entrevistas": 3,
    }


@pytest.mark.django_db
def test_news_section_rejects_self_parent_and_third_level() -> None:
    politics = NewsSection.objects.get(slug="politica")
    local = NewsSection.objects.get(slug="politica-local")

    politics.parent = politics
    with pytest.raises(ValidationError) as self_error:
        politics.full_clean()
    assert "Una sección no puede depender de sí misma." in str(self_error.value)

    invalid = NewsSection(name="Third level", slug="third-level", parent=local)
    with pytest.raises(ValidationError) as depth_error:
        invalid.full_clean()
    assert "Una subsección no puede depender de otra subsección." in str(
        depth_error.value
    )


@pytest.mark.django_db
def test_news_section_moves_and_level_conversion_rules() -> None:
    politics = NewsSection.objects.get(slug="politica")
    culture = NewsSection.objects.get(slug="cultura")
    local = NewsSection.objects.get(slug="politica-local")

    local.parent = culture
    local.full_clean()
    local.save()
    assert NewsSection.objects.get(pk=local.pk).parent == culture

    local.parent = None
    with pytest.raises(ValidationError) as subsection_error:
        local.full_clean()
    assert "Una subsección no puede convertirse en sección principal." in str(
        subsection_error.value
    )

    politics.parent = culture
    with pytest.raises(ValidationError) as section_error:
        politics.full_clean()
    assert "Una sección principal no puede convertirse en subsección." in str(
        section_error.value
    )


@pytest.mark.django_db
def test_news_taxonomy_derives_paths_parents_and_article_sections(
    home_page,
    section,
) -> None:
    page = create_news_page(home_page, section)
    music = NewsSection.objects.get(slug="musica")
    interviews = NewsSection.objects.get(slug="entrevistas")
    community = NewsSection.objects.get(slug="comunidad")
    page.section_assignments.set(
        [
            NewsPageSection(page=page, section=music),
            NewsPageSection(page=page, section=interviews),
            NewsPageSection(page=page, section=community),
        ]
    )
    page.__dict__.pop("taxonomy", None)

    assert [item.slug for item in page.taxonomy.explicit_sections] == [
        "musica",
        "entrevistas",
        "comunidad",
    ]
    assert [item.slug for item in page.taxonomy.effective_main_sections] == [
        "cultura",
        "entrevistas",
    ]
    assert page.taxonomy.visible_paths == (
        "Cultura › Música",
        "Entrevistas › Comunidad",
    )
    assert page.taxonomy.article_section_values == (
        "Cultura",
        "Cultura > Música",
        "Entrevistas",
        "Entrevistas > Comunidad",
    )


@pytest.mark.django_db
def test_news_page_section_is_unique(home_page, section) -> None:
    page = create_news_page(home_page, section)

    with pytest.raises(IntegrityError):
        NewsPageSection.objects.create(page=page, section=section)


@pytest.mark.django_db
def test_revision_only_section_reference_is_protected(home_page, section) -> None:
    page = create_news_page(home_page, section)
    revision = page.save_revision()
    page.section_assignments.all().delete()

    with pytest.raises(ProtectedError):
        section.delete()

    assert revision.content["section_assignments"][0]["section"] == section.pk


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

    sections = list(
        NewsSection.objects.filter(parent__isnull=True).values_list("name", flat=True)
    )

    assert sections[:2] == ["Earlier", "Política"]
    assert str(NewsSection.objects.get(slug="cultura")) == "Cultura"


@pytest.mark.django_db
def test_school_ordering_and_string_representation() -> None:
    School.objects.create(
        name="Second Fictional School",
        department_id="04",
        district_id="040101",
    )
    School.objects.create(
        name="First Fictional School",
        department_id="04",
        district_id="040126",
    )

    assert list(School.objects.values_list("name", flat=True)) == [
        "First Fictional School",
        "Second Fictional School",
    ]
    assert str(School.objects.first()) == "First Fictional School"


@pytest.mark.django_db
def test_draft_page_model_allows_no_taxonomy_assignment() -> None:
    page = NewsPage(
        title="Missing Section",
        slug="missing-section",
        publication_date=dt.date(2026, 7, 1),
        body=[("paragraph", "<p>Body.</p>")],
        coverage_department_id="04",
    )

    page.full_clean(exclude=["path", "depth"])


@pytest.mark.django_db
def test_used_section_is_protected(home_page, section) -> None:
    create_news_page(home_page, section)

    with pytest.raises(ProtectedError):
        section.delete()


@pytest.mark.django_db
def test_school_is_set_null_when_deleted(home_page, section) -> None:
    school = School.objects.create(
        name="Fictional School",
        department_id="04",
        district_id="040101",
    )
    news_page = create_news_page(home_page, section, school=school)

    school.delete()
    news_page.refresh_from_db()

    assert news_page.school is None


@pytest.mark.django_db
def test_contributor_group_string_representation_and_school_protection() -> None:
    school = School.objects.create(
        name="Fictional School",
        department_id="04",
        district_id="040101",
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

    assert contributor.school == school
    assert str(contributor) == "Fictional Contributor One"
    assert MinorContributor.AgeBand.values == ["under_14", "14_to_17"]


@pytest.mark.django_db
def test_minor_contributors_order_by_internal_name() -> None:
    school = School.objects.create(
        name="Fictional School",
        department_id="04",
        district_id="040101",
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
        department_id="04",
        district_id="040101",
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

    NewsPageAttribution.objects.create(
        page=news_page,
        kind=NewsPageAttribution.Kind.INTERNAL_CONTRIBUTOR,
        minor_contributor=first_contributor,
        sort_order=0,
    )
    NewsPageAttribution.objects.create(
        page=news_page,
        kind=NewsPageAttribution.Kind.INTERNAL_CONTRIBUTOR,
        minor_contributor=second_contributor,
        sort_order=1,
    )

    assert list(
        news_page.attributions.values_list(
            "minor_contributor__full_name",
            flat=True,
        ),
    ) == ["Fictional Contributor One", "Fictional Contributor Two"]


@pytest.mark.django_db
def test_news_page_rejects_duplicate_internal_contributor(home_page, section) -> None:
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
    news_page = create_news_page(home_page, section)

    NewsPageAttribution.objects.create(
        page=news_page,
        kind=NewsPageAttribution.Kind.INTERNAL_CONTRIBUTOR,
        minor_contributor=contributor,
    )

    with pytest.raises(IntegrityError):
        NewsPageAttribution.objects.create(
            page=news_page,
            kind=NewsPageAttribution.Kind.INTERNAL_CONTRIBUTOR,
            minor_contributor=contributor,
        )


@pytest.mark.django_db
def test_public_credits_keep_editorial_order(home_page, section) -> None:
    news_page = create_news_page(home_page, section)
    NewsPageAttribution.objects.create(
        page=news_page,
        kind=NewsPageAttribution.Kind.PUBLIC_CREDIT,
        display_name="Second public credit",
        sort_order=2,
    )
    NewsPageAttribution.objects.create(
        page=news_page,
        kind=NewsPageAttribution.Kind.PUBLIC_CREDIT,
        display_name="First public credit",
        sort_order=1,
    )

    assert list(news_page.public_attributions) == list(news_page.attributions.all())
    assert list(news_page.attributions.values_list("display_name", flat=True)) == [
        "First public credit",
        "Second public credit",
    ]


@pytest.mark.django_db
def test_author_profile_enforces_private_identity_and_minor_email_boundaries():
    school = School.objects.create(name="Fictional School", department_id="04")
    contributor = MinorContributor.objects.create(
        full_name="Private fictional minor",
        group=ContributorGroup.objects.create(name="Fictional group", school=school),
        age_band=MinorContributor.AgeBand.UNDER_14,
    )
    profile = AuthorProfile(
        display_name="Public fictional author",
        slug="public-fictional-author",
        minor_contributor=contributor,
        email="private@example.invalid",
    )

    with pytest.raises(ValidationError, match="no puede incluir correo"):
        profile.full_clean()


@pytest.mark.django_db
def test_author_profile_and_attribution_string_representations(home_page, section):
    school = School.objects.create(name="Fictional School", department_id="04")
    contributor = MinorContributor.objects.create(
        full_name="Private fictional minor",
        group=ContributorGroup.objects.create(name="Fictional group", school=school),
        age_band=MinorContributor.AgeBand.UNDER_14,
    )
    profile = AuthorProfile.objects.create(
        display_name="Public fictional author",
        slug="public-fictional-author-for-strings",
    )
    page = create_news_page(home_page, section)
    author = NewsPageAttribution.objects.create(
        page=page,
        kind=NewsPageAttribution.Kind.AUTHOR,
        author_profile=profile,
    )
    credit = NewsPageAttribution.objects.create(
        page=page,
        kind=NewsPageAttribution.Kind.PUBLIC_CREDIT,
        display_name="Fictional newsroom",
    )
    internal = NewsPageAttribution.objects.create(
        page=page,
        kind=NewsPageAttribution.Kind.INTERNAL_CONTRIBUTOR,
        minor_contributor=contributor,
    )

    expected_author_label = (
        "Public fictional author (public-fictional-author-for-strings)"
    )
    assert str(profile) == expected_author_label
    assert str(author) == expected_author_label
    assert str(credit) == "Fictional newsroom"
    assert str(internal) == "Private fictional minor"
    assert list(page.author_attributions) == [author]
    assert list(page.public_attributions) == [author, credit]

    conflicting_profile = AuthorProfile(
        display_name="Invalid fictional profile",
        slug="invalid-fictional-profile",
        user=get_user_model().objects.create_user(username="profile-user"),
        minor_contributor=contributor,
    )
    with pytest.raises(ValidationError, match="solo puede relacionarse"):
        conflicting_profile.full_clean()


@pytest.mark.django_db
def test_author_profile_generates_stable_spanish_slugs_and_suffixes() -> None:
    first = AuthorProfile.objects.create(display_name="María del Águila")
    second = AuthorProfile.objects.create(display_name="María del Águila")
    third = AuthorProfile.objects.create(display_name="María del Águila")

    assert [first.slug, second.slug, third.slug] == [
        "maria-del-aguila",
        "maria-del-aguila-2",
        "maria-del-aguila-3",
    ]
    first.display_name = "Nombre editorial posterior"
    first.save()
    first.refresh_from_db()
    assert first.slug == "maria-del-aguila"


@pytest.mark.django_db
def test_author_profile_generated_slug_reserves_space_for_collision_suffixes() -> None:
    max_length = AuthorProfile._meta.get_field("slug").max_length
    display_name = "a" * max_length
    profiles = [
        AuthorProfile.objects.create(display_name=display_name) for _ in range(10)
    ]

    assert profiles[0].slug == "a" * max_length
    assert profiles[1].slug == f"{'a' * (max_length - 2)}-2"
    assert profiles[-1].slug == f"{'a' * (max_length - 3)}-10"
    assert all(len(profile.slug) <= max_length for profile in profiles)

    profiles[0].display_name = "Nombre editorial posterior"
    profiles[0].save()
    profiles[0].refresh_from_db()

    assert profiles[0].slug == "a" * max_length


@pytest.mark.django_db
def test_author_profile_minor_email_constraint_rejects_bypass_writes() -> None:
    school = School.objects.create(name="Privacy constraint school", department_id="04")
    contributor = MinorContributor.objects.create(
        full_name="Privacy constraint minor",
        group=ContributorGroup.objects.create(
            name="Privacy constraint group", school=school
        ),
        age_band=MinorContributor.AgeBand.UNDER_14,
    )

    with transaction.atomic(), pytest.raises(IntegrityError):
        AuthorProfile.objects.create(
            display_name="Invalid direct-write profile",
            minor_contributor=contributor,
            email="minor@example.invalid",
        )

    minor_profile = AuthorProfile.objects.create(
        display_name="Valid minor profile", minor_contributor=contributor
    )
    adult_profile = AuthorProfile.objects.create(
        display_name="Valid adult profile", email="adult@example.invalid"
    )

    with transaction.atomic(), pytest.raises(IntegrityError):
        AuthorProfile.objects.filter(pk=minor_profile.pk).update(
            email="minor@example.invalid"
        )

    minor_profile.refresh_from_db()
    adult_profile.refresh_from_db()
    assert minor_profile.email == ""
    assert adult_profile.email == "adult@example.invalid"


@pytest.mark.django_db
def test_inactive_author_profile_is_only_valid_for_its_existing_attribution(
    home_page,
    section,
):
    page = create_news_page(home_page, section)
    historical_profile = AuthorProfile.objects.create(
        display_name="Historical fictional author",
        slug="historical-fictional-author",
    )
    another_inactive_profile = AuthorProfile.objects.create(
        display_name="Another inactive fictional author",
        slug="another-inactive-fictional-author",
        is_active=False,
    )
    attribution = NewsPageAttribution.objects.create(
        page=page,
        kind=NewsPageAttribution.Kind.AUTHOR,
        author_profile=historical_profile,
    )
    historical_profile.is_active = False
    historical_profile.save(update_fields=["is_active"])

    attribution.full_clean()
    replacement = NewsPageAttribution.objects.get(pk=attribution.pk)
    replacement.author_profile = another_inactive_profile
    new_attribution = NewsPageAttribution(
        page=page,
        kind=NewsPageAttribution.Kind.AUTHOR,
        author_profile=another_inactive_profile,
    )

    with pytest.raises(ValidationError, match="perfiles públicos de autor activos"):
        replacement.full_clean()
    with pytest.raises(ValidationError, match="perfiles públicos de autor activos"):
        new_attribution.full_clean()


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
