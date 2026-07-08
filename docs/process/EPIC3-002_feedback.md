# EPIC3-002 Feedback
**Status:** Implementation Closing Draft

## Implementation Summary

EPIC3-002 adds internal minor contributor tracking, editor-controlled public
credits, and conservative publication safeguards for identifiable minors.

The implementation keeps internal contributor records separate from public
credits. Public templates render only `NewsPagePublicCredit.display_name`; they
do not render `MinorContributor.full_name`, age bands, internal contribution
relations, or privacy flags.

No student, guardian, teacher, monitor, consent-document, public author profile,
custom permission, custom workflow, write API, encryption, deploy, CI, or
geography-normalization feature was added.

## Initial Repository State

- Branch: `EPIC3-002-minor-contributors-public-credits-privacy`.
- Initial `git status --short`: clean.
- Top-level `AGENTS.md` was read before editing.
- Ticket source was read from
  `~/Downloads/EPIC3-002_registro_interno_colaboradores_autoria_publica_privacidad_menores.md`.
- Current `docs/process/EPIC3-001_feedback.md` and
  `docs/editorial/guia_de_uso.md` were read before implementation.
- `apps.news` migration graph started at:
  `0001_initial` and `0002_bootstrap_editorial_data`.
- `apps.news` models initially included `NewsSection`, `School`, `NewsPage`,
  and `NewsPageTag`.
- The Home query initially selected related section, school, and featured image,
  but did not prefetch public credits because they did not exist yet.

## Models And Fields Added

- `ContributorGroup`
  - `name`
  - `school`
- `MinorContributor`
  - `full_name`
  - `group`
  - `age_band`
- `NewsPageContributor`
  - `page`
  - `contributor`
  - inherited `sort_order` from `Orderable`
- `NewsPagePublicCredit`
  - `page`
  - `display_name`
  - inherited `sort_order` from `Orderable`
- `NewsPage`
  - `contains_identifiable_minors`
  - `minor_publication_authorizations_verified`
  - `sensitive_content`

`MinorContributor` does not duplicate `School`. Its school is derived through
`MinorContributor.group.school`, preserving one source of truth for the group
and avoiding a later mismatch between a contributor's group and school.

The final `age_band` values are:

- `under_14`: `Menor de 14 años`
- `14_to_17`: `De 14 a 17 años`

No date of birth, exact age, DNI, email, phone, address, guardian data,
signature, PDF, image authorization, or contact field was added.

## Relationship Policies

- `ContributorGroup.school` uses `on_delete=PROTECT` so a school used by an
  internal contributor group cannot be silently removed.
- `MinorContributor.group` uses `on_delete=PROTECT` so contributor records
  cannot be orphaned by deleting their group.
- `NewsPageContributor.page` and `NewsPagePublicCredit.page` use
  `ParentalKey(..., on_delete=CASCADE)` as Wagtail/modelcluster child objects of
  `NewsPage`.
- `NewsPageContributor.contributor` uses `on_delete=PROTECT` so a contributor
  referenced by a page cannot be silently removed.

Duplicate contributors on the same page are protected in two layers:

- the generated Wagtail/modelcluster `internal_contributors` inline formset
  rejects duplicate `page` + `contributor` rows during Admin form validation;
- `unique_together = [("page", "contributor")]` on `NewsPageContributor`
  remains the persistence-level database backstop.

## Wagtail Admin Integration

- `ContributorGroup` and `MinorContributor` are registered in the existing
  `Editorial` snippet group.
- The final Admin destinations are:
  - `Secciones editoriales`
  - `Colegios`
  - `Grupos de colaboradores`
  - `Colaboradores menores`
- `NewsPage.content_panels` now includes:
  - `InlinePanel("public_credits", label="Firma pública")`
  - `InlinePanel("internal_contributors", label="Colaboradores internos")`
  - `MultiFieldPanel(..., heading="Privacidad de menores")`
- All new model labels, help text, panel labels, and validation errors in the
  changed surface are Spanish.

## Deferred Validation

The custom page form is `NewsPageAdminForm` in `apps/news/forms.py`.
`NewsPage.base_form_class` points to this form.

Source inspection in the running Docker environment confirmed:

- Wagtail version is `7.4.2`.
- `WagtailAdminPageForm` extends Wagtail's cluster model form stack.
- Generated page forms expose child inline formsets through `self.formsets`.
- The generated `NewsPage` formsets are keyed by `comments`,
  `internal_contributors`, and `public_credits`.
- `defer_required_fields()` sets `is_deferred_validation = True`.

Because Wagtail/modelcluster runs the parent form `clean()` before child formsets
in the default `ClusterForm.is_valid()` flow, `NewsPageAdminForm.clean()`
explicitly calls `self.formsets["public_credits"].is_valid()` before inspecting
submitted public credit forms.

Full validation counts an effective public credit when a submitted
`public_credits` form:

- is present in the real generated inline formset;
- is not marked for deletion according to the formset delete flag;
- has a non-blank `display_name` after stripping whitespace.

This means:

- a new unsaved inline public credit submitted in the same form counts;
- a public credit marked for deletion does not count;
- an empty inline row does not count.

Draft validation returns early when `is_deferred_validation` is true. Drafts can
therefore be saved without public credits or authorization confirmation.

## Publication Rules Implemented

Full validation blocks when:

- there is no effective public credit;
- `contains_identifiable_minors` is true and
  `minor_publication_authorizations_verified` is false.

Full validation does not block when:

- `contains_identifiable_minors` is false and the authorization checkbox is
  false;
- `sensitive_content` is true but the other rules are satisfied;
- internal minor contributors exist but `contains_identifiable_minors` is false.

The final Spanish validation messages are:

- `Añade al menos una firma pública antes de publicar la noticia.`
- `Confirma que se verificaron las autorizaciones requeridas para los menores identificables antes de publicar la noticia.`

## Normative Notice

The Admin privacy panel includes a Spanish informational notice that references
articles 22 to 25 of the Reglamento de la Ley N.º 29733, distinguishes minors
under 14 from adolescents aged 14 to 17, and states the conservative project
policy that public exposure of any identifiable minor requires editorial
verification of required authorizations.

The notice says it does not replace professional legal review.

The linked official URL is:

```text
https://diariooficial.elperuano.pe/Normas/obtenerDocumento?idNorma=23
```

The link is rendered with `target="_blank"` and
`rel="noopener noreferrer"`. The application does not make backend/runtime
requests to that URL.

## Public Rendering

Home now prefetches ordered public credits:

```python
Prefetch(
    "public_credits",
    queryset=NewsPagePublicCredit.objects.order_by("sort_order"),
)
```

Home and news detail render all public credit display names in editorial order,
separated with semicolons.

Neither Home nor detail loads or renders internal contributors. Tests assert the
absence of internal contributor names, `under_14`, `14_to_17`,
`contains_identifiable_minors`,
`minor_publication_authorizations_verified`, and `sensitive_content` in public
responses.

Existing or historical `NewsPage` rows without public credits continue to render
without error and without fabricated author text.

## Migrations

EPIC3-002 adds:

```text
apps/news/migrations/0003_newspage_contains_identifiable_minors_and_more.py
```

No changes were made to:

```text
apps/news/migrations/0001_initial.py
apps/news/migrations/0002_bootstrap_editorial_data.py
```

The new migration adds the three `NewsPage` boolean fields with `False`
defaults and creates `ContributorGroup`, `MinorContributor`,
`NewsPagePublicCredit`, and `NewsPageContributor`.

No data migration creates contributors, public credits, authorization
verifications, or sensitive-content flags.

The migration test creates a historical fictional `NewsPage` from the
`news.0002` schema, applies `news.0003`, and verifies:

- the page survives;
- all three new flags are false;
- zero public credits are fabricated;
- zero internal contributor rows are fabricated.

## Automated Validation

- Focused test command:
  `docker compose run --rm web sh -c "DJANGO_SETTINGS_MODULE=config.settings.test pytest apps/news/tests/test_forms.py apps/news/tests/test_models.py apps/news/tests/test_public_rendering.py apps/news/tests/test_admin_uat.py apps/news/tests/test_migrations.py -q"`
  - Result: `52 passed`.
- Full news test command:
  `docker compose run --rm web sh -c "DJANGO_SETTINGS_MODULE=config.settings.test pytest apps/news/tests -q"`
  - Result: `58 passed`.
- `make lint`
  - First run failed on import ordering, two long lines, and one Django model
    method-order style issue.
  - Root cause: new imports and long Spanish help text/test setup lines had not
    been formatted after implementation.
  - Durable fix: split long strings/lines, moved `MinorContributor.__str__`
    before the custom property, and used Ruff's safe import fixer for two import
    blocks.
  - Final result: passed, `All checks passed!`.
- `make migration-check`
  - First direct run failed with Docker API permission denied from the sandbox.
  - Root cause: sandboxed command could not access the Docker socket.
  - Retry disposition: reran the same Makefile target with approved escalation.
  - Final result: passed, `No changes detected`.
- `make check`
  - Result: passed.
  - Ruff: `All checks passed!`.
  - Migration drift: `No changes detected`.
  - Pytest: `67 passed`.
- Focused EPIC3-002 review correction validation:
  `docker compose run --rm web sh -c "DJANGO_SETTINGS_MODULE=config.settings.test pytest apps/news/tests/test_forms.py apps/news/tests/test_models.py -q"`
  - Result: `27 passed`.
- Review correction `make check`
  - Result: passed.
  - Ruff: `All checks passed!`.
  - Migration drift: `No changes detected`.
  - Pytest: `68 passed`.
- `git diff --check`
  - Result: passed.

### Translation Delta Validation

A focused Spanish Admin translation correction was applied after maintainer UAT
identified two adjacent Wagtail validation strings still rendered in English.

Project gettext overrides were added for:

* `The page could not be saved due to validation errors.`
* `Go to the first error`

The compiled project catalog was regenerated with `make compilemessages`.

The focused language tests passed, the final `make check` passed, and
`git diff --check` passed after the translation delta.

## Manual Validation

Luis completed the EPIC3-002 browser UAT in Wagtail Admin using only fictional,
non-sensitive data.

The UAT demonstrated:

* the `Editorial` navigation exposes contributor groups and minor contributors;
* a fictional contributor group can be associated with a school;
* fictional minor contributors can use both supported age bands;
* an incomplete `NewsPage` without a public credit can be saved as a draft;
* internal contributor names are not automatically copied into public credits;
* full publication without an effective public credit is blocked;
* the editor-controlled public credit remains independent from internal names;
* the minor privacy notice is visible and distinguishes the under-14 and
  14-to-17 age bands without presenting the project policy as universal legal
  advice;
* the official regulation link points to the expected source and opens
  externally;
* an identifiable-minor declaration without authorization verification blocks
  publication;
* publication succeeds after a valid public credit and the required
  authorization verification are present;
* Home and the public news detail render the chosen public credit;
* fictional internal minor names, age-band values, and internal privacy flags
  are absent from the public output and inspected HTML;
* `sensitive_content` does not introduce an additional hard publication block.

The first UAT pass found two adjacent generic Wagtail validation strings in
English. Project gettext overrides were added and a focused delta-UAT confirmed
that the generic validation message and first-error action now render in
Spanish.

No real minor data was used.

## Spanish Surface Findings

Focused browser UAT covered:

* `Editorial`;
* `Grupos de colaboradores`;
* `Colaboradores menores`;
* `Firma pública`;
* `Colaboradores internos`;
* `Privacidad de menores`;
* the legal notice and external regulation link;
* publication validation messages.

The initial browser UAT found these dependency strings in English:

* `The page could not be saved due to validation errors.`
* `Go to the first error`

Both strings are gettext-enabled Wagtail Admin messages used by the changed
validation flow. Project-level Spanish overrides were added to
`locale/es/LC_MESSAGES/django.po`, the compiled catalog was regenerated, and
focused delta-UAT confirmed the corrected Spanish output.

This remains a focused review of the EPIC3-002 editor-visible surfaces and is
not a claim that every installed Wagtail Admin surface has been fully audited
for Spanish translation coverage.

## Privacy And Access Notes

- No logging was added for `MinorContributor.full_name`.
- No public API was added.
- No public template renders internal contributor records or privacy flags.
- Internal minor names remain visible in the current Wagtail Admin snippet and
  page-edit surfaces for authorized adult editors.
- This ticket protects Wagtail Admin page-form publication validation. A future
  write API, student submission flow, external publisher, or Python publishing
  boundary must apply equivalent safeguards at its own boundary.

## Known Issues And Deferred Validation

- Treebeard manager warnings still appear during Django checks/migration
  commands. They were already out of scope for this ticket.

## New Work Discovered Disposition

- Student accounts / student draft submission: future product discovery; not
  promoted by this ticket.
- Teacher or monitor accounts: future permissions and workflow discovery; not
  promoted by this ticket.
- Permissions and row-level visibility for minor contributor data: important
  future privacy hardening; not implemented here.
- Adult editor public attribution linked to `User`/profile: future authorship
  modeling; not promoted here.
- Responsibility per contributor, such as photography, research, or writing:
  future editorial model; not promoted here.
- Formal class vs workshop group vs cohort modeling: future domain modeling;
  not promoted here.
- Cohort/enrollment year: future domain modeling; not promoted here.
- Policy for abbreviated minor public signatures and pseudonyms: future
  editorial/legal policy work; not encoded here.
- Field-level or application-level encryption/protection of minor names:
  future privacy/security hardening candidate; not implemented here.
- Individual authorization/document tracking if legal or operational review
  requires it: future compliance/product model; not implemented here.
- Future write API boundary applying equivalent publication safeguards:
  required architectural note for any future write path; not implemented here.

The preserved EPIC3-001 geography finding was not reopened. This ticket adds a
foreign key from `ContributorGroup` to `School`, but does not change `School`
geography semantics or coverage semantics.

* Contributor chooser scalability: the current contributor and group selection
  experience can become noisy when many records exist. Future editorial Admin
  work should evaluate native Wagtail searchable chooser behavior for
  contributor groups by name and minor contributors by internal full name
  before introducing custom JavaScript.
* Contributor lifecycle and archiving: workshops and contributor groups can end
  while their historical news relationships must remain intact. Future domain
  work should evaluate active/archive state for contributor groups and
  individual contributors so inactive records remain historically preserved but
  are excluded from new editorial selections. A group-level archive alone may
  be insufficient because an individual contributor can stop participating
  while the group remains active.
* School-scoped contributor selection: when a `NewsPage` has a school selected,
  the editor should not have to search through contributors from unrelated
  schools. Future chooser work should evaluate filtering selectable internal
  contributors to active contributors whose group belongs to the selected
  school. The behavior when `NewsPage.school` is empty still requires an
  explicit product decision.
* Contributor creation from the news editing flow: the current inline
  relationship can select an existing `MinorContributor`, but maintainer UAT
  showed that creating a missing contributor while editing the news item is not
  available in the current flow. Future Admin UX work should evaluate Wagtail's
  native chooser creation capabilities so an authorized editor can search for
  an existing contributor or create a new one without leaving the editorial
  task, while preserving the same privacy fields and school/group constraints.
* Long-form body authoring and internal images: maintainer UAT found the current
  `heading` / `paragraph` body editing experience too fragmented for long news
  articles. Future editorial content work should evaluate a richer configured
  text block that supports comfortable multi-paragraph authoring and a limited
  editorial toolbar such as bold, italic, links, numbered lists, bullet lists,
  and quotations. The existing `StreamField` architecture should be evaluated
  before replacing it with a monolithic field. The same work should consider
  zero-to-many images inside the article body as a concept separate from the
  optional featured image, including the metadata and public rendering rules
  required for each image use.
