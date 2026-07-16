from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from wagtail.models import (
    Collection,
    GroupApprovalTask,
    GroupCollectionPermission,
    GroupPagePermission,
    Task,
    Workflow,
    WorkflowPage,
    WorkflowTask,
)

from apps.home.models import HomePage
from apps.news.access import (
    DIRECTOR_GROUP_NAME,
    FINAL_REVIEW_TASK_NAME,
    FULL_EDITOR_PERMISSION,
    LEGACY_WORKFLOW_NAME,
    SEO_CURATOR_GROUP_NAME,
    SEO_EDITOR_PERMISSION,
    SEO_TASK_NAME,
    WORKFLOW_NAME,
)


def get_permission(app_label: str, model: str, codename: str) -> Permission:
    try:
        return Permission.objects.get(
            content_type__app_label=app_label,
            content_type__model=model,
            codename=codename,
        )
    except Permission.DoesNotExist as error:
        raise CommandError(
            f"Required permission {app_label}.{codename} is unavailable. "
            "Run migrations before bootstrapping MVP access."
        ) from error


def get_custom_permission(permission_name: str) -> Permission:
    app_label, codename = permission_name.split(".", maxsplit=1)
    return get_permission(app_label, "newspage", codename)


def get_or_create_group_task(name: str, group: Group) -> GroupApprovalTask:
    existing_task = Task.objects.filter(name=name).first()
    if existing_task is None:
        task = GroupApprovalTask.objects.create(name=name)
    else:
        specific_task = existing_task.specific
        if not isinstance(specific_task, GroupApprovalTask):
            raise CommandError(
                f"Task '{name}' already exists with an incompatible task type."
            )
        task = specific_task

    if not task.active:
        task.active = True
        task.save(update_fields=["active"])
    task.groups.set([group])
    return task


class Command(BaseCommand):
    help = "Configure idempotent MVP CMS groups, permissions, and workflow."

    def add_arguments(self, parser):
        parser.add_argument(
            "--director",
            action="append",
            default=[],
            dest="director_usernames",
            metavar="LOGIN",
            help="Assign an existing user to Director/editor; repeat as needed.",
        )
        parser.add_argument(
            "--seo-curator",
            action="append",
            default=[],
            dest="seo_usernames",
            metavar="LOGIN",
            help="Assign an existing user to Curador SEO; repeat as needed.",
        )
        parser.add_argument(
            "--combined-user",
            action="append",
            default=[],
            dest="combined_usernames",
            metavar="LOGIN",
            help="Assign an existing non-superuser to both MVP groups.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        home_pages = list(HomePage.objects.order_by("pk")[:2])
        if len(home_pages) != 1:
            raise CommandError(
                "Exactly one Inicio HomePage is required before bootstrapping access."
            )
        home_page = home_pages[0]

        director_group, _ = Group.objects.get_or_create(name=DIRECTOR_GROUP_NAME)
        seo_group, _ = Group.objects.get_or_create(name=SEO_CURATOR_GROUP_NAME)

        self._configure_global_permissions(director_group, seo_group)
        self._configure_page_permissions(director_group, seo_group, home_page)
        self._configure_collection_permissions(director_group, seo_group)
        workflow = self._configure_workflow(director_group, seo_group)
        WorkflowPage.objects.update_or_create(
            page=home_page,
            defaults={"workflow": workflow},
        )

        self._assign_users(
            options["director_usernames"],
            [director_group],
        )
        self._assign_users(
            options["seo_usernames"],
            [seo_group],
        )
        self._assign_users(
            options["combined_usernames"],
            [director_group, seo_group],
        )

        self.stdout.write(
            self.style.SUCCESS(
                "MVP access configured: Director/editor, Curador SEO, "
                "Revisión editorial, and the Inicio subtree assignment."
            )
        )

    def _configure_global_permissions(
        self,
        director_group: Group,
        seo_group: Group,
    ) -> None:
        access_admin = get_permission("wagtailadmin", "admin", "access_admin")
        full_editor = get_custom_permission(FULL_EDITOR_PERMISSION)
        seo_editor = get_custom_permission(SEO_EDITOR_PERMISSION)

        snippet_permissions = Permission.objects.filter(
            content_type__app_label="news",
            content_type__model__in=[
                "newssection",
                "school",
                "contributorgroup",
                "minorcontributor",
            ],
            codename__in=[
                "add_newssection",
                "change_newssection",
                "delete_newssection",
                "view_newssection",
                "add_school",
                "change_school",
                "delete_school",
                "view_school",
                "add_contributorgroup",
                "change_contributorgroup",
                "delete_contributorgroup",
                "view_contributorgroup",
                "add_minorcontributor",
                "change_minorcontributor",
                "delete_minorcontributor",
                "view_minorcontributor",
            ],
        )
        if snippet_permissions.count() != 16:
            raise CommandError(
                "The expected editorial snippet permissions are incomplete."
            )

        director_group.permissions.set(
            [access_admin, full_editor, seo_editor, *snippet_permissions]
        )
        seo_group.permissions.set([access_admin, seo_editor])

    def _configure_page_permissions(
        self,
        director_group: Group,
        seo_group: Group,
        home_page: HomePage,
    ) -> None:
        GroupPagePermission.objects.filter(
            group__in=[director_group, seo_group]
        ).delete()

        permissions = [
            get_permission("wagtailcore", "page", codename)
            for codename in ("add_page", "change_page", "publish_page")
        ]
        GroupPagePermission.objects.bulk_create(
            [
                GroupPagePermission(
                    group=director_group,
                    page=home_page,
                    permission=permission,
                )
                for permission in permissions
            ]
        )

    def _configure_collection_permissions(
        self,
        director_group: Group,
        seo_group: Group,
    ) -> None:
        root_collection = Collection.get_first_root_node()
        GroupCollectionPermission.objects.filter(
            group__in=[director_group, seo_group]
        ).delete()

        director_permissions = [
            get_permission("wagtailimages", "image", codename)
            for codename in ("add_image", "change_image", "choose_image")
        ] + [
            get_permission("wagtaildocs", "document", codename)
            for codename in (
                "add_document",
                "change_document",
                "choose_document",
            )
        ]
        seo_permissions = [get_permission("wagtailimages", "image", "choose_image")]
        GroupCollectionPermission.objects.bulk_create(
            [
                GroupCollectionPermission(
                    group=director_group,
                    collection=root_collection,
                    permission=permission,
                )
                for permission in director_permissions
            ]
            + [
                GroupCollectionPermission(
                    group=seo_group,
                    collection=root_collection,
                    permission=permission,
                )
                for permission in seo_permissions
            ]
        )

    def _configure_workflow(
        self,
        director_group: Group,
        seo_group: Group,
    ) -> Workflow:
        seo_task = get_or_create_group_task(SEO_TASK_NAME, seo_group)
        final_task = get_or_create_group_task(
            FINAL_REVIEW_TASK_NAME,
            director_group,
        )
        workflow = self._get_or_create_workflow()
        if not workflow.active:
            workflow.active = True
            workflow.save(update_fields=["active"])

        expected_tasks = (seo_task, final_task)
        WorkflowTask.objects.filter(workflow=workflow).exclude(
            task__in=expected_tasks
        ).delete()
        for sort_order, task in enumerate(expected_tasks):
            WorkflowTask.objects.update_or_create(
                workflow=workflow,
                task=task,
                defaults={"sort_order": sort_order},
            )
        return workflow

    def _get_or_create_workflow(self) -> Workflow:
        workflow = Workflow.objects.filter(name=WORKFLOW_NAME).first()
        legacy_workflow = Workflow.objects.filter(
            name=LEGACY_WORKFLOW_NAME,
        ).first()

        if workflow and legacy_workflow and workflow.pk != legacy_workflow.pk:
            raise CommandError(
                f"Both '{WORKFLOW_NAME}' and '{LEGACY_WORKFLOW_NAME}' exist. "
                "Resolve the duplicate workflows before running the bootstrap."
            )
        if workflow:
            return workflow
        if legacy_workflow:
            legacy_workflow.name = WORKFLOW_NAME
            legacy_workflow.save(update_fields=["name"])
            return legacy_workflow
        return Workflow.objects.create(name=WORKFLOW_NAME)

    def _assign_users(self, logins: list[str], groups: list[Group]) -> None:
        user_model = get_user_model()
        login_field = user_model.USERNAME_FIELD
        for login in dict.fromkeys(logins):
            try:
                user = user_model._default_manager.get(**{login_field: login})
            except user_model.DoesNotExist as error:
                raise CommandError(
                    f"No existing user has {login_field}={login!r}; "
                    "no user was created."
                ) from error
            user.groups.add(*groups)
