"""Thin Fabric entry point for the staging deployment orchestrator."""

from __future__ import annotations

import os

from fabric import Connection, task
from invoke import Exit

from ops.staging_deploy import (
    STAGING_ALIAS,
    CommandResult,
    DeploymentError,
    StagingDeployer,
    StandardLibrarySmokeProbe,
    SubprocessLocalRunner,
)


class FabricRemoteRunner:
    """Adapt one Fabric Connection to the transport-neutral runner contract."""

    def __init__(self, connection: Connection) -> None:
        self.connection = connection

    def run(self, command: str, *, timeout: int | None = None) -> CommandResult:
        result = self.connection.run(
            command,
            hide=True,
            in_stream=False,
            pty=False,
            timeout=timeout,
            warn=True,
        )
        return CommandResult(
            command=command,
            stdout=result.stdout or "",
            stderr=result.stderr or "",
            exited=result.exited,
        )

    def close(self) -> None:
        self.connection.close()


@task
def staging_deploy(context, sha=None):
    """Deploy origin/main or an approved SHA to the Oracle staging host."""

    requested_sha = sha or os.environ.get("STAGING_DEPLOY_SHA") or None
    connect_kwargs = dict(context.config.connect_kwargs)
    connect_kwargs.update(
        {
            "allow_agent": False,
            "look_for_keys": False,
        }
    )
    connection = Connection(
        STAGING_ALIAS,
        config=context.config,
        connect_timeout=10,
        connect_kwargs=connect_kwargs,
    )
    deployer = StagingDeployer(
        local=SubprocessLocalRunner(),
        remote=FabricRemoteRunner(connection),
        smoke=StandardLibrarySmokeProbe(),
    )
    try:
        deployer.deploy(requested_sha)
    except DeploymentError:
        raise Exit(code=1) from None
    except Exception:
        print("Deployment failed")
        print("Stage: internal")
        print("Code: unexpected_error")
        print(f"Previous SHA: {deployer.previous_sha}")
        print(f"Target SHA: {deployer.target_sha or requested_sha or 'unknown'}")
        print("Remote service changed: unknown")
        print("Next action: Stop and inspect the implementation before retrying.")
        raise Exit(code=1) from None
