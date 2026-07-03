COMPOSE = docker compose
WEB = $(COMPOSE) exec web
WEB_RUN = $(COMPOSE) run --rm web
WAIT_FOR_DB = until nc -z db 5432; do sleep 1; done;

.PHONY: build up down logs shell bash migrate makemigrations createsuperuser test lint format check

build:
	$(COMPOSE) build

up:
	$(COMPOSE) up

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f

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
	$(WEB_RUN) sh -c "$(WAIT_FOR_DB) DJANGO_SETTINGS_MODULE=config.settings.test pytest"

lint:
	$(WEB_RUN) ruff check .

format:
	$(WEB_RUN) ruff format .

check: lint test
