import importlib
import json
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

from apps.home.models import HomePage as RuntimeHomePage

NEWS_0001 = ("news", "0001_initial")
NEWS_0002 = ("news", "0002_bootstrap_editorial_data")
NEWS_0003 = ("news", "0003_newspage_contains_identifiable_minors_and_more")
NEWS_0004 = ("news", "0004_alter_newspage_body")
NEWS_0005 = ("news", "0005_alter_newspage_body")
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

        reconstructed_page = Revision.objects.get(pk=mixed_revision.pk).as_object()
        reconstructed_body = list(reconstructed_page.body.raw_data)

        assert reconstructed_body == json.loads(final_mixed_revision.content["body"])
        assert all(item.get("type") != "heading" for item in reconstructed_body)
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
