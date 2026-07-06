# School Newsroom

School Newsroom is a school digital newsroom and editorial CMS built with Django, Wagtail, and PostgreSQL.

Current status: base project only. This repository does not yet include news models, SEO workflows, editorial roles, public API, deployment, or final frontend work.

## Stack

- Python 3.12 inside Docker
- Django 5.2 LTS
- Wagtail 7.x
- PostgreSQL 16
- Docker Compose
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
make check
```

Command summary:

| Command                | Description                                   |
| ---------------------- | --------------------------------------------- |
| `make build`           | Build Docker images.                          |
| `make up`              | Start the local web and database services.    |
| `make down`            | Stop local services.                          |
| `make logs`            | Show service logs.                            |
| `make shell`           | Open a Django shell inside the web container. |
| `make bash`            | Open a Bash shell inside the web container.   |
| `make migrate`         | Run database migrations.                      |
| `make makemigrations`  | Create Django migrations.                     |
| `make createsuperuser` | Create a local Wagtail/Django admin user.     |
| `make test`            | Run pytest.                                   |
| `make lint`            | Run Ruff checks.                              |
| `make format`          | Format code with Ruff.                        |
| `make check`           | Run linting and tests.                        |

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
│   └── home/
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

`.env` is local-only and must not be committed.

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

## Current Scope

Included in the current base setup:

- Django/Wagtail project structure
- Split settings for local, test, and production
- Docker Compose with web and PostgreSQL services
- Makefile workflow
- Ruff, pytest, and pre-commit configuration
- Minimal `home` app and smoke tests
- VS Code recommendations and tasks

Not included yet:

- News/article models
- SEO assistant or Yoast-like workflow
- Editorial roles and permissions
- Public API
- Redis/Celery workers
- External media storage
- Deployment configuration
- Final public frontend design
