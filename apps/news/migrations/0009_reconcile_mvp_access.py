from django.core.exceptions import ImproperlyConfigured
from django.db import migrations


OBSOLETE_GROUP_NAMES = ("Moderadores", "Editores")
OBSOLETE_WORKFLOW_NAME = "Aprobación de moderadores"
OBSOLETE_TASK_NAME = "Aprobación de moderadores"
LEGACY_MVP_WORKFLOW_NAME = "Revisión editorial MVP"
MVP_WORKFLOW_NAME = "Revisión editorial"


def _fail(message):
    raise ImproperlyConfigured(f"EPIC4-001 access cleanup stopped: {message}")


def reconcile_mvp_access(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    GroupApprovalTask = apps.get_model("wagtailcore", "GroupApprovalTask")
    Task = apps.get_model("wagtailcore", "Task")
    TaskState = apps.get_model("wagtailcore", "TaskState")
    Workflow = apps.get_model("wagtailcore", "Workflow")
    WorkflowPage = apps.get_model("wagtailcore", "WorkflowPage")
    WorkflowState = apps.get_model("wagtailcore", "WorkflowState")
    WorkflowTask = apps.get_model("wagtailcore", "WorkflowTask")
    db_alias = schema_editor.connection.alias

    obsolete_groups = list(
        Group.objects.using(db_alias).filter(name__in=OBSOLETE_GROUP_NAMES)
    )
    obsolete_group_ids = {group.pk for group in obsolete_groups}
    for group in obsolete_groups:
        if group.user_set.using(db_alias).exists():
            _fail(
                f"group '{group.name}' still has assigned users; reassign or remove "
                "those memberships before retrying the migration."
            )

    task_matches = list(
        Task.objects.using(db_alias).filter(name=OBSOLETE_TASK_NAME)
    )
    if len(task_matches) > 1:
        _fail(
            f"more than one task is named '{OBSOLETE_TASK_NAME}'; resolve the "
            "ambiguous historical records before retrying."
        )
    obsolete_task = task_matches[0] if task_matches else None
    obsolete_group_task = None
    if obsolete_task:
        obsolete_group_task = (
            GroupApprovalTask.objects.using(db_alias)
            .filter(pk=obsolete_task.pk)
            .first()
        )
        if obsolete_group_task is None:
            _fail(
                f"task '{OBSOLETE_TASK_NAME}' is not a group approval task."
            )
        if TaskState.objects.using(db_alias).filter(task=obsolete_task).exists():
            _fail(
                f"task '{OBSOLETE_TASK_NAME}' has task-state history and cannot "
                "be removed automatically."
            )
        unexpected_task_group_ids = set(
            obsolete_group_task.groups.using(db_alias).values_list("pk", flat=True)
        ) - obsolete_group_ids
        if unexpected_task_group_ids:
            _fail(
                f"task '{OBSOLETE_TASK_NAME}' references non-obsolete groups."
            )

    for group in obsolete_groups:
        related_tasks = GroupApprovalTask.objects.using(db_alias).filter(groups=group)
        if obsolete_group_task:
            related_tasks = related_tasks.exclude(pk=obsolete_group_task.pk)
        if related_tasks.exists():
            _fail(
                f"group '{group.name}' is used by another workflow task."
            )

    workflow_matches = list(
        Workflow.objects.using(db_alias).filter(name=OBSOLETE_WORKFLOW_NAME)
    )
    if len(workflow_matches) > 1:
        _fail(
            f"more than one workflow is named '{OBSOLETE_WORKFLOW_NAME}'."
        )
    obsolete_workflow = workflow_matches[0] if workflow_matches else None
    if obsolete_workflow:
        if (
            WorkflowState.objects.using(db_alias)
            .filter(workflow=obsolete_workflow)
            .exists()
        ):
            _fail(
                f"workflow '{OBSOLETE_WORKFLOW_NAME}' has workflow-state history "
                "and cannot be removed automatically."
            )
        unexpected_workflow_tasks = WorkflowTask.objects.using(db_alias).filter(
            workflow=obsolete_workflow
        )
        if obsolete_task:
            unexpected_workflow_tasks = unexpected_workflow_tasks.exclude(
                task=obsolete_task
            )
        if unexpected_workflow_tasks.exists():
            _fail(
                f"workflow '{OBSOLETE_WORKFLOW_NAME}' references an unexpected task."
            )
        if (
            WorkflowPage.objects.using(db_alias)
            .filter(workflow=obsolete_workflow)
            .exclude(page__depth=1)
            .exists()
        ):
            _fail(
                f"workflow '{OBSOLETE_WORKFLOW_NAME}' is assigned outside the "
                "historical root page."
            )

    if obsolete_task:
        task_workflows = WorkflowTask.objects.using(db_alias).filter(
            task=obsolete_task
        )
        if obsolete_workflow:
            task_workflows = task_workflows.exclude(workflow=obsolete_workflow)
        if task_workflows.exists():
            _fail(
                f"task '{OBSOLETE_TASK_NAME}' is used by another workflow."
            )

    legacy_workflow = (
        Workflow.objects.using(db_alias)
        .filter(name=LEGACY_MVP_WORKFLOW_NAME)
        .first()
    )
    current_workflow = (
        Workflow.objects.using(db_alias).filter(name=MVP_WORKFLOW_NAME).first()
    )
    if legacy_workflow and current_workflow:
        _fail(
            f"both '{LEGACY_MVP_WORKFLOW_NAME}' and '{MVP_WORKFLOW_NAME}' exist; "
            "resolve the duplicate workflows before retrying."
        )

    if legacy_workflow:
        legacy_workflow.name = MVP_WORKFLOW_NAME
        legacy_workflow.save(using=db_alias, update_fields=["name"])

    if obsolete_workflow:
        WorkflowPage.objects.using(db_alias).filter(
            workflow=obsolete_workflow
        ).delete()
        WorkflowTask.objects.using(db_alias).filter(
            workflow=obsolete_workflow
        ).delete()
        obsolete_workflow.delete(using=db_alias)
    if obsolete_task:
        Task.objects.using(db_alias).filter(pk=obsolete_task.pk).delete()
    Group.objects.using(db_alias).filter(pk__in=obsolete_group_ids).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("news", "0008_alter_newspage_options"),
    ]

    operations = [
        migrations.RunPython(reconcile_mvp_access, migrations.RunPython.noop),
    ]
