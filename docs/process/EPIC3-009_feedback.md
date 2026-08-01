# EPIC3-009 Feedback

Status: **Implementation Closing Draft**

## Checkout and scope

- Active branch: `EPIC3-009-editorial-taxonomy`.
- Initial worktree: clean.
- Confirmed runtime: Django 5.2.16, Wagtail 7.4.2, and django-modelcluster 6.5.
- Confirmed migration baseline: `news.0011_alter_newspage_body`.
- The existing Docker-first Makefile, isolated browser Compose stack, Playwright
  configuration, browser fixture command, and Browser Regression workflow were
  reused. No dependency or alternate runner was added.
- Codex did not apply migrations to the maintainer's persistent database during
  implementation or either correction. After the initial implementation, the
  maintainer applied `news.0012`–`0014` to that database before performing the
  UAT that exposed the Admin and public findings. Disposable browser stacks
  applied migrations only to their isolated databases.

### Maintainer UAT correction baseline

The consolidated correction started on `EPIC3-009-editorial-taxonomy` with the
existing ticket worktree intentionally dirty. All prior ticket and maintainer
changes were preserved. The maintainer findings were:

- one mixed taxonomy management surface did not communicate the two creation
  intents and left the parent workflow unsuitable for the required root-only
  selector;
- an existing classification could change between root and child when model
  validation happened to allow the requested hierarchy; and
- the public detail rendered compact main names in the upper eyebrow and the
  complete readable paths again in a lower metadata row.

All steps from the detailed maintainer UAT pass that were not reported as
findings remain approved under deviation reporting. This correction does not
reinterpret them as rerun or newly approved UAT.

The approved decision is fixed type after creation: a main section remains a
main section, a subsection remains a subsection, and a subsection may move
between main sections. The existing `NewsSection` rows, model, content type,
permissions, and database table remain the single source of taxonomy data.
No maintainer data was changed.

The correction modifies `apps/news/models.py`,
`apps/news/taxonomy_forms.py`, `apps/news/wagtail_hooks.py`,
`apps/news/tests/test_models.py`, `apps/news/tests/test_admin_uat.py`,
`apps/news/tests/test_mvp_access.py`,
`apps/news/tests/test_public_rendering.py`, `templates/news/news_page.html`,
`tests/browser/taxonomy.spec.js`, `docs/editorial/guia_de_uso.md`, and this
feedback file. The intentional three-step migration boundary in
`0012_editorial_taxonomy_schema.py`, `0013_migrate_editorial_taxonomy.py`, and
`0014_remove_singular_section.py` was not modified, replaced, squashed, or
extended; no new migration was added.

### Post-diff-review correction

The consolidated UAT correction remained accepted. Diff review found two
focused Admin integrations that still used the shared model identity:

- Wagtail's canonical `SnippetAdminURLFinder` generated the root snippet edit
  URL for every `NewsSection`, so an audit/reference edit link for a subsection
  resolved to a correctly rejected 404; and
- both index actions still rendered `Añadir Sección editorial`, while the
  visible create headers used the global `Sección editorial` model label.

The causal URL fix keeps one finder registration and replaces its construction
logic with a `ModelAdminURLFinder` that reads the persisted `parent_id`. It
returns `wagtailsnippets_news_newssection:edit` for a root and
`news_subsections:edit` for a child, while the shared `ModelPermissionPolicy`
still returns no URL without change permission. The second `ModelViewSet`
continues not to register a competing finder, and direct wrong-surface URLs
continue returning 404.

Supported index/create view overrides now render `Añadir sección` and visible
`Sección` identity for roots, plus `Añadir subsección` and visible `Subsección`
identity for children. Their breadcrumbs and create success/error messages are
type-correct without changing the model's global `verbose_name` or introducing
custom templates. This review fix changes only `apps/news/wagtail_hooks.py`,
the focused Admin/access tests, `tests/browser/taxonomy.spec.js`, and this
feedback file. Models, taxonomy forms, public templates, and migrations remain
unchanged by it.

## Files changed

- **Domain and migrations:** `apps/news/models.py`, `apps/news/forms.py`,
  `apps/news/taxonomy.py`, `apps/news/widgets.py`, the three `news.0012`–`0014`
  migrations, and the focused model/form/migration tests.
- **Wagtail Admin:** `apps/news/panels.py`, `apps/news/wagtail_hooks.py`,
  `apps/news/taxonomy_forms.py`, the
  taxonomy widget template and scoped assets, the browser fixture/spec, Admin
  and access tests, and the Browser Regression path filters.
- **Public and SEO:** the public selector, filter view, navigation helper,
  Home/card/detail templates, SEO metadata builder and context panel, plus their
  rendering, query-growth, language, and JSON-LD tests.
- **Documentation and review:** `docs/editorial/guia_de_uso.md`, this feedback,
  and the temporary diff-review artifacts under `tmp/`.

## Implementation

### Hierarchy and revision-aware ownership

`NewsSection.parent` is an optional protected self-reference. A null parent is a
main section; a non-null parent is a subsection. Model validation rejects
self-parenting and a subsection below another subsection. Every existing root
must remain a root, every existing subsection must remain a subsection, and a
subsection may move between roots. Slugs remain globally unique and stable
name/PK tie-breakers supplement sibling `sort_order`.

`NewsPageSection` owns explicit classifications through a `ParentalKey` to
`NewsPage`, a protected foreign key to `NewsSection`, and the database constraint
`unique_news_page_section`. There is no manual selection order and no derived
parent row is stored. The former singular field is removed after data migration,
so there is one classification source of truth.

Only the classification identities in `section_assignments` are revisioned.
Section names and ordering remain editable current-state taxonomy data. A
subsection may move between root parents, while an existing row cannot switch
between root and child. Reopening an old revision therefore resolves its stored
IDs against the current labels and permitted hierarchy.

### Observed Wagtail revision serialization

An ephemeral test-database probe saved an existing `public_credits`
`ParentalKey` relation with Wagtail 7.4.2. Each child was serialized inside a
list with its concrete child primary key, order, owner primary key, and child
field. The observed item shape was exactly:

```python
{
    "pk": 1,
    "sort_order": 3,
    "page": 3,
    "display_name": "First revision probe credit",
}
```

The probe was removed. The migration consequently writes the non-orderable
taxonomy child in the corresponding modelcluster shape:

```python
{
    "pk": None,
    "page": page_id,
    "section": section_id,
}
```

Migration tests reconstruct the migrated revision with `Revision.as_object()`,
verify the prior body and classification, save a new revision, and reconstruct
that round trip. The assertions compare the exact explicit section IDs from the
real reconstructed objects; this is the automated revision evidence, not a
helper-only test. No duplicate preview, revert, or workflow fixture is needed.

Preview through the UI, revert through the UI, and the complete moderation
workflow remain pending maintainer UAT. They are Wagtail runtime boundaries and
are not claimed as causally automated by the historical reconstruction test.

### Migration and safe reverse

The published graph was not rewritten:

1. `0012_editorial_taxonomy_schema` adds the hierarchy and child assignment
   schema while retaining a nullable singular field.
2. `0013_migrate_editorial_taxonomy` copies current singular values, converts
   legacy `Revision.content`, and creates the 18 approved provisional
   subsections beneath the six stable main-section slugs.
3. `0014_remove_singular_section` removes the old field only after conversion.

The data migration uses historical models and the schema editor's database
alias. Missing stable roots, missing legacy section identities, and conflicting
provisional slug/name/parent identities fail with explicit evidence. Re-running
the forward function does not duplicate provisional rows.

The reverse function preflights representational ambiguity before writing.
Current pages and revisions must contain zero or one explicit assignment;
multiple assignments fail closed rather than being collapsed. Zero assignments
restore the nullable singular value as null. A provisional row still found by
its migration-owned slug must retain the expected name, parent, and order and
must be unused by current pages and historical revisions before it is removed.

This reverse path is deliberately comprehensive but is not a published
production rollback commitment. Its accepted limitation is important: if a
migration-owned provisional row has been renamed by changing its slug, the
reverse lookup no longer identifies it as migration-owned, so that row is
preserved rather than causing reversal to abort. A missing expected provisional
row is likewise skipped. An expected-slug row with changed name, parent, or
order, or one still referenced, aborts before collapse. No exhaustive matrix of
reverse combinations is claimed or required.

### Legacy-data policy

The forward migration preserves a valid legacy singular section as the same
single explicit assignment. A null or absent usable legacy value remains
unclassified; no arbitrary classification is invented. Existing unclassified
pages render safely, while classification becomes mandatory only when an editor
attempts to publish or republish through full validation.

Recognizable historical revision taxonomy is converted. If a revision points
to an unresolvable legacy section ID, the current implementation fails the
atomic migration with explicit evidence rather than writing a dangling or
partial conversion. For this pre-production project, omission of unconvertible
taxonomy metadata would also be acceptable if implemented atomically, but
perfect preservation of test-news history is not prioritized over successful
rendering and safe all-or-nothing migration behavior. New revisions created
after EPIC3-009 continue to preserve the exact explicit taxonomy identities.

### Single taxonomy boundary

`NewsTaxonomy` in `apps/news/taxonomy.py` is the one derivation boundary for:

- stable ordered explicit selections;
- de-duplicated effective main sections;
- public/read-only visible paths;
- ordered and de-duplicated `articleSection` values; and
- compact main-section names for existing cards and Home surfaces.

It consumes prefetched child assignments and bulk-loads sections with their
parents when revision-created in-memory objects do not already carry that
cache. Templates and SEO code do not reconstruct the hierarchy.

### Editor and deletion behavior

The News edit form declares one server-rendered multiple-choice field with the
approved label and help text. Its custom tree widget provides independent
checkboxes and disclosure buttons, Spanish accessible names, keyboard-operable
native controls, selected/error branch expansion, and small scoped CSS and
JavaScript. Cleaned explicit values replace the in-memory child relation before
Wagtail serializes draft, preview, revision, or workflow state. Duplicate input
is de-duplicated. Draft validation permits no classification; full validation
uses the approved field error.

Wagtail 7.4.2 rejects registering the same model as two snippets. The supported
Admin architecture therefore uses one canonical `SnippetViewSet` for
`Secciones` and one distinct `ModelViewSet` for `Subsecciones`. Both use the
same `NewsSection` model and `ModelPermissionPolicy`. The canonical viewset
registers one type-aware Admin URL finder and the second viewset registers no
competing finder. Their URL namespaces and prefixes are respectively
`wagtailsnippets_news_newssection` under
`/admin/snippets/news/newssection/` and `news_subsections` under
`/admin/news/subsections/`.

`Secciones` filters roots for its list and every object route and renders only
`Nombre`, `Slug`, and `Orden`. `Subsecciones` filters children for its list and
every object route, shows the root parent, and renders `Nombre`, `Slug`,
`Sección principal`, and `Orden`. Its explicit model form makes the parent
required and uses a normal select whose queryset contains only roots. The
previous shared snippet surface delegated the parent control to Wagtail's
registered-snippet chooser; that chooser represented the mixed model rather
than the required root-only creation intent. The dedicated form/queryset is the
causal correction.

Their index actions and visible create identities are also distinct:
`Añadir sección` / `Sección` and `Añadir subsección` / `Subsección`.
Type-correct breadcrumbs and create messages use the same supported view
overrides.

Model validation compares an existing row's persisted `parent_id` with the
submitted state. It rejects root-to-child and child-to-root conversion in
Spanish while retaining self-parent and third-level checks. A child-to-root
move is rejected even through a manipulated request; moving a child between
two roots remains valid. The root form has no parent field, so a crafted parent
key is ignored there as well.

Object loading is type-filtered for edit, delete, copy, history, and usage.
Wrong-type identifiers return 404. The root snippet's available bulk delete
preflight rejects child identifiers, while the generic subsection surface does
not expose a bulk checkbox/action in Wagtail 7.4.2. Deletion protection is
exact across the supported paths:

- children protect a main section through `NewsSection.parent`;
- current assignments protect a classification through
  `NewsPageSection.section`;
- `NewsSection.delete()` scans NewsPage revision content and raises
  `ProtectedError` for a historical-only reference; and
- Wagtail's individual and bulk snippet deletion paths preflight children,
  current assignments, and historical revisions, then redirect to the list
  with `No puedes eliminar esta clasificación porque contiene subsecciones o
  está asociada a noticias.` instead of returning a 500.

The two entries remain under `Editorial` and preserve the existing role
boundary. Director/editor receives the shared model permissions. Curador SEO
cannot see or access either management surface, receives only readable paths,
and a manipulated taxonomy POST on a News page is ignored.

### Public and SEO behavior

- Public navigation queries main sections only.
- Home, cards, and lists show de-duplicated effective main-section names in the
  existing compact space.
- News detail uses `NewsTaxonomy.visible_paths` in the existing upper eyebrow,
  joins multiple paths with semicolons, suppresses a redundant explicit parent
  when a child path in that branch already communicates it, and has no lower
  `Secciones y subsecciones` metadata row.
- `/noticias/?seccion=<main-slug>` retains its contract, includes explicit
  descendants, calls `distinct()`, and rejects subsection slugs as filter URLs.
- Public selectors prefetch assignments, sections, and parents.
- A constant-growth regression captures the full list request with one page and
  again with six pages, including descendant assignments, and asserts that the
  query counts are identical. The duplicate filter regression also asserts one
  rendered result when two descendant assignments match.
- JSON-LD emits `articleSection` only when classifications exist, always as an
  ordered array of visible names such as `Cultura` and `Cultura > Música`.
  Serialization continues through the existing safe JSON serializer.

The current Schema.org definition gives `articleSection` a `Text` range and
states that an article can belong to one or more sections, which is compatible
with repeated Text values represented by a JSON-LD array:
<https://schema.org/articleSection>. Google's current Article documentation
supports `NewsArticle` JSON-LD and instructs publishers to add applicable
properties: <https://developers.google.com/search/docs/appearance/structured-data/article>.
Google's general structured-data policy recommends JSON-LD, requires metadata
to represent visible content accurately, and does not guarantee a rich result:
<https://developers.google.com/search/docs/appearance/structured-data/sd-policies>.
No ranking or rich-result guarantee is claimed.

## Browser regression evidence

The original isolated Chromium close passed two repository scenarios. The UAT
correction extends the taxonomy file with a second scenario, so the current
final isolated run passes three repository browser scenarios. The original
taxonomy scenario performs these exact gestures and checks:

1. logs in and opens the normal News edit view;
2. verifies that all six branch containers are present, while causally checking
   only Cultura and Política as initially collapsed and Cultura's child list as
   hidden;
3. expands Cultura using its independent disclosure and verifies its root is
   unchecked;
4. selects only Música and verifies Cultura remains unchecked;
5. expands Entrevistas and selects both its root and Comunidad;
6. collapses Entrevistas with Space, expands it with Enter, tabs to the root
   checkbox, and confirms an unrelated minors-privacy checkbox remains
   unchanged;
7. saves the draft and verifies selected branches reopen with exact checkbox
   state;
8. removes Comunidad, saves, and verifies the other explicit selections remain;
9. removes every remaining classification and saves the empty draft;
10. verifies the representative Música, Entrevistas, and Comunidad controls are
    unchecked after the final draft reload; the spec does not claim an
    all-branch collapsed-state assertion at this point;
11. opens Wagtail's action dropdown, invokes the real `action-publish` submit,
    and verifies the approved Spanish error and expanded taxonomy panel; and
12. verifies no browser page errors and no change to the unrelated privacy
    checkbox.

The correction scenario opens the collapsed `Editorial` submenu, verifies the
distinct `Secciones` and `Subsecciones` links and URLs, follows each normal add
action, and now asserts the exact `Añadir sección` / `Añadir subsección` labels
and visible `Sección` / `Subsección` headings. It rejects the former shared
`Añadir Sección editorial` label, verifies the root form has no parent
combobox, and verifies the child form's parent combobox contains representative
roots but excludes `Música` and `Arte y literatura`. It then selects only
`Cultura › Música` on the disposable News page, publishes successfully, opens
the public detail, and verifies the complete path in
`.article-header .eyebrow` and the absence of the lower
`Secciones y subsecciones` label. Both scenarios assert no browser page errors.
This is focused interaction evidence, not a claim of complete Wagtail Admin
accessibility coverage.

## Automated validation

The implementation validation chronology was:

1. Focused domain/Admin/public/SEO regression:

   ```text
   docker compose run --rm web sh -c "until nc -z db 5432; do sleep 1; done; DJANGO_SETTINGS_MODULE=config.settings.test pytest -o cache_dir=/tmp/school-newsroom-pytest-cache apps/news/tests/test_models.py apps/news/tests/test_forms.py apps/news/tests/test_admin_uat.py apps/news/tests/test_mvp_access.py apps/news/tests/test_public_rendering.py apps/news/tests/test_seo_public.py apps/news/tests/test_language.py"
   ```

   Result after causal fixes: 124 passed.

2. Focused migration module:

   ```text
   docker compose run --rm web sh -c "until nc -z db 5432; do sleep 1; done; DJANGO_SETTINGS_MODULE=config.settings.test pytest -o cache_dir=/tmp/school-newsroom-pytest-cache apps/news/tests/test_migrations.py"
   ```

   Result before the final reverse delta: 18 passed.

3. Migration-state check:

   ```text
   docker compose run --rm web python manage.py makemigrations --check --dry-run --skip-checks
   ```

   Result: no changes detected.

4. `make browser-test` exposed the two Playwright precondition defects described
   below. The corrected focused scenario was then run with:

   ```text
   docker compose -f docker-compose.browser.yml run --rm browser-test npx playwright test tests/browser/taxonomy.spec.js --reporter=line
   ```

   Result after the final interaction correction: 1 passed.

5. `make lint` reported the modern `Iterable` import and one overlong line.

6. After the safe-reverse clarification in implementation, the exact focused
   migration command was:

   ```text
   docker compose run --rm web sh -c "until nc -z db 5432; do sleep 1; done; DJANGO_SETTINGS_MODULE=config.settings.test pytest -o cache_dir=/tmp/school-newsroom-pytest-cache apps/news/tests/test_migrations.py -k epic3_009 -q"
   ```

   Result: 4 passed, 15 deselected.

7. Formatting was checked and then applied only to the six reported files:

   ```text
   docker compose run --rm web sh -c "RUFF_CACHE_DIR=/tmp/school-newsroom-ruff-cache ruff format --check apps/news/forms.py apps/news/models.py apps/news/panels.py apps/news/selectors.py apps/news/seo_metadata.py apps/news/taxonomy.py apps/news/views.py apps/news/widgets.py apps/news/wagtail_hooks.py apps/news/tests/test_admin_uat.py apps/news/tests/test_forms.py apps/news/tests/test_language.py apps/news/tests/test_migrations.py apps/news/tests/test_models.py apps/news/tests/test_mvp_access.py apps/news/tests/test_public_rendering.py apps/news/tests/test_seo_public.py"
   docker compose run --rm web ruff format apps/news/forms.py apps/news/selectors.py apps/news/taxonomy.py apps/news/tests/test_forms.py apps/news/tests/test_migrations.py apps/news/tests/test_models.py
   ```

   Result: the check named six files; those six were reformatted.

8. Final browser gate:

   ```text
   make browser-test
   ```

   Result: 2 passed in Chromium.

9. Final general gate:

   ```text
   make check
   ```

   Result: Ruff passed, `makemigrations --check --skip-checks` reported no
   changes, and pytest reported 297 passed in 42.76 seconds.

10. Final implementation whitespace check:

    ```text
    git diff --check
    ```

    Result: passed with no whitespace errors.

This post-review clarification changed documentation only. Per its delta budget,
Python tests, `make check`, and `make browser-test` were not repeated.

The clarification itself was validated with:

```text
git diff --check
git diff --no-index --check tmp/EPIC3-009_pre_clarification/AGENTS.md AGENTS.md
git diff --no-index --check tmp/EPIC3-009_pre_clarification/docs/process/EPIC3-009_feedback.md docs/process/EPIC3-009_feedback.md
```

`git diff --check` passed. Each `--no-index` command returned the expected status
1 because the files differ and emitted no whitespace diagnostic. No executable
validation was run for this documentation-only delta.

### UAT correction automated validation

The correction used the following Docker-first evidence:

1. The focused model/Admin/permission/public/SEO command was:

   ```text
   docker compose run --rm -e DJANGO_SETTINGS_MODULE=config.settings.test web pytest apps/news/tests/test_models.py apps/news/tests/test_admin_uat.py apps/news/tests/test_mvp_access.py apps/news/tests/test_public_rendering.py apps/news/tests/test_seo_public.py
   ```

   It reached 98 passed and one failure. The remaining failure proved that
   Wagtail's copy mixin loads its object independently of
   `SingleObjectMixin.get_queryset()`. After adding explicit typed copy-object
   loading, the exact failing test passed. The later general gate collected and
   passed all 99 real tests in these focused modules.

2. Changed Python files were formatted and linted with scoped `ruff format`
   and `ruff check` commands. Three files were reformatted and the scoped lint
   passed.

3. The isolated focused browser command was:

   ```text
   docker compose -f docker-compose.browser.yml run --rm browser-test npx playwright test tests/browser/taxonomy.spec.js --reporter=line
   ```

   After two evidence-driven locator corrections described below, the result
   was 2 passed in Chromium.

4. The required final browser gate was run once:

   ```text
   make browser-test
   ```

   Result: 3 passed in Chromium. The disposable stack applied the published
   `0012`–`0014` migrations; no migration touched the maintainer database.

5. The first required general gate invocation was:

   ```text
   make check
   ```

   Ruff passed and `makemigrations --check --skip-checks` reported no changes.
   Pytest then reported 381 passed and two failures because it also collected
   the deliberately saved pre-correction `test_*.py` copies below
   `tmp/EPIC3-009_pre_uat_fix/`. Both failures came from those old copies; all
   current checkout tests passed. Per the ticket, the copies are removed only
   after generating the incremental correction artifact. The gate is rerun
   after that required cleanup, which directly invalidates the failed
   collection boundary.

6. After the required pre-copy cleanup, the repeated general gate passed:

   ```text
   make check
   ```

   Result: Ruff passed; `makemigrations --check --skip-checks` reported no
   changes; pytest reported 299 passed in 42.78 seconds.

7. The final whitespace evidence for the UAT correction was:

   ```text
   git diff --check
   ```

   Result: passed with no diagnostics before the UAT-correction handoff.

### Post-diff-review automated validation

The focused Admin URL and create-identity correction used the following
Docker-first evidence:

1. The causal Admin and permission regression command was:

   ```text
   docker compose run --rm -e DJANGO_SETTINGS_MODULE=config.settings.test web pytest apps/news/tests/test_admin_uat.py::test_editorial_snippet_destinations_are_available apps/news/tests/test_admin_uat.py::test_taxonomy_management_forms_keep_types_fixed_and_parent_choices_root_only apps/news/tests/test_admin_uat.py::test_taxonomy_cross_surface_object_urls_return_not_found apps/news/tests/test_mvp_access.py::test_director_and_seo_curator_real_permission_matrix
   ```

   Result: 4 passed in 5.53 seconds. This includes exact root/child
   `AdminURLFinder` destinations for a Director, no destination for a Curador
   SEO, and continued 404 responses for direct cross-surface URLs.

2. The three changed Python files were formatted and linted with scoped
   `ruff format` and `ruff check` commands. Ruff reformatted one file and the
   scoped lint passed.

3. Before changing the Playwright assertions, the rendered DOM and accessible
   headings were inspected in the disposable browser stack. The focused
   browser command was then:

   ```text
   docker compose -f docker-compose.browser.yml run --rm browser-test npx playwright test tests/browser/taxonomy.spec.js --reporter=line
   ```

   Result: 2 passed in Chromium. The scenarios assert `Añadir sección` with
   visible create identity `Sección`, and `Añadir subsección` with visible
   create identity `Subsección`; they also reject the previous shared action
   label.

4. The required final browser gate was run once:

   ```text
   make browser-test
   ```

   Result: 3 passed in Chromium.

5. The required final general gate was run once:

   ```text
   make check
   ```

   Result: Ruff passed; `makemigrations --check --skip-checks` reported no
   changes; pytest reported 299 passed in 42.72 seconds.

6. The final whitespace check was:

   ```text
   git diff --check
   ```

   Result: passed with no diagnostics.

No maintainer UAT was performed for this delta. The persistent maintainer
database had already received migrations `news.0012` through `news.0014` from
the maintainer before the earlier UAT; Codex applied migrations only in
disposable browser stacks. Delta UAT for the corrected canonical edit links and
the type-specific create labels remains pending.

## Failures and root causes encountered

- An early focused form/model run encountered a missing NewsPage content type
  while migrating a freshly constructed test state. The data migration now
  treats an absent content type as an empty revision queryset; normal migrated
  databases still convert every matching revision.
- A hierarchy ordering assertion initially included subsections in the main
  section list. The query was corrected to filter null parents.
- Two pre-ticket Admin assertions still expected the singular Spanish label.
  They were updated to the implemented plural taxonomy UI.
- Transactional migration tests can flush seed rows while leaving migration
  recorder state applied. The test-only `migrate_to_latest` helper now restores
  the six stable roots before asking `MigrationExecutor` to reach the leaves;
  production migration behavior was not weakened.
- The first browser invocation was blocked by sandbox access to the Docker
  socket and was rerun through the approved Docker path. One yielded execution
  lost its result and left no Playwright artifact, so a recovery run was needed
  rather than assuming success.
- The two causal Playwright failures were distinct from that infrastructure
  issue:
  1. a locator assumed directly visible checkboxes after the taxonomy tree had
     intentionally collapsed and hidden those controls; persistence checks now
     use the stable project-owned branch structure without pretending the
     hidden controls are in the accessibility tree; and
  2. Wagtail's real `action-publish` submit was mounted inside its action
     disclosure/dropdown and remained hidden until the menu was opened. The
     final regression opens that precondition, waits for the real submit to be
     visible, and then invokes it.
- Ruff reported one modern import rule and one long line; both were corrected.
- The modelcluster package does not expose `__version__`; runtime confirmation
  used installed package metadata and reported django-modelcluster 6.5.
- The first correction-focused pytest invocation accidentally inherited
  `config.settings.local`; Admin and public responses failed before assertions
  because the local WhiteNoise manifest was absent in the run container. The
  command was corrected to the repository test settings. This was an
  invocation defect, not an application failure.
- Wagtail 7.4.2 uses `SingleObjectMixin.get_queryset()` for edit/delete but its
  copy mixin performs a separate direct object lookup. The first cross-surface
  action test exposed the difference; typed `get_object()` implementations now
  make wrong-type copy URLs return 404 as well.
- The correction browser scenario first expected custom create text as a
  visible heading. DOM inspection showed Wagtail renders `Sección editorial`
  visibly and, on the generic view, the operation title only as a screen-reader
  heading. The test now asserts the concrete destination URL and the actual
  visible fields. A second failure showed Wagtail includes the required `*` in
  field accessible names; role locators now use the observed name prefixes.
- A manual cleanup attempt with `docker compose ... down --volumes` was blocked
  by the approval reviewer as destructive. The isolated Compose file declares
  no persistent database volume and uses `tmpfs`, so the stack was safely
  removed without `--volumes`; the final Makefile target performed its own
  approved cleanup.
- The first correction `make check` collected the saved pre-correction Python
  test copies from `tmp/`. The resulting two failures were old expectations
  running against corrected production code, not failures in current tests.
  Generating the required delta artifact and removing the pre-copy directory is
  the causal fix before the final general-gate rerun.

No failure was bypassed, and all affected validations were green at close.

## Manual validation and maintainer UAT

No manual maintainer UAT result is claimed. UAT remains pending and should use
only fictional, non-sensitive data. In particular, preview through the Wagtail
UI, revert through the Wagtail UI, and preservation through the complete
moderation workflow are accepted non-automated coverage and remain to be
exercised by the maintainer; no result for those paths has been invented.

- Taxonomy routes: open both `Wagtail Admin > Editorial > Secciones` and
  `Wagtail Admin > Editorial > Subsecciones`. Verify the root form contains
  `Nombre`, `Slug`, and `Orden` with no parent field. Verify the child form also
  contains the required `Sección principal` select, offers only roots, permits
  moving a fictional child between roots, rejects clearing its parent, and
  preserves protected deletion. Remove any unused fictional fixture afterward.
- News route: `/admin/pages/<page-id>/edit/`, tab `Edición de la noticia`, field
  `Secciones y subsecciones`. Use `Investigación ficticia sobre música
  comunitaria`, select Música plus Entrevistas and Comunidad, save/reopen, clear
  all values, and verify the exact publish error.
- Public route: open the fictional news detail and
  `/noticias/?seccion=cultura`. Confirm `Cultura › Música` and `Entrevistas ›
  Comunidad` appear once in the upper classification area, the lower
  classification row is absent, main-only navigation and filtering remain
  unchanged, and the expected four-value `articleSection` array remains.
- Curator route: use a separate Curador SEO account in an authorized workflow
  state. Verify read-only paths and the absence of taxonomy/snippet controls.
- Runtime revision routes: preview the draft with representative explicit
  selections, revert between revisions with different selections, and complete
  the authorized moderation workflow. Confirm exact identities at each step and
  record the result only after those UI paths are actually exercised.

## Warnings and deferred items

- Wagtail system checks continue to emit the existing Treebeard 6 compatibility
  warning for Wagtail collection/page managers during the isolated browser
  stack. It did not fail migration, startup, or the three Chromium scenarios;
  no dependency upgrade belongs to this correction.
- The 18 seeded subsections are explicitly provisional and editable. They are
  not the institution's definitive taxonomy.
- Historical revisions store taxonomy identities, not label or hierarchy
  snapshots. A later taxonomy rename or move intentionally changes how an old
  identity is displayed.
- Manual visual, permissions, and end-to-end workflow UAT remains for the
  maintainer; automated browser coverage used only the disposable Director
  fixture.

## Collisions and reusable boundaries

- **EPIC5-002:** reuse `NewsTaxonomy.article_section_values` and the read-only
  visible-path boundary for metadata/search work. A second `articleSection`
  derivation would risk ordering and derived-parent drift.
- **EPIC6-002:** reuse `public_news_pages()` and the main-section descendant
  predicate as the current filter contract. This ticket intentionally exposes
  no subsection URL or advanced combined filter UI; those decisions remain in
  EPIC6-002.

## New Work Discovered

- **Definitive institutional taxonomy.** Evidence: migration `0013` and the
  editor guide explicitly identify the 18 subsections as provisional. Impact:
  editors can validate the workflow, but the names are not an approved final
  information architecture. Suggested disposition: obtain a product/editorial
  decision on the definitive list and reconciliation approach; do not add a
  bulk importer or replacement workflow to EPIC3-009.
- **Manual Wagtail runtime UAT.** Evidence: automated coverage reconstructs
  revision objects and the browser spec exercises draft persistence plus a
  blocked publish attempt, but it does not causally drive preview, revert, or a
  complete moderation workflow. Impact: those integration paths retain manual
  confidence risk. Suggested disposition: execute the documented maintainer UAT
  before release; do not add the superseded four-test causal matrix.
- **Future subsection filtering.** Evidence: the implemented public contract
  intentionally accepts only a main-section slug and rejects subsection slugs.
  Impact: subsection URLs, combined filters, search, and pagination are absent
  by design. Suggested disposition: retain this work in the already identified
  EPIC6-002 scope; this is not a new implementation ticket.
- **Metadata/search reuse.** Evidence: EPIC3-009 centralizes visible paths and
  `articleSection` values in `NewsTaxonomy`. Impact: EPIC5-002 could introduce
  ordering or derived-parent drift if it recomputes them. Suggested disposition:
  reuse the existing boundary in EPIC5-002 rather than creating another
  taxonomy derivation.

## Durable process-learning candidates

- Probe a real Wagtail/modelcluster child relation before writing a historical
  revision migration; documented field names alone do not prove serialized
  revision shape.
- Migration tests that flush data can retain migration-recorder rows while
  deleting data-migration seeds. Test migration helpers should restore only the
  minimum published prerequisites before running a leaf migration.
- Wagtail action-menu submits can remain mounted while hidden. The general
  lesson has been promoted to the `AGENTS.md` browser-testing rule: inspect DOM
  and accessibility state, model disclosure preconditions explicitly, classify
  failures before retrying, and create a shared helper only after the same
  interaction exists in at least two specs.

## Post-review clarification outcome

- No production defect was found, so production code, migrations, tests, and
  browser specs were not changed.
- The existing `Revision.as_object()` assertions already satisfy the reduced
  automated revision contract with exact explicit IDs.
- Feedback claims now distinguish automated reconstruction, the browser's
  blocked-publication evidence, and pending manual preview/revert/workflow UAT.
- `AGENTS.md` now contains the permanent evidence-first Playwright locator and
  disclosure-precondition rule without ticket-specific retry history.
- No maintainer UAT result has been invented.
