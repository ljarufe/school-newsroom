# EPIC2-005 Closing Draft

## Ticket

Add automatic Pull Request validation with GitHub Actions for School Newsroom.

Pull Request: PR #4.

## Implementation Summary

EPIC2-005 added the first minimal GitHub Actions Pull Request validation workflow
for School Newsroom. The workflow runs on Pull Requests targeting `main`,
prepares a CI `.env` from `.env.example`, checks Docker Compose availability,
and delegates repository validation to `make check`.

No deploy workflow, branch protection, cache, version matrix, coverage reporting,
product feature, Docker Compose change, or Makefile change was added.

## Files Created Or Modified

- Created `.github/workflows/pr-validation.yml`.
- Created `docs/process/EPIC2-005_feedback.md`.

## Workflow Configuration

- Workflow name: `Pull Request Validation`.
- Job id: `validate`.
- Job/check name: `Validate repository`.
- Trigger: `pull_request` against base branch `main`.
- Trigger types: `opened`, `reopened`, `synchronize`.
- Runner: `ubuntu-latest`.
- Checkout action: `actions/checkout@v7`.
- Checkout credential persistence: `persist-credentials: false`.
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

## CI UAT Completed Before Review Correction

The real GitHub-hosted runner validated the initial workflow through PR #4.

Observed positive-path evidence:

- Workflow: `Pull Request Validation`.
- Job/check: `Validate repository`.
- The workflow ran from the real Pull Request entry point.
- The workflow completed green.
- The observed duration was approximately 45-50 seconds.
- The clean GitHub-hosted runner reached `make check`.
- Docker Compose automatically built the `school_newsroom-web` image on the
  clean runner.
- No explicit `make build` workflow step was required.
- No Makefile portability correction was required.
- Ruff passed.
- pytest reported `9 passed`.

This real runner evidence proved `make check` is self-sufficient for the current
clean GitHub-hosted runner path.

## Controlled Negative Path

Luis completed the controlled negative-path validation in PR #4.

A temporary file was introduced:

```text
apps/home/_ci_ruff_failure.py
```

with:

```python
import os
```

Local Ruff and pre-push validation hooks were selectively skipped only for this
deliberate remote CI probe so the regression could reach the GitHub Actions gate.

The workflow ran again through the `synchronize` event and failed red in the
expected validation stage. The observed Ruff failure was:

```text
F401 [*] `os` imported but unused
 --> apps/home/_ci_ruff_failure.py:1:8
  |
1 | import os
  |        ^^
  |
help: Remove unused import: `os`
Found 1 error.
[*] 1 fixable with the `--fix` option.
make: *** [Makefile:51: lint] Error 1
Error: Process completed with exit code 2.
```

This proves a Ruff failure makes the real
`Pull Request Validation / Validate repository` GitHub check fail.

## Restoration Evidence

The temporary Ruff probe was removed immediately after the negative-path run.
The restoration commit and push used the normal local hooks again.

Observed restoration evidence:

- `apps/home/_ci_ruff_failure.py` is absent from the final Pull Request delta.
- GitHub Actions ran again after restoration.
- The final validation returned green.
- `make check` passed.
- Ruff passed.
- pytest reported `9 passed`.

No temporary validation regression remains in the final repository state.

## Codex Review Finding And Correction

Codex Review was configured to run automatically when PR #4 was opened, so no
manual `@codex review` comment was needed for the initial review.

Codex Code Review produced one actionable P1 finding on
`.github/workflows/pr-validation.yml`: disable persisted checkout credentials for
Pull Request validation.

The finding is valid. This workflow uses the `pull_request` event, checks out
submitted Pull Request code, and then executes `make check`. A Pull Request can
modify files that `make check` executes, including the Makefile or tests.
`actions/checkout@v7` persists credentials for authenticated Git commands by
default, but this validation job does not need authenticated Git operations after
checkout.

The checkout step was corrected from:

```yaml
      - name: Check out repository
        uses: actions/checkout@v7
```

to:

```yaml
      - name: Check out repository
        uses: actions/checkout@v7
        with:
          persist-credentials: false
```

No Pull Request event, workflow permission, Makefile, Docker Compose, or
validation strategy change was made for this review correction.

## Validation After Checkout-Credential Correction

Validation completed locally after adding `persist-credentials: false`:

- `pre-commit run check-yaml --files .github/workflows/pr-validation.yml`
  - Passed.
- `make check`
  - Passed.
  - Ruff reported `All checks passed!`.
  - pytest reported `9 passed`.
- `git diff --check`
  - Passed.

GitHub Actions has not yet been observed on the corrected workflow head at the
time of this feedback update.

## Validation Still Required After Correction

Remaining maintainer validation:

- Commit and push the correction through the normal local hooks.
- Confirm GitHub Actions runs on the corrected workflow head.
- Confirm the corrected `Pull Request Validation / Validate repository` check is
  green.
- Request or review a fresh Codex Review result for the corrected PR head if
  needed.
- Resolve the GitHub review thread only after confirming the correction at the
  PR level.

No commit, push, review-thread resolution, PR reply, merge, or branch protection
change was performed by Codex.

## Failed Attempts And Retries

Initial implementation pass:

- `docker compose images`
  - First attempt failed because the Codex sandbox could not access the Docker
    daemon socket.
  - Retried with Docker daemon access and passed.

Checkout-credential correction pass:

- No workflow YAML validation, `make check`, or `git diff --check` retry was
  needed after the correction.

## Warnings And Known Differences

- Local validation proves the workflow file is syntactically valid and the
  repository validation command passes in the available local Docker environment.
- The real GitHub-hosted runner proved the initial workflow entry point, clean
  runner image build, positive path, negative Ruff path, and restoration path.
- GitHub Actions has not yet been observed on the PR head that includes
  `persist-credentials: false`.
- No secrets were added to the workflow or feedback.
- `staticfiles/` remains generated output and untracked.

## Reusable Process Learning

- Real GitHub Actions entry-point validation proved `make check` works on a
  clean GitHub-hosted runner and builds the Compose service image automatically.
- A CI workflow that executes submitted Pull Request code should avoid persisting
  checkout credentials when authenticated Git commands are unnecessary.
- Automatic Codex Review may run when a Pull Request is opened in the current
  repository configuration, so an explicit `@codex review` comment is not always
  required for the initial review.
- After a review finding changes the PR head, a fresh review of the corrected
  head may still be requested explicitly.
- Branch protection or GitHub rulesets remain a separate follow-up ticket after
  the workflow is accepted as a PR gate.

## AGENTS And Process Follow-Up Evaluation

No repository `AGENTS.md` change is needed for this ticket. The current rules
already cover Docker-first validation, Makefile usage, feedback files, secrets,
privacy, and leaving commits, pushes, and merges to the maintainer.

After the corrected workflow head receives a green GitHub Actions run, it is
reasonable to treat CI as a permanent Pull Request gate in the external process
source. Requiring that check before merge should remain a separate branch
protection or GitHub ruleset ticket, not part of EPIC2-005.
