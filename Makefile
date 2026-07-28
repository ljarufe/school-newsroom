IN_CONTAINER := $(shell test -f /.dockerenv && echo 1 || echo 0)
COMPOSE = docker compose
WAIT_FOR_DB = until nc -z db 5432; do sleep 1; done;
PYTEST_CACHE_DIR = /tmp/school-newsroom-pytest-cache
RUFF_CACHE_DIR = /tmp/school-newsroom-ruff-cache

.PHONY: build up down logs shell bash migrate makemigrations compilemessages createsuperuser test lint format migration-check check browser-test

ifeq ($(IN_CONTAINER),1)
WEB =
WEB_RUN =

build up down logs:
	@echo "This target controls Docker Compose and must be run from the host, outside the Dev Container."

browser-test:
	@echo "Browser tests use an isolated Docker Compose runner and must run from the host."
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

lint:
	$(WEB_RUN) sh -c "RUFF_CACHE_DIR=$(RUFF_CACHE_DIR) ruff check ."

format:
	$(WEB_RUN) sh -c "RUFF_CACHE_DIR=$(RUFF_CACHE_DIR) ruff format ."

migration-check:
	$(WEB_RUN) python manage.py makemigrations --check --skip-checks

check: lint migration-check test
