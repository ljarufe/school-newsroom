# EPIC8-005 Feedback

## Final status

**EPIC8-005 is complete.**

The implementation was merged, deployed to the real Oracle staging environment, calibrated, and accepted through Stage B operational UAT. The post-merge bootstrap defects discovered during that execution have focused durable source fixes and regression coverage in this follow-up.

No product, infrastructure, deployment, calibration, or staging UAT work remains pending for EPIC8-005. A later pull-request review correction limited to this follow-up delta does not require another documentation-only status update unless it materially changes the scope, implementation, validation evidence, or operational conclusions recorded here.

## Implementation summary

EPIC8-005 implements a two-layer, zero-cloud-cost staging control:

1. Caddy 2.11.4 is built reproducibly with `caddy-ratelimit` v0.1.0 and applies
   independent per-network-peer general, archive-search, and Wagtail-login-POST
   sliding-window zones.
2. Host Fail2ban 1.0.x consumes Caddy's bounded/redacted JSON access log and
   escalates repeated 429 responses to a temporary TCP 80/443 ban in
   `DOCKER-USER`.

The change does not add a Django limiter, application persistence, migrations,
cloud infrastructure, paid services, or a new public port.

## Files changed

- `docker/staging/Caddy.Dockerfile`
- `docker/staging/Caddyfile`
- `docker/staging/staging.env.example`
- `docker-compose.staging.yml`
- `ops/staging_deploy.py`
- `ops/staging_security/bootstrap_fail2ban.sh`
- `ops/staging_security/fail2ban/action.d/school-newsroom-docker-user-web.conf`
- `ops/staging_security/fail2ban/filter.d/school-newsroom-caddy-429.conf`
- `ops/staging_security/fail2ban/jail.d/school-newsroom.local.example`
- `ops/validate_staging_abuse_protection.sh`
- `ops/validate_staging_fail2ban.sh`
- `tests/fixtures/staging_security/Caddyfile`
- `tests/fixtures/staging_security/caddy-access.json`
- `tests/fixtures/staging_security/jail.local`
- `tests/fixtures/staging_security/staging-compose-test.env.example`
- `tests/ops/test_staging_deploy.py`
- `tests/ops/test_staging_security.py`
- `THIRD_PARTY_NOTICES.md`
- `docs/operations/oracle_always_free_staging.md`
- `docs/operations/oracle_staging_uat.md`
- `docs/process/EPIC8-005_feedback.md`

## Tool selection and design decisions

Evaluated controls were the standard Caddy image, a custom Caddy module,
Fail2ban with iptables-nft, UFW/INPUT-only blocking, a parallel native nftables
ruleset, and Django middleware/dependencies.

- The standard Caddy 2.11.4 image was not sufficient because the accepted live
  baseline proved it has no rate-limit module.
- `github.com/mholt/caddy-ratelimit` v0.1.0 was selected because its upstream
  source provides native Caddyfile matchers, multiple simultaneous zones, a
  sliding window, 429 errors, and `Retry-After` without Redis or application
  state. The dependency is Apache-2.0 and is pinned by tag. Both official Caddy
  build/runtime images are pinned by multi-architecture digest; Caddy remains
  2.11.4 on amd64 and arm64.
- Fail2ban is an escalation layer only. Ubuntu Noble package
  `1.0.2-3ubuntu0.1` is the accepted host baseline, and the versioned
  configuration supports Fail2ban 1.0.x. Its license is GPL-2.0.
- The action uses `DOCKER-USER`, not `INPUT`, because Docker-published ports are
  forwarded before a conventional host INPUT ban can protect the proxy. The
  dedicated chain is entered only for TCP destination ports 80 and 443 and
  never references SSH/22.
- UFW remains the base host boundary. No native nftables service/ruleset is
  introduced alongside Docker/UFW's iptables-nft ownership.
- A Django limiter was rejected because Caddy can express every approved scope
  before Gunicorn, and in-memory Django worker counters would not provide one
  global guarantee.

## Protected routes and identity

- `general_dynamic`: every request handled by the application proxy branch;
- `news_search`: exact `/noticias/` requests with a `buscar` parameter;
- `wagtail_login_post`: exact `POST /admin/login/` requests.

All keys use Caddy `{remote_host}`, the immediate verified network peer. No
`trusted_proxies`, `client_ip`, or request header is used as rate-limit
identity. Search and login requests also consume the general zone. Their
approved operational settings must be stricter after calibration.

`/media/*` remains in Caddy's earlier direct file handler and outside the
application limiter because it does not consume Gunicorn/PostgreSQL. Static
requests continue through the current application path and count toward the
general policy; static serving was not redesigned.

## Threshold and allowlist ownership

The six Caddy allowance/window values are required Compose environment inputs.
`docker/staging/staging.env.example` documents each one but intentionally
leaves it empty so a new operator or environment cannot inherit synthetic or
unreviewed values accidentally. Synthetic executable values exist only in
`tests/fixtures/staging_security/staging-compose-test.env.example`; they must
not be used as staging policy.

Real staging calibration is complete. The approved EPIC8-005 staging Caddy
policy is:

```text
general_dynamic: 60 events / 10s
news_search: 30 events / 60s
wagtail_login_post: 8 events / 60s
```

These values were selected from observed normal staging traffic and accepted
through controlled real-environment UAT. They are staging-specific and must not
be represented as production-ready policy.

The accepted host-local Fail2ban escalation policy used during Stage B was:

```text
findtime = 300
maxretry = 30
bantime = 900
```

Operational `ignoreip` remains host-local. The versioned jail template contains
deliberate `CALIBRATE_*` tokens, so it cannot be activated accidentally. No
personal maintainer IP/CIDR is committed.

## Logging and privacy

Caddy writes `/var/log/school-newsroom/caddy/access.json` through an explicit
host mount. Rotation is 10 MiB, at most three rolled files, and no more than 72
hours for rolled files. Request bodies are not logged. `buscar` values are
replaced by `REDACTED`, while Authorization, Cookie, Proxy-Authorization, and
Referer headers are explicitly deleted. Remote IP, timestamp, request identity, and
status remain available to the Fail2ban filter.

Fail2ban's host database is operational ban state, is not added to product
backups, and follows the packaged service's restart restoration behavior.

## Deployment and security invariants

The deployment build stage now builds `web` and `proxy`, before the unchanged
sequence:

```text
migrate -> update_index -> bootstrap -> Wagtail Site -> services/up -> health/smoke/registration
```

Remote preflight requires iptables, `DOCKER-USER`, an active named Fail2ban
jail, and the Caddy access-log file. Package installation remains an explicit
one-time host bootstrap and is never hidden in Compose/application startup.
The same-SHA successful path still skips build, migration, recreate, smoke, and
registration.

Only proxy publishes 80/443. Web exposes only container 8000, PostgreSQL has no
published port, the backend network remains internal, Docker log bounds and
`no-new-privileges` remain in place, and media/Docker volumes are preserved.

## Automated validation

Passed:

- `docker compose --env-file tests/fixtures/staging_security/staging-compose-test.env.example -f docker-compose.staging.yml config --quiet`
  — Compose configuration valid with isolated test/config values.
- `docker compose run --rm web pytest -q tests/ops/test_staging_security.py tests/ops/test_staging_deploy.py -o cache_dir=/tmp/school-newsroom-pytest-cache`
  — 37 passed.
- focused Ruff check and format check for `ops/staging_deploy.py`,
  `tests/ops/test_staging_deploy.py`, and
  `tests/ops/test_staging_security.py` — passed after one mechanical import
  layout fix.
- `ops/validate_staging_abuse_protection.sh` — passed. The pinned custom image
  built; `caddy version` reported 2.11.4; `caddy list-modules` contained
  `http.handlers.rate_limit`; the real Caddyfile validated; an invalid event
  value failed closed; normal requests passed; general, search, and login POST
  excess returned 429 with `Retry-After`; cooldown recovery passed; repeated
  media remained outside the limiter; the real JSON logger replaced `buscar`
  and omitted submitted Authorization/Cookie values.
- `ops/validate_staging_fail2ban.sh` — passed in a disposable Ubuntu 24.04
  network namespace. Fail2ban reported v1.0.2; the synthetic JSON produced two
  expected matches and one expected 200 non-match; `fail2ban-client -t`
  passed; manual ban inserted only the TCP 80/443 `DOCKER-USER` jump and source
  DROP; no port-22 jump existed; manual unban and jail stop removed the ban and
  dedicated chain.
- `docker compose --env-file tests/fixtures/staging_security/staging-compose-test.env.example -f docker-compose.staging.yml build proxy`
  — Compose built the custom proxy image successfully.
- `make check` — passed: Ruff, migration check (`No changes detected`), 458
  tests, and 90.42% total coverage.
- `sh -n ops/staging_security/bootstrap_fail2ban.sh ops/validate_staging_abuse_protection.sh ops/validate_staging_fail2ban.sh`
  — passed.
- `git diff --check` — passed.

### Pre-commit threshold-isolation correction

`docker/staging/staging.env.example` now retains all six required rate-limit
variable names with empty values and an explicit requirement for measured,
approved operator values before a secured deploy. The previous strict
synthetic values now live only in
`tests/fixtures/staging_security/staging-compose-test.env.example`.

Passed delta validation:

- `docker compose --env-file tests/fixtures/staging_security/staging-compose-test.env.example -f docker-compose.staging.yml config --quiet`
  — Compose configuration valid with the dedicated synthetic fixture.
- `docker compose run --rm web pytest -q tests/ops/test_staging_security.py -o cache_dir=/tmp/school-newsroom-pytest-cache`
  — 8 passed, including the operator-template versus synthetic-fixture
  threshold contract.
- focused Ruff check and format check for `tests/ops/test_staging_security.py`
  — passed.
- `git diff --check` — passed.

`make check` was not rerun for this correction: no application or runtime
implementation changed, and the existing 458-test evidence remains applicable.

### PR follow-up corrections

The access-log filter now deletes the request `Referer` header in addition to
Authorization, Cookie, and Proxy-Authorization. This is logging sanitization
only: Caddy's request forwarding and the application's Referrer-Policy behavior
are unchanged. The executable Caddy harness submits a Referer containing the
fictional search value `fictional-referer-search-term` and fails if that value
or the Referer header appears in the resulting access log.

The original synthetic Compose fixture used the ignored `.env` filename. The
repository-wide `*.env` ignore rule therefore excluded it from the commit,
which caused a clean-checkout CI `FileNotFoundError`. It has been replaced with
the tracked `tests/fixtures/staging_security/staging-compose-test.env.example`;
the operator-facing `docker/staging/staging.env.example` remains uncalibrated
with its six required values empty.

Passed delta validation:

- `git check-ignore -v tests/fixtures/staging_security/staging-compose-test.env.example`
  — no matching ignore rule (exit status 1); `git add -n` confirms the fixture
  is stageable.
- `docker compose --env-file tests/fixtures/staging_security/staging-compose-test.env.example -f docker-compose.staging.yml config --quiet`
  — passed.
- `docker compose run --rm web pytest -q tests/ops/test_staging_security.py -o cache_dir=/tmp/school-newsroom-pytest-cache`
  — 8 passed.
- focused Ruff check and format check for `tests/ops/test_staging_security.py`
  — passed.
- `ops/validate_staging_abuse_protection.sh` — passed, including the submitted
  fictional Referer redaction check.
- `git diff --check` — passed.

The first expanded Caddy harness run failed because its test-only access log
was created `0640 root:root`, so the unprivileged host assertion could not read
it. The fixture alone now uses `0644`; the production Caddyfile remains `0640`
and is explicitly covered by contract tests and real Caddy validation. The
rerun passed. Fail2ban 1.0.2 emitted its packaged warning that missing global
`allowipv6` defaults to `auto`; configuration and IPv4 action tests still
passed, and the custom action contains the Fail2ban family-specific
`ip6tables` binding. Real IPv6 host behavior remains part of staging UAT when
IPv6 is publicly enabled.

## Stage B real staging validation

The real staging UAT passed at deployed SHA
`cceddcb6b35e17ddcd62bd5e983ad91036f9a21a`. Caddy reported `v2.11.4` with
`http.handlers.rate_limit`, and `proxy`, `web`, and `db` were healthy/running.
The calibrated policy was general `60/10s`, search `30/60s`, and login POST
`8/60s`.

Home and `/noticias/` returned 200, `/admin/` returned 302, and normal public
and Admin navigation caused no false positive or ban. Controlled excess and
recovery passed for all zones: general `60x200` then `10x429`; search `30x200`
then `5x429`, `Retry-After: 42`, then 200; login POST `8x403` then `2x429`,
`Retry-After: 49`, then 403 after recovery.

The access-log check observed `buscar=REDACTED` and confirmed that direct
`buscar`, Authorization, Cookie, Proxy-Authorization, and Referer search
markers were absent. Fail2ban `1.0.2-3ubuntu0.1` was installed, configuration
testing passed, and the service was active/running. The controlled automatic
ban test reached `Total failed: 49`, `Currently banned: 1`, and `Total banned:
1`; the TCP 80/443 `DOCKER-USER` jump to `f2b-sn-web`, controlled-source DROP,
and RETURN were present. SSH remained usable while HTTP/HTTPS timed out;
automatic expiry restored HTTP 200, current bans returned to zero, and total
bans remained one.

The maintainer reported PASS for manual ban/unban, the operational allowlist,
break-glass stop/restart, service/resource checks, public/private port and
Docker network boundary, IPv6 applicability, unchanged OCI inventory/shape,
and zero Actual/Forecast cost. No unsupplied numeric resource readings, IP
addresses, secrets, or private operational evidence are recorded.

## Stage B bootstrap follow-up

The deployed run found that the bootstrap's broad `grep 'CALIBRATE_'` matched
the explanatory template comment after all active values had been rendered,
creating a false rejection. The bootstrap now uses a POSIX `awk` check that
examines only active `findtime`, `maxretry`, `bantime`, and `ignoreip`
assignments, while the manual pre-check uses the same semantics.

The same run also exposed a Fail2ban socket race: `fail2ban-client -t` and
`systemctl restart` succeeded, but the immediate named-jail status call ran
before the client socket was ready. The bootstrap now retries readiness at
0.5-second intervals for fewer than ten seconds, fails closed with a clear
error on timeout, and still displays the named-jail status after readiness.
These are durable source fixes; this follow-up branch is not represented as
deployed.

### Stage B follow-up delta validation

- `docker compose run --rm web pytest -q tests/ops/test_staging_security.py -o cache_dir=/tmp/school-newsroom-pytest-cache`
  — 15 passed. The added bootstrap tests execute the actual script with stubbed
  host commands and cover the untouched template, each active unresolved
  placeholder, a rendered comment, retry readiness, and timeout failure.
- focused Ruff check and format check for `tests/ops/test_staging_security.py`
  — passed.
- `sh -n ops/staging_security/bootstrap_fail2ban.sh` — passed.
- `git diff --check` — passed.

`make check` was intentionally not rerun: this is a focused bootstrap,
regression-test, and documentation delta. Real staging UAT was not rerun and
no deployment was made by this follow-up branch.

## Deferred executable validation and UAT

No EPIC8-005 staging UAT remains deferred. The repository-only regression
checks cannot replace future staging verification after a materially changed
host, firewall, Caddy, or Fail2ban environment.

## Rollback and restart behavior

The runbook documents jail-specific stop, manual unban, full Fail2ban stop,
restoring the previous approved Caddyfile/custom-image definition, validating
before proxy recreate, and preserving the active SSH session. No rollback
touches SSH rules, product volumes, media, or database migrations.

Caddy limiter state survives configuration reloads according to the selected
module and resets on process/container restart. Fail2ban temporary ban state is
managed by its host service/database.

The Stage B break-glass stop/restart/validation flow passed and SSH remained
available. EPIC8-005 does not claim that an already-active temporary ban was
explicitly tested across a complete VM reboot; that scenario is not required to
keep this ticket open, and no EPIC8-005 acceptance UAT remains pending.

## Warnings and known issues

- Values supplied for local executable tests are intentionally strict and must
  never be copied to staging as if calibrated.
- The accepted `60/10s`, `30/60s`, and `8/60s` values are staging-specific and
  are not production policy.
- EPIC8-005 is not complete DDoS protection, a WAF, or production perimeter
  security.
- Future material changes to Docker, iptables-nft, UFW, Fail2ban, Caddy, public
  IPv6 exposure, or the host image require targeted operational revalidation.

## New Work Discovered

No new work is required to complete EPIC8-005. EPIC8-006 remains the owner for
production perimeter protection, provider-edge decisions, production
calibration, and any future WAF/CDN/bot-management work.

The EPIC6-002 evidence-preservation workflow did not require a new F009 artifact
in this pass. No reason was found to revise F004 or F006.

## Side effects and operational changes

The complete EPIC8-005 lifecycle intentionally produced these staging changes:

- deployed SHA `cceddcb6b35e17ddcd62bd5e983ad91036f9a21a`;
- installed the approved Ubuntu Noble Fail2ban package and its package
  dependencies on the existing staging VM;
- created the host-local Fail2ban configuration and access-log path;
- activated the EPIC8-005 named jail;
- deployed the custom Caddy image with `caddy-ratelimit`;
- retained the existing Oracle VM, shape, public exposure, Docker topology, and
  zero-cost footprint.

It did not create a new OCI resource, paid service, VM, load balancer, WAF,
database service, Redis service, public application port, Django migration, or
product persistence.

The final bootstrap-followup branch itself performs no staging deployment,
package installation, OCI mutation, or Planka operation. At the point
represented by this feedback, implementation and Stage B acceptance are
complete. Normal Git commit, push, pull-request review, merge, local `main`
synchronization, branch cleanup, and tracker closure are repository lifecycle
actions rather than additional EPIC8-005 implementation or UAT work.
