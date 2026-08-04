import datetime as dt
import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.home.models import HomePage
from apps.news.access import (
    DIRECTOR_GROUP_NAME,
    SEO_CURATOR_GROUP_NAME,
)
from apps.news.models import NewsPage, NewsPagePublicCredit


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

        seo_username = os.environ["BROWSER_TEST_SEO_USERNAME"]
        seo_password = os.environ["BROWSER_TEST_SEO_PASSWORD"]
        seo_user, _ = get_user_model().objects.get_or_create(
            username=seo_username,
            defaults={"email": f"{seo_username}@example.invalid"},
        )
        seo_user.set_password(seo_password)
        seo_user.is_active = True
        seo_user.save(update_fields=["password", "is_active"])

        call_command(
            "bootstrap_mvp_access",
            director_usernames=[username],
            seo_usernames=[seo_username],
            verbosity=0,
        )
        if not user.groups.filter(name=DIRECTOR_GROUP_NAME).exists():
            raise CommandError("The browser fixture user lacks the Director role.")
        if not seo_user.groups.filter(name=SEO_CURATOR_GROUP_NAME).exists():
            raise CommandError(
                "The browser SEO fixture user lacks the Curador SEO role."
            )

        home_pages = list(HomePage.objects.order_by("pk")[:2])
        if len(home_pages) != 1:
            raise CommandError("The browser fixture requires exactly one HomePage.")
        home = home_pages[0]
        page = NewsPage.objects.filter(slug="nota-browser-epic3-006").first()
        if page is None:
            page = NewsPage(
                title="Nota browser EPIC3-006",
                slug="nota-browser-epic3-006",
                live=False,
                publication_date=dt.date(2026, 7, 28),
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
        page.coverage_province = "Arequipa"
        page.coverage_district = "Cercado"
        page.body = [
            ("paragraph", "<p>Bloque anterior.</p>"),
            ("paragraph", "<p>Bloque seleccionado.</p>"),
            ("paragraph", ""),
            ("paragraph", "<p>Bloque posterior.</p>"),
        ]
        page.save()
        page.section_assignments.all().delete()
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

        seo_page = NewsPage(
            title="Nota browser EPIC5-009",
            slug="nota-browser-epic5-009",
            live=False,
            publication_date=dt.date(2026, 8, 3),
            coverage_province="Arequipa",
            coverage_district="Cercado",
            body=[("paragraph", "<p>Contenido ficticio para el análisis SEO.</p>")],
            focus_keyphrase="periodismo escolar",
            seo_title="Periodismo escolar en una redacción local",
            search_description=(
                "Una investigación escolar fortalece la redacción local. Las "
                "noticias escolares circulan mediante contenido ficticio preparado "
                "para esta prueba."
            ),
        )
        home.add_child(instance=seo_page)
        NewsPagePublicCredit.objects.create(
            page=seo_page,
            sort_order=0,
            display_name="Redacción browser ficticia",
        )
        seo_page.save_revision(user=user)
        seo_page.get_workflow().start(seo_page, user)

        expected_seo_page_id = int(os.environ["BROWSER_TEST_SEO_PAGE_ID"])
        if seo_page.pk != expected_seo_page_id:
            raise CommandError(
                "The disposable SEO fixture page ID changed: "
                f"expected {expected_seo_page_id}, found {seo_page.pk}."
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Disposable browser fixtures ready: "
                f"editor page {page.pk}, SEO page {seo_page.pk}."
            )
        )
