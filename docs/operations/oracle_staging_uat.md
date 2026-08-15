# Oracle Staging UAT

Status: **Completed — EPIC8-001 accepted on the real Oracle staging environment**.

This document records the final minimum acceptance boundary for EPIC8-001. The maintainer and the approved adult product owner/Director executed the real-environment checks with fictional, non-sensitive content. Detailed screenshots, account identities, timestamps, and cloud identifiers remain in private evidence and are intentionally not committed.

Companion procedures:

- [Oracle Always Free Demo/Staging Runbook](oracle_always_free_staging.md) for provisioning and operations;
- [Wagtail MVP Access Runbook](wagtail_access_mvp.md) for the canonical roles, workflow, privacy assertions, and cleanup.

## Evidence rules

- Use only fictional/non-sensitive editorial content and images without real people.
- Never record passwords, secret keys, DuckDNS tokens, private SSH keys, expanded environment values, OCIDs, account numbers, database dumps, or private information about minors.
- Use separate active non-superuser sessions for `Director/editor` and `Curador SEO`; a technical superuser does not prove role isolation.
- Keep detailed evidence private and record only safe pass/fail summaries in Git.

## Final environment preconditions — Passed

Private execution evidence confirmed:

- the controlled Individual Pay As You Go amendment was used only to improve A1 capacity while all project resources remained Always Free and expected cost remained zero;
- the hard quota policy constrained A1 to 1 OCPU/4 GB, combined boot/block storage to 100 GB, blocked other Compute families, and blocked OCI volume backups;
- both USD 1 budgets and all four low-threshold Actual/Forecast alerts were active;
- the VM was a home-region `VM.Standard.A1.Flex` running Ubuntu 24.04 LTS on native `aarch64`;
- one approximately 50 GB boot volume and one 50 GB Balanced block volume were the only project storage resources;
- the data volume was mounted by UUID at `/srv/school-newsroom` and survived reboot;
- the dedicated subnet security list and VNIC NSG exposed only the approved ingress boundary;
- Caddy was the only service publishing host ports, with Gunicorn and PostgreSQL private;
- Docker logging was bounded for `proxy`, `web`, and `db`;
- DuckDNS resolved correctly, HTTP redirected to HTTPS, and the browser trusted the certificate;
- production settings, secure cookies, explicit hosts/origins, HTTPS Admin URL, and staging `noindex` were effective;
- a technical superuser and distinct nominal adult Director/editor and Curador SEO accounts existed.

## 1. Deployment and HTTPS smoke — Passed

- `db` healthy, `web` healthy/running, and `proxy` running.
- Only ports 80/443 were published by Compose; application and database ports were private.
- `proxy`, `web`, and `db` used `json-file` with `max-size=10m` and `max-file=3`.
- HTTP returned a permanent redirect to HTTPS.
- Home and `/noticias/` returned HTTP 200 over HTTPS.
- A fictional news detail and its `/media/` image loaded over HTTPS.
- `/admin/` redirected to the HTTPS login page.
- The certificate matched the staging hostname and was current.
- Staging metadata remained `noindex, follow`.

## 2. Migrations, access bootstrap, and site — Passed

- Migrations completed without an unresolved guarded-access conflict.
- `bootstrap_mvp_access` completed repeatedly without duplicate groups, tasks, workflow, or broadened permissions.
- Exactly one `Director/editor` group and one `Curador SEO` group were present.
- The owned tasks and `Revisión editorial` workflow were reconciled.
- The default Wagtail Site used the staging hostname and port 443.

## 3. Technical and nominal adult access — Passed

- The technical superuser authenticated only through HTTPS.
- The nominal Director account was active, non-superuser, and assigned only to `Director/editor`.
- The nominal SEO account was active, non-superuser, and assigned only to `Curador SEO`.
- No student, minor, teacher/monitor, parent, or shared generic account was introduced.

## 4. Editorial, workflow, SEO, and privacy UAT — Passed

Using the canonical fictional scenario:

- Director/editor created and saved draft content, then exercised the authorized direct-publication path.
- Director/editor created a second item and started `Revisión editorial`.
- Curador SEO saw only the authorized SEO surface and read-only public context.
- Internal fictitious minor data and privacy controls were absent from SEO/public context.
- Request-changes, revision, resubmission, and SEO approval behaved as specified.
- Curador SEO could not approve `Revisión editorial final` and could not publish.
- Director/editor completed the normal `Aprobar y Publicar` final action.
- Anonymous Home, listing, detail, image, byline, and metadata checks passed.
- Internal contributor/minor data remained absent from public HTML and metadata.
- A post-UAT bootstrap rerun did not duplicate or broaden access.

## 5. Database and media persistence — Passed

With the fictional UAT page and image:

- content and media survived `web`, `proxy`, and `db` restarts;
- PostgreSQL returned healthy after restart;
- content and media survived a same-SHA `up -d --build` redeploy without volume deletion;
- media remained below `/srv/school-newsroom/media` with the approved application ownership;
- PostgreSQL remained on `school_newsroom_staging_postgres_data`;
- a real VM reboot preserved the UUID mount, Docker/Compose runtime, database content, media, DuckDNS, and HTTPS.

## 6. Backup and restore boundary — Accepted deferral

Real backup generation, retention, off-server custody, restore commands, and restore drills were explicitly removed from the EPIC8-001 acceptance gate. They remain EPIC8-003 work and were not executed or claimed as passed here. The absence of a staging backup does not block this ticket under the approved closure amendment.

## 7. Access lifecycle — Passed

- Approved nominal adult accounts remain active only while their staging access is authorized.
- No convenience/shared account was retained.
- Any explicitly temporary adult account is deactivated rather than deleted so editorial attribution remains intact.

## 8. Cost, quota, budget, and inventory evidence — Passed

The maintainer completed the agreed closure schedule of three project/root cost and inventory checkpoints:

- project Cost to Date: zero;
- project forecast: zero or no positive forecast;
- tenancy Cost to Date: zero;
- tenancy forecast: zero or no positive forecast;
- paid SKU detected: no;
- both budgets active: yes;
- all four budget alerts active: yes;
- expected inventory only: yes;
- unexpected resource: none.

The accepted final inventory contained one A1 VM, one approximately 50 GB boot volume, one 50 GB block volume, and the documented network/governance resources. There was no OCI volume backup, Load Balancer, managed database, Object Storage dependency, customer-managed Vault key, or other paid project resource.

The original seven-day closure schedule was replaced by the maintainer-approved three-checkpoint schedule. Weekly reviews while staging remains active are ongoing operations, not an open EPIC8-001 acceptance item. Any future non-zero cost, positive forecast, paid SKU, quota widening, or unexpected resource remains a stop-and-investigate event.

## Final acceptance record

```text
Controlled Individual PAYG boundary: PASS
Budgets and four alert rules: PASS
Hard quota policy: PASS
Always Free capacity and approved inventory: PASS
Native ARM64 VM/runtime: PASS
Network and firewall boundary: PASS
Bounded Docker logging: PASS
DuckDNS and browser-trusted HTTPS: PASS
Public Home/news/detail smoke: PASS
HTTPS Admin: PASS
Migrations/bootstrap idempotency: PASS
Director/editor UAT: PASS
Curador SEO isolation/workflow UAT: PASS
Minor privacy verification: PASS
Container/redeploy persistence: PASS
VM reboot persistence: PASS
Three zero-cost checkpoints: PASS
Backup/restore execution: DEFERRED TO EPIC8-003 — ACCEPTED, NON-BLOCKING
Overall EPIC8-001 operational acceptance: PASS
```

## Cleanup

Follow the canonical cleanup sequence for fictional pages, media, and snippets. Cancel active workflows before page cleanup and preserve attribution where required. Keep approved nominal adult accounts active only while access remains authorized; deactivate temporary accounts. Never delete the owned groups, tasks, workflow, PostgreSQL named volume, or Oracle data volume during ordinary UAT cleanup.

## EPIC8-002 operator-triggered deployment UAT — Pending post-merge

Status: **Pending — execute only after EPIC8-002 is merged to `main` and the maintainer has synchronized the local checkout**.

This matrix extends the accepted EPIC8-001 environment without changing the OCI topology, cost boundary, backup boundary, product schema, permissions, workflow, or staging data policy. Use only fictional/non-sensitive editorial content and preserve the evidence rules above.

The maintainer-approved EPIC8-002 interaction amendment allows exactly one local startup prompt for the encrypted staging SSH private-key passphrase. The passphrase remains in the maintainer's password manager and must not be written to `.env`, Git, shell scripts, logs, evidence, or staging files. After that startup prompt, the deployment must run without SSH login-password prompts, `sudo` prompts, confirmations, editors, pauses, or remote input.

### A. First automated deploy — Pending

From the maintainer host, outside the Dev Container:

```bash
cd ~/Projects/school-newsroom
make staging-deploy
```

Record safe pass/fail evidence for:

- `.venv-ops` bootstrap completes automatically when required;
- Fabric prompts once locally for the private-key passphrase;
- `origin/main` is fetched and its current full SHA becomes the target;
- the local branch and local worktree are not deployment authority;
- the SSH alias resolves and the remote preflight passes;
- `sudo -n` succeeds without another prompt;
- the remote checkout is clean and detached;
- the non-blocking deployment lock is acquired;
- the previous SHA and target SHA are printed;
- checkout, build, `migrate --noinput`, `bootstrap_mvp_access`, Wagtail Site reconciliation, and `up -d` execute in order;
- `db` and `web` become healthy, `proxy` runs, and the health timeout is bounded;
- HTTP redirects to HTTPS;
- HTTPS Home and `/noticias/` return successfully;
- `/admin/` redirects to the HTTPS login path;
- TLS certificate and hostname verification pass;
- remote HEAD equals the target SHA;
- `/var/lib/school-newsroom/deployments/history.jsonl` contains the safe deployment result;
- `/var/lib/school-newsroom/deployments/current.json` represents the successful target only after all checks pass;
- no environment values, passphrase, private key, passwords, tokens, OCI identifiers, or private information are printed.

### B. Idempotent second deploy — Pending

Run again with unchanged `origin/main`:

```bash
make staging-deploy
```

Confirm:

- the same target SHA is detected;
- the result is `already_deployed`;
- no build runs;
- no migrations run;
- no service recreate runs;
- no HTTPS smoke is repeated as a material deployment;
- the lock is released cleanly;
- the command exits successfully.

### C. Optional approved SHA — Test-covered; real rollback not required

The automated tests must prove that:

```bash
make staging-deploy SHA=<sha>
```

resolves a commit and rejects a SHA outside `origin/main` history.

A real deployment of an older approved SHA is optional and must be performed only when operationally useful. Do not roll back database migrations automatically and do not move staging backward solely to satisfy this UAT.

### D. Controlled failure behavior — Test-covered

Use doubles or a disposable environment to validate:

- SSH connection failure before mutation;
- `sudo -n` failure before mutation;
- dirty remote checkout;
- occupied lock;
- build failure;
- migration failure without database rollback;
- bootstrap and Wagtail Site failure;
- service recreate failure;
- bounded health timeout and diagnostics;
- HTTPS smoke failure;
- transport exceptions preserving the active deployment stage rather than being mislabeled as a connection failure.

Do not deliberately break the real staging database or induce a real failed migration.

### E. Public/editorial regression after the first automated deploy — Pending

Using fictional/non-sensitive content, confirm the deployed staging environment still passes:

- Home;
- `/noticias/`;
- one published news detail;
- HTTPS images;
- captions, alt text, and credits;
- classification and public byline;
- internal contributor/minor data absent from public HTML and metadata;
- HTTPS Admin;
- Director/editor and Curador SEO boundaries;
- persistence after restarting `web`.

### F. Deferred EPIC6-003 sharing observations — Pending

Using the same fictional published news item, confirm:

- the sharing component appears after the body and before tags;
- the effective canonical is the public HTTPS URL;
- the public social image and existing caption/alt/credit behavior remain intact;
- Web Share works when supported by the device/browser;
- Clipboard works;
- WhatsApp receives title and URL;
- X receives title and URL;
- Facebook receives the canonical URL;
- email receives subject, description, and canonical URL.

Record only the observed behavior of external previews:

- WhatsApp preview;
- X card/preview through the currently available mechanism;
- Facebook crawler/preview;
- cache/refetch behavior when the platform exposes it.

External services may change UI, cache metadata, require a session, or delay refreshes. This UAT validates the deployed HTTPS URL, metadata, image, and observed behavior; it does not guarantee permanent third-party preview behavior.

### EPIC8-002 acceptance record — Pending

Update this block only after the real post-merge execution:

```text
First automated deploy: PENDING
Single local passphrase prompt: PENDING
No later interactive prompts: PENDING
Default origin/main target: PENDING
Remote detached HEAD matches target: PENDING
Build/migrate/bootstrap/Site/recreate: PENDING
Health and HTTPS smoke: PENDING
Deployment records: PENDING
Idempotent second deploy: PENDING
Optional SHA contract: TEST-COVERED
Controlled failure matrix: TEST-COVERED
Public/editorial regression: PENDING
EPIC6-003 sharing regression: PENDING
External preview observations: PENDING
Overall EPIC8-002 operational acceptance: PENDING
```

## EPIC8-005 staging abuse-protection UAT — Passed

Status: **Completed — Stage B/UAT passed on the real Oracle staging
environment at deployed SHA `cceddcb6b35e17ddcd62bd5e983ad91036f9a21a`.**

The deployed proxy reported Caddy `v2.11.4` with
`http.handlers.rate_limit`; `proxy`, `web`, and `db` were healthy/running.
The approved calibrated policy was general `60 events / 10s`, search
`30 events / 60s`, and login POST `8 events / 60s`.

Observed controlled results:

- Home returned 200, `/noticias/` returned 200, and `/admin/` returned 302.
  Normal public and Admin navigation produced no ban or false positive.
- The general run produced 60 responses with 200, then 10 with 429; recovery
  passed.
- The search run produced 30 responses with 200, then five with 429;
  `Retry-After: 42` was observed and recovery returned 200.
- The credential-free login POST run produced eight 403 responses before
  limiting, then two 429 responses; `Retry-After: 49` was observed. After
  recovery, the credential-free POST again returned 403 rather than 429.
- The bounded JSON access log contained `buscar=REDACTED`; direct `buscar`,
  Authorization, Cookie, Proxy-Authorization, and Referer search markers were
  absent.
- Ubuntu Fail2ban `1.0.2-3ubuntu0.1` was installed, configuration testing
  passed, and the service was active/running. The controlled automatic-ban
  test reported `Total failed: 49`, `Currently banned: 1`, and `Total banned:
  1`. `DOCKER-USER` contained the TCP 80/443 jump to `f2b-sn-web`; that chain
  contained the controlled-source DROP and RETURN. SSH remained usable while
  HTTP/HTTPS timed out. Automatic expiry restored HTTP 200, `Currently banned`
  returned to 0, and `Total banned` remained 1.

The maintainer also reported PASS for manual ban/unban, the operational
allowlist, break-glass stop/restart, service/resource checks, the public/private
port and Docker-network boundary, IPv6 applicability, OCI inventory/shape, and
zero Actual/Forecast cost. No numeric resource readings, IP addresses, secrets,
or private operational evidence are recorded here.

### Stage B bootstrap findings

The real bootstrap exposed two defects. Its broad `grep 'CALIBRATE_'` rejected
a fully rendered jail because the versioned explanatory comment retained that
text. Also, the immediate post-restart jail-status call could race the
Fail2ban socket even though systemd subsequently reported the daemon ready.

The follow-up source change limits placeholder detection to active `findtime`,
`maxretry`, `bantime`, and `ignoreip` assignments, and retries client readiness
for at most ten seconds before failing closed. This records the durable fix; it
does not claim that the follow-up branch itself has been deployed.

```text
Host bootstrap / Fail2ban 1.0.x: PASS
Calibrated general/search/login values: PASS — 60/10s, 30/60s, 8/60s
Normal public and Admin navigation: PASS
General excess / 429 / recovery: PASS — 60x200, 10x429, recovery passed
Search excess / 429 / Retry-After / recovery: PASS — 30x200, 5x429, 42, 200
Login POST excess / 429 / Retry-After / recovery: PASS — 8x403, 2x429, 49, 403
Bounded and redacted JSON access log: PASS
Automatic temporary ban / expiry: PASS
Manual ban / unban: PASS
Operational allowlist: PASS
SSH usable during web ban: PASS
Public/private port boundary: PASS
Health / restart loop / resource checks: PASS
OCI inventory / shape / zero cost: PASS
Break-glass exercise: PASS
Overall EPIC8-005 operational acceptance: PASS
```
