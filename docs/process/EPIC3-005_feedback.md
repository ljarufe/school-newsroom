# EPIC3-005 Feedback

## Status

Implementation Closing Draft

The implementation, automated technical close, and focused browser regression
are complete. The maintainer reported that the detailed visual and functional
UAT passed except for one `article_image` Tab-traversal defect. That deviation
is fixed and has focused real-browser evidence. The maintainer has not manually
repeated the complete UAT after this narrow correction.

Real commit, push, pull request, CI, and review evidence remain pending. This
document is therefore not Stage B closing feedback.

## Source and checkout

- Final source of truth: the approved `EPIC3-005` ticket supplied directly by
  the maintainer.
- Active branch: `EPIC3-005-wagtail-writing-mode`.
- This was a continuation of an intentionally dirty worktree. Existing valid
  summary-removal, migration, public/SEO, writing-mode, test, and documentation
  work was preserved.
- No spike patch was applied and no existing work was reset or reimplemented.
- Runtime exercised: Wagtail 7.4.2 through the repository's Docker-first test
  workflow.

## Final architecture

`NewsPage.body` remains the original and only `StreamField` instance and source
of truth. A field-specific `WritingModeFieldPanel` renders that original field
once inside a native Wagtail full-screen dialog. There is no copied body,
parallel editor state, hidden clone, or save-synchronization layer.

The normal `Edición de la noticia` surface retains a compact `Contenido` card
with `Sin contenido` or `Con contenido` and `Abrir modo redacción` or
`Revisar errores`. The dialog uses the exact labels `Modo redacción` and
`Volver`. Normal Wagtail editing remains available outside the writing dialog.

The native contextual Draftail toolbar remains the only text-formatting
toolbar. No shared top toolbar or synthetic formatting controls were added.
The CSS and JavaScript are loaded only by the custom `NewsPage.body` panel, so
unrelated Admin StreamFields are not affected.

The approved continuous-document presentation keeps separate paragraph,
`article_image`, YouTube, and Spotify blocks while reducing persistent panel
chrome. Images keep their chooser and editable caption, alt, and credit fields;
inactive images retain a compact figure-like presentation. YouTube and Spotify
retain compact provider-and-URL cards. The existing
`caption_alt_sync.js` integration and customized-alt protection are unchanged.

## Maintainer UAT state

Under the project's deviation-based UAT rule, the maintainer approved the
current visual presentation and every previously described UAT item except the
image traversal deviation below. The approved CSS was not changed during the
closing correction.

The maintainer did not manually repeat the full visual and functional UAT after
the narrow JavaScript correction. The correction instead received the focused
browser regression described below. A maintainer may optionally smoke-test the
corrected Tab sequence before staging; a new full UAT pass is not represented
as having occurred.

## Image Tab-traversal defect and correction

### Observed defect

Content-first `Tab` worked between text blocks but became stuck when traversal
reached an `article_image`.

### Root cause

The image target lookup accepted chooser actions without checking whether they
were rendered. For a chosen image, Wagtail keeps an empty-state
`chooser__choose-button` in a hidden `.unchosen` branch while rendering the
actual chosen-image dropdown toggle. The hidden button appeared earlier in the
DOM, so it was selected as the destination. The handler had already called
`preventDefault()` before trying to focus it; the hidden control could not
receive focus, leaving focus on the previous paragraph and creating the
apparent trap.

### Implemented correction

`static/news/js/writing_mode.js` now:

- accepts an image traversal target only when it is enabled, not hidden or
  `aria-hidden`, has a non-negative tab index, has rendered client rectangles,
  and is not CSS-hidden;
- resolves the meaningful image stop inside the actual image field, marking
  the current rendered chooser control for content traversal;
- refreshes that marker when Wagtail changes image chooser markup, preserving
  dynamically inserted, duplicated, deleted, and reordered blocks;
- supports forward and reverse traversal through paragraph, image, paragraph,
  YouTube, Spotify, and paragraph primary surfaces;
- preserves native ordering within visible image metadata fields and moves to
  the following block only after the final visible metadata control;
- leaves Tab events outside marked primary controls and the final visible image
  metadata control untouched, including chooser dialogs, Draftail chrome,
  menus, and popovers;
- calls `preventDefault()` only after both a live destination block and a valid
  destination control have been resolved.

No CSS, template, Python, migration, public, SEO, permission, workflow, or
privacy implementation changed for this correction.

## Focused real-browser regression

A disposable Chrome 123 session, Django live server, isolated test database,
fictional superuser, fictional article, and fictional one-pixel image exercised
the exact sequence:

```text
Párrafo → Imagen → Párrafo → YouTube → Spotify → Párrafo
```

The focused browser test passed:

```text
1 passed in 13.34s
```

Evidence confirms:

- forward `Tab` visited all six primary surfaces in the expected order;
- reverse `Shift+Tab` visited the same sequence in reverse;
- the selected image target was the rendered chosen-image dropdown toggle, not
  the hidden empty-state choose button;
- no insertion control, block action, or hidden image field entered the
  content-to-content sequence;
- visible image metadata followed `Pie de foto` → `Texto alternativo` →
  `Crédito de imagen`, then exited to the following paragraph;
- opening the real image chooser placed focus inside the nested modal;
- `Escape` closed only the nested chooser, kept `Modo redacción` open, and
  restored useful focus inside the image block;
- the approved `writing_mode.css` remained unchanged, recorded with SHA-256
  `c1d6cb243ee0b9541378f6c7f2e8f086dee2dfeb399f3efbea6a7f99dc36c7bf`.

Retained untracked evidence:

- `tmp/EPIC3-005-image-tab-regression/pre-fix-dom.json`;
- `tmp/EPIC3-005-image-tab-regression/focused-browser-evidence.json`;
- `tmp/EPIC3-005-image-tab-regression/focused-image-tab.png`.

The disposable browser harness was removed after the successful run. No
permanent browser dependency or source-string pseudo-browser test was added.

## Test-delta audit

Only tests added or materially changed by EPIC3-005 were audited.

- Summary removal and model/Admin absence are protected by language,
  form-surface, and role-surface tests.
- Migration and history compatibility are protected by the migration
  regression that crosses `0009` to `0010`, verifies the live column removal,
  preserves immutable revision JSON, and reconstructs the historical page and
  original body blocks.
- The prohibition on fabricated body excerpts is protected by Home, card, list,
  detail, and metadata output assertions.
- SEO, Open Graph, Twitter/X, and JSON-LD omission and explicit-field fallback
  rules are protected by public response tests.
- Permissions, workflow, and minor-privacy boundaries are protected by the
  existing role-specific Admin and manipulated-POST tests.
- Admin panel order, field absence, writing-mode asset wiring, Spanish labels,
  and nested validation rendering are protected through actual Django/Wagtail
  configuration or rendered HTML.

Two brittle tests were consolidated out:

1. a writing-mode test that searched many CSS and JavaScript implementation
   literals while claiming dynamic and browser behavior;
2. a materially rewritten SEO-assistant test that searched JavaScript source
   strings for the removed `summary` dependency.

Their distinct product risks remain covered by rendered Admin, model,
migration, and public metadata tests. No existing unrelated repository test was
removed, and no Python test was added for the image JavaScript source.

The affected test file passed before the general gate:

```text
apps/news/tests/test_admin_uat.py
10 passed in 5.12s
```

## Summary removal, migration, public output, and SEO

`NewsPage.summary` is absent from the model and Admin. Home hero, shared cards,
listing, detail, Admin SEO context, SEO live preview, Open Graph, Twitter/X,
and JSON-LD no longer depend on it. No replacement is synthesized from
`NewsPage.body`.

`search_description` is the only public base description source.
`og_description` may fall back only to that explicit field. When neither is
available, description metadata is omitted safely. Explicit SEO title, social
title, canonical, robots, image, sitemap, and public-credit behavior remain.

Migration `0010_remove_newspage_summary_and_more` depends on
`0009_reconcile_mvp_access` and contains only:

1. `RemoveField` for `NewsPage.summary`;
2. `AlterField` for the Spanish `og_description` help text.

No published migration was rewritten. The `paragraph` block identity and the
single original body `StreamField` remain unchanged. Historical revision JSON
may retain its old `summary` key; Wagtail reconstructs the current model while
ignoring that obsolete key. No migration was applied to the maintainer's
persistent database.

## Permissions, workflow, and privacy

No group, page, collection, task, workflow, moderation, or publication
permission changed. The technical superuser and `Director/editor` retain the
content surface. `Curador SEO` remains limited to its authorized SEO surface
and cannot bind body, privacy, contributor, menu, or publication fields.
`Revisión editorial` behavior is unchanged.

No internal minor contributor, age band, privacy flag, consent state, or
authorization state was introduced into the writing dialog or public output.

## Automated validation

Immediate JavaScript syntax:

```text
node --check static/news/js/writing_mode.js
passed
```

Focused test after the test-delta consolidation:

```text
10 passed in 5.12s
```

Final repository gate:

```text
make check
ruff: All checks passed!
makemigrations --check: No changes detected
pytest: 202 passed in 33.18s
```

Final whitespace validation:

```text
git diff --check
passed
```

## Post-UAT delta review

The post-UAT template, CSS, and JavaScript delta was reviewed against the
approved scope.

- The writing panel template is unchanged by the final correction.
- The visual UAT refinements in `writing_mode.css` remain scoped to the writing
  dialog and were not altered during closure.
- The only production change in the final correction is the image-aware
  traversal logic in `writing_mode.js`.
- No actionable regression, broad selector leak, duplicate body field, hidden
  focus destination, permission change, or privacy exposure was found.

`tmp/EPIC3-005_diff_review.txt` is regenerated after all repository changes and
contains the active branch, status, statistics, changed-file lists, complete
tracked unstaged diff, staged state, and complete relevant untracked ticket
files. Temporary browser and spike evidence is excluded from that review
artifact and remains untracked.

## Files in the complete ticket delta

Model, Admin, and migration:

- `apps/news/models.py`
- `apps/news/panels.py`
- `apps/news/migrations/0010_remove_newspage_summary_and_more.py`
- `apps/news/templates/news/admin/writing_mode_field_panel.html`
- `static/news/css/writing_mode.css`
- `static/news/js/writing_mode.js`

Public and SEO behavior:

- `apps/news/seo.py`
- `apps/news/seo_metadata.py`
- `apps/news/templates/news/admin/news_seo_context_panel.html`
- `apps/news/templates/news/admin/seo_assistant_panel.html`
- `static/news/js/seo_assistant.js`
- `templates/home/home_page.html`
- `templates/includes/news_card.html`
- `templates/news/news_page.html`

Tests and documentation:

- `apps/news/tests/test_admin_uat.py`
- `apps/news/tests/test_forms.py`
- `apps/news/tests/test_language.py`
- `apps/news/tests/test_migrations.py`
- `apps/news/tests/test_models.py`
- `apps/news/tests/test_mvp_access.py`
- `apps/news/tests/test_public_rendering.py`
- `apps/news/tests/test_seo.py`
- `apps/news/tests/test_seo_public.py`
- `docs/editorial/guia_de_uso.md`
- `docs/operations/wagtail_access_mvp.md`
- `docs/product/UX-001_public_site_design_handoff_guide.md`
- `docs/process/EPIC3-005_feedback.md`

## Warnings and limitations

- The maintainer did not repeat the complete UAT after the narrow image
  traversal correction. The exact corrected sequence has focused automated
  browser evidence.
- The final browser probe activated the visible Wagtail chooser menu action in
  page after a raw WebDriver element click reported that overlay element as not
  interactable. The chooser, focus placement, real `Escape` key handling, modal
  closure, parent-dialog persistence, and focus restoration were then observed
  in Chrome.
- Writing-mode selectors and focus behavior depend on Wagtail 7.4.2 markup and
  supported dialog behavior. A future major Wagtail upgrade should repeat these
  browser regressions.
- No user preference, product-wide default, shared toolbar, alternate body
  editor, or permanent browser-test dependency was added.

## New Work Discovered

No blocking new product work was discovered.

A future Wagtail upgrade should include browser regressions for:

- chosen and empty image chooser markup;
- content-first forward and reverse traversal;
- Telepath insertion overlays and nested dialog focus boundaries;
- Draftail contextual toolbar behavior;
- the scoped continuous-document panel selectors.

This is upgrade-compatibility work, not unfinished EPIC3-005 scope. Smart
paste, new block types, reusable blocks, taxonomy, advanced authorship, SEO v2,
sharing, notifications, live coverage, advertising, workshops, and deployment
remain out of scope.

## Durable knowledge candidates

- Wagtail image choosers retain both chosen and empty-state DOM branches.
  Keyboard destination logic must validate rendered state instead of trusting
  the first matching chooser action.
- `preventDefault()` for content-first Tab traversal must occur only after a
  live destination and focusable rendered control are resolved.
- A field-specific `BoundPanel.Media` plus native `{% dialog %}` is a narrow
  supported boundary for a full-screen authoring surface around one original
  Wagtail field.
- Immutable revision JSON can retain removed page-field keys. Current Wagtail
  reconstruction ignores the obsolete key while preserving historical body
  data.
- Public News description policy is explicit-field-only; body content is not a
  card or metadata excerpt without a future approved product change.

## Publication state

- Pending real commit.
- Pending real push.
- Pending PR/CI evidence.
- Pending PR review.
- No files are staged.
- No commit, push, pull request, or merge was performed by Codex.
