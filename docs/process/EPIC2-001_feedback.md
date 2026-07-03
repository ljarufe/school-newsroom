# EPIC2-001 Closing Report

## Ticket

Create the base repository and local environment for School Newsroom.

Operational project name: Noticias.
Technical project name: School Newsroom.
Repository name: `school-newsroom`.

## Final Summary

EPIC2-001 was completed as a Docker-first base setup for a Django + Wagtail + PostgreSQL project. The repository now contains the initial project structure, split settings, local Docker environment, Makefile workflow, lint/test tooling, VS Code recommendations, README instructions, `.env.example`, and an initial minimal `home` app with smoke tests.

The project can build, run migrations, start Wagtail Admin, and pass the configured quality checks. No news models, SEO features, roles, API, Redis, Celery, deployment configuration, or final frontend work were added.

## Commands Successfully Run

- `make build`
- `make migrate`
- `make test`
- `make lint`
- `make format`
- `make check`
- `docker compose up -d`
- `docker compose ps`
- `docker compose logs --tail=80 web`
- Internal container HTTP check for Wagtail Admin:
  `docker compose exec web python -c "from urllib.request import urlopen; response = urlopen('http://127.0.0.1:8000/admin/'); print(response.status, response.geturl())"`

Observed successful admin response:

```text
200 http://127.0.0.1:8000/admin/login/?next=/admin/
```

Latest validation results:

```text
make test  -> 2 passed
make lint  -> All checks passed
make check -> Ruff passed, pytest 2 passed
```

## Commands Not Run And Why

- `make createsuperuser`: not run because it is intentionally interactive and requires Luis to choose real local admin credentials.
- Browser login into `http://localhost:8000/admin/`: not completed by Codex because it requires manual browser interaction and the superuser credentials.
- Git commit and push: not run because the ticket explicitly reserves commit and push for Luis after manual validation.
- Planka health check: not run because the implementation did not touch Planka and no Planka validation was required for the repository changes.

## Problems Encountered During Implementation

- Docker Buildx initially failed inside the sandbox because it attempted to write under `~/.docker`, which was outside the writable workspace.
- Docker Compose commands initially needed elevated access to the Docker daemon.
- `depends_on` in Docker Compose did not guarantee that PostgreSQL was ready before Django commands ran.
- The initial admin test expected `/admin/` to return `200`, but Wagtail correctly redirects unauthenticated users to `/admin/login/?next=/admin/`.
- Tests initially loaded `config.settings.local` from `.env` instead of the intended `config.settings.test`.
- Tests initially failed with WhiteNoise manifest storage because static files had not been collected.
- Tests initially failed when rendering the Wagtail login page because the test used the database without the `pytest.mark.django_db` marker.
- The first host-level `curl -I http://localhost:8000/admin/` check failed from the sandbox even though Docker showed the web container running and port `8000` exposed.
- `.venv/` was not explicitly ignored in the first review pass.
- `README.md` initially included internal project-management/process notes that do not belong in repository onboarding documentation, including local Planka context, Codex workflow guidance, and a one-time first-push checklist.

## Failed Attempts Or Retries

- `make build` failed once due to sandbox restrictions on `~/.docker`; it passed after rerunning with approved Docker access.
- `make test` failed once because `/admin/` returned a redirect instead of `200`; the test was updated to follow the redirect.
- `make check` failed once because tests inherited WhiteNoise manifest static storage; test settings were updated to use standard static file storage.
- `make check` failed once because the Wagtail admin login render accessed the database; the test was marked with `pytest.mark.django_db`.
- Host `curl` to `localhost:8000` failed from the sandbox; the admin endpoint was then validated from inside the running `web` container.

## Root Causes

- The execution sandbox restricts writes outside the workspace and restricts direct Docker daemon access unless approved.
- Docker Compose `depends_on` controls startup order, not service readiness.
- Wagtail Admin redirects anonymous users to the login page by design.
- `.env` can override `pytest.ini` when `DJANGO_SETTINGS_MODULE` is already present in the environment.
- WhiteNoise manifest storage expects collected static assets when `DEBUG=False`.
- Wagtail admin templates query Wagtail locale data during render, so pytest must allow database access for that test.
- The sandbox cannot always reach host-published Docker ports even when containers are healthy.

## Solutions Applied

- Added a lightweight `nc` wait loop before starting the development server and before database-dependent Makefile commands.
- Updated `make test` to force `DJANGO_SETTINGS_MODULE=config.settings.test`.
- Updated test static storage to use `django.contrib.staticfiles.storage.StaticFilesStorage`.
- Updated the Wagtail admin test to follow the expected login redirect.
- Added `pytest.mark.django_db` to the admin login test.
- Validated Wagtail Admin from inside the running `web` container.
- Added explicit ignore coverage for `.venv/`.
- Clarified in the README that `make createsuperuser` is interactive and uses the running `web` container.
- Cleaned `README.md` so it focuses on developer onboarding, local setup, project structure, commands, environment variables, and troubleshooting. Removed unrelated local-tool notes, agent workflow notes, and one-time first-push process content.

## Files And Directories Created

- `.dockerignore`
- `.env`
- `.env.example`
- `.gitignore`
- `.pre-commit-config.yaml`
- `.vscode/extensions.json`
- `.vscode/settings.json`
- `.vscode/tasks.json`
- `Makefile`
- `README.md`
- `apps/__init__.py`
- `apps/home/__init__.py`
- `apps/home/apps.py`
- `apps/home/models.py`
- `apps/home/migrations/__init__.py`
- `apps/home/migrations/0001_initial.py`
- `apps/home/tests.py`
- `config/__init__.py`
- `config/settings/__init__.py`
- `config/settings/base.py`
- `config/settings/local.py`
- `config/settings/test.py`
- `config/settings/production.py`
- `config/urls.py`
- `config/wsgi.py`
- `docker-compose.yml`
- `docker/web/Dockerfile`
- `docs/adr/.gitkeep`
- `docs/ops/.gitkeep`
- `docs/process/EPIC2-001_feedback.md`
- `docs/product/.gitkeep`
- `manage.py`
- `media/.gitkeep`
- `pyproject.toml`
- `pytest.ini`
- `requirements.txt`
- `static/.gitkeep`
- `templates/404.html`
- `templates/500.html`
- `templates/home/home_page.html`

## Ignored Local Files And Directories

- `.env`
- `.venv/`
- `media/*`, except `media/.gitkeep`
- `__pycache__/`
- `.pytest_cache/`
- `.ruff_cache/`
- `.mypy_cache/`
- `staticfiles/`
- common OS/editor temporary files

## Deviations From The Original Ticket

- A local `.env` file was created to run Docker Compose commands. This is allowed by the ticket as long as `.env` remains untracked.
- PostgreSQL is exposed to the host on `5434:5432`. The ticket allowed this port if host exposure was needed.
- The Wagtail Admin HTTP validation was completed from inside the container because sandbox-level host `curl` could not connect to `localhost:8000`.
- The implementation uses Wagtail 7.4.x, the current compatible Wagtail version resolved during the build.
- Wagtail installs `djangorestframework` as a transitive dependency. The project did not add DRF as a direct project dependency and did not implement an API.

## Remaining Warnings

Wagtail system checks currently report Treebeard compatibility warnings:

```text
treebeard.E001: django.db.models.manager.BaseCollectionManagerFromCollectionQuerySet does not subclass treebeard.mp_tree.MP_NodeManager.
treebeard.E001: django.db.models.manager.BasePageManagerFromPageQuerySet does not subclass treebeard.mp_tree.MP_NodeManager.
```

These warnings do not block migrations, admin startup, or tests in the current setup. They appear to be dependency-level compatibility warnings related to future Treebeard 6 behavior.

Pytest also reports this non-blocking warning:

```text
No directory at: /app/staticfiles/
```

This does not block tests. `staticfiles/` is intentionally generated output and is ignored.

## Documentation Scope Correction

`README.md` should be treated as developer-facing repository documentation, not as a place for internal planning, local infrastructure context, agent workflow instructions, or one-time ticket checklists.

Correction applied/recommended:

- Remove Planka-specific notes from `README.md`; Planka is outside this repository and belongs in project/process context documents only.
- Remove Codex workflow notes from `README.md`; agent workflow belongs in ticket templates, process docs, or feedback documents.
- Remove the “Ready for First Push” checklist from `README.md`; it was a one-time ticket validation checklist, not permanent repository documentation.
- Keep the README focused on what another developer needs to install, configure, run, test, and troubleshoot the project.
- If a port is documented in the README, document only the port used by this repository, not the reason tied to unrelated local tools.

Future ticket guidance:

- Do not copy ticket acceptance criteria verbatim into the README unless they are permanent developer instructions.
- Do not include user-specific local environment details in repository docs.
- Do not include agent-specific workflow instructions in repository docs.
- Put planning/project-management/tooling context in `docs/process/` or the ticket feedback file instead.

## Technical Debt / Follow-up Items

### DEVX-001 — Add VS Code Dev Container Support

A cleaner future improvement is to add a `.devcontainer/` setup so VS Code can use the Docker-based development environment directly instead of analyzing the project with the host Python interpreter.

Context:

- The project intentionally follows a Docker-first workflow.
- Dependencies such as Django and Wagtail are installed inside the Docker image/container.
- VS Code/Pylance may show unresolved import warnings on the host, for example `Import "wagtail.models" could not be resolved` or Django import resolution warnings, even when Docker commands, tests, and runtime are working correctly.
- A local `.venv` can be used as an editor-only workaround, but it should not become the official runtime path.

Recommended future ticket:

```text
DEVX-001 — Add VS Code Dev Container for Docker-first development
```

Suggested scope:

- Add `.devcontainer/devcontainer.json`.
- Reuse the existing Docker Compose services where possible.
- Configure VS Code to attach to the `web` service/container.
- Ensure Python interpreter, Pylance, Ruff, pytest, and terminal commands run inside the container.
- Keep `make` commands as the official workflow.
- Document how to open/reopen the repository in the container.
- Do not add application features, news models, SEO, roles, API, deploy, Redis, Celery, or unrelated tooling.
- Do not use port `5433`.

Suggested acceptance criteria:

- VS Code can reopen the project in a dev container.
- Pylance resolves Django and Wagtail imports without requiring a host `.venv`.
- `make test`, `make lint`, and `make check` work from the integrated terminal.
- The existing Docker-first workflow remains unchanged for normal CLI usage.
- README or `docs/process/` explains the dev container workflow.
- `.devcontainer/` does not introduce secrets or production-only configuration.

Priority:

- Medium.
- Recommended before the project grows significantly, especially if multiple contributors or Codex/VS Code workflows will be used regularly.
- Not required to close EPIC2-001 because the runtime and quality checks already pass.

## Local Ports Used

- Web: `8000:8000`
- PostgreSQL: `5434:5432`

Port `5433` was not used.

## Planka Confirmation

Planka was not touched. No Planka files, services, configuration, ports, or database settings were modified.

Port `5433`, reserved for Planka PostgreSQL, was not used.

## Manual Steps Completed By Luis

Based on the ticket context and repository state:

- Local project directory exists at `~/Projects/school-newsroom`.
- Git repository is initialized.
- The project was opened in VS Code.
- Luis requested pre-commit review before the first commit.

## Manual Steps Still Required

- Run or keep the app running with `make up`.
- Run `make createsuperuser` in another terminal and create local Wagtail admin credentials.
- Open `http://localhost:8000/admin/` in a browser.
- Log in with the created superuser.
- Review `git status`.
- Review `git diff`.
- Confirm no generated files or large files are staged.
- Confirm `.env` is not tracked.
- Optionally confirm Planka manually if desired.
- Create the first commit manually.
- Push the initial branch manually.

Suggested commit message after validation:

```text
chore: create base Django Wagtail project
```

## Recommendations For EPIC2-002

- Keep EPIC2-002 narrow and avoid adding multiple product domains at once.
- Prefer one of these next scopes:
  - Create the first real Wagtail home page setup and initial site tree data.
  - Add a deterministic initial data command for the root/home page if needed.
  - Add basic project documentation for local developer operations.
- Do not add `news`, `seo`, `schools`, roles, API, Redis, Celery, storage, or deploy work unless EPIC2-002 explicitly scopes one of them.
- If the next ticket touches Wagtail pages, include acceptance criteria for migrations, admin editing, and public page rendering.
- Consider pinning exact dependency versions or adding a lock strategy before the project grows.
- Consider adding a `make status` or `make ps` command if Docker workflow diagnostics become common.
- Consider creating a dedicated `DEVX-001` ticket for `.devcontainer/` support before or alongside EPIC2-002, so VS Code/Pylance uses the container environment and does not require a host `.venv`.
- Add a README scope check to the next ticket review: README changes must be useful for developers onboarding to the repository and must not include unrelated local tools, agent workflow, or one-time ticket process checklists.

## Standard Ticket Template Improvements

Future tickets should include:

- A required "Commands to run" section split into automated commands and manual interactive commands.
- A required "Commands not to run" section for commit, push, deploy, or external systems.
- A "Sandbox/Docker notes" section that anticipates Docker daemon access and host port validation limits.
- A "Expected warnings" section to distinguish acceptable dependency warnings from blockers.
- A "Generated/ignored files" checklist.
- A "Manual validation" checklist that explicitly covers browser actions and credentials.
- A "Developer Experience / IDE validation" checklist for Docker-first projects, including whether VS Code/Pylance needs a dev container or editor-only interpreter workaround.
- A "README/documentation scope" check: permanent repository docs should contain setup, usage, architecture, troubleshooting, and developer onboarding only; ticket process, local external tools, and agent workflow instructions should stay in process docs or feedback files.
- A "Feedback file requirements" section so the closing report format is consistent across tickets.
