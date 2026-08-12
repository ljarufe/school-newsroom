# EPIC2-006 Feedback — Closing Feedback Final

## Scope and structural inventory

| Boundary | Disposition | Rationale |
| --- | --- | --- |
| `apps.home`, `apps.news` | Keep | The existing Django app boundaries remain coherent; persisted models, labels, tables, ContentTypes, and migration ownership stay in `apps.news`. |
| `apps/news/models.py` | Keep | It owns persisted editorial models and their framework configuration. Splitting it would not improve ownership enough to justify model-discovery risk. |
| `apps/news/smart_paste.py` | Split façade | `apps.news.smart_paste` remains the public API. Result contracts now live in `smart_paste_contracts.py` and are re-exported unchanged. |
| `apps/news/views.py` | Split façade | Public `robots_txt` and `news_list` remain in `views.py`; the Admin-only smart-paste HTTP endpoint lives in `smart_paste_views.py` and is re-exported. |
| `apps/news/wagtail_hooks.py` | Split discovery entry point | Wagtail registration remains in `wagtail_hooks.py`; deletion protection, Admin URL construction, and workflow redirect behavior live in `wagtail_hook_handlers.py`. Taxonomy Admin viewsets remain together. |
| `scripts/validation_delta.py`, `tests/test_validation_delta.py` | Keep | QA-001's one productive classification policy, fail-closed behavior, and Git-boundary doubles are unchanged. |
| `docs/ops/`, `docs/adr/` | Delete | Both were empty `.gitkeep` boundaries with no consumer or documented policy. |
| `docs/process/devcontainer.md` | Move | Durable developer documentation belongs in `docs/development/devcontainer.md`; ticket feedback remains in `docs/process/`. |
| Residual `.gitkeep` files | Delete | The affected `docs/product/` and `static/` directories already contain tracked files. |
| Compose, Dev Container, VS Code, Node | Keep | Their tool-owned entry points and browser-only Node boundary remain intact. |

## Reproducibility

- Added human-maintained direct dependency inputs: `requirements.in` and
  `requirements-ops.in`.
- Generated fully transitive, hash-checked `requirements.txt` and
  `requirements-ops.txt` using fixed `pip-tools==7.6.0` and compatible
  `pip==25.3` in the pinned Python image.
- Added host-only `make lock`. It uses the existing lock as constraints during
  ordinary regeneration and is intentionally not part of `make check`.
- A first successful generation was followed by a second `make lock`; bytewise
  `cmp` reported no delta for either lock.
- The web image installs the application lock with `pip install --require-hashes`.
  The host-operations Makefile path uses the operations lock with the same mode.
- A clean web build passed the existing spaCy model and Pyphen smoke. A runtime
  `pip check` passed, and spaCy, Pyphen, and Wagtail imported successfully.
- A clean operations install from the hash-checked lock passed `pip check` and
  reported Fabric `3.2.3`.

## Immutable external artifacts

| Artifact | Locked reference |
| --- | --- |
| Python web base | `python:3.12.11-slim-bookworm@sha256:519591d6871b7bc437060736b9f7456b8731f1499a57e22e6c285135ae657bf7` |
| PostgreSQL | `postgres:16.14@sha256:95206741a5b214807675e14165369d05b93a9cf692223b616d07cca227e74b0b` |
| Playwright | `mcr.microsoft.com/playwright:v1.61.1-noble@sha256:5b8f294aff9041b7191c34a4bab3ac270157a28774d4b0660e9743297b697e48` |
| Caddy | `caddy:2.11.4-alpine@sha256:5f5c8640aae01df9654968d946d8f1a56c497f1dd5c5cda4cf95ab7c14d58648` |
| GitHub checkout action | `actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1` (`v7`) |

The action SHA was resolved from the official `actions/checkout` `v7` tag.
Registry inspection confirmed the Playwright index exposes `linux/amd64` and
`linux/arm64`; the other selected runtime indexes were inspected before pinning.

## Validation evidence

- Focused suite: `apps/news/tests/test_smart_paste.py`,
  `apps/news/tests/test_admin_uat.py`, `apps/news/tests/test_models.py`,
  `apps/news/tests/test_migrations.py`, `tests/test_validation_delta.py`, and
  `tests/ops/test_staging_deploy.py` — 144 tests, exit code 0.
- `make browser-test` — executed against the isolated Compose stack; its six
  Chromium specs completed and the stack cleaned up.
- `make check` — passed: Ruff clean, `makemigrations --check --skip-checks`
  reported no changes, and the 435-test coverage run exited 0 with the existing
  90% threshold.
- `git diff --check` — passed.

## Maintainer UAT and ARM64 evidence

Maintainer UAT completed successfully.

- Lock regeneration from the host reproduced both generated lock files with no
  delta.
- The VS Code Dev Container reported Python 3.12.11 at
  `/usr/local/bin/python`; pytest discovery and Test Explorer worked after the
  configured interpreter was selected and VS Code was reloaded. No repository
  change was required for that local editor-state issue.
- Public smart-paste, view, model, and Wagtail discovery imports remained
  available through their documented façades.
- Clean-checkout onboarding verification passed, including the moved
  `docs/development/devcontainer.md` path and removal of the obsolete
  `docs/process/devcontainer.md` reference.
- Native ARM64 evidence was completed on the existing Oracle A1 ARM64 host
  without deploying staging or modifying running services, volumes, media, or
  database state. The locked web image built successfully for `linux/arm64`
  and reported Python 3.12.11 at runtime.

## Failures, warnings, and New Work Discovered

- Initial lock generation failed because fixed `pip-tools==7.6.0` is not
  compatible with the resolver's pip 26.2.1 internal API. The durable fix pins
  the ephemeral compiler environment to `pip==25.3`; no generated lock was
  accepted before that fix.
- The first compiler output warned that `setuptools` was unsafe and unpinned.
  The generator now uses `--allow-unsafe`, producing a hashed exact
  `setuptools` entry; clean hash-checked installation passed.
- New Work Discovered: local Buildx/QEMU support for ARM64 is absent. This is an
  local environment capability gap rather than a repository defect. Required
  ARM64 evidence was completed on the existing Oracle ARM64 host, so it does
  not block EPIC2-006.
- No staging deployment or migration creation was performed.

## Operational closure

The maintainer reported the following late lifecycle evidence after the
implementation delta was committed:

- real commit and push completed successfully with the repository hooks;
- the Pull Request was opened against `main`;
- required CI completed green for the current PR delta;
- automatic GitHub/Codex review completed with no findings;
- no implementation delta was introduced after the validated/UAT-approved
  state.

No additional validation, UAT, or diff review is required before merge because
there is no later code/configuration delta capable of invalidating the existing
evidence.

The remaining lifecycle actions are operational only:

1. Squash and merge the Pull Request.
2. Synchronize local `main`.
3. Remove the ticket branch and prune remote references.
4. Move the Planka Card from `Review` to `Done`.
5. Hand this Closing Feedback Final to the planning/consolidation chat.

`Released` does not apply because EPIC2-006 did not perform a real product
deployment.
