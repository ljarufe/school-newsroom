from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from ops.staging_deploy import (
    COMPOSE_FILE,
    CURRENT_DEPLOYMENT,
    DEPLOYMENT_HISTORY,
    EXPECTED_ORIGINS,
    REMOTE_REPOSITORY,
    STAGING_ALIAS,
    STAGING_ENV,
    CommandResult,
    DeploymentError,
    StagingDeployer,
    validate_command_contracts,
)

TARGET = "f" * 40
PREVIOUS = "a" * 40
HOSTNAME = "school-newsroom.duckdns.org"


class FakeLocal:
    def __init__(self, root: Path, *, target: str = TARGET, ancestor: bool = True):
        self.root = root
        self.target = target
        self.ancestor = ancestor
        self.calls: list[tuple[str, ...]] = []

    def run(self, args, *, cwd=None, timeout=None):
        args = tuple(args)
        self.calls.append(args)
        if args == ("git", "rev-parse", "--show-toplevel"):
            return CommandResult("", f"{self.root}\n")
        if args == ("git", "remote", "get-url", "origin"):
            return CommandResult("", f"{next(iter(EXPECTED_ORIGINS))}\n")
        if args == ("ssh", "-G", STAGING_ALIAS):
            return CommandResult(
                "",
                "hostname school-newsroom.duckdns.org\n"
                "user ubuntu\nport 22\n"
                "identityfile ~/.ssh/school_newsroom_oracle_staging\n",
            )
        if args == ("git", "fetch", "origin", "main"):
            return CommandResult("")
        if args[:3] == ("git", "rev-parse", "--verify"):
            return CommandResult("", f"{self.target}\n")
        if args[:3] == ("git", "merge-base", "--is-ancestor"):
            return CommandResult("", exited=0 if self.ancestor else 1)
        raise AssertionError(f"Unexpected local command: {args}")


class FakeSmoke:
    def __init__(self, *, fail: bool = False):
        self.fail = fail
        self.hostnames: list[str] = []

    def check(self, hostname: str):
        self.hostnames.append(hostname)
        if self.fail:
            raise RuntimeError("smoke failed")


class FakeClock:
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        self.value += 1.0
        return self.value


class FakeRemote:
    def __init__(
        self,
        *,
        previous: str = PREVIOUS,
        fail_contains: str | None = None,
        raise_contains: str | None = None,
        dirty: bool = False,
        lock_busy: bool = False,
        health: bool = True,
        sudo_ok: bool = True,
    ):
        self.previous = previous
        self.fail_contains = fail_contains
        self.raise_contains = raise_contains
        self.dirty = dirty
        self.lock_busy = lock_busy
        self.health = health
        self.sudo_ok = sudo_ok
        self.calls: list[str] = []
        self.closed = False

    def run(self, command: str, *, timeout=None):
        self.calls.append(command)
        if self.raise_contains and self.raise_contains in command:
            raise OSError("simulated transport failure")
        if self.fail_contains and self.fail_contains in command:
            return CommandResult(command, exited=1)
        if command == "sudo -n true" and not self.sudo_ok:
            return CommandResult(command, exited=1)
        if command.startswith("sudo -n test ! -e") and self.lock_busy:
            return CommandResult(command, exited=1)
        if "git remote get-url origin" in command:
            return CommandResult(command, f"{next(iter(EXPECTED_ORIGINS))}\n")
        if "git status --porcelain" in command:
            return CommandResult(command, "?? unexpected\n" if self.dirty else "")
        if "git rev-parse HEAD" in command:
            checked_out = any(
                f"git checkout --detach {TARGET}" in call for call in self.calls
            )
            head = TARGET if checked_out else self.previous
            return CommandResult(command, f"{head}\n")
        if "df -Pk" in command:
            return CommandResult(command, "44112584\n")
        if "sed -n 's/^STAGING_HOSTNAME=" in command:
            return CommandResult(command, f"{HOSTNAME}\n")
        if "ps --services --filter status=running" in command:
            return CommandResult(command, "db\nproxy\nweb\n")
        if "ps -q db" in command:
            return CommandResult(command, "db-id\n")
        if "ps -q web" in command:
            return CommandResult(command, "web-id\n")
        if "ps -q proxy" in command:
            return CommandResult(command, "proxy-id\n")
        if "docker inspect" in command:
            if not self.health:
                return CommandResult(command, "starting\n")
            if "proxy-id" in command:
                return CommandResult(command, "running\n")
            return CommandResult(command, "healthy\n")
        if "exec -T proxy caddy version" in command and not self.health:
            return CommandResult(command, exited=1)
        return CommandResult(command)

    def close(self):
        self.closed = True


def make_deployer(tmp_path, remote=None, smoke=None, output=None, **kwargs):
    remote = remote or FakeRemote()
    smoke = smoke or FakeSmoke()
    output = output if output is not None else []
    deployer = StagingDeployer(
        local=FakeLocal(tmp_path),
        remote=remote,
        smoke=smoke,
        output=output.append,
        clock=FakeClock(),
        sleep=lambda _: None,
        now=lambda: datetime(2026, 8, 5, 22, 0, tzinfo=UTC),
        repository_root=tmp_path,
        health_timeout=kwargs.pop("health_timeout", 2),
        health_poll=0,
        **kwargs,
    )
    return deployer, remote, smoke, output


def test_default_sha_uses_origin_main(tmp_path):
    deployer, _, _, _ = make_deployer(tmp_path, remote=FakeRemote(previous=TARGET))
    result = deployer.deploy()
    assert result.already_deployed is True
    assert (
        "git",
        "rev-parse",
        "--verify",
        "origin/main^{commit}",
    ) in deployer.local.calls


def test_optional_sha_is_resolved_as_commit_and_checked_against_main(tmp_path):
    deployer, _, _, _ = make_deployer(tmp_path, remote=FakeRemote(previous=TARGET))
    deployer.deploy("abc123")
    assert ("git", "rev-parse", "--verify", "abc123^{commit}") in deployer.local.calls
    assert (
        "git",
        "merge-base",
        "--is-ancestor",
        TARGET,
        "origin/main",
    ) in deployer.local.calls


def test_optional_sha_outside_main_fails_before_remote_use(tmp_path):
    remote = FakeRemote()
    deployer, _, _, output = make_deployer(tmp_path, remote=remote)
    deployer.local.ancestor = False
    with pytest.raises(DeploymentError) as captured:
        deployer.deploy("abc123")
    assert captured.value.code == "target_not_in_origin_main"
    assert remote.calls == []
    assert remote.closed is True
    assert "Deployment failed" in output


def test_missing_alias_fails_local_preflight(tmp_path):
    remote = FakeRemote()
    deployer, _, _, _ = make_deployer(tmp_path, remote=remote)
    original = deployer.local.run

    def run(args, **kwargs):
        if tuple(args) == ("ssh", "-G", STAGING_ALIAS):
            return CommandResult("", exited=1)
        return original(args, **kwargs)

    deployer.local.run = run
    with pytest.raises(DeploymentError) as captured:
        deployer.deploy()
    assert captured.value.code == "ssh_alias_missing"
    assert remote.calls == []


def test_ssh_connection_failure_is_classified_before_sudo_or_mutation(tmp_path):
    remote = FakeRemote(raise_contains="true")
    deployer, _, _, _ = make_deployer(tmp_path, remote=remote)
    with pytest.raises(DeploymentError) as captured:
        deployer.deploy()
    assert captured.value.code == "ssh_connection_failed"
    assert remote.calls == ["true"]
    assert not any("sudo -n true" in call for call in remote.calls)
    assert not any("git checkout --detach" in call for call in remote.calls)
    assert remote.closed is True


@pytest.mark.parametrize(
    ("remote", "code"),
    [
        (FakeRemote(sudo_ok=False), "sudo_n_failed"),
        (FakeRemote(dirty=True), "remote_checkout_dirty"),
        (FakeRemote(lock_busy=True), "deployment_already_running"),
    ],
)
def test_remote_preflight_failures_do_not_mutate(tmp_path, remote, code):
    deployer, _, _, _ = make_deployer(tmp_path, remote=remote)
    with pytest.raises(DeploymentError) as captured:
        deployer.deploy()
    assert captured.value.code == code
    assert not any("git checkout --detach" in call for call in remote.calls)
    assert not any("build web" in call for call in remote.calls)
    assert remote.closed is True


def test_already_deployed_is_noop_and_releases_lock(tmp_path):
    deployer, remote, smoke, output = make_deployer(
        tmp_path, remote=FakeRemote(previous=TARGET)
    )
    result = deployer.deploy()
    joined = "\n".join(remote.calls)
    assert result.already_deployed is True
    assert "build web" not in joined
    assert "migrate --noinput" not in joined
    assert "up -d" not in joined
    assert DEPLOYMENT_HISTORY not in joined
    assert "rmdir" in joined
    assert smoke.hostnames == []
    assert "already_deployed" in output
    assert remote.closed is True


def test_successful_deploy_runs_ordered_stages_and_records_success(tmp_path):
    deployer, remote, smoke, output = make_deployer(tmp_path)
    result = deployer.deploy()
    joined = "\n".join(remote.calls)
    assert result.target_sha == TARGET
    assert smoke.hostnames == [HOSTNAME]
    assert joined.index("git checkout --detach") < joined.index("build web")
    assert joined.index("build web") < joined.index("migrate --noinput")
    assert joined.index("migrate --noinput") < joined.index("bootstrap_mvp_access")
    assert joined.index("bootstrap_mvp_access") < joined.index("up -d")
    assert CURRENT_DEPLOYMENT in joined
    assert DEPLOYMENT_HISTORY in joined
    assert '"result":"success"' in joined
    assert "Deployment succeeded" in output
    assert remote.closed is True


@pytest.mark.parametrize(
    ("needle", "code", "service_changed"),
    [
        ("build web", "build_failed", "no"),
        ("migrate --noinput", "migration_failed", "no"),
        ("bootstrap_mvp_access", "bootstrap_failed", "no"),
        ("Default Wagtail Site", "site_reconciliation_failed", "no"),
        ("up -d", "recreate_failed", "unknown"),
    ],
)
def test_stage_failures_stop_and_record(tmp_path, needle, code, service_changed):
    remote = FakeRemote(fail_contains=needle)
    deployer, _, _, _ = make_deployer(tmp_path, remote=remote)
    with pytest.raises(DeploymentError) as captured:
        deployer.deploy()
    assert captured.value.code == code
    assert captured.value.service_changed == service_changed
    assert code in "\n".join(remote.calls)
    assert remote.closed is True


def test_transport_exception_during_build_keeps_build_stage_classification(tmp_path):
    remote = FakeRemote(raise_contains="build web")
    deployer, _, _, _ = make_deployer(tmp_path, remote=remote)
    with pytest.raises(DeploymentError) as captured:
        deployer.deploy()
    assert captured.value.code == "build_failed"
    assert captured.value.stage == "build"
    assert captured.value.service_changed == "no"
    assert any(f"git checkout --detach {PREVIOUS}" in call for call in remote.calls)
    assert remote.closed is True


def test_health_timeout_uses_bounded_logs_and_does_not_rollback(tmp_path):
    remote = FakeRemote(health=False)
    deployer, _, _, _ = make_deployer(tmp_path, remote=remote, health_timeout=1)
    with pytest.raises(DeploymentError) as captured:
        deployer.deploy()
    joined = "\n".join(remote.calls)
    assert captured.value.code == "health_timeout"
    assert "logs --tail=100 proxy" in joined
    assert "logs --tail=100 web" in joined
    assert "logs --tail=100 db" in joined
    target_checkout = joined.rfind(f"git checkout --detach {TARGET}")
    previous_checkout = joined.rfind(f"git checkout --detach {PREVIOUS}")
    assert previous_checkout < target_checkout


def test_smoke_failure_never_updates_current_record(tmp_path):
    remote = FakeRemote()
    deployer, _, _, _ = make_deployer(
        tmp_path, remote=remote, smoke=FakeSmoke(fail=True)
    )
    with pytest.raises(DeploymentError) as captured:
        deployer.deploy()
    joined = "\n".join(remote.calls)
    assert captured.value.code == "https_smoke_failed"
    assert CURRENT_DEPLOYMENT not in joined
    assert "https_smoke_failed" in joined


def test_output_and_commands_do_not_include_sensitive_environment_values(tmp_path):
    deployer, remote, _, output = make_deployer(tmp_path)
    deployer.deploy()
    text = "\n".join(output + remote.calls)
    assert "DJANGO_SECRET_KEY" not in text
    assert "POSTGRES_PASSWORD" not in text
    assert "DATABASE_URL=" not in text
    assert "printenv" not in text
    assert "docker compose" in text
    assert "config --quiet" in text


def test_command_contracts_use_safe_paths_and_no_destructive_commands():
    commands = "\n".join(validate_command_contracts())
    assert f"--env-file {STAGING_ENV}" in commands
    assert f"-f {COMPOSE_FILE}" in commands
    assert REMOTE_REPOSITORY in commands
    assert "migrate --noinput" in commands
    assert "checkout --detach" in commands
    assert "logs --tail=100" in commands
    for forbidden in (
        "down -v",
        "volume rm",
        "system prune",
        "git clean",
        "read ",
        "input(",
        "getpass",
    ):
        assert forbidden not in commands


def test_repository_contract_files_keep_fabric_local_and_prompt_once():
    makefile = Path("Makefile").read_text()
    requirements = Path("requirements-ops.txt").read_text()
    runtime_requirements = Path("requirements.txt")
    assert requirements == "fabric==3.2.3\n"
    assert "--prompt-for-passphrase" in makefile
    assert ".venv-ops" in makefile
    if runtime_requirements.exists():
        assert "fabric" not in runtime_requirements.read_text().lower()
