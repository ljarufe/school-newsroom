# EPIC8-005 Feedback

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
leaves it empty, so an operator must supply measured, approved staging values
before a secured deploy. Synthetic executable values exist only in
`tests/fixtures/staging_security/staging-compose-test.env.example`; they are not
calibrated staging values.

Fail2ban `findtime`, repeated-429 `maxretry`, `bantime`, and the operational
`ignoreip` list are host-local. The versioned jail template contains deliberate
`CALIBRATE_*` tokens, so it cannot be activated accidentally. No personal
maintainer IP/CIDR is committed.

Final staging values remain pending measured normal-navigation calibration and
controlled real UAT. No threshold is represented as production-ready.

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

## Manual validation

No manual staging, browser, host firewall, ban/unban, resource, or OCI cost
validation was performed during this implementation pass.

## Deferred executable validation and UAT

Real staging work remains explicitly deferred to the maintainer:

- select calibrated general/search/login and Fail2ban values;
- run the one-time Fail2ban host bootstrap;
- deploy an approved SHA;
- execute the complete EPIC8-005 section in `oracle_staging_uat.md`;
- prove normal navigation has no false positives;
- prove controlled 429, `Retry-After`, recovery, automatic/manual ban/unban,
  allowlist, and SSH continuity;
- inspect bounded logs and VM CPU/RAM on 1 OCPU/4 GB;
- confirm public/private ports, health, no restart loop, unchanged OCI
  inventory/shape, and zero Actual/Forecast cost.

No CPU/RAM observation or real Oracle result is claimed here.

## Rollback and restart behavior

The runbook documents jail-specific stop, manual unban, full Fail2ban stop,
restoring the previous approved Caddyfile/custom-image definition, validating
before proxy recreate, and preserving the active SSH session. No rollback
touches SSH rules, product volumes, media, or database migrations.

Caddy limiter state survives configuration reloads according to the selected
module and resets on process/container restart. Fail2ban temporary ban state is
managed by its host service/database; real restart behavior remains a staging
UAT item.

## Warnings and known issues

- Values supplied for local executable tests are intentionally strict and must
  never be copied to staging as if calibrated.
- EPIC8-005 is not complete DDoS protection, a WAF, or production perimeter
  security.
- Real host behavior across Docker, iptables-nft, UFW, and Fail2ban cannot be
  accepted from repository tests alone.

## New Work Discovered

No new product or infrastructure work was discovered during implementation.
EPIC8-006 remains the owner for production perimeter protection, provider-edge
decisions, production calibration, and any future WAF/CDN/bot-management work.

The EPIC6-002 evidence-preservation workflow did not require a new F009 artifact
in this pass. No reason was found to revise F004 or F006. Reconsider F009 only
if executable security validation exposes recurring teardown/evidence loss.

## Side effects

No commit, push, pull request, merge, staging deployment, host package install,
OCI mutation, or Planka change was performed.
