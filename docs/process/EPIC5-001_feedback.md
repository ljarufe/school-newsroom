# EPIC5-001 Feedback

## Status

Implementation Closing Draft

## Scope delivered

EPIC5-001 implements a professional editorial `Asistente SEO` surface for
`NewsPage` without adding dependencies or external runtime services.

The implementation:

- transforms the inherited promotion tab into `Asistente SEO` through Wagtail's
  supported `TabbedInterface` and `ObjectList` APIs;
- reuses native `slug`, `seo_title`, and `search_description` fields;
- keeps `show_in_menus` in a visibly separate `Navegación y menús` section and
  excludes it from analysis;
- adds the six approved `NewsPage` fields through migration `0006`;
- derives SEO and Spanish readability checks in pure Python;
- parses stored `RichText.source` HTML with the standard-library `HTMLParser`;
- stores no analysis results;
- limits Admin JavaScript to ordinary text inputs, counters, previews, and
  fallback indicators;
- emits public canonical, robots, Open Graph, Twitter/X, and safe JSON-LD
  `NewsArticle` metadata;
- applies the environment-level noindex default to both current public HTML
  page types, `HomePage` and `NewsPage`;
- uses Wagtail's native sitemap view backed by Django's sitemap framework;
- serves a crawl-permitting `robots.txt` with the current Wagtail Site sitemap;
- derives JSON-LD authors only from ordered, non-empty public credits.

## Native promotion surface

The resolved Wagtail 7.4.2 edit handler previously inherited a `Promocionar`
tab with native search-engine and menu panels. `NewsPage` now supplies a custom
edit handler whose visible tabs are `Contenido` and `Asistente SEO`.

`Page.settings_panels` remains registered as the third `ObjectList` in the
custom `TabbedInterface`, preserving Wagtail's settings/sidebar integration.
Wagtail 7.4.2 does not render that list as a visible `Propiedades` tab in the
observed page editor, and the implementation does not force one.

The native fields remain the only sources of truth for URL slug, SEO title, and
meta description. `show_in_menus` remains native but is rendered under
`Navegación y menús` with Spanish help text that states it does not affect the
SEO score.

## Data and migration

Migration `0006_newspage_seo_assistant_fields` adds:

```text
focus_keyphrase
og_title
og_description
og_image
canonical_url
seo_noindex
```

Existing pages receive blank values, a null social image, and `False` for the
page-level noindex flag. No historical metadata is fabricated and no published
migration was rewritten.

Canonical values use the existing Django URL validation plus a project
validator that limits the value to HTTP/HTTPS and rejects fragments.

## Deterministic SEO rules

Exact keyphrase matching is case-insensitive, whitespace-normalized, and
accent-insensitive. It does not use synonyms, stemming, word-form analysis, or
multiple keyphrases.

Implemented checks cover:

- focus keyphrase presence;
- keyphrase in native SEO title, slug, native meta description, summary or
  introduction, headings, and body;
- evident keyphrase overuse;
- native SEO-title and meta-description lengths;
- body word count;
- featured image;
- body-image alt text;
- internal and external links.

Thresholds:

```text
SEO title
missing or >70: problem
1–29 or 61–70: warning
30–60: good

Meta description
missing or >180: problem
1–119 or 161–180: warning
120–160: good

Body length
<150: problem
150–299: warning
>=300: good

Keyphrase overuse
>3 occurrences per 100 words and at least 4: warning
>5 occurrences per 100 words and at least 6: problem
```

## Readability rules

Implemented Spanish-oriented heuristics cover text presence, paragraph length,
sentence length, subheadings in long articles, and large text sections.
Nested RichText list items are captured as flat events without copying child
text into ancestor list-item events; the complete visible article text remains
available for article-level checks.

Thresholds:

```text
Paragraph
<=150 words: good
151–250: warning
>250: problem

Long sentence
>30 words
>25% long sentences: warning
>50% long sentences: problem

Subheading
not applicable below 300 article words
warning at 300+ words without H2/H3/H4

Continuous section
<=300 words: good
301–500: warning
>500: problem
```

These checks are presented as recommendations, not linguistic certification or
publication requirements.

## Overall status

The overall state is:

- `Incompleto` when focus keyphrase, native SEO title, native meta description,
  or article text is missing;
- `Necesita mejoras` when the core inputs exist but an applicable warning or
  problem remains;
- `Bueno` when every applicable check is good.

The existing Wagtail deferred-validation and publication-validation behavior is
unchanged. SEO recommendations never add form errors.

## Public metadata and canonical behavior

Public fallbacks are centralized:

```text
title: seo_title -> page title
description: search_description -> summary
OG title: og_title -> effective title
OG description: og_description -> effective description
OG image: og_image -> featured_image
canonical: canonical_url -> page.get_full_url(request)
site name: Wagtail Site.site_name -> WAGTAIL_SITE_NAME
```

Optional description outputs are conditional. The HTML meta description and
JSON-LD `description` are omitted when the native meta description and summary
produce no effective value. Open Graph and Twitter/X descriptions are omitted
when their effective social description is empty. No description is fabricated.

Additional fallback coverage confirms that an explicit `og_image` takes
precedence over `featured_image`. Clearing the optional field or deleting its
selected image leaves `og_image` null through `SET_NULL` and restores the
featured-image fallback.

The same canonical decision drives the canonical link, Open Graph URL,
JSON-LD `mainEntityOfPage`, and sitemap inclusion:

- empty or self canonical: include the local indexable page;
- different canonical: emit it publicly and omit the local page from the
  sitemap;
- no external URL is placed in the local sitemap.

## Indexation, sitemap, and robots

`SEO_DEFAULT_NOINDEX` is a typed `django-environ` Boolean with a conservative
default of `True`.

When true, Home and News emit `noindex, follow` and their sitemap hooks return no
entries. When false, Home is indexable and News is indexable unless its own
`seo_noindex` is true.

`robots.txt` always permits crawling and includes the absolute Wagtail Site
sitemap URL, so it never prevents crawlers from reading a noindex meta tag.

The native Wagtail sitemap provides live/public/restriction filtering. The
project only overrides per-page URL inclusion for the ticket's noindex and
canonical decisions; no custom sitemap engine was added.

## JSON-LD and privacy

JSON-LD is serialized with explicit escaping for script-breaking characters.
Authors are built exclusively from ordered, non-empty
`NewsPagePublicCredit.display_name` values.

Author objects intentionally contain only `name`. The implementation does not
infer or persist `Person` versus `Organization`, and it does not promise rich
result eligibility.

Internal contributors, `MinorContributor`, age bands, authorization flags, and
privacy fields are not queried for metadata and are covered by public-rendering
tests.

JSON-LD omits the optional `description` property when the effective public
description is empty and retains the existing non-empty fallback otherwise.
It also omits `datePublished` when an incomplete draft has no publication date;
no date is fabricated. The existing conditional `dateModified` behavior is
unchanged.

## JavaScript boundary

`seo_assistant.js` watches only normal title, slug, summary, SEO title, meta
description, social title, social description, and canonical inputs. Observing
the summary fixes live search/social description fallbacks when explicit
description fields are empty. The script updates character counts, previews,
slug representation, and fallback messages.

The panel now supplies the local served page URL separately from the effective
canonical URL. An existing external canonical is shown initially; clearing the
field restores the local URL in the live preview, and entering another canonical
shows that entered value.

Wagtail 7.4.2's `TabbedInterface` uses the native `w-tabs` controller and URL
fragment state. Successful form redirects do not retain that fragment. The
small persistence bridge stores the active SEO panel ID in `sessionStorage`,
scoped by the current Admin pathname, only when the native draft-save button is
submitted while that panel is active. On reload it consumes the state only when
Wagtail rendered a success message, the form has no validation errors, and no
different URL fragment requested another panel. It then activates Wagtail's own
tab trigger and URL state instead of changing panel classes directly.

Validation responses, named workflow actions, unrelated page paths, and URLs
that intentionally select another panel are not overridden. Unavailable session
storage degrades to Wagtail's default behavior.

It does not inspect Draftail ContentState, register Telepath adapters, analyze
body content, or integrate with external services. Server-side analysis after
save/reload remains authoritative.

## Independent local review correction

An independent local Codex review completed with this severity distribution:

```text
P0: 0
P1: 0
P2: 3
P3: 0
```

All three P2 findings were accepted and corrected:

1. `build_news_article_data()` called `isoformat()` unconditionally on a draft
   publication date. It now adds `datePublished` only when the date exists.
2. The Admin panel used the effective canonical as `data-public-url`, so clearing
   a saved external canonical could not restore the local URL. The panel now
   keeps the Wagtail served URL in that attribute and uses the effective
   canonical only for the initial preview and canonical-field behavior.
3. `_RichTextExtractor` appended each text chunk to every open capture, causing
   nested list-item content to appear in both child and ancestor events. It now
   appends to only the innermost active capture while retaining all visible text
   in the article snapshot.

## Files changed

Verified implementation inventory:

```text
.env.example
AGENTS.md (maintainer-authored handoff rules; preserved by Codex)
apps/home/models.py
apps/news/migrations/0006_newspage_seo_assistant_fields.py
apps/news/models.py
apps/news/panels.py
apps/news/seo.py
apps/news/seo_metadata.py
apps/news/views.py
apps/news/templates/news/admin/seo_assistant_panel.html
apps/news/tests/test_admin_uat.py
apps/news/tests/test_forms.py
apps/news/tests/test_language.py
apps/news/tests/test_migrations.py
apps/news/tests/test_seo.py
apps/news/tests/test_seo_public.py
config/settings/base.py
config/settings/tests.py
config/urls.py
docs/editorial/guia_de_uso.md
docs/process/EPIC5-001_feedback.md
static/news/css/seo_assistant.css
static/news/js/seo_assistant.js
templates/home/home_page.html
templates/news/news_page.html
```

Temporary, untracked handoff artifact regenerated after validation:

```text
tmp/EPIC5-001_diff_review.txt
```

The maintainer updated `AGENTS.md` with reusable inspection-only and
implementation-pass handoff artifact requirements. Codex read and followed that
change, preserved it in the worktree, included it in the complete diff-review
artifact, and did not author or overwrite it.

## Automated validation

Focused validation completed so far:

- existing form/Admin/public regression selection: 34 passed;
- pure SEO analysis: 35 passed;
- public SEO, indexation, sitemap, and robots: 6 passed;
- EPIC5-001 migration preservation test: 1 passed;
- combined affected migration, SEO, Admin, forms, and settings selection after
  migration-order fixes: 82 passed;
- Ruff after the first source delta: passed;
- migration drift after the first source delta: no changes detected.

Correction-pass focused validation:

```text
5 passed
```

This selection covers summary input observation, the existing non-empty summary
fallback, omission of empty HTML/JSON-LD descriptions, explicit OG-image
precedence, and clearing/deleting an OG image back to the featured-image
fallback. Image/rendition tests use temporary media storage.

Independent-review focused validation:

```text
4 passed in 4.63s
```

This selection covers a missing draft publication date, separate served and
canonical Admin preview values, the JavaScript canonical-clear wiring, and
nested-list extraction/readability calculations.

Making the served-URL distinction explicit as a final JavaScript constant
invalidated that focused evidence. The same selection was rerun successfully:

```text
4 passed in 4.59s
```

The executable Python, template, JavaScript, and test delta invalidated the
previous 139-test general-gate evidence. The technical-close gate below is rerun
after this correction pass; the earlier result is retained only as historical
implementation-pass evidence.

Initial implementation-pass technical-close gate (superseded by the correction
pass below):

```text
make check
Ruff: passed
Migration drift: no changes detected
pytest: 139 passed in 21.88s
git diff --check: passed
```

Correction-pass technical-close general gate:

```text
make check
Ruff: passed
Migration drift: no changes detected
pytest: 143 passed in 22.12s
git diff --check: passed
```

The Python, template, JavaScript, and focused-test changes from the independent
review invalidated the 143-test correction-pass evidence above. The current
technical-close gate is recorded below after rerunning it against this complete
delta.

Independent-review technical-close general gate (superseded by the final
JavaScript naming delta):

```text
make check
Ruff: passed
Migration drift: no changes detected
pytest: 147 passed in 21.75s
git diff --check: passed
```

The final executable JavaScript and regression-test delta invalidated this
147-test result. The complete technical-close gate was rerun once more and is
recorded below.

Final independent-review technical-close general gate:

```text
make check
Ruff: passed
Migration drift: no changes detected
pytest: 147 passed in 21.69s
git diff --check: passed
```

The executable Admin model, JavaScript, tests, and documentation changes from
the UAT correction pass invalidate the prior 147-test gate. Focused correction
evidence currently covers:

```text
2 passed in 4.94s
```

This selection proves the Spanish visible-tab inventory, absence of the former
`Promocionar` label, continued `Page.settings_panels` registration, and the
page-scoped success/error guards used by the active-tab persistence bridge.
Source-level tests do not prove browser storage, redirect, or focus behavior.

UAT-correction technical-close general gate:

```text
make check
Ruff: passed
Migration drift: no changes detected
pytest: 148 passed in 23.92s
git diff --check: passed
```

New file ownership was inspected after Docker-backed validation. Every new
repository file is owned by `ljarufe:ljarufe`; no repository media rendition or
compiled-output side effect is present.

## Maintainer browser UAT

The maintainer reported the following completed browser UAT results before this
correction pass.

Passed:

- live search preview;
- live social text preview;
- title and description counters;
- SEO checks;
- Spanish readability checks;
- body-image alt analysis;
- individual noindex;
- global noindex;
- sitemap;
- `robots.txt`;
- public metadata and safe public-author output.

Expected results:

- the exact focus keyphrase was absent from the tested headings, so the subtitle
  check correctly produced a warning;
- after adding a body image with alt text, its check became green.

Not applicable:

- authoring a nested list through the current Admin UI. No indentation control
  is exposed and `Tab` moves focus. Defensive parsing and regression coverage
  remain for imported, pasted, historical, or externally generated nested-list
  HTML.

Failed in UAT and corrected in this pass:

- the visible tab label was English;
- a successful draft save returned to `Contenido` instead of the SEO tab;
- documentation incorrectly claimed a visible `Propiedades` tab.

The corrected Spanish label and post-save tab restoration have not been marked
as manually passed; both require the maintainer retests below.

## Deferred validation

Two focused maintainer/browser retests remain required:

- confirm that the visible tab label is `Asistente SEO`;
- from `Asistente SEO`, save a valid draft/update and confirm that the reloaded
  editor returns to that tab. Also confirm that a validation error still lets
  Wagtail select the tab or panel containing the error.

Commit, push, CI, GitHub review, and merge are not completed by this
implementation handoff. The maintainer completed the reported UAT cases above;
only the two focused correction retests remain pending.

## Failed attempts and root causes

- The initial parallel focused lint/migration invocation produced a Docker API
  permission failure for migration-check while lint ran successfully. Repeating
  the migration check sequentially still encountered sandbox Docker access; the
  approved Docker-first command then completed and reported no drift.
- The first Ruff run found only new line-length violations. The source was
  reformatted directly and Ruff passed.
- Initial pure-analysis tests supplied tuple lists instead of Wagtail
  `StreamValue`; fixtures were corrected to use the model field's real runtime
  conversion.
- Initial public URL assertions concatenated a full multi-Site `page.url` to a
  hostname. Tests now use an explicit valid `.test` Site and request host.
- The first all-green readability fixture contained intentionally long
  sentences. It was rewritten into genuinely short sentences rather than
  weakening the deterministic threshold.
- The migration preservation assertion compared text directly with a
  `StreamValue`. It now verifies the preserved RichText source.
- The former latest-migration EPIC3 revision test used the current runtime model
  while intentionally holding the schema at `0005`. Adding `0006` made that
  assumption invalid, so the test now advances to the new leaf before current
  runtime reconstruction while retaining all historical `0004`/`0005`
  assertions.
- Transactional migration tests can legitimately remove bootstrap rows between
  cases. The EPIC5 migration fixture now creates a fictional Site and section
  when absent instead of relying on test order.
- The first correction-pass feedback patch used context copied from overlapping
  terminal read ranges and expected a duplicate line that was not present. The
  patch made no change; smaller exact patches updated the feedback successfully.
- Correction-pass lint found one overlong OG-image assertion. The assertion was
  formatted without changing behavior, and lint then passed before the general
  gate.
- The first installed-Wagtail inspection command imported Admin panels before
  initializing Django and raised `AppRegistryNotReady`. The corrected read-only
  probe called `django.setup()` and confirmed Wagtail 7.4.2's native `w-tabs`
  location behavior.
- A bounded regular-expression probe against Wagtail's minified one-line bundle
  was inefficient and was terminated. A byte-offset lookup followed by a fixed
  byte-range read isolated the controller without another broad scan.
- The first UAT-correction `make check` stopped at Ruff because one new
  source-level JavaScript assertion exceeded the line-length limit. Wrapping the
  assertion preserved its behavior; the repeated complete gate then passed.
- An optional host-side `node --check` probe could not run because the repository
  does not select a Node.js version for the installed asdf shim. No Node runtime
  or dependency was added for this ticket; JavaScript remains covered by focused
  source assertions and the pending browser retest.

## Warnings and known limitations

- Sentence splitting is deliberately heuristic and can misinterpret Spanish
  abbreviations or unusual punctuation.
- Search and social previews are conceptual rather than pixel-perfect copies of
  third-party interfaces.
- JSON-LD author type is intentionally unspecified because public credits are
  untyped.
- Correct production canonical, sitemap, robots, and image URLs depend on a
  correctly configured Wagtail Site hostname and port.
- Existing Treebeard manager compatibility warnings observed during migration
  inspection predate this ticket and were not changed.

## New Work Discovered

Potential future tickets, all outside EPIC5-001:

- full audit of untranslated Wagtail Admin strings, including status, usage,
  checks, validation banners, and explanatory panels;
- unified image chooser/upload UX and metadata across featured images, body
  images, and social images;
- investigation of images with repeated filenames and rendition/cache behavior;
- RichText paste and formatting ergonomics for content copied from external
  editors;
- optional nested-list authoring support if later editorial requirements
  justify it;
- reusable typed public author profiles or explicit public-credit author type;
- SEO curator roles and permissions;
- mandatory SEO review workflow;
- redirects and 404 SEO management;
- multiple or related keyphrases, synonyms, and Spanish word-form analysis;
- advanced internal-link suggestions and keyword cannibalization analysis;
- Google News/News SEO extensions;
- Search Console and sitemap submission;
- social publishing integrations;
- richer featured-image accessibility/context policy;
- browser automation for the Admin preview boundary.

## Durable knowledge candidates

The repository maintainer has already added durable inspection-only and
implementation-pass handoff artifact rules to `AGENTS.md`. Codex preserved but
did not author that change.

Public absolute URLs continuing to come from Wagtail Sites/page URL helpers,
rather than `WAGTAILADMIN_BASE_URL`, remains a useful technical convention in
this feedback. No additional repository-instruction update is proposed in this
correction pass.
