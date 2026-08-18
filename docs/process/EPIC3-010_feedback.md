# EPIC3-010 Final Implementation Feedback

## Implemented architecture

- `AuthorProfile` is the reusable, deliberately editorial public identity. It has
  public name, slug, optional Wagtail image, biography, public email, position,
  and work URL, plus optional protected links to either `User` or
  `MinorContributor`. It is never manufactured from either internal identity.
- `NewsPageAttribution` is the sole ordered authorship boundary. Its three
  mutually exclusive row kinds are `AUTHOR`, `PUBLIC_CREDIT`, and
  `INTERNAL_CONTRIBUTOR`; the legacy runtime models are removed.
- The unpublished `0020_unify_authorship_attribution` migration creates both
  models and constraints, copies legacy public credits followed by internal
  contributors in stable per-relation order, then removes the legacy models. It
  does not create fuzzy or synthetic author identities and preserves NewsPages.
- Historical Wagtail revisions are retained. New revisions serialize and reopen
  the unified rows. Historical legacy child relation names are not reconstructed;
  the migration/revision tests document that proportional Wagtail limitation.

## Editorial, permissions, and privacy boundaries

- Draft validation remains deferred. A publish/review action requires at least
  one `AUTHOR` or non-empty `PUBLIC_CREDIT`; an internal contributor alone never
  supplies public identity.
- An author profile linked to a minor requires the identifiable-minors and
  verified-authorizations flags before publication. Minor profiles reject public
  email, and public templates/selectors never expose `MinorContributor` internal
  fields or an internal full name.
- Inactive profiles are excluded from new Author chooser selections, including
  direct/tampered replacements. An existing selected inactive profile remains a
  valid historical value for editing, revisions, public cards, and its archive
  slug.
- Native Wagtail snippet chooser/viewset behavior is retained. Director/editor
  receives the needed AuthorProfile view/add/change permissions; chooser
  responses require model view permission and native contextual create/edit
  controls follow add/change. Curador SEO remains unable to access editorial
  attribution, AuthorProfile, School, or minor-contributor surfaces.
- The approved contextual FK paths are NewsPage → School, Attribution →
  AuthorProfile, Attribution → MinorContributor, MinorContributor →
  ContributorGroup, and ContributorGroup → School. User and geography remain
  excluded; Wagtail Images retains its native behavior.

## Public behavior and query boundary

- The public byline includes only ordered AUTHORS and free public credits.
  Author cards render after the body and before sharing/tags, omit empty optional
  fields, use safe external links, and never render internal contributor data.
- Author cards link to the structured `/noticias/?autor=<slug>` archive filter.
  The archive has no visible Author selector, preserves `autor` through search,
  taxonomy, tag, geography, ordering, and pagination, provides a removable
  author chip, and keeps inactive historical author archives valid.
- Search remains title > tags > body. Author names and biographies are not part
  of full-text search.
- JSON-LD emits an `AUTHOR` as `Person`, includes only explicitly supplied
  `work_url`, omits email by default, keeps generic free public credit metadata,
  and omits internal contributors.
- Public selectors prefetch only AUTHOR/PUBLIC_CREDIT rows and their public
  profile/photo relation. Query-count coverage verifies bounded archive/detail
  growth without loading internal minor data.

## Automated evidence

- The final UAT-correction focused suite passed: `151 passed, 2 warnings` in
  18.51s across model, form, Admin/UAT, browser-fixture, permission, and public
  rendering tests. Both warnings are Django's existing `URLField` Django-6
  default-scheme deprecation.
- The historical migration suite exercises the 0019 → 0020 boundary with legacy
  rows, deterministic order, page/revision preservation, and a newly saved
  unified revision. Model/form, archive, public rendering/share, SEO metadata,
  and permission tests cover the acceptance boundary.
- `python manage.py makemigrations --check --dry-run` reported `No changes
  detected`; no persistent database migration was applied.
- Final technical close: `make check` passed lint and migration drift, then
  completed `511 passed, 2 warnings in 132.74s` at `90.44%` total coverage. The
  warnings are the same Django `URLField` deprecation. `git diff --check`
  passed.

## Final browser evidence

- `make browser-test` ran 12 Playwright specifications successfully. The
  Director flow logged in, used the real `Autoría y créditos` inline panel,
  searched and selected an author profile, contextually created and edited an
  AuthorProfile, added a free public credit and internal contributor, retained
  order, saved, and reopened the page. It also contextually created and edited
  School, then exercised author-only and free-credit-only publication success,
  internal-only rejection, and minor-author privacy rejection.
- The public flow used the mobile viewport, verified the ordered mixed byline,
  two cards, safe degradation of missing optional fields, email/work links,
  keyboard navigation to the active author archive, archive-filter preservation,
  and absence of a visible Author control. The spec retained its strict
  attributable-console-error assertion and passed.
- The same browser run verifies initial, filtered, and cleared-result states for
  the protected User and MinorContributor choosers. It also cancels and selects
  a native image chooser from contextual AuthorProfile creation, then confirms
  that the parent form remains editable with only its own backdrop present.

## Maintainer UAT

Maintainer UAT completed successfully after two corrective UAT cycles.

The first UAT pass confirmed the core authorship/public-profile behavior and
identified concrete Admin UX and validation gaps: manual slug entry, a
non-searchable internal User selector, a plain contextual image select,
non-discriminated attribution rows, raw database-constraint wording, and a
public author card that did not yet read clearly as a distinct component.

Those findings were corrected with stable automatic slugs, native chooser
patterns, discriminated attribution-row UI with stale-value clearing, clear
Spanish server-side shape errors, native Wagtail image selection, and a scoped
responsive author-card presentation.

The UAT rerun then identified three remaining Admin integration defects: the
protected internal User chooser lost results while searching and did not restore
them when cleared; the related MinorContributor field still used a plain select;
and opening the native image chooser from contextual AuthorProfile creation
could leave the parent modal blocked.

The final correction makes the User results endpoint a native chooser
partial-results view with full-name/username searching and blank-query
restoration, gives MinorContributor the native searchable snippet chooser in
the relevant contexts, and adds the minimal nested-modal lifecycle adapter
needed for contextual AuthorProfile image cancel/select behavior.

The maintainer reran only the previously failed UAT boundaries. User chooser
search/reset, MinorContributor chooser search/reset, and contextual image
cancel/select all passed. No additional UAT defect was reported.

**Maintainer UAT: PASSED.**

## PR review and CI correction closure

- PR review found that the application-level minor-email validation could be
  bypassed by direct database writes. Migration `0021` clears public email from
  any historical minor-linked profiles before adding the database constraint
  `minor_contributor IS NULL OR email = ''`. Focused tests cover direct create,
  queryset update, and the historical migration boundary.
- PR review found that automatic slug collisions could exceed the actual slug
  field limit. Generation now derives its limit from the model field and
  truncates the base around each `-<n>` suffix. Focused tests cover a maximum
  length base, `-2`, `-10`, and a stable existing slug on edit.
- Browser CI failed on clean read-only checkouts because the ignored local media
  directory was hidden by the `.:/app:ro` bind mount while Compose still tried
  to mount a tmpfs at `/app/media`. Browser settings now use the disposable
  `/tmp/school-newsroom-browser-media` path and the conflicting tmpfs mount is
  removed; the application bind mount remains read-only.
- Focused review/CI regression evidence: `4 passed, 2 warnings` in 6.72s;
  `python manage.py makemigrations --check --dry-run` reported `No changes
  detected`; and `make browser-test` passed all 12 specifications. The warnings
  are the existing Django `URLField` Django-6 default-scheme deprecation.
- The final post-correction `make check` passed lint, migration drift, and
  `514 passed, 2 warnings in 133.84s` at `90.49%` total coverage. `git diff
  --check` passed.
- These were PR-review and CI-environment corrections only. Maintainer UAT
  remains **PASSED**; no further UAT behavior was requested or asserted here.

### Final clean-CI autosave race correction

- A subsequent clean GitHub browser run confirmed the media-mount correction,
  but exposed two deterministic `400 Bad Request` autosave responses while
  chooser-backed attribution rows were transiently incomplete: an `AUTHOR`
  before its AuthorProfile was selected and an `INTERNAL_CONTRIBUTOR` before
  its MinorContributor was selected.
- Root cause: Wagtail 7.4 autosave could cross its configured debounce interval
  while the editor was still inside a chooser. The exact server/database
  attribution-shape guards correctly reject those incomplete rows, so weakening
  them would have broken the approved integrity boundary.
- `attribution_rows.js` now pauses Wagtail autosave only while a non-deleted
  attribution row has a selected kind without its required payload, and resumes
  autosave on the same input/change event that completes or removes that row.
  Manual save, publication validation, forged-payload validation, and database
  constraints remain unchanged.
- The Playwright regression now deliberately crosses the configured autosave
  interval for incomplete AUTHOR and INTERNAL_CONTRIBUTOR rows and retains the
  strict browser-console assertion.
- Maintainer UAT remains PASSED; the focused manual rerun of the autosave race
  also passed.

## Warnings and retry classification

- A strict browser run reproduced a 400 from `POST /admin/pages/<id>/edit/`
  immediately after the contextual image-chooser trigger. The trigger was inside
  the parent page form while Wagtail's legacy workflow removed direct child
  modals. The correction prevents that contextual click's default form
  submission and preserves the parent-modal lifecycle. The focused re-run and
  final 12-spec browser run passed with the strict console assertion intact.
- The remaining warnings are the existing Django `URLField` deprecation noted
  above.

## New Work Discovered

None. No unrelated implementation was added.

## Process retrospective

EPIC3-010 exposed a material execution-process failure even though the approved
ticket had a coherent outcome and unusually explicit acceptance criteria. The
ticket should not be split retroactively and the normal model-routing policy
does not need to become more expensive by default. The primary durable change
belongs in F009.

### What went wrong

- The first implementation handoff was treated as technically closed because
  focused tests, browser tests, coverage, and `make check` were green, but the
  complete ticket acceptance matrix had not been reconciled requirement by
  requirement.
- Review findings were discovered incrementally and corrective prompts were sent
  before the full diff/ticket review had finished. This created a cascade of
  pre-UAT passes instead of one complete review followed by one complete
  correction.
- One corrective prompt was intentionally split into WP1/WP2 even though WP1
  could not possibly reach the next lifecycle gate. That was an orchestration
  error and should not be repeated.
- A corrective prompt explicitly prohibited feedback/diff-artifact updates even
  though the persistent repository instructions require those artifacts at the
  end of an implementation pass.
- General close gates were rerun several times while known acceptance gaps still
  existed. Green aggregate test counts were repeatedly mistaken for ticket
  completeness.
- The execution exceeded the intended resource budget substantially: more than
  40 percentage points of the weekly token allowance were consumed before
  ticket completion, with multiple long Codex passes and roughly two hours of
  aggregate agent execution before final UAT closure.
- UAT screenshots were not initially handed to Codex explicitly even when the
  corrective prompt depended on visual evidence. Codex cannot be assumed to see
  images from the maintainer/ChatGPT conversation.

### Required F009 improvements

1. Add a temporary acceptance-coverage ledger for tickets with explicit
   acceptance/test/browser matrices:
   `requirement -> implementation -> evidence -> PASS/PENDING`.
2. Do not allow technical close while any known pre-UAT required item remains
   pending. Aggregate tests/coverage are gates, not proof of completeness.
3. ChatGPT must finish the complete diff/ticket review before emitting a
   corrective implementation prompt.
4. A pre-UAT corrective prompt must contain all known findings and must be
   capable of ending at UAT readiness. Never knowingly schedule a second
   pre-UAT correction.
5. Expected pass budget:
   - one implementation pass;
   - at most one corrective pre-UAT pass;
   - one additional pass only for actual UAT findings;
   - one additional pass only for PR-review findings.
   Exceeding that budget is a process-failure signal requiring explicit
   reassessment rather than another automatic iteration.
6. Enforce the existing token/resource hard pause. Once the configured ticket
   budget or weekly reserve threshold is crossed, do not launch another Codex
   pass without explicit maintainer authorization.
7. Run the expensive general gate only after acceptance reconciliation says the
   implementation is ready for technical close. After later deltas, rerun only
   evidence actually invalidated by the delta, then re-establish the necessary
   close gate.
8. Every implementation/correction pass must leave the required factual feedback
   and complete diff-review artifact consistent with the checkout unless the
   pass is explicitly only a continuation of an interrupted close.
9. If an agent finishes implementation but times out before final gates or
   artifacts, the next instruction should be a minimal closure continuation,
   not a reopened implementation pass.
10. When UAT findings include screenshots or other visual evidence, ChatGPT must
    tell the maintainer *before the Codex prompt* exactly which images need to be
    attached and why. Images that can be fully replaced by textual facts need
    not be forwarded.
11. Work packages may structure a single Codex prompt internally, but should not
    become planned sequential user-visible passes for one coherent ticket.
12. Keep the normal model as default. Escalate to a more expensive model only
    for genuine unresolved technical uncertainty, not as compensation for weak
    orchestration.

### AGENTS.md / F008 implications

- F008's `one coherent outcome -> one ticket` rule remains appropriate. Do not
  create extra tickets merely because implementation is broad.
- AGENTS.md does not need to duplicate F009. At most add a concise persistent
  rule that an agent must not claim completion while required acceptance items
  remain unmapped or unresolved, and that implementation-pass artifacts must be
  updated consistently.
