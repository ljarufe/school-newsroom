from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPOSE = ROOT / "docker-compose.staging.yml"
CADDYFILE = ROOT / "docker/staging/Caddyfile"
PROXY_DOCKERFILE = ROOT / "docker/staging/Caddy.Dockerfile"
STAGING_ENV_EXAMPLE = ROOT / "docker/staging/staging.env.example"
STAGING_TEST_ENV = (
    ROOT / "tests/fixtures/staging_security/staging-compose-test.env.example"
)
FILTER = ROOT / "ops/staging_security/fail2ban/filter.d/school-newsroom-caddy-429.conf"
ACTION = (
    ROOT / "ops/staging_security/fail2ban/action.d/school-newsroom-docker-user-web.conf"
)
JAIL_EXAMPLE = (
    ROOT / "ops/staging_security/fail2ban/jail.d/school-newsroom.local.example"
)


def test_custom_proxy_pins_caddy_and_rate_limit_module():
    compose = COMPOSE.read_text()
    dockerfile = PROXY_DOCKERFILE.read_text()

    assert "dockerfile: docker/staging/Caddy.Dockerfile" in compose
    assert "school-newsroom-staging-proxy:2.11.4-ratelimit-v0.1.0" in compose
    assert dockerfile.count("caddy:2.11.4-") == 2
    assert dockerfile.count("@sha256:") == 2
    assert "xcaddy build v2.11.4" in dockerfile
    assert "github.com/mholt/caddy-ratelimit@v0.1.0" in dockerfile


def test_compose_keeps_only_proxy_ports_public_and_private_services_private():
    compose = COMPOSE.read_text()
    proxy, web_and_db = compose.split("  web:", 1)

    assert '      - "80:80"' in proxy
    assert '      - "443:443"' in proxy
    assert "    ports:" not in web_and_db
    assert '      - "8000"' in web_and_db
    assert '      - "5432"' not in compose
    assert "internal: true" in compose


def test_caddy_rate_limit_scopes_use_network_peer_and_preserve_media():
    caddyfile = CADDYFILE.read_text()

    assert caddyfile.index("handle @media") < caddyfile.index("rate_limit {")
    assert "zone general_dynamic" in caddyfile
    assert "zone news_search" in caddyfile
    assert "zone wagtail_login_post" in caddyfile
    assert caddyfile.count("key {remote_host}") == 3
    assert "client_ip" not in caddyfile
    assert "trusted_proxies" not in caddyfile
    assert "path /noticias/" in caddyfile
    assert "query buscar=*" in caddyfile
    assert "method POST" in caddyfile
    assert "path /admin/login/" in caddyfile
    assert "reverse_proxy web:8000" in caddyfile


def test_rate_limit_thresholds_are_required_operational_inputs():
    compose = COMPOSE.read_text()
    example = STAGING_ENV_EXAMPLE.read_text()
    test_environment = STAGING_TEST_ENV.read_text()
    names = (
        "CADDY_RATE_LIMIT_GENERAL_EVENTS",
        "CADDY_RATE_LIMIT_GENERAL_WINDOW",
        "CADDY_RATE_LIMIT_SEARCH_EVENTS",
        "CADDY_RATE_LIMIT_SEARCH_WINDOW",
        "CADDY_RATE_LIMIT_LOGIN_EVENTS",
        "CADDY_RATE_LIMIT_LOGIN_WINDOW",
    )

    expected_test_values = {
        "CADDY_RATE_LIMIT_GENERAL_EVENTS": "20",
        "CADDY_RATE_LIMIT_GENERAL_WINDOW": "10s",
        "CADDY_RATE_LIMIT_SEARCH_EVENTS": "3",
        "CADDY_RATE_LIMIT_SEARCH_WINDOW": "10s",
        "CADDY_RATE_LIMIT_LOGIN_EVENTS": "2",
        "CADDY_RATE_LIMIT_LOGIN_WINDOW": "10s",
    }

    for name in names:
        assert f"${{{name}:?" in compose
        assert f"{name}=\n" in example
        assert f"{name}={expected_test_values[name]}" in test_environment
    assert "REQUIRED BEFORE SECURED DEPLOY" in example
    assert "Synthetic repository-test values only" in test_environment


def test_access_log_is_bounded_and_redacts_sensitive_values():
    compose = COMPOSE.read_text()
    caddyfile = CADDYFILE.read_text()

    assert "/var/log/school-newsroom/caddy:/var/log/caddy" in compose
    assert "output file /var/log/caddy/access.json" in caddyfile
    assert "roll_size 10MiB" in caddyfile
    assert "roll_keep 3" in caddyfile
    assert "roll_keep_for 72h" in caddyfile
    assert "replace buscar REDACTED" in caddyfile
    assert "request>headers>Authorization delete" in caddyfile
    assert "request>headers>Cookie delete" in caddyfile
    assert "request>headers>Proxy-Authorization delete" in caddyfile
    assert "request>headers>Referer delete" in caddyfile


def test_fail2ban_contract_matches_429_and_never_targets_ssh_or_input():
    filter_text = FILTER.read_text()
    action_text = ACTION.read_text()
    jail_text = JAIL_EXAMPLE.read_text()

    assert '"remote_ip":"<ADDR>"' in filter_text
    assert '"status":429' in filter_text
    assert "DOCKER-USER" in action_text
    assert "--dports 80,443" in action_text
    assert "actionban" in action_text
    assert "actionunban" in action_text
    assert "SSH" not in action_text.upper()
    assert "INPUT" not in action_text
    assert "CALIBRATE_FINDTIME" in jail_text
    assert "CALIBRATE_MAXRETRY" in jail_text
    assert "CALIBRATE_BANTIME" in jail_text
    assert "CALIBRATE_OPERATIONAL_ALLOWLIST" in jail_text
    assert "/var/log/school-newsroom/caddy/access.json" in jail_text


def test_versioned_allowlist_has_no_personal_address():
    jail_text = JAIL_EXAMPLE.read_text()

    assert "ignoreip = 127.0.0.1/8 ::1 CALIBRATE_OPERATIONAL_ALLOWLIST" in jail_text
    assert "192.168." not in jail_text
    assert "10.0." not in jail_text


def test_host_bootstrap_is_explicit_and_outside_application_startup():
    bootstrap = (ROOT / "ops/staging_security/bootstrap_fail2ban.sh").read_text()
    compose = COMPOSE.read_text()
    web_start = (ROOT / "docker/staging/start-web.sh").read_text()

    assert "apt-get install --yes fail2ban" in bootstrap
    assert "CALIBRATE_" in bootstrap
    assert "fail2ban-client -t" in bootstrap
    assert "status school-newsroom-caddy-429" in bootstrap
    assert "apt-get" not in compose
    assert "fail2ban" not in web_start.lower()
