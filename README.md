# School Newsroom

School Newsroom is the technical repository for the Noticias planning project: a school digital newsroom and editorial CMS built with Django, Wagtail, and PostgreSQL.

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

## Local Environment Decisions

The official local workflow is Docker-first. Do not use a local Python virtual environment as the main runtime for this project.

The Docker Compose project name is `school_newsroom`. The local database name and user are both `school_newsroom`.

Do not use port `5433`; it is reserved for Planka. If PostgreSQL is exposed to the host, this project uses `5434:5432`.

## Requirements

- Git
- Docker
- Docker Compose
- VS Code, recommended for editing

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

`make check` runs linting and tests.

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

## Planka Notes

Planka remains outside this repository. This project must not touch the Planka installation or use Planka's reserved PostgreSQL port `5433`.

## Codex Workflow

Work should proceed ticket by ticket:

1. Use the ticket Markdown as the source of truth.
2. Keep code, filenames, app names, comments, and technical docs in English.
3. Implement only the scope of the current ticket.
4. Add a feedback Markdown file after development to document problems, fixes, and recommendations for the next ticket.
5. Luis reviews, validates, commits, and pushes manually.

## Ready for First Push

Do not commit or push until this checklist has been reviewed:

- `make build` works.
- `make up` starts `web` and `db`.
- `make migrate` runs without errors.
- `make createsuperuser` can create an admin user.
- `http://localhost:8000/admin/` loads Wagtail Admin.
- Admin login works with the created superuser.
- `make test` passes.
- `make lint` passes.
- `make format` runs.
- `make check` passes.
- `.env` exists only locally and is not tracked.
- `.env.example` exists and contains no real secrets.
- `.gitignore` excludes `.env`, `media/`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, and temporary files.
- No large or generated files were added accidentally.
- Planka was not touched.
- Port `5433` was not used.
- `git status` was reviewed.
- `git diff` was reviewed.

After the checklist passes, Luis can commit and push manually.
