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
