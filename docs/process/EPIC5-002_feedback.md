# EPIC5-002 Feedback

## Status

Implementation complete and technically validated.

## Scope delivered

EPIC5-002 replaces the 783-line `apps/news/seo.py` module with the approved
internal `apps.news.seo` package. The refactor preserves the current SEO
Assistant behavior and keeps the domain owned by `apps.news`.

The final package is:

```text
apps/news/seo/
├── __init__.py
├── analysis.py
├── content.py
├── keyphrases.py
└── readability.py
```

No feature from the superseded EPIC5-002 scope was implemented. In particular,
the change adds no related keyphrases, NLP, spaCy integration, advanced
readability rules, persistence, caching, social metadata changes, or future
scaffolding.

## Initial checkout

- Active branch: `EPIC5-002-modularize-seo`
- Initial `git status --short`: no output
- Initial implementation: `apps/news/seo.py`, 783 lines
- Initial responsibilities in one module: content extraction, RichText parsing,
  whitespace and match normalization, exact keyphrase matching and counting,
  image and link checks, length and word-count checks, readability rules,
  finding construction, and overall-state calculation.

The checkout agreed with the approved ticket. No branch operation was needed or
performed.

## Import and consumer inventory

The checkout-wide search included Python, templates, tests, forms, views,
helpers, documentation references, current local and remote Git refs, and the
history of `apps/news/seo.py`.

### Direct imports of `apps.news.seo`

- `apps/news/panels.py` imports `analyze_page` through `from .seo import
  analyze_page`. `SeoAssistantPanel.BoundPanel.get_context_data()` calls it and
  places the returned object in template context as `analysis`.
- `apps/news/tests/test_seo.py` imports `analyze_page`,
  `contains_exact_phrase`, `count_exact_phrase`, `count_words`, and
  `extract_content` through `from apps.news.seo import ...`.

No direct import exists in forms, views, models, template helpers, management
commands, migrations, or other application modules.

The Git-ref and file-history inspection found the same import shape in the
current branch, `main`, `origin/main`, the available historical branch refs, and
the original SEO Assistant commit. It found no historical migration importing
`apps.news.seo`.

### Indirect consumers and observable contracts

- `apps/news/templates/news/admin/seo_assistant_panel.html` consumes
  `analysis.overall_status`, `analysis.overall_label`, the ordered
  `analysis.seo_checks`, the ordered `analysis.readability_checks`, and each
  check's `status`, `label`, and `explanation`.
- `NewsPage.promote_panels` registers `SeoAssistantPanel`, so Wagtail page create
  and edit surfaces consume the analysis through the panel.
- `static/news/js/seo_assistant.js` consumes project-owned elements rendered by
  the panel template, but does not import, recalculate, or mutate the Python
  analysis findings.
- `apps/news/tests/test_admin_uat.py` and
  `apps/news/tests/test_mvp_access.py` exercise the rendered Admin boundary,
  including its Spanish headings, allowed fields, read-only editorial context,
  workflow surface, and minor-privacy exclusions.

There are no template, JavaScript, or public-view consumers of the Python helper
functions themselves.

### Separate metadata and taxonomy boundaries

`apps/news/seo_metadata.py` is not an `apps.news.seo` consumer. It remains an
unchanged sibling module used by `apps/home/models.py`, `apps/news/models.py`,
`apps/news/panels.py`, and `apps/news/views.py`. Migration
`0006_newspage_seo_assistant_fields.py` retains its historical import of
`apps.news.seo_metadata.validate_canonical_url`. This historical compatibility
path was not moved or edited.

The analysis engine has no direct dependency on `NewsTaxonomy`. The existing
Admin context boundary obtains `NewsTaxonomy.visible_paths` separately through
`NewsSeoContextPanel` and `NewsPage.taxonomy`. `apps/news/taxonomy.py` and this
integration remain unchanged.

The only repository references to the old `apps/news/seo.py` path outside the
deleted source file are historical process feedback documents. They describe
the architecture delivered by earlier tickets and were intentionally retained
as historical evidence rather than rewritten.

## Public API compatibility

`apps/news/seo/__init__.py` preserves every symbol imported by a real consumer:

```text
analyze_page
contains_exact_phrase
count_exact_phrase
count_words
extract_content
```

The package root contains no domain logic and declares only these five exports.
The existing imports in `panels.py` and `test_seo.py` did not need to change.

The former module also made internal implementation objects reachable as module
attributes even though no consumer imported them. The package root deliberately
does not re-export `LinkInfo`, `ContentEvent`, `ContentSnapshot`, `CheckResult`,
`AnalysisResult`, `normalize_whitespace`, `normalize_for_match`, or
`normalize_slug_for_match`. The data objects and normalization helpers still
exist at their responsible internal module where needed. Private helpers such
as `_RichTextExtractor`, `_image_metadata_check`, `_keyphrase_location_check`,
`_title_length_check`, `_description_length_check`, `_word_count_check`,
`_keyphrase_overuse_check`, and `_classify_links` remain private to their new
boundary or were replaced by an equivalent private boundary helper. No removed
root-level symbol had a checkout or historical import consumer.

## Final architecture and dependency direction

- `seo/__init__.py` is the compatibility API and contains re-exports only.
- `seo/analysis.py` owns `CheckResult`, `AnalysisResult`, SEO finding
  construction, finding grouping, coordination, and the overall state.
- `seo/content.py` owns RichText/HTML extraction, content events and snapshots,
  whitespace normalization, and word counting.
- `seo/keyphrases.py` owns accent/case/whitespace normalization for matching,
  slug normalization, exact phrase matching and counting, and the existing
  occurrence-rate calculation.
- `seo/readability.py` owns the existing sentence, paragraph, subheading, and
  continuous-section rules, thresholds, and messages. It returns internal
  finding values for `analysis.py` to construct as the shared public result
  contract.

The dependency direction is acyclic:

```text
seo/__init__.py -> analysis, content, keyphrases
analysis -> content, keyphrases, readability, image_metadata
keyphrases -> content
readability -> content
```

There is one implementation only. The old `apps/news/seo.py` file is deleted.
No dynamic proxy, import hook, compatibility shim, empty future module, or
separate Django app was introduced.

## Characterization coverage

Before the monolith was removed, `apps/news/tests/test_seo.py` was strengthened
and run against the original implementation. The new characterization asserts:

- the intermediate `Necesita mejoras` state and status, complementing the
  existing `Incompleto` and `Bueno` coverage;
- the exact observable order of all 16 SEO findings;
- the exact observable order of all five readability findings;
- representative copy and numeric outputs for exact phrase use, extracted word
  count, and subheading applicability;
- whitespace-only SEO title, description, keyphrase, and RichText behavior;
- empty snapshot fallbacks and empty-content readability copy.

The pre-existing suite already covers direct public imports, match
normalization, phrase boundaries and counts, content structure, nested lists,
links, images and fallbacks, title/description/body thresholds, keyphrase
overuse, paragraph and sentence thresholds, subheadings, continuous sections,
all overall states, and canonical validation.

The focused integration run also covers unchanged public metadata, Admin panel
rendering, the SEO curator surface, workflow authorization, and minor privacy.
The complete suite covers the separate taxonomy behavior and public queries.

## Differences found and corrected

No functional difference was found between the original implementation and the
package refactor.

While establishing characterization on the original module, two initially
estimated expected values were corrected from the actual baseline: the default
fixture contains two exact body occurrences of the keyphrase, and its body has
27 words because visible link text is included. These were test-authoring
corrections made before the implementation move, not product changes or weakened
assertions.

The first Docker formatting attempt was denied access to the Docker socket by
the execution sandbox. It was rerun through the approved Docker-first path and
succeeded. All written files remained owned by the checkout user (`1000:1000`).

## Automated validation

Original-implementation baseline:

```text
docker compose run --rm web sh -c 'until nc -z db 5432; do sleep 1; done; DJANGO_SETTINGS_MODULE=config.settings.test pytest -o cache_dir=/tmp/school-newsroom-pytest-cache apps/news/tests/test_seo.py'
40 passed
```

First post-refactor focused lint, formatting check, and SEO tests:

```text
docker compose run --rm web sh -c 'RUFF_CACHE_DIR=/tmp/school-newsroom-ruff-cache ruff check apps/news/seo apps/news/tests/test_seo.py && RUFF_CACHE_DIR=/tmp/school-newsroom-ruff-cache ruff format --check apps/news/seo apps/news/tests/test_seo.py && until nc -z db 5432; do sleep 1; done; DJANGO_SETTINGS_MODULE=config.settings.test pytest -o cache_dir=/tmp/school-newsroom-pytest-cache apps/news/tests/test_seo.py'
Ruff check passed; the format check identified two files to format
40 passed
```

After applying the targeted formatter, the final focused style check was:

```text
docker compose run --rm web sh -c 'RUFF_CACHE_DIR=/tmp/school-newsroom-ruff-cache ruff check apps/news/seo apps/news/tests/test_seo.py && RUFF_CACHE_DIR=/tmp/school-newsroom-ruff-cache ruff format --check apps/news/seo apps/news/tests/test_seo.py'
All checks passed
6 files already formatted
```

Ticket-focused integration tests:

```text
docker compose run --rm web sh -c 'until nc -z db 5432; do sleep 1; done; DJANGO_SETTINGS_MODULE=config.settings.test pytest -o cache_dir=/tmp/school-newsroom-pytest-cache apps/news/tests/test_seo.py apps/news/tests/test_seo_public.py apps/news/tests/test_admin_uat.py::test_news_page_create_surface_transforms_promote_tab_into_seo_assistant apps/news/tests/test_mvp_access.py::test_seo_curator_edit_surface_hides_content_properties_and_minor_data'
55 passed
```

General repository gate, run once after the implementation delta stabilized:

```text
make check
Ruff: passed
makemigrations --check --skip-checks: No changes detected
pytest: 301 passed
```

Whitespace and conflict check:

```text
git diff --check
no output
```

## Schema, dependencies, configuration, and generated files

- Dependencies added or changed: none
- Settings added or changed: none
- Models or fields added or changed: none
- Migrations created or edited: none
- Schema changes: none
- Persistent database migrations applied: none
- Caching or persistence added: none
- Generated repository files: none
- `apps/news/seo_metadata.py`: unchanged and still a sibling module
- `apps/news/taxonomy.py` and `NewsTaxonomy`: unchanged

## Manual and browser validation

No manual UAT was performed or requested. There is no visible delta, and the
Admin rendering and public metadata boundaries are covered by focused automated
tests.

`make browser-test` was not run. No template, panel, JavaScript, browser
interaction, or visible-state file changed, so the ticket's browser-test trigger
did not occur.

## Warnings and known issues

None identified for this ticket. The Docker database service started for test
runs, but no destructive Docker, volume, or persistent-data command was used.

## New Work Discovered

None.

The checkout does not contradict the approved split or the expected direction
for EPIC5-009. The package provides responsible existing boundaries without
adding any EPIC5-009 implementation or scaffolding.
