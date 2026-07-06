# EPIC2-004 Closing Report

## Ticket

Eliminate the repeated `/app/staticfiles/` warning from tests in School Newsroom.

Operational project name: Noticias.
Technical project name: School Newsroom.
Repository name: `school-newsroom`.

## Final Summary

EPIC2-004 identified the exact emitter and root cause of the repeated test warning:

```text
UserWarning: No directory at: /app/staticfiles/
```

The warning was emitted by WhiteNoise during Django middleware initialization in pytest. Test settings inherited `whitenoise.middleware.WhiteNoiseMiddleware` from base settings, so the first Django test request initialized the middleware, read `STATIC_ROOT=/app/staticfiles`, called `WhiteNoise.add_files()`, and warned because `staticfiles/` is generated output and does not exist in the repository or test container.

The fix is limited to `config.settings.test`: tests now remove WhiteNoise middleware while preserving the existing `StaticFilesStorage` override. Production and local WhiteNoise configuration remain unchanged. Regression tests now protect both the absence of WhiteNoise middleware in test settings and the non-manifest test staticfiles storage.

## Starting State

- `git branch --show-current`
  - Result: `EPIC2-004-staticfiles-warning`.
- `git status --short`
  - Initial result: clean worktree.

## Warning Reproduction Before The Fix

- `make test 2>&1 | tee /tmp/epic2-004-make-test-before.log`
  - First attempt failed before pytest because the sandbox blocked Docker daemon access.
  - Retried with Docker access and passed: `7 passed, 1 warning`.
  - The warning appeared once during `apps/home/tests.py::test_wagtail_admin_login_loads`.
- `grep -nF "No directory at: /app/staticfiles/" /tmp/epic2-004-make-test-before.log`
  - Result:

```text
19:  /usr/local/lib/python3.12/site-packages/django/core/handlers/base.py:61: UserWarning: No directory at: /app/staticfiles/
```

- `make check 2>&1 | tee /tmp/epic2-004-make-check-before.log`
  - Passed: Ruff passed, pytest passed with `7 passed, 1 warning`.
  - The warning appeared once in the pytest phase.
- `grep -nF "No directory at: /app/staticfiles/" /tmp/epic2-004-make-check-before.log`
  - Result:

```text
24:  /usr/local/lib/python3.12/site-packages/django/core/handlers/base.py:61: UserWarning: No directory at: /app/staticfiles/
```

## Exact Warning Emitter

- Installed package path:
  - `whitenoise`: `/usr/local/lib/python3.12/site-packages/whitenoise/__init__.py`
  - `whitenoise.base`: `/usr/local/lib/python3.12/site-packages/whitenoise/base.py`
  - `whitenoise.middleware`: `/usr/local/lib/python3.12/site-packages/whitenoise/middleware.py`
- Exact emitter:
  - Module: `whitenoise.base`
  - Class: `WhiteNoise`
  - Function: `WhiteNoise.add_files`
  - Line: `/usr/local/lib/python3.12/site-packages/whitenoise/base.py:110`
- Emitting code:

```text
warnings.warn(f"No directory at: {root}", stacklevel=3)
```

The warning appears in pytest at `django/core/handlers/base.py:61` because WhiteNoise sets `stacklevel=3`, pointing the warning to Django's middleware instantiation call:

```text
mw_instance = middleware(adapted_handler)
```

## Effective Staticfiles Configuration Inspected

The effective runtime settings were inspected inside Docker Compose.

`config.settings.test`:

```text
DEBUG: False
STATIC_ROOT: /app/staticfiles
STATIC_URL: /static/
STORAGES.staticfiles: {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}
WhiteNoise middleware before fix: True
```

`config.settings.local`:

```text
DEBUG: True
STATIC_ROOT: /app/staticfiles
STATIC_URL: /static/
STORAGES.staticfiles: {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'}
WhiteNoise middleware: True
```

`config.settings.production`, inspected with a test-only `DJANGO_SECRET_KEY`:

```text
DEBUG: False
STATIC_ROOT: /app/staticfiles
STATIC_URL: /static/
STORAGES.staticfiles: {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'}
WhiteNoise middleware: True
```

The container check confirmed `/app/staticfiles` does not exist:

```text
missing
ls: cannot access '/app/staticfiles': No such file or directory
```

## Root-Cause Chain

```text
pytest loads config.settings.test
-> config.settings.test imports config.settings.base
-> test settings inherit whitenoise.middleware.WhiteNoiseMiddleware
-> django.test.Client creates the Django handler for test_wagtail_admin_login_loads
-> django.core.handlers.base.BaseHandler.load_middleware initializes WhiteNoiseMiddleware
-> WhiteNoiseMiddleware.__init__ reads settings.STATIC_ROOT
-> effective STATIC_ROOT is /app/staticfiles
-> WhiteNoiseMiddleware.__init__ calls self.add_files(self.static_root, prefix=self.static_prefix)
-> WhiteNoise.add_files checks os.path.isdir('/app/staticfiles/')
-> the generated staticfiles directory is absent
-> WhiteNoise.add_files emits UserWarning: No directory at: /app/staticfiles/
```

The suite already uses `django.contrib.staticfiles.storage.StaticFilesStorage` in test settings, so tests do not require the production-style manifest storage or WhiteNoise static serving middleware.

## Solution Applied

- `config.settings.test` now derives from base settings and removes only `whitenoise.middleware.WhiteNoiseMiddleware` for tests.
- The existing test override of `STORAGES["staticfiles"]` to `django.contrib.staticfiles.storage.StaticFilesStorage` remains in place.
- Local and production WhiteNoise middleware and storage configuration were not changed.
- No warning filters, pytest warning suppression, tracked `staticfiles/`, dependency changes, site-packages patches, or `collectstatic` side effects were added.

## Regression Protection

Added settings tests that verify:

- `config.settings.test` does not include `whitenoise.middleware.WhiteNoiseMiddleware`.
- `config.settings.test` keeps `STORAGES["staticfiles"]["BACKEND"]` set to `django.contrib.staticfiles.storage.StaticFilesStorage`.

## Files And Directories Created Or Modified

- Modified `config/settings/test.py`.
- Modified `config/settings/tests.py`.
- Modified `README.md` to remove the now-obsolete troubleshooting note that said the `/app/staticfiles/` warning may appear during tests.
- Created `docs/process/EPIC2-004_feedback.md`.

No `staticfiles/` directory, cache directory, generated artifact, migration, product feature, CI configuration, or deploy file was added.

## Commands Successfully Run

- `git branch --show-current`
- `git status --short`
- `rg --files`
- `sed -n ... /home/ljarufe/Downloads/EPIC2-004_eliminar_warning_staticfiles_tests.md`
- `sed -n ... AGENTS.md`
- `sed -n ... Makefile`
- `sed -n ... .pre-commit-config.yaml`
- `sed -n ... pytest.ini`
- `sed -n ... requirements.txt`
- `sed -n ... pyproject.toml`
- `sed -n ... docker-compose.yml`
- `sed -n ... docker/web/Dockerfile`
- `sed -n ... config/settings/base.py`
- `sed -n ... config/settings/local.py`
- `sed -n ... config/settings/test.py`
- `sed -n ... config/settings/tests.py`
- `sed -n ... config/settings/production.py`
- `sed -n ... config/wsgi.py`
- `sed -n ... apps/home/tests.py`
- `sed -n ... docs/process/EPIC2-001_feedback.md`
- `sed -n ... docs/process/EPIC2-002_feedback.md`
- `sed -n ... docs/process/EPIC2-003_feedback.md`
- `rg -n "STATIC_ROOT|STATIC_URL|STORAGES|staticfiles|WhiteNoise|whitenoise|WHITENOISE|MIDDLEWARE|collectstatic" .`
- `make test 2>&1 | tee /tmp/epic2-004-make-test-before.log`
- `grep -nF "No directory at: /app/staticfiles/" /tmp/epic2-004-make-test-before.log`
- `make check 2>&1 | tee /tmp/epic2-004-make-check-before.log`
- `grep -nF "No directory at: /app/staticfiles/" /tmp/epic2-004-make-check-before.log`
- Docker runtime inspection of installed WhiteNoise package paths and source lines.
- Docker runtime inspection of effective test, local, and production settings.
- Docker runtime check that `/app/staticfiles` is absent.
- `docker compose run --rm web pytest config/settings/tests.py -q -o cache_dir=/tmp/school-newsroom-pytest-cache`
  - Final result: `7 passed in 0.01s`.
- `make test 2>&1 | tee /tmp/epic2-004-make-test-after.log`
  - Final result: `9 passed in 3.87s`.
- Absence check for `/tmp/epic2-004-make-test-after.log`
  - Passed with no target warning output.
- `make lint`
  - Final result: `All checks passed!`.
- `make check 2>&1 | tee /tmp/epic2-004-make-check-after.log`
  - Final result: Ruff passed, pytest `9 passed in 3.85s`.
- Absence check for `/tmp/epic2-004-make-check-after.log`
  - Passed with no target warning output.
- `pre-commit run --hook-stage pre-push --all-files`
  - First attempt failed before validation because Docker daemon access was blocked.
  - Retried with Docker access and passed: `make check ... Passed`.
- `git diff --check`
  - Final result: passed with no whitespace errors.
- `git status --short`
  - Final result: expected modified files and new feedback file only.

## Commands Not Run And Why

- `git commit`
  - Not run because the ticket reserves commits for the maintainer.
- `git push`
  - Not run because the ticket reserves pushes for the maintainer and requires real manual pre-push UAT.
- `git merge` or Squash and merge
  - Not run because merge actions are maintainer responsibilities.
- `collectstatic`
  - Not run because the ticket explicitly excludes using collected static output to hide this warning.
- `docker compose down -v`
  - Not run because destructive Docker volume commands are prohibited.
- Production checks using real production secrets
  - Not run. Production settings inspection used a test-only secret value.

## Problems Encountered

- The first `make test` reproduction attempt failed before pytest because the sandbox blocked Docker daemon access.
- The first `pre-commit run --hook-stage pre-push --all-files` attempt failed before Ruff because the pre-push hook runs `make check`, which needs Docker daemon access.
- The README contained a stale troubleshooting section documenting the target warning as expected. This was removed after the fix so permanent developer documentation does not preserve obsolete behavior.

## Failed Attempts Or Retries

- `make test 2>&1 | tee /tmp/epic2-004-make-test-before.log`
  - First attempt failed with Docker socket permission denied.
  - Retried with Docker access and reproduced the warning.
- `pre-commit run --hook-stage pre-push --all-files`
  - First attempt failed with Docker socket permission denied while the hook invoked `make check`.
  - Retried with Docker access and passed.

## Root Causes Of Failed Attempts

- The Codex sandbox restricts direct access to the Docker daemon unless the command is explicitly approved.
- The project correctly uses Docker Compose for validation, so `make test`, `make check`, and the pre-push hook require Docker daemon access from the host workflow.

## Warning Validation After The Fix

- `make test` after the fix:
  - `9 passed`.
  - No warnings summary.
  - Explicit grep for `No directory at: /app/staticfiles/` returned no matches.
- `make check` after the fix:
  - Ruff passed.
  - Pytest `9 passed`.
  - No warnings summary.
  - Explicit grep for `No directory at: /app/staticfiles/` returned no matches.
- `pre-commit run --hook-stage pre-push --all-files`
  - Passed after Docker access was available.
  - Output did not show the target warning.

## Remaining Warnings

No warning appeared in the after-fix `make test` or `make check` output.

Known Wagtail/Treebeard compatibility warnings remain outside EPIC2-004 scope if they appear in other Django system-check contexts.

## Deviations From The Ticket

- `README.md` was modified even though the expected code fix did not require README changes. The reason is narrow and direct: the README contained a permanent troubleshooting note saying the exact target warning may appear during tests. Keeping it would make developer-facing documentation false after this ticket.
- No other scope deviation was made.

## Manual Validation Completed By Luis

Luis completed the maintainer process UAT for EPIC2-004.

A real commit automatically invoked the configured pre-commit hooks:

```text
fix end of files.........................................................Passed
trim trailing whitespace.................................................Passed
check yaml...........................................(no files to check)Skipped
check toml...........................................(no files to check)Skipped
ruff check...............................................................Passed
ruff format..............................................................Passed
```

A real push automatically invoked the configured pre-push hook:

```text
make check...............................................................Passed
```

The real pre-push output did not include:

```text
No directory at: /app/staticfiles/
```

When the Pull Request was opened against `main`, GitHub automatically preloaded the repository Pull Request template introduced in EPIC2-003.

Codex code review completed with no findings requiring correction.

## Automatic Pre-Commit Invocation UAT Status

Passed.

The real `git commit` command automatically invoked the configured pre-commit hooks before creating the commit.

## Automatic Pre-Push Invocation UAT Status

Passed.

The real `git push` command automatically invoked:

```text
pre-push
-> make check
```

The hook passed and the target `/app/staticfiles/` warning did not appear.

## PR Template Preload UAT Status

Passed.

GitHub automatically preloaded `.github/pull_request_template.md` when the EPIC2-004 Pull Request was opened against `main`.

## Codex Review Status

Completed with no findings requiring changes.

## Recommendations For EPIC2-005

- Keep using configuration tests for settings-level behavior changes.
- Keep generated static output untracked.
- Do not add `collectstatic` to routine test execution.
- Keep future developer-experience tickets narrow and require before/after warning evidence when removing known warnings.

## AGENTS.md, External Process Source, And Living Guide

- `AGENTS.md` should not change for this ticket. The issue was a one-time test-settings configuration bug, not a reusable repository rule for every future task.
- The external process source does not need a new permanent rule unless repeated warning-cleanup tickets appear. The existing guidance to inspect real state, avoid unrelated scope, and record validation was sufficient.
- The living ticket-process guide could benefit from a small reminder for warning-removal tickets: prove the exact emitter and causal chain before applying a likely fix. That is useful process guidance, but it does not need to become repository-local `AGENTS.md` policy.

## Standard Ticket Template Improvements

For future warning-removal tickets, include:

- Required before and after log capture commands.
- Required grep or equivalent absence checks.
- Required emitter identification with module, class, function, and installed package path.
- Explicit exclusions against warning filters and generated artifact workarounds.
