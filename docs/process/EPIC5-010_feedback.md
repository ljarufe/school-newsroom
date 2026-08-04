# EPIC5-010 Stage A Feedback

## Stage A status

Implementation and automated validation are complete. This file records
technical evidence produced by Codex. Maintainer UAT is pending and is not
claimed as passed.

## Implementation structure

- `apps.news.seo.content` remains the single StreamField extraction boundary.
  Its existing ordered `ContentSegment` snapshot is reused without reparsing.
- `apps.news.seo.nlp` continues to own lazy spaCy loading and inference. Its
  immutable `NlpToken` now also exposes the project-owned token index,
  dependency label, head index, sorted morphology features, sentence
  membership, and the ticket's shared word flag. Immutable `NlpSentence`
  values expose character and token boundaries. No spaCy object leaves this
  module.
- `apps.news.seo.linguistics` remains the orchestration boundary. Keyphrases
  and all ordered segments are sent through one `pipeline.pipe` batch, and the
  same immutable analyzed segments feed the advanced rules.
- `apps.news.seo.advanced_readability` owns the fixed connector lexicon,
  advanced rule formulas, immutable findings and evidence, Spanish
  hyphenation initialization, and its process-local success/failure cache.
- `apps.news.seo.analysis` adds `advanced_readability_checks` to the aggregate
  result while preserving the established `readability_checks` and overall
  status calculation.
- `seo_assistant_panel.html` renders a separate `Legibilidad avanzada` card.
  The original `Legibilidad` card and its template contract remain unchanged.

The new immutable result types are `AdvancedReadabilityFinding` and
`AdvancedReadabilityEvidence`. A finding contains a stable ID, status, title,
explanation, human-readable metric, optional unrounded numeric value, at most
three evidence items, and derived locations. Evidence contains bounded text,
the block location, and an optional local metric.

## Authorized input and exclusions

Advanced denominators contain only visible `paragraph`, `list`, and `quote`
segments from `body`. Headings remain ordered segment boundaries but their
words are excluded. Public and SEO titles, meta description, slug, tables,
image alt text, captions, credits, embeds, taxonomy, tags, school and coverage,
public credits, internal contributors, privacy fields, and hidden Admin data
are excluded. Each segment is a separate spaCy document, so a sentence cannot
cross segments.

A word is an NLP token that contains at least one Unicode letter, contains no
digit, and is neither whitespace nor punctuation. Content tokens are words
whose POS is `ADJ`, `ADV`, `NOUN`, `PROPN`, or `VERB`.

## Basic readability characterization

Before editing, 8 focused existing tests passed in the Docker runtime. The
stable basic order is:

1. `Texto del artículo`
2. `Longitud de párrafos`
3. `Longitud de oraciones`
4. `Uso de subtítulos`
5. `Bloques de texto`

The existing paragraph boundaries remain 150/250 words, long sentences remain
strictly more than 30 words with existing 25/50 percent status boundaries,
subheadings remain applicable from 300 words, and continuous blocks retain
300/500 boundaries. Existing Spanish copy is unchanged. These five findings
still participate in `Incompleto / Necesita mejoras / Bueno`; advanced
findings do not.

## Advanced rules, formulas, and thresholds

The visible order and stable IDs are:

| ID | Finding | Rule |
| --- | --- | --- |
| `long-sentences` | Oraciones extensas con evidencia | More than 30 words; good through 25%, improve above 25%; visible percent is floored. |
| `consecutive-openings` | Comienzos consecutivos | Run of at least three equal signatures made from the first two normalized content lemmas, or one when only one exists. |
| `connectors` | Uso de conectores | Not applicable below 5 sentences; improve below 10%, informative from 10% to below 20%, good from 20%. |
| `periphrastic-passive` | Pasiva perifrástica | Direct `ser` auxiliary plus verbal participle predicate; zero is good; one or below 10% is informative; at least two and at least 10% needs improvement. |
| `syntactic-complexity` | Complejidad sintáctica | At least three clause heads; not applicable below 3 sentences; zero is good; through 20% is informative; above 20% needs improvement. |
| `lexical-density` | Densidad léxica | Content tokens divided by words; informative from 50 words. |
| `lexical-diversity` | Diversidad léxica | Mean TTR across every consecutive 50-content-lemma window; informative from exactly 50 content tokens. |
| `flesch-szigriszt` | Flesch-Szigriszt e INFLESZ | `206.835 - 62.3 * syllables/words - words/sentences`; gate at 100 words and 3 sentences. |

INFLESZ bands are below 40 `Muy difícil`, 40 to below 55 `Algo difícil`, 55
to below 65 `Normal`, 65 to below 80 `Bastante fácil`, and 80 or more `Muy
fácil`. The unrounded IFSZ value remains in the immutable finding for tests;
the Admin metric displays one decimal and is not clamped. Values below 55 need
improvement, while values from 55 are good for this finding only.

## Fixed connector lexicon

- Addition: `además`, `también`, `asimismo`, `incluso`, `de igual manera`,
  `por otra parte`.
- Contrast or concession: `sin embargo`, `no obstante`, `en cambio`, `por el
  contrario`, `aunque`, `aun así`.
- Cause: `porque`, `ya que`, `debido a`, `puesto que`.
- Consequence: `por eso`, `por lo tanto`, `por consiguiente`, `en
  consecuencia`, `así que`.
- Order or time: `primero`, `en primer lugar`, `después`, `luego`, `más tarde`,
  `finalmente`, `mientras tanto`.
- Explanation or example: `por ejemplo`, `es decir`, `en otras palabras`.
- Conclusion: `en resumen`, `en síntesis`, `para concluir`.

Expressions are normalized with the existing case/accent normalization and
matched as complete token sequences. Longer expressions are tried first. Each
sentence contributes at most once to the ratio even when multiple expressions
or categories are present.

## Real dependency mappings

Inspection used `es_core_news_sm` 3.8.0 in the normal Python 3.12 image. The
accepted `El borrador fue revisado...` mapping was `fue` = `AUX`, lemma `ser`,
dependency `aux`, headed directly by `revisado`; `revisado` = `VERB`,
dependency `ROOT`, morphology includes `VerbForm=Part`. The model mapped
`está revisado` to lemma `estar` plus an `ADJ` root, so it is rejected. It
mapped reflexive `se revisó` to `expl:pv` plus a finite verbal root and no `ser`
auxiliary, so it is rejected. The implementation accepts the model's direct
auxiliary labels `aux` and `aux:pass`, and predicate clause labels listed
below, while still requiring a `VERB` participle.

Clause heads are verbal `ROOT`, `advcl`, `ccomp`, `xcomp`, `acl`,
`acl:relcl`, and verbal `conj` tokens with a `VerbForm` feature. In the causal
model inspection, a three-head sentence mapped to `ROOT + ccomp + advcl`.
A verbal coordination mapped to `conj`; a nominal coordination also mapped to
`conj` but is rejected by the POS requirement. Ordinary `aux` tokens are not
in the clause-head set and do not inflate the count.

## Pyphen and bundled dictionary evidence

- Dependency: `pyphen==0.17.2`.
- Wheel: `pyphen-0.17.2-py3-none-any.whl`.
- Wheel SHA-256:
  `3a07fb017cb2341e1d9ff31b8634efb1ae4dc4b130468c7c39dd3d32e7c3affd`.
- Python metadata: `Requires-Python >=3.9`; installation and import were
  inspected successfully with Python 3.12.
- Pyphen declared alternatives: GPL-2.0-or-later / LGPL-2.1-or-later /
  MPL-1.1. Effective project choice: MPL-1.1.
- `Pyphen(lang="es_ES")` resolves offline through language fallback `es` to
  bundled `pyphen/dictionaries/hyph_es.dic`.
- Dictionary SHA-256:
  `b2e170c3c25f5de25447ca0acf6bc8baf9dd761e228e9646e2c25f2e7c47f4f6`.
- Bundled notice file:
  `pyphen/dictionaries/README_hyph_es.txt`, SHA-256
  `0053b520c70ef49fdaa5beddf9bf4c76fcefb422748601a2f18a33ed923bcf8c`.
- Bundled provenance and authorship: Spanish patterns from
  LibreOffice/Apache OpenOffice, initially developed by Santiago Bosio with
  `patgen` and manually labeled training data.
- Dictionary declared alternatives: GPL-3.0-or-later /
  LGPL-3.0-or-later / MPL-1.1-or-later. Effective project choice: MPL-1.1.

The complete bundled Spanish notice is reproduced in
`THIRD_PARTY_NOTICES.md`. The inspected Pyphen 0.17.2 wheel contains no
MIT-origin attribution for this dictionary. The maintainer corrected that
inaccurate original ticket statement. Current LibreOffice licensing may be
linked as external upstream provenance but is not represented as bundled wheel
content.

## Degradation, privacy, and persistence

- Pipeline load or per-request inference failure produces one existing visible
  linguistic warning and eight unavailable advanced findings. Basic SEO,
  basic readability, overall status, editing, save, workflow, and publication
  remain available.
- Text above `SEO_NLP_MAX_CHARACTERS` is not truncated and produces eight
  unavailable findings for that response.
- Pyphen initialization success or failure may be cached once per process. A
  Pyphen-only failure leaves the first seven findings available and marks only
  Flesch-Szigriszt unavailable.
- Bounded logs contain model/dictionary identifiers and exception classes, not
  article content or evidence.
- No network service or runtime dictionary download is used.
- Results and evidence are derived only. There is no result cache, persistence,
  schema change, or migration.
- Existing Curador SEO form and POST boundaries are unchanged. The card is
  read-only within the already authorized SEO surface and does not expose new
  editable content or minor data.

## Causal and integration tests

The versioned causal test module covers the 30/31-word boundary, exactly and
above 25%, two versus three repeated openings, connector 0/10/20% boundaries,
multiword and single-sentence counting, accepted `fue revisado`, rejected
`está revisado` and reflexive `se`, one passive and two at 10%, two versus
three clause heads, nominal coordination rejection, 49/50-word density,
49/50/more MATTR inputs, exact formula, INFLESZ boundaries, 99/100-word and
sentence gates, authorized/excluded inputs, segment boundaries, evidence order
and limit, immutable NLP data, one inference batch, model/inference failure,
Pyphen-only failure, and unchanged overall status.

The aggregate result keeps the existing seven-position constructor contract;
the additive advanced tuple is a trailing field with an empty default.

Current focused evidence:

- Pre-change basic readability characterization: 8 passed.
- Initial advanced causal run: 39 passed.
- Expanded causal/Admin/permission selection after integration: 44 passed.
- Stable complete focused unit/integration group: 102 passed.
- Stable focused Admin/permission group: 8 passed.
- Rebuilt-image Pyphen-specific test: 1 passed.
- Focused lint and formatter checks for the same delta: passed.
- Normal `make build`: passed on Python 3.12.13. The Dockerfile verified the
  spaCy annotations, exact Pyphen version, offline `es_ES` fallback, installed
  dictionary path, and real `ex-tra-or-di-na-rio` hyphenation.
- Installed-artifact smoke with container networking disabled: passed with the
  expected dictionary and notice hashes.
- `pip check`: passed with `No broken requirements found`.
- Django smoke through the rebuilt image and real entrypoint: passed with the
  five pre-existing Treebeard `E001` forward-compatibility warnings.
- Explicit migration check: passed with `No changes detected`.
- `make browser-test`: 4 passed. The existing Curador SEO regression now also
  verifies the separate advanced card and a visible connector finding with
  status, metric, location, and evidence, while retaining body/taxonomy
  restrictions and zero page errors.
- Final `make check`: passed Ruff, migration check, and all 380 pytest tests in
  48.12 seconds.
- Final review corrections changed the single-run metric from a plural to
  `1 secuencia problemática.` and moved the additive aggregate field to a
  trailing default so the existing positional constructor remains compatible.
  The complete 43-test advanced causal module and focused Ruff/format checks
  passed afterward; no broader evidence was invalidated.

The final diff review includes the complete relevant tracked and untracked
delta. `git diff --check` passed.

## Performance and capacity evidence

Measurements ran in one rebuilt normal `web` container on CPU with Python
3.12.13. Each dataset used exact 300, 1,000, or 3,000 words distributed in
100-word paragraph segments and 20-word parser sentences. spaCy inference was
completed before timing; the measured function was the full advanced-rule
derivation. Each median uses 11 warm samples after one warm-up.

| Measurement | Observed value |
| --- | ---: |
| Advanced-only median, 300 words | 1.222 ms |
| Advanced-only median, 1,000 words | 4.051 ms |
| Advanced-only median, 3,000 words | 12.248 ms |
| RSS immediately before Pyphen initialization | 177,096 KiB |
| RSS after Pyphen initialization | 177,264 KiB |
| Pyphen RSS increment | 168 KiB (0.164 MiB) |
| RSS after advanced executions | 178,068 KiB |
| Combined increment from pre-Pyphen point | 972 KiB (0.949 MiB) |
| Observed spaCy pipeline load attempts | 1 |
| Observed Pyphen initialization attempts | 1 |

EPIC5-009 measured full linguistic pipeline medians of 10.2 ms, 33.1 ms, and
104.4 ms at approximately the same sizes, plus about 121.87 MiB RSS per
process. The new advanced-only medians are approximately 12.0%, 12.2%, and
11.7% of those earlier NLP timings. The corpora differ, so this is a capacity
comparison rather than a combined benchmark. The measured 0.164 MiB Pyphen
increment and sub-1 MiB combined increment do not materially change the
existing recommendation to account primarily for spaCy's roughly 121.87 MiB
per worker. These results do not justify a result cache, worker-count change,
or other infrastructure delta. No SLA is introduced.

The first probe invocation failed before application import because executing
the file under `tmp/` placed `/app/tmp` rather than `/app` on `sys.path`. It
was classified as a probe invocation error, corrected with an explicit
`PYTHONPATH=/app`, and did not invalidate application behavior. A second probe
run added the required post-analysis RSS point; the first partial measurement
was superseded rather than combined with the final evidence. The temporary
probe was removed afterward.

## False positives, false negatives, and threshold recommendations

The causal fixtures confirm conservative rejection of `estar + participle`,
reflexive `se`, and nominal coordination. The exact approved UAT A prose was
also analyzed in a disposable process. It produced the expected 356 words and
15 sentences; the first three `equipo escolar` openings; 10/15 connector
sentences; all five expected passive constructions grouped into three sentence
occurrences; 202 content tokens; MATTR 0.976; and IFSZ 47.5 (`Algo difícil`).

Complexity reported 12/15 sentences. Inspection found that the fixture itself
contains many approved verbal roots, subordinate predicates, and verbal
coordinations; examples such as `reunió / comparó / separó` satisfy the closed
three-head definition. This is a high but explainable result, not evidence for
an incidental threshold adjustment. No false positive or false negative was
observed in the approved passive examples. Small-model false negatives remain
possible by design, and the rule deliberately prefers them to weak `se` or
text-ending heuristics.

No approved threshold was changed. There is currently no evidence to add any
advanced finding to the overall status; that remains out of scope and should
be reconsidered only in a later calibrated ticket after editorial UAT and a
larger representative corpus.

## UAT

Maintainer UAT A-D is pending. The UAT A analysis described above is automated
calibration only and is not attributed to Luis. Runtime inspection found the
real Compose services `db` and `web`; only the persistent `db` service was
running. To rebuild the image and recreate only the real `web` service before
UAT, Luis must run:

```console
docker compose up -d --build --no-deps --force-recreate web
```

Codex did not run that command, replace or stop a persistent UAT web runtime,
apply migrations, or modify the maintainer's persistent database.

## New Work Discovered

The Django system check continues to report five pre-existing Treebeard `E001`
forward-compatibility warnings. They are unrelated to advanced readability and
were not implemented in this ticket. No other out-of-scope product work was
identified.

## Maintainer-approved addendum: Treebeard compatibility

After Stage A, the maintainer explicitly approved resolving the five recurring
`treebeard.E001` warnings on this branch. This addendum supersedes only the
Treebeard item recorded under New Work Discovered; the earlier entry remains as
the historical Stage A observation.

The installed dependency set was Django 5.2.16, Wagtail 7.4.2, and
django-treebeard 5.3.0. Treebeard 5.3 checks every materialized-path model's
default manager in preparation for Treebeard 6. Wagtail 7.4.2 defines
`BasePageManager` and `BaseCollectionManager` from Django's `Manager`, not
`MP_NodeManager`; the generated page manager therefore produced four warnings
for Wagtail's base and project page models, and the generated collection
manager produced one. The managers were Wagtail-owned, so changing project
page managers could not truthfully correct the base Page and Collection
warnings without monkey-patching third-party code.

Wagtail 7.4.2 declares support for `django-treebeard>=4.8,<6.0`.
`django-treebeard>=5.2,<5.3` is now a direct compatibility constraint: the 5.2
series supports Python 3.12 and requires Django 5.2, retains the manager and
tree behavior supported by this Wagtail release, and predates the Treebeard 6
forward check. The rebuilt Python 3.12 image resolved django-treebeard 5.2.2
while retaining Django 5.2.16 and Wagtail 7.4.2. `pip check` reported no broken
requirements. No Wagtail or Django upgrade, manager override, suppressed
check, third-party patch, page-tree data change, schema change, or migration
was introduced.

A focused regression asserts the resolved 5.2 series, path ordering for the
Wagtail Page and Collection managers, the Page manager's `specific` queryset
API, and absence of `treebeard.E001` from Django's check registry. Existing
affected page/model tests continue to exercise root lookup, child creation,
tree traversal, manager queries, and public rendering.

Addendum validation:

- Focused Ruff and format checks for the three changed Python files: passed.
- Normal image build: passed and resolved django-treebeard 5.2.2.
- Complete advanced-readability causal module plus affected model, home-page,
  and public-rendering tests: 107 passed under `config.settings.test`.
- Real `python manage.py check`: `System check identified no issues (0
  silenced).`
- `pip check`: `No broken requirements found.`
- Explicit migration check: `No changes detected`.
- Addendum-authorized `make check`: Ruff and migration checks passed; all 384
  tests passed in 48.19 seconds.

The first sandboxed build invocation stopped before Docker evaluated the
project because Buildx could not write its activity metadata under the
read-only sandbox. The approved out-of-sandbox retry passed. The first focused
test invocation used Compose's local settings, so 29 rendering cases failed
because the newly built development image had no collected static manifest;
the advanced and model cases in that invocation passed. The same focused set
was rerun once with the repository's `config.settings.test` setting and all 107
tests passed. Neither failure indicated an application or dependency defect.
