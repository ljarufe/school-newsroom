from django.core.exceptions import ImproperlyConfigured
from django.db import migrations


BOOTSTRAP_HOME_TITLES = {"Home", "Welcome to your new Wagtail site!"}
SPANISH_ONLY_LOCALE_ERROR = (
    "School Newsroom is currently a Spanish-only single-language product. "
    "The unexpected Wagtail Locale state requires explicit manual review "
    "before this migration can continue."
)
UNEXPECTED_HOME_TYPE_ERROR = (
    "The default Site root still looks like the known Wagtail bootstrap Home "
    "page, but it uses an unexpected Page subtype. Manual review is required "
    "before converting it to the School Newsroom HomePage."
)
UNSUPPORTED_HOME_REVISION_ERROR = (
    "The default Site root still looks like the known Wagtail bootstrap Home "
    "page, but it has existing revisions. Manual review is required before "
    "changing its Page type because this migration does not rewrite revision "
    "content or content types."
)
BOOTSTRAP_ADMIN_NAME_CONFLICT_ERROR = (
    "A known Wagtail bootstrap admin object could not be renamed because the "
    "Spanish target name already exists. Manual review is required before "
    "merging or renaming permissions and workflow data."
)
BOOTSTRAP_ADMIN_NAME_NORMALIZATIONS = [
    ("auth", "Group", "Moderators", "Moderadores"),
    ("auth", "Group", "Editors", "Editores"),
    (
        "wagtailcore",
        "Workflow",
        "Moderators approval",
        "Aprobación de moderadores",
    ),
    (
        "wagtailcore",
        "Task",
        "Moderators approval",
        "Aprobación de moderadores",
    ),
]


def seed_initial_news_sections(apps, schema_editor):
    NewsSection = apps.get_model("news", "NewsSection")
    db_alias = schema_editor.connection.alias

    sections = [
        ("Política", "politica", 10),
        ("Cultura", "cultura", 20),
        ("Medio Ambiente", "medio-ambiente", 30),
        ("Problemáticas Sociales", "problematicas-sociales", 40),
        ("Columnas", "columnas", 50),
        ("Entrevistas", "entrevistas", 60),
    ]

    for name, slug, sort_order in sections:
        NewsSection.objects.using(db_alias).get_or_create(
            slug=slug,
            defaults={"name": name, "sort_order": sort_order},
        )


def align_spanish_locale_and_admin_language(apps, schema_editor):
    Locale = apps.get_model("wagtailcore", "Locale")
    UserProfile = apps.get_model("wagtailusers", "UserProfile")
    db_alias = schema_editor.connection.alias

    locales = list(Locale._base_manager.using(db_alias).order_by("id"))

    if not locales:
        Locale._base_manager.using(db_alias).create(language_code="es")
    elif len(locales) == 1 and locales[0].language_code != "es":
        locale = locales[0]
        locale.language_code = "es"
        locale.save(using=db_alias, update_fields=["language_code"])

    UserProfile.objects.using(db_alias).exclude(
        preferred_language__in=["", "es"],
    ).update(preferred_language="es")


def validate_spanish_locale_invariant(apps, schema_editor):
    Locale = apps.get_model("wagtailcore", "Locale")
    db_alias = schema_editor.connection.alias

    language_codes = list(
        Locale._base_manager.using(db_alias)
        .order_by("id")
        .values_list("language_code", flat=True),
    )
    if language_codes != ["es"]:
        raise ImproperlyConfigured(SPANISH_ONLY_LOCALE_ERROR)


def normalize_bootstrap_home_page(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    HomePage = apps.get_model("home", "HomePage")
    Page = apps.get_model("wagtailcore", "Page")
    Revision = apps.get_model("wagtailcore", "Revision")
    Site = apps.get_model("wagtailcore", "Site")
    db_alias = schema_editor.connection.alias

    site = Site.objects.using(db_alias).filter(is_default_site=True).first()
    if site is None:
        return

    root = Page._base_manager.using(db_alias).get(id=site.root_page_id)
    base_page_content_type = ContentType.objects.db_manager(db_alias).get(
        app_label="wagtailcore",
        model="page",
    )
    home_content_type, _ = ContentType.objects.db_manager(db_alias).get_or_create(
        app_label="home",
        model="homepage",
    )

    bootstrap_like = root.slug == "home" and root.title in BOOTSTRAP_HOME_TITLES
    is_base_page = root.content_type_id == base_page_content_type.id
    is_home_page = root.content_type_id == home_content_type.id

    if bootstrap_like and not is_base_page and not is_home_page:
        raise ImproperlyConfigured(UNEXPECTED_HOME_TYPE_ERROR)

    if is_base_page and bootstrap_like:
        revision_count = (
            Revision._base_manager.using(db_alias)
            .filter(
                base_content_type_id=base_page_content_type.id,
                object_id=str(root.id),
            )
            .count()
        )
        if revision_count:
            raise ImproperlyConfigured(UNSUPPORTED_HOME_REVISION_ERROR)

        if not HomePage._base_manager.using(db_alias).filter(
            page_ptr_id=root.id,
        ).exists():
            table_name = schema_editor.connection.ops.quote_name(HomePage._meta.db_table)
            column_name = schema_editor.connection.ops.quote_name("page_ptr_id")
            with schema_editor.connection.cursor() as cursor:
                cursor.execute(
                    f"INSERT INTO {table_name} ({column_name}) VALUES (%s)",
                    [root.id],
                )

        Page._base_manager.using(db_alias).filter(id=root.id).update(
            content_type_id=home_content_type.id,
            title="Inicio",
            draft_title="Inicio",
        )
        return

    if is_home_page and bootstrap_like:
        Page._base_manager.using(db_alias).filter(id=root.id).update(
            title="Inicio",
            draft_title="Inicio",
        )


def normalize_known_bootstrap_admin_names(apps, schema_editor):
    db_alias = schema_editor.connection.alias

    for app_label, model_name, source_name, target_name in (
        BOOTSTRAP_ADMIN_NAME_NORMALIZATIONS
    ):
        model = apps.get_model(app_label, model_name)
        manager = model._default_manager.using(db_alias)
        source = manager.filter(name=source_name).first()
        if source is None:
            continue

        if manager.filter(name=target_name).exclude(pk=source.pk).exists():
            raise ImproperlyConfigured(BOOTSTRAP_ADMIN_NAME_CONFLICT_ERROR)

        source.name = target_name
        source.save(using=db_alias, update_fields=["name"])


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0001_initial"),
        ('news', '0001_initial'),
        ("wagtailusers", "0015_userprofile_keyboard_shortcuts"),
    ]

    operations = [
        migrations.RunPython(seed_initial_news_sections, migrations.RunPython.noop),
        migrations.RunPython(
            align_spanish_locale_and_admin_language,
            migrations.RunPython.noop,
        ),
        migrations.RunPython(validate_spanish_locale_invariant, migrations.RunPython.noop),
        migrations.RunPython(normalize_bootstrap_home_page, migrations.RunPython.noop),
        migrations.RunPython(
            normalize_known_bootstrap_admin_names,
            migrations.RunPython.noop,
        ),
    ]
