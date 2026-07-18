from urllib.parse import unquote, urlsplit

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403


def required_environment_value(name: str) -> str:
    value = env.ENVIRON.get(name, "")  # noqa: F405
    if not value.strip():
        raise ImproperlyConfigured(f"{name} must be configured for production.")
    return value.strip()


def validate_host(host: str) -> None:
    if (
        not host
        or host == "*"
        or host.startswith(".")
        or "://" in host
        or ":" in host
        or "@" in host
        or "/" in host
        or any(character.isspace() for character in host)
    ):
        raise ImproperlyConfigured(
            "DJANGO_ALLOWED_HOSTS must contain bare explicit hostnames."
        )


def validate_https_url(name: str, value: str, allowed_hosts: list[str]) -> None:
    parsed = urlsplit(value)
    try:
        port = parsed.port
    except ValueError as error:
        raise ImproperlyConfigured(
            f"{name} must be an HTTPS origin for an allowed host."
        ) from error

    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or port not in {None, 443}
        or parsed.netloc not in {parsed.hostname, f"{parsed.hostname}:443"}
        or parsed.username
        or parsed.password
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
        or parsed.hostname not in allowed_hosts
    ):
        raise ImproperlyConfigured(
            f"{name} must be an HTTPS origin for an allowed host."
        )


def postgresql_connection_identity(
    database_url: str,
) -> tuple[str, str, str, int, str]:
    parsed = urlsplit(database_url)

    try:
        port = parsed.port or 5432
    except ValueError as error:
        raise ImproperlyConfigured(
            "DATABASE_URL must be a complete non-development PostgreSQL URL "
            "in production."
        ) from error

    return (
        unquote(parsed.username or ""),
        unquote(parsed.password or ""),
        (parsed.hostname or "").lower(),
        port,
        unquote(parsed.path.lstrip("/")),
    )


DEBUG = False
SECRET_KEY = env("DJANGO_SECRET_KEY")  # noqa: F405
if not SECRET_KEY.strip() or SECRET_KEY.strip() in {
    "change-me",
    "replace-with-a-strong-random-secret",
}:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be configured for production.")

database_url = required_environment_value("DATABASE_URL")
parsed_database_url = urlsplit(database_url)
if (
    postgresql_connection_identity(database_url)
    == postgresql_connection_identity(DEFAULT_DATABASE_URL)  # noqa: F405
    or "replace-with-" in database_url
    or parsed_database_url.scheme not in {"postgres", "postgresql"}
    or not parsed_database_url.hostname
    or not parsed_database_url.username
    or not parsed_database_url.password
    or parsed_database_url.path in {"", "/"}
):
    raise ImproperlyConfigured(
        "DATABASE_URL must be a complete non-development PostgreSQL URL in production."
    )
DATABASES = {"default": env.db("DATABASE_URL")}  # noqa: F405

required_environment_value("DJANGO_ALLOWED_HOSTS")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")  # noqa: F405
if not ALLOWED_HOSTS or ALLOWED_HOSTS == ["localhost", "127.0.0.1"]:
    raise ImproperlyConfigured(
        "DJANGO_ALLOWED_HOSTS must be configured for the production hostname."
    )
for allowed_host in ALLOWED_HOSTS:
    validate_host(allowed_host)

required_environment_value("DJANGO_CSRF_TRUSTED_ORIGINS")
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS")  # noqa: F405
if not CSRF_TRUSTED_ORIGINS:
    raise ImproperlyConfigured(
        "DJANGO_CSRF_TRUSTED_ORIGINS must include the production HTTPS origin."
    )
for trusted_origin in CSRF_TRUSTED_ORIGINS:
    validate_https_url(
        "DJANGO_CSRF_TRUSTED_ORIGINS",
        trusted_origin,
        ALLOWED_HOSTS,
    )

WAGTAILADMIN_BASE_URL = required_environment_value("DJANGO_WAGTAILADMIN_BASE_URL")
validate_https_url(
    "DJANGO_WAGTAILADMIN_BASE_URL",
    WAGTAILADMIN_BASE_URL,
    ALLOWED_HOSTS,
)

LOG_LEVEL = required_environment_value("DJANGO_LOG_LEVEL").upper()
if LOG_LEVEL not in {"INFO", "WARNING", "ERROR"}:
    raise ImproperlyConfigured(
        "DJANGO_LOG_LEVEL must be one of INFO, WARNING, or ERROR."
    )

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "console": {
            "format": "{asctime} {levelname} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "console",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
}

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)  # noqa: F405
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = env.int("DJANGO_SECURE_HSTS_SECONDS", default=3600)  # noqa: F405
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(  # noqa: F405
    "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS",
    default=False,
)
SECURE_HSTS_PRELOAD = env.bool("DJANGO_SECURE_HSTS_PRELOAD", default=False)  # noqa: F405

FILE_UPLOAD_PERMISSIONS = 0o644
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o755
