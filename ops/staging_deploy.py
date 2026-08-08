"""Testable orchestration for deploying an approved SHA to staging."""

from __future__ import annotations

import http.client
import json
import os
import re
import shlex
import ssl
import subprocess
import time
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

STAGING_ALIAS = "school-newsroom-staging"
REMOTE_REPOSITORY = "/opt/school-newsroom"
COMPOSE_FILE = "docker-compose.staging.yml"
STAGING_ENV = "/etc/school-newsroom/staging.env"
MEDIA_DIRECTORY = "/srv/school-newsroom/media"
DEPLOYMENTS_DIRECTORY = "/var/lib/school-newsroom/deployments"
CURRENT_DEPLOYMENT = f"{DEPLOYMENTS_DIRECTORY}/current.json"
DEPLOYMENT_HISTORY = f"{DEPLOYMENTS_DIRECTORY}/history.jsonl"
LOCK_DIRECTORY = "/var/lock/school-newsroom-staging-deploy.lock"
EXPECTED_ORIGINS = frozenset(
    {
        "https://github.com/ljarufe/school-newsroom.git",
        "git@github.com:ljarufe/school-newsroom.git",
        "ssh://git@github.com/ljarufe/school-newsroom.git",
    }
)
MIN_FREE_KB = 5 * 1024 * 1024
HEALTH_TIMEOUT_SECONDS = 180
HEALTH_POLL_SECONDS = 5
COMMAND_TIMEOUT_SECONDS = 900
LOG_TAIL_LINES = 100
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class CommandResult:
    """Small command result shared by local and remote adapters."""

    command: str
    stdout: str = ""
    stderr: str = ""
    exited: int = 0

    @property
    def ok(self) -> bool:
        return self.exited == 0


class LocalRunner(Protocol):
    """Execute a local command without opening an interactive shell."""

    def run(
        self,
        args: Sequence[str],
        *,
        cwd: Path | None = None,
        timeout: int | None = None,
    ) -> CommandResult: ...


class RemoteRunner(Protocol):
    """Execute commands through one already-configured SSH connection."""

    def run(
        self,
        command: str,
        *,
        timeout: int | None = None,
    ) -> CommandResult: ...

    def close(self) -> None: ...


class ExceptionSafeRemoteRunner:
    """Convert transport exceptions into safe command failures."""

    def __init__(self, runner: RemoteRunner) -> None:
        self.runner = runner

    def run(
        self,
        command: str,
        *,
        timeout: int | None = None,
    ) -> CommandResult:
        try:
            return self.runner.run(command, timeout=timeout)
        except Exception:
            return CommandResult(
                command=command,
                stderr="remote_transport_error",
                exited=255,
            )

    def close(self) -> None:
        try:
            self.runner.close()
        except Exception:
            pass


class SmokeProbe(Protocol):
    """Validate public HTTP and HTTPS behavior."""

    def check(self, hostname: str) -> None: ...


class SubprocessLocalRunner:
    """Local runner using argv-only subprocess execution."""

    def run(
        self,
        args: Sequence[str],
        *,
        cwd: Path | None = None,
        timeout: int | None = None,
    ) -> CommandResult:
        environment = os.environ.copy()
        environment["GIT_TERMINAL_PROMPT"] = "0"
        completed = subprocess.run(
            list(args),
            cwd=cwd,
            capture_output=True,
            check=False,
            text=True,
            timeout=timeout,
            env=environment,
        )
        return CommandResult(
            command=shlex.join(args),
            stdout=completed.stdout,
            stderr=completed.stderr,
            exited=completed.returncode,
        )


class StandardLibrarySmokeProbe:
    """Public smoke checks with certificate and hostname validation enabled."""

    def __init__(self, *, timeout: int = 15) -> None:
        self.timeout = timeout

    def check(self, hostname: str) -> None:
        self._check_http_redirect(hostname)
        self._check_https_path(hostname, "/", {200})
        self._check_https_path(hostname, "/noticias/", {200})
        self._check_https_path(hostname, "/admin/", {301, 302, 303, 307, 308})

    def _check_http_redirect(self, hostname: str) -> None:
        connection = http.client.HTTPConnection(hostname, 80, timeout=self.timeout)
        try:
            connection.request("HEAD", "/")
            response = connection.getresponse()
            location = response.getheader("Location", "")
            response.read()
        finally:
            connection.close()
        if response.status not in {301, 302, 303, 307, 308}:
            raise SmokeCheckError("http_redirect_status")
        if not location.startswith(f"https://{hostname}"):
            raise SmokeCheckError("http_redirect_target")

    def _check_https_path(
        self,
        hostname: str,
        path: str,
        expected_statuses: set[int],
    ) -> None:
        context = ssl.create_default_context()
        connection = http.client.HTTPSConnection(
            hostname,
            443,
            timeout=self.timeout,
            context=context,
        )
        try:
            connection.request("HEAD", path)
            response = connection.getresponse()
            response.read()
        finally:
            connection.close()
        if response.status not in expected_statuses:
            raise SmokeCheckError(f"https_status_{path}_{response.status}")


class SmokeCheckError(RuntimeError):
    """Public smoke failed without exposing response content."""


@dataclass
class DeploymentError(RuntimeError):
    """Stable deployment failure suitable for safe operator output."""

    stage: str
    code: str
    next_action: str
    previous_sha: str = "unknown"
    target_sha: str = "unknown"
    service_changed: str = "no"

    def __post_init__(self) -> None:
        RuntimeError.__init__(self, self.code)


@dataclass(frozen=True)
class DeploymentResult:
    """Successful deployment result."""

    previous_sha: str
    target_sha: str
    remote_head: str
    already_deployed: bool
    duration_seconds: int


@dataclass(frozen=True)
class RemotePreflight:
    """Safe values collected before any remote mutation."""

    previous_sha: str
    hostname: str
    running_services: tuple[str, ...]


class StagingDeployer:
    """Orchestrate one deploy while keeping transport details replaceable."""

    def __init__(
        self,
        *,
        local: LocalRunner,
        remote: RemoteRunner,
        smoke: SmokeProbe,
        output: Callable[[str], None] = print,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
        repository_root: Path | None = None,
        health_timeout: int = HEALTH_TIMEOUT_SECONDS,
        health_poll: int = HEALTH_POLL_SECONDS,
    ) -> None:
        self.local = local
        self.remote = ExceptionSafeRemoteRunner(remote)
        self.smoke = smoke
        self.output = output
        self.clock = clock
        self.sleep = sleep
        self.now = now
        self.repository_root = repository_root or Path.cwd()
        self.health_timeout = health_timeout
        self.health_poll = health_poll
        self.previous_sha = "unknown"
        self.target_sha = "unknown"
        self.service_changed = "no"
        self.lock_token: str | None = None

    def deploy(self, requested_sha: str | None = None) -> DeploymentResult:
        started = self.clock()
        try:
            self._stage("local_preflight")
            self.target_sha = self._local_preflight(requested_sha)

            self._stage("remote_preflight")
            preflight = self._remote_preflight()
            self.previous_sha = preflight.previous_sha

            self._stage("lock")
            self._acquire_lock()

            if (
                self.previous_sha == self.target_sha
                and self._last_successful_deployment_matches_target()
            ):
                duration = max(0, round(self.clock() - started))
                self.output("already_deployed")
                self._print_success(
                    remote_head=self.previous_sha,
                    duration=duration,
                    already_deployed=True,
                )
                return DeploymentResult(
                    previous_sha=self.previous_sha,
                    target_sha=self.target_sha,
                    remote_head=self.previous_sha,
                    already_deployed=True,
                    duration_seconds=duration,
                )

            self._record_started()

            self._stage("checkout")
            self._checkout_target()

            self._stage("build")
            self._run_before_recreate(
                command=self._compose("build web"),
                failure_code="build_failed",
                next_action=(
                    "Inspect the bounded build output and retry after correction."
                ),
            )

            self._stage("migrations")
            self._run_before_recreate(
                command=self._compose(
                    "run --rm web python manage.py migrate --noinput"
                ),
                failure_code="migration_failed",
                next_action=(
                    "Inspect migration state before retrying; an applied migration "
                    "is not rolled back automatically."
                ),
            )

            self._stage("bootstrap")
            self._run_before_recreate(
                command=self._compose(
                    "run --rm web python manage.py bootstrap_mvp_access"
                ),
                failure_code="bootstrap_failed",
                next_action="Inspect bootstrap output before retrying.",
            )

            self._stage("wagtail_site")
            self._run_before_recreate(
                command=self._site_reconciliation_command(),
                failure_code="site_reconciliation_failed",
                next_action="Inspect the default Wagtail Site before retrying.",
            )

            self._stage("recreate")
            recreate = self.remote.run(
                self._compose("up -d"), timeout=COMMAND_TIMEOUT_SECONDS
            )
            if not recreate.ok:
                self.service_changed = "unknown"
                self._print_bounded_diagnostics()
                self._record_failure("recreate_failed", "recreate")
                raise self._error(
                    "recreate",
                    "recreate_failed",
                    "Inspect bounded service status and logs; do not delete volumes.",
                    service_changed="unknown",
                )
            self.service_changed = "yes"

            self._stage("health")
            self._wait_for_health()

            self._stage("https_smoke")
            try:
                self.smoke.check(preflight.hostname)
            except Exception:
                self._record_failure("https_smoke_failed", "https_smoke")
                raise self._error(
                    "https_smoke",
                    "https_smoke_failed",
                    "Inspect DNS, Caddy and bounded proxy/web logs.",
                    service_changed="yes",
                ) from None

            self._stage("register")
            remote_head = self._remote_stdout(
                f"cd {shlex.quote(REMOTE_REPOSITORY)} && git rev-parse HEAD",
                stage="register",
                code="remote_head_unavailable",
            )
            if remote_head != self.target_sha:
                self._record_failure("remote_head_mismatch", "register")
                raise self._error(
                    "register",
                    "remote_head_mismatch",
                    "Inspect the remote checkout before another deploy.",
                    service_changed="yes",
                )
            self._record_success(remote_head)

            duration = max(0, round(self.clock() - started))
            self._print_success(
                remote_head=remote_head,
                duration=duration,
                already_deployed=False,
            )
            return DeploymentResult(
                previous_sha=self.previous_sha,
                target_sha=self.target_sha,
                remote_head=remote_head,
                already_deployed=False,
                duration_seconds=duration,
            )
        except DeploymentError as error:
            self._print_failure(error)
            raise
        finally:
            try:
                self._release_lock()
            finally:
                self.remote.close()

    def _local_preflight(self, requested_sha: str | None) -> str:
        root = self._local_stdout(
            ["git", "rev-parse", "--show-toplevel"],
            code="not_git_repository",
        )
        if Path(root).resolve() != self.repository_root.resolve():
            raise self._error(
                "local_preflight",
                "not_repository_root",
                "Run make staging-deploy from the repository root.",
            )

        origin = self._local_stdout(
            ["git", "remote", "get-url", "origin"],
            code="origin_missing",
        )
        if origin not in EXPECTED_ORIGINS:
            raise self._error(
                "local_preflight",
                "origin_unexpected",
                "Restore the approved origin remote before deploying.",
            )

        ssh_config = self.local.run(
            ["ssh", "-G", STAGING_ALIAS],
            cwd=self.repository_root,
            timeout=30,
        )
        if not ssh_config.ok:
            raise self._error(
                "local_preflight",
                "ssh_alias_missing",
                "Configure the approved SSH alias before deploying.",
            )
        ssh_values = {}
        for line in ssh_config.stdout.splitlines():
            key, _, value = line.partition(" ")
            if key in {"hostname", "user", "port", "identityfile"}:
                ssh_values.setdefault(key, value.strip())
        if (
            ssh_values.get("hostname") in {None, "", STAGING_ALIAS}
            or not ssh_values.get("user")
            or not ssh_values.get("identityfile")
        ):
            raise self._error(
                "local_preflight",
                "ssh_alias_missing",
                "Configure hostname, user and identity for the approved SSH alias.",
            )

        fetch = self.local.run(
            ["git", "fetch", "origin", "main"],
            cwd=self.repository_root,
            timeout=120,
        )
        if not fetch.ok:
            raise self._error(
                "local_preflight",
                "origin_main_fetch_failed",
                "Restore non-interactive access to origin/main and retry.",
            )

        candidate = (
            f"{requested_sha.strip()}^{{commit}}"
            if requested_sha
            else "origin/main^{commit}"
        )
        target = self._local_stdout(
            ["git", "rev-parse", "--verify", candidate],
            code="target_sha_invalid",
        ).lower()
        if not SHA_PATTERN.fullmatch(target):
            raise self._error(
                "local_preflight",
                "target_sha_invalid",
                "Provide a valid commit SHA from origin/main.",
            )

        ancestry = self.local.run(
            ["git", "merge-base", "--is-ancestor", target, "origin/main"],
            cwd=self.repository_root,
            timeout=30,
        )
        if not ancestry.ok:
            raise self._error(
                "local_preflight",
                "target_not_in_origin_main",
                "Select a commit belonging to the approved origin/main history.",
            )
        return target

    def _remote_preflight(self) -> RemotePreflight:
        checks = (
            ("ssh_connection_failed", "true"),
            ("sudo_n_failed", "sudo -n true"),
            (
                "remote_checkout_missing",
                f"test -d {shlex.quote(REMOTE_REPOSITORY)}/.git",
            ),
            ("remote_git_missing", "command -v git >/dev/null"),
            (
                "staging_env_missing",
                f"sudo -n test -f {shlex.quote(STAGING_ENV)}",
            ),
            (
                "remote_fetch_unavailable",
                f"cd {shlex.quote(REMOTE_REPOSITORY)} && "
                "timeout 20 env GIT_TERMINAL_PROMPT=0 "
                "git fetch --dry-run --prune origin >/dev/null",
            ),
            ("docker_unavailable", "sudo -n docker info >/dev/null"),
            (
                "compose_unavailable",
                "sudo -n docker compose version >/dev/null",
            ),
            (
                "compose_file_missing",
                f"test -f {shlex.quote(REMOTE_REPOSITORY)}/{COMPOSE_FILE}",
            ),
            (
                "media_directory_missing",
                f"test -d {shlex.quote(MEDIA_DIRECTORY)}",
            ),
            (
                "compose_config_invalid",
                self._compose("config --quiet"),
            ),
        )
        for code, command in checks:
            result = self.remote.run(command, timeout=30)
            if not result.ok:
                next_action = (
                    "Verify the SSH alias, host key and private-key passphrase."
                    if code == "ssh_connection_failed"
                    else "Restore the documented staging prerequisite and retry."
                )
                raise self._error(
                    "remote_preflight",
                    code,
                    next_action,
                )

        origin = self._remote_stdout(
            f"cd {shlex.quote(REMOTE_REPOSITORY)} && git remote get-url origin",
            stage="remote_preflight",
            code="remote_origin_missing",
        )
        if origin not in EXPECTED_ORIGINS:
            raise self._error(
                "remote_preflight",
                "remote_origin_unexpected",
                "Restore the approved remote origin before deploying.",
            )

        status = self.remote.run(
            (
                f"cd {shlex.quote(REMOTE_REPOSITORY)} && "
                "git status --porcelain=v1 --untracked-files=all"
            ),
            timeout=30,
        )
        if not status.ok:
            raise self._error(
                "remote_preflight",
                "remote_status_failed",
                "Inspect the remote checkout before deploying.",
            )
        if status.stdout.strip():
            raise self._error(
                "remote_preflight",
                "remote_checkout_dirty",
                "Resolve remote tracked and untracked changes manually.",
            )

        lock_check = self.remote.run(
            f"sudo -n test ! -e {shlex.quote(LOCK_DIRECTORY)}",
            timeout=15,
        )
        if not lock_check.ok:
            raise self._error(
                "remote_preflight",
                "deployment_already_running",
                "Wait for the active deploy or inspect a stale lock manually.",
            )

        previous_sha = self._remote_stdout(
            f"cd {shlex.quote(REMOTE_REPOSITORY)} && git rev-parse HEAD",
            stage="remote_preflight",
            code="previous_sha_unavailable",
        ).lower()
        if not SHA_PATTERN.fullmatch(previous_sha):
            raise self._error(
                "remote_preflight",
                "previous_sha_invalid",
                "Inspect the remote checkout before deploying.",
            )

        free_kb_text = self._remote_stdout(
            (f"df -Pk {shlex.quote(REMOTE_REPOSITORY)} | awk 'NR == 2 {{print $4}}'"),
            stage="remote_preflight",
            code="disk_space_unavailable",
        )
        try:
            free_kb = int(free_kb_text)
        except ValueError:
            raise self._error(
                "remote_preflight",
                "disk_space_invalid",
                "Inspect filesystem capacity before deploying.",
            ) from None
        if free_kb < MIN_FREE_KB:
            raise self._error(
                "remote_preflight",
                "insufficient_disk_space",
                "Free disk space safely before deploying; do not prune blindly.",
            )

        hostname = self._remote_stdout(
            (f"sudo -n sed -n 's/^STAGING_HOSTNAME=//p' {shlex.quote(STAGING_ENV)}"),
            stage="remote_preflight",
            code="staging_hostname_unavailable",
        )
        if not hostname or any(character.isspace() for character in hostname):
            raise self._error(
                "remote_preflight",
                "staging_hostname_invalid",
                "Correct STAGING_HOSTNAME without printing the environment.",
            )

        services_result = self.remote.run(
            self._compose("ps --services --filter status=running"),
            timeout=30,
        )
        if not services_result.ok:
            raise self._error(
                "remote_preflight",
                "service_status_unavailable",
                "Inspect Compose status before deploying.",
            )
        services = tuple(
            sorted(
                line.strip()
                for line in services_result.stdout.splitlines()
                if line.strip()
            )
        )
        return RemotePreflight(
            previous_sha=previous_sha,
            hostname=hostname,
            running_services=services,
        )

    def _last_successful_deployment_matches_target(self) -> bool:
        existence = self.remote.run(
            f"sudo -n test -f {shlex.quote(CURRENT_DEPLOYMENT)}",
            timeout=15,
        )
        if existence.exited == 1:
            return False
        if not existence.ok:
            raise self._error(
                "idempotency",
                "current_deployment_read_failed",
                "Inspect the deployment record before retrying.",
            )

        current = self.remote.run(
            f"sudo -n cat {shlex.quote(CURRENT_DEPLOYMENT)}",
            timeout=15,
        )
        if not current.ok:
            raise self._error(
                "idempotency",
                "current_deployment_read_failed",
                "Inspect the deployment record before retrying.",
            )

        try:
            record = json.loads(current.stdout)
        except (json.JSONDecodeError, TypeError):
            raise self._error(
                "idempotency",
                "current_deployment_invalid",
                "Inspect the deployment record before retrying.",
            ) from None
        if not isinstance(record, dict):
            raise self._error(
                "idempotency",
                "current_deployment_invalid",
                "Inspect the deployment record before retrying.",
            )

        return (
            record.get("result") == "success"
            and record.get("target_sha") == self.target_sha
        )

    def _acquire_lock(self) -> None:
        token = uuid.uuid4().hex
        owner = f"{LOCK_DIRECTORY}/owner"
        command = (
            "sudo -n sh -c "
            + shlex.quote(
                f"umask 077; mkdir {LOCK_DIRECTORY} && printf '%s\\n' \"$1\" > {owner}"
            )
            + " -- "
            + shlex.quote(token)
        )
        result = self.remote.run(command, timeout=15)
        if not result.ok:
            raise self._error(
                "lock",
                "deployment_already_running",
                "Wait for the active deploy or inspect a stale lock manually.",
            )
        self.lock_token = token

    def _release_lock(self) -> None:
        if not self.lock_token:
            return
        owner = f"{LOCK_DIRECTORY}/owner"
        script = (
            f'test "$(cat {owner} 2>/dev/null)" = "$1" && '
            f"rm -f {owner} && rmdir {LOCK_DIRECTORY}"
        )
        try:
            result = self.remote.run(
                "sudo -n sh -c "
                + shlex.quote(script)
                + " -- "
                + shlex.quote(self.lock_token),
                timeout=15,
            )
            if not result.ok:
                self.output("Warning: lock_release_failed")
        except Exception:
            self.output("Warning: lock_release_failed")
        finally:
            self.lock_token = None

    def _checkout_target(self) -> None:
        commands = (
            "env GIT_TERMINAL_PROMPT=0 git fetch --prune origin",
            f"git cat-file -e {shlex.quote(self.target_sha + '^{commit}')}",
            (
                "git merge-base --is-ancestor "
                f"{shlex.quote(self.target_sha)} origin/main"
            ),
            f"git checkout --detach {shlex.quote(self.target_sha)}",
        )
        for command in commands:
            result = self.remote.run(
                f"cd {shlex.quote(REMOTE_REPOSITORY)} && {command}",
                timeout=120,
            )
            if not result.ok:
                restored = self._restore_checkout()
                self._record_failure("checkout_failed", "checkout")
                code = "checkout_failed" if restored else "checkout_restore_failed"
                next_action = (
                    "Inspect remote Git access and the approved target SHA."
                    if restored
                    else "Restore the previous remote SHA manually before retrying."
                )
                raise self._error("checkout", code, next_action)
        verification = self.remote.run(
            f"cd {shlex.quote(REMOTE_REPOSITORY)} && git rev-parse HEAD",
            timeout=60,
        )
        remote_head = verification.stdout.strip().lower() if verification.ok else ""
        if remote_head != self.target_sha:
            restored = self._restore_checkout()
            self._record_failure("checkout_verification_failed", "checkout")
            code = (
                "checkout_verification_failed"
                if restored
                else "checkout_restore_failed"
            )
            next_action = (
                "Inspect the remote checkout before retrying."
                if restored
                else "Restore the previous remote SHA manually before retrying."
            )
            raise self._error("checkout", code, next_action)

    def _run_before_recreate(
        self,
        *,
        command: str,
        failure_code: str,
        next_action: str,
    ) -> None:
        result = self.remote.run(command, timeout=COMMAND_TIMEOUT_SECONDS)
        if result.ok:
            return
        stage = self._current_stage_from_code(failure_code)
        restored = self._restore_checkout()
        self._record_failure(failure_code, stage)
        if not restored:
            raise self._error(
                stage,
                "checkout_restore_failed",
                "Restore the previous remote SHA manually before retrying.",
            )
        raise self._error(stage, failure_code, next_action)

    def _restore_checkout(self) -> bool:
        if not SHA_PATTERN.fullmatch(self.previous_sha):
            return False
        result = self.remote.run(
            (
                f"cd {shlex.quote(REMOTE_REPOSITORY)} && "
                f"git checkout --detach {shlex.quote(self.previous_sha)}"
            ),
            timeout=60,
        )
        return result.ok

    def _wait_for_health(self) -> None:
        deadline = self.clock() + self.health_timeout
        while self.clock() <= deadline:
            db = self._container_state("db", require_health=True)
            web = self._container_state("web", require_health=True)
            proxy = self._container_state("proxy", require_health=False)
            caddy = self.remote.run(
                self._compose("exec -T proxy caddy version >/dev/null"),
                timeout=20,
            ).ok
            if db == "healthy" and web == "healthy" and proxy == "running" and caddy:
                return
            self.sleep(self.health_poll)
        self._print_bounded_diagnostics()
        self._record_failure("health_timeout", "health")
        raise self._error(
            "health",
            "health_timeout",
            "Inspect bounded service status and logs before another deploy.",
            service_changed="yes",
        )

    def _container_state(self, service: str, *, require_health: bool) -> str:
        container_id = self.remote.run(
            self._compose(f"ps -q {shlex.quote(service)}"), timeout=20
        )
        if not container_id.ok or not container_id.stdout.strip():
            return "missing"
        template = (
            "{{if .State.Health}}{{.State.Health.Status}}"
            "{{else}}{{.State.Status}}{{end}}"
            if require_health
            else "{{.State.Status}}"
        )
        result = self.remote.run(
            "sudo -n docker inspect --format "
            + shlex.quote(template)
            + " "
            + shlex.quote(container_id.stdout.strip()),
            timeout=20,
        )
        return result.stdout.strip() if result.ok else "unknown"

    def _print_bounded_diagnostics(self) -> None:
        status = self.remote.run(self._compose("ps"), timeout=30)
        if status.stdout.strip():
            self.output(status.stdout.strip())
        for service in ("proxy", "web", "db"):
            logs = self.remote.run(
                self._compose(f"logs --tail={LOG_TAIL_LINES} {service}"),
                timeout=30,
            )
            if logs.stdout.strip():
                self.output(logs.stdout.strip())
            if logs.stderr.strip():
                self.output(logs.stderr.strip())

    def _record_started(self) -> None:
        timestamp = self.now().isoformat().replace("+00:00", "Z")
        record = {
            "previous_sha": self.previous_sha,
            "target_sha": self.target_sha,
            "deployed_at_utc": timestamp,
            "result": "started",
        }
        self._write_record(record, update_current=False)

    def _record_success(self, remote_head: str) -> None:
        timestamp = self.now().isoformat().replace("+00:00", "Z")
        record = {
            "previous_sha": self.previous_sha,
            "target_sha": self.target_sha,
            "deployed_at_utc": timestamp,
            "result": "success",
        }
        self._write_record(record, update_current=True)
        if remote_head != self.target_sha:
            raise self._error(
                "register",
                "remote_head_mismatch",
                "Inspect the remote checkout.",
                service_changed="yes",
            )

    def _record_failure(self, code: str, stage: str) -> None:
        if not self.lock_token:
            return
        timestamp = self.now().isoformat().replace("+00:00", "Z")
        record = {
            "previous_sha": self.previous_sha,
            "target_sha": self.target_sha,
            "deployed_at_utc": timestamp,
            "result": code,
            "stage": stage,
            "remote_service_changed": self.service_changed,
        }
        try:
            self._write_record(record, update_current=False)
        except DeploymentError:
            self.output("Warning: deployment_failure_record_failed")

    def _write_record(self, record: dict[str, str], *, update_current: bool) -> None:
        payload = json.dumps(record, sort_keys=True, separators=(",", ":"))
        setup = f"sudo -n install -d -m 0750 {shlex.quote(DEPLOYMENTS_DIRECTORY)}"
        if not self.remote.run(setup, timeout=15).ok:
            raise self._error(
                "register",
                "deployment_record_directory_failed",
                "Inspect deployment record directory permissions.",
                service_changed=self.service_changed,
            )
        history = (
            "printf '%s\\n' "
            + shlex.quote(payload)
            + " | sudo -n tee -a "
            + shlex.quote(DEPLOYMENT_HISTORY)
            + " >/dev/null"
        )
        if not self.remote.run(history, timeout=15).ok:
            raise self._error(
                "register",
                "deployment_history_write_failed",
                "Inspect deployment history permissions.",
                service_changed=self.service_changed,
            )
        if not update_current:
            return
        temporary = f"{CURRENT_DEPLOYMENT}.tmp"
        current = (
            "printf '%s\\n' "
            + shlex.quote(payload)
            + " | sudo -n tee "
            + shlex.quote(temporary)
            + " >/dev/null && sudo -n mv "
            + shlex.quote(temporary)
            + " "
            + shlex.quote(CURRENT_DEPLOYMENT)
        )
        if not self.remote.run(current, timeout=15).ok:
            raise self._error(
                "register",
                "current_deployment_write_failed",
                "Inspect deployment record permissions.",
                service_changed=self.service_changed,
            )

    def _site_reconciliation_command(self) -> str:
        python = (
            "import os; "
            "from wagtail.models import Site; "
            "site = Site.objects.get(is_default_site=True); "
            'site.hostname = os.environ["STAGING_HOSTNAME"]; '
            "site.port = 443; "
            'site.save(update_fields=["hostname", "port"]); '
            'print(f"Default Wagtail Site: {site.hostname}:{site.port}")'
        )
        return self._compose(
            "run --rm web python manage.py shell -c " + shlex.quote(python)
        )

    def _compose(self, arguments: str) -> str:
        return (
            "cd "
            + shlex.quote(REMOTE_REPOSITORY)
            + " && sudo -n docker compose --env-file "
            + shlex.quote(STAGING_ENV)
            + " -f "
            + shlex.quote(COMPOSE_FILE)
            + " "
            + arguments
        )

    def _local_stdout(self, args: Sequence[str], *, code: str) -> str:
        result = self.local.run(args, cwd=self.repository_root, timeout=60)
        if not result.ok:
            raise self._error(
                "local_preflight",
                code,
                "Correct the local repository prerequisite and retry.",
            )
        return result.stdout.strip()

    def _remote_stdout(self, command: str, *, stage: str, code: str) -> str:
        result = self.remote.run(command, timeout=60)
        if not result.ok:
            raise self._error(
                stage,
                code,
                "Inspect the remote prerequisite and retry.",
                service_changed=self.service_changed,
            )
        return result.stdout.strip()

    def _error(
        self,
        stage: str,
        code: str,
        next_action: str,
        *,
        service_changed: str | None = None,
    ) -> DeploymentError:
        return DeploymentError(
            stage=stage,
            code=code,
            next_action=next_action,
            previous_sha=self.previous_sha,
            target_sha=self.target_sha,
            service_changed=service_changed or self.service_changed,
        )

    def _stage(self, stage: str) -> None:
        self.output(f"==> {stage}")

    def _print_success(
        self,
        *,
        remote_head: str,
        duration: int,
        already_deployed: bool,
    ) -> None:
        self.output("Deployment succeeded")
        self.output(f"Previous SHA: {self.previous_sha}")
        self.output(f"Target SHA: {self.target_sha}")
        self.output(f"Remote HEAD: {remote_head}")
        if already_deployed:
            self.output("Result: already_deployed")
        else:
            self.output("Build: passed")
            self.output("Migrations: passed")
            self.output("Bootstrap: passed")
            self.output("Wagtail Site: passed")
            self.output("Health: passed")
            self.output("HTTPS smoke: passed")
        self.output(f"Duration: {duration}s")

    def _print_failure(self, error: DeploymentError) -> None:
        self.output("Deployment failed")
        self.output(f"Stage: {error.stage}")
        self.output(f"Code: {error.code}")
        self.output(f"Previous SHA: {error.previous_sha}")
        self.output(f"Target SHA: {error.target_sha}")
        self.output(f"Remote service changed: {error.service_changed}")
        self.output(f"Next action: {error.next_action}")

    @staticmethod
    def _current_stage_from_code(code: str) -> str:
        return {
            "build_failed": "build",
            "migration_failed": "migrations",
            "bootstrap_failed": "bootstrap",
            "site_reconciliation_failed": "wagtail_site",
        }[code]


def validate_command_contracts() -> tuple[str, ...]:
    """Expose generated command contracts for focused tests and review."""

    compose_prefix = (
        f"cd {REMOTE_REPOSITORY} && sudo -n docker compose "
        f"--env-file {STAGING_ENV} -f {COMPOSE_FILE}"
    )
    return (
        f"{compose_prefix} build web",
        f"{compose_prefix} run --rm web python manage.py migrate --noinput",
        f"{compose_prefix} run --rm web python manage.py bootstrap_mvp_access",
        f"{compose_prefix} up -d",
        f"cd {REMOTE_REPOSITORY} && git checkout --detach <sha>",
        f"{compose_prefix} logs --tail={LOG_TAIL_LINES} web",
    )
