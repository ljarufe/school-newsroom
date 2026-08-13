# EPIC6-002 Closing Feedback Final

## Delivered scope

The public `/noticias/` archive now has a reusable archive boundary:

- `NewsArchiveFilterForm` normalizes `buscar`, `seccion`, `subseccion`,
  `etiqueta`, `orden`, and `pagina` once.
- Immutable `NewsArchiveCriteria` carries normalized values and preserves only
  effective query parameters.
- `NewsArchiveQueryService` starts with `public_news_pages()`, retains Site,
  public/live, eager-loading, and uniqueness constraints, and applies each
  structured criterion explicitly.
- Django `Paginator` is the HTML-only adapter with ten cards per page.

The archive provides exact main-section, subsection, and tag filtering; safe
invalid and incompatible states; an accessible chronological ordering toggle;
query-preserving pagination; and `noindex, follow` for effective searches.
Detail-page tags link to their exact archive filter.

The public navigation includes a compact dependency-free search affordance with
the accessible name `Buscar noticias`, linking from every public page to
`/noticias/#buscar-noticias`.

The subsection control is progressively enhanced in the browser without backend
requests: standalone subsection choices are grouped by their parent main
section, option labels contain only the subsection name, selecting a main
section shows only compatible subsections, and an incompatible selected
subsection is cleared. The backend remains authoritative, still supports
standalone `subseccion=<slug>`, and still rejects manually forced incompatible
section/subsection pairs with an explicit error state.

## Search implementation

The Wagtail 7.4.2 runtime resolves ModelSearch 1.3.2, whose native PostgreSQL
backend supports `Fuzzy(query, unaccent=True)` over
`wagtailsearch_indexentry.title_text` and `body_text`. No direct Page/Tag
`TrigramSimilarity` query or StreamField JSON trigram index was added.

`NewsPage.search_fields` indexes only public editorial text:

- title with the highest weight;
- tags with the middle weight;
- body with the lower weight.

The observable archive ranking test verifies title > tag > body. Internal
contributors, minor/privacy fields, workflow data, and other non-public data
are not indexed or queried.

The primary search path is native OR FTS relevance. Native fuzzy search is used
only when FTS returns zero results. Explicit `orden=asc|desc` preserves the
matching result set but overrides relevance with publication chronology.

The calibrated `FUZZY_SIMILARITY_THRESHOLD` remains the ModelSearch default
`0.3`: controlled fixtures accept `festivla` for `Festival` and
`radioescoalr` for `radioescolar`, while rejecting
`xilofonoimprobable`.

Tag changes explicitly reindex their parent page through ModelSearch because a
taggit through-model update does not save the parent Page and therefore does
not trigger ModelSearch's normal Page post-save handler.

## Migration and query-plan evidence

`news.0016_public_news_search_infrastructure` reproducibly installs `unaccent`
and `pg_trgm`, creates the immutable `f_unaccent(text)` wrapper, creates the
project-owned `school_newsroom_es` Spanish unaccent/stemming configuration, and
creates native ModelSearch expression GIN indexes on `title_text` and
`body_text`.

Forward/reverse migration evidence passed against Django's disposable test
database.

A separate disposable PostgreSQL database with forty fictional archive pages
produced native ModelSearch `EXPLAIN ANALYZE` evidence:

- FTS returned 40 rows in 1.459 ms and ranked with the title/body tsvectors.
- Fuzzy returned 40 rows in 0.861 ms using
  `word_similarity(..., f_unaccent(title_text/body_text))` at threshold 0.3.
- At this intentionally small fixture volume PostgreSQL chose the existing
  IndexEntry content-type/object index and sequential joins rather than the GIN
  indexes; no test asserts a specific planner choice.

A real `update_index --backend default` call in the disposable test database
rebuilt an existing NewsPage index entry and made its existing title content
searchable.

For an existing maintained environment, apply the migration and run:

```text
python manage.py update_index --backend default
```

before relying on the new search fields/configuration for previously indexed
content.

## Automated validation

Final validation after the maintainer UAT remediation:

- focused UAT-remediation public-rendering tests:
  `4 passed, 34 deselected`;
- focused UAT-remediation Playwright archive scenario: `1 passed`;
- focused archive public-rendering tests: `35 passed`;
- browser fixture unit tests: `2 passed`;
- migration forward/reverse test: `1 passed`;
- changed-file Ruff and formatting checks: passed;
- `make check`: passed with `444 passed`, 90.4% coverage, lint green, and
  migration detection green;
- `make browser-test`: passed all 7 Chromium scenarios;
- `git diff --check`: passed.

The final archive browser scenario covers the public search navigation
affordance and anchor, tag navigation, search/query preservation, main-section
and exact-subsection filters, dependent subsection behavior, standalone
subsection use, a structured combination, empty and invalid states, manually
forced incompatible filters, chronological ordering, pagination, mobile layout,
keyboard focus, and browser console errors.

## Failure disposition

Two browser-run incidents occurred during implementation and remediation:

1. An earlier complete browser-gate failure could not be reproduced. A direct
   diagnostic run and the subsequent official `make browser-test` both passed
   all seven Chromium scenarios. It remains classified as unreproduced; no
   product fix was made for an unproven cause.
2. During the final UAT remediation, one browser-gate attempt stopped before
   Playwright because a focused run had intentionally retained its disposable
   database and the deterministic browser fixture encountered an existing
   slug. After confirming cleanup of that temporary state, the single full
   rerun passed all seven scenarios. This was environmental fixture state, not
   a product failure.

No browser assertions were weakened or skipped to obtain a green gate.

## Maintainer UAT

Maintainer UAT passed for the implemented archive/search behavior and the final
UAT remediation.

Validated behavior includes:

- normal and accent-insensitive search;
- controlled fuzzy typo behavior;
- section, subsection, tag, and combined filters;
- exact incompatible-filter error behavior;
- search-result ordering and chronological asc/desc ordering;
- pagination and query-parameter preservation;
- tag navigation;
- mobile and keyboard usability;
- negative minor-contributor discovery behavior;
- the global `Buscar noticias` navigation affordance;
- archive search-anchor navigation;
- subsection labels using only their own names;
- client-side filtering of subsection choices by selected main section;
- clearing an incompatible subsection after changing the main section;
- standalone subsection filtering remaining usable;
- manually forced incompatible section/subsection URLs remaining rejected by
  the server.

## Documentation

`docs/editorial/guia_de_uso.md` documents the public search/archive behavior in
Spanish, including search discovery, combinable filters, tag navigation,
chronological ordering, pagination, empty/invalid states, subsection behavior,
and the privacy boundary.

## Future handoff

EPIC3-010 should add a public-author criterion to `NewsArchiveCriteria` and an
explicit service handler; it must not index internal minor contributors.

A future normalized Peru geography ticket should add its own explicit
geography criterion instead of filtering the existing free-text coverage
fields.

Archive/search caching remains a conditioned candidate only if measured
PostgreSQL archive/search latency or load demonstrates a concrete bottleneck.

An external Elasticsearch/OpenSearch backend remains a conditioned candidate
only if PostgreSQL search no longer satisfies a demonstrated product or
performance requirement.

No cache, external search backend, author filter, or geography filter is
implemented by EPIC6-002.
