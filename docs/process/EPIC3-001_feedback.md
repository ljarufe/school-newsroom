# EPIC3-001 Feedback

## Implementation Summary

EPIC3-001 adds the first editorial news publishing flow for School Newsroom.
Editors can manage Spanish Wagtail snippets for editorial sections and schools,
create `NewsPage` pages below `HomePage`, tag them, optionally attach a featured
image, publish through Wagtail's native page workflow, list public news on Home,
and render public detail pages.

The final closure pass consolidated the unpublished `apps.news` migration
history, kept the accepted product implementation unchanged, made the `setpriv`
runtime dependency explicit, and corrected this feedback inventory.

The maintainer then completed the real Dev Container rebuild validation and the
complete editorial browser UAT with fictional/non-sensitive data. The UAT found
remaining Spanish Admin gaps, English bootstrap workflow/group names, an English
visible HomePage type label, snippet discoverability friction, a root URL
browser observation, and a future geography-data need. This pass resolves those
concrete findings without reopening the accepted news model, query, publishing,
language, or migration-structure decisions.

No custom editorial workflow, roles, privacy/consent model, SEO metadata, API,
search, embeds, multimedia blocks, deploy infrastructure, CI workflow change, or
production configuration was added.

## Initial Repository State

- Branch recorded before closure pass: `EPIC3-001-editorial-news-core`.
- Active branch matched the current ticket.
- `docker-compose.yml` has no retained final delta against `main`.
- Before migration consolidation, the local `news` migration table contained:
  `0001_initial`, `0002_seed_initial_news_sections`,
  `0003_alter_newspage_options_alter_newssection_options_and_more`,
  `0004_align_spanish_locale_and_admin_language`,
  `0005_validate_spanish_locale_invariant`, and
  `0006_rename_bootstrap_home_page_to_inicio`.
- Local editorial data before rollback: `NewsPage=0`, `School=0`,
  `NewsSection=6`. The six rows were seed data, and no maintainer UAT/editorial
  content was present.
- Local Wagtail state before consolidation: one Locale row `es`; default Site
  root page id `2`; specific class `HomePage`; title `Inicio`; draft title
  `Inicio`; slug `home`; root revision count `0`.

## Maintainer UAT Evidence

The maintainer rebuilt/reopened the Dev Container successfully, ran the
requested Dev Container validation successfully, accessed Spanish Wagtail Admin,
confirmed the six seeded editorial sections, created a fictional school,
created a fictional `NewsPage` below `Inicio`, saved a draft, confirmed the
draft was absent from anonymous Home, published the page through Wagtail,
confirmed it appeared on Home, opened the public detail page, confirmed title,
metadata, StreamField content, tags, and featured-image flow as applicable, and
used a second fictional story to confirm visual publication-date ordering.

Only fictional/non-sensitive data was used.

UAT findings addressed in this pass:

- Remaining Wagtail Admin strings appeared in English on dashboard, reports,
  workflow, account preferences, and page-type usage screens.
- Stored Wagtail bootstrap names `Moderators`, `Editors`, and
  `Moderators approval` appeared in English.
- The visible HomePage page-type label appeared as `Home Page`.
- `Colegios` was hard to discover through the generic snippets navigation.
- A browser observation suggested `http://localhost:8000/` might navigate to
  `/admin/`.
- Province/district free-text fields need future geography modeling.

## Files Created Or Modified

- Modified `.vscode/tasks.json`.
- Modified `AGENTS.md`.
- Modified `Makefile`.
- Modified `README.md`.
- Modified `apps/home/models.py`.
- Created `apps/home/migrations/0002_alter_homepage_options.py`.
- Modified `config/settings/base.py`.
- Modified `docker/web/Dockerfile`.
- Created `docker/web/entrypoint.sh`.
- Created `docs/editorial/guia_de_uso.md`.
- Modified `docs/process/devcontainer.md`.
- Created `docs/process/EPIC3-001_feedback.md`.
- Created `locale/es/LC_MESSAGES/django.po`.
- Created `locale/es/LC_MESSAGES/django.mo`.
- Modified `templates/404.html`.
- Modified `templates/500.html`.
- Modified `templates/home/home_page.html`.
- Created `apps/news/__init__.py`.
- Created `apps/news/apps.py`.
- Created `apps/news/models.py`.
- Created `apps/news/wagtail_hooks.py`.
- Created `apps/news/migrations/__init__.py`.
- Created `apps/news/migrations/0001_initial.py`.
- Created `apps/news/migrations/0002_bootstrap_editorial_data.py`.
- Created `apps/news/tests/__init__.py`.
- Created `apps/news/tests/test_language.py`.
- Created `apps/news/tests/test_admin_uat.py`.
- Created `apps/news/tests/test_migrations.py`.
- Created `apps/news/tests/test_models.py`.
- Created `apps/news/tests/test_public_rendering.py`.
- Created `templates/news/news_page.html`.
- Created `templates/news/blocks/heading.html`.

## Final `apps.news` Structure

```text
apps/news/
  __init__.py
  apps.py
  models.py
  migrations/
    __init__.py
    0001_initial.py
    0002_bootstrap_editorial_data.py
  tests/
    __init__.py
    test_language.py
    test_migrations.py
    test_models.py
    test_public_rendering.py
```

No `0003+` `apps.news` migration is retained.

## Models And Publishing Flow

- `NewsSection` is a Wagtail snippet with Spanish editor labels and deterministic
  ordering by `sort_order`, then `name`.
- `School` is a Wagtail snippet with Spanish editor labels and no contact
  details, exact addresses, student records, or other minor PII fields.
- `NewsPage` is a Wagtail `Page` model with Spanish editor labels, required
  publication date, summary, StreamField body, required section, optional school,
  coverage fields, optional featured image, and tags.
- `NewsPage.section` uses `on_delete=PROTECT`.
- `NewsPage.school` and `NewsPage.featured_image` use `on_delete=SET_NULL`.
- `NewsPage.parent_page_types = ["home.HomePage"]`.
- `NewsPage.subpage_types = []`.
- `HomePage.subpage_types = ["news.NewsPage"]`.
- `HomePage` has Spanish editor-visible metadata:
  `Página de inicio` / `Páginas de inicio`.
- `HomePage.get_context()` exposes `latest_news` from live, public descendant
  pages, ordered by `publication_date` and `first_published_at`, limited to 12.
- `NewsSection` and `School` remain snippets but are registered through a
  Wagtail `SnippetViewSetGroup` as top-level Admin menu `Editorial`, with
  destinations `Secciones editoriales` and `Colegios`.

## Migrations

- `0001_initial.py`
  - Generated from the final accepted model state.
  - Creates `NewsSection`, `School`, `NewsPage`, and `NewsPageTag`.
  - Includes final Spanish model metadata, field labels, StreamField block
    labels, relationship policies, JSON StreamField state, and tag field state.
- `0002_bootstrap_editorial_data.py`
  - Seeds exactly six initial editorial sections:
    `politica`, `cultura`, `medio-ambiente`, `problematicas-sociales`,
    `columnas`, and `entrevistas`.
  - Aligns Wagtail Locale/Admin language state for the Spanish-only product:
    zero Locale rows create `es`; one non-Spanish Locale row is updated to `es`
    to preserve page FKs; one existing `es` row is left unchanged; non-empty
    non-Spanish `UserProfile.preferred_language` values are normalized to `es`;
    empty preferences are left empty.
  - Validates the final Locale invariant: exactly one Locale row with
    `language_code == "es"`.
  - Normalizes only the known Wagtail bootstrap default Site root to `Inicio`
    and `home.HomePage` when safe.
  - Normalizes only untouched known Wagtail bootstrap Admin names:
    `Moderators` -> `Moderadores`, `Editors` -> `Editores`, and
    `Moderators approval` -> `Aprobación de moderadores` for both Workflow and
    Task rows.
  - Uses separate `RunPython` functions for section seed, Locale/Admin
    alignment, Locale invariant validation, Home normalization, and bootstrap
    Admin-name normalization.
  - Uses `db_alias = schema_editor.connection.alias` and applies that alias to
    migration reads and writes.
  - Uses safe non-destructive reverse operations.

Earlier unpublished local migrations `0003` through `0006` existed during
iterative review. Because the branch had not been committed, pushed, or opened
as a PR, they were consolidated before maintainer UAT; no published migration
history was rewritten.

## Migration Safety

- The `news` app was rolled back with Django migration operations before
  replacing migration files. This removed only unpublished local `apps.news`
  schema/data and was safe because there were no local `NewsPage` or `School`
  rows and no maintainer-created editorial/UAT data.
- `0002_bootstrap_editorial_data.py` is idempotent for the demonstrated local
  already-normalized Home state.
- Home conversion is limited to the default Site root when it is the known base
  `wagtailcore.Page` bootstrap page with slug `home` and title `Home` or
  `Welcome to your new Wagtail site!`.
- If a bootstrap-looking root uses an unexpected Page subclass, the migration
  fails closed with an operational `ImproperlyConfigured` exception.
- Generic base Page conversion requires zero matching Wagtail `Revision` rows.
  The local default root had revision count `0`. The migration test conversion
  fixture also uses revision count `0`.
- The unsupported revision test creates one historical `Revision` row and
  verifies the migration fails closed without silently retyping the Page.
- The migration does not rewrite revision JSON, revision content types, or
  arbitrary editor-authored page titles.
- Bootstrap Admin-name normalization fails closed if a Spanish target name
  already exists separately from the known English source row.

## Translation Strategy

- Project-owned locale overrides live under `locale/es/LC_MESSAGES/django.po`.
- `LOCALE_PATHS = [BASE_DIR / "locale"]` gives the project catalog precedence
  over installed dependency catalogs.
- The retained compiled catalog `locale/es/LC_MESSAGES/django.mo` is committed
  because Django runtime uses `.mo` files and Docker Compose bind mounts hide
  image-layer files under `/app`.
- `make compilemessages` regenerates `.mo` through Docker using
  `python manage.py compilemessages`.
- GNU gettext is installed explicitly through the existing Dockerfile apt layer.
- The observed Admin strings came from the Django `django` gettext domain across
  Wagtail Admin, Wagtail users, and Wagtail core source. Stored bootstrap names
  were database data and are handled by migration/local alignment, not gettext.

## Ownership And `setpriv`

- A temporary Docker Compose `user:` approach was tried during development.
  Review found the hardcoded fallback unsuitable for non-1000 Linux Dev
  Container users, so that Compose change was restored.
- `docker-compose.yml` has no retained final change.
- The retained solution is `docker/web/Dockerfile` plus
  `docker/web/entrypoint.sh`.
- The entrypoint detects the owner of bind-mounted `/app` and uses `setpriv` to
  run the process with that UID/GID.
- The retained Makefile change is migration drift integration, not UID/GID
  injection.
- `setpriv` is made explicit by installing Debian package `util-linux` through
  the existing apt layer. The rebuilt image reported `util-linux is already the
  newest version` and `util-linux set to manually installed`.
- `gettext` is made explicit through the same apt layer for reproducible project
  translation compilation.

## Automated Validation

- `docker compose run --rm web ... python manage.py migrate news zero`: passed.
- `docker compose run --rm web ... python manage.py migrate news`: passed with
  final `news.0001` and `news.0002`.
- `docker compose run --rm web ... pytest apps/news/tests/test_migrations.py -q`:
  `6 passed`.
- `make migration-check`: passed, `No changes detected`.
- `docker compose run --rm web ... pytest apps/news/tests -q`: `31 passed`.
- Fresh migration sequence with temporary SQLite database inside the container:
  passed through `news.0001_initial` and `news.0002_bootstrap_editorial_data`.
- `docker compose build web`: passed after adding `util-linux`.
- Rebuilt image `command -v setpriv`: `/usr/bin/setpriv`.
- Rebuilt image default bind mount ownership validation:
  `uid=1000 gid=1000 groups=1000`, `/app` write `1000:1000`, media write
  `1000:1000`.
- Non-1000 `/app` owner simulation: `uid=12345 gid=12346 groups=12346`.
- `make lint`: passed after the retry noted below.
- `make check`: passed; Ruff passed, migration drift check reported
  `No changes detected`, and pytest reported `40 passed`.
- `pre-commit run --hook-stage pre-push --all-files`: passed.
- `git diff --check`: passed.
- `git diff -- docker-compose.yml`: empty.
- Final local database inspection: Locale rows `[(1, "es")]`; default Site root
  id `2`; specific class `HomePage`; title `Inicio`; draft title `Inicio`;
  slug `home`; locale `es`; root revision count `0`.
- Final artifact scan found no `0003+` news migrations, probe files,
  migration drift probes, revision/Locale probes, ownership/media probes, or
  external review artifacts under `tmp/`.
- Final secrets scan found only existing local-development placeholders and
  documented/test-only values. No production secrets were added.
- Final PII scan found only fictional test tag strings and process-feedback
  text; no real student/minor PII was added.
- Maintainer-UAT pass focused tests:
  `pytest apps/news/tests/test_admin_uat.py apps/news/tests/test_migrations.py -q`
  reported `13 passed`.
- `pytest apps/news/tests -q`: `38 passed`.
- `make compilemessages`: passed and generated `django.mo` as UID/GID `1000`.
- `docker compose build web`: passed after `django.mo` was generated, so the
  retained compiled catalog is present in the image layer as well as the bind
  mount.
- Runtime translation check inside the rebuilt `web` container confirmed:
  `Search all pages…` -> `Buscar en todas las páginas...`,
  `Page types usage` -> `Uso de tipos de página`,
  `Keyboard shortcuts` -> `Atajos de teclado`, and
  `Use server time zone` -> `Usar zona horaria del servidor`.
- Final `make check`: passed; pytest reported `47 passed`.
- Final `pre-commit run --hook-stage pre-push --all-files`: passed.
- Root URL server-level investigation from inside the running `web` container:
  both `http://127.0.0.1:8000/` and `http://127.0.0.1:8000` sent request target
  `/`, returned `200 OK`, had no `Location` header, and rendered public Home.
  No routing change was made.
- Local one-off bootstrap Admin-name alignment was run against the current
  development database with the same function retained in `news.0002`; final
  local rows were `Moderadores`, `Editores`, and
  `Aprobación de moderadores`.

## Failed Attempts, Retries, And Root Causes

- Initial migration history accumulated review corrections as `0003` through
  `0006`. External review identified that this was noisy for an unpublished
  branch, so the history was consolidated to `0001` and `0002`.
- Migration test retry: the first consolidated test harness targeted only
  `news.0001`, so the historical app registry did not include `home.HomePage`.
  Root cause: `home.0001` is a dependency of `news.0002`, not `news.0001`.
  Fix: tests now target the explicit pre-`news.0002` state
  `[("home", "0001_initial"), ("news", "0001_initial")]`.
- Migration test retry: the test database had no default Site, and Wagtail
  runtime Page creation needed a Locale matching `LANGUAGE_CODE = "es"`.
  Fix: Home migration tests create a minimal default Site only when missing and
  prepare one Spanish Locale for that setup.
- Lint retry: `make lint` initially failed on an unused historical `HomePage`
  variable in `test_migrations.py`. The variable was removed and lint passed.
- Maintainer-UAT retry: `make compilemessages` first used `django-admin
  compilemessages`, which failed because the project package was not on
  `PYTHONPATH`. The Makefile target now uses `python manage.py compilemessages`.
- Maintainer-UAT retry: the local bootstrap-name alignment initially attempted a
  direct Python import of a migration module whose filename begins with digits.
  That is invalid syntax; the one-off operation was rerun with
  `importlib.import_module`.
- Maintainer-UAT retry: focused Admin tests exposed missing translations for
  the keyboard-shortcuts status sentence, a page-type report setup without a
  HomePage row, and a historical Task fixture missing `content_type_id`. The
  catalog and tests were corrected.

## Warnings

- Wagtail/Django system checks still emit the existing Treebeard manager warning
  for Treebeard 6 compatibility during management commands. This is outside
  EPIC3-001 scope and was not introduced as a product feature.
- The fresh SQLite migration validation does not create a default Wagtail Site;
  the Home normalization is intentionally a no-op when no default Site exists.
- No GitHub Actions, deployment, or remote CI validation was run in this pass.

## Final Maintainer Delta-UAT

The maintainer completed the focused browser delta-UAT after the
maintainer-UAT correction pass.

Validated manually:

- Both `http://localhost:8000/` and `http://localhost:8000` displayed the
  public Home in the browser; the earlier apparent navigation to `/admin/`
  was not reproduced after the server-level investigation.
- The Wagtail Admin sidebar exposed the top-level `Editorial` menu.
- `Editorial -> Secciones editoriales` was accessible.
- `Editorial -> Colegios` was accessible and made school management easier to
  discover than the generic snippets navigation.
- The Admin screens from the original UAT screenshots displayed the targeted
  Spanish translation corrections.
- Known bootstrap group, workflow, and task names displayed as `Moderadores`,
  `Editores`, and `Aprobación de moderadores`.
- The visible HomePage type label displayed as `Página de inicio`.
- Internal technical identifiers such as `home.homepage` and `news.newspage`
  remained unchanged.
- The account/preferences surface from the original UAT screenshots displayed
  the targeted Spanish translation corrections.

The full two-story editorial publishing UAT was not repeated because the
maintainer-UAT correction delta did not change NewsPage creation, draft/public
behavior, Home ordering, or public detail rendering.

The maintainer also observed additional English strings in other Wagtail Admin
surfaces outside the screenshot-driven correction scope. Those residual
translation gaps do not block EPIC3-001 and are deferred to separate follow-up
work.

Spanish Admin coverage must continue to be reviewed manually when a ticket
introduces or changes an editor-visible Admin surface. Missing dependency
translations discovered in those affected surfaces should be corrected or
explicitly dispositioned before the ticket closes.

No GitHub Actions or deployment validation has been completed at this point.

## New Work Discovered

- The recurring Treebeard 6 warning should be tracked separately if the project
  upgrades Treebeard or Wagtail dependencies. It is not a blocker for this
  ticket.
- Future backlog ticket: `Normalize school and editorial coverage geography
  with official Peru location data`. It must preserve the distinction between
  school location and news coverage territory.
- Privacy/authorship/consent remains the next critical editorial product
  priority before collecting real student/minor data.
- Future follow-up: complete residual Spanish translation coverage for Wagtail
  Admin surfaces that remain in English outside the screens corrected by
  EPIC3-001. Translation gaps should continue to be discovered through focused
  manual UAT of new or changed Admin surfaces rather than by claiming complete
  Wagtail translation coverage from this ticket.

## Reusable Process Learning

- For unpublished Django feature branches, consolidate iterative migration
  corrections before PR when the final state can be represented cleanly.
- Migration tests that exercise data migrations should use the exact historical
  app registry state needed by the migration under test, including cross-app
  dependencies such as `home.0001`.
- For Docker-first bind mounts, validating generated file ownership must include
  both the common host UID and a non-1000 owner simulation.
- Feedback files should distinguish retained migration design from temporary
  review-history files so maintainer UAT sees the candidate repository state.
- Changes to editor-visible Wagtail Admin workflows, navigation, fields, or
  editorial behavior should update the Spanish editor guide in the same
  implementation so documentation follows the product surface.
- Validation should be delta-based: use focused checks while implementing and
  reserve the general validation gate for technical close or a later delta that
  can invalidate the previous result.
- A validation command should not be repeated by routine after an unchanged
  successful result. Recurrent failures or workflow friction should trigger
  root-cause analysis and a durable process/environment correction instead of
  accumulating permanent retry instructions.
- Spanish Wagtail Admin coverage requires focused manual review of new or
  changed editor-visible surfaces. Residual dependency translation gaps outside
  the affected surface may be dispositioned as separate follow-up work.
