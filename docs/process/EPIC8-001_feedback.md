# EPIC8-001 Closing Feedback Final

## Status

**Closing Feedback Final — implementation and real Oracle staging acceptance complete; ready for final PR checks and squash merge.**

The repository implementation, local validation, real OCI provisioning, native ARM64 deployment, HTTPS, editorial UAT, persistence, and the agreed zero-cost closure checks passed. Backup and restore execution were explicitly deferred to EPIC8-003 and are accepted as non-blocking for EPIC8-001.

## Summary

EPIC8-001 delivers a manual, reproducible, production-like demo/staging path for School Newsroom on Oracle Cloud while leaving the development Compose topology unchanged. The environment runs Django/Wagtail behind Caddy, with private PostgreSQL, persistent editorial media, secure production settings, explicit operator actions for migrations/access/site reconciliation, and no automatic deployment.

A material maintainer-approved amendment allowed conversion from Free Tier to **Individual Pay As You Go** solely to improve access to Always Free A1 capacity. Hard quotas, dual USD 1 budgets, four low-threshold alerts, resource-by-resource eligibility checks, and zero-cost acceptance remained mandatory. This amendment did not authorize paid resources or usage above Always Free limits.

The real staging environment is publicly reachable through browser-trusted HTTPS. The public site and Wagtail Admin work, nominal adult editorial roles passed UAT, content/media survived restarts, same-SHA redeploy, and VM reboot, and three agreed cost/inventory checkpoints completed at zero.

## Implemented repository files

- `docker-compose.staging.yml`: standalone `proxy`/`web`/`db` staging topology, private backend networks, persistent PostgreSQL volume, host-backed media, health checks, and bounded logging.
- `docker/staging/Caddyfile`: HTTP-to-HTTPS redirect, automatic TLS, reverse proxy, and read-only media route.
- `docker/staging/staging.env.example`: safe non-secret staging contract.
- `docker/staging/start-web.sh`: bounded database readiness, `collectstatic`, and Gunicorn startup without migration/bootstrap side effects.
- `Dockerfile`: non-root application runtime compatible with the staging topology.
- production settings and tests: fail-closed secret/database/host/origin/Admin URL requirements, secure proxy/cookie behavior, controlled logging, and staging noindex.
- `docs/operations/oracle_always_free_staging.md`: complete manual provisioning and operations runbook, including controlled PAYG guardrails and real closure state.
- `docs/operations/oracle_staging_uat.md`: final real-environment acceptance matrix and accepted EPIC8-003 backup deferral.
- `docs/process/EPIC8-001_feedback.md`: this final factual closure record.
- README/ignore files and focused tests required by the implementation.

## Repository-local validation

The implementation pass established:

- production settings focused tests: 34 passed;
- staging Compose parsing with safe dummy values;
- only Caddy publishing host ports 80/443;
- `proxy`, `web`, and `db` using `json-file` with `max-size=10m` and `max-file=3`;
- successful local x86_64 staging-image build;
- non-root web runtime as UID/GID `10001:10001`;
- successful static collection;
- disposable migrations;
- `bootstrap_mvp_access` idempotency;
- fictional media routing and disposable local storage checks;
- `make check`: Ruff passed, no migration drift, and 227 tests passed;
- `git diff --check`, secret review, and repository ownership review passed;
- runbook Bash blocks passed non-executing syntax validation during implementation.

Known deploy-check warnings remain intentional for this temporary hostname: existing Wagtail/Treebeard future-compatibility warnings plus HSTS subdomain/preload warnings because those options are deliberately disabled. HTTPS redirect, secure cookies, and a bounded HSTS duration are enabled.

## Real Oracle deployment validation

Private maintainer evidence confirmed:

- home region Chile Central/Santiago;
- account upgraded to Individual Pay As You Go under the approved zero-cost boundary;
- root quota policy active, including regional and AD A1 counters;
- A1 capped to 1 OCPU/4 GB, other Compute families blocked, combined storage capped to 100 GB, OCI volume backups blocked;
- project and tenancy-root USD 1 budgets with four Actual/Forecast alerts active;
- one `VM.Standard.A1.Flex` with 1 OCPU, 4 GB RAM, native `aarch64`;
- Ubuntu 24.04 LTS after replacing the initially provisioned Ubuntu 20.04 boot image;
- one approximately 50 GB boot volume and one 50 GB Balanced data block volume;
- ext4 data volume mounted by UUID at `/srv/school-newsroom`;
- Docker Engine, Compose, and Buildx running natively on ARM64;
- DuckDNS timer working without exposing the token;
- browser-trusted Caddy/Let's Encrypt HTTPS;
- HTTP redirect, public Home/news pages, secure Admin login, and current certificate;
- migrations, Wagtail Site reconciliation, technical superuser, and repeated access bootstrap;
- only Caddy publishing 80/443, with application/database private;
- bounded Docker logging for all three services.

## Editorial UAT and privacy

The adult Director/product owner and the separate nominal adult SEO user completed the canonical UAT with fictional/non-sensitive content:

- Director/editor draft and authorized direct publication: passed;
- `Revisión editorial` workflow start: passed;
- SEO task visibility and isolation: passed;
- request changes, revise, resubmit, and SEO approval: passed;
- SEO inability to approve the final editorial task or publish: passed;
- Director final `Aprobar y Publicar`: passed;
- public Home/list/detail/image/byline/metadata: passed;
- internal fictitious minor and contributor privacy boundaries: passed;
- bootstrap rerun after UAT without duplicated or broadened access: passed.

No account for a student, minor, teacher/monitor, or parent was created. No shared generic account was introduced.

## Persistence validation

Using the fictional UAT article and image:

- web restart: passed;
- proxy restart: passed;
- PostgreSQL restart and health recovery: passed;
- same-SHA `up -d --build` redeploy without volume deletion: passed;
- PostgreSQL named-volume persistence: passed;
- media persistence under `/srv/school-newsroom/media`: passed;
- VM reboot preserving UUID mount, Docker/Compose, database, media, DuckDNS, and HTTPS: passed.

## Cost and inventory acceptance

The maintainer completed the approved three-checkpoint closure schedule. Final result:

- project Cost to Date: zero;
- project forecast: zero or no positive forecast;
- tenancy Cost to Date: zero;
- tenancy forecast: zero or no positive forecast;
- paid SKU: none;
- budgets: active;
- four alerts: active;
- expected project inventory only;
- unexpected resource: none.

The original daily-first-seven-days closure condition was explicitly replaced by three checkpoints through the agreed final review. Weekly cost/inventory review while staging remains active is operational maintenance after closure, not a reason to keep this ticket open.

## Failures, causes, and resolutions

### GitGuardian continued to flag a corrected branch

Cause: the scanner evaluated secret-like content in earlier commits within the PR range.

Resolution: consolidate the branch into clean history and push with `--force-with-lease`; correcting only the latest working tree was insufficient. GitGuardian subsequently passed.

### A1 creation returned `Out of capacity`

Cause: external OCI host capacity in the tenancy's only Santiago Availability Domain, not repository or network configuration.

Resolution: controlled retries of the unchanged Always Free A1 target, followed by the approved Individual PAYG amendment with hard financial guardrails. No paid shape or larger resource was selected.

### Quota policy blocked the approved A1 request

Cause: the first policy restored only AD A1 counters; OCI also enforced regional core and memory counters.

Resolution: update the same root policy to permit both `standard-a1-*-count` and `standard-a1-*-regional-count` at exactly 1 OCPU/4 GB, while retaining the zeroed families and storage/backup guardrails.

### Initial image was Ubuntu 20.04

Cause: the actual launched image did not match the approved Ubuntu 24.04 target.

Resolution: preserve scarce A1 capacity by replacing the boot volume rather than terminating the instance.

### OCI image selector was empty and Console replacement returned `kmsKeyId` validation errors

Cause: OCI Console did not populate the compatible image list and sent an empty KMS field.

Resolution: use the official Ubuntu 24.04 ARM64 image OCID through OCI Cloud Shell/CLI, omitting customer-managed KMS. The replacement completed and the old boot volume terminated.

### SSH agent refused the approved key

Cause: the local desktop SSH agent interfered with the protected private key.

Resolution: connect with `IdentityAgent=none`, `IdentitiesOnly=yes`, and the explicit private-key path.

### Host key changed after boot replacement

Resolution: remove the obsolete known-host entry and accept the new verified host key.

### ext4 label was truncated

Cause: filesystem label length limit.

Resolution: no operational change was required because `/etc/fstab` mounts the volume by UUID.

### systemd warned after editing `fstab`

Resolution: run `systemctl daemon-reload`, mount, verify with `findmnt`, and complete a real reboot test.

### DuckDNS updater returned failure/`KO`

Cause: the first stored token/domain combination was invalid; the earlier token had also appeared in a screenshot and required rotation.

Resolution: rotate the token, recreate the root-only curl configuration, validate a manual `OK`, reset the oneshot service, and reactivate the timer.

### Cost estimator displayed list pricing

Cause: the estimator did not necessarily apply tier unit pricing in the displayed estimate.

Resolution: do not infer either cost or gratuity from the estimator alone; verify Always Free eligibility, quotas, add-ons, Cost Analysis, settled data, and inventory. Final observed cost remained zero.

## Approved closure amendments

- Individual Pay As You Go is allowed solely for Always Free A1 capacity access under the documented quotas/budgets/zero-cost boundary.
- EPIC8-001 closes after the three agreed cost/inventory checkpoints; the original seven-day closure gate no longer applies.
- Real backup creation and restore validation are not EPIC8-001 gates and remain EPIC8-003.
- Weekly cost/activity review continues as staging operation after ticket closure.

## Security, privacy, and scope review

- No real secret, password, token, private key, cloud identifier, database dump, or private minor data is committed.
- The real environment file and DuckDNS curl configuration remain root-only outside the checkout.
- Only Caddy publishes host ports; PostgreSQL and Gunicorn remain private.
- Media UAT used fictional/non-sensitive content.
- Nominal adult users are role-scoped and non-superuser.
- No paid shape, paid load balancer, managed database, Object Storage dependency, customer-managed Vault key, trial-only service, Kubernetes, Terraform, AWS/R2, automatic GitHub deployment, or permanent staging branch was introduced.
- This environment remains demo/staging, not production.

## New Work Discovered

Non-blocking future work remains separated:

- **EPIC8-002:** permanent `staging` branch, GitHub Actions/manual approval flow, deployment automation, rollback, and CI secret handling.
- **EPIC8-003:** database/media backups, retention, encrypted off-server custody, restore drill, and minimum observability.
- Optional future tickets: real-domain lifecycle, transactional email/password recovery, immutable dependency/image locking, and a formal staging retention/access policy.

## Final handoff and merge boundary

The implementation and operational acceptance are complete. Before merge, the maintainer must still apply this final documentation replacement, push it, confirm the repository's required PR validation and GitGuardian checks are green, resolve any final review conversation, and use **Squash and merge**. A failure in that final documentation delta must be incorporated here before merge; otherwise no application redeploy or repeated UAT is required because the closing delta is documentation-only.
