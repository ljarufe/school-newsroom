import pytest
from django.conf import settings
from django.test import Client


def test_django_settings_load() -> None:
    assert settings.WAGTAIL_SITE_NAME == "School Newsroom"


@pytest.mark.django_db
def test_wagtail_admin_login_loads() -> None:
    response = Client().get("/admin/", follow=True)
    assert response.status_code == 200
    assert response.redirect_chain == [("/admin/login/?next=/admin/", 302)]
