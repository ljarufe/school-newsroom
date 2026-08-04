# EPIC5-009 Implementation Feedback

Status: Implementation Closing Draft

## Outcome

EPIC5-009 adds an ordered, revision-aware `NewsPageRelatedKeyphrase` relation,
an in-process Spanish spaCy boundary, conservative lemma matching, structured
evidence, and the related-keyphrase Wagtail workflow. Existing exact checks and
the overall SEO state remain authoritative and unchanged. No findings or
evidence are persisted, and no external NLP service or runtime download was
introduced.

The Director/editor retains the complete form. Curador SEO receives only the
existing authorized SEO fields and the new `related_keyphrases` formset. Tests
cover manipulated POST attempts against body, taxonomy, minor privacy fields,
contributors, credits, and navigation settings. Wagtail comments JavaScript is
not loaded when its formset has been removed by this role boundary.

## Dependencies, licenses, and reproducibility

- spaCy: `3.8.14`, MIT.
- `es_core_news_sm`: `3.8.0`, GNU GPL v3.0, explicitly accepted for this
  project.
- Click: `8.4.2`, BSD-3-Clause. It is a direct workaround because spaCy 3.8.14
  imports Click while the previous resolved dependency graph did not install it.
- Official model wheel:
  `https://github.com/explosion/spacy-models/releases/download/es_core_news_sm-3.8.0/es_core_news_sm-3.8.0-py3-none-any.whl`.
- Wheel SHA-256:
  `e451a83d6df79b87e9eed0cb553f03e99e36a3bab18a7b79f0dcfd1fdf875e12`.
- Installation is reproducible through exact requirements and a direct wheel
  URL with a hash. The normal Docker build installs all three artifacts and
  performs the real model smoke. It never runs `spacy download`.
- Separate notices, sources, versions, and licenses are recorded in
  `THIRD_PARTY_NOTICES.md`; spaCy's MIT license is not attributed to the model.

The active pipeline components are `tok2vec`, `morphologizer`, `parser`,
`attribute_ruler`, and `lemmatizer`. `ner` is explicitly excluded. Although the
model publishes `senter`, it is not active in the loaded default pipeline;
sentence boundaries are supplied by the parser and were verified together with
lemma, POS, morphology, and dependency annotations.

## NLP architecture and behavior

`apps.news.seo.nlp` owns device selection, lazy loading, component and
annotation validation, process-local success/failure caching, bounded logging,
inference, and conversion to immutable project-owned token structures. No
spaCy `Doc`, `Span`, or `Token` reaches rules or templates. A failed load is
logged once and is not retried in that process. An inference failure does not
discard a pipeline that was loaded successfully.

`apps.news.seo.content` supplies ordered `ContentSegment` values for public and
effective SEO titles, description, headings, paragraphs, lists, quotes, tables,
and contextual image alt text. The slug remains available only through the
legacy exact snapshot. `apps.news.seo.linguistics` performs contiguous,
order-preserving surface/lemma matching and produces project-owned findings.
No public API was added to `apps.news.seo`; `analyze_page` remains the integration
entry point.

The introduction is the first 100 significant body tokens. Distribution applies
from 300 significant body tokens and divides body positions into three
testable approximate zones. Two or more occurrences in at least two zones are
good; two or more in one zone need improvement; one is informative; shorter
content is not applicable. New flexive and related findings never affect the
overall state.

Observed model limitations were kept visible in the test record. Conservative
contiguous matching rejected reordered words, a synonym, and non-contiguous
tokens as intended, with no false positives in the causal fixtures. The small
Spanish model did not assign compatible lemmas to the gender pair
`reportero`/`reportera`, producing an observed false negative. Tests therefore
do not claim general linguistic precision.

## Model, migration, revisions, and workflow

Migration `news.0015_newspagerelatedkeyphrase_and_more` creates the ordered
ParentalKey relation and updates visible field metadata. Historical pages
migrate with zero related phrases. The migration does not synthesize data and
does not change published migrations.

Modelcluster revisions serialize phrases and order. Automated coverage verifies
zero-to-four effective rows, whitespace deletion, normalized duplicate rules,
save/reopen, ordered revision reconstruction, and a revert-style reconstruction
from an earlier revision. The browser fixture saves and reopens related phrases
on a page in the real SEO workflow. No migration was applied to the maintainer's
persistent database.

## Degradation and privacy

Missing/incompatible models and inference failures preserve legacy exact
analysis and editing behavior, emit one visible Spanish warning for the
response, and avoid HTTP 500 errors. Text above `SEO_NLP_MAX_CHARACTERS`
(default `50000`) is not truncated; advanced findings become unavailable and a
distinct warning is shown. Logs contain model/error class identifiers only,
never article text or evidence. No content leaves the application process.

## Performance and architecture evidence

Measurements were taken in one normal `web` container on CPU with Python
`3.12.13`, architecture `x86_64`, spaCy `3.8.14`, and model `3.8.0`:

| Measurement | Observed value |
| --- | ---: |
| Cold import/load plus first small inference | 0.4953 s |
| RSS before load | 85.31 MiB |
| RSS after load | 207.18 MiB |
| Approximate RSS increase | 121.87 MiB |
| Median full linguistic analysis, 300 words (3 runs) | 0.0102 s |
| Median full linguistic analysis, 1,000 words (3 runs) | 0.0331 s |
| Median full linguistic analysis, 3,000 words (3 runs) | 0.1044 s |
| Configured/active device | `cpu` / `cpu` |
| Observed pipeline load count | 1 |

The normal amd64 image built and the real smoke passed on `x86_64`. An explicit
binary-only Python 3.12 resolution downloaded the published
`spacy-3.8.14-cp312-cp312-manylinux2014_aarch64.manylinux_2_17_aarch64.whl`;
the approved model wheel is architecture-neutral (`py3-none-any`). Actual ARM64
execution remains deferred to the authorized staging deployment ticket, as
required.

These measurements do not justify result caching for EPIC5-009. The model is
already cached once per process and measured warm latency is small relative to
an Admin save/reload. EPIC5-010 should reuse the structured segments and loaded
pipeline, measure its own added rules, and revisit result caching only if its
broader analysis materially changes request cost. The roughly 122 MiB per-process
model footprint should be included in future worker-count capacity decisions.

## Automated validation

- Normal `docker compose build web`: passed. The first build exposed that
  `senter` is published but inactive; the durable smoke now validates semantic
  sentence annotations instead of incorrectly requiring that optional pipe.
- Explicit clean smoke: passed for `import spacy`, `spacy.load` with `ner`
  excluded, all required annotations, and `pip check` (`No broken requirements
  found`).
- Migration check: passed with no missing migrations.
- Focused close: 23 passed.
- `make browser-test`: 4 passed. It exercises the real inline
  add-four/fifth-limit/reorder/delete/save/reopen flow, exact and flexive
  findings, unauthorized body/taxonomy absence, and zero page errors. Separate
  editor and SEO workflow pages prevent cross-scenario workflow locking.
- Final `make check`: passed Ruff, migration check, and all 337 pytest tests in
  48.32 seconds.
- Final `git diff --check`: passed after the stable documentation delta.

Earlier browser failures were classified before retrying: one test deleted the
row it had just moved; sharing a workflow page made historical editor scenarios
read-only; and Wagtail loaded comments JavaScript after the restricted form had
removed its comment formset. The final fixture uses separate pages, and the
form's comments media follows the effective formset boundary.

## Maintainer UAT and approved UI addendum

The complete required maintainer UAT is approved. Luis reported: “Delta-UAT A,
B y C aprobadas sin desviaciones.” The original relationship, ordering,
persistence, and permission behavior had no reported deviation. This records
only the completed ticket UAT; it does not attribute broader browser, role, or
deployment validation to Luis.

The approved ticket was not rewritten. The custom `Contexto de la noticia —
solo lectura` panel was removed as a deliberate maintainer product decision:
the authorized Curador SEO role can inspect the complete article through
Wagtail's native Preview. Full article content is therefore readable through
authorized native Preview, while body, taxonomy, privacy, credits, and
collaborators remain unavailable for editing by Curador SEO.

- Delta-UAT A approved removal of that redundant custom panel, confirmed that
  `Configuración SEO` is the first section, and confirmed that native Preview
  remains available to Curador SEO without making restricted editorial fields
  editable.
- Delta-UAT B approved normal linguistic results on `localhost:8000`, including
  flexive variants, locations, distribution, and bounded evidence.
- Delta-UAT C approved controlled degradation: exact-analysis continuity,
  save/reload without HTTP 500, one failed model load per process, bounded
  logs, disposable-container cleanup, and preservation of the normal service.

The original UAT 2 described linguistic concepts but did not name the exact
Admin panels, states, labels, and evidence to inspect. The completed delta UAT
made those visible checks explicit. All content in the reference scenario below
is fictional and safe to copy.

### UAT 1: revision-aware relation

Use Curador SEO at `Wagtail Admin -> Páginas -> noticia ficticia -> Asistente
SEO`.

- Principal: `periodismo escolar`
- Related, in order: `investigación escolar`, `noticia escolar`, `jóvenes
  reporteros`, `redacción periodística`
- Fifth attempt: `cobertura estudiantil`
- Normalized duplicate attempt: `  PERIODÍSMO   ESCOLAR  `

Verify the four-row limit, duplicate error, order, delete/re-add, and
save/reopen behavior.

### UAT 2: exact, flexive, and distribution

Use the same principal and related values, then create the following fictional
article as separate Wagtail blocks. It exceeds 300 words and deliberately
contains headings and a list.

**Title:** Laboratorio ficticio de periodismo escolar abre sus cuadernos

**Paragraph:** El periodismo escolar comenzó el lunes con una reunión inventada
en la biblioteca del colegio Horizonte. Una investigación escolar propuso
observar cómo circulan las noticias escolares dentro de una comunidad imaginaria,
sin entrevistar a personas reales ni registrar datos personales. Los jóvenes
reporteros prepararon preguntas, compararon formatos y acordaron que la
redacción periodística debía explicar cada decisión con claridad. Durante esa
primera sesión, otra práctica de redacción periodística consistió en separar los
hechos ficticios de las opiniones del equipo.

**H2:** Un método sencillo para una historia inventada

**Paragraph:** Para ensayar, el grupo dibujó un mapa de fuentes completamente
ficticias: una cartelera azul, una radio que sólo existe en el ejercicio y un
club de lectura creado para la nota. Los periodismos escolares de tres talleres
imaginarios sirvieron como comparación gramatical, no como referencia a centros
reales. Cada estudiante revisó fechas inventadas, marcó dudas y anotó qué dato
necesitaba una segunda comprobación. Nadie publicó nombres, fotografías,
horarios personales ni información que permitiera identificar a menores.

**List:**

- Confirmar que cada lugar, persona y cifra del ejercicio sea ficticio.
- Distinguir una observación comprobable de una interpretación editorial.
- Escribir un título claro y una descripción breve antes de guardar.
- Revisar la evidencia mostrada por el asistente sin convertirla en una orden.

**H3:** Del cuaderno al borrador

**Paragraph:** Después del recreo simulado, el equipo transformó sus notas en
cuatro párrafos. Primero describió el propósito del laboratorio; luego explicó
el método; más tarde comparó dos posibles estructuras; finalmente añadió un
cierre. La docente ficticia recordó que una herramienta lingüística puede
reconocer variaciones de número o género, pero no decide si una historia es
verdadera, justa o relevante. Por eso el grupo leyó el texto en voz alta,
contrastó cada afirmación y corrigió una secuencia que alteraba el sentido.

**H2:** Hallazgos del ensayo

**Paragraph:** En la segunda mitad del ejercicio, la investigación escolar
apareció de nuevo para resumir el proceso. Las noticias escolares también
regresaron en una sección distinta, de modo que el panel pudiera mostrar una
variante flexiva distribuida. El grupo observó que una coincidencia exacta y una
predicción por lema se presentan por separado. También comprobó que una frase
presente una sola vez recibe una orientación diferente de otra repetida en
varias zonas. Ninguna recomendación sustituyó la revisión humana ni cambió por
sí sola el estado general de la nota.

**Paragraph:** Al cerrar la jornada ficticia, el equipo volvió a nombrar el
periodismo escolar como práctica de aprendizaje. Guardó el borrador, recargó la
página y revisó ejemplos abreviados, ubicaciones y distribución. Después anotó
dos mejoras para la próxima sesión: redactar transiciones más naturales y
explicar mejor el origen de cada cifra inventada. El ejercicio terminó sin
publicación real, sin servicios externos y sin información de estudiantes.

Expected signals include exact `periodismo escolar`, flexive `periodismos
escolares`, exact and distributed `investigación escolar`, flexive-only and
distributed `noticia escolar` through `noticias escolares`, one occurrence of
`jóvenes reporteros`, and two first-zone occurrences of `redacción periodística`.
Save and reload before checking findings.

### UAT 3: controlled degradation

The original disposable-degradation instruction had not been validated as a
complete startup procedure: it did not explicitly invoke Django through
`runserver ... --noreload`. Its first disposable attempt failed while Docker
published the host port, before Django or the NLP pipeline started, so it
provided no application-level evidence.

During the final preflight, port 8001 was occupied on `127.0.0.1` by a VS Code
`code` process (PID 34718). That external process was not stopped. This explains
the observed final port conflict and is compatible with the earlier conflict,
but does not prove that the same PID owned the port during the historical
attempt. After checking port availability and leaving the normal `web` service
undisturbed, the approved UAT used free port 8002:

```bash
docker compose run --rm \
  --name school-newsroom-epic5-009-degradation \
  -p 8002:8000 \
  -e SEO_NLP_MODEL=missing_test_model \
  web python manage.py runserver 0.0.0.0:8000 --noreload
```

This validated HTTP 200, one visible warning, retained legacy exact analysis,
successful save/reload, no page errors, exactly one bounded model-load failure
log, and removal of the disposable container.

## Normal-runtime UAT root cause and resolution

The previous running `web` container used a Dev Container image built before
spaCy and the Spanish model were added. Effective NLP settings were correct,
but `import spacy` failed with `ModuleNotFoundError`. This was an image/process
lifecycle problem, not a defect in the NLP implementation.

The corrected normal-runtime command was:

```bash
docker compose up -d --build --force-recreate web
```

The rebuilt image and active container were verified to match. spaCy 3.8.14,
`es_core_news_sm`, and the required linguistic components loaded inside that
exact running container. The real normal-runtime smoke produced exact and
flexive matches, zone distribution, a maximum of three evidence fragments, one
pipeline load, and no warning. A failed model load is cached per process, so
the failed process must be recreated or restarted after correcting its image.

## Closing state

- Maintainer UAT: approved; no maintainer UAT remains pending.
- Pending real commit.
- Pending real push.
- Pending PR/CI evidence.
- Pending PR review.

## Warnings, known issues, and New Work Discovered

- Existing Treebeard `E001` forward-compatibility warnings remain visible in
  Django system checks. They predate and are unrelated to EPIC5-009.
- Real ARM64 execution and staging UAT are deferred to an authorized deploy.
- The small model's `reportero`/`reportera` false negative is documented; a
  larger model or heuristic expansion is not recommended without a separate
  measured ticket.
- New Work Discovered: future capacity planning should account for the measured
  per-worker RSS increase. No blocking defect or immediate follow-up feature was
  discovered.

## Durable process and source learnings

- Validate required linguistic annotations, not every component advertised in
  model metadata; parser-provided sentence boundaries make inactive `senter`
  valid in this pipeline.
- Browser fixtures for role-specific workflow stages need separate pages so one
  task lock cannot invalidate another role's scenario.
- Wagtail form media must follow the effective instance formset boundary when a
  permission layer removes relations after form-class construction.
- Keep exact and linguistic analysis in separate derived paths so local NLP can
  fail without changing the established SEO contract.
- Editorial/privacy source candidate: Curador SEO may read the complete article
  through authorized native Preview while remaining unable to edit restricted
  editorial fields.
- Technical source candidate: spaCy and `es_core_news_sm` are image
  dependencies; after dependency changes, rebuild and recreate the actual web
  runtime before UAT.
- Execution-guide candidate: visible Admin UAT must name exact panels, labels,
  states, and evidence.
- Execution-guide candidate: disposable server tests must preflight the host
  port, explicitly start the intended server boundary, and disable autoreload
  when validating per-process caching.
- Execution-guide candidate: distinguish Docker or network startup failure from
  an application or NLP failure.
