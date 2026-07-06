IN_CONTAINER := $(shell test -f /.dockerenv && echo 1 || echo 0)
COMPOSE = docker compose
WAIT_FOR_DB = until nc -z db 5432; do sleep 1; done;
PYTEST_CACHE_DIR = /tmp/school-newsroom-pytest-cache
RUFF_CACHE_DIR = /tmp/school-newsroom-ruff-cache

.PHONY: build up down logs shell bash migrate makemigrations createsuperuser test lint format check

ifeq ($(IN_CONTAINER),1)
WEB =
WEB_RUN =

build up down logs:
	@echo "This target controls Docker Compose and must be run from the host, outside the Dev Container."
else
WEB = $(COMPOSE) exec web
WEB_RUN = $(COMPOSE) run --rm web

build:
	$(COMPOSE) build

up:
	$(COMPOSE) up

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f
endif

shell:
	$(WEB) python manage.py shell

bash:
	$(WEB) bash

migrate:
	$(WEB_RUN) sh -c "$(WAIT_FOR_DB) python manage.py migrate"

makemigrations:
	$(WEB_RUN) python manage.py makemigrations

createsuperuser:
	$(WEB) python manage.py createsuperuser

test:
	$(WEB_RUN) sh -c "$(WAIT_FOR_DB) DJANGO_SETTINGS_MODULE=config.settings.test pytest -o cache_dir=$(PYTEST_CACHE_DIR)"

lint:
	$(WEB_RUN) sh -c "RUFF_CACHE_DIR=$(RUFF_CACHE_DIR) ruff check ."

format:
	$(WEB_RUN) sh -c "RUFF_CACHE_DIR=$(RUFF_CACHE_DIR) ruff format ."

check: lint test
