# Repository Instructions For Codex

These instructions apply to the whole repository.

## General rules

- All repository technical content must be written in English.
- The official application runtime is Docker-first.
- Codex local in VS Code is the primary implementation agent.
- The Dev Container is the Python editor, test, and debug environment.
- The Makefile is the stable validation interface; use `make check` for general repository validation.
- Repository-writing commands executed through Docker must not leave root/container-owned generated files in the bind-mounted checkout.
- When introducing a new generator or tooling path, inspect ownership of generated repository files.
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
- Keep repository technical content and internal identifiers in English, but keep all public application copy and the Wagtail editor/admin experience in Spanish.
- Custom model/admin labels, help text, panel headings, and editor-visible product terminology must be Spanish.
- When a change adds or modifies an editor-visible Wagtail Admin workflow, navigation path, field, or editorial behavior, update `docs/editorial/guia_de_uso.md` in the same change. Keep the guide in Spanish and document only behavior that actually exists.
- Use delta-based validation: run focused checks while editing and reserve `make check` for technical close or when a later delta can invalidate the previous general validation. Do not repeat unchanged validation by routine.
- Classify failures before retrying. Recurrent failures or workflow friction require root-cause investigation and a durable fix instead of repeated retries or permanent troubleshooting workarounds.
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
