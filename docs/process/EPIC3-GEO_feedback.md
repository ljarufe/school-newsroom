# EPIC3-GEO Closing Feedback

## Delivered scope

The repository now has an `apps.geography` bounded context with normalized
Department, Province, and District models. Official UBIGEO codes are stored as
string primary keys, hierarchy rows use protected foreign keys, and `is_active`
supports territorial retirement without deleting referenced history.

School location and NewsPage editorial coverage are separate normalized
boundaries. Each exposes a required department and optional district, omits an
editorial province field, and rejects a district whose internal province belongs
to another department. Coverage is never inferred from School location.

One reusable dependent-district widget serves the School snippet editor, NewsPage
coverage editor, and public archive. It uses the local read-only
`/geografia/distritos/` lookup after three characters, limits results to the
selected active department, renders at most 20 candidates, supports keyboard
selection, clears incompatible state, cancels stale requests, and does not render
the complete district catalog in HTML.

The existing `/noticias/` archive boundary now accepts `departamento` and
`distrito`, validates invalid or incompatible combinations explicitly, applies
coverage filters before pagination, and preserves them alongside search,
taxonomy, tag, ordering, and pagination parameters. Public coverage, section,
subsection, and tag metadata link back to their structured archive filters.
Search weighting, primary FTS, and fuzzy fallback behavior were not changed.

## Official source and provenance

- Authority: Instituto Nacional de Estadística e Informática (INEI).
- Publication: *Perú: Población Total Proyectada al 30 de Junio de cada año,
  según Departamento, Provincia y Distrito, 2018-2026*.
- Official publication page:
  `https://www.gob.pe/institucion/inei/informes-publicaciones/6894980-peru-poblacion-total-proyectada-al-30-de-junio-de-cada-ano-segun-departamento-provincia-y-distrito-2018-2026`.
- Resolved resource:
  `https://cdn.www.gob.pe/uploads/document/file/8261096/6894980-peru-poblacion-total-proyectada-al-30-de-junio-de-cada-ano-segun-departamento-provincia-y-distrito-2018-2026.xlsx?v=1768402069`.
- Cutoff/publication date: 2025-12-31.
- Format: XLSX; worksheet `POB. PROYECTADA 2018-2026`; UBIGEO in column A
  and territorial name in column B.
- Raw size: 212,580 bytes.
- Raw XLSX SHA-256:
  `9436df29b883fd4a9db3705040a6668ff4efe7047c2643249b6b6bedd90d5c8b`.
- Normalized CSV SHA-256:
  `58a2959fa22fd9ff3b515a357f451e26a56f82178dfa363f64499d996fb0fff3`.
- Counts: 25 department-level units, 196 provinces, and 1,892 districts.
- Arequipa is department code `04`; Callao is represented at the department
  level used by the product.
- License status: License not explicitly stated on the selected INEI
  publication/resource.

The maintainer approved this official source with that documented provenance
limitation. No license was inferred from a different INEI dataset. The normalized
snapshot contains only the territorial code/name columns needed by the product;
population values, headers, notes, and the national aggregate were excluded.
Whitespace and footnote suffixes were normalized, source names were converted to
display case, and hierarchy codes were derived from `DD0000`, `DDPP00`, and
`DDPPDD`. Full transformation details are in `apps/geography/data/README.md`.

`openpyxl` 3.1.5 is now an explicit direct dependency for controlled XLSX
parsing. Its installed metadata reports the MIT license, recorded in
`THIRD_PARTY_NOTICES.md`.

## Migrations and legacy behavior

The migration graph is:

```text
geography.0001 -> create Department, Province, District
geography.0002 -> load the versioned CSV snapshot without network access
news.0017      -> add temporary nullable normalized foreign keys
news.0018      -> assign Arequipa 04 and NULL district to every legacy row
news.0019      -> remove legacy text fields, rename FKs, finalize constraints
```

The backfill fails closed if department `04` is absent. It does not fuzzy-match
legacy text, infer coverage from School, retain a second source of truth, delete
revisions, or rewrite geography inside pre-ticket revision JSON. A pre-ticket
revision may therefore require an editor to select normalized coverage before
saving it again, as approved by the ticket. Revisions created after the normalized
model is active save and reopen normally.

## Updater

`python manage.py update_peru_geography` downloads the one project-owned official
INEI resource, fully parses and validates it, prints a deterministic summarized
diff, and performs no mutation by default. `--source <local-path>` accepts
controlled XLSX or normalized CSV files and deliberately rejects remote URLs.

Only `--apply` mutates. Application is atomic and idempotent: new codes are
created, official names are updated, reappearing codes are reactivated, missing
codes are marked inactive, and existing rows are never deleted. Duplicate codes,
malformed hierarchy, orphans, unexpected parent changes, inaccessible sources,
and parsing errors fail before writes; database failures roll back the complete
application.

The updater is not called by migrations, startup, requests, Docker entrypoints,
bootstrap, deployment, or search-index rebuilds. CI and browser tests use only
the versioned snapshot or controlled local fixtures.

## Public and editor contracts

- Editor fields: `Departamento *` and optional `Distrito`; Province is internal.
- Lookup: `GET /geografia/distritos/?departamento=04&buscar=are`.
- Archive parameters: `departamento=<2-digit-code>` and
  `distrito=<6-digit-code>`; district links always include department context.
- Department filters include department-only and district-specific coverage.
- District filters match exact coverage and exclude department-only coverage.
- School location and NewsPage coverage can intentionally differ.
- Geography selectors are eager-loaded by the public-news selector; lookup is
  department-first and bounded. No cache, Redis, or complete initial district
  option list was introduced.

## Automated validation

Completed validation during implementation:

- official-source preflight: approved resource resolved; XLSX structure,
  checksum, hierarchy, 25/196/1,892 counts, absence of orphans/duplicates, and
  Arequipa code `04` verified;
- focused geography, editor, browser-fixture, and public rendering tests:
  63 passed before entering the historical migration module;
- complete historical migration suite: 22 passed;
- focused Playwright archive scenario: passed;
- focused Playwright School/News dependent-geography scenario: passed;
- Docker-first Ruff formatting and lint: passed;
- maintainer UAT: all 12 approved areas passed on 2026-08-15.

Final `make migration-check`, `make check`, complete `make browser-test`, coverage,
`git diff --check`, and maintainer UAT results are recorded at technical close
below.

## Failure disposition

- An initial direct pytest invocation omitted the repository test settings and
  produced manifest/configuration errors. The Docker-first invocation with
  `config.settings.test` classified this as an invocation error; application
  tests then ran normally.
- Historical migration tests initially lost data-migration rows because
  pytest-django flushes transactional tests while migration recorder entries
  remain applied. The migration-test helper now restores the versioned UBIGEO
  snapshot under that test-only condition, matching its existing bootstrap-data
  repair responsibility.
- Several older migration tests instantiated the current runtime model against
  deliberately historical schemas. They now use migration-state models and only
  use runtime revision reconstruction after returning to the latest schema.
- Browser failures were classified from rendered roles/DOM and server evidence:
  strict locators matched Wagtail panel anchors as well as controls, a detail link
  also appeared in global navigation, and the new detail fixture initially
  altered an established archive taxonomy count. Locators are now scoped to the
  owned form controls/article and the fixture uses an independent taxonomy path.
- The dependent widget initially initialized before Wagtail had rendered the
  snippet form. Initialization is now DOM-ready and idempotent; the focused
  School and News coverage workflow passes.

No product behavior was bypassed with forced locators, arbitrary sleeps, skipped
tests, or weakened server-side validation.

## Maintainer UAT

Maintainer UAT passed on 2026-08-15.

The maintainer completed all 12 approved UAT areas successfully:

1. School with department only.
2. School with department and district.
3. NewsPage coverage with department only.
4. NewsPage coverage with department and district.
5. Server-side rejection of a manipulated incompatible district.
6. School location differing intentionally from NewsPage coverage.
7. Public archive filtering by department.
8. Public archive filtering by exact district.
9. Geography combined with search, taxonomy, tag, and ordering.
10. Pagination preserving active territorial criteria.
11. Public detail navigation through department, district, section, subsection,
    and existing tag links.
12. Updater dry-run, explicit apply, restoration, and idempotence against the
    reviewed local fixture.

No maintainer UAT finding required an implementation correction. The UAT did not
apply an unreviewed live INEI download to staging.

## Warnings and known limitations

- License not explicitly stated on the selected INEI publication/resource.
- Pre-ticket revision geography is intentionally not normalized precisely.
- The dated snapshot must never be silently replaced after a migration references
  it; a reviewed future snapshot needs a new filename and migration.
- The default updater performs a live official-source read only when an operator
  invokes the command; availability or upstream format changes can make the check
  fail closed.

## New Work Discovered

`GEO-OPS-001 — Automate periodic UBIGEO update checks`

Future production scope: run `update_peru_geography` monthly in check-only mode,
alert on a diff or failure, and never auto-apply. Use the smallest scheduler
already present at implementation time; do not introduce Celery solely for this
job. Any territorial application continues to require human review and explicit
`--apply`.

## Technical close

- `make migration-check`: passed, no model changes detected.
- `make check`: passed with 491 tests and all lint/migration gates green.
- Coverage: 90.09%, satisfying the configured 90% gate.
- `make browser-test`: passed all 8 Chromium scenarios.
- Focused migration suite: 22 passed.
- Focused dependent-geography Playwright scenario: passed.
- Focused public archive Playwright scenario: passed.
- `git diff --check`: passed before the final handoff artifact generation and
  rerun after the documentation result update.
- Maintainer UAT: passed, 12/12 approved areas completed successfully.
- No EPIC8-005, Caddy, Fail2ban, staging-security, deployment-ordering, or
  production files were changed.
