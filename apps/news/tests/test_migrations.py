import importlib
from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone
from wagtail.models import Locale as RuntimeLocale
from wagtail.models import Page as RuntimePage
from wagtail.models import Revision, Site
from wagtail.users.models import UserProfile

NEWS_0001 = ("news", "0001_initial")
NEWS_0002 = ("news", "0002_bootstrap_editorial_data")
HOME_0001 = ("home", "0001_initial")
BEFORE_NEWS_0002 = [HOME_0001, NEWS_0001]


def migrate_to(targets):
    if isinstance(targets, tuple):
        targets = [targets]
    executor = MigrationExecutor(connection)
    executor.migrate(targets)
    return executor.loader.project_state(targets).apps


def migrate_to_latest():
    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())


def bootstrap_migration_module():
    return importlib.import_module(
        "apps.news.migrations.0002_bootstrap_editorial_data",
    )


def migration_schema_editor():
    return SimpleNamespace(connection=connection)


def prepare_base_bootstrap_home(apps, *, title="Welcome to your new Wagtail site!"):
    ContentTypeModel = apps.get_model("contenttypes", "ContentType")
    Page = apps.get_model("wagtailcore", "Page")
    SiteModel = apps.get_model("wagtailcore", "Site")
    db_alias = connection.alias

    if not SiteModel.objects.using(db_alias).filter(is_default_site=True).exists():
        runtime_locale = RuntimeLocale.objects.order_by("id").first()
        if runtime_locale is None:
            RuntimeLocale.objects.create(language_code="es")
        elif runtime_locale.language_code != "es":
            runtime_locale.language_code = "es"
            runtime_locale.save(update_fields=["language_code"])

        tree_root = RuntimePage.get_first_root_node()
        if tree_root is None:
            tree_root = RuntimePage.add_root(
                instance=RuntimePage(title="Root", slug="root"),
            )
        site_root = RuntimePage(title=title, slug="home", live=True)
        tree_root.add_child(instance=site_root)
        Site.objects.update_or_create(
            hostname="testserver",
            defaults={
                "port": 80,
                "site_name": "School Newsroom",
                "root_page": site_root,
                "is_default_site": True,
            },
        )

    site = SiteModel.objects.using(db_alias).get(is_default_site=True)
    root = Page._base_manager.using(db_alias).get(id=site.root_page_id)
    base_page_content_type = ContentTypeModel.objects.db_manager(db_alias).get(
        app_label="wagtailcore",
        model="page",
    )

    with connection.cursor() as cursor:
        cursor.execute(
            "DELETE FROM home_homepage WHERE page_ptr_id = %s",
            [root.id],
        )

    Page._base_manager.using(db_alias).filter(id=root.id).update(
        content_type_id=base_page_content_type.id,
        slug="home",
        title=title,
        draft_title=title,
    )
    return root.id, base_page_content_type


@pytest.mark.django_db(transaction=True)
def test_bootstrap_data_migration_aligns_locale_and_admin_language():
    try:
        apps = migrate_to(BEFORE_NEWS_0002)
        db_alias = connection.alias
        locale_model = apps.get_model("wagtailcore", "Locale")

        locale = locale_model._base_manager.using(db_alias).order_by("id").first()
        locale.language_code = "en"
        locale.save(using=db_alias, update_fields=["language_code"])

        user = (
            get_user_model()
            .objects.db_manager(db_alias)
            .create(
                username="migration-language-editor",
            )
        )
        UserProfile.objects.db_manager(db_alias).create(
            user_id=user.id,
            preferred_language="en",
        )

        apps = migrate_to(NEWS_0002)
        locale_model = apps.get_model("wagtailcore", "Locale")

        assert list(
            locale_model._base_manager.using(db_alias).values_list(
                "language_code",
                flat=True,
            ),
        ) == ["es"]
        assert (
            UserProfile.objects.db_manager(db_alias)
            .get(user_id=user.id)
            .preferred_language
            == "es"
        )
    finally:
        migrate_to_latest()


@pytest.mark.django_db(transaction=True)
def test_bootstrap_data_migration_locale_invariant_fails_for_multiple_locales():
    try:
        apps = migrate_to(BEFORE_NEWS_0002)
        db_alias = connection.alias
        locale_model = apps.get_model("wagtailcore", "Locale")
        migration_module = bootstrap_migration_module()

        locale_model._base_manager.using(db_alias).get_or_create(language_code="es")
        locale_model._base_manager.using(db_alias).get_or_create(language_code="en")

        with pytest.raises(ImproperlyConfigured, match="Spanish-only"):
            migration_module.validate_spanish_locale_invariant(
                apps,
                migration_schema_editor(),
            )
    finally:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM wagtailcore_locale WHERE language_code <> %s",
                ["es"],
            )
            cursor.execute(
                """
                INSERT INTO wagtailcore_locale (language_code)
                SELECT %s
                WHERE NOT EXISTS (
                    SELECT 1 FROM wagtailcore_locale WHERE language_code = %s
                )
                """,
                ["es", "es"],
            )
        migrate_to_latest()


@pytest.mark.django_db(transaction=True)
def test_bootstrap_data_migration_converts_generic_bootstrap_home_page():
    try:
        apps = migrate_to(BEFORE_NEWS_0002)
        db_alias = connection.alias
        root_id, _base_page_content_type = prepare_base_bootstrap_home(apps)
        Revision.objects.db_manager(db_alias).filter(object_id=str(root_id)).delete()

        apps = migrate_to(NEWS_0002)
        ContentTypeModel = apps.get_model("contenttypes", "ContentType")
        HomePage = apps.get_model("home", "HomePage")
        Page = apps.get_model("wagtailcore", "Page")

        root = Page._base_manager.using(db_alias).get(id=root_id)
        home_content_type = ContentTypeModel.objects.db_manager(db_alias).get(
            app_label="home",
            model="homepage",
        )

        assert root.content_type_id == home_content_type.id
        assert root.title == "Inicio"
        assert root.draft_title == "Inicio"
        assert root.slug == "home"
        assert root.locale.language_code == "es"
        assert (
            HomePage._base_manager.using(db_alias)
            .filter(
                page_ptr_id=root_id,
            )
            .exists()
        )
    finally:
        migrate_to_latest()


@pytest.mark.django_db(transaction=True)
def test_bootstrap_data_migration_normalizes_known_admin_bootstrap_names():
    try:
        apps = migrate_to(BEFORE_NEWS_0002)
        db_alias = connection.alias
        ContentTypeModel = apps.get_model("contenttypes", "ContentType")
        Group = apps.get_model("auth", "Group")
        Task = apps.get_model("wagtailcore", "Task")
        Workflow = apps.get_model("wagtailcore", "Workflow")
        task_content_type, _ = ContentTypeModel.objects.db_manager(
            db_alias,
        ).get_or_create(app_label="wagtailcore", model="groupapprovaltask")

        Group.objects.using(db_alias).get_or_create(name="Moderators")
        Group.objects.using(db_alias).get_or_create(name="Editors")
        Workflow.objects.using(db_alias).get_or_create(name="Moderators approval")
        Task.objects.using(db_alias).get_or_create(
            name="Moderators approval",
            defaults={"content_type_id": task_content_type.id},
        )

        apps = migrate_to(NEWS_0002)
        Group = apps.get_model("auth", "Group")
        Task = apps.get_model("wagtailcore", "Task")
        Workflow = apps.get_model("wagtailcore", "Workflow")

        assert Group.objects.using(db_alias).filter(name="Moderadores").exists()
        assert Group.objects.using(db_alias).filter(name="Editores").exists()
        assert (
            Workflow.objects.using(db_alias)
            .filter(
                name="Aprobación de moderadores",
            )
            .exists()
        )
        assert (
            Task.objects.using(db_alias)
            .filter(
                name="Aprobación de moderadores",
            )
            .exists()
        )
    finally:
        migrate_to_latest()


@pytest.mark.django_db(transaction=True)
def test_bootstrap_admin_name_normalization_fails_on_target_conflict():
    try:
        apps = migrate_to(BEFORE_NEWS_0002)
        db_alias = connection.alias
        Group = apps.get_model("auth", "Group")
        migration_module = bootstrap_migration_module()

        Group.objects.using(db_alias).get_or_create(name="Moderators")
        Group.objects.using(db_alias).get_or_create(name="Moderadores")

        with pytest.raises(ImproperlyConfigured, match="Spanish target name"):
            migration_module.normalize_known_bootstrap_admin_names(
                apps,
                migration_schema_editor(),
            )
    finally:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM auth_group WHERE name IN (%s, %s)",
                ["Moderators", "Moderadores"],
            )
        migrate_to_latest()


@pytest.mark.django_db(transaction=True)
def test_bootstrap_home_migration_fails_for_unexpected_specific_page_type():
    root_id = None
    base_page_content_type_id = None
    try:
        apps = migrate_to(BEFORE_NEWS_0002)
        db_alias = connection.alias
        root_id, base_page_content_type = prepare_base_bootstrap_home(
            apps,
            title="Home",
        )
        base_page_content_type_id = base_page_content_type.id
        ContentTypeModel = apps.get_model("contenttypes", "ContentType")
        Page = apps.get_model("wagtailcore", "Page")
        migration_module = bootstrap_migration_module()

        news_page_content_type, _ = ContentTypeModel.objects.db_manager(
            db_alias,
        ).get_or_create(app_label="news", model="newspage")
        Page._base_manager.using(db_alias).filter(id=root_id).update(
            content_type_id=news_page_content_type.id,
        )

        with pytest.raises(ImproperlyConfigured, match="unexpected Page subtype"):
            migration_module.normalize_bootstrap_home_page(
                apps,
                migration_schema_editor(),
            )

        assert (
            Page._base_manager.using(db_alias).get(id=root_id).content_type_id
            == news_page_content_type.id
        )
    finally:
        with connection.cursor() as cursor:
            if root_id is not None:
                cursor.execute(
                    """
                    UPDATE wagtailcore_page
                    SET content_type_id = %s
                    WHERE id = %s
                    """,
                    [base_page_content_type_id, root_id],
                )
                cursor.execute(
                    "DELETE FROM home_homepage WHERE page_ptr_id = %s",
                    [root_id],
                )
        migrate_to_latest()


@pytest.mark.django_db(transaction=True)
def test_bootstrap_home_migration_fails_for_unsupported_revision_state():
    root_id = None
    try:
        apps = migrate_to(BEFORE_NEWS_0002)
        db_alias = connection.alias
        root_id, base_page_content_type = prepare_base_bootstrap_home(
            apps,
            title="Home",
        )
        Page = apps.get_model("wagtailcore", "Page")
        RevisionModel = apps.get_model("wagtailcore", "Revision")
        migration_module = bootstrap_migration_module()

        RevisionModel._base_manager.using(db_alias).create(
            content_type_id=base_page_content_type.id,
            base_content_type_id=base_page_content_type.id,
            object_id=str(root_id),
            created_at=timezone.now(),
            object_str="Home",
            content={},
        )

        with pytest.raises(ImproperlyConfigured, match="existing revisions"):
            migration_module.normalize_bootstrap_home_page(
                apps,
                migration_schema_editor(),
            )

        assert (
            Page._base_manager.using(db_alias).get(id=root_id).content_type_id
            == base_page_content_type.id
        )
    finally:
        if root_id is not None:
            Revision.objects.db_manager(connection.alias).filter(
                object_id=str(root_id),
            ).delete()
        migrate_to_latest()


@pytest.mark.django_db
def test_final_migrated_default_site_root_is_spanish_home_page() -> None:
    site = Site.objects.get(is_default_site=True)
    home = site.root_page.specific

    assert home.__class__.__name__ == "HomePage"
    assert home.title == "Inicio"
    assert home.draft_title == "Inicio"
    assert home.slug == "home"
    assert home.locale.language_code == "es"
