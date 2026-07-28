import datetime as dt
import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.home.models import HomePage
from apps.news.access import DIRECTOR_GROUP_NAME
from apps.news.models import NewsPage, NewsPagePublicCredit, NewsSection


class Command(BaseCommand):
    help = "Create the disposable fixture used by the browser regression."

    @transaction.atomic
    def handle(self, *args, **options):
        if not getattr(settings, "BROWSER_TESTING", False):
            raise CommandError(
                "This command is restricted to config.settings.browser_test."
            )

        username = os.environ["BROWSER_TEST_USERNAME"]
        password = os.environ["BROWSER_TEST_PASSWORD"]
        user, _ = get_user_model().objects.get_or_create(
            username=username,
            defaults={"email": f"{username}@example.invalid"},
        )
        user.set_password(password)
        user.is_active = True
        user.save(update_fields=["password", "is_active"])

        call_command(
            "bootstrap_mvp_access",
            director_usernames=[username],
            verbosity=0,
        )
        if not user.groups.filter(name=DIRECTOR_GROUP_NAME).exists():
            raise CommandError("The browser fixture user lacks the Director role.")

        home_pages = list(HomePage.objects.order_by("pk")[:2])
        if len(home_pages) != 1:
            raise CommandError("The browser fixture requires exactly one HomePage.")
        home = home_pages[0]
        section = NewsSection.objects.get(slug="politica")
        page = NewsPage.objects.filter(slug="nota-browser-epic3-006").first()
        if page is None:
            page = NewsPage(
                title="Nota browser EPIC3-006",
                slug="nota-browser-epic3-006",
                live=False,
                publication_date=dt.date(2026, 7, 28),
                section=section,
                coverage_province="Arequipa",
                coverage_district="Cercado",
                body=[
                    ("paragraph", "<p>Bloque anterior.</p>"),
                    ("paragraph", "<p>Bloque seleccionado.</p>"),
                    ("paragraph", ""),
                    ("paragraph", "<p>Bloque posterior.</p>"),
                ],
            )
            home.add_child(instance=page)

        page.title = "Nota browser EPIC3-006"
        page.live = False
        page.publication_date = dt.date(2026, 7, 28)
        page.section = section
        page.coverage_province = "Arequipa"
        page.coverage_district = "Cercado"
        page.body = [
            ("paragraph", "<p>Bloque anterior.</p>"),
            ("paragraph", "<p>Bloque seleccionado.</p>"),
            ("paragraph", ""),
            ("paragraph", "<p>Bloque posterior.</p>"),
        ]
        page.save()
        NewsPagePublicCredit.objects.update_or_create(
            page=page,
            sort_order=0,
            defaults={"display_name": "Redacción browser ficticia"},
        )
        page.save_revision(user=user)

        expected_page_id = int(os.environ["BROWSER_TEST_PAGE_ID"])
        if page.pk != expected_page_id:
            raise CommandError(
                "The disposable fixture page ID changed: "
                f"expected {expected_page_id}, found {page.pk}."
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Disposable browser fixture ready: page {page.pk}, user {username}."
            )
        )
