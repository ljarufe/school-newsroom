# EPIC3-004 Feedback

## Status

Implementation Closing Draft. The technical implementation and automated close
gate are complete. Real browser/Admin UAT is deferred to the maintainer and is
not claimed here.

## Source and initial checkout

- Source of truth: the refreshed `~/Downloads/EPIC3-004.md` containing the
  approved “Unificar metadata editorial y UX de imágenes de noticia” ticket.
- Active branch: `EPIC3-004-unify-news-image-metadata`.
- Initial `git status --short`: clean.
- Initial News migration leaf: `0006_newspage_seo_assistant_fields`; migrations
  `0001` through `0006` were applied in the inspected development database.
- Repository support range: `wagtail>=7.0,<8.0`; inspected installation:
  Wagtail 7.4.2.

## Maintainer UAT findings and corrections

The maintainer's real Admin review identified three presentation/authoring
issues in the initial implementation. They are corrections within EPIC3-004,
not New Work Discovered:

- the repeated contextual-image explanatory `HelpPanel` created visual noise
  and exposed unnecessary framework terminology, so it was removed from both
  featured and social image groups without replacement;
- the standalone “Cómo editar el contenido” panel visually attached itself to
  the preceding featured-image group, so its copy was shortened and supplied as
  `FieldPanel("body", help_text=...)`, which renders through Wagtail's supported
  field-panel help boundary inside the `Contenido` surface;
- caption-to-alt assistance existed only in `article_image`, so its state
  machine was extracted and shared by featured, body, and social image contexts.

Real browser verification of these corrections remains maintainer UAT.

## Implementation summary and shared pattern

`apps.news.image_metadata` is the shared low-risk policy boundary. It defines
the Spanish caption/alt/credit labels and help text, creates consistently
configured blank-safe model fields, strips effective values, and declares the
two required metadata parts. `apps.news.panels.contextual_image_panels()` builds
the repeated field-panel sequence for featured and social images without a
general explanatory `HelpPanel`.

The body `article_image` block reuses the same copy constants. Full form
validation iterates the two model-backed image contexts and the shared required
parts instead of maintaining separate featured/social validation branches. SEO
analysis uses one shared image-metadata check for the featured image and the
effective social image. Public social fallback cleanup and featured rendering
also use the common effective-text helper.

`static/news/js/caption_alt_sync.js` is the shared Admin authoring boundary. It
owns the synchronization state machine, duplicate-initialization guard, and the
two fixed NewsPage field-pair initializers. `NewsPageAdminForm.Media` loads it
for featured/social fields. `ArticleImageBlockAdapter.Media` lists it before
`article_image_block.js`; the Telepath block adapter resolves dynamic inputs by
prefix and delegates to the same project-owned function.

This keeps the three contexts conceptually aligned without forcing the
StreamField block into the model-field or page-panel implementation.

## Fields and migration

Generated migration:

```text
apps/news/migrations/0007_newspage_featured_image_alt_text_and_more.py
```

It adds these blank-safe fields without a data migration:

```text
featured_image_caption   CharField(max_length=500)
featured_image_alt_text  CharField(max_length=500)
featured_image_credit    CharField(max_length=255)
og_image_caption         CharField(max_length=500)
og_image_alt_text        CharField(max_length=500)
og_image_credit          CharField(max_length=255)
```

It also alters only the Spanish help text of `featured_image` and `og_image`.
The migration depends on News `0006` and `wagtailimages.0027_image_description`.
That Wagtail Images node is already the dependency used by the repository's
published News `0001` migration, so the generated migration does not raise the
established Wagtail migration baseline. Generated files are owned by the host
user. No published migration was rewritten.

Historical rows receive empty strings for all six fields. The migration
regression reconstructs historical revision content after `0007` and confirms
that no caption, alt text, or credit is fabricated.

## Admin placement and validation

The featured image group is immediately after `Resumen` and immediately before
the `Contenido` StreamField. It contains the native image chooser followed by
`Pie de foto`, `Texto alternativo`, and optional `Crédito de imagen`. Neither the
featured nor social group contains the removed general explanatory `HelpPanel`.

The concise Content help is attached directly to the body `FieldPanel`:

```text
Selecciona texto para mostrar la barra de formato. Usa el pin para mantenerla
visible y "/" para insertar o dividir bloques.
```

The social image and its three contextual fields remain nested under
`Configuración para redes sociales` in `Asistente SEO`. The body image remains
inside `Contenido`.

`NewsPageAdminForm.clean()` still returns before publication rules when Wagtail
enables deferred validation. Draft tests select featured and social images while
leaving their contextual metadata incomplete and remain valid. In full
validation, an effective caption and alt are required for each explicitly
selected featured or social image; whitespace-only input is rejected and credit
is optional. No independent social metadata is required when `og_image` is
empty and the featured-image fallback applies.

## Article image preservation

`article_image` retains this exact order:

```text
image, caption, alt_text, credit
```

Its image, caption, and alt remain required in full validation, credit remains
optional, and its semantic public template is unchanged. The Telepath adapter
still handles dynamically created/reopened blocks, but
`article_image_block.js` now delegates synchronization to
`schoolNewsroom.images.setupCaptionAltSync()` from the shared script. Empty alt
or alt equal to caption remains synchronizable; manual alt editing stops later
caption changes from overwriting it. Duplicate initialization is guarded on the
alt input. No persistent state or StreamField migration was added.

## Public rendering and SEO metadata

- Home hero and shared Home/list cards use only effective
  `featured_image_alt_text` for `alt`; cards do not display caption or credit.
- News detail renders the featured image explicitly inside `figure`, uses the
  contextual alt, and conditionally renders caption and optional credit.
- Historical featured images with no contextual metadata render safely with an
  empty alt and no fabricated figcaption. The global Wagtail Image description
  is not used as a News alt fallback.
- Body images retain their existing figure/caption/alt/credit output.
- Social images remain metadata-only and are not displayed as article content.
- Effective social image selection remains `og_image -> featured_image`.
- `og:image:alt` and `twitter:image:alt` use `og_image_alt_text` for an explicit
  social image, or `featured_image_alt_text` when the image itself falls back.
  Whitespace-only unused social alt text cannot suppress the featured fallback.
- JSON-LD image behavior and public-credit-only authorship are unchanged.
- The SEO Assistant now checks contextual featured metadata and the effective
  social image metadata using the same rule helper.

The SEO social preview uses the same effective contextual alt. Project CSS now
applies the existing body-image figcaption treatment to featured figcaptions.

## Global Wagtail Image separation

The implementation keeps the stock `wagtailimages.Image` model and adds no
`WAGTAILIMAGES_IMAGE_MODEL`, `AbstractImage`, or `AbstractRendition` code.
Global asset title, description, tags, focal point, and usage remain in Wagtail's
image library. They are neither copied into the six News fields nor used as
public News caption/alt/credit fallbacks. The same asset may therefore have
different contextual metadata for featured, body, and social use.

## Chooser/upload audit

Source inspection, form/widget inspection, and a server-rendered chooser request
established the following for featured image, body `article_image`, and social
`og_image`:

- all three use Wagtail 7.4.2 `AdminImageChooser`;
- all three resolve `wagtailimages_chooser:choose`;
- choosing an existing item uses Wagtail's native chosen response;
- uploading uses `ImageUploadView` and the native image form;
- `Editar esta imagen` resolves through `AdminURLFinder`; the inspected asset
  URL was `/admin/images/1/`, the global asset edit screen;
- the rendered modal response was HTTP 200, contained Spanish `Búsqueda` and
  `Subir`, and placed `tab-search` before `tab-upload`.

Wagtail's generic chooser template places the search trigger and panel first,
places the creation/upload tab second, and sets
`data-w-tabs-use-location-value="false"`. `BaseChooser` exposes the modal URL but
no supported initial-tab option, and the Image chooser viewset exposes the
upload tab identifier but no supported request parameter for selecting it.

Therefore default `Subir` was not implemented. Doing so for all three contexts
would require replacing or reordering Wagtail's generic chooser template/viewset
or manipulating its internal tab JavaScript. That does not meet the ticket's
small, supported, maintainable, low-risk boundary. Search remains available and
native behavior is unchanged.

This is server/source evidence, not proof of real browser modal behavior.

## Empty/broken chooser image diagnosis

No browser observation of an empty thumbnail is claimed. The inspected local
database contained five Wagtail Image assets. None had a blank file name, none
referenced a missing storage file, and all had at least one rendition (observed
counts: 8, 9, 1, 2, and 4). No project-code cause or reproducible broken asset
was found, so no image library, storage, fixture, or rendition repair was added.

Maintainer browser UAT should report any specific asset ID and network/media
response if a visually empty chooser tile appears; that evidence can distinguish
local data/media state from a project defect.

## Privacy and scope safeguards

No metadata field reads `MinorContributor`, internal contributor relations, age
bands, privacy flags, users, schools, or authorization data. Public image
metadata is editor-entered contextual text only. Regression coverage combines a
featured image with internal minor data and privacy flags, confirms the
contextual social alt is emitted, and confirms the internal name, age band, and
flags are absent.

No custom image model, chooser replacement, storage change, external download,
AI, OCR, face/minor detection, role/permission change, demo data, deployment
code, secrets, credentials, production values, or real minor data was added.

## Tests and automated validation

Coverage added or adapted includes:

- draft versus full validation for both featured and social contexts;
- missing effective caption and alt, including whitespace-only values;
- optional credit for both model-backed contexts;
- article-image order, labels, native chooser, validation, and Admin media;
- Admin panel location, removed image HelpPanels, body-scoped concise help, and
  social-panel nesting;
- form/Telepath media wiring and deterministic shared-script ordering;
- source-level featured/social field-pair initialization and body delegation;
- blank-safe fields and historical migration/revision behavior;
- Home/list contextual alt without visible card caption;
- detail caption, alt, optional credit, and historical safe fallback;
- explicit social alt, featured social fallback, and whitespace behavior;
- privacy/non-exposure in public image metadata;
- SEO analysis for featured and effective social metadata.

Focused validation results:

```text
138 tests: 137 passed, 1 test assertion failed; corrected and rerun
22 SEO public/Admin tests passed
28 migration/block tests: 27 passed, 1 historical runtime-schema test failed;
corrected and the affected migration test passed
1 blank-safe model test passed after adding explicit django_db isolation
```

Initial implementation general gate before maintainer UAT corrections:

```text
make check
ruff: All checks passed!
makemigrations --check: No changes detected
pytest: 178 passed in 28.09s
```

Maintainer UAT correction validation:

```text
Focused Admin panels, language/copy, blocks, forms, and media wiring:
60 passed in 5.61s

make migration-check:
No changes detected

make check:
ruff: All checks passed!
makemigrations --check: No changes detected
pytest: 179 passed in 27.40s
```

Source/wiring assertions confirm that both contextual image groups omit the
removed `HelpPanel`, body help is attached to its `FieldPanel`, the form loads
the shared script, the block adapter loads the shared script before its
dependent script, the two fixed field pairs are present, and the block script
delegates instead of retaining a second state machine. This is not browser
runtime evidence.

`git diff --check` is run again after this closing-draft update and recorded in
the final handoff chat and diff-review artifact.

## Failed attempts and root causes

- Initial Docker source inspection was blocked by the sandbox's Docker socket
  boundary. The approved read-only container command succeeded; this was not a
  repository defect.
- The first direct Wagtail widget inspection omitted `django.setup()` and raised
  `AppRegistryNotReady`. Initializing Django resolved the probe.
- The first server-rendered chooser probe used disallowed host `testserver` and
  returned HTTP 400. A scoped `override_settings(ALLOWED_HOSTS=["testserver"])`
  produced the expected HTTP 200 response.
- One SEO public test asserted that featured alt text was absent from the whole
  detail document. It legitimately appears on the visible featured image; the
  assertion was narrowed to social meta tags.
- A historical migration test migrated the schema only through `0006` and then
  reconstructed with the new runtime model, causing undefined-column errors.
  It now advances to `0007` before runtime reconstruction and verifies blank
  metadata.
- The first full gate isolated a new unmarked test that instantiated
  `NewsPage()` and therefore queried `ContentType`. Adding `django_db` made the
  dependency explicit; the rerun passed and the second full gate was green.
- `makemigrations` emitted the existing Treebeard 6 future-compatibility
  warnings for Wagtail managers. Generation, migration checks, and all tests
  succeeded; this ticket does not change Treebeard or Wagtail managers.
- During the maintainer-correction inspection, one combined shell probe placed
  a Docker command behind another command and hit the sandbox Docker-socket
  boundary. Running the already approved read-only Python inspection directly
  succeeded. No repository change was required.

## Editorial guide

`docs/editorial/guia_de_uso.md` now explains the featured-image location; the
three image contexts; caption versus alt versus optional credit; per-use News
data versus general file data in the image library; shared caption-to-alt
assistance and its manual-customization boundary; draft/full validation; visible
detail versus card/social behavior; native Search/Upload use; social fallback;
and the evidence-based decision to leave `Búsqueda` as the native initial tab.

## Deferred maintainer browser UAT

Use only fictional, non-sensitive content and complete the ticket's manual
validation. In particular, the maintainer must still verify:

1. Featured image appears after Summary and immediately before Content, with no
   repeated general image-metadata help block.
2. Featured chooser can search, upload, choose, clear, and open global asset
   editing; its contextual fields remain on NewsPage.
3. Content shows the concise help inside its own field surface and no standalone
   “Cómo editar el contenido” section.
4. Featured, body, and social captions initially copy to alt; continued caption
   edits update a still-synchronized alt; manually customized alt remains intact
   after later caption edits; reopening empty/equal/custom alt preserves the
   specified state.
5. Body image retains field order, chooser behavior, dynamic-block
   initialization, and semantic public output.
6. Social image chooser and metadata remain inside Asistente SEO without the
   removed general HelpPanel.
7. All three modals open with native `Búsqueda` first and retain `Subir`.
8. Draft save accepts incomplete contextual metadata.
9. Publish/workflow/full validation blocks missing/whitespace featured and
   explicit social caption/alt with clear Spanish errors; credit remains optional.
10. Home/list cards use contextual featured alt without visible caption/credit.
11. Detail shows contextual featured alt/caption/optional credit and a historical
   page without metadata remains safe and caption-free.
12. Open Graph, Twitter/X, canonical, robots, and JSON-LD remain correct for an
    explicit social image and featured-image fallback.
13. No internal minor name, age band, contributor relation, authorization flag,
    or privacy flag appears publicly.
14. If a chooser thumbnail is empty, capture the asset ID, file/media URL,
    browser network result, and whether `/admin/images/<id>/` can render it.

## Warnings and known issues

- Browser/modal behavior, responsive visual appearance, and real publication
  actions are deferred; source and Django client tests do not replace UAT.
- Existing historical pages are public-safe but will be blocked on future full
  validation until editors add required featured metadata, as approved.
- The existing Treebeard future warning remains outside this ticket.

## New Work Discovered

No blocking new work was discovered.

Potential future work, outside EPIC3-004:

- reevaluate an initial-tab API if a future supported Wagtail release adds one;
- investigate a specific local asset only if browser UAT provides a reproducible
  broken-thumbnail asset ID and media response;
- handle the existing Treebeard 6 compatibility warning in its dependency
  maintenance work, not in this feature.

## Durable knowledge candidates

- News image caption, alt, and credit are contextual per use and must never be
  sourced automatically from the global Wagtail Image model.
- The effective social image contract is `og_image -> featured_image`; alt text
  must follow the selected image context.
- Wagtail 7.4.2's native image chooser has no supported initial-tab option at the
  widget/viewset boundary used by this project.
- Migration tests that deliberately migrate backward must not use the newer
  runtime model until the schema returns to the matching/latest state.
- Generated third-party migration dependencies must be reviewed against the
  declared support range and the repository's established migration baseline.
