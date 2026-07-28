# EPIC3-006 Feedback

## Status

Implementation Closing Draft — Pull Request review follow-up.

The maintainer confirmed that the final UAT passed with no pending functional
or visual deviations. The implementation and its final visual corrections are
therefore approved for technical closing.

Pull Request #15 is open. Two non-blocking P2 review threads and one failing
browser-regression run were investigated and corrected locally. The follow-up
changes have not been committed or pushed, the review threads remain open, and
the updated GitHub Actions run, review completion, and merge remain pending.

## Root cause

The initial implementation treated structured paste as a separate import
workflow. It added a button, modal, review step, and explicit confirmation even
though the intended editorial interaction was a direct `Ctrl+V` inside
`NewsPage.body` while writing mode was active.

That extra workflow also obscured three UI defects visible in the first UAT:

- imported paragraph and heading boundaries retained Word-generated leading and
  trailing whitespace structures;
- writing-mode block selection and spacing were inconsistent across rich text,
  image, and table blocks;
- Wagtail's table controls remained permanently expanded, partially
  untranslated, and poorly spaced.

The corrections remove the workflow mismatch rather than layering another
fallback over it.

## Corrected behavior

### Direct structured paste

The button, modal, review summary, confirmation controls, modal-only styles,
listeners, copy, and browser assertions were removed. There is no alternative
button or confirmation path.

The writing-mode panel now installs one guarded paste listener for `body`.
Clipboard inspection happens synchronously from the paste event. Structured
paste is selected for multiple block-level elements, headings, lists, tables,
quotes, horizontal rules, or more than one non-empty plain-text line. A single
ordinary inline fragment remains a native Draftail paste, including a word,
phrase, URL, or inline bold/italic content.

Structured input is still sent through the authenticated, CSRF-protected
server-side normalizer. Raw clipboard HTML is never inserted directly.
Successful responses are inserted through Wagtail's StreamField client API and
produce a short Spanish live notification. A table-degradation warning is
summarized as `Una tabla fue simplificada.` Failures leave the existing body
unchanged and report a retry message.

Supported bold and italic styles declared directly on paragraph and heading
elements are applied to their normalized contents. Inline semantic elements
also honor explicit CSS overrides: `font-weight: normal` or a numeric weight
below 600 suppresses `<b>`/`<strong>` conversion, and `font-style: normal`
suppresses `<em>`/`<i>` conversion.

The listener does not intercept image inputs, captions, alternative text,
credits, other administrative inputs or selectors, table cells, or fields
outside `body`. Initialization, processing, event identity, and late-response
guards prevent one paste event from being inserted more than once.

Closing or reopening writing mode now invalidates the active request version.
Before insertion, the client also verifies the same StreamBlock controller,
ordered child-controller identities, and canonical form-backed values captured
when the request began. A response from an old writing-mode session, deleted or
reordered anchor, or incompatible body change is discarded without insertion,
rollback, or success notification. A fresh paste in the reopened session
continues normally.

Insertion follows the corrected contract:

- an empty body receives imported blocks from index zero;
- an active completely empty paragraph is replaced;
- an active populated or non-text block receives the import immediately after
  itself when the focus is not editing an internal field;
- an unresolved target appends safely.

Writing mode remains active throughout the operation.

### Boundary normalization

Paragraphs and headings now remove only fabricated boundary noise: whitespace
and non-breaking-space-only text, empty inline wrappers, leading or trailing
breaks, and empty Word auxiliary elements such as `o:p`. The recursive edge
walker also trims whitespace and non-breaking spaces from the outer edge of a
mixed text node that contains meaningful text, including when that text is
nested inside a supported inline wrapper.

The cleanup is structural and does not call an indiscriminate `strip()` on
serialized rich text. Interior manual breaks, significant spacing between
inline elements, bold, italic, links, and legitimate text remain intact.
Causal tests combine repeated `br` elements, `&nbsp;`, empty wrappers, and
interior formatting. Separate exact fixtures cover mixed leading paragraph
text, mixed text around interior strong markup, and a wrapped H3 while retaining
spaces between sibling wrappers and an interior manual break.

### Writing-mode presentation

The gap between a block and its following add control was reduced without
changing the control's clickable area. The selected state is now consistent
across paragraphs, H2/H3/H4 content, lists, quotes, separators, images, and
tables: a thin left line, no top, right, or bottom line, no outer rectangular
card border or shadow, no extra card background, and preserved keyboard focus
for internal controls.

Wagtail's StreamField panel pseudo-elements, nested-panel divider decoration,
and Draftail focus border were the overlapping sources of the horizontal
selection lines. Their writing-mode rules are now consolidated at the owning
panel and editor selectors, while buttons, fields, cells, and other internal
controls keep their own focus indication. Draftail's populated editor minimum
was reduced from 40 pixels to one line, while empty paragraphs retain a one-line
editable target.

Only one block owns the contextual toolbar at a time. Pointer and keyboard
ownership are synchronized, ownership is cleared when the interaction leaves
the block, and the toolbar moves inside the block when there is not enough room
above it. The icon controls use their inspected Wagtail actions for Spanish
accessible names and visible tooltips.

Image caption and credit presentation use Wagtail Admin's sans-serif family,
with their hierarchy retained by size and weight. This rule is scoped to the
article-image block in writing mode and does not affect public rendering or
other forms.

The table block follows contextual expansion in writing mode:

- an unselected valid table shows only its data grid;
- selecting the grid, a block control, or the block by keyboard reveals the
  title inside the selected block, the toolbar aligned to the right, the header
  selector, caption, help text, and the unchanged data grid;
- selecting another table contracts the previous table;
- an invalid table remains expanded so its error and affected control stay
  visible;
- hidden controls are inert and absent from the tab order;
- the first grid click remains available to Handsontable after expansion;
- hover does not select, expand, contract, or resize the table;
- saved and reopened visible grids are compacted from their rendered rows after
  layout, without measuring hidden ancestors or writing a height to the outer
  block.

Normal Wagtail editing mode is unchanged.

Collapsed contextual controls use `display: none`, so they reserve no space.
The selected table content has a small inset from the left selection line, and
table field width and spacing match the image-block form language without
altering Handsontable's cell focus, data, rows, or scrollbars.

### Table localization

Project-level Django translations now cover all visible contributed TableBlock
labels, help text, and selector options while preserving the underlying stored
values:

- `Encabezados de tabla`;
- `¿Qué celdas deben mostrarse como encabezados?`;
- `Descripción de la tabla`;
- the complete Spanish accessibility help text;
- `Sin encabezados`;
- the first-row, first-column, and combined header options.

The Spanish message catalog was compiled through the project Makefile. No
content migration or CSS text substitution was introduced.

### Imported tables and nested lists

The exact UAT production table is covered as a 4 by 4 matrix. Its existing first
row becomes the header, its caption remains empty, and no row, column, or cell
is shifted or fabricated.

Merged source cells are not made editable as merged cells. Rowspans and
colspans expand deterministically into a rectangular grid: source text occupies
the anchor cell and continuation positions are empty. This preserves column
positions and produces a non-blocking simplification warning.

Nested tables remain unsupported as nested grids. Their inner text is retained
inside the outer cell with readable separation and produces a non-blocking
warning.

Simple ordered and unordered lists remain supported. Nested lists are flattened
to one level in source order, retain their text, and report a warning instead of
claiming hierarchical preservation.

## Reference material

The original approved ticket, prior feedback, editorial guide, preliminary
implementation material, first-UAT screenshots, and consolidated correction
instructions were used as requirements.

The comprehensive UAT DOCX at
`/home/ljarufe/Downloads/EPIC3-006_UAT_pegado_inteligente_completo.docx` was
inspected read-only as editorial reference. It was not copied into the
repository, parsed in production, or treated as proof of the exact clipboard
HTML emitted by Microsoft Word.

## Files changed

### Application, Admin, and localization

- `apps/news/blocks.py`
- `apps/news/models.py`
- `apps/news/panels.py`
- `apps/news/smart_paste.py`
- `apps/news/views.py`
- `apps/news/wagtail_hooks.py`
- `apps/news/migrations/0011_alter_newspage_body.py`
- `apps/news/templates/news/admin/writing_mode_field_panel.html`
- `config/settings/base.py`
- `locale/es/LC_MESSAGES/django.po`
- `locale/es/LC_MESSAGES/django.mo`
- `static/news/css/writing_mode.css`
- `static/news/js/smart_paste.js`
- `static/news/js/writing_mode.js`
- `static/public/css/site.css`

The preliminary untracked modal-only stylesheet
`static/news/css/smart_paste.css` was removed.

### Browser infrastructure

- `.github/workflows/browser-regression.yml`
- `.dockerignore`
- `.gitignore`
- `Makefile`
- `apps/news/management/commands/setup_browser_test.py`
- `config/settings/browser_test.py`
- `docker-compose.browser.yml`
- `docker/browser/Dockerfile`
- `package.json`
- `package-lock.json`
- `playwright.config.js`
- `tests/browser/smart-paste.spec.js`

### Tests and documentation

- `apps/news/tests/test_admin_uat.py`
- `apps/news/tests/test_blocks.py`
- `apps/news/tests/test_language.py`
- `apps/news/tests/test_migrations.py`
- `apps/news/tests/test_mvp_access.py`
- `apps/news/tests/test_public_rendering.py`
- `apps/news/tests/test_smart_paste.py`
- `docs/editorial/guia_de_uso.md`
- `docs/process/EPIC3-006_feedback.md`

The generated `tmp/EPIC3-006_diff_review.txt` is a local review artifact and
must not be staged or committed.

## Automated validation

### Focused smart-paste coverage

```text
apps/news/tests/test_smart_paste.py
38 passed in 4.57s
```

The two added cases cover supported styles declared on block elements and
normal-weight overrides on semantic bold elements.

### Browser regression

The Pull Request follow-up browser regression passed locally:

```text
make browser-test
1 passed (3.8s)
total command duration: 25.53s
passed; disposable services and volumes removed
```

The scenario covers structured and native paste boundaries, stale-response
discard, all insertion positions, endpoint failure without content loss,
contextual tables, Spanish controls, left-only block selection, table spacing,
narrow viewport geometry, save/reopen persistence, and retained table data.

### Repository gate

```text
make check
ruff: All checks passed!
makemigrations --check --skip-checks: No changes detected
pytest: 276 passed in 32.35s
```

### JavaScript and browser Compose configuration

```text
node --check static/news/js/writing_mode.js
node --check playwright.config.js
node --check static/news/js/smart_paste.js
node --check tests/browser/smart-paste.spec.js
all passed in the project browser container; 0.86s

docker compose -f docker-compose.browser.yml config --quiet
passed; under 0.1s
```

The localization catalog did not change after its previous successful
compilation, so `make compilemessages` was not repeated.

```text
git diff --check
passed after the final feedback update; under 0.1s
```

## Validation failures and retries

- GitHub Actions Browser Regression run `30403272783` failed while comparing
  the stale-response snapshot. On the slower hosted runner, the snapshot was
  captured immediately after StreamField `setState()` restored the blocks but
  before three non-empty Draftail controllers synchronized their hidden form
  values. The expected state therefore contained `"null"` strings while the
  later state contained equivalent Draftail JSON. The browser test now waits
  for those known non-empty form values before capturing the unchanged-state
  snapshot; the complete comparison remains in place and the same regression
  passes locally.
- The first closing `make browser-test` attempt failed because its narrow-table
  assertion compared a contextual control with the outer selected block. The
  approved visual delta added a 0.75-rem content inset, so the assertion was
  corrected to use the selected panel content box. The failed command took
  25.73 seconds.
- The second attempt exposed an intermittent test-only race after reopening the
  writing-mode dialog: visibility could resolve before the application handled
  `w-dialog:shown`, allowing the synthetic paste to begin during request-version
  invalidation. The test now waits for the launcher's application-owned
  `aria-expanded="true"` state and the next animation frame. The attempt took
  approximately 30 seconds.
- The third attempt reached the corrected narrow-table assertion and showed the
  native field chrome consumed 12 pixels rather than the old 8-pixel allowance.
  The assertion now uses a 16-pixel tolerance while still requiring the control
  to remain inside and fill the approved content area. The failed command took
  25.43 seconds.
- A host invocation of `node --check` did not inspect any file because `asdf`
  has no Node version configured for this checkout. The same four commands were
  rerun successfully in the repository's browser-test container.

The Pull Request follow-up changes preserve supported formatting more
accurately and stabilize only the precondition for the browser snapshot. They
do not invalidate any part of the approved UAT.

## Manual validation

The maintainer confirmed that the final UAT passed without pending deviations.
This approval covers the functional smart-paste behavior and the final visual
corrections for single-toolbar ownership and placement, accessible tooltips,
image caption and credit typography, left-only block selection, visible table
grids, selected-table header and controls, table spacing, and non-selecting
hover behavior.

## Deferred validation

- Commit and push of the Pull Request review follow-up.
- GitHub Actions rerun on the updated Pull Request head.
- Review-thread replies or resolution.
- Review completion and merge.

## Persistent database state

No migration, fake migration, or reversal command targeted the persistent
Compose database during closing. Disposable Django test databases and the
isolated browser Compose project were the only databases initialized by the
requested validations.

A read-only `showmigrations news` query confirmed
`news.0011_alter_newspage_body` remains applied in the persistent
`school_newsroom` database. `make check` also reported no model changes
requiring a migration.

## Warnings and known limitations

- Merged tables, nested tables, and nested list hierarchy intentionally degrade
  as documented above.
- Django/Wagtail continues to emit five pre-existing Treebeard `E001` warnings
  during migration and browser startup.
- The Admin JavaScript boundary is tied to the inspected Wagtail 7.4 StreamField
  and TableBlock controller behavior and must be rerun after a Wagtail upgrade.
- The isolated browser path performs fresh migrations on each run and can incur
  a large cold Playwright image download.

## New Work Discovered

- Investigate the existing Treebeard `E001` warnings before upgrading to
  Treebeard 6.
