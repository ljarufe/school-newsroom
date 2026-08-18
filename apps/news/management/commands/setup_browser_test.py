import datetime as dt
import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from wagtail.images import get_image_model

from apps.home.models import HomePage
from apps.news.access import (
    DIRECTOR_GROUP_NAME,
    SEO_CURATOR_GROUP_NAME,
)
from apps.news.models import (
    AuthorProfile,
    ContributorGroup,
    MinorContributor,
    NewsPage,
    NewsPageAttribution,
    NewsPageSection,
    NewsSection,
    School,
)

GIF_BYTES = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!"
    b"\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01"
    b"\x00\x00\x02\x02D\x01\x00;"
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
        user.first_name = "Admin"
        user.last_name = "Director"
        user.save(update_fields=["password", "is_active", "first_name", "last_name"])

        seo_username = os.environ["BROWSER_TEST_SEO_USERNAME"]
        seo_password = os.environ["BROWSER_TEST_SEO_PASSWORD"]
        seo_user, _ = get_user_model().objects.get_or_create(
            username=seo_username,
            defaults={"email": f"{seo_username}@example.invalid"},
        )
        seo_user.set_password(seo_password)
        seo_user.is_active = True
        seo_user.first_name = "Admin"
        seo_user.last_name = "SEO"
        seo_user.save(
            update_fields=["password", "is_active", "first_name", "last_name"]
        )

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
        browser_author, _ = AuthorProfile.objects.update_or_create(
            slug="autora-browser-ficticia",
            defaults={
                "display_name": "Autora browser ficticia",
                "bio": "Biografía pública ficticia para la prueba browser.",
                "email": "autora.browser@example.invalid",
                "position": "Periodista",
                "work_url": "https://example.invalid/autora-browser",
                "is_active": True,
            },
        )
        browser_group, _ = ContributorGroup.objects.update_or_create(
            name="Grupo browser ficticio",
            school=school_with_district,
        )
        browser_minor, _ = MinorContributor.objects.update_or_create(
            full_name="Colaborador interno browser ficticio",
            defaults={
                "group": browser_group,
                "age_band": MinorContributor.AgeBand.FROM_14_TO_17,
            },
        )
        browser_minor_profile, _ = AuthorProfile.objects.update_or_create(
            slug="autor-menor-browser-ficticio",
            defaults={
                "display_name": "Autor menor browser ficticio",
                "bio": "Biografía pública ficticia de autor menor.",
                "minor_contributor": browser_minor,
                "is_active": True,
            },
        )
        browser_minimal_author, _ = AuthorProfile.objects.update_or_create(
            slug="autora-minima-browser-ficticia",
            defaults={
                "display_name": "Autora mínima browser ficticia",
                "is_active": True,
            },
        )
        image_model = get_image_model()
        if not image_model.objects.filter(title="Imagen browser ficticia").exists():
            image_model.objects.create(
                title="Imagen browser ficticia",
                file=SimpleUploadedFile(
                    "imagen-browser-ficticia.gif",
                    GIF_BYTES,
                    content_type="image/gif",
                ),
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
        page.attributions.all().delete()
        AuthorProfile.objects.filter(slug="autora-creada-browser-ficticia").delete()
        School.objects.filter(
            name__in=("Colegio creado browser", "Colegio editado browser")
        ).delete()
        NewsPageAttribution.objects.create(
            page=page,
            kind=NewsPageAttribution.Kind.PUBLIC_CREDIT,
            sort_order=0,
            display_name="Redacción browser ficticia",
        )
        page.save_revision(user=user)

        expected_page_id = int(os.environ["BROWSER_TEST_PAGE_ID"])
        if page.pk != expected_page_id:
            raise CommandError(
                "The disposable fixture page ID changed: "
                f"expected {expected_page_id}, found {page.pk}."
            )

        seo_page = NewsPage.objects.filter(slug="nota-browser-epic5-009").first()
        if seo_page is None:
            seo_page = NewsPage(
                title="Nota browser EPIC5-009",
                slug="nota-browser-epic5-009",
                live=False,
                publication_date=dt.date(2026, 8, 3),
                coverage_department_id="04",
                coverage_district_id="040101",
            )
            home.add_child(instance=seo_page)
        seo_page.title = "Nota browser EPIC5-009"
        seo_page.live = False
        seo_page.publication_date = dt.date(2026, 8, 3)
        seo_page.coverage_department_id = "04"
        seo_page.coverage_district_id = "040101"
        seo_page.body = [
            (
                "paragraph",
                "<p>Además, el borrador ficticio fue revisado por dos "
                "editoras adultas. El equipo comparó fuentes inventadas. "
                "La redacción ordenó los datos del ejercicio. El grupo "
                "explicó el contexto escolar imaginario. La editora guardó "
                "la práctica sin publicar información real.</p>",
            )
        ]
        seo_page.focus_keyphrase = "periodismo escolar"
        seo_page.seo_title = "Periodismo escolar en una redacción local"
        seo_page.search_description = (
            "Una investigación escolar fortalece la redacción local. Las "
            "noticias escolares circulan mediante contenido ficticio preparado "
            "para esta prueba."
        )
        seo_page.save()
        seo_page.attributions.all().delete()
        NewsPageAttribution.objects.create(
            page=seo_page,
            kind=NewsPageAttribution.Kind.PUBLIC_CREDIT,
            sort_order=0,
            display_name="Redacción browser ficticia",
        )
        seo_page.save_revision(user=user)
        if seo_page.current_workflow_state is None:
            seo_page.get_workflow().start(seo_page, user)

        expected_seo_page_id = int(os.environ["BROWSER_TEST_SEO_PAGE_ID"])
        if seo_page.pk != expected_seo_page_id:
            raise CommandError(
                "The disposable SEO fixture page ID changed: "
                f"expected {expected_seo_page_id}, found {seo_page.pk}."
            )

        public_share_page = NewsPage.objects.filter(
            slug="nota-publica-browser-epic6-003"
        ).first()
        if public_share_page is None:
            public_share_page = NewsPage(
                title='Feria ficticia "A & B" comparte aprendizajes',
                slug="nota-publica-browser-epic6-003",
                live=True,
                publication_date=dt.date(2026, 8, 4),
                coverage_department_id="15",
                coverage_district_id="150101",
            )
            home.add_child(instance=public_share_page)
        public_share_page.title = 'Feria ficticia "A & B" comparte aprendizajes'
        public_share_page.live = True
        public_share_page.publication_date = dt.date(2026, 8, 4)
        public_share_page.body = [
            (
                "paragraph",
                "<h2>Aprendizajes del taller ficticio</h2>"
                "<p>Una comunidad ficticia comparte una práctica escolar "
                "sin incluir información real de menores.</p>",
            )
        ]
        public_share_page.og_title = 'Aprendizajes <ficticios> "A & B"'
        public_share_page.og_description = (
            "Una comunidad ficticia comparte aprendizajes de un taller "
            "escolar sin incluir datos reales de menores."
        )
        public_share_page.canonical_url = (
            "https://example.org/noticia-ficticia"
            "?origen=school-newsroom&grupo=A%20%26%20B"
        )
        public_share_page.seo_noindex = True
        public_share_page.school = school_department_only
        public_share_page.coverage_department_id = "15"
        public_share_page.coverage_district_id = "150101"
        public_share_page.save()
        public_share_page.attributions.all().delete()
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
        NewsPageAttribution.objects.create(
            page=public_share_page,
            kind=NewsPageAttribution.Kind.AUTHOR,
            author_profile=browser_author,
            sort_order=0,
        )
        NewsPageAttribution.objects.create(
            page=public_share_page,
            kind=NewsPageAttribution.Kind.PUBLIC_CREDIT,
            sort_order=1,
            display_name="Redacción pública ficticia",
        )
        NewsPageAttribution.objects.create(
            page=public_share_page,
            kind=NewsPageAttribution.Kind.AUTHOR,
            author_profile=browser_minimal_author,
            sort_order=2,
        )
        NewsPageAttribution.objects.create(
            page=public_share_page,
            kind=NewsPageAttribution.Kind.INTERNAL_CONTRIBUTOR,
            minor_contributor=browser_minor,
            sort_order=3,
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

        scenario_pages = (
            (
                "nota-browser-solo-autor",
                "Nota browser sólo autor",
                NewsPageAttribution.Kind.AUTHOR,
                browser_author,
            ),
            (
                "nota-browser-solo-firma",
                "Nota browser sólo firma",
                NewsPageAttribution.Kind.PUBLIC_CREDIT,
                "Firma browser ficticia",
            ),
            (
                "nota-browser-solo-interno",
                "Nota browser sólo interno",
                NewsPageAttribution.Kind.INTERNAL_CONTRIBUTOR,
                browser_minor,
            ),
            (
                "nota-browser-autor-menor",
                "Nota browser autor menor",
                NewsPageAttribution.Kind.AUTHOR,
                browser_minor_profile,
            ),
        )
        expected_scenario_page_ids = (
            int(os.environ["BROWSER_TEST_AUTHOR_ONLY_PAGE_ID"]),
            int(os.environ["BROWSER_TEST_CREDIT_ONLY_PAGE_ID"]),
            int(os.environ["BROWSER_TEST_INTERNAL_ONLY_PAGE_ID"]),
            int(os.environ["BROWSER_TEST_MINOR_AUTHOR_PAGE_ID"]),
        )
        for (slug, title, kind, value), expected_id in zip(
            scenario_pages, expected_scenario_page_ids, strict=True
        ):
            scenario_page = NewsPage.objects.filter(slug=slug).first()
            if scenario_page is None:
                scenario_page = NewsPage(
                    title=title,
                    slug=slug,
                    live=False,
                    publication_date=dt.date(2026, 8, 5),
                    coverage_department_id="04",
                    coverage_district_id="040101",
                    body=[("paragraph", "<p>Escenario browser ficticio.</p>")],
                )
                home.add_child(instance=scenario_page)
            scenario_page.title = title
            scenario_page.live = False
            scenario_page.contains_identifiable_minors = False
            scenario_page.minor_publication_authorizations_verified = False
            scenario_page.save()
            NewsPageSection.objects.update_or_create(
                page=scenario_page,
                section=NewsSection.objects.get(slug="politica"),
            )
            scenario_page.attributions.all().delete()
            attribution_kwargs = {"page": scenario_page, "kind": kind}
            if kind == NewsPageAttribution.Kind.AUTHOR:
                attribution_kwargs["author_profile"] = value
            elif kind == NewsPageAttribution.Kind.PUBLIC_CREDIT:
                attribution_kwargs["display_name"] = value
            else:
                attribution_kwargs["minor_contributor"] = value
            NewsPageAttribution.objects.create(**attribution_kwargs)
            scenario_page.save_revision(user=user)
            if scenario_page.pk != expected_id:
                raise CommandError(
                    "The disposable authorship scenario page ID changed: "
                    f"expected {expected_id}, found {scenario_page.pk}."
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
                f"public share page {public_share_page.pk}; four authorship "
                "scenarios; 11 archive pages."
            )
        )
