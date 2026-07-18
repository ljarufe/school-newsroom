# EPIC8-001 Implementation Closing Draft

## Status

Implementation Closing Draft. Repository implementation and local technical validation are complete. The approved Individual Pay As You Go account upgrade, Oracle provisioning, native VM validation, DNS, public HTTPS, real persistence/backup evidence, and browser/editorial UAT remain maintainer work and are not claimed as passed.

## Summary

EPIC8-001 adds a standalone production-like staging path for a manual Oracle Always Free deployment while leaving the development Compose topology unchanged. A maintainer-approved material scope amendment now permits upgrading the account from Free Tier to **Individual Pay As You Go** solely to improve A1 capacity access while continuing to consume only Always Free resources at an expected zero cost. It does not authorize paid resources or usage above Always Free limits.

The staging topology uses Caddy as the only host-published service, Gunicorn for Django/Wagtail, PostgreSQL on an internal Compose network, a stable database volume, and a persistent host media directory shared read-write with the application and read-only with Caddy. Docker JSON logs for all three services use bounded rotation. The web startup waits for PostgreSQL, runs `collectstatic`, and then starts Gunicorn. It deliberately does not run migrations, bootstrap access, or create users during an ordinary restart.

Production settings now fail closed for the secret key, database URL, explicit hosts, HTTPS CSRF origins, HTTPS Wagtail Admin base URL, and controlled console log level. Staging remains `DEBUG=False`, uses secure cookies and HTTPS redirect behavior, and keeps conservative noindex behavior. The image has a fixed non-root application identity and retains the existing development bind-mount ownership behavior through the entrypoint.

The operator runbook documents current Oracle checks conservatively, with official source links and mandatory live Console verification before every resource creation. It includes the controlled Individual Pay As You Go procedure, a root-owned hard quota policy, USD 1 project and tenancy-root budgets with low-threshold alerts, project/root Cost Analysis and inventory schedules, limits/usage, zero-cost stop conditions, exact A1 and storage sizing, a dedicated subnet security list plus independently reviewed VNIC NSG boundary, VM/network/storage provisioning, Docker installation, host firewall, UUID mounts, DuckDNS token handling and HTTPS updater, manual deployment, migrations, access bootstrap, Wagtail Site reconciliation, HTTPS-only nominal adult user administration, bounded logs, persistence, backup/restore, access deactivation, and periodic cost/activity review.

No real hostname, DNS record, certificate, user, password, token, private key, backup, or production value was added to the checkout. The maintainer has already created or configured external OCI account, governance, compartment, and networking resources outside Git; their detailed operational evidence remains private and will be consolidated once before merge.

## Implemented files

- `docker-compose.staging.yml`: standalone staging topology with no development source bind mount or database port, reusable `json-file` rotation (`10m`, three files) for every service, and external-file pass-through for sensitive values without inline secret expressions.
- `docker/staging/Caddyfile`: automatic HTTPS reverse proxy and read-only `/media/` serving.
- `docker/staging/start-web.sh`: bounded database wait, static collection, and Gunicorn startup; executable mode `0755`.
- `docker/staging/staging.env.example`: safe validation placeholders only.
- `docker/web/Dockerfile`: fixed UID/GID 10001 application user and application-owned runtime paths.
- `config/settings/base.py`: environment-backed Wagtail Admin base URL and log-level schema.
- `config/settings/production.py`: fail-closed production contract, secure proxy/cookie behavior, console logging, and uploaded-file modes.
- `config/settings/tests.py`: focused production rejection and secure-contract coverage.
- `.gitignore` and `.dockerignore`: broader secret, key, dump, backup, and temporary-data exclusions.
- `docs/operations/oracle_always_free_staging.md`: operator-ready provisioning and operations runbook.
- `docs/operations/oracle_staging_uat.md`: real-environment acceptance checklist with evidence boundaries.
- `README.md`: developer-facing links and corrected current-scope wording.
- `docs/process/EPIC8-001_feedback.md`: this implementation handoff draft.

No model or editor workflow changed, so no migration or update to `docs/editorial/guia_de_uso.md` was required.

## Automated and local validation

The following checks passed locally using only dummy or fictional values:

- active branch confirmation: `EPIC8-001-oracle-always-free-staging`;
- focused Ruff and formatting checks for production settings/tests;
- focused production settings tests: `34 passed`;
- production `manage.py check --deploy` with dummy values: command completed with no errors and the warnings listed below;
- staging Compose configuration parsing with a safe temporary environment;
- complete safe-environment inspection confirmed that the effective web service receives `DATABASE_URL` and `DJANGO_SECRET_KEY` and the effective database service receives `POSTGRES_PASSWORD`, without printing any value;
- omission inspection confirmed all three pass-through values remain unresolved/null with no value to inject when omitted from a temporary environment; the mandatory runbook preflight stops that deployment, production settings reject the missing web values, and a new PostgreSQL volume refuses normal initialization without its password;
- exact published-port inspection: `proxy` publishes only `80` and `443`; `web` and `db` publish no host ports;
- effective Compose logging inspection: `proxy`, `web`, and `db` each resolve to `json-file` with `max-size=10m` and `max-file=3`;
- shell syntax check for `docker/staging/start-web.sh`;
- executable mode check for `docker/staging/start-web.sh`: `0755`;
- Caddy validation of the versioned `Caddyfile` using dummy environment values;
- local native x86_64 staging image build;
- application runtime identity: the staging web service is configured as UID/GID `10001:10001`, and the final image starts commands with that identity;
- static collection: `217` files copied and `635` post-processed with the manifest-backed WhiteNoise storage;
- disposable PostgreSQL migration run through the complete migration graph;
- `bootstrap_mvp_access` run twice without duplicate owned objects;
- disposable access query confirmed one each of `Director/editor`, `Curador SEO`, `Revisión SEO`, `Revisión editorial final`, and the owned workflow;
- staging web health check reached healthy state;
- internal public response and hashed static request returned HTTP 200;
- fictional media created by the web process was UID/GID `10001:10001`, mode `0644`, and was served through a disposable Caddy route;
- disposable custom-format PostgreSQL dump accepted by `pg_restore --list`;
- disposable media archive accepted by `tar --list`;
- local validation backup artifacts were non-empty, mode `0600`, and owned by the host maintainer user;
- repository inspection found no Docker-generated root-owned ticket files.

Technical-close gates:

- `make check`: passed; Ruff passed, migration drift check reported `No changes detected`, and all `227` tests passed;
- `make check` was not repeated after the focused Compose corrections and controlled-PAYG documentation amendment because no Python, migration, or application behavior changed; the pre-push repository gate remains responsible for the next general run, and the prior `227`-test evidence remains applicable;
- the current official Oracle upgrade/payment, quotas, budgets, Cost Analysis, limits/usage, and Cost Reports guidance was reviewed, and volatile operational statements were date-qualified;
- all 24 Bash-fenced runbook blocks passed non-executing `bash -n` syntax validation after the documentation amendment;
- focused contradiction review confirmed that the account model, data-volume/combined-storage sizing, shape fallback, and list-price gates match the approved amendment in the touched documentation and README;
- `git diff --check`: passed;
- final secret/unsafe-value review: passed for all ticket files;
- final ownership review: all repository ticket files remain owned by UID/GID `1000:1000`; no root/container-owned repository output was created.

## Validation boundaries and warnings

The production deploy check reports the existing five Treebeard/Wagtail future-compatibility warnings. It also reports Django security warnings `security.W005` and `security.W021` because HSTS subdomain inclusion and preload are deliberately disabled for a temporary third-party staging hostname. HTTPS redirect, secure cookies, and a one-hour HSTS duration remain enabled. These warnings are intentional for this environment and are not evidence that public HTTPS works.

The local image build proves only the current x86_64 host path. It does not prove Oracle Ampere ARM64 compatibility or that the approved 1-OCPU/4-GB A1 target is sufficient for this stack. Image tags and Python dependency ranges are not immutable, so a future rebuild can resolve newer compatible patch versions even though the deploy procedure pins an approved repository commit.

The local persistence checks used disposable Docker volumes and fictional media. They demonstrate the storage topology and normal container/redeploy behavior locally, not the Oracle block-volume mount, VM reboot persistence, or real public routing.

The local backup validation created and inspected disposable artifacts only. No destructive restore was run against persistent development or staging data; the formal restore drill remains EPIC8-003 scope.

## Failures, retries, and classification

- Repeated real `VM.Standard.A1.Flex` launch attempts while the account was Free Tier returned `Out of capacity` in the only available Availability Domain in Chile Central (Santiago). This is an external OCI capacity condition; the repository implementation and network configuration were not the cause. The approved Individual Pay As You Go amendment may improve capacity access but does not guarantee it, and no successful upgrade or VM launch is claimed here.
- Initial sandboxed Docker/build access could not write Buildx state or reach the Docker socket. Approved Docker access completed the same build and runtime checks. This was an execution-permission boundary, not a repository defect.
- Initial host-side access to a disposable published media port was blocked by the sandbox. The same fictional media request succeeded with approved local Docker/network access.
- The first disposable backup attempt could not reach Docker under the sandbox and left no usable evidence. The approved rerun replaced it and produced valid non-empty mode-0600 artifacts.
- A late focused-test attempt targeted the normal development `web` service after it was no longer running. The focused checks were rerun in the already built staging image with the checkout bind-mounted and passed. No repeated application failure remains.
- The first pass-through omission assertion expected Compose to remove unresolved mapping keys. Effective Compose JSON instead retains those keys with null values and injects no secret value. The focused assertion and documentation were corrected to test the actual null/no-value boundary; no secret-handling defect remained.

## Manual validation deferred to the maintainer

The following are explicitly pending on the real Oracle environment and must not be marked passed from this repository work:

- approved Free Tier to Individual Pay As You Go upgrade, completion email, final plan/account-type state, and current home region;
- root quota policy creation, propagation, statement-order/effective-limit verification, and zero-backup enforcement;
- both USD 1 budgets, all four alert rules/delivery, pre/post-upgrade project/root cost baselines, scheduled cost checks, settled Cost and Usage Report evidence, and full resource inventories;
- current **Always Free-eligible** labels, estimator disclaimer where applicable, allowances, limits, usage, and actual capacity for every resource;
- VM, VCN/dedicated subnet security list/VNIC NSG, public IP, approximately 46.6–50 GB boot volume, separate 50 GB data volume, and host firewall provisioning;
- native build and resource-fit evidence on the approved Oracle ARM64 A1 VM with 1 OCPU/4 GB;
- persistent storage mounted by UUID at `/srv/school-newsroom` and verified after a real reboot;
- real `/etc/school-newsroom/staging.env` creation and safe secret custody;
- DuckDNS account/update behavior, DNS propagation, Caddy certificate issuance/renewal, public HTTP-to-HTTPS redirect, and browser trust;
- external confirmation that only ports 22 (restricted where practical), 80, and 443 are reachable and PostgreSQL/Gunicorn remain private;
- real migrations, two access-bootstrap executions, Wagtail Site hostname reconciliation, and technical superuser creation;
- nominal adult `Director/editor` and `Curador SEO` user creation through HTTPS Admin;
- Home, news list/detail, media, secure Admin, workflow, permission-isolation, final-publication, and minors' privacy browser UAT;
- database/media survival across real container restarts, redeploy, and VM reboot;
- real Oracle database/media backup generation, checks, custody decision, and basic restore-procedure review;
- adult-user deactivation and the required immediate, settled, daily-first-week, weekly, and infrastructure-deploy Oracle cost/activity reviews.

Until DNS and browser-trusted HTTPS pass, no Wagtail Admin credential may be shared or used over the Internet.

## Security, privacy, cost, and scope review

- No real credentials, tokens, hostnames, IP addresses, certificates, private keys, dumps, archives, or cloud identifiers are present in ticket changes.
- The committed environment file is a deliberately unusable `.invalid` template, and production settings reject its secret/database placeholders.
- Sensitive Compose entries are pass-through mappings with no inline values. The external environment preflight checks presence without printing values, and no broad secret-scanner exclusion was added.
- The DuckDNS token is never placed in Compose, Git, command arguments, example values, feedback, or logs; the runbook captures it interactively into a root-readable curl configuration.
- Caddy alone publishes host ports. PostgreSQL remains on the internal backend network, and the application port remains Compose-internal so clients cannot connect directly and spoof the trusted proxy header.
- The runbook requires independent inspection of the subnet security-list collection and every VNIC NSG because their rules are cumulative; the VCN default security list must not remain associated with the staging subnet.
- Docker `json-file` logs are explicitly rotated for all services; systemd journal retention is documented separately for host services.
- Media is public by design; the runbook and UAT require fictional/non-sensitive content and prohibit real minor data.
- Both budgets are documented as soft alerting controls, never as hard spending limits. Hard quotas constrain the named A1/storage resources but do not directly cap monetary cost.
- The approved Individual Pay As You Go upgrade is limited to A1 capacity access under verified quotas, dual budgets, Always Free usage, and zero-cost acceptance. No Corporate conversion, paid shape/service, usage above Always Free limits, trial-only dependency, paid load balancer, managed database, external object storage, AWS/R2, Kubernetes, Terraform, GitHub deployment workflow, staging-branch automation, scheduled OCI backup, transactional email, or forced password-change feature was introduced.

## New Work Discovered

No blocking new repository work was discovered. The following remain separate concerns:

- EPIC8-002: staging-branch/GitHub deployment automation, if later approved;
- EPIC8-003: scheduled backups, formal restore drill, retention, and minimum observability;
- current Oracle capacity and native ARM64/resource-fit validation, which cannot be established locally;
- a real-domain/DNS/TLS lifecycle if the temporary free hostname is later replaced;
- transactional email/password recovery and enforced first-login password change;
- immutable dependency locks and container-image digests if byte-for-byte rebuild reproducibility becomes a requirement.

## Handoff restrictions

This draft does not mark EPIC8-001 accepted or complete because the approved ticket requires real Oracle access, HTTPS, persistence, backup, and browser/editorial UAT evidence. Do not commit, push, open a Pull Request, or merge as part of this implementation pass. The temporary checkout inspection and diff-review artifacts must remain untracked.
