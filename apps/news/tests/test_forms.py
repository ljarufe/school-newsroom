import datetime as dt
import json

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from wagtail.blocks.stream_block import StreamBlockValidationError
from wagtail.blocks.struct_block import StructBlockValidationError
from wagtail.images import get_image_model
from wagtail.models import Page

from apps.home.models import HomePage
from apps.news.forms import NewsPageAdminForm
from apps.news.models import (
    ContributorGroup,
    MinorContributor,
    NewsPage,
    NewsPagePublicCredit,
    NewsSection,
    School,
)

GIF_BYTES = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!"
    b"\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01"
    b"\x00\x00\x02\x02D\x01\x00;"
)

PARAGRAPH_CONTENTSTATE = json.dumps(
    {
        "blocks": [
            {
                "key": "reported",
                "type": "unstyled",
                "text": "Reported context",
                "depth": 0,
                "inlineStyleRanges": [],
                "entityRanges": [],
                "data": {},
            },
        ],
        "entityMap": {},
    },
)


@pytest.fixture
def home_page():
    home = HomePage.objects.first()
    if home is not None:
        return home

    root = Page.get_first_root_node()
    home = HomePage(title="Inicio", slug="inicio-form-tests")
    root.add_child(instance=home)
    return home


@pytest.fixture
def section():
    return NewsSection.objects.get(slug="politica")


def create_news_page(home_page, section, *, slug="form-news-existing"):
    page = NewsPage(
        title="Existing Form News",
        slug=slug,
        live=False,
        publication_date=dt.date(2026, 7, 1),
        summary="A concise public summary for a fictional news item.",
        body=[("paragraph", "<p>Reported context</p>")],
        section=section,
        coverage_province="Arequipa",
        coverage_district="Cercado",
    )
    home_page.add_child(instance=page)
    return page


def create_uploaded_image():
    image_model = get_image_model()
    return image_model.objects.create(
        title="Imagen editorial genérica",
        file=SimpleUploadedFile(
            "admin-body.gif",
            GIF_BYTES,
            content_type="image/gif",
        ),
    )


def admin_form_data(
    section,
    *,
    title="Form News",
    slug="form-news",
    public_credits=None,
    deleted_credit_ids=None,
    internal_contributor_ids=None,
    contains_identifiable_minors=False,
    authorizations_verified=False,
    sensitive_content=False,
    body_block=None,
):
    public_credits = public_credits or []
    deleted_credit_ids = deleted_credit_ids or []
    internal_contributor_ids = internal_contributor_ids or []
    body_block = body_block or {
        "type": "paragraph",
        "value": PARAGRAPH_CONTENTSTATE,
    }
    data = {
        "title": title,
        "slug": slug,
        "publication_date": "2026-07-01",
        "summary": "A concise public summary for a fictional news item.",
        "body-count": "1",
        "body-0-deleted": "",
        "body-0-order": "0",
        "body-0-type": body_block["type"],
        "body-0-id": "11111111-1111-4111-8111-111111111111",
        "section": str(section.pk),
        "school": "",
        "coverage_province": "Arequipa",
        "coverage_district": "Cercado",
        "featured_image": "",
        "tags": "",
        "seo_title": "",
        "search_description": "",
        "show_in_menus": "",
        "go_live_at": "",
        "expire_at": "",
        "public_credits-TOTAL_FORMS": str(
            len(public_credits) + len(deleted_credit_ids),
        ),
        "public_credits-INITIAL_FORMS": str(len(deleted_credit_ids)),
        "public_credits-MIN_NUM_FORMS": "0",
        "public_credits-MAX_NUM_FORMS": "1000",
        "internal_contributors-TOTAL_FORMS": str(len(internal_contributor_ids)),
        "internal_contributors-INITIAL_FORMS": "0",
        "internal_contributors-MIN_NUM_FORMS": "0",
        "internal_contributors-MAX_NUM_FORMS": "1000",
    }

    if body_block["type"] == "article_image":
        data.update(
            {
                "body-0-value-image": body_block.get("image", ""),
                "body-0-value-caption": body_block.get("caption", ""),
                "body-0-value-alt_text": body_block.get("alt_text", ""),
                "body-0-value-credit": body_block.get("credit", ""),
            },
        )
    else:
        data["body-0-value"] = body_block["value"]

    if contains_identifiable_minors:
        data["contains_identifiable_minors"] = "on"
    if authorizations_verified:
        data["minor_publication_authorizations_verified"] = "on"
    if sensitive_content:
        data["sensitive_content"] = "on"

    for index, credit_id in enumerate(deleted_credit_ids):
        data[f"public_credits-{index}-id"] = str(credit_id)
        data[f"public_credits-{index}-display_name"] = "Deleted public credit"
        data[f"public_credits-{index}-ORDER"] = str(index)
        data[f"public_credits-{index}-DELETE"] = "on"

    offset = len(deleted_credit_ids)
    for index, display_name in enumerate(public_credits, start=offset):
        data[f"public_credits-{index}-id"] = ""
        data[f"public_credits-{index}-display_name"] = display_name
        data[f"public_credits-{index}-ORDER"] = str(index)

    for index, contributor_id in enumerate(internal_contributor_ids):
        data[f"internal_contributors-{index}-id"] = ""
        data[f"internal_contributors-{index}-contributor"] = str(contributor_id)
        data[f"internal_contributors-{index}-ORDER"] = str(index)

    return data


def make_admin_form(home_page, section, *, instance=None, **data_kwargs):
    form_class = NewsPage.get_edit_handler().get_form_class()
    if instance is None:
        instance = NewsPage()
    data = admin_form_data(section, **data_kwargs)
    return form_class(data=data, instance=instance, parent_page=home_page)


@pytest.mark.django_db
def test_draft_validation_allows_missing_public_credit(home_page, section) -> None:
    form = make_admin_form(
        home_page,
        section,
        slug="draft-without-public-credit",
    )

    form.defer_required_fields()

    assert form.is_valid()
    assert form.is_deferred_validation


@pytest.mark.django_db
def test_empty_seo_fields_remain_non_blocking_for_full_validation(
    home_page,
    section,
) -> None:
    form = make_admin_form(
        home_page,
        section,
        slug="publish-without-seo-recommendations",
        public_credits=["Fictional school newsroom team"],
    )

    assert form.is_valid()
    assert form.cleaned_data["focus_keyphrase"] == ""
    assert form.cleaned_data["canonical_url"] == ""
    assert form.cleaned_data["seo_noindex"] is False


@pytest.mark.django_db
def test_draft_validation_allows_incomplete_article_image_block(
    home_page,
    section,
) -> None:
    form = make_admin_form(
        home_page,
        section,
        slug="draft-with-incomplete-article-image",
        body_block={
            "type": "article_image",
            "image": "",
            "caption": "",
            "alt_text": "",
            "credit": "",
        },
    )

    form.defer_required_fields()

    assert form.is_valid()
    assert form.is_deferred_validation


@pytest.mark.django_db
def test_full_validation_requires_article_image_caption_and_alt(
    home_page,
    section,
    settings,
    tmp_path,
) -> None:
    settings.MEDIA_ROOT = tmp_path
    image = create_uploaded_image()
    form = make_admin_form(
        home_page,
        section,
        slug="full-with-incomplete-article-image",
        public_credits=["Fictional school newsroom team"],
        body_block={
            "type": "article_image",
            "image": str(image.pk),
            "caption": "   ",
            "alt_text": "   ",
            "credit": "",
        },
    )

    assert not form.is_valid()
    assert "body" in form.errors
    assert NewsPageAdminForm.BODY_BLOCK_ERROR in str(form.errors["body"])
    assert "StreamBlock" not in str(form.errors["body"])

    body_error = form.errors.as_data()["body"][0]
    assert isinstance(body_error, StreamBlockValidationError)
    article_image_error = body_error.block_errors[0]
    assert isinstance(article_image_error, StructBlockValidationError)
    assert set(article_image_error.block_errors) == {"caption", "alt_text"}


@pytest.mark.django_db
def test_full_validation_requires_public_credit(home_page, section) -> None:
    form = make_admin_form(
        home_page,
        section,
        slug="full-without-public-credit",
    )

    assert not form.is_valid()
    assert NewsPageAdminForm.PUBLIC_CREDIT_REQUIRED_ERROR in str(
        form.errors["__all__"],
    )


@pytest.mark.django_db
def test_full_validation_accepts_new_unsaved_inline_public_credit(
    home_page,
    section,
) -> None:
    form = make_admin_form(
        home_page,
        section,
        slug="full-with-new-public-credit",
        public_credits=["Fictional school newsroom team"],
    )

    assert form.is_valid()
    assert (
        form.formsets["public_credits"].forms[0].cleaned_data["display_name"]
        == "Fictional school newsroom team"
    )


@pytest.mark.django_db
def test_full_validation_ignores_deleted_public_credit(home_page, section) -> None:
    page = create_news_page(home_page, section, slug="deleted-credit-page")
    public_credit = NewsPagePublicCredit.objects.create(
        page=page,
        display_name="Existing public credit",
        sort_order=0,
    )
    form = make_admin_form(
        home_page,
        section,
        instance=page,
        title="Existing Form News",
        slug="deleted-credit-page",
        deleted_credit_ids=[public_credit.pk],
    )

    assert not form.is_valid()
    assert NewsPageAdminForm.PUBLIC_CREDIT_REQUIRED_ERROR in str(
        form.errors["__all__"],
    )


@pytest.mark.django_db
def test_full_validation_ignores_empty_inline_public_credit(
    home_page,
    section,
) -> None:
    form = make_admin_form(
        home_page,
        section,
        slug="full-with-empty-public-credit",
        public_credits=[""],
    )

    assert not form.is_valid()
    assert NewsPageAdminForm.PUBLIC_CREDIT_REQUIRED_ERROR in str(
        form.errors["__all__"],
    )


@pytest.mark.django_db
def test_identifiable_minors_require_authorization_checkbox(
    home_page,
    section,
) -> None:
    form = make_admin_form(
        home_page,
        section,
        slug="identifiable-without-authorization",
        public_credits=["Fictional school newsroom team"],
        contains_identifiable_minors=True,
    )

    assert not form.is_valid()
    assert NewsPageAdminForm.MINOR_AUTHORIZATION_REQUIRED_ERROR in str(
        form.errors["minor_publication_authorizations_verified"],
    )


@pytest.mark.django_db
def test_identifiable_minors_with_authorization_and_public_credit_are_valid(
    home_page,
    section,
) -> None:
    form = make_admin_form(
        home_page,
        section,
        slug="identifiable-with-authorization",
        public_credits=["Fictional school newsroom team"],
        contains_identifiable_minors=True,
        authorizations_verified=True,
    )

    assert form.is_valid()


@pytest.mark.django_db
def test_authorization_checkbox_not_required_without_identifiable_minors(
    home_page,
    section,
) -> None:
    form = make_admin_form(
        home_page,
        section,
        slug="not-identifiable-without-authorization",
        public_credits=["Fictional school newsroom team"],
        contains_identifiable_minors=False,
        authorizations_verified=False,
    )

    assert form.is_valid()


@pytest.mark.django_db
def test_sensitive_content_does_not_block_when_other_rules_pass(
    home_page,
    section,
) -> None:
    form = make_admin_form(
        home_page,
        section,
        slug="sensitive-content-valid",
        public_credits=["Fictional school newsroom team"],
        sensitive_content=True,
    )

    assert form.is_valid()


@pytest.mark.django_db
def test_internal_contributor_does_not_require_authorization_by_itself(
    home_page,
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
    form = make_admin_form(
        home_page,
        section,
        slug="internal-contributor-without-authorization",
        public_credits=["Fictional school newsroom team"],
        internal_contributor_ids=[contributor.pk],
        contains_identifiable_minors=False,
        authorizations_verified=False,
    )

    assert form.is_valid()


@pytest.mark.django_db
def test_generated_page_form_rejects_duplicate_internal_contributors(
    home_page,
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
    form = make_admin_form(
        home_page,
        section,
        slug="duplicate-internal-contributor",
        public_credits=["Fictional school newsroom team"],
        internal_contributor_ids=[contributor.pk, contributor.pk],
    )

    assert not form.is_valid()

    formset = form.formsets["internal_contributors"]
    assert not formset.is_valid()
    non_form_messages = [
        message
        for error in formset.non_form_errors().as_data()
        for message in error.messages
    ]

    assert any(
        "duplicado" in message and "page" in message and "contributor" in message
        for message in non_form_messages
    )
    assert formset.forms[0].errors.as_data() == {}
    assert formset.forms[1].non_field_errors()
