from django.core.exceptions import ImproperlyConfigured
from django.db import migrations


MISSING_MAIN_SECTION_ERROR = (
    "EPIC3-009 could not find an expected main section with its stable slug. "
    "Manual taxonomy review is required before continuing."
)
SUBSECTION_CONFLICT_ERROR = (
    "EPIC3-009 found a provisional subsection slug with an incompatible identity. "
    "Manual taxonomy review is required before continuing."
)
REVISION_SECTION_ERROR = (
    "EPIC3-009 found a NewsPage revision whose singular section no longer exists. "
    "The revision must be repaired explicitly before continuing."
)
UNSAFE_REVERSE_ERROR = (
    "EPIC3-009 cannot reverse the taxonomy migration because at least one current "
    "page or historical revision cannot be represented safely by the singular "
    "section field. Remove ambiguity explicitly before retrying."
)

PROVISIONAL_SUBSECTIONS = {
    "politica": [
        ("Política local", "politica-local", 10),
        ("Participación ciudadana", "participacion-ciudadana", 20),
        ("Gobierno y gestión", "gobierno-y-gestion", 30),
    ],
    "cultura": [
        ("Arte y literatura", "arte-y-literatura", 10),
        ("Música", "musica", 20),
        ("Cine y audiovisual", "cine-y-audiovisual", 30),
        ("Patrimonio y memoria", "patrimonio-y-memoria", 40),
        ("Tradiciones", "tradiciones", 50),
    ],
    "medio-ambiente": [
        ("Cambio climático", "cambio-climatico", 10),
        ("Biodiversidad", "biodiversidad", 20),
        ("Agua", "agua", 30),
        ("Residuos y reciclaje", "residuos-y-reciclaje", 40),
    ],
    "problematicas-sociales": [
        ("Educación", "educacion", 10),
        ("Salud", "salud", 20),
    ],
    "columnas": [
        ("Opinión", "opinion", 10),
    ],
    "entrevistas": [
        ("Perfiles", "perfiles", 10),
        ("Comunidad", "comunidad", 20),
        ("Trayectorias", "trayectorias", 30),
    ],
}


def _news_page_revisions(apps, db_alias):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Revision = apps.get_model("wagtailcore", "Revision")
    news_page_content_type = ContentType.objects.db_manager(db_alias).filter(
        app_label="news",
        model="newspage",
    ).first()
    if news_page_content_type is None:
        return Revision.objects.using(db_alias).none()
    return Revision.objects.using(db_alias).filter(
        content_type_id=news_page_content_type.pk
    )


def migrate_pages_and_revisions(apps, schema_editor):
    NewsPage = apps.get_model("news", "NewsPage")
    NewsPageSection = apps.get_model("news", "NewsPageSection")
    NewsSection = apps.get_model("news", "NewsSection")
    db_alias = schema_editor.connection.alias

    for page_id, section_id in NewsPage.objects.using(db_alias).values_list(
        "pk", "section_id"
    ):
        if section_id is not None:
            NewsPageSection.objects.using(db_alias).get_or_create(
                page_id=page_id,
                section_id=section_id,
            )

    known_section_ids = set(
        NewsSection.objects.using(db_alias).values_list("pk", flat=True)
    )
    for revision in _news_page_revisions(apps, db_alias).iterator():
        content = dict(revision.content)
        if "section" not in content:
            continue
        section_id = content.pop("section")
        if section_id is None:
            content["section_assignments"] = []
        else:
            if section_id not in known_section_ids:
                raise ImproperlyConfigured(REVISION_SECTION_ERROR)
            page_id = content.get("pk") or int(revision.object_id)
            content["section_assignments"] = [
                {
                    "pk": None,
                    "page": page_id,
                    "section": section_id,
                }
            ]
        revision.content = content
        revision.save(using=db_alias, update_fields=["content"])

    for parent_slug, children in PROVISIONAL_SUBSECTIONS.items():
        parent = (
            NewsSection.objects.using(db_alias)
            .filter(slug=parent_slug, parent_id__isnull=True)
            .first()
        )
        if parent is None:
            raise ImproperlyConfigured(MISSING_MAIN_SECTION_ERROR)

        for name, slug, sort_order in children:
            existing = (
                NewsSection.objects.using(db_alias).filter(slug=slug).first()
            )
            if existing is None:
                NewsSection.objects.using(db_alias).create(
                    name=name,
                    slug=slug,
                    sort_order=sort_order,
                    parent_id=parent.pk,
                )
                continue
            if existing.name != name or existing.parent_id != parent.pk:
                raise ImproperlyConfigured(SUBSECTION_CONFLICT_ERROR)


def restore_singular_sections(apps, schema_editor):
    NewsPage = apps.get_model("news", "NewsPage")
    NewsPageSection = apps.get_model("news", "NewsPageSection")
    NewsSection = apps.get_model("news", "NewsSection")
    db_alias = schema_editor.connection.alias

    provisional_sections = []
    for parent_slug, children in PROVISIONAL_SUBSECTIONS.items():
        existing_children = [
            (
                name,
                slug,
                sort_order,
                NewsSection.objects.using(db_alias).filter(slug=slug).first(),
            )
            for name, slug, sort_order in children
        ]
        if not any(child is not None for _, _, _, child in existing_children):
            continue
        parent = (
            NewsSection.objects.using(db_alias).filter(slug=parent_slug).first()
        )
        if parent is None or parent.parent_id is not None:
            raise ImproperlyConfigured(UNSAFE_REVERSE_ERROR)
        for name, slug, sort_order, child in existing_children:
            if child is None:
                continue
            if (
                child.name != name
                or child.parent_id != parent.pk
                or child.sort_order != sort_order
            ):
                raise ImproperlyConfigured(UNSAFE_REVERSE_ERROR)
            provisional_sections.append(child)

    provisional_ids = {section.pk for section in provisional_sections}
    if NewsPageSection.objects.using(db_alias).filter(
        section_id__in=provisional_ids
    ).exists():
        raise ImproperlyConfigured(UNSAFE_REVERSE_ERROR)
    for content in _news_page_revisions(apps, db_alias).values_list(
        "content", flat=True
    ):
        if any(
            isinstance(assignment, dict)
            and assignment.get("section") in provisional_ids
            for assignment in content.get("section_assignments", [])
        ):
            raise ImproperlyConfigured(UNSAFE_REVERSE_ERROR)

    page_plan = []
    for page_id in NewsPage.objects.using(db_alias).values_list("pk", flat=True):
        section_ids = list(
            NewsPageSection.objects.using(db_alias)
            .filter(page_id=page_id)
            .values_list("section_id", flat=True)[:2]
        )
        if len(section_ids) > 1:
            raise ImproperlyConfigured(UNSAFE_REVERSE_ERROR)
        page_plan.append((page_id, section_ids[0] if section_ids else None))

    revision_plan = []
    for revision in _news_page_revisions(apps, db_alias).iterator():
        content = dict(revision.content)
        assignments = content.get("section_assignments", [])
        if not isinstance(assignments, list) or len(assignments) > 1:
            raise ImproperlyConfigured(UNSAFE_REVERSE_ERROR)
        if assignments:
            assignment = assignments[0]
            if not isinstance(assignment, dict) or not assignment.get("section"):
                raise ImproperlyConfigured(UNSAFE_REVERSE_ERROR)
            content["section"] = assignment["section"]
        else:
            content["section"] = None
        content.pop("section_assignments", None)
        revision_plan.append((revision, content))

    for page_id, section_id in page_plan:
        NewsPage.objects.using(db_alias).filter(pk=page_id).update(
            section_id=section_id
        )
    for revision, content in revision_plan:
        revision.content = content
        revision.save(using=db_alias, update_fields=["content"])
    NewsSection.objects.using(db_alias).filter(pk__in=provisional_ids).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("news", "0012_editorial_taxonomy_schema"),
    ]

    operations = [
        migrations.RunPython(
            migrate_pages_and_revisions,
            restore_singular_sections,
        ),
    ]
