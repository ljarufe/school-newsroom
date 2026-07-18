import importlib
import sys
from collections.abc import Iterator
from types import ModuleType

import environ
import pytest
from django.core.exceptions import ImproperlyConfigured
from pytest import MonkeyPatch

BASE_SETTINGS_MODULE = "config.settings.base"
PRODUCTION_SETTINGS_MODULE = "config.settings.production"
TEST_SETTINGS_MODULE = "config.settings.test"
SETTINGS_MODULES = (PRODUCTION_SETTINGS_MODULE, BASE_SETTINGS_MODULE)
TEST_SECRET_KEY = "test-only-production-secret-key"
TEST_DATABASE_URL = "postgresql://staging:dummy-password@db:5432/staging"
TEST_HOST = "staging.example.invalid"
TEST_ORIGIN = f"https://{TEST_HOST}"
VALID_PRODUCTION_ENVIRONMENT = {
    "DJANGO_SECRET_KEY": TEST_SECRET_KEY,
    "DATABASE_URL": TEST_DATABASE_URL,
    "DJANGO_ALLOWED_HOSTS": TEST_HOST,
    "DJANGO_CSRF_TRUSTED_ORIGINS": TEST_ORIGIN,
    "DJANGO_WAGTAILADMIN_BASE_URL": TEST_ORIGIN,
    "DJANGO_LOG_LEVEL": "INFO",
}
TEST_STATICFILES_STORAGE_BACKEND = (
    "django.contrib.staticfiles.storage.StaticFilesStorage"
)
WHITENOISE_MIDDLEWARE = "whitenoise.middleware.WhiteNoiseMiddleware"


def skip_read_env(*args: object, **kwargs: object) -> None:
    return None


@pytest.fixture
def isolated_settings_modules(monkeypatch: MonkeyPatch) -> Iterator[None]:
    saved_modules = {name: sys.modules.get(name) for name in SETTINGS_MODULES}

    for name in SETTINGS_MODULES:
        sys.modules.pop(name, None)

    monkeypatch.setattr(environ.Env, "read_env", skip_read_env)

    yield

    for name in SETTINGS_MODULES:
        sys.modules.pop(name, None)

    for name, module in saved_modules.items():
        if module is not None:
            sys.modules[name] = module


def import_production_settings() -> ModuleType:
    return importlib.import_module(PRODUCTION_SETTINGS_MODULE)


def import_base_settings() -> ModuleType:
    return importlib.import_module(BASE_SETTINGS_MODULE)


def import_test_settings() -> ModuleType:
    return importlib.import_module(TEST_SETTINGS_MODULE)


def configure_valid_production_environment(monkeypatch: MonkeyPatch) -> None:
    for name, value in VALID_PRODUCTION_ENVIRONMENT.items():
        monkeypatch.setenv(name, value)


def test_test_settings_disable_whitenoise_middleware() -> None:
    test_settings = import_test_settings()

    assert WHITENOISE_MIDDLEWARE not in test_settings.MIDDLEWARE


def test_test_settings_use_staticfiles_storage_without_manifest() -> None:
    test_settings = import_test_settings()

    assert (
        test_settings.STORAGES["staticfiles"]["BACKEND"]
        == TEST_STATICFILES_STORAGE_BACKEND
    )


@pytest.mark.usefixtures("isolated_settings_modules")
@pytest.mark.parametrize(
    "configured_secret",
    [None, "", "   ", "change-me", "replace-with-a-strong-random-secret"],
)
def test_production_rejects_invalid_secret_key(
    monkeypatch: MonkeyPatch,
    configured_secret: str | None,
) -> None:
    if configured_secret is None:
        monkeypatch.delenv("DJANGO_SECRET_KEY", raising=False)
    else:
        monkeypatch.setenv("DJANGO_SECRET_KEY", configured_secret)

    with pytest.raises(ImproperlyConfigured, match="DJANGO_SECRET_KEY"):
        import_production_settings()


@pytest.mark.usefixtures("isolated_settings_modules")
def test_production_accepts_configured_secret_key(
    monkeypatch: MonkeyPatch,
) -> None:
    configure_valid_production_environment(monkeypatch)

    production_settings = import_production_settings()

    assert production_settings.SECRET_KEY == TEST_SECRET_KEY


@pytest.mark.usefixtures("isolated_settings_modules")
@pytest.mark.parametrize(
    "missing_name",
    [
        "DATABASE_URL",
        "DJANGO_ALLOWED_HOSTS",
        "DJANGO_CSRF_TRUSTED_ORIGINS",
        "DJANGO_WAGTAILADMIN_BASE_URL",
        "DJANGO_LOG_LEVEL",
    ],
)
def test_production_rejects_missing_required_environment(
    monkeypatch: MonkeyPatch,
    missing_name: str,
) -> None:
    configure_valid_production_environment(monkeypatch)
    monkeypatch.delenv(missing_name)

    with pytest.raises(ImproperlyConfigured, match=missing_name):
        import_production_settings()


@pytest.mark.usefixtures("isolated_settings_modules")
def test_production_rejects_development_database_url(
    monkeypatch: MonkeyPatch,
) -> None:
    configure_valid_production_environment(monkeypatch)
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://school_newsroom:school_newsroom@db:5432/school_newsroom",
    )

    with pytest.raises(ImproperlyConfigured, match="non-development PostgreSQL"):
        import_production_settings()


@pytest.mark.usefixtures("isolated_settings_modules")
def test_production_rejects_database_placeholder(
    monkeypatch: MonkeyPatch,
) -> None:
    configure_valid_production_environment(monkeypatch)
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://staging:replace-with-password@db:5432/staging",
    )

    with pytest.raises(ImproperlyConfigured, match="non-development PostgreSQL"):
        import_production_settings()


@pytest.mark.usefixtures("isolated_settings_modules")
@pytest.mark.parametrize(
    "database_url",
    [
        "sqlite:////tmp/staging.sqlite3",
        "postgresql://staging@db:5432/staging",
        "postgresql://staging:dummy-password@db:5432/",
    ],
)
def test_production_rejects_incomplete_or_non_postgresql_database_url(
    monkeypatch: MonkeyPatch,
    database_url: str,
) -> None:
    configure_valid_production_environment(monkeypatch)
    monkeypatch.setenv("DATABASE_URL", database_url)

    with pytest.raises(ImproperlyConfigured, match="non-development PostgreSQL"):
        import_production_settings()


@pytest.mark.usefixtures("isolated_settings_modules")
@pytest.mark.parametrize(
    "configured_hosts",
    [
        "*",
        ".example.invalid",
        "staging.example.invalid:443",
        "https://staging.example.invalid",
        "staging.example.invalid/path",
    ],
)
def test_production_rejects_unsafe_allowed_hosts(
    monkeypatch: MonkeyPatch,
    configured_hosts: str,
) -> None:
    configure_valid_production_environment(monkeypatch)
    monkeypatch.setenv("DJANGO_ALLOWED_HOSTS", configured_hosts)

    with pytest.raises(ImproperlyConfigured, match="DJANGO_ALLOWED_HOSTS"):
        import_production_settings()


@pytest.mark.usefixtures("isolated_settings_modules")
@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("DJANGO_CSRF_TRUSTED_ORIGINS", "http://staging.example.invalid"),
        ("DJANGO_CSRF_TRUSTED_ORIGINS", "https://other.example.invalid"),
        ("DJANGO_WAGTAILADMIN_BASE_URL", "http://staging.example.invalid"),
        ("DJANGO_WAGTAILADMIN_BASE_URL", "https://other.example.invalid"),
        ("DJANGO_WAGTAILADMIN_BASE_URL", "https://staging.example.invalid:444"),
        ("DJANGO_WAGTAILADMIN_BASE_URL", "https://staging.example.invalid:bad"),
        ("DJANGO_WAGTAILADMIN_BASE_URL", "https://staging.example.invalid/admin/"),
    ],
)
def test_production_rejects_unsafe_https_urls(
    monkeypatch: MonkeyPatch,
    name: str,
    value: str,
) -> None:
    configure_valid_production_environment(monkeypatch)
    monkeypatch.setenv(name, value)

    with pytest.raises(ImproperlyConfigured, match=name):
        import_production_settings()


@pytest.mark.usefixtures("isolated_settings_modules")
def test_production_rejects_unsafe_log_level(monkeypatch: MonkeyPatch) -> None:
    configure_valid_production_environment(monkeypatch)
    monkeypatch.setenv("DJANGO_LOG_LEVEL", "DEBUG")

    with pytest.raises(ImproperlyConfigured, match="DJANGO_LOG_LEVEL"):
        import_production_settings()


@pytest.mark.usefixtures("isolated_settings_modules")
def test_production_accepts_complete_secure_contract(
    monkeypatch: MonkeyPatch,
) -> None:
    configure_valid_production_environment(monkeypatch)

    production_settings = import_production_settings()

    assert production_settings.DEBUG is False
    assert production_settings.ALLOWED_HOSTS == [TEST_HOST]
    assert production_settings.CSRF_TRUSTED_ORIGINS == [TEST_ORIGIN]
    assert production_settings.WAGTAILADMIN_BASE_URL == TEST_ORIGIN
    assert production_settings.DATABASES["default"]["HOST"] == "db"
    assert production_settings.SECURE_SSL_REDIRECT is True
    assert production_settings.SESSION_COOKIE_SECURE is True
    assert production_settings.CSRF_COOKIE_SECURE is True
    assert production_settings.SECURE_HSTS_INCLUDE_SUBDOMAINS is False
    assert production_settings.SECURE_HSTS_PRELOAD is False
    assert production_settings.LOGGING["root"]["level"] == "INFO"
    assert production_settings.FILE_UPLOAD_PERMISSIONS == 0o644
    assert production_settings.FILE_UPLOAD_DIRECTORY_PERMISSIONS == 0o755


@pytest.mark.usefixtures("isolated_settings_modules")
def test_seo_default_noindex_is_conservative(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv("SEO_DEFAULT_NOINDEX", raising=False)

    base_settings = import_base_settings()

    assert base_settings.SEO_DEFAULT_NOINDEX is True


@pytest.mark.usefixtures("isolated_settings_modules")
def test_seo_default_noindex_can_be_disabled(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("SEO_DEFAULT_NOINDEX", "false")

    base_settings = import_base_settings()

    assert base_settings.SEO_DEFAULT_NOINDEX is False


@pytest.mark.usefixtures("isolated_settings_modules")
@pytest.mark.parametrize(
    "database_url",
    [
        "postgresql://school_newsroom:school_newsroom@db/school_newsroom",
        "postgres://school_newsroom:school_newsroom@db:5432/school_newsroom",
        "postgresql://school_newsroom:school_newsroom@DB:5432/school_newsroom",
        ("postgresql://school%5Fnewsroom:school%5Fnewsroom@db:5432/school_newsroom"),
    ],
)
def test_production_rejects_equivalent_development_database_urls(
    monkeypatch: MonkeyPatch,
    database_url: str,
) -> None:
    configure_valid_production_environment(monkeypatch)
    monkeypatch.setenv("DATABASE_URL", database_url)

    with pytest.raises(
        ImproperlyConfigured,
        match="non-development PostgreSQL",
    ):
        import_production_settings()
