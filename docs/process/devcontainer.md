# VS Code Dev Container Workflow

School Newsroom is Docker-first. The recommended VS Code setup is to reopen the repository inside the existing Docker Compose `web` service so the editor, terminal, Python extension, Pylance, Ruff, pytest, debugger, Git tooling, and SSH client use the same project environment as the application.

## Prerequisites

- Docker and Docker Compose running on the host.
- VS Code.
- VS Code Dev Containers extension.

## Open The Project In The Container

1. Open the repository folder in VS Code.
2. Open the Command Palette.
3. Run `Dev Containers: Reopen in Container`.
4. Wait for VS Code to start the Docker Compose services and attach to the `web` service.
5. Confirm the lower-left status bar shows `Dev Container: School Newsroom`.

The Dev Container reuses `docker-compose.yml`, opens the workspace at `/app`, and starts the `web` and `db` services. The integrated terminal should also open in `/app`.

The container-specific Python settings live in `.devcontainer/devcontainer.json`, not in workspace settings. This avoids making a local VS Code window expect `/usr/local/bin/python` before the repository is reopened in the container.

Verify the Python runtime from the integrated terminal:

```bash
python -c "import sys; print(sys.executable)"
python --version
```

Expected interpreter path:

```text
/usr/local/bin/python
```

## Development User And Tools

The Dev Container config uses the official `common-utils` Feature to provide common developer utilities, Git, an SSH client, sudo support, and a non-root development user. VS Code connects as that non-root user instead of `root`, with UID/GID updates enabled to reduce bind-mount ownership problems on Linux hosts.

After rebuilding the Dev Container, verify:

```bash
whoami
id
git --version
git status --short
git diff
ssh -V
```

Creating files from the integrated terminal should not leave root-owned files in the repository.

## Normal Server

The normal Django/Wagtail development server remains available at:

```text
http://localhost:8000/
```

Wagtail Admin is available at:

```text
http://localhost:8000/admin/
```

## General Validation

The Makefile remains the source of truth for full repository validation:

```bash
make test
make lint
make check
```

Use `make check` before reviewing a change or preparing a commit.

When the Makefile is run on the host, project commands delegate to Docker Compose. When it is run from inside the Dev Container, validation commands use the current container runtime directly because Docker CLI is intentionally not required inside the container.

The Makefile sends pytest and Ruff caches to `/tmp/school-newsroom-*` so validation does not create or depend on tool cache files inside the bind-mounted repository.

## Targeted Test Investigation

Use VS Code Test Explorer for focused investigation of one test, one file, or a small subset of tests. VS Code is configured inside the Dev Container to use pytest with:

```text
config.settings.test
```

Test Explorer is not a replacement for `make check`; it is a targeted diagnostic tool.

## Debug A Test

1. Open the test file.
2. Add a breakpoint on an executable Python line.
3. Open Testing in VS Code.
4. Choose `Debug Test`.
5. Inspect Variables, Watch, Call Stack, Breakpoints, and Debug Console.

The `Python: Debug tests` profile sets `DJANGO_SETTINGS_MODULE=config.settings.test`.

Practical debugger controls:

- Continue resumes execution until the next breakpoint or program end.
- Step Over runs the current line without entering called functions.
- Step Into enters the function being called.
- Step Out finishes the current function and returns to its caller.

## Debug Django/Wagtail

Use `Run and Debug` and select:

```text
Django/Wagtail: Debug server
```

This starts:

```bash
python manage.py runserver 0.0.0.0:8001 --noreload
```

Open the debug server at:

```text
http://localhost:8001/
```

The normal service server on `http://localhost:8000/` remains separate from the debug server on port `8001`. The debug profile uses `--noreload` so breakpoint behavior remains predictable.

Add a breakpoint to project Python code executed by the behavior being investigated, then trigger that behavior through the debug server on port `8001`.

## Ports

| Port | Purpose                                  |
| ---- | ---------------------------------------- |
| 8000 | Normal Django/Wagtail development server |
| 8001 | VS Code Django/Wagtail debug server      |
| 5434 | Host-exposed project PostgreSQL          |

## Troubleshooting

If Python imports appear unresolved, confirm the repository is actually reopened in the Dev Container and the status bar shows `Dev Container: School Newsroom`.

If the selected interpreter looks invalid in a local VS Code window, reopen the repository in the Dev Container. `/usr/local/bin/python` is the container interpreter, not a host interpreter.

If tests do not appear, confirm pytest is enabled after opening the Dev Container and refresh Test Explorer.

For diagnostics, check `View -> Problems`. For Python and Pylance details, check `View -> Output` and select the relevant Python or Pylance output channel.

If port `8001` is unavailable, check the VS Code Ports panel while the debug profile is running.
