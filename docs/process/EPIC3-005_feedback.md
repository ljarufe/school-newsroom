# EPIC3-005 Feedback

## Status

Closing Feedback Final

EPIC3-005 reached its stable implementation and operational review boundary.
The implementation was committed and pushed, Pull Request #14 was opened,
GitHub Actions passed, maintainer UAT passed under the project's
deviation-based reporting rule, and the Codex Pull Request review was
completed.

The review produced one keyboard-accessibility finding concerning forward and
reverse Tab traversal through visible `article_image` metadata fields. The
maintainer reviewed the finding and explicitly chose not to change the
implementation in this Pull Request. The limitation is documented below and
is handed off as follow-up work; it is not represented as fixed or as a false
positive.

This file replaces the earlier `Implementation Closing Draft`.

## Source and checkout

- Source of truth: the approved `EPIC3-005` ticket supplied directly by the
  maintainer.
- Working branch: `EPIC3-005-wagtail-writing-mode`.
- Published implementation commit:
  `aae79bff6231f30e1f28db44b89d622d1768cf46`.
- Pull Request:
  `https://github.com/ljarufe/school-newsroom/pull/14`.
- Runtime exercised during implementation: Wagtail 7.4.2 through the
  repository's Docker-first workflow.
- The implementation continued from an intentionally non-clean worktree.
  Existing valid summary-removal, migration, public/SEO, writing-mode, test,
  and documentation work was preserved.
- No spike patch was applied and no existing implementation was reset or
  recreated.

## Final architecture

`NewsPage.body` remains the original and only body `StreamField` and source of
truth. A field-specific `WritingModeFieldPanel` renders that original field
once inside a native Wagtail full-screen dialog. There is no copied body,
parallel editor state, hidden clone, or save-synchronization layer.

The normal `Edición de la noticia` surface retains a compact `Contenido` card
with `Sin contenido` or `Con contenido` and `Abrir modo redacción` or
`Revisar errores`. The dialog uses the visible labels `Modo redacción` and
`Volver`. The original Wagtail field and its native save behavior remain in the
same page-edit form.

The native contextual Draftail toolbar remains the only text-formatting
toolbar. No shared top toolbar, copied React control, or synthetic formatting
toolbar was introduced.

The implementation is scoped through the custom `NewsPage.body` panel template
and its `BoundPanel.Media`. Its CSS and JavaScript do not load on unrelated
Admin StreamFields.

The writing surface keeps separate `paragraph`, `article_image`, `youtube`, and
`spotify` blocks while presenting them as a compact continuous document.
Images retain the Wagtail chooser and the contextual `Pie de foto`,
`Texto alternativo`, and `Crédito de imagen` fields. The existing
caption-to-alt synchronization and manually customized-alt protection remain
unchanged.

## Summary removal and description policy

`NewsPage.summary` was removed from:

- the model and Admin editing surface;
- Home hero and secondary cards;
- shared news cards;
- `/noticias/` listing;
- article detail;
- Admin SEO read-only context;
- SEO live preview and analysis;
- Open Graph;
- Twitter/X;
- JSON-LD.

No replacement excerpt is synthesized from `NewsPage.body`.

`search_description` is the only public base-description source.
`og_description` may fall back only to that explicit field. When the explicit
description fields are empty, description metadata is omitted safely.

Migration `0010_remove_newspage_summary_and_more` depends on
`0009_reconcile_mvp_access` and contains only:

1. removal of `NewsPage.summary`;
2. the approved Spanish help-text adjustment for `og_description`.

No published migration was rewritten. Historical Wagtail revision JSON may
retain the obsolete `summary` key; current reconstruction ignores that key
while preserving the historical body content.

## Permissions, workflow, and privacy

No group, page, collection, task, workflow, moderation, publication, or
collection permission changed.

- The technical superuser and `Director/editor` retain the content surface.
- `Curador SEO` remains restricted to its authorized SEO surface and cannot
  bind body, privacy, contributor, menu, or publication fields.
- `Revisión editorial` behavior remains unchanged.

No internal minor contributor, age band, privacy flag, consent state, or
authorization state was added to the writing dialog, SEO context, preview, or
public output.

## Maintainer UAT

The maintainer completed the detailed visual and functional UAT using the
project's deviation-based reporting rule. All described areas were accepted
after the scoped visual corrections.

The maintainer also manually repeated the final focused delta-UAT for the
previously observed image-block traversal trap. The affected forward and
reverse sequence passed: focus could enter and leave the image block without
becoming stuck on a hidden chooser control. A complete UAT was not repeated
after that narrow correction because only the affected delta required
revalidation.

The later Pull Request review identified a narrower path that the UAT and
temporary browser evidence had not proved: normal Tab traversal from the
marked image chooser into each visible metadata input. That limitation is
recorded in the review section and must not be confused with the earlier hidden
chooser-control trap, which was fixed.

## Automated and focused validation

Immediate JavaScript syntax validation:

```text
node --check static/news/js/writing_mode.js
passed
```

Focused Admin test after the test-delta audit:

```text
apps/news/tests/test_admin_uat.py
10 passed in 5.12s
```

Focused disposable browser regression:

```text
1 passed in 13.34s
```

That probe proved:

- forward and reverse traversal through the primary paragraph, image,
  paragraph, YouTube, Spotify, and paragraph surfaces;
- rejection of the hidden Wagtail empty-state chooser button as a focus
  destination;
- absence of insertion controls and hidden block actions from the
  content-to-content sequence;
- image chooser opening, nested-dialog focus, `Escape`, parent-dialog
  persistence, and useful focus restoration;
- preservation of the approved CSS.

The Pull Request review subsequently narrowed the claim: the probe did not
prove that ordinary Tab from the selected image chooser enters the first
visible caption/alt/credit control before leaving the block.

Final local repository gate before the implementation commit:

```text
make check
ruff: All checks passed!
makemigrations --check: No changes detected
pytest: 202 passed in 33.18s
```

Whitespace validation:

```text
git diff --check
passed
```

GitHub Actions:

```text
Workflow: Pull Request Validation
Run: 29
Conclusion: success
```

No executable code changed after the Pull Request review. Therefore the
existing local and CI evidence was not invalidated and was not repeated by
ceremony.

## Test-delta audit

Only tests added or materially changed by EPIC3-005 were audited.

The retained tests protect distinct risks:

- removal of `summary` from the model and Admin;
- migration and historical-revision compatibility;
- absence of fabricated body excerpts in public rendering;
- explicit description omission and fallback behavior for SEO, Open Graph,
  Twitter/X, and JSON-LD;
- role, workflow, authorization, and minor-privacy boundaries;
- Admin panel configuration, Spanish labels, assets, and validation wiring.

Two brittle source-literal tests were consolidated out:

1. a writing-mode test that searched CSS and JavaScript implementation
   literals while claiming dynamic browser behavior;
2. a materially rewritten SEO-assistant test that searched JavaScript source
   strings for the removed `summary` dependency.

Their product risks remain covered by model, migration, rendered Admin, and
public metadata tests. No unrelated repository test was removed, and no
Python source-string test was added for the image keyboard behavior.

## Pull Request review and finding disposition

Codex reviewed implementation commit `aae79bff62` on Pull Request #14 and
reported one P1 finding in `static/news/js/writing_mode.js`:

> Let Tab enter the image metadata fields.

The finding established that:

- the image chooser is marked as the primary content traversal target;
- the next normal Tab is redirected directly to the following StreamField
  block;
- visible caption, alt-text, and credit inputs are therefore skipped by
  ordinary forward keyboard traversal;
- reverse traversal has the analogous limitation;
- keyboard-only editors cannot complete all image metadata through the normal
  Tab sequence.

Disposition:

- The maintainer reviewed the behavior and chose not to change the
  implementation in EPIC3-005.
- The finding is accepted as a known keyboard-accessibility limitation for
  this ticket.
- It is not classified as fixed, false positive, or fully covered by the
  earlier browser probe.
- The limitation must be considered by the ticket-definition chat and retained
  in the roadmap until it receives an explicit disposition.

No code, CSS, migration, test, permission, workflow, privacy, or public-output
delta was introduced after review.

## Files in the complete implementation delta

### Model, Admin, and migration

- `apps/news/models.py`
- `apps/news/panels.py`
- `apps/news/migrations/0010_remove_newspage_summary_and_more.py`
- `apps/news/templates/news/admin/writing_mode_field_panel.html`
- `static/news/css/writing_mode.css`
- `static/news/js/writing_mode.js`

### Public and SEO behavior

- `apps/news/seo.py`
- `apps/news/seo_metadata.py`
- `apps/news/templates/news/admin/news_seo_context_panel.html`
- `apps/news/templates/news/admin/seo_assistant_panel.html`
- `static/news/js/seo_assistant.js`
- `templates/home/home_page.html`
- `templates/includes/news_card.html`
- `templates/news/news_page.html`

### Tests and documentation

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

Temporary diff-review and browser-evidence artifacts under `tmp/` remain local
and untracked. They are not part of the Pull Request.

## Warnings and known limitations

### Accepted image metadata keyboard limitation

Normal Tab and Shift+Tab traversal does not enter all visible
`article_image` caption, alt-text, and credit controls from the marked chooser
stop. Pointer users and users who directly focus those controls can edit them,
but the ordinary keyboard-only path is incomplete.

Recommended follow-up acceptance boundary:

1. Tab from the preceding block reaches one meaningful image chooser stop.
2. The next Tab enters the first visible metadata control.
3. Caption, alt text, and credit follow their visible native order.
4. Tab after the final visible metadata control reaches the next block.
5. Shift+Tab traverses the same sequence in reverse.
6. Hidden, disabled, collapsed, and non-rendered chooser controls are skipped.
7. Nested chooser, `Escape`, dynamic block insertion, and focus restoration
   remain intact.
8. The transition is protected by a real browser regression at an appropriate
   tracked test boundary.

### Wagtail compatibility

Writing-mode selectors and focus behavior depend on Wagtail 7.4.2 panel,
StreamField, Telepath, Draftail, chooser, and native dialog markup. A future
major Wagtail upgrade should repeat focused browser regressions for:

- chosen and empty image chooser branches;
- content-first forward and reverse traversal;
- Telepath insertion overlays;
- nested dialog focus boundaries;
- Draftail contextual toolbar behavior;
- the scoped continuous-document presentation.

### Scope boundaries retained

No per-user preference, product-wide default, shared toolbar, parallel body
editor, permanent browser-test dependency, smart paste, automatic block
normalization, new block type, reusable block system, advanced authorship, SEO
v2, sharing, notifications, live coverage, advertising, workshops, or deploy
work was introduced.

## New Work Discovered

### Article-image metadata keyboard accessibility

Evidence:

- Codex Pull Request review on implementation commit `aae79bff62`;
- the normal Tab sequence skips visible caption, alt-text, and credit inputs.

Impact:

- incomplete keyboard-only authoring for a block whose caption and alt fields
  are required when an image is present;
- the temporary browser probe did not protect the exact transition that
  failed;
- further behavior-critical Wagtail Admin JavaScript would increase risk
  without an explicit browser-test strategy.

Suggested disposition:

- retain as high-priority accessibility debt;
- define a focused follow-up before broadening or reusing the writing mode;
- decide whether it belongs in a dedicated Admin accessibility ticket or in
  the existing Admin JS/browser-testing prerequisite;
- do not lose it inside a generic future Wagtail-upgrade task.

No other blocking new product work was discovered.

## Durable knowledge candidates

- `NewsPage.body` can be presented as a full-screen continuous writing surface
  through a field-specific `BoundPanel.Media` and native Wagtail dialog without
  creating a second body field or synchronization layer.
- Wagtail image choosers retain chosen and empty-state DOM branches. Focus
  destination logic must validate rendered state rather than trusting the first
  matching chooser action.
- `preventDefault()` in content-first Tab handling must occur only after a live
  destination has been resolved.
- A browser test that proves block-to-block traversal does not necessarily
  prove native traversal through every visible control inside a complex block.
  Coverage and claims must name the exact transition.
- Immutable Wagtail revision JSON may retain a removed concrete page-field key;
  current reconstruction can ignore the obsolete key while preserving
  historical body data.
- Public News description policy is explicit-field-only. Body content is not a
  card or metadata excerpt without a future approved product decision.
- Review comments displayed by a VS Code GitHub extension are not automatically
  available to an existing Codex session. The session must fetch the Pull
  Request threads or receive the comment explicitly.

## Operational publication state

- Implementation commit: published.
- Remote branch: published.
- Pull Request #14: open against `main`.
- Pull Request Validation run #29: passed.
- Codex Pull Request review: completed with one finding.
- Finding disposition: accepted known limitation; no code change requested by
  the maintainer.
- Final feedback replacement: ready for the final documentation-only commit.
- Final merge remains a maintainer action using `Squash and merge`.
