# EPIC2-002 Closing Report

## Ticket

Prepare VS Code for development, testing, and debugging with Dev Containers.

Operational project name: Noticias.
Technical project name: School Newsroom.
Repository name: `school-newsroom`.

## Final Summary

EPIC2-002 implemented and corrected the VS Code Dev Container workflow for the existing Docker-first Django/Wagtail project. VS Code is configured to reopen the repository in the existing Docker Compose `web` service, use `/app` as the container workspace, use `/usr/local/bin/python` as the Python interpreter inside the container, enable pytest discovery with `config.settings.test`, and provide debug profiles for targeted pytest debugging and Django/Wagtail debugging on port `8001`.

The final project decision is that the Dev Container provides the Python development, editor language tooling, testing, and debugging environment. Codex remains local to VS Code/the host as the implementation agent. The Makefile is the stable interface used by local Codex for general validation through Docker Compose, while targeted Python test/debug work is available inside the Dev Container.

The corrective iterations moved Python runtime settings out of workspace-level VS Code settings and into Dev Container customizations, so a local VS Code window no longer expects the container-only interpreter path. The Dev Container now uses a non-root development user through the official `common-utils` Dev Container Feature and installs Git/SSH tooling through that Feature.

A later experimental attempt to install Codex in the Dev Container Remote Extension Host and persist a Dev-Container-specific `CODEX_HOME` was manually rejected because it produced an unstable developer experience. That integration was reverted before closing EPIC2-002.

The Makefile was updated after real Dev Container validation showed Docker CLI is not available inside the container. From the host, the Makefile still delegates to Docker Compose. From inside the Dev Container, `make test`, `make lint`, and `make check` run against the current container runtime directly. These commands remain the official general validation workflow. VS Code Test Explorer and Run and Debug are configured only as targeted diagnostic tools.

Luis manually validated the main VS Code flows: reopening in the Dev Container, Pylance import resolution, Test Explorer discovery and execution, `Debug Test`, debugger Variables/Call Stack/Debug Console, and the `Django/Wagtail: Debug server` profile. Request-time breakpoint validation during an HTTP request is intentionally deferred until a future ticket introduces a real project Python code path executed during such a request.

Permanent developer documentation was added to `README.md` and `docs/process/devcontainer.md`. Ticket-specific findings, retries, warnings, and manual validation status are recorded in this file.

After the initial Pull Request was opened, Codex Code Review found one valid P1 regression: `config.settings.production` inherited the local `change-me` secret fallback from the shared django-environ schema. The correction was made on the same EPIC2-002 branch before merge. Production settings now explicitly reject the placeholder secret with `ImproperlyConfigured`, while local/test contexts can still use the current local fallback.

A follow-up Codex Code Review P2 comment correctly identified that blank production secrets also needed fail-closed handling. Production settings now reject missing, empty, whitespace-only, and placeholder `DJANGO_SECRET_KEY` values at settings import time.

## Commands Successfully Run

- `pwd && rg --files`
  - Confirmed repository path: `/home/ljarufe/Projects/school-newsroom`.
  - Listed the repository files before editing.
- `sed -n '1,260p' /home/ljarufe/Downloads/EPIC2-002_preparar_vscode_devcontainer_pruebas_debug.md`
  - Read the first part of the ticket.
- `sed -n '261,620p' /home/ljarufe/Downloads/EPIC2-002_preparar_vscode_devcontainer_pruebas_debug.md`
  - Read the Dev Container, extension, Pylance, pytest, and debug requirements.
- `sed -n '621,980p' /home/ljarufe/Downloads/EPIC2-002_preparar_vscode_devcontainer_pruebas_debug.md`
  - Read the documentation, validation, and responsibility requirements.
- `sed -n '981,1280p' /home/ljarufe/Downloads/EPIC2-002_preparar_vscode_devcontainer_pruebas_debug.md`
  - Read the acceptance criteria and manual checklist.
- `sed -n '1,260p' docs/process/EPIC2-001_feedback.md`
  - Used the EPIC2-001 closing report as the structure and quality reference.
- `find . -maxdepth 3 -type f \( -path './.vscode/*' -o -path './.devcontainer/*' -o -name 'Makefile' -o -name 'docker-compose.yml' -o -name 'pytest.ini' -o -name 'pyproject.toml' -o -name 'requirements.txt' -o -name 'README.md' \) -print`
  - Confirmed existing VS Code files and absence of `.devcontainer/` before implementation.
- `git status --short`
  - Confirmed the worktree was clean before editing.
- `sed -n '1,240p' docker-compose.yml`
  - Confirmed services `web` and `db`, bind mount `.:/app`, normal web port `8000:8000`, PostgreSQL port `5434:5432`, and existing `web` command.
- `sed -n '1,240p' Makefile`
  - Confirmed targets delegate to Docker Compose and force `DJANGO_SETTINGS_MODULE=config.settings.test` for `make test`.
- `sed -n '1,220p' .vscode/settings.json`
  - Confirmed pytest was disabled before this ticket.
- `sed -n '1,220p' .vscode/extensions.json`
  - Confirmed existing recommendations.
- `sed -n '1,220p' .vscode/tasks.json`
  - Confirmed tasks call `make` targets and do not duplicate Makefile internals.
- `sed -n '1,220p' docker/web/Dockerfile`
  - Confirmed `WORKDIR /app`, Python 3.12 base image, requirements installation, and default runserver command.
- `sed -n '1,220p' pytest.ini`
  - Confirmed pytest uses `config.settings.test`.
- `sed -n '1,260p' pyproject.toml`
  - Confirmed Ruff configuration.
- `sed -n '1,260p' README.md`
  - Reviewed existing permanent developer documentation.
- `sed -n '1,220p' config/settings/test.py && sed -n '1,180p' apps/home/tests.py`
  - Confirmed test settings and current tests.
- `sed -n '1,220p' config/settings/local.py`
  - Confirmed local debug settings.
- `docker compose ps`
  - Initial result: no running services displayed.
- `docker compose logs --tail=80 web`
  - Retrieved prior `web` logs. Logs showed the known Treebeard warnings and successful Wagtail admin requests from earlier runs.
- `docker compose run --rm web sh -c 'which python && python --version && python -c "import sys; print(sys.executable)" && python -c "import django; print(django.get_version())" && python -c "import wagtail; print(wagtail.__version__)" && python -c "import pytest; print(pytest.__version__)"'`
  - Passed after rerun with Docker approval.
  - Observed:

```text
/usr/local/bin/python
Python 3.12.13
/usr/local/bin/python
5.2.15
7.4.2
8.4.2
```

- `mkdir -p .devcontainer`
  - Created the Dev Container directory.
- `jq empty .devcontainer/devcontainer.json`
  - Passed.
- `jq empty .vscode/settings.json`
  - Passed.
- `jq empty .vscode/extensions.json`
  - Passed.
- `jq empty .vscode/launch.json`
  - Passed.
- `make test`
  - Passed: 2 tests passed, 1 known warning.
- `make lint`
  - Passed: `All checks passed!`
- `make check`
  - Passed: Ruff passed, 2 tests passed, 1 known warning.
- `docker compose run --rm web pytest --ds=config.settings.test --collect-only -q`
  - Passed. Collected 2 tests:

```text
apps/home/tests.py::test_wagtail_admin_login_loads
apps/home/tests.py::test_django_settings_load
```

- `docker compose ps`
  - Final result: `db` running on `0.0.0.0:5434->5432/tcp`; no normal `web` service running at that moment.
- `docker compose logs --tail=80 web`
  - Retrieved prior `web` logs, including known Treebeard warnings and prior successful admin traffic.
- `git diff --check`
  - Passed with no whitespace errors.
- `git status --short`
  - Confirmed modified and new files after implementation.
- `git diff --stat`
  - Showed tracked-file changes. Untracked new files were not included in the stat output.
- `git diff -- .vscode/extensions.json .vscode/settings.json .vscode/launch.json README.md docs/process/devcontainer.md .devcontainer/devcontainer.json`
  - Reviewed the tracked diff. New untracked file contents were reviewed separately with `sed`.
- `pwd && rg --files`
  - Corrective iteration context inside the Dev Container confirmed workspace path `/app`.
- `sed -n '1,260p' .devcontainer/devcontainer.json`
  - Confirmed the initial Dev Container used the `web` service but had no non-root user, no Dev Container Feature for developer utilities, no Codex Remote Extension Host install, and no persistent Dev-Container-specific `CODEX_HOME`.
- `sed -n '1,240p' .vscode/settings.json`
  - Confirmed workspace-level Python settings incorrectly pointed local VS Code at `/usr/local/bin/python`.
- `sed -n '1,260p' config/settings/base.py`
  - Confirmed inline django-environ defaults were used for `DJANGO_SECRET_KEY` and `DATABASE_URL`.
- `id && whoami && printf 'HOME=%s\nCODEX_HOME=%s\n' "$HOME" "${CODEX_HOME-}" && command -v git || true && command -v ssh || true && command -v docker || true && command -v make || true`
  - Confirmed the current Dev Container session ran as `root`, `HOME=/root`, no `CODEX_HOME`, no `git`, no `ssh`, no `docker`, and `make` available at `/usr/bin/make`.
- `python - <<'PY' ... environ ... PY`
  - Confirmed installed `django-environ` version `0.14.0` and inspected `Env.__init__`, `Env.__call__`, `Env.get_value`, and `Env.db` behavior.
- `python -m json.tool .devcontainer/devcontainer.json >/tmp/devcontainer.json.pretty && python -m json.tool .vscode/settings.json >/tmp/settings.json.pretty && python -m json.tool .vscode/extensions.json >/tmp/extensions.json.pretty && python -m json.tool .vscode/launch.json >/tmp/launch.json.pretty && echo ok`
  - Passed after the corrective Dev Container and VS Code settings changes.
- `make test`
  - Passed after Makefile adjustment from inside the Dev Container: pytest used `cache_dir=/tmp/school-newsroom-pytest-cache`, 2 tests passed, 1 known `staticfiles` warning.
- `make lint`
  - Passed after Makefile adjustment from inside the Dev Container with `RUFF_CACHE_DIR=/tmp/school-newsroom-ruff-cache`: `All checks passed!`.
- `make check`
  - Passed after Makefile adjustment from inside the Dev Container: Ruff passed with `RUFF_CACHE_DIR=/tmp/school-newsroom-ruff-cache`, pytest used `cache_dir=/tmp/school-newsroom-pytest-cache`, 2 tests passed, 1 known `staticfiles` warning.
- `python - <<'PY' ... from config.settings import base ... PY`
  - Confirmed the django-environ schema-default refactor preserved local defaults: `DJANGO_SECRET_KEY` default `change-me`, database host `db`, port `5432`, and database name `school_newsroom`.
- `sed -n '1,260p' /home/ljarufe/.codex/attachments/66c59150-e40a-4679-b2ed-7f04d2b3658d/pasted-text.txt`
  - Read the final local Codex closing instructions.
- `sed -n '1,320p' docs/process/EPIC2-002_feedback.md`
  - Reviewed the current feedback state before the final correction.
- `git status --short`
  - Confirmed the current worktree state before the final correction.
- `rg --files`
  - Reconfirmed repository files.
- `sed -n '321,760p' docs/process/EPIC2-002_feedback.md`
  - Reviewed the rest of the current feedback state before the final correction.
- `sed -n '1,260p' .devcontainer/devcontainer.json`
  - Confirmed the Dev Container still contained the experimental Codex Remote Extension Host integration.
- `sed -n '1,240p' .gitignore`
  - Confirmed `.codex/` had been added as a blanket ignore.
- `sed -n '1,220p' .vscode/extensions.json`
  - Confirmed `eamodio.gitlens` was still recommended.
- `sed -n '1,260p' .vscode/settings.json`
  - Confirmed workspace settings no longer contained container-only Python settings.
- `sed -n '1,260p' Makefile`
  - Confirmed the dual host/Dev-Container Makefile behavior was present and should be preserved.
- `sed -n '1,340p' README.md`
  - Reviewed permanent developer documentation.
- `sed -n '1,340p' docs/process/devcontainer.md`
  - Confirmed Dev Container process documentation still described Codex in the Remote Extension Host before final cleanup.
- `sed -n '1,320p' config/settings/base.py`
  - Confirmed the django-environ schema-default refactor was present and should be preserved.
- `sed -n '1,220p' .vscode/launch.json`
  - Confirmed debug configurations remained present.
- `git diff -- .devcontainer/devcontainer.json .gitignore .vscode/extensions.json .vscode/settings.json Makefile README.md config/settings/base.py docs/process/devcontainer.md .vscode/launch.json`
  - Reviewed the current diff before final cleanup.
- `rg -n "Codex|CODEX|codex|GitLens|gitlens|openai|school_newsroom_codex_home|Manual Steps|Solutions Applied|Final Summary|Problems Encountered|Failed Attempts|Root Causes|Files And Directories|Deviations|VS Code Problems|Manual Validation|Recommendations|Standard Ticket" docs/process/EPIC2-002_feedback.md docs/process/devcontainer.md README.md .devcontainer/devcontainer.json .gitignore .vscode/extensions.json`
  - Located Codex Remote Extension Host, GitLens, and feedback sections requiring final edits.
- `find .codex -maxdepth 3 -type f -print`
  - Returned no files.
- `rg -n "Codex|CODEX|codex|GitLens|gitlens|openai|school_newsroom_codex_home" .devcontainer .gitignore .vscode README.md docs/process/devcontainer.md`
  - Confirmed no Codex Remote Extension Host, GitLens, or Codex volume references remained in permanent config/docs after cleanup.
- `jq empty .devcontainer/devcontainer.json`
  - Passed after final cleanup.
- `jq empty .vscode/settings.json`
  - Passed after final cleanup.
- `jq empty .vscode/extensions.json`
  - Passed after final cleanup.
- `jq empty .vscode/launch.json`
  - Passed after final cleanup.
- `make check`
  - Passed from the local Codex/host environment.
  - Confirmed the host Makefile path still works through Docker Compose.
  - Ruff result: `All checks passed!`
  - Pytest result: 2 tests passed, 1 known `/app/staticfiles/` warning.
- `git diff --check`
  - Passed with no whitespace errors.
- `git status --short`
  - Final status showed modified tracked files and expected untracked new files.
- `git diff --stat`
  - Reviewed final tracked-file diff summary.
- `git diff -- .devcontainer/devcontainer.json .vscode/extensions.json .vscode/settings.json .vscode/launch.json Makefile README.md config/settings/base.py docs/process/devcontainer.md`
  - Reviewed final diff for the main implementation files. New untracked files were reviewed separately with `sed`.
- `sed -n '1,220p' config/settings/base.py`
  - Reviewed the shared django-environ schema default for `DJANGO_SECRET_KEY`.
- `sed -n '1,220p' config/settings/production.py`
  - Confirmed production read `SECRET_KEY = env("DJANGO_SECRET_KEY")` with no inline default, but inherited the shared schema default.
- `sed -n '1,220p' config/settings/test.py`
  - Confirmed test settings were unchanged.
- `sed -n '1,220p' apps/home/tests.py`
  - Reviewed the existing test location and structure.
- `find . -maxdepth 3 -type f \( -path './.devcontainer/*' -o -path './.vscode/*' -o -path './docs/process/*' -o -path './config/settings/*' -o -name '*test*.py' -o -name 'tests.py' \) -print | sort`
  - Confirmed `.devcontainer/devcontainer-lock.json` exists and reviewed relevant settings/test files.
- `sed -n '1,240p' .devcontainer/devcontainer-lock.json`
  - Confirmed the generated lockfile records the resolved `common-utils` Feature version and digest.
- `docker compose run --rm web pytest config/settings/tests.py -q -o cache_dir=/tmp/school-newsroom-pytest-cache`
  - Passed after the first production secret correction: 3 targeted production secret regression cases passed.
- `make check`
  - Passed after the first Pull Request review correction.
  - Ruff result: `All checks passed!`
  - Pytest result: 5 tests passed, 1 known `/app/staticfiles/` warning.
- `git diff -- config/settings/production.py config/settings/tests.py docs/process/EPIC2-002_feedback.md .devcontainer/devcontainer-lock.json`
  - Reviewed the production secret correction diff.
- `rg -n "SECRET_KEY|production secret|devcontainer-lock|Files And Directories|Root Causes|Solutions Applied|Failed Attempts|Problems Encountered|Commands Successfully Run|Final Summary|Codex Code Review|Review" docs/process/EPIC2-002_feedback.md`
  - Located feedback sections needing Pull Request review updates.
- `docker compose run --rm web pytest config/settings/tests.py -q -o cache_dir=/tmp/school-newsroom-pytest-cache`
  - Passed after the follow-up blank-secret correction: 5 targeted production secret regression cases passed.
- `make check`
  - Passed after the follow-up blank-secret correction.
  - Ruff result: `All checks passed!`
  - Pytest result: 7 tests passed, 1 known `/app/staticfiles/` warning.
- `git diff --check`
  - Passed with no whitespace errors.
- `git status --short`
  - Final status showed `config/settings/production.py`, `config/settings/tests.py`, and `docs/process/EPIC2-002_feedback.md` changed by the follow-up PR review correction.

## Commands Not Run And Why

- `Dev Containers: Reopen in Container`
  - Not run by Codex because it requires the real VS Code UI on Luis's machine.
- VS Code Problems inspection
  - Not run by Codex because it requires VS Code UI diagnostics.
- VS Code Test Explorer visual discovery
  - Not run by Codex because it requires VS Code UI. The equivalent pytest collection command was run successfully.
- VS Code `Debug Test`
  - Not run by Codex because it requires VS Code UI debugger interaction.
- VS Code `Run and Debug -> Django/Wagtail: Debug server`
  - Not run by Codex because it requires VS Code UI debugger interaction and port forwarding.
- Browser validation of `http://localhost:8000/`
  - Not run by Codex because browser validation belongs to Luis's local UI.
- Browser validation of `http://localhost:8001/`
  - Not run by Codex because the debug server must be started from VS Code Run and Debug.
- `make up`
  - Not run because the ticket did not require starting the normal long-running web service from Codex after implementation. Existing Makefile behavior was preserved and `make test`, `make lint`, and `make check` were the required general validation commands.
- `make createsuperuser`
  - Not run because it is interactive.
- `docker compose down -v`
  - Not run because it is destructive to volumes and explicitly forbidden.
- `rm -rf`
  - Not run because destructive commands were forbidden.
- `git commit`
  - Not run because the ticket says Luis will commit manually.
- `git push`
  - Not run because the ticket says Luis will push manually.
- `Dev Containers: Rebuild Container`
  - Not run by local Codex because it requires the real VS Code UI. The final code change removes Codex Remote Extension Host integration and does not require Codex to validate its own remote extension state.
- Docker volume deletion for the unused `school_newsroom_codex_home` volume
  - Not run because deleting Docker volumes is destructive and was explicitly forbidden. The unused local volume may remain harmlessly outside the repository.
- Creation of `.codex/config.toml`
  - Not run because the final instruction explicitly said not to create project-scoped Codex config in this ticket.
- Copying files from `~/.codex`
  - Not run because copying `auth.json`, sessions, history, or personal agent state into the repository was explicitly forbidden.

## Problems Encountered During Implementation

- Docker access was initially blocked by the Codex sandbox when running `docker compose run --rm web ...`.
- Host Python commands `python` and `python3` could not be used for JSON validation because the host has no active Python version configured for those commands.
- `docker compose logs --tail=80 web` returned historical logs for a previously run `web` service even when `docker compose ps` did not show `web` currently running.
- VS Code UI features could not be validated by Codex directly.
- The initial Dev Container ran VS Code remote tooling as `root`.
- The initial Dev Container did not have `git` or `ssh` installed, and VS Code reported `Git not found`.
- The initial workspace-level `python.defaultInterpreterPath` caused a local VS Code window to warn that `/usr/local/bin/python` was invalid before reopening in the Dev Container.
- An experimental iteration attempted to run Codex inside the Dev Container Remote Extension Host and persist Dev-Container-specific Codex state.
- Repeated Codex sign-in/setup occurred inside the Dev Container.
- The Dev Container Codex thread/task list did not match the local Codex thread/task list.
- Historical host-local threads were not available as expected.
- A recently used Dev-Container Codex conversation was not available after reopening.
- Codex later remained stuck while loading/signing in.
- VS Code eventually became unresponsive during the remote Codex workflow.
- The persisted Dev-Container-specific `CODEX_HOME` did not provide an acceptable developer experience.
- This was not classified as a Django/Wagtail project failure.
- The initial Makefile could not run `make test`, `make lint`, or `make check` from inside the Dev Container because it always delegated to Docker Compose.
- Pylance reported django-environ argument type diagnostics for inline defaults in `config/settings/base.py`.
- Codex Code Review found a P1 production secret regression after the initial Pull Request was opened.
- The regression allowed `config.settings.production` to inherit the local `change-me` placeholder secret through the shared django-environ schema.
- A follow-up Codex Code Review P2 comment found that explicitly blank or whitespace-only production secrets were still accepted by the guard.

## Failed Attempts Or Retries

- First attempt:

```bash
docker compose run --rm web sh -c 'which python && python --version && python -c "import sys; print(sys.executable)" && python -c "import django; print(django.get_version())" && python -c "import wagtail; print(wagtail.__version__)" && python -c "import pytest; print(pytest.__version__)"'
```

Failed with:

```text
unable to get image 'postgres:16': permission denied while trying to connect to the docker API at unix:///var/run/docker.sock
```

It passed after rerunning with approved Docker access.

- JSON validation with:

```bash
python -m json.tool .devcontainer/devcontainer.json
python -m json.tool .vscode/settings.json
python -m json.tool .vscode/extensions.json
python -m json.tool .vscode/launch.json
```

Failed with:

```text
No version is set for command python
Consider adding one of the following versions in your config file at /home/ljarufe/Projects/school-newsroom/.tool-versions
python 3.12.11
```

- JSON validation with:

```bash
python3 -m json.tool .devcontainer/devcontainer.json
python3 -m json.tool .vscode/settings.json
python3 -m json.tool .vscode/extensions.json
python3 -m json.tool .vscode/launch.json
```

Failed with:

```text
No version is set for command python3
Consider adding one of the following versions in your config file at /home/ljarufe/Projects/school-newsroom/.tool-versions
python 3.12.11
```

Validation succeeded after switching to `jq empty`.

- Corrective iteration first attempted:

```bash
make test
```

Inside the Dev Container this failed with:

```text
/bin/sh: 1: docker: not found
make: *** [Makefile:36: test] Error 127
```

It passed after the Makefile learned to run validation commands directly when `/.dockerenv` is present.

- Experimental Dev Container Codex Remote Extension Host flow failed manual validation.

Manual findings:

```text
Repeated Codex sign-in/setup occurred inside the Dev Container.
The Dev Container Codex thread/task list did not match the local Codex thread/task list.
Historical host-local threads were not available as expected.
A recently used Dev-Container Codex conversation was not available after reopening.
Codex later remained stuck while loading/signing in.
VS Code eventually became unresponsive during the remote Codex workflow.
The persisted Dev-Container-specific CODEX_HOME did not provide an acceptable developer experience.
```

Final decision:

```text
Codex local is the implementation agent.
The Dev Container is the Python/editor/test/debug environment.
```

- Pull Request review correction was required after the initial PR was opened.

Review finding:

```text
Require the production secret key
```

Codex Code Review correctly identified that production settings could accept the local `change-me` placeholder because the default had moved into the shared django-environ schema.

- Follow-up Pull Request review correction was required after the first production secret guard.

Review finding:

```text
Reject blank production secrets too
```

Codex Code Review correctly identified that `DJANGO_SECRET_KEY=` and whitespace-only values should also fail at production settings import time.

## Root Causes

- Docker daemon access is restricted by the Codex execution sandbox unless explicitly approved.
- The host Python command is managed by local tooling and no active version is selected for `python` or `python3` in this repository context.
- Docker Compose keeps logs for stopped service containers, so `docker compose logs web` can show historical logs even when `web` is not currently running.
- Dev Containers, Problems, Test Explorer, debug breakpoints, Variables, Watch, Call Stack, Debug Console, and forwarded browser ports are visual/editor workflows that require Luis's VS Code session.
- Host VS Code and the Dev Container have separate extension hosts and separate agent state. Moving the implementation agent into the Remote Extension Host introduced authentication/session persistence problems that are unrelated to the Django/Wagtail project.
- The initial Dev Container used the base image default user, which was `root`.
- The normal Docker image intentionally did not include editor/developer tooling such as Git and SSH; those are Dev Container concerns.
- Workspace-level Python settings apply before VS Code reopens the repository in the container, so container-only interpreter paths do not belong in `.vscode/settings.json`.
- django-environ supports declaring casts/defaults in the `environ.Env(...)` schema; inline defaults hit a Pylance typing edge around `NoValue` overloads.
- The original production settings call had no default, but moving `DJANGO_SECRET_KEY=(str, "change-me")` into the shared base schema changed production behavior. `config.settings.production` still called `env("DJANGO_SECRET_KEY")`, but that call now resolved to the shared development placeholder instead of failing closed.
- The first production guard only rejected the literal placeholder. It did not reject explicitly configured blank or whitespace-only `DJANGO_SECRET_KEY` values, so those values could pass settings import instead of failing closed immediately.
- Docker CLI is not installed inside the Dev Container, so Make targets that always call `docker compose` cannot serve as the in-container validation interface.

## Solutions Applied

- Used the existing Docker Compose `web` service as the Dev Container service.
- Configured the Dev Container workspace at `/app`, matching the Dockerfile `WORKDIR` and Compose bind mount.
- Configured VS Code to use `/usr/local/bin/python` inside Dev Container customizations, confirmed inside the `web` service.
- Enabled pytest in Dev Container customizations and set `python.testing.pytestArgs` to `["--ds=config.settings.test"]`.
- Added `Python: Debug tests` with `purpose: ["debug-test"]` and `DJANGO_SETTINGS_MODULE=config.settings.test`.
- Added `Django/Wagtail: Debug server` using `debugpy`, `manage.py runserver 0.0.0.0:8001 --noreload`, and `DJANGO_SETTINGS_MODULE=config.settings.local`.
- Added `ms-python.debugpy` to VS Code extension recommendations and Dev Container customizations.
- Added permanent Dev Container documentation to `README.md` and `docs/process/devcontainer.md`.
- Used `jq empty` for JSON validation after host Python command failures.
- Added the official `ghcr.io/devcontainers/features/common-utils:2` Dev Container Feature to create/configure the `vscode` non-root development user and install common developer utilities including Git and SSH client.
- Set `remoteUser` to `vscode` and left `updateRemoteUserUID` enabled so VS Code remote tooling does not run as `root`.
- Reverted the experimental Codex Remote Extension Host integration from `.devcontainer/devcontainer.json`.
- Removed `openai.chatgpt` from Dev Container remote extensions.
- Removed the Dev-Container-specific `CODEX_HOME` environment variable.
- Removed the Docker-managed `school_newsroom_codex_home` mount from the Dev Container.
- Removed the `postStartCommand` whose only purpose was to prepare the Dev-Container-specific Codex home.
- Removed the blanket `.codex/` ignore from `.gitignore`; `find .codex -maxdepth 3 -type f -print` returned no files, and future project-scoped `.codex/config.toml` should not be accidentally blocked.
- Removed the workspace recommendation for `eamodio.gitlens`; GitLens is not a decided dependency or tool for this ticket.
- Moved Python runtime/test settings out of `.vscode/settings.json`; that file now keeps only editor settings that are valid outside and inside the Dev Container.
- Moved django-environ defaults for `DJANGO_SECRET_KEY` and `DATABASE_URL` into the `environ.Env(...)` schema and read them without inline defaults, preserving runtime behavior while avoiding the Pylance argument type diagnostics.
- Added an explicit production guard in `config/settings/production.py` that rejects missing, empty, whitespace-only, and placeholder `DJANGO_SECRET_KEY` values with `django.core.exceptions.ImproperlyConfigured`.
- Added targeted regression tests proving production rejects missing, empty, whitespace-only, and placeholder secrets, and accepts a separately configured non-placeholder test secret.
- Updated the Makefile so host runs still delegate to Docker Compose and in-container validation runs directly against the current container runtime.
- Configured Makefile validation and Dev Container pytest/Ruff settings to use `/tmp/school-newsroom-*` caches so tool cache files do not need to be created in the bind-mounted repository.
- Left Docker Compose, VS Code tasks, and the Dockerfile unchanged because the corrective needs are Dev-Container-specific.

## Files And Directories Created Or Modified

Created:

- `.devcontainer/devcontainer.json`
- `.devcontainer/devcontainer-lock.json`
- `.vscode/launch.json`
- `config/settings/tests.py`
- `docs/process/devcontainer.md`
- `docs/process/EPIC2-002_feedback.md`

Modified:

- `.devcontainer/devcontainer.json`
- `Makefile`
- `.vscode/extensions.json`
- `.vscode/settings.json`
- `config/settings/base.py`
- `config/settings/production.py`
- `docs/process/EPIC2-002_feedback.md`
- `docs/process/devcontainer.md`
- `README.md`

Generated lockfile note:

- `.devcontainer/devcontainer-lock.json` is intentionally versioned because it records the resolved Dev Container Feature version and digest for `ghcr.io/devcontainers/features/common-utils:2`.

Touched with no final diff:

- `.gitignore` was temporarily changed to ignore `.codex/`, then restored before closing the ticket.

Unchanged by design:

- `docker-compose.yml`
- `.vscode/tasks.json`
- `docker/web/Dockerfile`

## Deviations From The Original Ticket

- No product-scope deviation from the ticket scope.
- `Makefile` was modified only after real Dev Container validation showed a technical need: the in-container environment does not include Docker CLI, so the official validation targets could not run from the integrated terminal.
- `docker-compose.yml` was not modified because the existing `web` and `db` services, bind mount, workspace path, and ports already matched the required workflow.
- `docs/process/devcontainer.md` was created because the ticket allowed extended permanent documentation there.
- VS Code visual validation was completed by Luis for the main Dev Container, Test Explorer, test debugging, and debug server flows.
- Codex did not add a permanent request-time hook or view only to demonstrate Django/Wagtail breakpoints. Luis decided not to spend more time now on a temporary request-time breakpoint demonstration. This validation is deferred until the first future ticket introduces a real project Python code path executed during a request.
- An experimental attempt to run Codex inside the Dev Container Remote Extension Host and persist Dev-Container-specific `CODEX_HOME` was implemented during the iteration, then reverted after manual validation showed an unstable developer experience.
- Historical host-local Codex sessions were not migrated. Final decision: Codex local remains the implementation agent, and the Dev Container remains the Python/editor/test/debug environment.

## Remaining Warnings

Known pytest warning:

```text
apps/home/tests.py::test_wagtail_admin_login_loads
  /usr/local/lib/python3.12/site-packages/django/core/handlers/base.py:61: UserWarning: No directory at: /app/staticfiles/
    mw_instance = middleware(adapted_handler)
```

Classification: known non-blocking project/test warning from EPIC2-001. It does not block `make test`, `make lint`, or `make check`.

Known Docker web logs / Django system check warnings:

```text
<class 'django.db.models.manager.BaseCollectionManagerFromCollectionQuerySet'>: (treebeard.E001) django.db.models.manager.BaseCollectionManagerFromCollectionQuerySet does not subclass treebeard.mp_tree.MP_NodeManager. This will cause an error in Treebeard 6.
<class 'django.db.models.manager.BasePageManagerFromPageQuerySet'>: (treebeard.E001) django.db.models.manager.BasePageManagerFromPageQuerySet does not subclass treebeard.mp_tree.MP_NodeManager. This will cause an error in Treebeard 6.
<class 'django.db.models.manager.BasePageManagerFromPageQuerySet'>: (treebeard.E001) django.db.models.manager.BasePageManagerFromPageQuerySet does not subclass treebeard.mp_tree.MP_NodeManager. This will cause an error in Treebeard 6.
```

Classification: known non-blocking dependency compatibility warning from EPIC2-001. It was not changed or silenced in this ticket.

Host Python tooling warning:

```text
No version is set for command python
Consider adding one of the following versions in your config file at /home/ljarufe/Projects/school-newsroom/.tool-versions
python 3.12.11
```

Classification: host tooling warning, not part of the official project runtime. The official runtime remains Docker-first.

## VS Code Problems / Diagnostics Status

Luis validated that false unresolved imports for Django and Wagtail disappeared after reopening the repository in the Dev Container. The warning `An Invalid Python interpreter is selected` appeared only in the local VS Code window before reopening in the Dev Container, because the workspace-level setting pointed at the container path `/usr/local/bin/python`.

Final clarification after returning to local Codex sessions:

- Local VS Code windows that are not reopened in the Dev Container can still show diagnostics such as `Import "wagtail.models" could not be resolved`.
- This is expected for a Docker-first repository because Django, Wagtail, pytest, and related dependencies are installed in the `web` container, not in a host virtual environment.
- This is not a project runtime failure while `make test`, `make lint`, and `make check` pass through Docker Compose.
- The accepted fix for editor accuracy is to use `Dev Containers: Reopen in Container` for Python/Pylance/Test Explorer/debug work.
- The ticket intentionally did not hide `reportMissingImports` globally and did not introduce a host `.venv` as an official workflow.

Corrective action:

- Container-specific Python interpreter and pytest settings were moved from `.vscode/settings.json` to `.devcontainer/devcontainer.json` under `customizations.vscode.settings`.
- `.vscode/settings.json` now contains only editor settings that are valid both inside and outside the Dev Container.
- django-environ inline defaults were moved into the `environ.Env(...)` schema in `config/settings/base.py`.

Expected post-correction result:

- Local VS Code should no longer warn merely because `/usr/local/bin/python` does not exist on the host.
- Inside the Dev Container, Python should still resolve to `/usr/local/bin/python`.
- Pylance should no longer report the two django-environ `NoValue` argument type diagnostics in `config/settings/base.py`.

## Test Explorer Status

Configured:

- `python.testing.pytestEnabled`: `true`
- `python.testing.unittestEnabled`: `false`
- `python.testing.pytestArgs`: `["--ds=config.settings.test", "-o", "cache_dir=/tmp/school-newsroom-pytest-cache"]`

These settings now live in Dev Container customizations.

Non-visual validation completed:

```bash
docker compose run --rm web pytest --ds=config.settings.test --collect-only -q
```

Result:

```text
apps/home/tests.py::test_wagtail_admin_login_loads
apps/home/tests.py::test_django_settings_load

2 tests collected in 0.01s
```

Luis manually validated that Test Explorer discovers the 2 current tests, can run `apps/home/tests.py`, and reports `2 passed` with the known `/app/staticfiles/` warning.

## Test Debug Status

Configured in `.vscode/launch.json`:

```text
Python: Debug tests
```

Important settings:

- `type`: `debugpy`
- `request`: `launch`
- `purpose`: `["debug-test"]`
- `DJANGO_SETTINGS_MODULE`: `config.settings.test`

Luis manually validated that `Debug Test` works, VS Code stops at a breakpoint in an existing test, Variables can be inspected, and Call Stack and Debug Console work.

## Django/Wagtail Debug Status

Configured in `.vscode/launch.json`:

```text
Django/Wagtail: Debug server
```

Important settings:

- `type`: `debugpy`
- `program`: `${workspaceFolder}/manage.py`
- `args`: `["runserver", "0.0.0.0:8001", "--noreload"]`
- `django`: `true`
- `console`: `integratedTerminal`
- `DJANGO_SETTINGS_MODULE`: `config.settings.local`

Luis manually validated that the `Django/Wagtail: Debug server` configuration works, the debug server starts from VS Code, and the general debug flow works.

Note: the current base Wagtail project has very little custom Python code that runs on every HTTP request. Codex intentionally did not add no-op product code just to create a breakpoint target. Luis decided to defer this specific validation until the first future ticket introduces a real request-time project code path.

## Manual Validation Completed By Luis

- `Dev Containers: Reopen in Container` works.
- VS Code shows `Dev Container: School Newsroom`.
- Workspace inside the container is `/app`.
- The integrated terminal is inside the container.
- Before this correction, `whoami` returned `root`.
- Container Python is `/usr/local/bin/python`.
- Python version is `3.12.13`.
- Django version is `5.2.15`.
- Wagtail version is `7.4.2`.
- pytest version is `8.4.2`.
- Local VS Code showed `An Invalid Python interpreter is selected` before reopening in the Dev Container.
- After reopening in the Dev Container, the interpreter warning disappeared and `/usr/local/bin/python` was valid.
- False unresolved imports for Django/Wagtail disappeared inside the Dev Container.
- Test Explorer discovered the 2 current tests.
- Tests can be run from Test Explorer and pass.
- `apps/home/tests.py` passes from Testing with `2 passed` and the known `/app/staticfiles/` warning.
- `Debug Test` works.
- The debugger stops at a breakpoint in an existing test.
- Variables can be inspected during test debug.
- Call Stack and Debug Console work.
- `Django/Wagtail: Debug server` works.
- The debug server can be started with VS Code.
- The general debug flow tested by Luis works.
- Post-rebuild Dev Container user validation succeeded:

```text
whoami -> vscode
id -> uid=1000(vscode) gid=1000(vscode) groups=1000(vscode)
git --version -> git version 2.47.3
ssh -V -> OpenSSH_10.0p2 Debian-7+deb13u4
HOME -> /home/vscode
```

- Ownership validation succeeded:

```text
temporary file created in /app
owner UID -> 1000
group GID -> 1000
repository on host remains owned by ljarufe:ljarufe
temporary file removed successfully
```

- The Dev Container main technical flow is validated and should be preserved.
- The Codex Remote Extension Host workflow was manually rejected after instability; Codex local remains the implementation agent.

## Manual Steps Still Required

Manual VS Code validation that remains deferred:

- Request-time debug breakpoint validation remains deferred until a future ticket introduces a real project Python code path executed during an HTTP request.

Before committing manually, Luis should review the final status and diff:

```bash
git status --short
git diff
```

Current local Codex validation from the host after the final cleanup is recorded in the command log above. The expected runtime versions remain:

```text
/usr/local/bin/python
Django 5.2.15
Wagtail 7.4.2
pytest 8.4.2
```

## Recommendations For The Next Ticket

- Keep the Makefile as the official validation interface and avoid copying its internals into editor tasks.
- Treat VS Code workflows as diagnostic tools for targeted investigation, not as replacements for `make check`.
- If manual validation finds real VS Code Problems diagnostics, classify each one before changing configuration. Do not silence diagnostics globally.
- Consider a future dependency follow-up for the Treebeard warnings only if they become blocking or if dependency versions indicate a clear upstream fix.
- Keep process feedback in `docs/process/*_feedback.md`; keep `README.md` limited to permanent developer onboarding.
- For this project, keep Codex running locally as the implementation agent unless a future ticket demonstrates a concrete need to move it into a Remote Extension Host and validates authentication/session persistence first.

## Standard Ticket Template Improvements

- Include an explicit "Manual UI Validation Pending" section for tickets that require VS Code, browser, or debugger interaction.
- Require commands to be split into "CLI validated by Codex" and "UI/manual validated by Luis".
- Ask the ticket author to identify which warnings are already known before implementation starts.
- Require a "Do not touch" section for stable files such as `Makefile`, `docker-compose.yml`, data volumes, `.env`, and Git history.
- Include a required "Post-implementation feedback update after manual validation" step so this file can be revised after Luis completes VS Code checks.
- For Docker-first repositories with Codex local as the implementation agent, do not assume the coding-agent IDE extension must run inside the Dev Container. Separate application runtime/editor language tooling, implementation agent runtime, and Docker host operations.
- Only move an agent into the Remote Extension Host when there is a demonstrated need and its authentication/session persistence has been validated.
