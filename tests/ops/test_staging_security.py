import os
import subprocess
import tempfile
from pathlib import Path

import pytest

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
BOOTSTRAP = ROOT / "ops/staging_security/bootstrap_fail2ban.sh"


def _rendered_jail():
    return (
        JAIL_EXAMPLE.read_text()
        .replace("CALIBRATE_FINDTIME", "10m")
        .replace("CALIBRATE_MAXRETRY", "5")
        .replace("CALIBRATE_BANTIME", "1h")
        .replace("CALIBRATE_OPERATIONAL_ALLOWLIST", "198.51.100.0/24")
    )


def _write_stub(command_directory, name, content):
    path = command_directory / name
    path.write_text(content)
    path.chmod(0o755)


def _run_bootstrap(jail_content, status_failures=0):
    with tempfile.TemporaryDirectory() as temporary_directory:
        temporary_path = Path(temporary_directory)
        command_directory = temporary_path / "bin"
        command_directory.mkdir()
        jail_path = temporary_path / "rendered.local"
        status_count_path = temporary_path / "status-count"
        sleep_log_path = temporary_path / "sleeps"
        jail_path.write_text(jail_content)

        _write_stub(command_directory, "id", "#!/bin/sh\necho 0\n")
        for name in (
            "apt-get",
            "iptables",
            "install",
            "touch",
            "chown",
            "chmod",
            "systemctl",
        ):
            _write_stub(command_directory, name, "#!/bin/sh\nexit 0\n")
        _write_stub(
            command_directory,
            "fail2ban-client",
            """#!/bin/sh
case "$1" in
    --version)
        echo "Fail2Ban v1.0.2"
        ;;
    -t)
        exit 0
        ;;
    status)
        status_count=0
        if [ -f "$FAKE_STATUS_COUNT" ]; then
            status_count=$(cat "$FAKE_STATUS_COUNT")
        fi
        status_count=$((status_count + 1))
        printf '%s\\n' "$status_count" > "$FAKE_STATUS_COUNT"
        if [ "$status_count" -le "$FAKE_STATUS_FAILURES" ]; then
            exit 1
        fi
        echo "Status for the jail: $2"
        ;;
esac
""",
        )
        _write_stub(
            command_directory,
            "sleep",
            '#!/bin/sh\nprintf \'sleep %s\\n\' "$1" >> "$FAKE_SLEEP_LOG"\n',
        )

        environment = {
            **os.environ,
            "PATH": f"{command_directory}:{os.environ['PATH']}",
            "FAKE_STATUS_COUNT": str(status_count_path),
            "FAKE_STATUS_FAILURES": str(status_failures),
            "FAKE_SLEEP_LOG": str(sleep_log_path),
        }
        result = subprocess.run(
            ["sh", str(BOOTSTRAP), str(jail_path)],
            check=False,
            capture_output=True,
            env=environment,
            text=True,
        )
        status_calls = (
            int(status_count_path.read_text()) if status_count_path.exists() else 0
        )
        sleep_calls = (
            sleep_log_path.read_text().splitlines() if sleep_log_path.exists() else []
        )
        return result, status_calls, sleep_calls


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
    bootstrap = BOOTSTRAP.read_text()
    compose = COMPOSE.read_text()
    web_start = (ROOT / "docker/staging/start-web.sh").read_text()

    assert "apt-get install --yes fail2ban" in bootstrap
    assert "CALIBRATE_" in bootstrap
    assert "fail2ban-client -t" in bootstrap
    assert "status school-newsroom-caddy-429" in bootstrap
    assert "apt-get" not in compose
    assert "fail2ban" not in web_start.lower()


def test_bootstrap_rejects_untouched_jail_template():
    result, status_calls, sleep_calls = _run_bootstrap(JAIL_EXAMPLE.read_text())

    assert result.returncode == 1
    assert "Replace every active CALIBRATE_* value" in result.stderr
    assert status_calls == 0
    assert sleep_calls == []


def test_bootstrap_accepts_rendered_jail_with_calibration_comment():
    rendered_jail = _rendered_jail().replace(
        "ignoreip = 127.0.0.1/8 ::1 198.51.100.0/24",
        "ignoreip = 127.0.0.1/8 ::1\n    198.51.100.0/24",
    )
    result, status_calls, sleep_calls = _run_bootstrap(rendered_jail, status_failures=2)

    assert "# CALIBRATE_* tokens intentionally" in rendered_jail
    assert "\n    198.51.100.0/24" in rendered_jail
    assert result.returncode == 0
    assert "Status for the jail: school-newsroom-caddy-429" in result.stdout
    assert status_calls == 4
    assert sleep_calls == ["sleep 0.5", "sleep 0.5"]


@pytest.mark.parametrize(
    "placeholder",
    (
        "CALIBRATE_FINDTIME",
        "CALIBRATE_MAXRETRY",
        "CALIBRATE_BANTIME",
        "CALIBRATE_OPERATIONAL_ALLOWLIST",
    ),
)
def test_bootstrap_rejects_each_unresolved_active_calibration_placeholder(placeholder):
    rendered_jail = _rendered_jail().replace(
        {
            "CALIBRATE_FINDTIME": "10m",
            "CALIBRATE_MAXRETRY": "5",
            "CALIBRATE_BANTIME": "1h",
            "CALIBRATE_OPERATIONAL_ALLOWLIST": "198.51.100.0/24",
        }[placeholder],
        placeholder,
    )
    result, status_calls, sleep_calls = _run_bootstrap(rendered_jail)

    assert result.returncode == 1
    assert "Replace every active CALIBRATE_* value" in result.stderr
    assert status_calls == 0
    assert sleep_calls == []


def test_bootstrap_rejects_unresolved_ignoreip_continuation():
    rendered_jail = _rendered_jail().replace(
        "ignoreip = 127.0.0.1/8 ::1 198.51.100.0/24",
        "ignoreip = 127.0.0.1/8 ::1\n    CALIBRATE_OPERATIONAL_ALLOWLIST",
    )
    result, status_calls, sleep_calls = _run_bootstrap(rendered_jail)

    assert result.returncode == 1
    assert "Replace every active CALIBRATE_* value" in result.stderr
    assert status_calls == 0
    assert sleep_calls == []


def test_bootstrap_readiness_timeout_fails_closed():
    result, status_calls, sleep_calls = _run_bootstrap(
        _rendered_jail(), status_failures=20
    )

    assert result.returncode == 1
    assert "Fail2ban did not become ready within 10 seconds." in result.stderr
    assert status_calls == 20
    assert sleep_calls == ["sleep 0.5"] * 19
