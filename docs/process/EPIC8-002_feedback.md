# EPIC8-002 — Stage A Technical Feedback

## Status

Implementation prepared through the approved contingency workflow without Codex.
The maintainer completed the focused ops tests, `make migration-check`,
`make check`, and `git diff --check` successfully before the final maintainer
review.

That review found one material failure-classification gap: an unexpected Fabric
transport exception could escape the adapter and be mislabeled globally as an
SSH connection failure even after a later deployment stage had started. The
final delta converts remote transport exceptions into safe command failures
inside the testable orchestration boundary, adds an explicit connection probe,
and adds focused coverage for connection failure and a transport exception during
build.

The real post-merge deploy and staging UAT remain pending and are not claimed as
completed in Stage A.

## Summary

EPIC8-002 adds a host-only `make staging-deploy` entry point that prepares a
separate local operations virtual environment and deploys an approved
`origin/main` commit to the existing Oracle staging host through Fabric and SSH.

The implementation keeps Fabric outside the Django runtime, centralizes the
deployment state machine in a testable Python module, uses doubles in tests, and
does not connect to staging during automated testing.

## Maintainer-approved interaction amendment

The approved ticket originally required zero prompts, including no Fabric
passphrase prompt. During preflight, the maintainer explicitly replaced that
constraint with a simpler operating policy suitable for infrequent deploys:

- `make staging-deploy` may prompt exactly once, locally and up front, for the
  encrypted SSH private-key passphrase;
- the passphrase remains stored in KeePass and is not persisted by the project;
- Fabric receives it through `--prompt-for-passphrase` for the lifetime of the
  process only;
- after that prompt, the deploy has no SSH login-password prompt, no `sudo`
  prompt, no confirmation, no editor, and no remote input;
- the dedicated key bypasses the interfering desktop agent through the local
  SSH alias and the Fabric connection explicitly sets `allow_agent=False` and
  `look_for_keys=False`.

The passphrase is deliberately not read from `.env`. An ignored `.env` is still
plaintext, would mix a local SSH secret with application configuration, and is
not required for an occasional operator-run deploy.

## Final structure

```text
requirements-ops.txt
fabfile.py
ops/__init__.py
ops/staging_deploy.py
tests/ops/test_staging_deploy.py
Makefile
.gitignore
docs/operations/oracle_always_free_staging.md
docs/operations/oracle_staging_uat.md
docs/process/EPIC8-002_feedback.md
```

The Oracle runbook now documents `make staging-deploy` as the normal
operator-triggered code-deployment path and preserves the long manual sequence
as recovery. The Oracle UAT document preserves the accepted EPIC8-001 evidence
and adds a separate EPIC8-002 post-merge matrix whose real-environment items
remain explicitly pending.

## Fabric and the local operations environment

- Fabric is pinned as `fabric==3.2.3` in `requirements-ops.txt`.
- Fabric 3.2.3 is distributed under the BSD License.
- Fabric is not added to `requirements.txt`, the web image, Compose, or staging.
- `.venv-ops/` is ignored by Git.
- `make staging-deploy` creates `.venv-ops` automatically when required.
- The requirements file SHA-256 is stored inside `.venv-ops` so installation is
  repeated only when the environment is missing, Fabric is missing, or the
  requirements content changed.
- Pip runs with `--no-input`.
- The target is rejected inside the Dev Container because it owns a host-side
  SSH and deployment workflow.

## SSH alias and authentication

The repository expects the stable local alias:

```text
school-newsroom-staging
```

The alias remains outside Git in `~/.ssh/config` and resolves hostname, user,
port, identity, host-key policy, and `IdentityAgent none`. Local preflight checks
that `ssh -G` resolves a hostname, user, and identity file.

Fabric loads the alias and receives the private-key passphrase through its
single startup prompt. Paramiko agent and automatic key discovery are disabled.
Host-key verification remains enabled through the normal Fabric/Paramiko known
hosts behavior.

## SHA default and override

Without `SHA`, local preflight performs:

```text
git fetch origin main
git rev-parse --verify origin/main^{commit}
```

With `make staging-deploy SHA=<sha>`, it resolves `<sha>^{commit}`.

Both paths require:

```text
git merge-base --is-ancestor <target> origin/main
```

The local worktree does not need to be clean because files from the local
worktree are never deployed.

## Preflights

### Local

- repository root;
- approved `origin` URL;
- resolved SSH alias;
- non-interactive `origin/main` fetch;
- full target commit;
- target ancestry in `origin/main`.

### Remote

Before deployment mutation:

- explicit SSH connection probe;
- `sudo -n true`;
- Git checkout at `/opt/school-newsroom`;
- approved remote origin;
- remote fetch dry run with `GIT_TERMINAL_PROMPT=0`;
- `/etc/school-newsroom/staging.env` existence without printing it;
- Docker and Compose availability;
- `docker-compose.staging.yml` existence;
- `/srv/school-newsroom/media` existence;
- quiet Compose configuration validation;
- tracked and untracked worktree cleanliness;
- no existing deploy lock;
- previous SHA;
- at least 5 GiB free on the checkout filesystem;
- safe extraction of `STAGING_HOSTNAME` only;
- current running service inventory.

## Lock

The deploy uses a non-blocking atomic remote lock directory:

```text
/var/lock/school-newsroom-staging-deploy.lock
```

The owner token is generated locally, written root-only, checked during release,
and never contains credentials. An existing lock fails with
`deployment_already_running`; the process does not wait indefinitely.

## Remote command sequence

Within the lock:

1. append a safe `started` history record;
2. `git fetch --prune origin` with terminal prompting disabled;
3. verify the target commit and its ancestry in remote `origin/main`;
4. `git checkout --detach <target>` and verify HEAD;
5. build `web` while existing containers continue running;
6. run `python manage.py migrate --noinput` through the newly built service;
7. run `python manage.py bootstrap_mvp_access`;
8. reconcile the default Wagtail Site from `STAGING_HOSTNAME` with port 443;
9. run `docker compose up -d`;
10. wait with a bounded timeout for healthy `db` and `web`, running `proxy`,
    and an executable Caddy process;
11. perform local HTTP redirect, HTTPS Home, `/noticias/`, `/admin/`, certificate,
    and hostname validation;
12. verify remote HEAD;
13. append success history and atomically update `current.json`.

Every Compose command uses:

```text
sudo -n docker compose
--env-file /etc/school-newsroom/staging.env
-f docker-compose.staging.yml
```

## Registration

The implementation writes safe JSON records under:

```text
/var/lib/school-newsroom/deployments/current.json
/var/lib/school-newsroom/deployments/history.jsonl
```

History records contain only SHAs, UTC time, result, stage when applicable, and
whether services may have changed. `current.json` is updated only after health,
HTTPS smoke, and remote HEAD verification succeed.

A target already equal to remote HEAD acquires and releases the lock, reports
`already_deployed`, and skips checkout, build, migrations, recreate, smoke, and
material deployment registration.

## Failure behavior

- local and remote preflight failures occur before deployment mutation;
- remote transport exceptions are converted into safe command failures inside
  the orchestration boundary, so the active stage keeps its own failure code;
- an SSH transport failure on the first remote probe is reported specifically as
  `ssh_connection_failed`;
- the final Fabric fallback is reserved for unexpected internal errors and does
  not claim that services were unchanged;
- checkout, build, migration, bootstrap, and Site failures restore the remote
  checkout to the previous SHA before service recreation;
- migration failure does not attempt database rollback and instructs the
  maintainer to inspect whether any operation applied;
- recreate, health, or smoke failures do not perform blind rollback after
  migrations;
- health failure prints only bounded Compose status and the last 100 lines for
  `proxy`, `web`, and `db`;
- failure history is best effort and cannot replace the primary failure code;
- lock release is attempted in `finally`, and the SSH connection is always
  closed;
- safe final output uses stable stage/code/next-action fields and does not print
  environment values or passphrases.

No implementation command uses `down -v`, `docker volume rm`, global prune,
`git clean`, stash, merge, rebase, destructive reset, OCI mutation, backup, or
product migration generation.

## Test architecture

`ops/staging_deploy.py` owns the orchestration and depends on small local,
remote, and smoke protocols.

`fabfile.py` is only the Fabric adapter. Tests import neither Fabric nor the
real SSH transport.

Focused tests use doubles and cover:

- default `origin/main` resolution;
- optional SHA commit resolution and ancestry;
- SHA outside main;
- missing SSH alias;
- failed SSH connection before remote mutation;
- failed `sudo -n`;
- dirty remote checkout;
- occupied lock;
- already-deployed no-op;
- successful ordered deployment;
- build, migration, bootstrap, Site, and recreate failures;
- transport exception during build preserving build-stage classification;
- health timeout and bounded logs;
- HTTPS smoke failure;
- current record only after success;
- secret-free output;
- Compose, env-file, detached checkout, bounded-log, and destructive-command
  contracts;
- Fabric separation and the single passphrase prompt entry point;
- connection closure and lock release.

## Validation

Before the final review delta, the maintainer reported these repository gates
passing in the real checkout:

```text
focused ops tests: PASS
make migration-check: PASS
make check: PASS
git diff --check: PASS
```

The final review delta changes only failure classification, two focused tests,
and documentation. Package-side validation for that delta is recorded separately
when the final package is generated; the maintainer must rerun the focused ops
tests, `make check`, and `git diff --check` after extraction.

`make browser-test` is not required because the delta does not modify a browser
workflow, fixture, public template, or public JavaScript.

## Deferred real deployment and UAT

The first real `make staging-deploy` remains maintainer-controlled and must occur
only after merge to `main`. It will provide the evidence for:

- one local passphrase prompt and no later interaction;
- target resolution from the new `origin/main`;
- real ARM64 build;
- migrations, bootstrap, Site reconciliation, recreate, health, and HTTPS smoke;
- deployment records;
- idempotent second invocation;
- the complete fictional news UAT;
- the deferred EPIC6-003 sharing and external-preview observations.

No real deploy or UAT is claimed in this draft.

## Documentation state

Stage A updates:

```text
docs/operations/oracle_always_free_staging.md
docs/operations/oracle_staging_uat.md
docs/process/EPIC8-002_feedback.md
```

The runbook now separates the normal `make staging-deploy` /
`make staging-deploy SHA=<sha>` path from manual recovery. The UAT file adds the
post-merge EPIC8-002 acceptance matrix without fabricating real results.

After Luis executes the first real deploy and UAT, Stage B must update the UAT
record and this feedback file with the observed pass/fail evidence before final
ticket closure.

## New Work Discovered

No separate product, schema, OCI, cost, backup, or migration work was introduced.
A stale-lock recovery policy may be considered only if a real interrupted deploy
shows that manual inspection is insufficient; it is not required for this ticket.

## Durable knowledge candidates

After real acceptance, F004 should record:

- local deploy by approved `origin/main` SHA;
- one permitted local private-key passphrase prompt for infrequent deploys;
- `IdentityAgent none` / Paramiko agent-disabled authentication;
- automatic `.venv-ops` bootstrap;
- remote deployment lock and records;
- normal automated path versus manual recovery path;
- continued separation of EPIC8-003 backup/restore work.

## Contingency workflow

This implementation was produced without Codex. The package contains only the
approved repository paths, excludes secrets and runtime data, and is intended to
be listed and SHA-256 verified before extraction from the repository root by the
maintainer.
