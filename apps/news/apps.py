from django.apps import AppConfig


class NewsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.news"
    label = "news"

    def ready(self) -> None:
        from . import search_signals  # noqa: F401
