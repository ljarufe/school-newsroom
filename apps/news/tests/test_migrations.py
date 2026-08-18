import importlib
import json
from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.db import connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import override_settings
from django.utils import timezone
from wagtail.models import (
    GroupApprovalTask as RuntimeGroupApprovalTask,
)
from wagtail.models import (
    Locale as RuntimeLocale,
)
from wagtail.models import (
    Page as RuntimePage,
)
from wagtail.models import (
    Revision,
    Site,
)
from wagtail.models import (
    Task as RuntimeTask,
)
from wagtail.models import (
    Workflow as RuntimeWorkflow,
)
from wagtail.models import (
    WorkflowPage as RuntimeWorkflowPage,
)
from wagtail.models import (
    WorkflowTask as RuntimeWorkflowTask,
)
from wagtail.users.models import UserProfile

from apps.home.models import HomePage as RuntimeHomePage
from apps.news.models import NewsPage as RuntimeNewsPage
from apps.news.models import NewsPageSection as RuntimeNewsPageSection
from apps.news.models import NewsSection as RuntimeNewsSection

NEWS_0001 = ("news", "0001_initial")
NEWS_0002 = ("news", "0002_bootstrap_editorial_data")
NEWS_0003 = ("news", "0003_newspage_contains_identifiable_minors_and_more")
NEWS_0004 = ("news", "0004_alter_newspage_body")
NEWS_0005 = ("news", "0005_alter_newspage_body")
NEWS_0006 = ("news", "0006_newspage_seo_assistant_fields")
NEWS_0007 = ("news", "0007_newspage_featured_image_alt_text_and_more")
NEWS_0008 = ("news", "0008_alter_newspage_options")
NEWS_0009 = ("news", "0009_reconcile_mvp_access")
NEWS_0010 = ("news", "0010_remove_newspage_summary_and_more")
NEWS_0011 = ("news", "0011_alter_newspage_body")
NEWS_0012 = ("news", "0012_editorial_taxonomy_schema")
NEWS_0013 = ("news", "0013_migrate_editorial_taxonomy")
NEWS_0014 = ("news", "0014_remove_singular_section")
NEWS_0015 = ("news", "0015_newspagerelatedkeyphrase_and_more")
NEWS_0016 = ("news", "0016_public_news_search_infrastructure")
NEWS_0017 = ("news", "0017_add_normalized_geography_fields")
NEWS_0018 = ("news", "0018_backfill_normalized_geography")
NEWS_0019 = ("news", "0019_finalize_normalized_geography")
NEWS_0020 = ("news", "0020_unify_authorship_attribution")
NEWS_0021 = ("news", "0021_authorprofile_minor_email_privacy")
GEOGRAPHY_0002 = ("geography", "0002_load_ubigeo_2025_12_31")
HOME_0001 = ("home", "0001_initial")
BEFORE_NEWS_0002 = [HOME_0001, NEWS_0001]


@pytest.fixture(autouse=True)
def use_builtin_search_config_for_historical_migration_states():
    """Historical states precede the project-owned FTS configuration."""
    with override_settings(
        WAGTAILSEARCH_BACKENDS={
            "default": {
                "BACKEND": "wagtail.search.backends.database",
                "SEARCH_CONFIG": "spanish",
                "FUZZY_SIMILARITY_THRESHOLD": 0.3,
            },
        }
    ):
        yield


def migrate_to(targets):
    if isinstance(targets, tuple):
        targets = [targets]
    executor = MigrationExecutor(connection)
    restore_geography_snapshot_after_transactional_flush(executor)
    executor.migrate(targets)
    return executor.loader.project_state(targets).apps


def migrate_to_latest():
    executor = MigrationExecutor(connection)
    restore_geography_snapshot_after_transactional_flush(executor)
    if ("news", "0002_bootstrap_editorial_data") in executor.loader.applied_migrations:
        with connection.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO news_newssection (name, slug, sort_order)
                VALUES (%s, %s, %s)
                ON CONFLICT (slug) DO NOTHING
                """,
                [
                    ("Política", "politica", 10),
                    ("Cultura", "cultura", 20),
                    ("Medio Ambiente", "medio-ambiente", 30),
                    (
                        "Problemáticas Sociales",
                        "problematicas-sociales",
                        40,
                    ),
                    ("Columnas", "columnas", 50),
                    ("Entrevistas", "entrevistas", 60),
                ],
            )
    executor.migrate(executor.loader.graph.leaf_nodes())


def restore_geography_snapshot_after_transactional_flush(executor):
    """Restore migration-owned data removed by pytest-django's database flush."""
    if GEOGRAPHY_0002 not in executor.loader.applied_migrations:
        return
    apps = executor.loader.project_state([GEOGRAPHY_0002]).apps
    Department = apps.get_model("geography", "Department")
    if Department.objects.using(connection.alias).exists():
        return
    geography_migration_module = importlib.import_module(
        "apps.geography.migrations.0002_load_ubigeo_2025_12_31",
    )
    geography_migration_module.load_snapshot(
        apps,
        SimpleNamespace(connection=connection),
    )


def bootstrap_migration_module():
    return importlib.import_module(
        "apps.news.migrations.0002_bootstrap_editorial_data",
    )


def migration_schema_editor():
    return SimpleNamespace(connection=connection)


def mvp_access_migration_module():
    return importlib.import_module(
        "apps.news.migrations.0009_reconcile_mvp_access",
    )


def taxonomy_migration_module():
    return importlib.import_module(
        "apps.news.migrations.0013_migrate_editorial_taxonomy",
    )


def prepare_obsolete_mvp_access(apps):
    Group = apps.get_model("auth", "Group")
    Page = apps.get_model("wagtailcore", "Page")
    db_alias = connection.alias

    RuntimeWorkflow.objects.using(db_alias).filter(
        name__in=[
            "Aprobación de moderadores",
            "Revisión editorial MVP",
            "Revisión editorial",
        ]
    ).delete()
    RuntimeTask.objects.using(db_alias).filter(
        name="Aprobación de moderadores"
    ).delete()

    moderator_group, _ = Group.objects.using(db_alias).get_or_create(name="Moderadores")
    Group.objects.using(db_alias).get_or_create(name="Editores")
    moderator_group.user_set.clear()

    task = RuntimeGroupApprovalTask.objects.using(db_alias).create(
        name="Aprobación de moderadores"
    )
    task.groups.set([moderator_group.pk])
    workflow = RuntimeWorkflow.objects.using(db_alias).create(
        name="Aprobación de moderadores"
    )
    RuntimeWorkflowTask.objects.using(db_alias).create(
        workflow=workflow,
        task=task,
        sort_order=0,
    )
    runtime_root_page = RuntimePage.get_first_root_node()
    if runtime_root_page is None:
        RuntimeLocale.objects.get_or_create(language_code="es")
        runtime_root_page = RuntimePage.add_root(
            instance=RuntimePage(title="Root", slug="root"),
        )
    root_page = Page.objects.using(db_alias).get(pk=runtime_root_page.pk)
    RuntimeWorkflowPage.objects.using(db_alias).update_or_create(
        page_id=root_page.pk,
        defaults={"workflow": workflow},
    )
    legacy_workflow = RuntimeWorkflow.objects.using(db_alias).create(
        name="Revisión editorial MVP"
    )
    return moderator_group.pk, task.pk, workflow.pk, legacy_workflow.pk


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
        if "apps" in locals():
            db_alias = connection.alias
            Group = apps.get_model("auth", "Group")
            Task = apps.get_model("wagtailcore", "Task")
            Workflow = apps.get_model("wagtailcore", "Workflow")
            Workflow.objects.using(db_alias).filter(
                name__in=[
                    "Moderators approval",
                    "Aprobación de moderadores",
                ]
            ).delete()
            Task.objects.using(db_alias).filter(
                name__in=[
                    "Moderators approval",
                    "Aprobación de moderadores",
                ]
            ).delete()
            Group.objects.using(db_alias).filter(
                name__in=[
                    "Moderators",
                    "Moderadores",
                    "Editors",
                    "Editores",
                ]
            ).delete()
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
def test_epic4_access_migration_removes_only_safe_obsolete_records_and_renames():
    try:
        apps = migrate_to(NEWS_0008)
        Group = apps.get_model("auth", "Group")
        db_alias = connection.alias
        unrelated_group = Group.objects.using(db_alias).create(
            name="Grupo no relacionado"
        )
        _group_id, _task_id, _workflow_id, legacy_workflow_id = (
            prepare_obsolete_mvp_access(apps)
        )

        apps = migrate_to(NEWS_0009)
        Group = apps.get_model("auth", "Group")
        Task = apps.get_model("wagtailcore", "Task")
        Workflow = apps.get_model("wagtailcore", "Workflow")
        WorkflowPage = apps.get_model("wagtailcore", "WorkflowPage")

        assert (
            not Group.objects.using(db_alias)
            .filter(name__in=["Moderadores", "Editores"])
            .exists()
        )
        assert Group.objects.using(db_alias).filter(pk=unrelated_group.pk).exists()
        assert (
            not Task.objects.using(db_alias)
            .filter(name="Aprobación de moderadores")
            .exists()
        )
        assert (
            not Workflow.objects.using(db_alias)
            .filter(name="Aprobación de moderadores")
            .exists()
        )
        renamed_workflow = Workflow.objects.using(db_alias).get(
            name="Revisión editorial"
        )
        assert renamed_workflow.pk == legacy_workflow_id
        assert (
            not Workflow.objects.using(db_alias)
            .filter(name="Revisión editorial MVP")
            .exists()
        )
        assert (
            not WorkflowPage.objects.using(db_alias)
            .filter(workflow_id=_workflow_id)
            .exists()
        )
    finally:
        migrate_to_latest()


@pytest.mark.django_db(transaction=True)
def test_epic4_access_migration_fails_before_deleting_an_assigned_group():
    username = "obsolete-group-member"
    try:
        apps = migrate_to(NEWS_0008)
        Group = apps.get_model("auth", "Group")
        User = apps.get_model("auth", "User")
        db_alias = connection.alias
        moderator_group_id, _task_id, _workflow_id, _legacy_id = (
            prepare_obsolete_mvp_access(apps)
        )
        user = User.objects.using(db_alias).create(username=username)
        user.groups.add(moderator_group_id)

        with pytest.raises(ImproperlyConfigured, match="still has assigned users"):
            mvp_access_migration_module().reconcile_mvp_access(
                apps,
                migration_schema_editor(),
            )

        assert Group.objects.using(db_alias).filter(pk=moderator_group_id).exists()
        assert (
            RuntimeWorkflow.objects.using(db_alias)
            .filter(name="Revisión editorial MVP")
            .exists()
        )
    finally:
        if "User" in locals():
            User.objects.using(db_alias).filter(username=username).delete()
        migrate_to_latest()


@pytest.mark.django_db(transaction=True)
def test_epic4_access_migration_fails_on_an_unexpected_group_dependency():
    extra_task_id = None
    try:
        apps = migrate_to(NEWS_0008)
        Group = apps.get_model("auth", "Group")
        db_alias = connection.alias
        moderator_group_id, _task_id, _workflow_id, _legacy_id = (
            prepare_obsolete_mvp_access(apps)
        )
        extra_task = RuntimeGroupApprovalTask.objects.using(db_alias).create(
            name="Otra aprobación vigente"
        )
        extra_task_id = extra_task.pk
        extra_task.groups.set([moderator_group_id])

        with pytest.raises(
            ImproperlyConfigured,
            match="used by another workflow task",
        ):
            mvp_access_migration_module().reconcile_mvp_access(
                apps,
                migration_schema_editor(),
            )

        assert Group.objects.using(db_alias).filter(pk=moderator_group_id).exists()
    finally:
        if extra_task_id is not None:
            RuntimeTask.objects.filter(pk=extra_task_id).delete()
        migrate_to_latest()


@pytest.mark.django_db(transaction=True)
def test_epic3_002_migration_preserves_existing_news_without_fabricated_data():
    page_id = None
    try:
        apps = migrate_to(NEWS_0002)
        db_alias = connection.alias
        ContentType = apps.get_model("contenttypes", "ContentType")
        NewsSection = apps.get_model("news", "NewsSection")
        Page = apps.get_model("wagtailcore", "Page")
        SiteModel = apps.get_model("wagtailcore", "Site")

        if not Site.objects.db_manager(db_alias).filter(is_default_site=True).exists():
            RuntimeLocale.objects.db_manager(db_alias).get_or_create(
                language_code="es",
            )
            root = RuntimePage.get_first_root_node()
            if root is None:
                root = RuntimePage.add_root(
                    instance=RuntimePage(title="Root", slug="root"),
                )
            home_page = RuntimeHomePage(title="Inicio", slug="inicio-migration-test")
            root.add_child(instance=home_page)
            Site.objects.db_manager(db_alias).create(
                hostname="testserver",
                port=80,
                site_name="School Newsroom",
                root_page=home_page,
                is_default_site=True,
            )

        site = SiteModel.objects.using(db_alias).get(is_default_site=True)
        home = RuntimePage.objects.get(pk=site.root_page_id)
        base_child = RuntimePage(
            title="Historical Fictional News",
            slug="historical-news",
        )
        home.add_child(instance=base_child)
        page_id = base_child.pk

        news_page_content_type, _ = ContentType.objects.db_manager(
            db_alias,
        ).get_or_create(app_label="news", model="newspage")
        Page._base_manager.using(db_alias).filter(pk=page_id).update(
            content_type_id=news_page_content_type.pk,
        )
        section, _ = NewsSection.objects.using(db_alias).get_or_create(
            slug="politica",
            defaults={"name": "Política", "sort_order": 10},
        )
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO news_newspage (
                    page_ptr_id,
                    publication_date,
                    summary,
                    body,
                    coverage_province,
                    coverage_district,
                    featured_image_id,
                    section_id,
                    school_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    page_id,
                    timezone.datetime(2026, 7, 1).date(),
                    "Historical fictional summary.",
                    json.dumps(
                        [
                            {
                                "type": "heading",
                                "value": "Historical context",
                                "id": "11111111-1111-4111-8111-111111111111",
                            },
                        ],
                    ),
                    "Arequipa",
                    "Cercado",
                    None,
                    section.pk,
                    None,
                ],
            )

        apps = migrate_to(NEWS_0003)
        MigratedNewsPage = apps.get_model("news", "NewsPage")
        NewsPagePublicCredit = apps.get_model("news", "NewsPagePublicCredit")
        NewsPageContributor = apps.get_model("news", "NewsPageContributor")

        migrated_page = MigratedNewsPage.objects.using(db_alias).get(pk=page_id)

        assert migrated_page.contains_identifiable_minors is False
        assert migrated_page.minor_publication_authorizations_verified is False
        assert migrated_page.sensitive_content is False
        assert (
            NewsPagePublicCredit.objects.using(db_alias).filter(page_id=page_id).count()
            == 0
        )
        assert (
            NewsPageContributor.objects.using(db_alias).filter(page_id=page_id).count()
            == 0
        )
    finally:
        migrate_to_latest()


@pytest.mark.django_db(transaction=True)
def test_epic3_003_body_migrations_preserve_then_convert_historical_content():
    page_id = None
    revision_ids = []
    historical_body = [
        {
            "type": "heading",
            "value": "Historical <context> & evidence",
            "id": "11111111-1111-4111-8111-111111111111",
        },
        {
            "type": "paragraph",
            "value": "<p>Historical rich text paragraph.</p>",
            "id": "22222222-2222-4222-8222-222222222222",
        },
    ]
    heading_revision_body = [
        {
            "type": "heading",
            "value": "Draft <context> & evidence",
            "id": "33333333-3333-4333-8333-333333333333",
            "custom_item_key": "preserved",
        },
    ]
    mixed_revision_body = [
        {
            "type": "paragraph",
            "value": "<p>Existing revision paragraph.</p>",
            "id": "44444444-4444-4444-8444-444444444444",
        },
        {
            "type": "heading",
            "value": "Scheduled heading",
            "id": "55555555-5555-4555-8555-555555555555",
        },
        {
            "type": "paragraph",
            "value": "<p>Following revision paragraph.</p>",
            "id": "66666666-6666-4666-8666-666666666666",
        },
    ]
    no_heading_revision_body = [
        {
            "type": "paragraph",
            "value": "<p>Already compatible.</p>",
            "id": "77777777-7777-4777-8777-777777777777",
        },
    ]
    unrelated_revision_body = [
        {
            "type": "heading",
            "value": "Not a NewsPage heading",
            "id": "88888888-8888-4888-8888-888888888888",
        },
    ]

    try:
        apps = migrate_to(NEWS_0003)
        db_alias = connection.alias
        ContentType = apps.get_model("contenttypes", "ContentType")
        NewsSection = apps.get_model("news", "NewsSection")
        Page = apps.get_model("wagtailcore", "Page")
        SiteModel = apps.get_model("wagtailcore", "Site")

        if not Site.objects.db_manager(db_alias).filter(is_default_site=True).exists():
            RuntimeLocale.objects.db_manager(db_alias).get_or_create(
                language_code="es",
            )
            root = RuntimePage.get_first_root_node()
            if root is None:
                root = RuntimePage.add_root(
                    instance=RuntimePage(title="Root", slug="root"),
                )
            home_page = RuntimeHomePage(
                title="Inicio",
                slug="inicio-epic3-003-migration-test",
            )
            root.add_child(instance=home_page)
            Site.objects.db_manager(db_alias).create(
                hostname="testserver",
                port=80,
                site_name="School Newsroom",
                root_page=home_page,
                is_default_site=True,
            )

        site = SiteModel.objects.using(db_alias).get(is_default_site=True)
        home = RuntimePage.objects.get(pk=site.root_page_id)
        base_child = RuntimePage(
            title="Historical Structured News",
            slug="historical-structured-news",
        )
        home.add_child(instance=base_child)
        page_id = base_child.pk

        news_page_content_type, _ = ContentType.objects.db_manager(
            db_alias,
        ).get_or_create(app_label="news", model="newspage")
        Page._base_manager.using(db_alias).filter(pk=page_id).update(
            content_type_id=news_page_content_type.pk,
        )
        section, _ = NewsSection.objects.using(db_alias).get_or_create(
            slug="politica",
            defaults={"name": "Política", "sort_order": 10},
        )
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO news_newspage (
                    page_ptr_id,
                    publication_date,
                    summary,
                    body,
                    coverage_province,
                    coverage_district,
                    featured_image_id,
                    section_id,
                    school_id,
                    contains_identifiable_minors,
                    minor_publication_authorizations_verified,
                    sensitive_content
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    page_id,
                    timezone.datetime(2026, 7, 1).date(),
                    "Historical fictional summary.",
                    json.dumps(historical_body),
                    "Arequipa",
                    "Cercado",
                    None,
                    section.pk,
                    None,
                    False,
                    False,
                    False,
                ],
            )

        apps = migrate_to(NEWS_0004)
        ContentType = apps.get_model("contenttypes", "ContentType")
        MigratedNewsPage = apps.get_model("news", "NewsPage")
        Page = apps.get_model("wagtailcore", "Page")
        RevisionModel = apps.get_model("wagtailcore", "Revision")
        migrated_page = MigratedNewsPage.objects.using(db_alias).get(pk=page_id)

        migrated_body = list(migrated_page.body.raw_data)

        assert migrated_body == historical_body
        assert {block["type"] for block in migrated_body} == {
            "heading",
            "paragraph",
        }

        news_page_content_type = ContentType.objects.using(db_alias).get(
            app_label="news",
            model="newspage",
        )
        page_content_type = ContentType.objects.using(db_alias).get(
            app_label="wagtailcore",
            model="page",
        )
        revision_created_at = timezone.now()
        scheduled_at = revision_created_at + timezone.timedelta(days=2)
        heading_revision_content = {
            "pk": page_id,
            "title": "Historical Structured News",
            "slug": "historical-structured-news",
            "body": json.dumps(heading_revision_body),
            "custom_top_level_key": {"preserved": True},
        }
        mixed_revision_content = {
            "pk": page_id,
            "title": "Scheduled Historical Structured News",
            "slug": "historical-structured-news",
            "summary": "Historical revision summary kept only in revision JSON.",
            "body": json.dumps(mixed_revision_body),
            "custom_top_level_key": ["preserved", 2],
        }
        no_heading_revision_content = {
            "pk": page_id,
            "title": "Compatible Historical Structured News",
            "slug": "historical-structured-news",
            "body": json.dumps(no_heading_revision_body),
            "custom_top_level_key": "unchanged",
        }
        unrelated_revision_content = {
            "pk": home.pk,
            "title": "Inicio",
            "slug": home.slug,
            "body": json.dumps(unrelated_revision_body),
            "custom_top_level_key": "unrelated",
        }

        heading_revision = RevisionModel.objects.using(db_alias).create(
            content_type_id=news_page_content_type.pk,
            base_content_type_id=page_content_type.pk,
            object_id=str(page_id),
            created_at=revision_created_at,
            object_str="Historical Structured News",
            content=heading_revision_content,
        )
        mixed_revision = RevisionModel.objects.using(db_alias).create(
            content_type_id=news_page_content_type.pk,
            base_content_type_id=page_content_type.pk,
            object_id=str(page_id),
            created_at=revision_created_at,
            object_str="Scheduled Historical Structured News",
            content=mixed_revision_content,
            approved_go_live_at=scheduled_at,
        )
        no_heading_revision = RevisionModel.objects.using(db_alias).create(
            content_type_id=news_page_content_type.pk,
            base_content_type_id=page_content_type.pk,
            object_id=str(page_id),
            created_at=revision_created_at,
            object_str="Compatible Historical Structured News",
            content=no_heading_revision_content,
        )
        unrelated_revision = RevisionModel.objects.using(db_alias).create(
            content_type_id=page_content_type.pk,
            base_content_type_id=page_content_type.pk,
            object_id=str(home.pk),
            created_at=revision_created_at,
            object_str="Inicio",
            content=unrelated_revision_content,
        )
        revision_ids = [
            heading_revision.pk,
            mixed_revision.pk,
            no_heading_revision.pk,
            unrelated_revision.pk,
        ]
        Page._base_manager.using(db_alias).filter(pk=page_id).update(
            latest_revision_id=mixed_revision.pk,
            latest_revision_created_at=revision_created_at,
        )

        apps = migrate_to(NEWS_0005)
        FinalNewsPage = apps.get_model("news", "NewsPage")
        FinalPage = apps.get_model("wagtailcore", "Page")
        FinalRevision = apps.get_model("wagtailcore", "Revision")
        final_page = FinalNewsPage.objects.using(db_alias).get(pk=page_id)
        final_body = list(final_page.body.raw_data)

        assert final_body == [
            {
                "type": "paragraph",
                "value": ("<h2>Historical &lt;context&gt; &amp; evidence</h2>"),
                "id": "11111111-1111-4111-8111-111111111111",
            },
            historical_body[1],
        ]
        final_heading_revision = FinalRevision.objects.using(db_alias).get(
            pk=heading_revision.pk,
        )
        final_mixed_revision = FinalRevision.objects.using(db_alias).get(
            pk=mixed_revision.pk,
        )
        final_no_heading_revision = FinalRevision.objects.using(db_alias).get(
            pk=no_heading_revision.pk,
        )
        final_unrelated_revision = FinalRevision.objects.using(db_alias).get(
            pk=unrelated_revision.pk,
        )

        assert json.loads(final_heading_revision.content["body"]) == [
            {
                "type": "paragraph",
                "value": "<h2>Draft &lt;context&gt; &amp; evidence</h2>",
                "id": "33333333-3333-4333-8333-333333333333",
                "custom_item_key": "preserved",
            },
        ]
        assert json.loads(final_mixed_revision.content["body"]) == [
            mixed_revision_body[0],
            {
                "type": "paragraph",
                "value": "<h2>Scheduled heading</h2>",
                "id": "55555555-5555-4555-8555-555555555555",
            },
            mixed_revision_body[2],
        ]
        assert {
            key: value
            for key, value in final_heading_revision.content.items()
            if key != "body"
        } == {
            key: value
            for key, value in heading_revision_content.items()
            if key != "body"
        }
        assert {
            key: value
            for key, value in final_mixed_revision.content.items()
            if key != "body"
        } == {
            key: value for key, value in mixed_revision_content.items() if key != "body"
        }
        assert final_no_heading_revision.content == no_heading_revision_content
        assert final_unrelated_revision.content == unrelated_revision_content
        assert final_heading_revision.created_at == heading_revision.created_at
        assert final_mixed_revision.approved_go_live_at == scheduled_at
        assert final_mixed_revision.object_id == str(page_id)
        assert (
            FinalPage._base_manager.using(db_alias).get(pk=page_id).latest_revision_id
            == mixed_revision.pk
        )
        assert list(final_page.body.stream_block.child_blocks) == [
            "paragraph",
            "article_image",
            "youtube",
            "spotify",
        ]
        assert final_page.body.stream_block.child_blocks["paragraph"].features == [
            "bold",
            "italic",
            "link",
            "h2",
            "h3",
            "h4",
            "ol",
            "ul",
            "blockquote",
            "hr",
            "document-link",
        ]

        migrate_to(NEWS_0010)
        with connection.cursor() as cursor:
            columns = {
                column.name
                for column in connection.introspection.get_table_description(
                    cursor,
                    "news_newspage",
                )
            }
        assert "summary" not in columns
        migrate_to_latest()
        assert (
            Revision.objects.get(pk=mixed_revision.pk).content["summary"]
            == "Historical revision summary kept only in revision JSON."
        )
        reconstructed_page = Revision.objects.get(pk=mixed_revision.pk).as_object()
        reconstructed_body = list(reconstructed_page.body.raw_data)

        assert reconstructed_body == json.loads(final_mixed_revision.content["body"])
        assert all(item.get("type") != "heading" for item in reconstructed_body)
        assert not hasattr(reconstructed_page, "summary")
        assert reconstructed_page.featured_image_caption == ""
        assert reconstructed_page.featured_image_alt_text == ""
        assert reconstructed_page.featured_image_credit == ""
        assert reconstructed_page.og_image_caption == ""
        assert reconstructed_page.og_image_alt_text == ""
        assert reconstructed_page.og_image_credit == ""
    finally:
        if revision_ids:
            Revision.objects.filter(pk__in=revision_ids).delete()
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


@pytest.mark.django_db(transaction=True)
def test_epic5_001_migration_preserves_news_with_blank_safe_seo_defaults() -> None:
    try:
        apps = migrate_to(NEWS_0005)
        db_alias = connection.alias
        ContentType = apps.get_model("contenttypes", "ContentType")
        NewsSection = apps.get_model("news", "NewsSection")
        SiteModel = apps.get_model("wagtailcore", "Site")

        if not Site.objects.db_manager(db_alias).filter(is_default_site=True).exists():
            RuntimeLocale.objects.db_manager(db_alias).get_or_create(
                language_code="es",
            )
            root = RuntimePage.get_first_root_node()
            if root is None:
                root = RuntimePage.add_root(
                    instance=RuntimePage(title="Root", slug="root"),
                )
            home_page = RuntimeHomePage(
                title="Inicio",
                slug="inicio-epic5-001-migration-test",
            )
            root.add_child(instance=home_page)
            Site.objects.db_manager(db_alias).create(
                hostname="testserver",
                port=80,
                site_name="School Newsroom",
                root_page=home_page,
                is_default_site=True,
            )

        site = SiteModel.objects.using(db_alias).get(is_default_site=True)
        home = RuntimePage.objects.get(pk=site.root_page_id)
        base_child = RuntimePage(
            title="Historical SEO Fictional News",
            slug="historical-seo-news",
        )
        home.add_child(instance=base_child)
        news_page_content_type = ContentType.objects.using(db_alias).get(
            app_label="news",
            model="newspage",
        )
        RuntimePage.objects.filter(pk=base_child.pk).update(
            content_type_id=news_page_content_type.pk,
        )
        section, _ = NewsSection.objects.using(db_alias).get_or_create(
            slug="politica",
            defaults={"name": "Política", "sort_order": 10},
        )

        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO news_newspage (
                    page_ptr_id,
                    publication_date,
                    summary,
                    body,
                    coverage_province,
                    coverage_district,
                    featured_image_id,
                    section_id,
                    school_id,
                    contains_identifiable_minors,
                    minor_publication_authorizations_verified,
                    sensitive_content
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    base_child.pk,
                    timezone.datetime(2026, 7, 12).date(),
                    "Historical fictional summary.",
                    json.dumps(
                        [
                            {
                                "type": "paragraph",
                                "value": "<p>Historical fictional body.</p>",
                                "id": "99999999-9999-4999-8999-999999999999",
                            },
                        ],
                    ),
                    "Arequipa",
                    "",
                    None,
                    section.pk,
                    None,
                    False,
                    False,
                    False,
                ],
            )

        apps = migrate_to(NEWS_0006)
        MigratedNewsPage = apps.get_model("news", "NewsPage")
        migrated_page = MigratedNewsPage.objects.using(db_alias).get(
            pk=base_child.pk,
        )

        assert migrated_page.focus_keyphrase == ""
        assert migrated_page.og_title == ""
        assert migrated_page.og_description == ""
        assert migrated_page.og_image_id is None
        assert migrated_page.canonical_url == ""
        assert migrated_page.seo_noindex is False
        assert migrated_page.body[0].value.source == "<p>Historical fictional body.</p>"
    finally:
        migrate_to_latest()


@pytest.mark.django_db(transaction=True)
def test_epic5_009_migration_leaves_historical_news_without_related_phrases() -> None:
    page_id = None
    try:
        apps = migrate_to(NEWS_0014)
        ContentType = apps.get_model("contenttypes", "ContentType")
        HistoricalNewsPage = apps.get_model("news", "NewsPage")
        HistoricalPage = apps.get_model("wagtailcore", "Page")
        home = RuntimeHomePage.objects.first()
        if home is None:
            root = RuntimePage.get_first_root_node()
            if root is None:
                RuntimeLocale.objects.get_or_create(language_code="es")
                root = RuntimePage.add_root(
                    instance=RuntimePage(title="Root", slug="root")
                )
            home = RuntimeHomePage(title="Inicio", slug="inicio-epic5-009")
            root.add_child(instance=home)
        base_child = RuntimePage(
            title="Noticia histórica ficticia EPIC5-009",
            slug="noticia-historica-epic5-009",
            live=False,
        )
        home.add_child(instance=base_child)
        page_id = base_child.pk
        news_content_type = ContentType.objects.get(
            app_label="news",
            model="newspage",
        )
        HistoricalPage._base_manager.filter(pk=page_id).update(
            content_type_id=news_content_type.pk,
        )
        HistoricalNewsPage(
            page_ptr_id=page_id,
            publication_date=timezone.datetime(2026, 8, 3).date(),
            body=[
                {
                    "type": "paragraph",
                    "value": "<p>Contenido histórico ficticio.</p>",
                    "id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                }
            ],
            coverage_province="Arequipa",
            coverage_district="",
        ).save_base(raw=True, force_insert=True)

        apps = migrate_to(NEWS_0015)
        RelatedKeyphrase = apps.get_model("news", "NewsPageRelatedKeyphrase")

        assert not RelatedKeyphrase.objects.filter(page_id=page_id).exists()
    finally:
        if page_id is not None:
            Revision.objects.filter(object_id=str(page_id)).delete()
        migrate_to_latest()


@pytest.mark.django_db(transaction=True)
def test_epic3_006_migration_preserves_body_and_adds_table_schema() -> None:
    home_id = None
    page_id = None
    revision_id = None
    section_id = None
    try:
        apps = migrate_to(NEWS_0010)
        db_alias = connection.alias
        ContentType = apps.get_model("contenttypes", "ContentType")
        HistoricalNewsPage = apps.get_model("news", "NewsPage")
        HistoricalNewsSection = apps.get_model("news", "NewsSection")
        HistoricalPage = apps.get_model("wagtailcore", "Page")
        HistoricalRevision = apps.get_model("wagtailcore", "Revision")
        historical_body = HistoricalNewsPage._meta.get_field("body")
        assert "table" not in historical_body.stream_block.child_blocks

        # Historical Page models do not expose Treebeard's add_child API. Use
        # runtime Page classes only to create the isolated tree nodes, then use
        # the migration-state models for the NewsPage row and assertions.
        RuntimeLocale.objects.get_or_create(language_code="es")
        root = RuntimePage.get_first_root_node()
        if root is None:
            root = RuntimePage.add_root(
                instance=RuntimePage(title="Root", slug="root"),
            )
        home = RuntimeHomePage(
            title="Historical smart paste home",
            slug="historical-smart-paste-home",
        )
        root.add_child(instance=home)
        home_id = home.pk

        base_child = RuntimePage(
            title="Historical smart paste news",
            slug="historical-smart-paste-news",
            live=False,
        )
        home.add_child(instance=base_child)
        page_id = base_child.pk
        news_page_content_type = ContentType.objects.using(db_alias).get(
            app_label="news",
            model="newspage",
        )
        page_content_type = ContentType.objects.using(db_alias).get(
            app_label="wagtailcore",
            model="page",
        )
        HistoricalPage._base_manager.using(db_alias).filter(pk=page_id).update(
            content_type_id=news_page_content_type.pk,
        )

        section, _ = HistoricalNewsSection.objects.using(db_alias).get_or_create(
            slug="epic3-006-migration",
            defaults={"name": "EPIC3-006 migration", "sort_order": 999},
        )
        section_id = section.pk
        historical_body_data = [
            {
                "type": "paragraph",
                "value": "<p>Existing historical body.</p>",
                "id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            }
        ]
        historical_page = HistoricalNewsPage(
            page_ptr_id=page_id,
            publication_date=timezone.datetime(2026, 7, 28).date(),
            body=historical_body_data,
            section_id=section.pk,
            coverage_province="Arequipa",
        )
        historical_page.save_base(
            raw=True,
            using=db_alias,
            force_insert=True,
        )
        revision = HistoricalRevision.objects.using(db_alias).create(
            content_type_id=news_page_content_type.pk,
            base_content_type_id=page_content_type.pk,
            object_id=str(page_id),
            created_at=timezone.now(),
            object_str="Historical smart paste news",
            content={
                "pk": page_id,
                "title": "Historical smart paste news",
                "slug": "historical-smart-paste-news",
                "body": json.dumps(historical_body_data),
            },
        )
        revision_id = revision.pk

        apps = migrate_to(NEWS_0011)
        MigratedNewsPage = apps.get_model("news", "NewsPage")
        migrated_body = MigratedNewsPage._meta.get_field("body")
        migrated_page = MigratedNewsPage.objects.get(pk=page_id)

        assert list(migrated_body.stream_block.child_blocks) == [
            "paragraph",
            "article_image",
            "table",
            "youtube",
            "spotify",
        ]
        assert migrated_page.body[0].value.source == "<p>Existing historical body.</p>"
        table_value = migrated_body.stream_block.to_python(
            [
                {
                    "type": "table",
                    "value": {
                        "data": [["Nombre", "Valor"], ["Dato", "10"]],
                        "table_caption": "Tabla histórica",
                        "table_header_choice": "row",
                        "first_row_is_table_header": True,
                        "first_col_is_header": False,
                    },
                }
            ]
        )
        assert table_value[0].block_type == "table"
        assert table_value[0].value["data"][1] == ["Dato", "10"]
        MigratedRevision = apps.get_model("wagtailcore", "Revision")
        revision_body = json.loads(
            MigratedRevision.objects.using(db_alias).get(pk=revision_id).content["body"]
        )
        assert revision_body[0]["value"] == "<p>Existing historical body.</p>"
    finally:
        migrate_to_latest()
        if revision_id is not None:
            Revision.objects.filter(pk=revision_id).delete()
        if page_id is not None:
            page = RuntimePage.objects.filter(pk=page_id).first()
            if page is not None:
                page.delete()
        if home_id is not None:
            home = RuntimePage.objects.filter(pk=home_id).first()
            if home is not None:
                home.delete()
        if section_id is not None:
            RuntimeNewsSection.objects.filter(pk=section_id).delete()


@pytest.mark.django_db(transaction=True)
def test_epic3_010_migrates_legacy_attributions_without_rewriting_revisions():
    home_id = None
    page_id = None
    revision_id = None
    try:
        apps = migrate_to(NEWS_0019)
        db_alias = connection.alias
        ContentType = apps.get_model("contenttypes", "ContentType")
        HistoricalNewsPage = apps.get_model("news", "NewsPage")
        HistoricalPage = apps.get_model("wagtailcore", "Page")
        HistoricalSchool = apps.get_model("news", "School")
        HistoricalGroup = apps.get_model("news", "ContributorGroup")
        HistoricalMinor = apps.get_model("news", "MinorContributor")
        HistoricalCredit = apps.get_model("news", "NewsPagePublicCredit")
        HistoricalContributor = apps.get_model("news", "NewsPageContributor")
        HistoricalRevision = apps.get_model("wagtailcore", "Revision")

        RuntimeLocale.objects.get_or_create(language_code="es")
        root = RuntimePage.get_first_root_node()
        if root is None:
            root = RuntimePage.add_root(instance=RuntimePage(title="Root", slug="root"))
        home = RuntimeHomePage(title="EPIC3-010 home", slug="epic3-010-home")
        root.add_child(instance=home)
        home_id = home.pk
        base_page = RuntimePage(
            title="EPIC3-010 legacy news", slug="epic3-010-legacy-news", live=False
        )
        home.add_child(instance=base_page)
        page_id = base_page.pk
        news_content_type = ContentType.objects.using(db_alias).get(
            app_label="news", model="newspage"
        )
        HistoricalPage._base_manager.using(db_alias).filter(pk=page_id).update(
            content_type_id=news_content_type.pk
        )
        HistoricalNewsPage(
            page_ptr_id=page_id,
            publication_date=timezone.datetime(2026, 8, 1).date(),
            body=[
                {
                    "type": "paragraph",
                    "value": "<p>Historical attribution body.</p>",
                    "id": "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
                }
            ],
            coverage_department_id="04",
        ).save_base(raw=True, using=db_alias, force_insert=True)
        school = HistoricalSchool.objects.using(db_alias).create(
            name="Historical fictional school", department_id="04"
        )
        minor = HistoricalMinor.objects.using(db_alias).create(
            full_name="Historical private minor",
            group=HistoricalGroup.objects.using(db_alias).create(
                name="Historical fictional group", school=school
            ),
            age_band="under_14",
        )
        HistoricalCredit.objects.using(db_alias).create(
            page_id=page_id, display_name="First historical credit", sort_order=3
        )
        HistoricalCredit.objects.using(db_alias).create(
            page_id=page_id, display_name="Second historical credit", sort_order=4
        )
        HistoricalContributor.objects.using(db_alias).create(
            page_id=page_id, contributor_id=minor.pk, sort_order=0
        )
        revision = HistoricalRevision.objects.using(db_alias).create(
            content_type_id=news_content_type.pk,
            base_content_type_id=news_content_type.pk,
            object_id=str(page_id),
            created_at=timezone.now(),
            object_str="EPIC3-010 legacy news",
            content={"pk": page_id, "title": "EPIC3-010 legacy news"},
        )
        revision_id = revision.pk

        apps = migrate_to(NEWS_0020)
        MigratedAttribution = apps.get_model("news", "NewsPageAttribution")
        HistoricalAuthorProfile = apps.get_model("news", "AuthorProfile")
        MigratedRevision = apps.get_model("wagtailcore", "Revision")
        HistoricalAuthorProfile.objects.using(db_alias).create(
            display_name="Historical minor author",
            slug="historical-minor-author",
            minor_contributor_id=minor.pk,
            email="historical-minor@example.invalid",
        )
        assert list(
            MigratedAttribution.objects.using(db_alias)
            .filter(page_id=page_id)
            .values_list("kind", "display_name", "minor_contributor_id", "sort_order")
        ) == [
            ("PUBLIC_CREDIT", "First historical credit", None, 0),
            ("PUBLIC_CREDIT", "Second historical credit", None, 1),
            ("INTERNAL_CONTRIBUTOR", "", minor.pk, 2),
        ]
        assert (
            MigratedRevision.objects.using(db_alias).filter(pk=revision_id).count() == 1
        )

        apps = migrate_to(NEWS_0021)
        MigratedAuthorProfile = apps.get_model("news", "AuthorProfile")
        assert (
            MigratedAuthorProfile.objects.using(db_alias)
            .get(slug="historical-minor-author")
            .email
            == ""
        )

        migrate_to_latest()
        legacy_revision = Revision.objects.get(pk=revision_id)
        assert legacy_revision.as_object().pk == page_id
        page = RuntimeNewsPage.objects.get(pk=page_id)
        post_migration_revision = page.save_revision()
        assert "attributions" in post_migration_revision.content
        assert post_migration_revision.as_object().attributions.count() == 3
    finally:
        migrate_to_latest()
        if revision_id is not None:
            Revision.objects.filter(pk=revision_id).delete()
        if page_id is not None:
            page = RuntimePage.objects.filter(pk=page_id).first()
            if page is not None:
                page.delete()
        if home_id is not None:
            home = RuntimePage.objects.filter(pk=home_id).first()
            if home is not None:
                home.delete()


@pytest.mark.django_db(transaction=True)
def test_epic3_009_migrates_current_page_and_revision_relation_shape() -> None:
    home_id = None
    page_id = None
    revision_id = None
    try:
        apps = migrate_to(NEWS_0011)
        db_alias = connection.alias
        ContentType = apps.get_model("contenttypes", "ContentType")
        HistoricalNewsPage = apps.get_model("news", "NewsPage")
        HistoricalNewsSection = apps.get_model("news", "NewsSection")
        HistoricalPage = apps.get_model("wagtailcore", "Page")
        HistoricalRevision = apps.get_model("wagtailcore", "Revision")

        RuntimeLocale.objects.get_or_create(language_code="es")
        root = RuntimePage.get_first_root_node()
        if root is None:
            root = RuntimePage.add_root(
                instance=RuntimePage(title="Root", slug="root"),
            )
        home = RuntimeHomePage(
            title="Historical taxonomy home",
            slug="historical-taxonomy-home",
        )
        root.add_child(instance=home)
        home_id = home.pk
        base_child = RuntimePage(
            title="Historical taxonomy news",
            slug="historical-taxonomy-news",
            live=False,
        )
        home.add_child(instance=base_child)
        page_id = base_child.pk

        news_page_content_type, _ = ContentType.objects.db_manager(
            db_alias
        ).get_or_create(app_label="news", model="newspage")
        page_content_type, _ = ContentType.objects.db_manager(db_alias).get_or_create(
            app_label="wagtailcore", model="page"
        )
        HistoricalPage._base_manager.using(db_alias).filter(pk=page_id).update(
            content_type_id=news_page_content_type.pk,
        )
        seeded_sections = {}
        for name, slug, sort_order in [
            ("Política", "politica", 10),
            ("Cultura", "cultura", 20),
            ("Medio Ambiente", "medio-ambiente", 30),
            ("Problemáticas Sociales", "problematicas-sociales", 40),
            ("Columnas", "columnas", 50),
            ("Entrevistas", "entrevistas", 60),
        ]:
            seeded_sections[slug], _ = HistoricalNewsSection.objects.using(
                db_alias
            ).get_or_create(
                slug=slug,
                defaults={"name": name, "sort_order": sort_order},
            )
        section = seeded_sections["politica"]
        body_data = [
            {
                "type": "paragraph",
                "value": "<p>Historical taxonomy body.</p>",
                "id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
            }
        ]
        HistoricalNewsPage(
            page_ptr_id=page_id,
            publication_date=timezone.datetime(2026, 7, 31).date(),
            body=body_data,
            section_id=section.pk,
            coverage_province="Arequipa",
        ).save_base(raw=True, using=db_alias, force_insert=True)
        revision = HistoricalRevision.objects.using(db_alias).create(
            content_type_id=news_page_content_type.pk,
            base_content_type_id=page_content_type.pk,
            object_id=str(page_id),
            created_at=timezone.now(),
            object_str="Historical taxonomy news",
            content={
                "pk": page_id,
                "title": "Historical taxonomy news",
                "slug": "historical-taxonomy-news",
                "publication_date": "2026-07-31",
                "coverage_province": "Arequipa",
                "body": json.dumps(body_data),
                "section": section.pk,
            },
        )
        revision_id = revision.pk

        apps = migrate_to(NEWS_0014)
        MigratedNewsPageSection = apps.get_model("news", "NewsPageSection")
        MigratedRevision = apps.get_model("wagtailcore", "Revision")
        migrated_revision = MigratedRevision.objects.using(db_alias).get(pk=revision_id)

        assert list(
            MigratedNewsPageSection.objects.using(db_alias)
            .filter(page_id=page_id)
            .values_list("section_id", flat=True)
        ) == [section.pk]
        assert "section" not in migrated_revision.content
        assert migrated_revision.content["section_assignments"] == [
            {"pk": None, "page": page_id, "section": section.pk}
        ]

        migrate_to(NEWS_0015)
        migrate_to_latest()
        reconstructed = Revision.objects.get(pk=revision_id).as_object()
        assert list(
            reconstructed.section_assignments.values_list("section_id", flat=True)
        ) == [section.pk]
        assert reconstructed.body[0].value.source == (
            "<p>Historical taxonomy body.</p>"
        )
        # Pre-ticket revisions intentionally keep their legacy geography. An
        # editor must choose normalized coverage before creating a new revision.
        assert reconstructed.coverage_department_id is None
        reconstructed.coverage_department_id = "04"
        reconstructed.coverage_district_id = None
        round_trip = reconstructed.save_revision()
        round_trip_object = round_trip.as_object()
        assert list(
            round_trip_object.section_assignments.values_list("section_id", flat=True)
        ) == [section.pk]
        assert round_trip_object.body[0].value.source == (
            "<p>Historical taxonomy body.</p>"
        )
    finally:
        migrate_to_latest()
        if revision_id is not None:
            Revision.objects.filter(pk=revision_id).delete()
        if page_id is not None:
            page = RuntimePage.objects.filter(pk=page_id).first()
            if page is not None:
                page.delete()
        if home_id is not None:
            home = RuntimePage.objects.filter(pk=home_id).first()
            if home is not None:
                home.delete()


@pytest.mark.django_db(transaction=True)
def test_epic3_009_provisional_bootstrap_is_idempotent_and_conflicts_fail() -> None:
    try:
        apps = migrate_to(NEWS_0012)
        NewsSection = apps.get_model("news", "NewsSection")
        db_alias = connection.alias
        for name, slug, sort_order in [
            ("Política", "politica", 10),
            ("Cultura", "cultura", 20),
            ("Medio Ambiente", "medio-ambiente", 30),
            ("Problemáticas Sociales", "problematicas-sociales", 40),
            ("Columnas", "columnas", 50),
            ("Entrevistas", "entrevistas", 60),
        ]:
            NewsSection.objects.using(db_alias).get_or_create(
                slug=slug,
                defaults={"name": name, "sort_order": sort_order},
            )
        culture = NewsSection.objects.using(db_alias).get(slug="cultura")
        NewsSection.objects.using(db_alias).create(
            name="Conflicting music",
            slug="musica",
            sort_order=999,
        )

        with pytest.raises(ImproperlyConfigured, match="incompatible identity"):
            with transaction.atomic():
                taxonomy_migration_module().migrate_pages_and_revisions(
                    apps,
                    migration_schema_editor(),
                )

        NewsSection.objects.using(db_alias).filter(slug="musica").delete()
        migration = taxonomy_migration_module()
        migration.migrate_pages_and_revisions(apps, migration_schema_editor())
        migration.migrate_pages_and_revisions(apps, migration_schema_editor())

        assert NewsSection.objects.using(db_alias).filter(slug="musica").count() == 1
        assert (
            NewsSection.objects.using(db_alias).get(slug="musica").parent_id
            == culture.pk
        )
        assert (
            NewsSection.objects.using(db_alias).filter(parent_id__isnull=False).count()
            == 18
        )
    finally:
        migrate_to_latest()


@pytest.mark.django_db(transaction=True)
def test_epic3_009_reverse_fails_before_collapsing_multiple_assignments() -> None:
    page_id = None
    home_id = None
    try:
        migrate_to_latest()
        RuntimeLocale.objects.get_or_create(language_code="es")
        root = RuntimePage.get_first_root_node()
        if root is None:
            root = RuntimePage.add_root(
                instance=RuntimePage(title="Root", slug="root"),
            )
        home = RuntimeHomePage(
            title="Reverse taxonomy home",
            slug="reverse-taxonomy-home",
        )
        root.add_child(instance=home)
        home_id = home.pk
        page = RuntimeNewsPage(
            title="Reverse taxonomy news",
            slug="reverse-taxonomy-news",
            live=False,
            publication_date=timezone.datetime(2026, 7, 31).date(),
            body=[("paragraph", "<p>Reverse taxonomy body.</p>")],
            coverage_department_id="04",
            coverage_district_id=None,
        )
        home.add_child(instance=page)
        page_id = page.pk
        politics, _ = RuntimeNewsSection.objects.get_or_create(
            slug="politica",
            defaults={"name": "Política", "sort_order": 10},
        )
        culture, _ = RuntimeNewsSection.objects.get_or_create(
            slug="cultura",
            defaults={"name": "Cultura", "sort_order": 20},
        )
        RuntimeNewsPageSection.objects.create(
            page=page,
            section=politics,
        )
        RuntimeNewsPageSection.objects.create(
            page=page,
            section=culture,
        )
        executor = MigrationExecutor(connection)
        historical_apps = executor.loader.project_state([NEWS_0013]).apps

        with pytest.raises(ImproperlyConfigured, match="cannot reverse"):
            taxonomy_migration_module().restore_singular_sections(
                historical_apps,
                migration_schema_editor(),
            )

        assert RuntimeNewsPageSection.objects.filter(page_id=page_id).count() == 2
    finally:
        if page_id is not None:
            page = RuntimePage.objects.filter(pk=page_id).first()
            if page is not None:
                page.delete()
        if home_id is not None:
            home = RuntimePage.objects.filter(pk=home_id).first()
            if home is not None:
                home.delete()


@pytest.mark.django_db(transaction=True)
def test_epic3_009_reverse_preserves_an_unclassified_page_as_null() -> None:
    page_id = None
    home_id = None
    try:
        apps = migrate_to(NEWS_0013)
        ContentType = apps.get_model("contenttypes", "ContentType")
        HistoricalNewsPage = apps.get_model("news", "NewsPage")
        HistoricalPage = apps.get_model("wagtailcore", "Page")
        RuntimeLocale.objects.get_or_create(language_code="es")
        root = RuntimePage.get_first_root_node()
        if root is None:
            root = RuntimePage.add_root(
                instance=RuntimePage(title="Root", slug="root"),
            )
        home = RuntimeHomePage(
            title="Unclassified reverse home",
            slug="unclassified-reverse-home",
        )
        root.add_child(instance=home)
        home_id = home.pk
        base_child = RuntimePage(
            title="Unclassified reverse news",
            slug="unclassified-reverse-news",
            live=False,
        )
        home.add_child(instance=base_child)
        page_id = base_child.pk
        news_content_type = ContentType.objects.get(
            app_label="news",
            model="newspage",
        )
        HistoricalPage._base_manager.filter(pk=page_id).update(
            content_type_id=news_content_type.pk,
        )
        HistoricalNewsPage(
            page_ptr_id=page_id,
            publication_date=timezone.datetime(2026, 7, 31).date(),
            body=[
                {
                    "type": "paragraph",
                    "value": "<p>Unclassified reverse body.</p>",
                    "id": "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
                }
            ],
            coverage_province="Arequipa",
            coverage_district="",
            section_id=None,
        ).save_base(raw=True, force_insert=True)

        apps = migrate_to(NEWS_0012)
        HistoricalNewsPage = apps.get_model("news", "NewsPage")

        assert HistoricalNewsPage.objects.get(pk=page_id).section_id is None
    finally:
        migrate_to_latest()
        if page_id is not None:
            page = RuntimePage.objects.filter(pk=page_id).first()
            if page is not None:
                page.delete()
        if home_id is not None:
            home = RuntimePage.objects.filter(pk=home_id).first()
            if home is not None:
                home.delete()


@pytest.mark.django_db(transaction=True)
def test_public_news_search_migration_is_forward_and_reverse_reproducible():
    try:
        migrate_to(NEWS_0015)
        migrate_to(NEWS_0016)
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT extname FROM pg_extension "
                "WHERE extname IN ('pg_trgm', 'unaccent')"
            )
            extensions = {row[0] for row in cursor.fetchall()}
            cursor.execute(
                "SELECT 1 FROM pg_ts_config WHERE cfgname = 'school_newsroom_es'"
            )
            config_exists = cursor.fetchone() is not None
            cursor.execute("SELECT 1 FROM pg_proc WHERE proname = 'f_unaccent'")
            function_exists = cursor.fetchone() is not None
            cursor.execute(
                "SELECT indexname FROM pg_indexes "
                "WHERE tablename = 'wagtailsearch_indexentry'"
            )
            indexes = {row[0] for row in cursor.fetchall()}

        assert extensions == {"pg_trgm", "unaccent"}
        assert config_exists
        assert function_exists
        assert {
            "news_archive_title_text_unaccent_trgm",
            "news_archive_body_text_unaccent_trgm",
        }.issubset(indexes)

        migrate_to(NEWS_0015)
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT extname FROM pg_extension "
                "WHERE extname IN ('pg_trgm', 'unaccent')"
            )
            assert {row[0] for row in cursor.fetchall()} == {"pg_trgm", "unaccent"}
            cursor.execute(
                "SELECT 1 FROM pg_ts_config WHERE cfgname = 'school_newsroom_es'"
            )
            assert cursor.fetchone() is None
            cursor.execute("SELECT 1 FROM pg_proc WHERE proname = 'f_unaccent'")
            assert cursor.fetchone() is None
            cursor.execute(
                "SELECT indexname FROM pg_indexes "
                "WHERE tablename = 'wagtailsearch_indexentry'"
            )
            indexes = {row[0] for row in cursor.fetchall()}
            assert "news_archive_title_text_unaccent_trgm" not in indexes
            assert "news_archive_body_text_unaccent_trgm" not in indexes
    finally:
        migrate_to_latest()


@pytest.mark.django_db(transaction=True)
def test_geography_migrations_backfill_legacy_rows_and_support_new_revisions():
    page_id = None
    home_id = None
    try:
        apps = migrate_to([NEWS_0016, GEOGRAPHY_0002])
        HistoricalSchool = apps.get_model("news", "School")
        HistoricalNewsPage = apps.get_model("news", "NewsPage")
        HistoricalPage = apps.get_model("wagtailcore", "Page")
        ContentTypeModel = apps.get_model("contenttypes", "ContentType")
        database = connection.alias

        school = HistoricalSchool.objects.using(database).create(
            name="Legacy geography school",
            province="Legacy province",
            district="Legacy district",
        )
        RuntimeLocale.objects.get_or_create(language_code="es")
        root = RuntimePage.get_first_root_node()
        if root is None:
            root = RuntimePage.add_root(instance=RuntimePage(title="Root", slug="root"))
        home = RuntimeHomePage(
            title="Legacy geography home", slug="legacy-geography-home"
        )
        root.add_child(instance=home)
        home_id = home.pk
        base_child = RuntimePage(
            title="Legacy geography news",
            slug="legacy-geography-news",
            live=False,
        )
        home.add_child(instance=base_child)
        page_id = base_child.pk
        news_content_type = ContentTypeModel.objects.db_manager(database).get(
            app_label="news",
            model="newspage",
        )
        HistoricalPage._base_manager.using(database).filter(pk=page_id).update(
            content_type_id=news_content_type.pk,
        )
        HistoricalNewsPage(
            page_ptr_id=page_id,
            publication_date=timezone.datetime(2026, 8, 1).date(),
            body=[
                {
                    "type": "paragraph",
                    "value": "<p>Legacy geography body.</p>",
                    "id": "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
                }
            ],
            coverage_province="Legacy province",
            coverage_district="Legacy district",
        ).save_base(raw=True, using=database, force_insert=True)

        apps = migrate_to([NEWS_0019, GEOGRAPHY_0002])
        MigratedSchool = apps.get_model("news", "School")
        MigratedNewsPage = apps.get_model("news", "NewsPage")
        migrated_school = MigratedSchool.objects.get(pk=school.pk)
        migrated_page = MigratedNewsPage.objects.get(pk=page_id)

        assert migrated_school.department_id == "04"
        assert migrated_school.district_id is None
        assert migrated_page.coverage_department_id == "04"
        assert migrated_page.coverage_district_id is None
        assert not any(
            field.name == "province" for field in MigratedSchool._meta.fields
        )
        assert not any(
            field.name == "coverage_province" for field in MigratedNewsPage._meta.fields
        )

        migrate_to_latest()
        runtime_page = RuntimeNewsPage.objects.get(pk=page_id)
        revision = runtime_page.save_revision()
        reopened = revision.as_object()
        assert reopened.coverage_department_id == "04"
        assert reopened.coverage_district_id is None
    finally:
        migrate_to_latest()
        if page_id is not None:
            page = RuntimePage.objects.filter(pk=page_id).first()
            if page is not None:
                page.delete()
        if home_id is not None:
            home = RuntimePage.objects.filter(pk=home_id).first()
            if home is not None:
                home.delete()
