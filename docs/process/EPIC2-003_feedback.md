# EPIC2-003 Closing Report

## Ticket

Standardize the local development process, hooks, and Pull Request template for School Newsroom.

Operational project name: Noticias.
Technical project name: School Newsroom.
Repository name: `school-newsroom`.

## Final Summary

EPIC2-003 added the repository-level Codex instructions, pre-push validation through the existing `pre-commit` framework, a concise GitHub Pull Request template, and permanent README documentation for installing and running local hooks.

The normal pre-commit stage remains fast and staged-file oriented. It runs whitespace, YAML, TOML, Ruff check, and Ruff format hooks. The pre-push stage runs `make check`, preserving the Docker-first and Dev Container workflow established by EPIC2-001 and EPIC2-002.

No product features, GitHub Actions, CI, deploy infrastructure, Docker-in-Docker, Docker socket mounts, or destructive data/volume/Git-history commands were added or run. Codex did not commit, push, or merge. The repository maintainer later performed the real commit and push workflow as manual UAT.

## Post-Review Adjustments

- Added a persistent AGENTS.md rule that commits, pushes, and merges are left to the repository maintainer unless the current task explicitly authorizes them.
- Aligned the README host installation command with the supported project range: `pipx install "pre-commit>=4.2,<5.0"`.
- Normalized machine-specific absolute home paths in this feedback file to `~/...` where the username is not relevant.
- Clarified that hook-generated empty-file and Ruff formatting changes are retained only as one-time behavior-neutral baseline normalization for the newly enforced `pre-commit run --all-files` gate.
- Generalized process learnings so they do not promote one-off implementation details as universal rules.
- Validated the hook configuration and stages with supported `pre-commit 4.6.0` from the project Docker environment.

## Maintainer UAT And Real Git Hook Validation

After the implementation and post-review adjustments, Luis performed the real repository Git workflow from the Ubuntu host.

Initial real Git workflow:

- `git commit -m "chore: standardize local development workflow"`
  - Created initial commit `bb4b70e`.
  - The command completed immediately and showed no pre-commit hook output.
- `git push -u origin EPIC2-003-standardize-local-workflow`
  - The initial push completed successfully.
  - The command showed no pre-push or `make check` output.

The absence of hook output exposed a real process gap: the hook configuration had been validated manually, but the Git hook scripts had not yet been installed in the maintainer's clone.

Host tooling and hook installation:

- Host `pipx` version: `1.4.3`.
- `pipx ensurepath --prepend` was attempted but the installed pipx version does not support the `--prepend` option.
- `pipx install "pre-commit>=4.2,<5.0"` installed `pre-commit 4.6.0`.
- `type -a pre-commit` confirmed `~/.local/bin/pre-commit` is resolved before the system installation.
- `pre-commit --version` returned `pre-commit 4.6.0`.
- `pre-commit install` installed:
  - `.git/hooks/pre-commit`
  - `.git/hooks/pre-push`
- The generated hook scripts reference the pipx-managed pre-commit Python environment.

The repository configuration was updated with:

- `minimum_pre_commit_version: "4.2.0"`
- `default_install_hook_types: [pre-commit, pre-push]`

This makes the supported minimum version explicit and allows one `pre-commit install` command to install both required Git hook types.

Real host validation after installation:

- `pre-commit validate-config`
  - Passed.
- `pre-commit run --all-files`
  - Passed.
  - `end-of-file-fixer`, `trailing-whitespace`, `check-yaml`, `check-toml`, `ruff-check`, and `ruff-format` all passed.
- `pre-commit run --hook-stage pre-push --all-files`
  - Passed.
  - The `make check` hook ran successfully.
- `git diff --check`
  - Passed.
- `git status --short`
  - Only the expected `.pre-commit-config.yaml` and `README.md` follow-up changes remained before the feedback update.

The real maintainer UAT demonstrated that manually running hook stages is not sufficient evidence that Git will invoke them automatically. A ticket introducing Git hooks must also account for hook-script installation in the working clone.

## Commands Successfully Run

- `git branch --show-current`
  - Result: `EPIC2-003-standardize-local-workflow`.
- `git status --short`
  - Initial result before edits: clean worktree.
- `sed -n ... ~/Downloads/EPIC2-003_estandarizar_proceso_hooks_pr_template.md`
  - Read the full EPIC2-003 ticket from the provided attachment.
- `rg --files`
  - Inspected repository file layout.
- `git ls-files AGENTS.md README.md Makefile docker-compose.yml .env.example docker/web/Dockerfile pytest.ini pyproject.toml .pre-commit-config.yaml .vscode/settings.json .devcontainer/devcontainer.json docs/process/EPIC2-001_feedback.md docs/process/EPIC2-002_feedback.md docs/process/devcontainer.md`
  - Confirmed tracked required files and that `AGENTS.md` did not yet exist.
- `sed -n ... README.md Makefile docker-compose.yml .env.example docker/web/Dockerfile pytest.ini pyproject.toml .pre-commit-config.yaml .vscode/settings.json .devcontainer/devcontainer.json docs/process/EPIC2-001_feedback.md docs/process/EPIC2-002_feedback.md docs/process/devcontainer.md requirements.txt`
  - Inspected the required repository context before editing.
- `find . -name AGENTS.md -print`
  - Confirmed only the new top-level `./AGENTS.md` exists after implementation.
- `pre-commit validate-config`
  - Passed after rerunning with approved access to the normal host pre-commit cache.
- `pre-commit run --all-files`
  - Final result: passed.
  - Hooks: `end-of-file-fixer`, `trailing-whitespace`, `check-yaml`, `check-toml`, `ruff-check`, `ruff-format`.
- `pre-commit run --hook-stage pre-push --all-files --verbose`
  - Passed after restoration of the temporary negative-validation regression.
  - Evidence showed the `make-check` hook invoking `make check`, which ran Ruff and pytest through Docker Compose.
- `pre-commit run --hook-stage pre-push --all-files`
  - Final exact required command result: passed.
- `make test`
  - Passed: 7 tests passed, 1 known warning.
- `make lint`
  - Passed: `All checks passed!`.
- `make check`
  - Passed: Ruff passed; pytest reported 7 passed, 1 known warning.
- `pre-commit run check-yaml --files docs/process/_hook_validation_bad.yaml`
  - Expected failure confirmed for the temporary invalid YAML file.
- `test -f AGENTS.md`
  - Passed.
- `test -f .github/pull_request_template.md`
  - Passed.
- `test -f docs/process/EPIC2-003_feedback.md`
  - Passed.
- `find docs/process -name '_hook_validation_bad.yaml' -print`
  - Returned no files after cleanup.
- `find .github -maxdepth 3 -type f -print`
  - Returned only `.github/pull_request_template.md`.
- `rg -n "Planka|ChatGPT|5433|ljarufe|/home|Luis" AGENTS.md README.md .github/pull_request_template.md .pre-commit-config.yaml`
  - Returned no matches.
- `rg -n "Review guidelines|Docker-first|Makefile|Dev Container|docs/process/<TICKET-ID>_feedback.md|manual validation|secrets|minors" AGENTS.md`
  - Confirmed required AGENTS.md concepts are present.
- `rg -n "## Summary|## Ticket and closing feedback|## What changed|## How to test|### Automated|### Manual|## Validation completed|## Known warnings or deferred validation|## Review focus" .github/pull_request_template.md`
  - Confirmed the required PR template sections are present.
- `docker compose run --rm web pre-commit --version`
  - Result: `pre-commit 4.6.0`.
- `docker compose run --rm web sh -c 'command -v git || true; pre-commit --version'`
  - Confirmed the Docker project environment has `/usr/bin/git` and `pre-commit 4.6.0`.
- `docker compose run --rm web sh -c 'pwd; git --version; git status --short'`
  - Confirmed the first Docker `pre-commit run --all-files` failure was Git safe-directory handling for `/app`.
- `docker compose run --rm web sh -c 'git config --global --add safe.directory /app && pre-commit --version'`
  - Result: `pre-commit 4.6.0`.
- `docker compose run --rm web sh -c 'git config --global --add safe.directory /app && pre-commit validate-config'`
  - Supported-version config validation passed.
- `docker compose run --rm web sh -c 'git config --global --add safe.directory /app && pre-commit run --all-files'`
  - Supported-version all-files validation passed.
- `docker compose run --rm web sh -c 'git config --global --add safe.directory /app && pre-commit run --hook-stage pre-push --all-files'`
  - Supported-version pre-push validation passed.
- `git diff --check`
  - Final result: passed with no whitespace errors.
- `git status --short`
  - Final result: only expected EPIC2-003 created/modified files remained; no temporary validation files or temporary regressions remained.

## Commands Not Run By Codex And Why

- `pre-commit install`
  - Not run to avoid changing local `.git/hooks` in the maintainer's working copy. The command is documented in `README.md`.
- `pre-commit install --hook-type pre-push`
  - Not run to avoid changing local `.git/hooks` in the maintainer's working copy. The command is documented in `README.md`.
- `pipx run --spec "pre-commit>=4.2,<5.0" pre-commit ...`
  - Not run because `pipx` is not installed on the host. The supported-version validation was run with `pre-commit 4.6.0` from the project Docker environment instead.
- A real `git commit`
  - Not run because the ticket explicitly prohibits test commits and automatic commits.
- `git push`, `git merge`
  - Not run because the ticket explicitly prohibits push and merge actions.
- `docker compose down -v`
  - Not run because volume deletion is destructive and prohibited.
- `rm -rf`
  - Not run because destructive removal is prohibited.
- New VS Code/Codex session validation of AGENTS.md loading
  - Not run because it requires Luis to start a separate local Codex run in VS Code.
- Real PR creation and GitHub template preload validation
  - Not run because the ticket prohibits pushing/opening the PR from Codex.

## Problems Encountered

- Host `pre-commit` first failed because the sandbox blocked writes to `~/.cache/pre-commit`.
- `pre-commit run --all-files` modified existing files through `end-of-file-fixer` and `ruff-format`.
- Ruff failed in the first full pre-commit pass because the repository-local `.ruff_cache` directory is owned by `nobody:nogroup` from container execution.
- The first positive pre-push validation showed two normal file hooks running during the `pre-push` stage in addition to `make check`.
- The first temporary pre-push failure regression used `assert False`, which Ruff blocks with `B011` before pytest runs.
- Host `pipx` was not installed, so the supported-version validation could not use `pipx run --spec "pre-commit>=4.2,<5.0" ...`.
- The first supported-version Docker `pre-commit run --all-files` attempt failed because Git treated the bind-mounted `/app` repository as a dubious-ownership directory.

## Failed Attempts And Retries

- `pre-commit validate-config`
  - First attempt failed with `OSError: [Errno 30] Read-only file system: '~/.cache/pre-commit'`.
  - Retried with approved host-cache access and passed.
- `pre-commit run --all-files`
  - First attempt without approved host-cache access failed with `OSError: [Errno 30] Read-only file system: '~/.cache/pre-commit/.lock'`.
  - Retried with approved host-cache access.
  - That retry failed after modifying files because Ruff could not write to `.ruff_cache`.
  - Updated Ruff hook args to use `/tmp/school-newsroom-ruff-cache`.
  - Reran `pre-commit run --all-files`; it passed.
- `pre-commit run --hook-stage pre-push --all-files --verbose`
  - First positive run passed but showed `end-of-file-fixer` and `trailing-whitespace` running in the pre-push stage.
  - Added explicit `stages: [pre-commit]` to the normal hooks.
  - Reran config validation and both hook stages; behavior matched the ticket scope.
- Temporary pre-push failure validation
  - First temporary regression used `assert False`; the actual pre-push hook reached `make check` but failed during Ruff lint with `B011`.
  - Retried with `raise AssertionError("temporary pre-push validation regression")`; Ruff passed and pytest failed through the actual pre-push hook.
  - Removed the temporary regression and reran the pre-push stage successfully.
- Supported-version validation
  - `docker compose run --rm web pre-commit run --all-files` failed with `FatalError: git failed. Is it installed, and are you in a Git repository directory?`.
  - `docker compose run --rm web sh -c 'pwd; git --version; git status --short'` showed the root cause: Git safe-directory protection for the bind-mounted `/app` repository.
  - Retried supported-version validation with `git config --global --add safe.directory /app` inside the disposable Docker Compose run container.
  - `pre-commit validate-config`, `pre-commit run --all-files`, and `pre-commit run --hook-stage pre-push --all-files` then passed with `pre-commit 4.6.0`.

## Root Causes

- The execution sandbox did not allow host `pre-commit` to create or lock its default cache under the home directory without approval.
- Docker-created cache directories in the bind-mounted repository can be owned by the container user, making host-level Ruff cache writes fail.
- `default_stages: [pre-commit]` alone was not enough with the installed hook metadata to keep every normal hook out of the pre-push run.
- `assert False` is intentionally rejected by the configured Ruff rule set, so it is not a lint-clean way to force a pytest failure.
- The official project Docker environment has supported `pre-commit 4.6.0`, but Git requires a safe-directory exception for `/app` when the repository is bind-mounted with host ownership and commands run as `root` in a disposable container.

## Solutions Applied

- Created top-level `AGENTS.md` with persistent repository instructions and `## Review guidelines`.
- Added the persistent AGENTS.md Git side-effect rule: commits, pushes, and merges are left to the repository maintainer unless the current task explicitly authorizes them.
- Updated `.pre-commit-config.yaml` with `default_stages: [pre-commit]` and explicit `stages: [pre-commit]` on normal hooks so existing fast hooks stay in the normal commit stage.
- Updated Ruff pre-commit hook args to use `/tmp/school-newsroom-ruff-cache`, matching the Makefile cache strategy.
- Added a local `make-check` pre-push hook that runs `make check` through `pre-commit`.
- Created `.github/pull_request_template.md` with the required sections and reviewer-reproducible testing prompts.
- Updated `README.md` with permanent hook installation and usage documentation, including the supported host install range `pipx install "pre-commit>=4.2,<5.0"`.
- Created this ticket feedback file.
- Retained the hook-generated empty-file and Ruff formatting changes as one-time baseline normalization required for the newly enforced `pre-commit run --all-files` gate, after exact diff inspection confirmed that the changes are behavior-neutral.
- Adjusted the temporary negative pre-push validation after Ruff correctly rejected `assert False`, so the retry reached the intended pytest failure stage through the actual pre-push gate.
- Used the project Docker environment for supported-version validation because host `pipx` is unavailable and the host `pre-commit` binary is outside the supported range.
- Added a disposable container-local Git safe-directory setting before running supported-version pre-commit commands against `/app`.

## Files And Directories Created Or Modified

- Created `AGENTS.md`.
- Modified `.pre-commit-config.yaml`.
- Created `.github/`.
- Created `.github/pull_request_template.md`.
- Modified `README.md`.
- Created `docs/process/EPIC2-003_feedback.md`.
- Modified existing empty marker/module files through `end-of-file-fixer` as one-time behavior-neutral baseline normalization for `pre-commit run --all-files`:
  - `apps/__init__.py`
  - `apps/home/__init__.py`
  - `apps/home/migrations/__init__.py`
  - `config/__init__.py`
  - `config/settings/__init__.py`
  - `docs/adr/.gitkeep`
  - `docs/ops/.gitkeep`
  - `docs/product/.gitkeep`
  - `static/.gitkeep`
- Modified existing Python formatting through `ruff-format` as one-time behavior-neutral baseline normalization for `pre-commit run --all-files`:
  - `config/settings/base.py`
  - `config/settings/production.py`

## Deviations From The Ticket

- No scope deviations were made.
- The temporary invalid YAML file was removed with `apply_patch` instead of `rm`; this was an equally safe cleanup technique and left no final diff.
- The local hook installation commands were documented but not run, to avoid changing local `.git/hooks` outside the repository content.
- The first temporary pre-push failure used `assert False`, but Ruff blocked it before pytest. The retry used a lint-clean `AssertionError` so pytest failure was demonstrated through the actual pre-push hook.

## Hook Validation Results

- Normal pre-commit positive validation:
  - `pre-commit run --all-files` passed.
  - Confirmed commit-stage hooks: `end-of-file-fixer`, `trailing-whitespace`, `check-yaml`, `check-toml`, `ruff-check`, `ruff-format`.
- Invalid YAML negative validation:
  - Created temporary `docs/process/_hook_validation_bad.yaml` with invalid YAML.
  - Ran `pre-commit run check-yaml --files docs/process/_hook_validation_bad.yaml`.
  - Hook failed with exit code 1 and a YAML parse error, as expected.
  - Removed the temporary file.
  - Confirmed it does not remain in `git status --short` or `find docs/process -name '_hook_validation_bad.yaml' -print`.
- Pre-push positive validation:
  - `pre-commit run --hook-stage pre-push --all-files --verbose` passed.
  - Output showed `make-check` running `make check`.
  - `make check` ran Ruff through Docker Compose and pytest through Docker Compose.
  - Pytest result: 7 passed, 1 known warning.
  - Exact required command `pre-commit run --hook-stage pre-push --all-files` also passed.
- Pre-push negative validation:
  - Added a temporary failing regression to `apps/home/tests.py`.
  - First attempt with `assert False` failed through the pre-push hook during `make check` linting with Ruff `B011`.
  - Retried with `raise AssertionError("temporary pre-push validation regression")`.
  - The actual pre-push hook reached `make check`, Ruff passed, and pytest failed with 1 failed, 6 passed, 1 warning.
  - Removed the temporary regression.
  - Confirmed `apps/home/tests.py` has no remaining diff.
  - Reran pre-push validation successfully after restoration.
- Supported-version validation:
  - Exact version used: `pre-commit 4.6.0`.
  - Invocation environment: Docker Compose `web` service, with a disposable container-local `git config --global --add safe.directory /app` setting.
  - `pre-commit validate-config` passed.
  - `pre-commit run --all-files` passed.
  - `pre-commit run --hook-stage pre-push --all-files` passed.
  - No destructive or temporary negative-path experiments were repeated during this post-review validation.

## AGENTS.md Validation Status

- `AGENTS.md` exists at the repository root.
- No nested `AGENTS.md` files exist.
- The file is in English.
- It contains persistent repository instructions only.
- It includes the exact `## Review guidelines` section.
- It records Docker-first, Dev Container, Codex local, Makefile validation, ticket scope, feedback, manual-validation truthfulness, non-destructive command, secret, and minors' privacy rules.
- Scans of `AGENTS.md`, `README.md`, `.github/pull_request_template.md`, and `.pre-commit-config.yaml` found no Planka, ChatGPT, personal path, local port `5433`, or Luis-specific content.
- Functional validation that a brand-new Codex run reads `AGENTS.md` is deferred to Luis because it requires a separate VS Code/Codex session.

## PR Template Validation Status

- `.github/pull_request_template.md` exists.
- It is in English.
- It contains all required sections:
  - `## Summary`
  - `## Ticket and closing feedback`
  - `## What changed`
  - `## How to test`
  - `### Automated`
  - `### Manual`
  - `## Validation completed`
  - `## Known warnings or deferred validation`
  - `## Review focus`
- `How to test` asks for exact reviewer-reproducible commands, URLs, actions, roles, and expected results where applicable.
- The template avoids generic validation claims such as `Works locally` and `Test normally`.
- The template does not include Planka local details, ChatGPT workflow, secrets, or ticket history.
- The EPIC2-003 Pull Request did not preload the template because this PR introduces the template before it exists on the default branch. GitHub documents that templates become available to collaborators after they are merged into the repository's default branch. Automatic preload validation is therefore deferred to the next Pull Request after EPIC2-003 is merged.

## Remaining Warnings

- Pytest still reports the known non-blocking warning:

```text
No directory at: /app/staticfiles/
```

- Host `pre-commit --version` reported `pre-commit 3.6.2`, while the project dependency range in `requirements.txt` is `pre-commit>=4.2,<5.0`. Post-review validation passed with supported `pre-commit 4.6.0` from the project Docker environment. The README now recommends `pipx install "pre-commit>=4.2,<5.0"` for host hook tooling.
- Existing repository cache directories `.ruff_cache` and `.pytest_cache` are owned by `nobody:nogroup` from container execution. This ticket avoided relying on repo-local Ruff cache writes by routing Ruff hook cache to an isolated writable cache path.

## Manual Validation Completed By Luis

- Confirmed the active ticket branch and clean worktree before the initial commit.
- Performed the initial real commit and push and observed that neither Git hook executed automatically.
- Installed supported host `pre-commit 4.6.0` through pipx.
- Confirmed the pipx-managed `pre-commit` executable is resolved before the older system installation.
- Ran `pre-commit install` and confirmed both `.git/hooks/pre-commit` and `.git/hooks/pre-push` were installed.
- Inspected the generated Git hook scripts and confirmed they use the pipx-managed pre-commit environment.
- Ran `pre-commit validate-config` successfully on the host.
- Ran the normal pre-commit stage successfully on all files.
- Ran the pre-push stage successfully and confirmed `make check` passed.
- Confirmed `git diff --check` passes.
- Confirmed no temporary validation files or regressions remain in the worktree.
- Opened the real EPIC2-003 Pull Request and observed that the new PR template was not automatically preloaded.

## Manual Validation Still Required

- Fresh-session Codex loading of `AGENTS.md` remains deferred because Codex quota is temporarily unavailable. The file itself and its persistent rules were reviewed during the EPIC2-003 follow-up review.
- Automatic GitHub Pull Request template preload must be validated on the next Pull Request after EPIC2-003 is merged into the default branch.
- GitHub `@codex review` is unavailable during ticket closure because the Codex quota is temporarily exhausted. The full EPIC2-003 patch is reviewed in the follow-up project chat instead.

## Recommendations For The Next Ticket

- Keep using `make check` as the general validation command and pre-push gate.
- Keep pre-commit hooks limited to fast, staged-file-oriented checks.
- Avoid adding product-feature work to developer-experience tickets.
- Use isolated writable cache locations for host/container validation when repository-local cache ownership is incompatible between execution users.
- For future hook negative validation, ensure the failure reaches the component or stage the validation is intended to exercise; an earlier unrelated failure is not sufficient evidence.

## Project Process Source Update

The external project process source should be updated.

Reusable changes to add:

- Repository tickets that add or alter hooks should validate both positive and negative paths through the actual hook stage, not only by running equivalent commands directly.
- Negative-path validation must reach the component or stage it is intended to exercise; an earlier unrelated failure is not sufficient evidence.
- If a hook modifies files during validation, inspect the diff, record the modification, and rerun the affected validation after accepting or correcting the change.
- Keep normal pre-commit hooks explicitly scoped to `pre-commit` and expensive repository validation explicitly scoped to `pre-push`.
- Host/container validation should use an isolated writable cache when repository-local cache ownership is incompatible between execution users.
- Actual automated gate entry points must be validated when a ticket adds or changes them.
- Do not require real hook installation, commits, pushes, or PR creation from Codex unless a ticket explicitly authorizes those side effects.

- Git-hook tickets must verify that the documented installation command actually installs every required hook type in a real maintainer clone.
- When practical and authorized, the first real maintainer commit and push after hook installation should be treated as UAT of automatic hook invocation; manual `pre-commit run` commands validate hook behavior but do not prove Git hook scripts are installed.
- Validation of a newly introduced GitHub Pull Request template belongs to a subsequent Pull Request after the template is available on the default branch.

What should not change yet:

- Do not add GitHub Actions or CI as a default requirement.
- Do not make Draft PRs mandatory.
- Do not move product-feature validation into this developer-experience process ticket pattern.

## Standard Ticket Template Improvements

- For tickets that introduce Git hook types, require the ticket to define a reproducible installation command and record whether a real clone has the corresponding `.git/hooks` scripts installed.
- Add an explicit prompt to report `git branch --show-current` and initial `git status --short` in the feedback file.
- For tickets that change gate wiring or need proof of downstream command invocation, request one verbose positive run such as `pre-commit run --hook-stage pre-push --all-files --verbose` so the feedback can include evidence of the downstream command.
- For negative-path validation, require evidence that the failure reached the intended component or stage.
- Add a reminder that tool-generated changes must be inspected, classified against ticket scope, documented, and rerun before final validation when retained.
