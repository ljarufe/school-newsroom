FROM python:3.12-slim

ARG APP_UID=10001
ARG APP_GID=10001

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        build-essential \
        gettext \
        libpq-dev \
        netcat-traditional \
        util-linux \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid "${APP_GID}" app \
    && useradd \
        --uid "${APP_UID}" \
        --gid "${APP_GID}" \
        --create-home \
        --home-dir /home/app \
        --shell /usr/sbin/nologin \
        app

COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip \
    && pip install -r /app/requirements.txt

COPY docker/web/entrypoint.sh /usr/local/bin/school-newsroom-entrypoint
RUN chmod +x /usr/local/bin/school-newsroom-entrypoint

COPY --chown=app:app . /app
RUN mkdir -p /app/media /app/staticfiles \
    && chown -R app:app /app /home/app

EXPOSE 8000

ENTRYPOINT ["school-newsroom-entrypoint"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
