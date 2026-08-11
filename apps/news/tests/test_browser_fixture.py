import io

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import override_settings
from wagtail.models import Collection, Locale, Page

from apps.home.models import HomePage
from apps.news.access import DIRECTOR_GROUP_NAME, SEO_CURATOR_GROUP_NAME
from apps.news.models import NewsPage, NewsPagePublicCredit

pytestmark = pytest.mark.django_db


def next_page_id() -> int:
    with connection.cursor() as cursor:
        cursor.execute("SELECT last_value, is_called FROM wagtailcore_page_id_seq")
        last_value, is_called = cursor.fetchone()
    return last_value + int(is_called)


def test_browser_fixture_command_rejects_non_browser_settings() -> None:
    with pytest.raises(
        CommandError,
        match="restricted to config.settings.browser_test",
    ):
        call_command("setup_browser_test")


@override_settings(BROWSER_TESTING=True)
def test_browser_fixture_command_creates_the_disposable_regression_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    Locale.objects.get_or_create(language_code="es")
    if Collection.get_first_root_node() is None:
        Collection.add_root(instance=Collection(name="Root"))
    root = Page.get_first_root_node()
    if root is None:
        root = Page.add_root(instance=Page(title="Root", slug="root"))
    if not HomePage.objects.exists():
        root.add_child(
            instance=HomePage(title="Browser fixture home", slug="browser-fixture-home")
        )
    existing_editor_page = Page._base_manager.filter(
        slug="nota-browser-epic3-006"
    ).first()
    first_new_page_id = next_page_id()
    expected_editor_page_id = (
        existing_editor_page.pk if existing_editor_page else first_new_page_id
    )
    expected_seo_page_id = first_new_page_id + int(existing_editor_page is None)
    expected_public_share_page_id = expected_seo_page_id + 1
    fixture_environment = {
        "BROWSER_TEST_USERNAME": "browser-director",
        "BROWSER_TEST_PASSWORD": "browser-director-password",
        "BROWSER_TEST_SEO_USERNAME": "browser-seo",
        "BROWSER_TEST_SEO_PASSWORD": "browser-seo-password",
        "BROWSER_TEST_PAGE_ID": str(expected_editor_page_id),
        "BROWSER_TEST_SEO_PAGE_ID": str(expected_seo_page_id),
        "BROWSER_TEST_PUBLIC_SHARE_PAGE_ID": str(expected_public_share_page_id),
    }
    for name, value in fixture_environment.items():
        monkeypatch.setenv(name, value)

    output = io.StringIO()
    call_command("setup_browser_test", stdout=output)

    director = get_user_model().objects.get(username="browser-director")
    seo_curator = get_user_model().objects.get(username="browser-seo")
    editor_page = NewsPage.objects.filter(slug="nota-browser-epic3-006").first()
    seo_page = (
        NewsPage.objects.filter(slug="nota-browser-epic5-009").order_by("-pk").first()
    )
    public_share_page = (
        NewsPage.objects.filter(slug="nota-publica-browser-epic6-003")
        .order_by("-pk")
        .first()
    )

    assert director.check_password("browser-director-password")
    assert director.groups.filter(name=DIRECTOR_GROUP_NAME).exists()
    assert seo_curator.check_password("browser-seo-password")
    assert seo_curator.groups.filter(name=SEO_CURATOR_GROUP_NAME).exists()
    assert editor_page is not None
    assert editor_page.pk == expected_editor_page_id
    assert editor_page.live is False
    assert editor_page.body[2].value.source == ""
    assert seo_page is not None
    assert seo_page.pk == expected_seo_page_id
    assert seo_page.get_workflow() is not None
    assert public_share_page is not None
    assert public_share_page.pk == expected_public_share_page_id
    assert public_share_page.live is True
    assert public_share_page.seo_noindex is True
    assert list(public_share_page.tags.names()) == ["browser-share"]
    assert NewsPagePublicCredit.objects.filter(
        page=public_share_page,
        display_name="Redacción pública ficticia",
    ).exists()
    assert "Disposable browser fixtures ready" in output.getvalue()
