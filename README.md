# School Newsroom

School Newsroom is a school digital newsroom and editorial CMS built with Django, Wagtail, and PostgreSQL.

Current status: editorial MVP. The project includes Wagtail-managed news pages,
editorial sections, schools, tags, images, an SEO Assistant, adult CMS roles, a
native editorial workflow, and server-rendered public pages. It does not include
public accounts, custom authentication, automatic deployment, or a public write API.

## Stack

- Python 3.12 inside Docker
- Django 5.2 LTS
- Wagtail 7.x
- PostgreSQL 16
- spaCy 3.8 with the local Spanish `es_core_news_sm` CPU pipeline
- Docker Compose
- Gunicorn, WhiteNoise, and Caddy for manual staging deployment
- Ruff
- pytest
- pre-commit

## Requirements

Install these tools on the host machine:

- Git
- Docker
- Docker Compose
- pipx, recommended for host Git hook tooling
- VS Code, recommended for editing

The official local runtime is Docker-first. A host Python virtual environment is not required to run the project.

## Local Environment

The Docker Compose project name is `school_newsroom`.

Default local services:

| Service | Purpose                    | Local URL / Port                        |
| ------- | -------------------------- | --------------------------------------- |
| `web`   | Django/Wagtail application | `http://localhost:8000`                 |
| `db`    | PostgreSQL database        | host port `5434`, container port `5432` |

Default local database settings:

| Setting                     | Value             |
| --------------------------- | ----------------- |
| Database name               | `school_newsroom` |
| Database user               | `school_newsroom` |
| Database host inside Docker | `db`              |
| Database port inside Docker | `5432`            |

## Local Setup

Create a local environment file:

```bash
cp .env.example .env
```

Build the containers:

```bash
make build
```

Start the app:

```bash
make up
```

Keep this process running while using the local site. Run the remaining commands in another terminal.

Run migrations:

```bash
make migrate
```

Create a Wagtail admin user:

```bash
make createsuperuser
```

This command is interactive and uses the running `web` container.

Open Wagtail Admin:

```text
http://localhost:8000/admin/
```

Open the public Home:

```text
http://localhost:8000/
```

## Local Linguistic Analysis

The normal image build installs `spacy==3.8.14`, `click==8.4.2`, and the
checksum-pinned `es_core_news_sm==3.8.0` wheel. The Dockerfile smoke imports
spaCy, loads the model with `ner` excluded, and verifies sentence boundaries,
lemmas, part-of-speech tags, morphology, and dependencies. The application does
not download models during startup, requests, tests, or editorial use.

CPU is the default and the supported runtime for local development and staging.
The optional `prefer_gpu` and `require_gpu` settings only select a device when
the host already provides a compatible spaCy GPU environment; this repository
does not install CUDA, CuPy, PyTorch, transformers, or GPU drivers.

Run an explicit smoke in the normal image with:

```bash
docker compose run --rm web python -c "import spacy; nlp = spacy.load('es_core_news_sm', exclude=['ner']); print(nlp.pipe_names)"
```

The library, model, and Click workaround have distinct licenses. See
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

## Editorial News Flow

The current product language is Spanish. Wagtail Admin and public application copy are Spanish-only.

Start the local services and prepare the database:

```bash
make up
make migrate
```

Create a local Wagtail admin user if one does not already exist:

```bash
make createsuperuser
```

After migrations, configure the reproducible MVP roles and workflow:

```bash
docker compose exec web python manage.py bootstrap_mvp_access
```

The bootstrap does not create human users or passwords. Use the technical
superuser to create users and assign the generated `Director/editor` and
`Curador SEO` groups.

Use Wagtail Admin at:

```text
http://localhost:8000/admin/
```

Current editorial setup:

- Manage editorial sections through `Editorial` -> `Secciones editoriales`.
- Manage schools through `Editorial` -> `Colegios`.
- Create news through `Páginas` -> `Inicio` -> `Añadir página hija` -> `Noticia`.
- Draft news is not visible on the anonymous public Home.
- Publishing a news page through Wagtail makes it visible on the public Home.
- The news title on Home links to the public detail page.

The Spanish editor guide is available at
[`docs/editorial/guia_de_uso.md`](docs/editorial/guia_de_uso.md).

The canonical superadmin and access runbook is available at
[`docs/operations/wagtail_access_mvp.md`](docs/operations/wagtail_access_mvp.md).

## VS Code Dev Container

### Prerequisites

- Docker.
- Docker Compose.
- VS Code.
- VS Code Dev Containers extension.

### Open The Development Environment

1. Open the repository normally in VS Code.
2. Open the Command Palette.
3. Run `Dev Containers: Reopen in Container`.
4. Wait for the container and remote extensions to initialize.
5. Confirm the lower-left status bar shows `Dev Container: School Newsroom`.

The integrated terminal should open in `/app`. Python dependencies are resolved from the container, and a host `.venv` is not required. Inside the Dev Container, this command should print `/usr/local/bin/python`:

```bash
python -c "import sys; print(sys.executable)"
```

### Normal Server

The normal Django/Wagtail development server uses:

```text
http://localhost:8000/
```

Wagtail Admin uses:

```text
http://localhost:8000/admin/
```

### General Project Validation

Run full repository validation from the integrated terminal:

```bash
make test
make lint
make check
```

Use `make check` as the general validation command before reviewing a change or preparing a commit.

### Browser Regression

Run the browser regression from the host, outside the Dev Container:

```bash
make browser-test
```

This command uses `docker-compose.browser.yml` to create completely disposable
application services and a disposable database. It does not use or modify the
project's persistent database, and it removes its containers and volumes when
the run finishes, including after a test failure. No host `npm install` is
required. The first run can take longer while Docker downloads or builds the
required images.

### Targeted Tests In VS Code

Use the Testing/Test Explorer panel for focused investigation:

1. Open the Testing panel.
2. Locate the pytest tests.
3. Run a single test or a test file.

Test Explorer uses `config.settings.test`. It is useful for targeted diagnosis, but it does not replace `make check`.

### Debug A Test

1. Open the test file.
2. Add a breakpoint to an executable Python line.
3. Open Test Explorer.
4. Use `Debug Test`.
5. Inspect Variables, Watch, Call Stack, and Debug Console.

Use Continue to resume execution, Step Over to run the current line without entering called functions, Step Into to enter the function being called, and Step Out to finish the current function and return to its caller.

### Debug Django/Wagtail

1. Open Run and Debug.
2. Select `Django/Wagtail: Debug server`.
3. Press F5.

This starts a separate debug server on:

```text
http://localhost:8001/
```

The normal server remains on port `8000`. The debug profile uses `--noreload` so breakpoint behavior remains predictable. Add a breakpoint to the project Python code executed by the behavior being investigated, open port `8001`, and trigger the corresponding action.

### Ports

| Port | Purpose                                  |
| ---- | ---------------------------------------- |
| 8000 | Normal Django/Wagtail development server |
| 8001 | VS Code Django/Wagtail debug server      |
| 5434 | Host-exposed project PostgreSQL          |

### Troubleshooting

If Python imports appear unresolved, confirm the repository is actually reopened in the Dev Container and that `python -c "import sys; print(sys.executable)"` returns `/usr/local/bin/python`.

If tests do not appear, confirm pytest is enabled after opening the Dev Container and refresh Test Explorer.

For editor diagnostics, check `View -> Problems`. For Python or Pylance details, check `View -> Output` and select the relevant Python or Pylance output channel.

If port `8001` is unavailable, check the VS Code Ports panel while the debug profile is running.

More details are available in `docs/process/devcontainer.md`.

## Make Commands

```bash
make build
make up
make down
make logs
make shell
make bash
make migrate
make makemigrations
make createsuperuser
make test
make lint
make format
make migration-check
make check
make browser-test
```

Command summary:

| Command                | Description                                        |
| ---------------------- | -------------------------------------------------- |
| `make build`           | Build Docker images.                               |
| `make up`              | Start the local web and database services.         |
| `make down`            | Stop local services.                               |
| `make logs`            | Show service logs.                                 |
| `make shell`           | Open a Django shell inside the web container.      |
| `make bash`            | Open a Bash shell inside the web container.        |
| `make migrate`         | Run database migrations.                           |
| `make makemigrations`  | Create Django migrations.                          |
| `make createsuperuser` | Create a local Wagtail/Django admin user.          |
| `make test`            | Run pytest.                                        |
| `make lint`            | Run Ruff checks.                                   |
| `make format`          | Format code with Ruff.                             |
| `make migration-check` | Check for model changes missing migrations.        |
| `make check`           | Run linting, migration drift, and tests.           |
| `make browser-test`    | Run the disposable host-side browser regression.   |

## Quality Tools

Run tests:

```bash
make test
```

Run Ruff linting:

```bash
make lint
```

Format code:

```bash
make format
```

Create migrations after model changes:

```bash
make makemigrations
```

Check for missing migrations without writing files:

```bash
make migration-check
```

Apply migrations:

```bash
make migrate
```

Run all required checks:

```bash
make check
```

## Git Hooks

This project uses `pre-commit` for fast commit-time checks and a pre-push hook that runs the general repository validation command.

If you run Git on the host, install `pre-commit` on the host:

```bash
pipx install "pre-commit>=4.2,<5.0"
```

If you run Git inside the Dev Container, `pre-commit` is available from the project Python dependencies.

Install the commit and pre-push hooks where you run Git:

```bash
pre-commit install
```

The normal pre-commit stage is intentionally fast and staged-file oriented. It configures:

- Ruff check
- Ruff format
- end-of-file-fixer
- trailing-whitespace
- check-yaml
- check-toml

Run the commit hooks manually:

```bash
pre-commit run --all-files
```

Run the pre-push hook manually without pushing:

```bash
pre-commit run --hook-stage pre-push --all-files
```

The pre-push hook runs `make check`. On the host, `make check` delegates to Docker Compose. Inside the Dev Container, it uses the current container runtime directly. Pull requests should use `.github/pull_request_template.md`.

## Project Structure

```text
school-newsroom/
├── apps/
│   ├── home/
│   └── news/
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── local.py
│   │   ├── test.py
│   │   └── production.py
│   ├── urls.py
│   └── wsgi.py
├── docker/
│   └── web/
│       └── Dockerfile
├── docs/
│   ├── adr/
│   ├── ops/
│   ├── process/
│   └── product/
├── static/
├── templates/
├── docker-compose.yml
├── Makefile
├── manage.py
├── pyproject.toml
├── pytest.ini
└── requirements.txt
```

## Environment Variables

Copy `.env.example` to `.env` for local development.

Important variables:

| Variable                 | Purpose                                                                    |
| ------------------------ | -------------------------------------------------------------------------- |
| `DJANGO_SETTINGS_MODULE` | Django settings module. Defaults to `config.settings.local` locally.       |
| `DJANGO_SECRET_KEY`      | Local development secret key. Use a real secret outside local development. |
| `DJANGO_DEBUG`           | Enables/disables debug mode.                                               |
| `DJANGO_ALLOWED_HOSTS`   | Comma-separated allowed hosts.                                             |
| `DATABASE_URL`           | PostgreSQL connection URL used by Django.                                  |
| `POSTGRES_DB`            | PostgreSQL database created by Docker.                                     |
| `POSTGRES_USER`          | PostgreSQL user created by Docker.                                         |
| `POSTGRES_PASSWORD`      | PostgreSQL password created by Docker.                                     |
| `SEO_NLP_MODEL`          | Local spaCy pipeline package; defaults to `es_core_news_sm`.                |
| `SEO_NLP_DEVICE`         | `cpu`, `prefer_gpu`, or `require_gpu`; defaults to `cpu`.                   |
| `SEO_NLP_MAX_CHARACTERS` | Maximum visible characters per advanced analysis; defaults to `50000`.     |

`.env` is local-only and must not be committed.

## Local advanced readability

The SEO Admin analysis uses the existing ordered `ContentSegment` snapshot and
one batched spaCy inference for keyphrase and advanced-readability rules. spaCy
objects remain inside `apps.news.seo.nlp`; immutable project structures expose
sentence membership, token offsets, POS, morphology, dependency labels, and
head indexes to the rules. Results are request-derived, are not persisted, and
are not cached.

Advanced readability accepts only visible `paragraph`, `list`, and `quote`
body segments. Headings preserve editorial boundaries but do not contribute
words. Titles, SEO metadata, tables, image metadata, taxonomy, credits, and
internal fields are excluded. Each segment is parsed as a separate document,
so sentences cannot cross block boundaries. Text above
`SEO_NLP_MAX_CHARACTERS` is not truncated.

`pyphen==0.17.2` supplies its bundled generic Spanish dictionary offline.
`Pyphen(lang="es_ES")` resolves to `pyphen/dictionaries/hyph_es.dic`; no
startup or request-time download is used. The image build verifies the package
version, dictionary resolution, file presence, and a real Spanish hyphenation.
The artifact and dictionary notices and hashes are recorded in
`THIRD_PARTY_NOTICES.md`.

Flesch-Szigriszt is calculated only with at least 100 words and three parser
sentences:

```text
206.835 - 62.3 * (syllables / words) - (words / sentences)
```

INFLESZ boundaries are `40`, `55`, `65`, and `80`; values below `55` need
review and values from `55` are good for this finding only. The other rule
thresholds and the fixed connector lexicon live in
`apps/news/seo/advanced_readability.py` and are covered by causal boundary
tests. Advanced findings never contribute to the SEO assistant's overall
status. A spaCy failure leaves all eight unavailable, while a Pyphen-only
failure leaves the first seven available and only disables Flesch-Szigriszt.

## Troubleshooting

### Docker daemon permission errors

If Docker commands fail because the current user cannot access the Docker daemon, confirm Docker is running and that your user has permission to run Docker commands.

```bash
docker ps
```

### Database is not ready yet

Docker Compose starts services in order, but PostgreSQL may still need a few seconds before accepting connections. The project includes a lightweight readiness check for database-dependent commands. If a command still fails during startup, wait a moment and run it again.

### Wagtail Admin redirects from `/admin/`

Unauthenticated requests to `/admin/` redirect to the login page. This is expected behavior.

Expected local login URL:

```text
http://localhost:8000/admin/login/?next=/admin/
```

### VS Code or Pylance cannot resolve Django/Wagtail imports

The project runs inside Docker, so dependencies are installed in the container. If VS Code uses the host Python interpreter, Pylance may show unresolved import warnings even when the application and tests work correctly.

Use `Dev Containers: Reopen in Container` so VS Code uses the Python environment inside the `web` service. A host Python virtual environment is not part of the official local workflow.

### Wagtail / Treebeard warnings

Wagtail system checks may report Treebeard compatibility warnings in the current dependency set. These warnings do not block migrations, admin startup, or tests in the current setup.

## Manual Demo/Staging Operations

The repository includes a standalone, production-like staging topology for a
manual Oracle Always Free deployment. It does not modify the local development
Compose topology and does not deploy automatically.

- [Oracle Always Free staging runbook](docs/operations/oracle_always_free_staging.md)
- [Oracle staging UAT](docs/operations/oracle_staging_uat.md)
- [Wagtail MVP access runbook](docs/operations/wagtail_access_mvp.md)

Real staging secrets belong in `/etc/school-newsroom/staging.env`, never in the
repository. Oracle capacity, cost eligibility, DNS, HTTPS, public firewall,
reboot persistence, and browser UAT require maintainer validation on the real
environment.

## Current Scope

Included in the current base setup:

- Django/Wagtail project structure
- Split settings for local, test, and production
- Docker Compose with web and PostgreSQL services
- Makefile workflow
- Ruff, pytest, and pre-commit configuration
- Initial editorial news core with Wagtail snippets and pages
- Minimal `home` app and focused editorial tests
- VS Code recommendations and tasks
- Manual Oracle demo/staging Compose, proxy, and operations documentation

Not included yet:

- Public API
- Redis/Celery workers
- External media storage
- Automatic deployment
- Final public frontend design
