# QA-001 — Stage A Technical Feedback

## Status

Implementation is prepared for maintainer review. This feedback records only
local, automated evidence. A real QA-001 pre-push, Pull Request Validation,
Browser Regression in the PR, the post-merge documentation-only probe, and
required-check configuration remain operational evidence for Luis.

## Validation policy

`scripts/validation_delta.py` is the repository-owned, stdlib-only source of
truth for documentation-only classification. Its explicit allowlist is:

- `docs/**`
- `README.md`
- `AGENTS.md`
- `THIRD_PARTY_NOTICES.md`
- `.github/pull_request_template.md`

Every other path, missing or unresolvable ref, invalid pre-commit push
environment, and ref deletion selects `full-validation`. The classifier does
not inspect the worktree or staged files. Existing destination branches use the
actual remote-old to local-new endpoint delta; new branches use a merge-base
delta from the configured remote's `main`; Pull Requests use their base/head
merge-base delta.

The pre-push hook invokes this policy through pre-commit's documented
`PRE_COMMIT_*` push-ref environment contract. Documentation-only pushes report
their lightweight route and do not start Docker, pytest, or migration checks.
All other pushes run `make check`. Pull Request Validation always starts for
pull requests to `main` and retains the visible job name `Validate repository`;
it uses the same script against the checked-out PR head and `origin/main`.

## Second-pass suite inventory and rationalization

| Suite / test area | Protected risk | Evidence type | Possible overlap | Disposition | Replacement / surviving evidence |
| --- | --- | --- | --- | --- | --- |
| `test_admin_uat.py::test_seo_assistant_javascript_restores_served_url_after_canonical_clear` | Clearing canonical input restores the served public URL in the SEO preview | Source-literal JavaScript inspection | Browser SEO editor behavior | Replace — deleted | `z-related-keyphrases.spec.js` now changes then clears the canonical control and observes the restored preview URL. |
| `test_admin_uat.py::test_seo_assistant_javascript_persists_tab_only_after_successful_draft_save` | A successful draft save returns the editor to the active SEO tab | Source-literal JavaScript inspection | Browser SEO editor behavior | Replace — deleted | `z-related-keyphrases.spec.js` selects the SEO tab, saves a draft, and observes the selected visible tab after navigation. |
| `test_admin_uat.py::test_seo_assistant_keeps_served_url_separate_from_external_canonical` | Initial server-side hydration distinguishes an external canonical URL from the served URL | Django rendered Admin response | New browser test | Keep | The browser test covers client-side updates; this test separately verifies the server-provided initial values. |
| `test_admin_uat.py::test_editorial_snippet_destinations_are_available` | Taxonomy lists do not expose an object through the wrong management surface | Django rendered list response | Browser taxonomy navigation and labels | Simplify and rename to `test_taxonomy_lists_exclude_cross_type_objects` | Retains server-side cross-type object isolation; removes labels, add links, and unrelated snippet availability already covered by browser or registration. |
| `test_admin_uat.py::test_taxonomy_management_forms_keep_types_fixed_and_parent_choices_root_only` | Root-only parent choices and crafted POST protection | Form and HTTP behavior | Browser add-surface controls | Simplify | Retains queryset restriction, crafted invalid parent rejection, ignored root parent, required parent, and reassignment persistence; removes add-page headings, labels, and field visibility covered by `taxonomy.spec.js`. |
| `test_forms.py` taxonomy cases | Draft/publish validation, revision-aware assignments, widget error expansion | Form and persistence behavior | Browser tree interactions | Keep | Browser proves interaction; these tests prove server validation, revision serialization, and invalid form behavior. |
| `test_models.py` taxonomy cases | Hierarchy, database constraints, deletion protection, and derived taxonomy | Model/database behavior | Form and browser taxonomy tests | Keep | The apparent overlap is layered: constraints and protected deletion cannot be established by browser happy paths. |
| `test_language.py::test_news_admin_panels_explain_content_authoring_and_public_credit` | Internal Wagtail panel classes and ordering | Private panel structure | Admin rendering, smart-paste, taxonomy, and SEO browser tests | Delete | Observable editor contracts remain in Admin HTTP and Chromium tests; internal order/classes are not a durable language contract. |
| `test_language.py::test_social_image_metadata_panels_remain_in_seo_assistant` | Internal promote-panel nesting | Private panel structure | SEO Admin rendering and browser SEO editor | Delete | No product behavior is asserted beyond implementation placement; visible SEO configuration remains covered at the rendered editor boundary. |
| `test_language.py::test_related_keyphrase_inline_is_immediately_after_primary_keyphrase` | Private inline-panel adjacency | Private panel structure | `test_forms.py` related-keyphrase validation and browser related-keyphrase editing | Delete | Server validation and the end-to-end add/reorder/delete/save workflow remain. |
| `test_language.py::test_custom_editor_visible_labels_are_spanish` | Spanish model/editor labels and help text | Model metadata/UI-copy contract | Model/block schema assertions | Simplify | Removes `max_length` and legacy field-absence assertions, which are schema rather than language evidence; Spanish labels remain. |
| `test_public_share.py::ShareMarkupParser` and `test_live_noindex_detail_renders_escaped_share_actions_in_contract_order` | Server metadata escaping, privacy, no third-party embed leakage, share interaction markup | Custom HTML parser plus rendered response | `public-share.spec.js` channel controls, order, links, target/rel, notification, and keyboard behavior | Simplify; parser deleted and test renamed `test_live_noindex_detail_escapes_server_rendered_share_metadata` | Keeps noindex, escaped `data-share-*` attributes, canonical source, privacy omission, XSS safety, no iframe, and local script inclusion. URL-builder tests retain exact encoding. |
| `test_public_share.py::test_share_link_builder_*` | Exact social/email URL encoding and empty-description behavior | Pure Python URL-builder tests | Browser link parsing | Keep | Browser checks rendered links, while these lower-cost tests retain edge-case encoding and CRLF semantics. |
| `tests/browser/public-share.spec.js` | Web Share/clipboard detection, notices, keyboard use, responsive fallback, rendered link behavior | Chromium behavior | Rendered share response | Keep | Owns browser/runtime behavior after parser simplification. |
| `tests/browser/taxonomy.spec.js` | Menu navigation, add surfaces, tree disclosure, persistence, publish error, and public detail | Chromium behavior | Admin taxonomy HTML assertions | Keep | It replaces removed observable HTML assertions, while server-side enforcement stays in pytest. |
| `test_blocks.py` | StreamField configuration, table bounds, editor integration, and legacy-content technical compatibility | Block/model behavior | Smart-paste browser spec | Keep | Browser covers editing workflow; these deterministic tests cover configuration and compatibility boundaries. |
| `test_smart_paste.py` | Sanitization, table conversion, limits, endpoint method/CSRF/permission enforcement | Parser and HTTP behavior | Smart-paste browser workflow | Keep | Browser exercises a representative flow; the suite retains security and hostile-input cases. |
| `test_seo.py`, `test_seo_linguistics.py`, `test_seo_nlp.py`, `test_advanced_readability.py` | Deterministic SEO, Spanish NLP, failure caching, and metric boundaries | Domain/unit behavior | SEO browser display | Keep | Browser evidence cannot replace exact linguistic, numerical, cache, and failure-safety contracts. |
| `test_seo_public.py` | Public metadata, JSON-LD, robots, and sitemap privacy/indexing | Server rendering behavior | Public-share browser spec | Keep | The browser spec covers sharing controls, not metadata and crawler contracts. |
| `test_migrations.py` | Published migration history and data transitions | Historical migration tests | None suitable | Keep — high-risk | No reduction justified without risking historical compatibility. |
| `test_mvp_access.py` | Roles, permissions, crafted POST denial, and native workflow | Authorization/workflow integration | Browser role flows | Keep — high-risk | Browser proves a few user flows but cannot replace the permission matrix and crafted-request protection. |
| `apps/home/tests.py`, `config/settings/tests.py`, `tests/ops/test_staging_deploy.py` | Home behavior, settings safety, deployment orchestration | Focused unit/integration tests | None material | Keep | No concrete duplicate branch found. |
| `tests/test_validation_delta.py` | Docs-only routing cannot bypass executable validation | Temporary-Git-repository tests | CI/pre-push integration | Add | Deterministically covers both shared classifier consumers' boundary. |

### Applied rationalizations

- Deleted five incidental source/private-structure tests: the two SEO JavaScript
  source-literal tests and three `test_language.py` panel-structure tests.
- Replaced the two SEO source tests with one observable Chromium scenario in the
  existing SEO browser spec; no new spec file was added.
- Simplified two taxonomy Admin tests by removing UI labels and field-presence
  assertions already exercised in `taxonomy.spec.js`, while retaining all
  backend restrictions and cross-surface isolation.
- Removed `ShareMarkupParser` and its parsing assertions. The simplified server
  test retains only server-only privacy, escaping, metadata, iframe, and script
  contracts; the existing browser spec owns rendered interaction and link UI.
- Removed schema-only assertions from the Spanish language contract. No helpers
  were consolidated: the audited fixtures differ in required page state,
  permissions, or test semantics, so a shared abstraction would add coupling.

There were no merged or moved tests. Migration history and authorization/workflow
coverage remain unchanged by design.

## Browser Regression boundary

The conditional browser workflow remains separate from `make check` and is not
a global required check. Its boundary now additionally covers the taxonomy form
used by `taxonomy.spec.js`; the SEO engine, panels, JavaScript, and CSS used by
the SEO curator spec; `config/urls.py` for browser-accessible routes; and the
shared base template used by public browser behavior. Existing smart-paste,
taxonomy, public-share, fixture, Docker, and browser-runner paths remain.

## Automated validation

- Pytest count: 429 before second-pass rationalization; 424 collected after.
- Playwright count: 5 before second-pass rationalization; 6 passed after. The
  increase is the single observable SEO replacement for two deleted source tests.
- `tests/test_validation_delta.py`: final review correction pending; the
  superseding result is recorded below.
- `pre-commit run check-yaml --files .pre-commit-config.yaml
  .github/workflows/pr-validation.yml .github/workflows/browser-regression.yml`:
  passed.
- `make check`: passed locally after rationalization (Ruff, migration drift,
  and 424 pytest tests).
- `make browser-test`: passed locally after the browser replacement through the
  isolated Docker Compose Chromium runner (6 specs).
- `git diff --check`: passed after the final feedback update.

## Deferred operational evidence

- UAT A: real QA-001 push and PR workflow results, including the full route.
- UAT B: post-merge docs-only pre-push and temporary PR probe.
- UAT C: Luis verifies or configures `Validate repository` as required on
  `main`, while Browser Regression remains non-required globally.

## New Work Discovered

None during the QA-001 boundary audit.

## Maintainer-approved third-pass addendum: test cost and coverage

The maintainer-approved QA-001 addendum superseded the original ticket's
coverage/runtime exclusion only for this execution. It did not authorize
product, permission, migration-history, staging, or repository-cleanup work.

### Plain pytest duration evidence

The initial plain-profile command was run before the migration optimization:

```bash
docker compose run --rm web sh -c 'until nc -z db 5432; do sleep 1; done; DJANGO_SETTINGS_MODULE=config.settings.test pytest -o cache_dir=/tmp/school-newsroom-pytest-cache --durations=25 --durations-min=0.5'
```

It collected 424 tests, but the execution transport truncated the terminal
output before the duration table and total. Therefore the baseline total and
top-ten durations are not recorded here rather than reconstructed or guessed.
This is a documentation limitation, not a claimed timing result.

Investigation found two migration tests making full historical transitions only
to exercise failure branches in pure migration helpers:

- the multiple-locale invariant failure test;
- the known-bootstrap-admin target-conflict failure test.

The final maintainer review restored both tests to the historical migration app
registry and transition boundary. Their runtime-registry performance shortcut
was removed: migration fidelity takes precedence over a small timing gain.

The final plain profile used the same command with `-q` and reported `426
passed in 46.17s`. Its top ten were:

| Duration | Phase | Test |
| --- | --- | --- |
| 4.97s | setup | `apps/home/tests.py::test_wagtail_admin_login_loads` |
| 2.88s | call | `test_bootstrap_home_migration_fails_for_unexpected_specific_page_type` |
| 2.86s | call | `test_bootstrap_home_migration_fails_for_unsupported_revision_state` |
| 2.78s | call | `test_bootstrap_data_migration_normalizes_known_admin_bootstrap_names` |
| 2.69s | call | `test_bootstrap_data_migration_converts_generic_bootstrap_home_page` |
| 2.66s | call | `test_bootstrap_data_migration_aligns_locale_and_admin_language` |
| 2.21s | call | `test_epic3_002_migration_preserves_existing_news_without_fabricated_data` |
| 1.96s | call | `test_epic3_003_body_migrations_preserve_then_convert_historical_content` |
| 1.65s | call | `test_epic5_001_migration_preserves_news_with_blank_safe_seo_defaults` |
| 0.94s | call | `test_epic3_009_migrates_current_page_and_revision_relation_shape` |

All final durations at or above two seconds are the one-time Django database
setup or deliberate historical migration transitions. They remain because
migration-history protection is high risk; no test was skipped, moved out of
the plain suite, or weakened for timing. Coverage timing is reported separately
below and must not be compared directly with this plain-pytest profile.

### Coverage gate

`pytest-cov>=6.0,<7.0` was added to `requirements.txt`; the rebuilt image
resolved pytest-cov 6.3.0 with coverage.py 7.15.4. `.coveragerc` enables branch
coverage for first-party runtime directories `apps`, `config`, `ops`, and
`scripts`. It omits only migration modules from the percentage, as approved,
and test modules from the measured application source; no production module,
settings module, or operational module was broadly excluded.

`make coverage` runs the complete pytest suite with
`--cov-report=term-missing:skip-covered` and `--cov-fail-under=90`. `make test`
remains plain pytest. `make check` now runs Ruff, migration drift, then this
coverage gate once instead of running plain pytest a second time.

The initial coverage command exposed two classified failures:

1. The initial classifier-test design created temporary Git repositories. The
   Docker test image intentionally did not contain `git`, so that design
   produced 414 passed, 10 errors, and 87.0% coverage. The maintainer rejected
   adding Git to the shared web/staging image; the final correction replaces
   those test-local repositories with a narrow adapter-level Git double.
2. With the environment corrected, all 424 tests passed but coverage was
   88.30%, below the required 90%.

Coverage remediation added two behavior-focused tests for the disposable
browser fixture management command: its non-browser-settings guard and its
complete fixture contract (roles, expected IDs, workflow assignment, public
metadata, and completion output). The final review correction removes the
collection-order workaround and is recorded below.

Final coverage evidence:

- `make coverage`: passed; `426 passed in 66.21s`.
- Branch coverage: `90.02%` (90% minimum met).
- The report retains visible gaps in settings entry modules, deployment error
  paths, smart-paste edge paths, and selected command failures. They are not
  hidden by new omissions and remain candidates for separately scoped work.

### Third-pass validation and scope boundaries

- `tests/test_validation_delta.py`: superseded by the final review correction
  below.
- `apps/news/tests/test_browser_fixture.py`: superseded by the final review
  correction below.
- The full plain profile passed (`426 passed in 46.17s`).
- `make coverage` passed as recorded above.
- Final `make check`: passed Ruff, migration drift, and coverage (`426 passed
  in 67.15s`, 90.02%). Its first technical-close attempt stopped at Ruff before
  migration or pytest because the new test's import block was not in the
  repository's required order; the focused Ruff correction passed before the
  single final retry.
- Browser Regression was not rerun in this pass: no Playwright spec, browser
  fixture behavior, or product browser boundary changed. The second pass's
  isolated runner result remains `6 passed`; real PR Browser Regression remains
  deferred operational evidence.

No product behavior, roles, permissions, migrations, staging configuration, or
browser trigger policy was changed by this addendum. No incidental product work
was implemented. The final maintainer correction leaves `docker/web/Dockerfile`
unchanged: Git is not installed in the shared web/staging image.

## Final maintainer review correction

The final maintainer review corrected four QA-001 implementation details before
commit/push. No unrelated rationalization, product, staging, or GitHub-setting
work was performed.

### Pre-commit managed pre-push contract

The local pre-push hook is managed by pre-commit, so
`scripts/validation_delta.py pre-push` now uses pre-commit's documented
`PRE_COMMIT_FROM_REF`, `PRE_COMMIT_TO_REF`, and `PRE_COMMIT_REMOTE_NAME`
environment contract. It does not rely on Git's raw pre-push stdin reaching the
configured local hook.

- Existing destination branches classify the direct remote-old to local-new
  endpoint delta.
- New branches classify the local endpoint against the configured remote's
  `main` from their merge base, allowing the QA-001 UAT B documentation-only
  branch shape to take the lightweight route.
- Ref deletion, missing/invalid refs, an absent remote name, and an
  unresolvable remote main fail closed to full validation.
- Pull Request Validation remains merge-base-to-head classification. The shared
  allowlist and fail-closed path policy are unchanged.

`tests/test_validation_delta.py` now has 26 deterministic Git-adapter tests:
existing docs/executable endpoints, new-branch docs/executable deltas, missing
remote main, deletion, invalid refs, both rename directions, direct endpoint
semantics, PR merge-base semantics, and the explicit UAT B README-commit shape.
The command-level test invokes the classifier with the documented environment,
not injected raw stdin. The adapter doubles only the classifier's Git command
boundary; production `scripts/validation_delta.py` still invokes real Git via
`subprocess` in actual pre-push and Pull Request Validation execution.

### Browser fixture isolation

`test_z_browser_fixture.py` was replaced by the responsibility-based
`test_browser_fixture.py`; no test filename controls collection order. The
tests use normal `pytest.mark.django_db` rollback isolation. Fixture setup
reuses an existing Wagtail root, collection root, HomePage, and persisted browser
fixture page when present. Expected IDs come from PostgreSQL's Wagtail Page
sequence, rather than a maximum-row assumption, so historical migration tests
cannot make the test mispredict a newly allocated page ID.

The required explicit ordering proof passed in both directions:

- migration suite then browser fixture suite: `22 passed in 40.10s`;
- browser fixture suite then migration suite: `22 passed in 40.28s`.

### Historical migration boundary restored

The two attempted runtime-registry shortcuts were removed. These tests again
migrate to `BEFORE_NEWS_0002`, obtain models from that historical app registry,
and invoke the migration helpers with that historical state:

- `test_bootstrap_data_migration_locale_invariant_fails_for_multiple_locales`;
- `test_bootstrap_admin_name_normalization_fails_on_target_conflict`.

Their final plain-profile durations are respectively 2.65s and 2.67s. This is
intentional high-risk migration-history cost. The successful final plain profile
reported `431 passed in 49.57s`; its ≥2-second cases were the one-time Django
setup (4.89s) and the protected migration transitions (2.11s–2.78s).

### Final correction validation

- Focused Ruff for the corrected Python files: passed.
- `make coverage`: passed, `431 passed in 74.25s`, branch coverage `90.03%`.
- Final `make check`: passed Ruff, migration drift, and coverage (`431 passed
  in 72.73s`, branch coverage `90.03%`).

### Corrected failure classifications

- Restoring the migration cleanup initially introduced an indentation error;
  corrected to the historical cleanup structure before test execution.
- Replacing `transaction=True` exposed fixture assumptions about a pre-existing
  HomePage and Page IDs after historical migration tests. The test now reuses
  that state and reads the real PostgreSQL sequence. No migration or production
  behavior changed.

## Final maintainer correction: Git-free classifier tests

The maintainer rejected the temporary Git-repository test design and the
associated attempt to install Git in the shared web/staging Docker image. The
QA-001 Dockerfile diff has been removed. After rebuilding the image, an explicit
container check confirmed that `git` is not installed.

`tests/test_validation_delta.py` now replaces only the `git_output` adapter
with deterministic responses for the exact Git commands expected by the
classifier. This keeps production behavior intact: `scripts/validation_delta.py`
continues to run real Git commands through `subprocess` when pre-push or Pull
Request Validation actually executes. The test suite does not replace that
production integration with worktree or staged-file inspection.

The 26 focused tests cover documentation-only and executable deltas, deletion,
rename, multiple commits through merge-base classification, valid and
unresolvable refs, missing push metadata, command dispatch, and full-route
`make check` execution. In particular, the UAT B shape is modeled as a new
branch with a zero remote-old ref, a local new ref, `origin/main`, and a
README-only merge-base delta; it selects `documentation-only`. The executable
twin selects `full-validation`.

### Final automated evidence

- Focused classifier suite: passed, `26 passed in 0.03s`, in the rebuilt
  Git-free web image.
- Focused Ruff for `tests/test_validation_delta.py` and
  `scripts/validation_delta.py`: passed.
- `make coverage`: passed, `435 passed in 72.44s`; branch coverage `90.14%`
  against the unchanged 90% requirement.
- The first final-correction coverage attempt reached 89.66% because the new
  script command branches were not yet directly exercised. Meaningful CLI and
  full-route tests corrected that gap; no assertion or coverage threshold was
  weakened.
- Final `make check`: passed. Ruff and migration drift passed before the full
  435-test coverage phase; the Docker runner completed successfully with the
  same Git-free validation environment and unchanged 90% gate.

### Deferred operational evidence

The adapter tests provide deterministic unit evidence only. Luis must still
collect real-Git lifecycle evidence for a QA-001 pre-push, Pull Request
Validation, Browser Regression in the actual PR, UAT A, post-merge docs-only
UAT B, and required-check UAT C. Browser Regression was not rerun for this
correction because no Playwright spec, browser fixture behavior, or browser
trigger boundary changed.

## Pull Request operational evidence

The QA-001 implementation was committed as `6c327c3` and pushed through the
real repository pre-push hook. The hook completed successfully.

The Pull Request was opened against `main` and the real GitHub workflows
completed successfully:

- `Pull Request Validation / Validate repository`: passed.
- `Browser Regression / Browser regression`: passed.
- GitGuardian Security Checks: passed.
- The Pull Request reported no conflicts with `main`.
- Automatic GitHub/Codex review completed without findings.

This closes the pre-merge operational evidence for QA-001.

Still intentionally deferred until after merge:

- UAT B: real documentation-only new-branch pre-push and temporary PR probe.
- UAT C: verify/configure `Validate repository` as required on `main`, while
  Browser Regression remains conditional and not globally required.
