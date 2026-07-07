# EPIC2-005 Implementation Feedback

## Ticket

Add automatic Pull Request validation with GitHub Actions for School Newsroom.

## Implementation Summary

Created the first minimal GitHub Actions workflow for Pull Requests targeting `main`.
The workflow prepares a local CI environment from `.env.example`, confirms Docker
Compose is available, and delegates repository validation to `make check`.

No deploy workflow, branch protection, cache, version matrix, coverage reporting,
product feature, or Makefile rewrite was added.

## Files Created Or Modified

- Created `.github/workflows/pr-validation.yml`.
- Created `docs/process/EPIC2-005_feedback.md`.

## Workflow Configuration

- Workflow name: `Pull Request Validation`.
- Job id: `validate`.
- Job name: `Validate repository`.
- Trigger: `pull_request` against base branch `main`.
- Trigger types: `opened`, `reopened`, `synchronize`.
- Runner: `ubuntu-latest`.
- Checkout action: `actions/checkout@v7`.
- Declared permissions: `contents: read`.
- Validation command: `make check`.
- The workflow does not use `pull_request_target`.
- The workflow does not define `push`, `workflow_dispatch`, `schedule`, deploy,
  caching, matrices, coverage, CodeQL, or Dependabot behavior.

## CI Environment Preparation

The workflow creates `.env` with:

```bash
cp .env.example .env
```

`.env.example` was inspected before using it. It contains local development and
test-suitable values only:

- `DJANGO_SECRET_KEY=change-me`
- `DJANGO_DEBUG=true`
- localhost allowed hosts
- local Docker Compose PostgreSQL database name, user, password, host, port, and
  `DATABASE_URL`

No production database credentials, real Django secret key, cloud credentials,
GitHub secrets, personal tokens, Planka credentials, or other production values
were found or added.

## Clean-Environment Evidence Available To Codex

The real repository state was inspected before editing:

- Active branch: `EPIC2-005-pr-validation-ci`.
- Initial `git status --short`: clean.
- Existing `.github` content: `.github/pull_request_template.md` only; no
  existing workflows.
- `docker-compose.yml` defines a `build:` section for the `web` service.
- `Makefile` defines `make check` as `lint test`, and both targets use
  `docker compose run --rm web`.

Codex could not fully reproduce a pristine GitHub-hosted runner because the local
Docker daemon already had a usable project image. The available local evidence
showed Docker Compose was available and the Compose configuration was valid.

No `make build` step was added and the Makefile was not modified because no
actual portability defect or clean-runner failure was demonstrated during this
implementation pass.

## Automated Validation Completed Locally

Required final local validation:

- `pre-commit run check-yaml --files .github/workflows/pr-validation.yml`
  - Passed.
- `make check`
  - Passed.
  - Ruff reported `All checks passed!`.
  - Pytest reported `9 passed`.
- `git diff --check`
  - Passed.

Additional local checks:

- `docker compose version`
  - Passed.
- `docker compose config --quiet`
  - Passed.
- `docker compose images`
  - Passed after Docker daemon access was available.
- `docker compose run --rm web true`
  - Passed after Docker daemon access was available.

## Failed Attempts And Retries

- `docker compose images`
  - First attempt failed because the Codex sandbox could not access the Docker
    daemon socket.
  - Retried with Docker daemon access and passed.

No workflow YAML validation, `make check`, or `git diff --check` retry was
needed after the final files were in place.

## GitHub Pull Request Validation Deferred To Luis

The real GitHub Actions entry point cannot be proven by local YAML validation
alone. Luis still needs to validate the real Pull Request integration after
pushing this branch and opening or updating a Pull Request against `main`.

Positive path still required:

- Open or update the Pull Request against `main`.
- Confirm the workflow starts automatically.
- Confirm the visible check corresponds to
  `Pull Request Validation / Validate repository`.
- Confirm the logs show `make check`.
- Confirm Ruff and pytest run inside that validation.
- Confirm the run finishes green.

Controlled negative path still required:

- Introduce a temporary deterministic Ruff failure in the branch.
- Push/update the Pull Request.
- Confirm the same `Validate repository` check turns red because Ruff fails.
- Restore the temporary failure immediately.
- Push/update the Pull Request again.
- Confirm the same check returns green.
- Confirm no temporary regression remains in the final diff.

Restoration and final green-run validation are therefore deferred to Luis.

## Warnings And Known Differences

- Local validation proves the workflow file is syntactically valid and the
  repository validation command passes in the available local Docker environment.
- Local validation does not prove GitHub will trigger the workflow or display the
  check on the Pull Request.
- The local Docker environment was not pristine because the project image already
  existed.
- No secrets were added to the workflow or feedback.
- `staticfiles/` remains generated output and untracked.

## Reusable Process Learning

- A ticket that adds GitHub Actions must separate local configuration validation
  from real GitHub-hosted runner validation.
- `make check` remains the stable repository validation interface; workflow YAML
  should not duplicate Ruff or pytest internals while that interface exists.
- Branch protection or GitHub rulesets should be handled as a separate follow-up
  ticket after the PR validation workflow has real successful-run evidence.
- If the real GitHub runner later proves that `make check` does not build the
  service image as needed, the next correction should document the exact runner
  failure and choose the smallest fix between Makefile portability and a
  workflow-only `make build` preparation step.

## AGENTS And Process Follow-Up Evaluation

No repository `AGENTS.md` change is needed for this ticket. The current rules
already cover Docker-first validation, Makefile usage, feedback files, secrets,
privacy, and leaving commits, pushes, and merges to the maintainer.

The external process source and living ticket guide should not be changed by
Codex during EPIC2-005. After a real GitHub Actions positive path and controlled
negative path pass, it would be reasonable to treat CI as a permanent PR gate in
the external process source. Requiring the check before merge should be tracked
as a separate branch protection or ruleset ticket, not implemented here.
