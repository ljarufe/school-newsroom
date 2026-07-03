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

## Pre-commit

Pre-commit is installed inside the Docker image. This project configures:

- Ruff check
- Ruff format
- end-of-file-fixer
- trailing-whitespace
- check-yaml
- check-toml

To run pre-commit manually inside the container:

```bash
docker compose exec web pre-commit run --all-files
```

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

Current options:

- Treat those warnings as editor-only warnings if Docker commands pass.
- Create a local `.venv` only for editor IntelliSense, not as the official runtime.
- Add a future `.devcontainer/` setup so VS Code uses the container environment directly.

### Static files warning in tests

A warning like this may appear during tests:

```text
No directory at: /app/staticfiles/
```

This is non-blocking in the current local setup. `staticfiles/` is generated output and is ignored.

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
