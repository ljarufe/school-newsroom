# EPIC4-001 Feedback

## Status

Implementation Closing Draft — the code correction and focused automated
validation are complete. The final general repository gate and maintainer
browser UAT are recorded separately below.

## Scope delivered

EPIC4-001 provides a reproducible adult CMS access model and a native Wagtail
editorial workflow. It does not create human users, store passwords, add a
custom authentication system, or replace Wagtail's workflow engine.

Operational objects after migration and bootstrap:

```text
Group: Director/editor
Group: Curador SEO
Task 1: Revisión SEO
Task 2: Revisión editorial final
Workflow: Revisión editorial
WorkflowPage assignment: Inicio
```

The transactional, idempotent command remains:

```text
python manage.py bootstrap_mvp_access
```

It reconciles the exact group permissions, group approval tasks, task order,
workflow assignment, and optional membership of existing users supplied through
`--director`, `--seo-curator`, or `--combined-user`. It never accepts a password
or creates a user.

## Correction pass

The post-UAT correction addressed only the observed EPIC4-001 gaps.

### Historical access cleanup and workflow identity

Data migration `0009_reconcile_mvp_access` removes the exact obsolete groups
`Moderadores` and `Editores` and the exact obsolete task, workflow, and root
assignment named `Aprobación de moderadores`.

The migration preflights the complete deletion before changing data. It stops
with an actionable `ImproperlyConfigured` error when:

- an obsolete group still has assigned users;
- an obsolete group is used by another approval task;
- the obsolete task is not a `GroupApprovalTask`, has task-state history, uses
  an unrelated group, or belongs to another workflow;
- the obsolete workflow has state history, an unrelated task, or an assignment
  outside the historical tree root;
- either exact historical name is ambiguous;
- both the legacy and corrected MVP workflow names exist.

Unrelated groups, tasks, workflows, and assignments are preserved. Automated
migration tests cover safe cleanup, preservation of an unrelated group,
assigned-user failure, and unexpected task dependency failure.

The owned workflow is renamed from `Revisión editorial MVP` to `Revisión
editorial` in place. Both the migration and bootstrap preserve the existing
workflow primary key instead of creating a duplicate. The bootstrap also fails
transactionally on an unresolved old/new name conflict.

The local development database was migrated and bootstrapped successfully. Its
observed final state was exactly two groups, two tasks, one active workflow with
the pre-existing workflow ID, one `Inicio` assignment, and the expected task
order.

### Read-only SEO review context

The SEO tab now starts with a server-rendered panel that has no form options or
editable controls.

For `NewsPage`, `Contexto de la noticia — solo lectura` renders:

- title, section, publication date, and summary;
- the body through Wagtail's normal block rendering;
- the featured image and contextual public caption, alt text, and credit;
- public credits;
- `Previsualizar borrador completo`, linked to Wagtail's draft preview.

It deliberately excludes internal contributors, internal group/school
relationships, age bands, privacy declarations, and authorization flags. The
panel uses the revision-bound page instance that Wagtail is moderating.

`HomePage` and `InstitutionalPage` receive `Contexto de la página — solo
lectura`, with the page title and the same explicit draft-preview action.

Rendering tests cover all three page types. Crafted POST tests prove that a SEO
curator can save authorized SEO fields but cannot replace news content,
institutional content, navigation, privacy state, public credits, or internal
contributor relations.

### Workflow action redirect

A narrow `after_edit_page` hook applies only when Wagtail has successfully
processed `action-workflow-action`. It reloads the page after the task action
and redirects to `wagtailadmin_home` only when the acting user no longer has
edit access.

This fixes both SEO outcomes that end task-derived access:

- `Solicitar cambios` moves the workflow to `needs_changes`;
- SEO approval moves it to `Revisión editorial final`.

Wagtail's success message is added before the hook and remains visible on the
dashboard. Request-level tests assert the persisted state, next task, exact
dashboard redirect, rendered success message, and absence of a permission
error. Users who retain edit access, including Director/editor at final review,
continue through Wagtail's normal redirect path.

### Exact Spanish UI text

The project locale overrides the two workflow dashboard headings as:

```text
Your pages and snippets in a workflow
-> Tus páginas y elementos editoriales en flujo de trabajo

Awaiting your review
-> Pendientes de tu revisión
```

The related screen-reader table label `Privacy and access` is also translated
as `Privacidad y acceso`. The compiled project catalog is tracked and remains
owned by the host user.

Source and rendered-response inspection established that Wagtail 7.4.2 builds
the submit action as `Enviar a %(workflow_name)s`; the documented and tested
label is therefore `Enviar a Revisión editorial`.

Rendered tests also lock the final-review labels observed in this installation:

- `Publicar`;
- `Cancelar flujo de trabajo`;
- `Solicitar cambios`;
- `Aprobar y Publicar`;
- `Aprobar con comentario y Publicar`;
- `Guardar borrador`.

`Publicar` is the Director/editor direct override. `Aprobar y Publicar` is the
normal final workflow action.

## Permission boundaries retained

Director/editor has Wagtail Admin access, the full and SEO editorial-surface
permissions, page add/change/publish on the `Inicio` subtree, reviewed editorial
snippet permissions, image add/change/choose, and document add/change/choose.
The role does not receive user/group administration or superuser status.

Curador SEO has Wagtail Admin access, the SEO surface permission, chooser-only
access to existing images, and no persistent page permission. Native current
task membership grants temporary editor access. The generated form contains
only the approved SEO field whitelist; protected page fields and child formsets
are removed before POST binding.

A non-superuser assigned to both groups accumulates both permission sets and can
complete both tasks. It is supported for a single-person operation but is not a
valid account for isolation UAT.

The workflow remains assigned to `Inicio`, so native ancestor lookup covers the
Home, news, and institutional pages below it. Final task approval publishes the
latest revision through Wagtail's native completion action. Director/editor
retains direct publish as an intentional MVP override.

## Privacy safeguards retained

Existing validation still requires an effective public credit, complete
contextual metadata for selected images, and authorization verification when
identifiable minors are declared. Curador SEO receives no internal contributor
formset or snippet permission. Public templates and JSON-LD continue to use
explicit public credits rather than internal contributor data.

No row-level school, district, province, or territory isolation is claimed.

## Documentation and UAT precision

The editor guide now documents the real workflow name, submit action, final
approval actions, read-only context, and draft preview. The operations runbook
contains a copy-ready Spanish UAT with:

- exact user, menu, page, tab, field, task, and action labels;
- fixed fictional accounts, school, contributor group, minor, images, public
  credits, direct-publish news, workflow news, SEO, social, and image metadata;
- preconditions, expected results, verification, and cleanup;
- separate checks for direct override publication, request changes, SEO
  approval, normal final publication, dashboard redirects, generic page
  context, and public minor privacy.

Process learning: future UAT plans for editor-visible changes should be written
from rendered/source-verified navigation and labels, include complete
copy-paste samples, distinguish preconditions from expected results, and define
cleanup before maintainer execution.

## Files added

- `apps/home/forms.py`
- `apps/news/access.py`
- `apps/news/management/__init__.py`
- `apps/news/management/commands/__init__.py`
- `apps/news/management/commands/bootstrap_mvp_access.py`
- `apps/news/migrations/0008_alter_newspage_options.py`
- `apps/news/migrations/0009_reconcile_mvp_access.py`
- `apps/news/templates/news/admin/news_seo_context_panel.html`
- `apps/news/templates/news/admin/page_seo_context_panel.html`
- `apps/news/tests/test_mvp_access.py`
- `docs/operations/wagtail_access_mvp.md`
- `docs/process/EPIC4-001_feedback.md`

## Files updated

- `README.md`
- `apps/home/models.py`
- `apps/news/forms.py`
- `apps/news/models.py`
- `apps/news/panels.py`
- `apps/news/tests/test_migrations.py`
- `apps/news/wagtail_hooks.py`
- `docs/editorial/guia_de_uso.md`
- `locale/es/LC_MESSAGES/django.po`
- `locale/es/LC_MESSAGES/django.mo`

## Automated validation

Focused correction evidence:

```text
EPIC4 cleanup migration tests: 3 passed
EPIC4 MVP access/workflow/admin tests: 20 passed
Combined correction-focused selection: 20 passed, 11 deselected
Rendered workflow action labels: passed
SEO action redirect request tests: 2 passed
```

General repository gate:

```text
make check
Ruff: passed
Migration drift: no changes detected
pytest: 202 passed
```

Final whitespace validation:

```text
git diff --check: passed
```

## Failed attempts and root causes

1. Direct focused pytest was initially invoked without
   `DJANGO_SETTINGS_MODULE=config.settings.test`, so WhiteNoise's production
   manifest storage rejected missing collected static assets. The repository's
   test settings were then used; request tests rendered normally.
2. The first context template referenced `instance`, while Wagtail exposes a
   panel's bound object as `self.instance`. The preview link rendered because it
   was supplied separately, but context values were blank. Both templates now
   use the bound revision instance, and their rendering tests pass.
3. The first full gate reached 201 passing tests and one teardown failure in an
   older migration test. That test deliberately fabricated a base `Task` with a
   `GroupApprovalTask` content type but no child table row; the new safety guard
   correctly refused to delete it while returning to latest migrations. Its
   teardown now removes that deliberately inconsistent fixture before applying
   later migrations. The cleanup migration's own safe and unsafe cases remain
   covered independently.

## Warnings and known limitations

- `make migrate` emits the checkout's existing Treebeard 6 forward-compatibility
  manager warnings. EPIC4-001 does not alter page or collection tree managers.
- Manual browser UAT has not been executed by Codex and is not reported as
  passed.
- Direct Director/editor publication is intentional, so workflow compliance is
  operational rather than absolute for that role.
- The MVP has group/page/collection granularity, not row-level school or
  territory isolation.
- Outgoing email and forced first-login password change are not implemented.

## Deferred manual validation

Maintainer browser UAT remains required. Use `Maintainer UAT (pending,
Spanish)` in `docs/operations/wagtail_access_mvp.md` and record actual results
without converting the documented expected results into evidence.

## New Work Discovered

1. Configure transactional email, sender-domain controls, deployment secrets,
   the external Admin URL, and delivery testing before enabling email recovery.
2. Consider a forced first-login password-change mechanism if the documented
   private temporary-password procedure becomes insufficient.
3. Evaluate explicit school or territory requirements before adding row-level
   access controls; native Wagtail group/page/collection permissions do not
   provide that isolation.
4. If future SEO requirements outgrow permission-gated native panels, consider
   a dedicated review view that preserves the same server-side whitelist and
   workflow authorization boundary.
