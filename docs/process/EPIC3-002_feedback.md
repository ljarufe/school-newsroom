# EPIC3-002 Feedback

**Status:** Closing Feedback Final

## Implementation Summary

EPIC3-002 adds internal minor contributor tracking, editor-controlled public
credits, and conservative publication safeguards for identifiable minors.

The implementation keeps internal contributor records separate from public
credits. Public templates render only `NewsPagePublicCredit.display_name`; they
do not render `MinorContributor.full_name`, age bands, internal contribution
relations, or privacy flags.

The final implementation also closes two adjacent Spanish Admin translation
gaps found during maintainer browser UAT and adds regression coverage for
duplicate internal contributors at the real generated Wagtail/modelcluster
page-form boundary.

No student, guardian, teacher, monitor, consent-document, public author profile,
custom permission, custom workflow, write API, encryption, deploy, CI, or
geography-normalization feature was added.

## Initial Repository State

- Branch: `EPIC3-002-minor-contributors-public-credits-privacy`.
- Initial `git status --short`: clean.
- Top-level `AGENTS.md` was read before editing.
- Ticket source was read from
  `~/Downloads/EPIC3-002_registro_interno_colaboradores_autoria_publica_privacidad_menores.md`.
- Current `docs/process/EPIC3-001_feedback.md` and
  `docs/editorial/guia_de_uso.md` were read before implementation.
- `apps.news` migration graph started at:
  `0001_initial` and `0002_bootstrap_editorial_data`.
- `apps.news` models initially included `NewsSection`, `School`, `NewsPage`,
  and `NewsPageTag`.
- The Home query initially selected related section, school, and featured image,
  but did not prefetch public credits because they did not exist yet.

## Models And Fields Added

- `ContributorGroup`
  - `name`
  - `school`
- `MinorContributor`
  - `full_name`
  - `group`
  - `age_band`
- `NewsPageContributor`
  - `page`
  - `contributor`
  - inherited `sort_order` from `Orderable`
- `NewsPagePublicCredit`
  - `page`
  - `display_name`
  - inherited `sort_order` from `Orderable`
- `NewsPage`
  - `contains_identifiable_minors`
  - `minor_publication_authorizations_verified`
  - `sensitive_content`

`MinorContributor` does not duplicate `School`. Its school is derived through
`MinorContributor.group.school`, preserving one source of truth for the group
and avoiding a later mismatch between a contributor's group and school.

The final `age_band` values are:

- `under_14`: `Menor de 14 años`
- `14_to_17`: `De 14 a 17 años`

No date of birth, exact age, DNI, email, phone, address, guardian data,
signature, PDF, image authorization, or contact field was added.

## Relationship Policies

- `ContributorGroup.school` uses `on_delete=PROTECT` so a school used by an
  internal contributor group cannot be silently removed.
- `MinorContributor.group` uses `on_delete=PROTECT` so contributor records
  cannot be orphaned by deleting their group.
- `NewsPageContributor.page` and `NewsPagePublicCredit.page` use
  `ParentalKey(..., on_delete=CASCADE)` as Wagtail/modelcluster child objects of
  `NewsPage`.
- `NewsPageContributor.contributor` uses `on_delete=PROTECT` so a contributor
  referenced by a page cannot be silently removed.

Duplicate contributors on the same page are protected in two layers:

- the generated Wagtail/modelcluster `internal_contributors` inline formset
  rejects duplicate `page` + `contributor` rows during Admin form validation;
- `unique_together = [("page", "contributor")]` on `NewsPageContributor`
  remains the persistence-level database backstop.

The generated-page-form regression test submits the same fictional
`MinorContributor` in two real `internal_contributors` inline rows and verifies
that the page form and child formset are invalid, that the formset exposes the
duplicate uniqueness error, and that the duplicate row receives a non-field
error. No custom duplicate-validation layer was added because the installed
modelcluster behavior already enforces the invariant at the Admin form boundary.

## Wagtail Admin Integration

- `ContributorGroup` and `MinorContributor` are registered in the existing
  `Editorial` snippet group.
- The final Admin destinations are:
  - `Secciones editoriales`
  - `Colegios`
  - `Grupos de colaboradores`
  - `Colaboradores menores`
- `NewsPage.content_panels` now includes:
  - `InlinePanel("public_credits", label="Firma pública")`
  - `InlinePanel("internal_contributors", label="Colaboradores internos")`
  - `MultiFieldPanel(..., heading="Privacidad de menores")`
- All new model labels, help text, panel labels, and product validation errors in
  the changed surface are Spanish.
- `WagtailAdminPageForm` is imported through Wagtail's documented public
  `wagtail.admin.forms` module.

## Deferred Validation And Inline Formset Behavior

The custom page form is `NewsPageAdminForm` in `apps/news/forms.py`.
`NewsPage.base_form_class` points to this form.

Source inspection in the running Docker environment confirmed:

- Wagtail version is `7.4.2`.
- `WagtailAdminPageForm` extends Wagtail's cluster model form stack.
- Generated page forms expose child inline formsets through `self.formsets`.
- The generated `NewsPage` formsets are keyed by `comments`,
  `internal_contributors`, and `public_credits`.
- `defer_required_fields()` sets `is_deferred_validation = True`.

Because Wagtail/modelcluster runs the parent form `clean()` before child formsets
in the default `ClusterForm.is_valid()` flow, `NewsPageAdminForm.clean()`
explicitly calls `self.formsets["public_credits"].is_valid()` before inspecting
submitted public credit forms.

Review of the installed Django/modelcluster behavior did not demonstrate
dangerous recursion or re-entry from this explicit child-formset validation.
The child formset must have `cleaned_data` available before the parent form can
evaluate new unsaved inline public credits.

Full validation counts an effective public credit when a submitted
`public_credits` form:

- is present in the real generated inline formset;
- is not marked for deletion according to the formset delete flag;
- has a non-blank `display_name` after stripping whitespace.

This means:

- a new unsaved inline public credit submitted in the same form counts;
- a public credit marked for deletion does not count;
- an empty inline row does not count.

Draft validation returns early when `is_deferred_validation` is true. Drafts can
therefore be saved without public credits or authorization confirmation.

## Publication Rules Implemented

Full validation blocks when:

- there is no effective public credit;
- `contains_identifiable_minors` is true and
  `minor_publication_authorizations_verified` is false.

Full validation does not block when:

- `contains_identifiable_minors` is false and the authorization checkbox is
  false;
- `sensitive_content` is true but the other rules are satisfied;
- internal minor contributors exist but `contains_identifiable_minors` is false.

The final Spanish product validation messages are:

- `Añade al menos una firma pública antes de publicar la noticia.`
- `Confirma que se verificaron las autorizaciones requeridas para los menores identificables antes de publicar la noticia.`

## Normative Notice

The Admin privacy panel includes a Spanish informational notice that references
articles 22 to 25 of the Reglamento de la Ley N.º 29733, distinguishes minors
under 14 from adolescents aged 14 to 17, and states the conservative project
policy that public exposure of any identifiable minor requires editorial
verification of required authorizations.

The notice says it does not replace professional legal review.

The linked official URL is:

```text
https://diariooficial.elperuano.pe/Normas/obtenerDocumento?idNorma=23
```

The link is rendered with `target="_blank"` and
`rel="noopener noreferrer"`. The application does not make backend/runtime
requests to that URL.

Primary-source review of the official regulation during diff review confirmed
that the implemented notice uses differentiated age criteria without falsely
claiming that parental or guardian authorization is universally required for
every data-processing case involving every person under 18. The stricter
publication confirmation remains explicitly a conservative School Newsroom
product policy.

## Public Rendering

Home now prefetches ordered public credits:

```python
Prefetch(
    "public_credits",
    queryset=NewsPagePublicCredit.objects.order_by("sort_order"),
)
```

Home and news detail render all public credit display names in editorial order,
separated with semicolons.

Neither Home nor detail loads or renders internal contributors. Tests assert the
absence of internal contributor names, `under_14`, `14_to_17`,
`contains_identifiable_minors`,
`minor_publication_authorizations_verified`, and `sensitive_content` in public
responses.

Existing or historical `NewsPage` rows without public credits continue to render
without error and without fabricated author text.

## Migrations

EPIC3-002 adds:

```text
apps/news/migrations/0003_newspage_contains_identifiable_minors_and_more.py
```

No changes were made to:

```text
apps/news/migrations/0001_initial.py
apps/news/migrations/0002_bootstrap_editorial_data.py
```

The new migration adds the three `NewsPage` boolean fields with `False`
defaults and creates `ContributorGroup`, `MinorContributor`,
`NewsPagePublicCredit`, and `NewsPageContributor`.

No data migration creates contributors, public credits, authorization
verifications, or sensitive-content flags.

The migration test creates a historical fictional `NewsPage` from the
`news.0002` schema, applies `news.0003`, and verifies:

- the page survives;
- all three new flags are false;
- zero public credits are fabricated;
- zero internal contributor rows are fabricated.

Before maintainer browser UAT, the local persistent development database still
had `news.0003` unapplied. `showmigrations news` demonstrated:

```text
[X] 0001_initial
[X] 0002_bootstrap_editorial_data
[ ] 0003_newspage_contains_identifiable_minors_and_more
```

This explained the observed PostgreSQL `ProgrammingError` for the missing
`news_newspage.contains_identifiable_minors` column. The migration file and
test database behavior were correct; the local persistent schema was still at
`news.0002`.

The maintainer applied the existing migration manually with `make migrate`.
The local Admin then loaded against the expected schema and UAT continued.
No migration file, Docker entrypoint, Dev Container startup, or automatic
migration behavior was changed. The maintainer explicitly chose to keep local
migration application manual.

## Review Findings And Corrections

The real diff review found no blocker and no product-scope deviation.

Two focused corrections were applied before UAT:

1. `WagtailAdminPageForm` was changed from the internal
   `wagtail.admin.forms.pages` import path to the documented public
   `wagtail.admin.forms` module.
2. A generated-page-form regression test was added for duplicate internal
   contributors. The test demonstrated that modelcluster's existing child
   formset uniqueness validation rejects the duplicate before persistence, so a
   new custom duplicate-validation design was not required.

The feedback ticket-source path was also normalized from a machine-specific
absolute home path to `~/Downloads/...`.

During review, two initially suspected implementation concerns were investigated
and not promoted as findings:

- use of the formset `_should_delete_form()` helper was retained after checking
  Django's own formset behavior and documented custom-validation examples;
- explicit `public_credits` formset validation inside the parent page-form
  `clean()` was retained because the parent clean runs before the normal child
  formset validation stage and needs child `cleaned_data` for new inline rows.

No product decision from the maintainer was required for these points because
framework evidence resolved the implementation path.

## Automated Validation

Implementation validation:

- Focused test command:
  `docker compose run --rm web sh -c "DJANGO_SETTINGS_MODULE=config.settings.test pytest apps/news/tests/test_forms.py apps/news/tests/test_models.py apps/news/tests/test_public_rendering.py apps/news/tests/test_admin_uat.py apps/news/tests/test_migrations.py -q"`
  - Result: `52 passed`.
- Full news test command:
  `docker compose run --rm web sh -c "DJANGO_SETTINGS_MODULE=config.settings.test pytest apps/news/tests -q"`
  - Result: `58 passed`.
- `make lint`
  - First run failed on import ordering, two long lines, and one Django model
    method-order style issue.
  - Root cause: new imports and long Spanish help text/test setup lines had not
    been formatted after implementation.
  - Durable fix: split long strings/lines, moved `MinorContributor.__str__`
    before the custom property, and used Ruff's safe import fixer for two import
    blocks.
  - Final result: passed, `All checks passed!`.
- `make migration-check`
  - First direct run failed with Docker API permission denied from the Codex
    sandbox.
  - Root cause: the sandboxed command could not access the Docker socket.
  - Retry disposition: the same Makefile target was rerun with approved
    escalation.
  - Final result: passed, `No changes detected`.
- Initial implementation `make check`
  - Result: passed.
  - Ruff: `All checks passed!`.
  - Migration drift: `No changes detected`.
  - Pytest: `67 passed`.

Review-correction validation:

- Focused command:
  `docker compose run --rm web sh -c "DJANGO_SETTINGS_MODULE=config.settings.test pytest apps/news/tests/test_forms.py apps/news/tests/test_models.py -q"`
  - Result: `27 passed`.
- Review-correction `make check`
  - Result: passed.
  - Ruff: `All checks passed!`.
  - Migration drift: `No changes detected`.
  - Pytest: `68 passed`.
- `git diff --check`
  - Result: passed.

Translation delta validation:

- Project gettext overrides were added for:
  - `The page could not be saved due to validation errors.`
  - `Go to the first error`
- `make compilemessages`
  - Result: passed.
- Focused language tests
  - Result: passed.
- Final local `make check` after the translation/test delta
  - Result: passed.
- Final `git diff --check`
  - Result: passed.
- Pre-commit formatting changed maintainer-added translation/test code during
  the real commit flow. The maintainer inspected the formatter delta, staged the
  resulting changes deliberately, and completed the commit.

Pull Request validation:

- Pull Request: `#6 — EPIC3-002: add minor contributor privacy safeguards`.
- Head commit inspected for CI evidence:
  `e0488d74043dd98c82d0ccd5233ef607a33afa53`.
- GitHub Actions workflow `Pull Request Validation`, run `#7`, completed with
  `conclusion: success`.
- Job `Validate repository` completed successfully.
- No additional local suite was rerun solely because CI was green.

## Maintainer Browser UAT

Luis completed the EPIC3-002 browser UAT in Wagtail Admin using only fictional,
non-sensitive data.

The UAT demonstrated:

- the `Editorial` navigation exposes contributor groups and minor contributors;
- a fictional contributor group can be associated with a school;
- fictional minor contributors can use both supported age bands;
- an incomplete `NewsPage` without a public credit can be saved as a draft;
- internal contributor names are not automatically copied into public credits;
- full publication without an effective public credit is blocked;
- the editor-controlled public credit remains independent from internal names;
- the minor privacy notice is visible and distinguishes the under-14 and
  14-to-17 age bands without presenting the project policy as universal legal
  advice;
- the official regulation link points to the expected source and opens
  externally;
- an identifiable-minor declaration without authorization verification blocks
  publication;
- publication succeeds after a valid public credit and the required
  authorization verification are present;
- Home and the public news detail render the chosen public credit;
- fictional internal minor names, age-band values, and internal privacy flags
  are absent from the public output and inspected HTML;
- `sensitive_content` does not introduce an additional hard publication block.

The first UAT pass found two adjacent generic Wagtail validation strings in
English:

- `The page could not be saved due to validation errors.`
- `Go to the first error`

Project gettext overrides were added and a focused delta-UAT confirmed that the
generic validation message and the first-error action now render in Spanish.

The full UAT was not repeated after the translation-only correction because the
delta did not change publication rules, persistence, public rendering, or
privacy behavior.

No real minor data was used.

## Spanish Surface Findings

Focused browser UAT covered:

- `Editorial`;
- `Grupos de colaboradores`;
- `Colaboradores menores`;
- `Firma pública`;
- `Colaboradores internos`;
- `Privacidad de menores`;
- the legal notice and external regulation link;
- publication validation messages.

The initial browser UAT found these dependency strings in English:

- `The page could not be saved due to validation errors.`
- `Go to the first error`

Both strings are gettext-enabled Wagtail Admin messages used by the changed
validation flow. Project-level Spanish overrides were added to
`locale/es/LC_MESSAGES/django.po`, the compiled catalog was regenerated, and
focused delta-UAT confirmed the corrected Spanish output:

- `No se pudo guardar la página debido a errores de validación.`
- `Ir al primer error`

This remains a focused review of the EPIC3-002 editor-visible surfaces and is
not a claim that every installed Wagtail Admin surface has been fully audited
for Spanish translation coverage.

## Privacy And Access Notes

- No logging was added for `MinorContributor.full_name`.
- No public API was added.
- No public template renders internal contributor records or privacy flags.
- Internal minor names remain visible in the current Wagtail Admin snippet and
  page-edit surfaces for authorized adult editors.
- This ticket protects Wagtail Admin page-form publication validation. A future
  write API, student submission flow, external publisher, or Python publishing
  boundary must apply equivalent safeguards at its own boundary.

## Failures, Retries, And Root Causes

- Initial lint failures were caused by implementation formatting/import-order
  issues and were corrected before the general gate.
- The direct `make migration-check` sandbox failure was caused by Codex sandbox
  Docker-socket permissions, not by migration drift.
- The first browser attempt reached a PostgreSQL missing-column error because
  the local persistent development database had not yet applied `news.0003`.
  `showmigrations news` identified the exact pending migration; `make migrate`
  resolved the environment state. No code or migration design change was
  required.
- The first narrow review-fix artifact had an empty diff body because
  `apps/news/forms.py` and `apps/news/tests/test_forms.py` were still untracked
  and `git diff -- <path>` does not include new untracked files. The relevant
  current file contents were then reviewed directly. This was an artifact
  construction error, not an implementation defect.
- The follow-up review initially requested the already-reviewed feedback file
  again together with the code delta. The maintainer correctly removed it
  because the complete updated feedback had already been delivered and reviewed
  with no later uncertainty about its contents. The second review was limited
  to the new code evidence.
- Pre-commit formatting modified maintainer-added code during the real commit
  flow. The formatter delta was inspected and deliberately included rather than
  blindly retrying the commit.

## Known Issues And Deferred Validation

- Treebeard manager warnings still appear during Django checks/migration
  commands. They were already known, remain non-blocking for the validated
  flows, and were outside EPIC3-002 scope.
- Internal minor-name visibility still depends on current adult Wagtail Admin
  access and general permissions. Custom role/row-level visibility hardening is
  not implemented by this ticket.
- No deployment validation was required or performed.
- No real-minor operational validation was performed; technical UAT used only
  fictional, non-sensitive data.

No required EPIC3-002 browser UAT remains pending.

## Pull Request And Review Evidence

Pull Request `#6` was opened against `main` with the approved EPIC3-002 branch.

GitHub-hosted validation completed successfully through the repository's real
Pull Request workflow.

The Codex review bot left a `+1` reaction on the Pull Request. At the time of
closing-feedback preparation, no Codex review comments, inline review threads,
or submitted reviews with findings were present.

No code, migration, privacy, authorization, or public-rendering delta was made
after the successful CI result and no-finding Codex review signal.

Accordingly, no further local `make check`, full UAT repetition, or full diff
re-review was performed by ceremony.

## New Work Discovered

### Contributor chooser scalability

The current contributor and group selection experience can become noisy when
many records exist.

Future editorial Admin work should evaluate native Wagtail searchable chooser
behavior for contributor groups by name and minor contributors by internal full
name before introducing custom JavaScript.

### Contributor lifecycle and archiving

Workshops and contributor groups can end while historical news relationships
must remain intact.

Future domain work should evaluate active/archive state for contributor groups
and individual contributors so inactive records remain historically preserved
but are excluded from new editorial selections.

A group-level archive alone may be insufficient because an individual
contributor can stop participating while the group remains active.

### School-scoped contributor selection

When a `NewsPage` has a school selected, the editor should not have to search
through contributors from unrelated schools.

Future chooser work should evaluate filtering selectable internal contributors
to active contributors whose group belongs to the selected school.

The behavior when `NewsPage.school` is empty still requires an explicit product
decision. A future ticket should decide whether no contributors are selectable
until a school is chosen or whether another explicit fallback is required.

### Contributor creation from the news editing flow

The current inline relationship can select an existing `MinorContributor`, but
maintainer UAT demonstrated that a missing contributor cannot currently be
created from the news-editing task.

Future Admin UX work should evaluate Wagtail's native chooser creation
capabilities so an authorized editor can search for an existing contributor or
create a new one without leaving the editorial task, while preserving the same
privacy fields and school/group constraints.

### Long-form body authoring and internal images

Maintainer UAT found the current `heading` / `paragraph` body editing experience
too fragmented for long news articles.

Future editorial content work should evaluate a richer configured text block
that supports comfortable multi-paragraph authoring and a limited editorial
toolbar such as bold, italic, links, numbered lists, bullet lists, and
quotations.

The existing `StreamField` architecture should be evaluated before replacing it
with a monolithic field.

The same work should consider zero-to-many images inside the article body as a
concept separate from the optional featured image, including metadata and public
rendering rules required for each image use.

### Previously identified future work preserved

The following EPIC3-002 definition findings remain future work and were not
implemented:

- student accounts / student draft submission;
- teacher or monitor accounts;
- permissions and row-level visibility for minor contributor data;
- adult editor public attribution linked to `User`/profile;
- responsibility per contributor, such as photography, research, or writing;
- formal class vs workshop group vs cohort modeling;
- cohort/enrollment year;
- policy for abbreviated minor public signatures and pseudonyms;
- field-level or application-level encryption/protection of minor names;
- individual authorization/document tracking if legal or operational review
  requires it;
- future write API boundaries applying equivalent publication safeguards.

The preserved EPIC3-001 geography finding was not reopened. This ticket adds a
foreign key from `ContributorGroup` to `School`, but does not change `School`
geography semantics or coverage semantics.

Final backlog disposition and sequencing belong to the ticket-definition chat
and consolidated roadmap, not to this execution feedback.

## Durable Knowledge Candidates For Consolidation

The chat responsible for live project sources should evaluate the following
durable knowledge candidates against the current consolidated sources and
roadmap.

### Editorial / privacy domain

- `internal contributor != public credit` is now implemented and UAT-demonstrated.
- Internal minor contributors are registered with `full_name`, group, and the
  two current age bands only.
- Publication safeguards at the current Wagtail Admin boundary are demonstrated
  end to end.
- Public rendering exposes only ordered editor-controlled public credits.
- The Admin validation flow now has focused project gettext overrides for its
  generic Wagtail validation message and first-error action.
- Current internal minor-name access remains broader than future role/row-level
  privacy hardening may require.

### Technical architecture

- `news.0003_newspage_contains_identifiable_minors_and_more` is the published
  EPIC3-002 migration candidate and preserves historical `NewsPage` rows.
- `NewsPageAdminForm` uses the documented public
  `wagtail.admin.forms.WagtailAdminPageForm` import path.
- The installed Wagtail/modelcluster generated child formset validates the
  `page + contributor` uniqueness invariant before persistence; the database
  uniqueness rule remains the persistence backstop.
- Parent page-form validation that depends on newly submitted inline rows must
  account for the parent-clean/child-formset lifecycle and inspect the real
  generated formset rather than only persisted relations.
- Home prefetches ordered `public_credits`; public paths do not need internal
  contributors for attribution.

### Roadmap candidates

- searchable contributor/group choosers;
- contributor group and individual active/archive lifecycle;
- school-scoped active contributor selection;
- create contributor from the news-editing chooser flow;
- richer long-form authoring within the existing structured-content direction;
- zero-to-many article-body images kept conceptually separate from featured
  image;
- previously preserved privacy, permissions, signature-policy, authorization
  tracking, and future-write-boundary findings.

### Execution-process learning candidates

- During diff review, the follow-up chat should act as a critical decision
  checkpoint only when the real delta reveals a material choice with multiple
  reasonable paths affecting product behavior, privacy, authorization,
  persistence/data integrity, migration strategy, architecture, public
  exposure, workflow, or UAT. The chat should investigate framework/repository
  evidence first and ask Luis only when evidence does not close the material
  choice.
- A later delta review should request only evidence invalidated by that delta.
  A complete updated file already delivered and reviewed should not be requested
  again under another artifact form unless it changed afterwards or new
  uncertainty exists.
- Commands that export review artifacts must handle untracked files explicitly;
  a path-limited `git diff` is insufficient for new files.
- For Stage B closure, after Codex supplies the Implementation Closing Draft and
  Luis uploads it to the follow-up chat, the follow-up chat should accumulate
  review/UAT/Git/CI/review evidence and generate one complete downloadable
  `docs/process/<TICKET-ID>_feedback.md` replacement. Luis should not be asked to
  edit the feedback section by section.
- When a maintainer performs a detailed sequential UAT and later reports that
  everything passed except explicitly named deviations, the follow-up chat can
  treat unreported checklist cases as passed rather than requiring a redundant
  PASS/FAIL matrix.
- Luis currently starts the Docker/Dev Container environment through VS Code.
  UAT guidance for his local workflow should not routinely include `make up`.
  Migration commands should still be stated explicitly when a ticket introduces
  a new migration and the local persistent schema must be prepared.
- The maintainer explicitly chose not to make Codex apply migrations to the
  persistent local development database and not to add automatic migration
  execution to Docker or Dev Container startup.

Some of these candidates may already be represented in the newly consolidated
execution guide or technical/editorial sources. The main consolidation chat
should update only the sources whose current-state projection materially
changes and should avoid duplicating already-consolidated rules.

## Operational Closure State

At the time this Closing Feedback Final was prepared:

- implementation was committed and pushed to the ticket branch;
- Pull Request `#6` was open and mergeable against `main`;
- GitHub Actions Pull Request validation was green;
- the Codex bot left a `+1` review signal and no findings were present;
- maintainer browser UAT and focused translation delta-UAT were complete;
- no required EPIC3-002 validation remained pending;
- no code delta existed after CI/review.

The remaining repository lifecycle action is to commit this factual Stage B
feedback replacement, push the documentation-only delta, confirm the automatic
Pull Request validation remains green, and then Squash and merge Pull Request
`#6`.

After merge, the maintainer should sync `main`, confirm the ticket changes are
present, clean the local ticket branch safely, prune remote refs, confirm a
clean worktree, move the Planka Card from `Review` to `Done`, and hand this
Closing Feedback Final to the main ticket-definition/consolidation chat.
