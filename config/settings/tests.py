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
SETTINGS_MODULES = (PRODUCTION_SETTINGS_MODULE, BASE_SETTINGS_MODULE)
TEST_SECRET_KEY = "test-only-production-secret-key"


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


@pytest.mark.usefixtures("isolated_settings_modules")
@pytest.mark.parametrize("configured_secret", [None, "", "   ", "change-me"])
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
    monkeypatch.setenv("DJANGO_SECRET_KEY", TEST_SECRET_KEY)

    production_settings = import_production_settings()

    assert production_settings.SECRET_KEY == TEST_SECRET_KEY
