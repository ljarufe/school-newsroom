# Oracle Staging UAT

Status: **Pending maintainer execution on the real Oracle environment**.

This checklist records the minimum acceptance evidence for EPIC8-001. Expected results are not execution results. Do not mark an item passed until the named actor performs it on the real staging hostname and records non-sensitive evidence.

Use these companion procedures:

- [Oracle Always Free Demo/Staging Runbook](oracle_always_free_staging.md) for cloud, deployment, persistence, backup, restore, HTTPS, and cost operations;
- [Wagtail MVP Access Runbook](wagtail_access_mvp.md) for the canonical role matrix, fixed fictitious UAT data, workflow actions, privacy assertions, user lifecycle, and cleanup.

## Evidence rules

- Use only fictional/non-sensitive editorial content and images without real people.
- Never record passwords, secret keys, DuckDNS tokens, private SSH keys, expanded environment values, OCIDs, account numbers, private IP inventories, certificates' private keys, database dumps, or media archives.
- Do not record a real minor's name, image, school relationship, age, authorization, or internal record.
- Use separate active non-superuser sessions for `Director/editor` and `Curador SEO`. A technical superuser cannot demonstrate isolation.
- Record the date/time, actor role, action, observed result, pass/fail, and a safe evidence reference. A written expected result is not evidence.
- Redact public IPs, account identity, adult email addresses, and unrelated logs from screenshots.

## Preconditions

The maintainer must confirm all of these before UAT:

- the OCI account remains Free Tier/Always Free and has not been upgraded to Pay As You Go;
- every created resource was labeled **Always Free-eligible** with zero estimated cost at creation;
- the USD 1 monthly budget and low-threshold actual/forecast alerts are active, with the understanding that they are not hard spending limits;
- the VM is in the home region and the selected Compute/storage resources remain inside current free limits;
- the data volume is mounted at `/srv/school-newsroom` by UUID;
- `/srv/school-newsroom/media` and `/srv/school-newsroom/backups` exist with the documented ownership/modes;
- DuckDNS resolves the staging hostname to the VM;
- HTTP redirects to HTTPS and the browser trusts the certificate for the exact hostname;
- the subnet is associated only with `school-newsroom-staging-subnet`; the VCN default security list is not associated; the dedicated list has no TCP ingress and retains only required stateful egress plus essential ICMP/path-MTU rules;
- every NSG attached to the VNIC has been inspected; `school-newsroom-staging-web` contains only the approved stateful TCP ingress, with port 22 restricted to the maintainer CIDR and ports 80/443 public;
- neither the subnet security lists nor any VNIC NSG contains an unexpected rule for TCP 22, 8000, 5432, or 5434; checking the NSG alone is not accepted as proof because OCI applies the union of both rule collections;
- Caddy is the only service publishing host ports, PostgreSQL is not public, and the guest/combined OCI firewall boundaries expose only the approved ports;
- `proxy`, `web`, and `db` each use Docker `json-file` logging with `max-size=10m` and `max-file=3`;
- no Admin credential has been shared or used over plain HTTP;
- `DJANGO_SETTINGS_MODULE=config.settings.production`, `DEBUG=False`, secure cookies, strict hosts/origins, HTTPS Admin base URL, and `SEO_DEFAULT_NOINDEX=true` are effective;
- there is a known technical superuser and two distinct approved nominal adult staging users, one for each role, with private temporary passwords.

If HTTPS or any cost/security precondition fails, stop before credential-based Admin UAT.

## UAT identities and fictional data

Use the fixed fictitious content and scenario steps in the [canonical UAT section](wagtail_access_mvp.md#uat-del-mantenedor), but execute them with the two approved nominal adult staging accounts:

| Canonical scenario-role label | Real staging session |
| --- | --- |
| `uat_director` | the approved nominal adult account that is active, non-superuser, and assigned only to `Director/editor` |
| `uat_seo` | the approved nominal adult account that is active, non-superuser, and assigned only to `Curador SEO` |

`uat_director` and `uat_seo` are scenario-role labels, not required usernames and not instructions to create extra generic accounts. Do not introduce shared accounts by default. If an explicitly temporary account is necessary, tie it to one identified adult operator, keep it non-superuser with only the scenario's group, and deactivate it after UAT. Passwords must be communicated privately. Do not create accounts for students, minors, teachers/monitors, or parents.

## 1. Deployment and HTTPS smoke

Record the result of each item:

1. `docker compose ... ps` shows `db` healthy, `web` healthy, and `proxy` running/restarting normally.
2. The subnet details show `school-newsroom-staging-subnet` as the only associated security list and show that the VCN default security list is absent. The dedicated list has no TCP ingress and only the documented stateful egress and essential ICMP/path-MTU rules.
3. Inspect every NSG attached to the VNIC. Confirm `school-newsroom-staging-web` has only TCP 22 from the maintainer CIDR and TCP 80/443 from `0.0.0.0/0`; confirm neither the subnet security lists nor any attached NSG has unexpected TCP 22, 8000, 5432, or 5434 rules. NSG evidence by itself is insufficient.
4. Repository review and host socket inspection show only Caddy publishing 80/443; 8000, 5432, and 5434 are not public.
5. Run the runbook's targeted `docker compose ps -q` plus formatted `docker inspect` check. Record that `proxy`, `web`, and `db` each report `driver=json-file max-size=10m max-file=3`, without recording environments.
6. `http://<staging-hostname>/` redirects to `https://<staging-hostname>/`.
7. The browser shows a trusted certificate matching the exact hostname.
8. The anonymous Home opens over HTTPS.
9. `/noticias/` opens over HTTPS.
10. A fictional news detail opens and its image loads from `/media/` over HTTPS.
11. `/admin/` redirects to the HTTPS login page and secure cookies are present after login.
12. Public metadata remains `noindex, follow` for the staging environment.
13. Bounded Caddy, Gunicorn/Django, and PostgreSQL logs contain no credentials, tokens, environment dumps, or private minor data. Systemd journal retention is checked separately for host services such as the DuckDNS updater and is not treated as the Docker-log bound.

Do not use an actual hostname, IP, or certificate identifier in the repository evidence file.

## 2. Migrations, access bootstrap, and site

1. Apply migrations using the exact command in the Oracle runbook and record success/failure.
2. If `0009_reconcile_mvp_access` stops on assigned obsolete groups or unexpected dependencies, record the safe error classification and stop. Do not delete blindly.
3. Run `bootstrap_mvp_access` twice.
4. Confirm exactly one group named `Director/editor` and exactly one named `Curador SEO`.
5. Confirm obsolete exact-name groups `Moderadores` and `Editores` are absent when the guarded migration was able to reconcile them.
6. Confirm tasks `Revisión SEO` and `Revisión editorial final` exist once each.
7. Confirm workflow `Revisión editorial` exists once, orders the SEO task before final editorial review, and is assigned to the `Inicio` subtree.
8. Confirm legacy `Revisión editorial MVP` and `Aprobación de moderadores` objects are absent where the guarded migration allowed cleanup.
9. Confirm the default Wagtail Site uses the staging hostname, port 443, and the intended `Inicio` root page.
10. Confirm the second bootstrap did not change object counts or create duplicates.

## 3. Technical and nominal adult access

1. Sign in as the technical superuser over HTTPS.
2. Create/review the approved nominal adult Director account through **Configuración** -> **Usuarios**, with **Administrador** clear and only `Director/editor` selected. This account executes the canonical `uat_director` scenario.
3. Create/review the approved nominal adult SEO account, with **Administrador** clear and only `Curador SEO` selected. This account executes the canonical `uat_seo` scenario.
4. Deliver temporary passwords privately and test **Cuenta** -> **Cambiar contraseña** without recording either password.
5. Confirm the nominal Director account cannot administer users/groups/permissions.
6. Confirm the nominal SEO account cannot administer users/groups/permissions and cannot see the `Editorial` area or internal minor snippets.

## 4. Editorial and workflow UAT

Execute all applicable steps in [Wagtail MVP Access Runbook — UAT del mantenedor](wagtail_access_mvp.md#uat-del-mantenedor), using separate browser sessions:

1. Create the documented fictitious school, contributor group, internal fictitious minor record, and non-person image fixtures as `Director/editor`/technical superuser where authorized.
2. Using the nominal Director account mapped to the canonical `uat_director` scenario, create the documented direct-publication fictional news item, including required image caption, alt text, credit, public byline, and SEO fields.
3. Confirm a saved draft is not public, then use the authorized direct publish override and verify the public detail.
4. Using the nominal Director account, create the documented workflow fictional news item and send it to `Revisión editorial`.
5. Using the nominal SEO account mapped to the canonical `uat_seo` scenario, confirm only the authorized SEO surface and read-only public context are visible.
6. Confirm the SEO context does not expose the internal fictitious minor name, age band, privacy flags, or authorization controls.
7. Request changes, confirm access ends appropriately, revise as director, resubmit, and approve SEO.
8. Confirm the nominal SEO account cannot open or approve `Revisión editorial final` and cannot publish.
9. Using the nominal Director account, select the normal final action `Aprobar y Publicar` and confirm final publication.
10. Verify anonymously that internal contributor data is absent from public HTML/metadata while the intended public credit is present.
11. Execute the documented Home and institutional-page SEO context checks.
12. Re-run `bootstrap_mvp_access` after UAT and confirm no duplicate or broadened permissions.

The existing access runbook defines the exact Spanish labels, fictitious content, expected boundaries, and cleanup. Do not replace its expected results with a generic “works” claim.

## 5. Database and media persistence

Using the fictional page/image created above:

1. Record a safe page slug and a checksum/reference for the non-person test image.
2. Restart `web`; confirm the page remains in PostgreSQL and the image URL still loads.
3. Restart `proxy`; confirm both remain available.
4. Restart `db`, wait for its health check, and confirm both remain available.
5. Perform a manual same-commit `up -d --build` redeploy without `-v`; confirm both remain available.
6. Confirm the media file remains below `/srv/school-newsroom/media` with UID/GID 10001 and public-readable file mode, without copying the file into evidence.
7. Confirm the PostgreSQL volume is still `school_newsroom_staging_postgres_data`.

A VM reboot test is pending real Oracle validation. After reboot, additionally verify the UUID mount, Docker startup, Compose status, database, media, DuckDNS, and HTTPS before marking reboot persistence passed.

## 6. Backup evidence

1. Use a short maintenance window and run the documented database/media backup commands.
2. Confirm a non-zero custom-format database dump, media archive, and checksum file exist under `/srv/school-newsroom/backups` with mode 0600.
3. Confirm `pg_restore --list` accepts the database dump.
4. Confirm `tar --list` accepts the media archive.
5. Confirm neither backup is below the repository or media web root.
6. Record whether an adult maintainer-controlled encrypted off-server copy was made; do not assume any external destination is free.

EPIC8-001 does not require a destructive restore drill. Review the basic restore procedure and leave a real restore as pending unless the maintainer separately authorizes a disposable/maintenance target.

## 7. Deactivation and access removal

1. If an explicitly temporary adult account was created for UAT, open **Configuración** -> **Usuarios** as the technical superuser and clear **Activo** for that account. Do not deactivate an approved ongoing nominal account unless its access is actually being withdrawn.
2. Confirm that account can no longer sign in.
3. Leave every explicitly temporary account inactive after UAT; do not reactivate it as a convenience account.
4. If no temporary account exists, perform this check only when an approved nominal adult's access is genuinely being withdrawn. Do not create an extra account solely for this check.
5. Preserve account/history unless the environment's explicit retention policy authorizes deletion.
6. Confirm no shared credential was introduced as a replacement.

## 8. Cost and activity evidence

After deployment/UAT:

1. Open **Billing & Cost Management** -> **Cost Management** -> **Budgets** and confirm the USD 1 monthly budget and both low-threshold alerts remain active.
2. Open **Billing & Cost Management** -> **Cost Management** -> **Cost Analysis**, filter to the staging compartment/current month, and record the observed cost without account identifiers.
3. Open **Governance & Administration** -> **Tenancy Management** -> **Limits, Quotas and Usage** and review current Compute/block-volume usage in the home region.
4. Review the instance metrics/activity and current Oracle idle-instance policy. Do not manufacture traffic to avoid reclamation.
5. Confirm no unexpected Load Balancer, managed database, Object Storage, paid public IP, backup, snapshot, or trial-only resource exists.

Any non-zero cost or unexpected resource is a failed acceptance item until investigated. Budget status alone never proves zero cost.

## Result record template

Create a private UAT record outside Git or use a ticket system approved for non-sensitive evidence. For every item use:

```text
Check ID:
Executed at (UTC):
Actor role:
Action performed:
Observed result:
Pass / Fail / Blocked:
Safe evidence reference:
Notes / follow-up:
```

## EPIC8-001 acceptance summary template

Do not fill this section in repository documentation. Use it in the maintainer's private execution record:

```text
Oracle account/resource zero-cost verification: Pending
Home-region and free-capacity verification: Pending
Native VM architecture build: Pending
Subnet security-list and VNIC NSG verification: Pending
Public/guest firewall verification: Pending
Bounded Docker logging verification: Pending
DuckDNS and valid HTTPS: Pending
Public Home/news/detail smoke: Pending
HTTPS Admin access: Pending
Migrations/bootstrap idempotency: Pending
Director/editor UAT: Pending
Curador SEO isolation/workflow UAT: Pending
Minor privacy verification: Pending
Container/redeploy persistence: Pending
VM reboot persistence: Pending
Real staging backup generation: Pending
Basic restore procedure reviewed: Pending
Adult-user deactivation: Pending
Final Cost Analysis review: Pending
```

## Cleanup

Follow the canonical UAT cleanup sequence for fictional pages, media, and snippets. Cancel active workflows before page cleanup and preserve attribution where required. Deactivate every explicitly temporary adult test account after UAT; do not create or retain generic shared accounts. Keep approved nominal adult accounts active only while their real access remains authorized. Never delete the owned groups, tasks, or `Revisión editorial` workflow. Do not delete Docker volumes, the Oracle data volume, or backups as part of ordinary UAT cleanup.
