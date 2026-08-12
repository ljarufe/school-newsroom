IN_CONTAINER := $(shell test -f /.dockerenv && echo 1 || echo 0)
COMPOSE = docker compose
WAIT_FOR_DB = until nc -z db 5432; do sleep 1; done;
PYTEST_CACHE_DIR = /tmp/school-newsroom-pytest-cache
RUFF_CACHE_DIR = /tmp/school-newsroom-ruff-cache
OPS_VENV = .venv-ops
OPS_PYTHON = $(OPS_VENV)/bin/python
OPS_FAB = $(OPS_VENV)/bin/fab
OPS_REQUIREMENTS = requirements-ops.txt
OPS_REQUIREMENTS_STAMP = $(OPS_VENV)/.requirements.sha256
LOCK_IMAGE = python:3.12.11-slim-bookworm@sha256:519591d6871b7bc437060736b9f7456b8731f1499a57e22e6c285135ae657bf7
LOCK_CONTAINER = docker run --rm --user "$(shell id -u):$(shell id -g)" --volume "$(CURDIR):/app" --workdir /app --env HOME=/tmp --env PIP_CACHE_DIR=/tmp/pip-cache $(LOCK_IMAGE)
export STAGING_DEPLOY_SHA := $(SHA)

.PHONY: build up down logs shell bash migrate makemigrations compilemessages createsuperuser test coverage lint format migration-check check browser-test lock staging-deploy

ifeq ($(IN_CONTAINER),1)
WEB =
WEB_RUN =

build up down logs:
	@echo "This target controls Docker Compose and must be run from the host, outside the Dev Container."

browser-test:
	@echo "Browser tests use an isolated Docker Compose runner and must run from the host."
	@exit 1

lock:
	@echo "Lock generation uses the pinned Python image and must run from the host."
	@exit 1

staging-deploy:
	@echo "Staging deployment must run from the host, outside the Dev Container."
	@exit 1
else
WEB = $(COMPOSE) exec web
WEB_RUN = $(COMPOSE) run --rm web
BROWSER_COMPOSE = $(COMPOSE) -f docker-compose.browser.yml

build:
	$(COMPOSE) build

up:
	$(COMPOSE) up

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f

browser-test:
	@status=0; \
	cleanup() { \
		trap - EXIT HUP INT TERM; \
		cleanup_status=0; \
		$(BROWSER_COMPOSE) down --volumes --remove-orphans || cleanup_status=$$?; \
		if [ "$$status" -eq 0 ] && [ "$$cleanup_status" -ne 0 ]; then \
			status=$$cleanup_status; \
		fi; \
		exit "$$status"; \
	}; \
	trap 'status=$$?; cleanup' EXIT; \
	trap 'status=129; cleanup' HUP; \
	trap 'status=130; cleanup' INT; \
	trap 'status=143; cleanup' TERM; \
	$(BROWSER_COMPOSE) up --build --abort-on-container-exit --exit-code-from browser-test || status=$$?; \
	exit "$$status"

lock:
	$(LOCK_CONTAINER) sh -ec 'python -m venv /tmp/lock-venv; /tmp/lock-venv/bin/pip install --disable-pip-version-check pip==25.3 pip-tools==7.6.0; /tmp/lock-venv/bin/pip-compile --allow-unsafe --generate-hashes --strip-extras --output-file requirements.txt requirements.in; /tmp/lock-venv/bin/pip-compile --allow-unsafe --generate-hashes --strip-extras --output-file requirements-ops.txt requirements-ops.in'

staging-deploy:
	@set -eu; \
	if [ ! -x "$(OPS_PYTHON)" ]; then \
		python3 -m venv "$(OPS_VENV)"; \
	fi; \
	requirements_sha="$$(sha256sum "$(OPS_REQUIREMENTS)" | awk '{print $$1}')"; \
	installed_sha="$$(cat "$(OPS_REQUIREMENTS_STAMP)" 2>/dev/null || true)"; \
	if [ ! -x "$(OPS_FAB)" ] || [ "$$requirements_sha" != "$$installed_sha" ]; then \
		PIP_DISABLE_PIP_VERSION_CHECK=1 "$(OPS_PYTHON)" -m pip install --no-input --require-hashes -r "$(OPS_REQUIREMENTS)"; \
		printf '%s\n' "$$requirements_sha" > "$(OPS_REQUIREMENTS_STAMP)"; \
	fi; \
	"$(OPS_FAB)" --prompt-for-passphrase staging-deploy
endif

shell:
	$(WEB) python manage.py shell

bash:
	$(WEB) bash

migrate:
	$(WEB_RUN) sh -c "$(WAIT_FOR_DB) python manage.py migrate"

makemigrations:
	$(WEB_RUN) python manage.py makemigrations

compilemessages:
	$(WEB_RUN) python manage.py compilemessages

createsuperuser:
	$(WEB) python manage.py createsuperuser

test:
	$(WEB_RUN) sh -c "$(WAIT_FOR_DB) DJANGO_SETTINGS_MODULE=config.settings.test pytest -o cache_dir=$(PYTEST_CACHE_DIR)"

coverage:
	$(WEB_RUN) sh -c "$(WAIT_FOR_DB) DJANGO_SETTINGS_MODULE=config.settings.test pytest -o cache_dir=$(PYTEST_CACHE_DIR) --cov --cov-config=.coveragerc --cov-report=term-missing:skip-covered --cov-fail-under=90"

lint:
	$(WEB_RUN) sh -c "RUFF_CACHE_DIR=$(RUFF_CACHE_DIR) ruff check ."

format:
	$(WEB_RUN) sh -c "RUFF_CACHE_DIR=$(RUFF_CACHE_DIR) ruff format ."

migration-check:
	$(WEB_RUN) python manage.py makemigrations --check --skip-checks

check: lint migration-check coverage
