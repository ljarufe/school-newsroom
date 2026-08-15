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
from apps.news.models import (
    NewsPage,
    NewsPagePublicCredit,
    NewsPageSection,
    NewsSection,
    School,
)


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
        school_department_only, _ = School.objects.update_or_create(
            name="Colegio browser departamental ficticio",
            defaults={"department_id": "04", "district_id": None},
        )
        school_with_district, _ = School.objects.update_or_create(
            name="Colegio browser distrital ficticio",
            defaults={"department_id": "04", "district_id": "040103"},
        )
        School.objects.update_or_create(
            name="Colegio browser Lima ficticio",
            defaults={"department_id": "15", "district_id": "150101"},
        )
        page = NewsPage.objects.filter(slug="nota-browser-epic3-006").first()
        if page is None:
            page = NewsPage(
                title="Nota browser EPIC3-006",
                slug="nota-browser-epic3-006",
                live=False,
                publication_date=dt.date(2026, 7, 28),
                coverage_department_id="04",
                coverage_district_id="040101",
                body=[
                    ("paragraph", "<p>Bloque anterior.</p>"),
                    ("paragraph", "<p>Bloque seleccionado.</p>"),
                    ("paragraph", ""),
                    ("paragraph", "<p>Bloque posterior.</p>"),
                ],
                school=school_with_district,
            )
            home.add_child(instance=page)

        page.title = "Nota browser EPIC3-006"
        page.live = False
        page.publication_date = dt.date(2026, 7, 28)
        page.coverage_department_id = "04"
        page.coverage_district_id = "040101"
        page.body = [
            ("paragraph", "<p>Bloque anterior.</p>"),
            ("paragraph", "<p>Bloque seleccionado.</p>"),
            ("paragraph", ""),
            ("paragraph", "<p>Bloque posterior.</p>"),
        ]
        page.school = school_with_district
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
            coverage_department_id="04",
            coverage_district_id="040101",
            body=[
                (
                    "paragraph",
                    "<p>Además, el borrador ficticio fue revisado por dos "
                    "editoras adultas. El equipo comparó fuentes inventadas. "
                    "La redacción ordenó los datos del ejercicio. El grupo "
                    "explicó el contexto escolar imaginario. La editora guardó "
                    "la práctica sin publicar información real.</p>",
                )
            ],
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

        public_share_page = NewsPage(
            title='Feria ficticia "A & B" comparte aprendizajes',
            slug="nota-publica-browser-epic6-003",
            live=True,
            publication_date=dt.date(2026, 8, 4),
            body=[
                (
                    "paragraph",
                    "<h2>Aprendizajes del taller ficticio</h2>"
                    "<p>Una comunidad ficticia comparte una práctica escolar "
                    "sin incluir información real de menores.</p>",
                )
            ],
            og_title='Aprendizajes <ficticios> "A & B"',
            og_description=(
                "Una comunidad ficticia comparte aprendizajes de un taller "
                "escolar sin incluir datos reales de menores."
            ),
            canonical_url=(
                "https://example.org/noticia-ficticia"
                "?origen=school-newsroom&grupo=A%20%26%20B"
            ),
            seo_noindex=True,
            school=school_department_only,
            coverage_department_id="15",
            coverage_district_id="150101",
        )
        home.add_child(instance=public_share_page)
        public_share_page.tags.add("browser-share")
        public_share_page.save()
        public_politics = NewsSection.objects.get(slug="politica")
        public_local_politics = NewsSection.objects.get(slug="politica-local")
        NewsPageSection.objects.update_or_create(
            page=public_share_page,
            section=public_politics,
        )
        NewsPageSection.objects.update_or_create(
            page=public_share_page,
            section=public_local_politics,
        )
        NewsPagePublicCredit.objects.create(
            page=public_share_page,
            sort_order=0,
            display_name="Redacción pública ficticia",
        )
        public_share_page.save_revision(user=user)

        expected_public_share_page_id = int(
            os.environ["BROWSER_TEST_PUBLIC_SHARE_PAGE_ID"]
        )
        if public_share_page.pk != expected_public_share_page_id:
            raise CommandError(
                "The disposable public share fixture page ID changed: "
                f"expected {expected_public_share_page_id}, "
                f"found {public_share_page.pk}."
            )

        archive_section = NewsSection.objects.get(slug="cultura")
        archive_subsection = NewsSection.objects.get(slug="musica")
        for index in range(11):
            slug = f"archivo-browser-epic6-002-{index}"
            archive_page = NewsPage.objects.filter(slug=slug).first()
            if archive_page is None:
                archive_page = NewsPage(
                    title=f"Archivo browser {index}",
                    slug=slug,
                    live=True,
                    publication_date=dt.date(2026, 8, index + 1),
                    coverage_department_id=("15" if index == 1 else "04"),
                    coverage_district_id=(
                        None if index == 0 else "150101" if index == 1 else "040101"
                    ),
                    body=[("paragraph", "<p>Archivo browser para búsqueda.</p>")],
                )
                home.add_child(instance=archive_page)
            archive_page.title = f"Archivo browser {index}"
            archive_page.live = True
            archive_page.publication_date = dt.date(2026, 8, index + 1)
            archive_page.coverage_department_id = "15" if index == 1 else "04"
            archive_page.coverage_district_id = (
                None if index == 0 else "150101" if index == 1 else "040101"
            )
            archive_page.body = [("paragraph", "<p>Archivo browser para búsqueda.</p>")]
            archive_page.save()
            NewsPageSection.objects.update_or_create(
                page=archive_page,
                section=archive_section,
            )
            if index == 0:
                NewsPageSection.objects.update_or_create(
                    page=archive_page,
                    section=archive_subsection,
                )
            archive_page.tags.add("archivo-browser")
            archive_page.save()

        self.stdout.write(
            self.style.SUCCESS(
                "Disposable browser fixtures ready: "
                f"editor page {page.pk}, SEO page {seo_page.pk}, "
                f"public share page {public_share_page.pk}; 11 archive pages."
            )
        )
