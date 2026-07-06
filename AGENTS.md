# Repository Instructions For Codex

These instructions apply to the whole repository.

## General rules

- All repository technical content must be written in English.
- The official application runtime is Docker-first.
- Codex local in VS Code is the primary implementation agent.
- The Dev Container is the Python editor, test, and debug environment.
- The Makefile is the stable validation interface; use `make check` for general repository validation.
- Inspect the real repository state before editing.
- Implement only the current ticket scope and avoid unrelated improvements.
- Keep `README.md` developer-facing.
- Create or update `docs/process/<TICKET-ID>_feedback.md` for every ticket.
- Do not invent manual validation results. Record manual validation only when it is actually known.
- Leave commits, pushes, and merges to the repository maintainer unless the current task explicitly authorizes them.
- Do not use destructive data, Docker volume, or Git-history commands without explicit approval.
- Do not commit secrets, credentials, private keys, tokens, or production values.
- Privacy risks involving minors are high priority.

## Development workflow

- Preserve the Docker-first runtime and the Dev Container workflow.
- Do not introduce Docker-in-Docker or require the Docker socket inside the Dev Container.
- Use the existing Makefile targets instead of duplicating command internals.
- Keep pre-commit hooks fast and suitable for staged files.
- Do not add CI, deploy infrastructure, or product features unless the current ticket explicitly requires them.

## Review guidelines

- Secrets, credentials, private keys, tokens, or production values are blocking findings.
- Accidental PII exposure or logging is blocking or high priority.
- Minors' privacy requires special attention.
- Model changes require appropriate migrations.
- Behavior changes require relevant tests.
- Authorization and permission regressions are blocking findings.
- Docker-first workflow regressions are high priority.
- Unrelated scope added to a ticket should be flagged.
- `README.md` should remain developer-facing and should not include ticket history or agent workflow noise.
- Feedback files must distinguish automated validation, manual validation, deferred validation, warnings, and known issues.
