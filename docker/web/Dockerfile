FROM python:3.12-slim

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

COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip \
    && pip install -r /app/requirements.txt

COPY docker/web/entrypoint.sh /usr/local/bin/school-newsroom-entrypoint
RUN chmod +x /usr/local/bin/school-newsroom-entrypoint

COPY . /app

EXPOSE 8000

ENTRYPOINT ["school-newsroom-entrypoint"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
