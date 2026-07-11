# EPIC3-003 Implementation Closing Draft

## Status

Implementation Closing Draft. Maintainer delta browser UAT is complete. Commit,
push, pull request, review, CI, merge, and post-merge evidence do not exist and
remain maintainer-owned.

## Checkout Evidence

- Branch before editing: `EPIC3-003-structured-news-body-media`.
- The branch matches EPIC3-003.
- The checkout was already dirty with the in-progress EPIC3-003 implementation.
- Untracked `tmp/` review notes were treated as unrelated and left untouched.

## Final Product Implementation

`NewsPage.body` remains `StreamField(use_json_field=True)` and now exposes these
children in this exact order:

1. `paragraph`
2. `article_image`
3. `youtube`
4. `spotify`

`paragraph` keeps its internal name and uses native Wagtail `RichTextBlock`
behavior. Its explicit visible features are `bold`, `italic`, `link`, `h2`,
`h3`, `h4`, `ol`, `ul`, `blockquote`, `hr`, and `document-link`. Rich-text
`image`, generic `embed`, and arbitrary HTML are not enabled.

The separate `heading` / `Subtítulo` authoring block was removed. Editors create
H2, H3, and H4 structure inside a paragraph. Structured `article_image`,
`youtube`, and `spotify` remain because they enforce actual product policy:
per-use image metadata and validation, and provider-specific URL restrictions
and public fallbacks.

The existing article-image caption-to-alt JavaScript remains. It initializes
existing and dynamically inserted blocks, seeds an empty alt value from the
caption, and stops synchronization after manual alt customization without
persisting a synchronization flag.

The YouTube and Spotify blocks retain block-boundary provider/path validation,
original URL storage, provider-labelled fallback links after controlled embed
unavailability, and propagation of unexpected rendering exceptions.

## Product Decision Correction And Removed Compatibility Work

The approved ticket originally encoded a six-feature paragraph restriction and
a separate heading block. The product owner's underlying preference was a simple
editor, not a confirmed prohibition of useful native Wagtail features. Browser
UAT exposed that mismatch: the contextual toolbar, pin behavior, and `/` command
surface were useful once explained. The pre-existing Wagtail default feature
inventory should have been shown before the restriction was hardened.

The custom paragraph compatibility path went through several corrections while
trying to preserve historical features behind the six-feature UI:

- raw migration JSON preservation was initially mistaken for editor round-trip
  compatibility;
- a custom converter then preserved historical HTML but did not by itself prove
  Draftail runtime entity support;
- hidden value-aware block/entity options were added for existing content;
- paste filtering, split-block EditorState initial values, and Draft.js 0.10.5's
  legacy global entity storage each exposed additional framework boundaries;
- hidden heading and horizontal-rule support was added after the adjacent paste
  state was audited;
- browser UAT still observed React failures for synthetic historical IMAGE and
  EMBED states, while Wagtail's EditorFallback preserved the last saved field
  value.

The product owner confirmed that the IMAGE/EMBED fixtures were synthetic and no
real production or historical paragraph data requires that compatibility path.
The final decision enables native H2/H3/H4/HR/document-link authoring and removes
the custom converter, widget, Telepath adapter, value-aware detection/runtime
options, EditorState normalization, and
`static/news/js/legacy_paragraph_draftail.js` instead of patching the shim again.

Migration `0004` serializes the import path
`apps.news.blocks.ParagraphBlock`. Django must resolve that path while loading
the already-applied migration graph, so the name remains only as an alias to
Wagtail's native `RichTextBlock`. It is not a subclass and carries no custom
editor behavior, media, converter, or adapter. The runtime model directly uses
`blocks.RichTextBlock`.

## Heading Data Migration

New migration `news.0005_alter_newspage_body` runs operations in this order:

1. Iterate the historical `NewsPage` model under the `0004` field state.
2. Convert each raw `heading` item to `paragraph` with an H2 rich-text value.
3. HTML-escape the original CharBlock text before interpolation.
4. Preserve list order, the existing item dictionary, and its `id` where
   present; leave every non-heading item unchanged.
5. Alter the field state to remove `heading` and apply the final paragraph
   feature list and child order.

The reverse operation is intentionally a no-op. A safe reverse migration cannot
distinguish an editor-authored H2 paragraph from a migrated heading without
adding persistent markers or transforming unrelated content. No image, embed,
document, contributor, credit, or privacy metadata is fabricated.

Automated migration evidence compares normalized `StreamValue.raw_data` at
`0004` and `0005`, including escaped heading text, stable item ID and ordering,
an unchanged paragraph item, and the final migration-state block configuration.

## Admin And Validation Behavior

A supported Wagtail `HelpPanel` immediately precedes `Contenido` with concise
Spanish instructions for revealing and pinning the formatting toolbar, using
`/` for block actions, and Markdown-like writing shortcuts. It contains no
framework implementation terminology and adds no custom JavaScript.

The public-credit `InlinePanel` has supported Spanish help text explaining that
a credit is optional while drafting and required for publication. The existing
publication guard is unchanged; no normal required marker was added.

`NewsPageAdminForm.add_error()` recognizes only a body
`StreamBlockValidationError` and changes that object's summary message to
`Revisa los bloques marcados con errores.` before delegating to Django. The same
special error object and its `block_errors` remain intact, so article-image
`image`, `caption`, and `alt_text` details continue to reach the StreamField UI.
This is neither a global Wagtail patch nor a CSS/template replacement.

Real UAT identified both the technical `Validation error in StreamBlock` summary
and the poor discoverability of the publication-credit requirement. Those
findings are corrected here.

## Editor Guide

`docs/editorial/guia_de_uso.md` now describes the final UI in Spanish:

- one paragraph block may contain multiple paragraphs and H2/H3/H4 structure;
- selecting text reveals the contextual toolbar, the pin keeps it visible, and
  Wagtail remembers that browser preference;
- `/` opens the command/action surface, including `Split block` where available;
- the editor supports verified Markdown-like shortcuts but is not general
  Markdown;
- all enabled rich-text features are listed;
- images use the structured block for required caption/contextual alt and
  optional credit, including the caption-to-alt drafting behavior;
- YouTube and Spotify use explicit provider blocks, not generic embeds;
- public credit is optional in drafts and required before publication;
- the page-level content error directs editors to marked blocks with details.

The shortcut table is based on the installed Draftail 2.0.1 bundle's block,
inline-style, and horizontal-rule input maps: `## `, `### `, `#### `, `* `,
`- `, `1. `, `> `, `---`, paired `**` / `__`, and paired `*` / `_`.

## Automated Validation

Current evidence during this refactor:

- Affected focused suite, first run: 49 passed and 11 failed.
  - Classification: all failures shared one test-fixture root cause. The fixture
    changed from `CharBlock` to native rich text but posted database HTML where
    Draftail's form boundary requires serialized ContentState JSON.
  - Correction: the shared form fixture now posts a minimal fictional
    ContentState value.
- Focused form suite after correction: 13 passed.
- Full affected focused suite after correction: 60 passed.
- `make check`: passed.
  - Ruff: passed.
  - Migration drift (`makemigrations --check --skip-checks`): no changes
    detected.
  - Full pytest suite: 91 passed.
- `git diff --check`: passed with no output.

Focused coverage includes final native paragraph features and widget options,
absence of the legacy adapter/script/helpers, article-image validation and
deferred drafts, caption-to-alt media registration, malformed same-provider
URLs, provider fallbacks, unexpected render exceptions, Spanish admin help,
public-credit publication behavior, body summary plus nested error objects,
migration conversion, H2 rendering, body order, and public privacy boundaries.

## Manual Validation

Previously reported maintainer UAT remains accepted for behavior not invalidated
by this refactor: multiple paragraphs, contextual/pinned toolbar behavior,
caption-to-alt synchronization and manual override, detailed image child errors,
image field order, `/` command surface and split action, and previously exercised
media/public rendering paths.

No new browser UAT was performed by the implementation agent.

The maintainer completed the requested delta browser UAT and all cases passed:

- `make migrate` successfully applied `news.0005_alter_newspage_body`.
- The Spanish `Cómo editar el contenido` help appears before `Contenido`.
- Final paragraph authoring controls include bold, italic, link, H2, H3, H4,
  ordered list, unordered list, blockquote, horizontal rule, and document link.
- Rich-text image, generic embed, and the separate `Subtítulo` StreamField block
  are absent.
- The body chooser contains only `Párrafo`, `Imagen`, `Video de YouTube`, and
  `Audio o pódcast de Spotify`.
- Full validation shows
  `Contenido: Revisa los bloques marcados con errores.` and no longer exposes
  `Validation error in StreamBlock`.
- The structured image block still shows its specific Spanish nested errors.
- The public-credit help is visible.
- A draft remains saveable without a public credit.
- Publication without an effective public credit remains blocked.
- Existing `Subtítulo` content migrated to H2 inside a paragraph in the same
  body position without disturbing surrounding blocks.

No maintainer browser UAT remains pending for EPIC3-003. The full original
EPIC3-003 UAT did not need to be repeated.

## Delivery Evidence Pending

The following evidence does not exist yet and remains pending:

- real commit / pre-commit evidence;
- real push / pre-push evidence;
- Pull Request and CI evidence;
- PR review evidence;
- merge and post-merge evidence.

## Failed Attempts And Root Causes

- Early provider fallback code caught broad `Exception` around embed rendering.
  Wagtail's frontend embed path already converts `EmbedException` to empty HTML.
  The catch was removed so controlled unavailability triggers fallback and
  unexpected exceptions propagate.
- Python-only rich-text round trips were initially overclaimed as browser
  compatibility. Draftail runtime entity registration, paste filtering, and
  EditorState split values were separate boundaries; the resulting shim was
  repeatedly corrected before the product restriction was revised.
- Initial Wagtail panel/plugin inspection omitted `django.setup()` and failed
  with `AppRegistryNotReady`. Re-running the same read-only probes after loading
  Django confirmed the 7.4.2 signatures and plugin options.
- Removing `ParagraphBlock` entirely made migration generation fail because
  already-applied `0004` serialized that import path. A native-class alias is
  retained solely for migration graph loadability.
- The first affected suite after the refactor posted HTML to a Draftail form
  widget and produced 11 JSON decode failures. The shared fixture was corrected
  to the real ContentState submission boundary; no runtime workaround was added.

## Warnings And Deferred Validation

- Django system checks emit existing Treebeard 6 manager warnings from Wagtail
  internals during migration commands. No EPIC3-003 project code path caused
  them.
- Live provider availability is not part of automated validation; embed tests
  use fictional cached values or controlled failures.

## New Work Discovered

### Contributor/group/chooser model depth

- Finding: internal contributor and group models still do not represent roles,
  responsibilities, cohorts, photographer attribution, or reusable public
  profiles.
- Evidence: `ContributorGroup`, `MinorContributor`, `NewsPageContributor`, and
  `NewsPagePublicCredit` remain deliberately minimal.
- Impact: richer attribution and contributor chooser workflows remain absent.
- Recommended disposition: merge with the accumulating EPIC3-CONTRIB candidate;
  do not implement in EPIC3-003.

### Featured image metadata

- Finding: `featured_image` still has no per-use caption, contextual alt
  override, or credit.
- Evidence: the field remains the existing Wagtail image foreign key, while body
  images use `ArticleImageBlock`.
- Impact: featured-image accessibility/credit policy differs from body images.
- Recommended disposition: evaluate in a future media metadata/accessibility
  ticket; keep featured-image policy unchanged here.

### Caption versus alt editorial training

- Finding: caption seeding accelerates drafting, but caption and contextual alt
  remain different editorial concepts.
- Evidence: separate values are persisted and synchronization stops after manual
  alt customization.
- Impact: editors need examples of useful alt text when the caption is not an
  adequate description.
- Recommended disposition: add editorial training/examples later; do not add
  automatic semantic rewriting.

### Conservative provider URL coverage

- Finding: YouTube and Spotify URL patterns intentionally cover a conservative
  set of known hosts and paths.
- Evidence: provider block URL parsers reject wrong providers and supported path
  shapes without effective IDs.
- Impact: legitimate new provider URL variants may require later support.
- Recommended disposition: collect real editorial examples before expanding
  allowlists.

### Integrate the editorial guide inside Wagtail Admin

- Finding: editors currently rely on the repository guide plus short contextual
  help; there is no complete protected guide inside Admin.
- Evidence: UAT established value in contextual instruction, while this ticket
  explicitly defers an Admin guide surface.
- Impact: discoverability may remain fragmented as the MVP grows.
- Recommended disposition: near MVP completion, evaluate one canonical source,
  a protected Admin help view, Help menu entry, optional Admin homepage panel,
  and deep links from relevant editor surfaces. Do not duplicate guide HTML or
  implement these surfaces in EPIC3-003.

## Durable Source And Process Knowledge Candidates

1. A product-owner preference such as "minimal", "simple", or "prefer" must not
   automatically become a hard acceptance prohibition. Present native capability
   delta, restriction cost, compatibility implications, and bypasses before
   requesting explicit confirmation.
2. For a new library that materially affects frontend, Wagtail Admin, or visual
   behavior, provide official documentation and an official demo, Storybook,
   playground, or useful visual examples when available. Pair that preview with
   a native-capability inventory and explicit enable/disable decisions.
3. Before creating a framework adapter or shim, present the native alternative
   and the demonstrated product requirement that prevents using it.
4. A material framework-boundary misunderstanding must trigger a consolidated
   adjacent-state audit before another correction is issued.
5. Tests and feedback must not claim runtime behavior beyond the boundary
   actually executed. Source/configuration assertions prove wiring only.
6. Framework subclass/adapter work must inspect the base implementation, exact
   signature, accepted input shapes, and material call sites first.
7. When a prerequisite command has an already-known next workflow, deliver both
   in the same instruction block. A failure interrupts the flow; routine output
   should not become an unnecessary checkpoint.
8. When UAT requires a technical fixture outside normal workflows, explain the
   real state simulated, why the UI cannot create it, the risk validated, and
   that it is local/test-only.
9. UAT instructions for contextual framework UI must state the exact revealing
   gesture, such as selecting text or typing `/`.
10. The real React/Draftail crash after repeated source-only uncertainty is
    sufficient evidence that another behavior-critical Wagtail Admin
    JavaScript/Telepath/Draftail customization should first define a lightweight
    executable JavaScript/browser testing strategy.
11. Historical migration files may serialize project block class paths. Removing
    runtime custom behavior can still require a non-behavioral import alias so
    Django can load the migration graph.
12. Wagtail `StreamBlockValidationError.message` can be specialized at a page
    form's `add_error` boundary without replacing the object or losing nested
    `block_errors` JSON.

## Final Git Status

```text
 M apps/news/forms.py
 M apps/news/models.py
 M apps/news/tests/test_forms.py
 M apps/news/tests/test_language.py
 M apps/news/tests/test_migrations.py
 M apps/news/tests/test_models.py
 M apps/news/tests/test_public_rendering.py
 M docs/editorial/guia_de_uso.md
?? apps/news/blocks.py
?? apps/news/migrations/0004_alter_newspage_body.py
?? apps/news/migrations/0005_alter_newspage_body.py
?? apps/news/tests/test_blocks.py
?? docs/process/EPIC3-003_feedback.md
?? static/news/
?? templates/news/blocks/article_image.html
```
