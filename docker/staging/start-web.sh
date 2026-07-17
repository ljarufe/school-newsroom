#!/bin/sh
set -eu

umask 022

database_host="${POSTGRES_HOST:-db}"
database_port="${POSTGRES_PORT:-5432}"
database_wait_attempts="${DATABASE_WAIT_ATTEMPTS:-60}"

case "$database_wait_attempts" in
    "" | 0 | *[!0-9]*)
        echo "DATABASE_WAIT_ATTEMPTS must be a positive integer." >&2
        exit 1
        ;;
esac

attempt=1
until nc -z "$database_host" "$database_port"; do
    if [ "$attempt" -ge "$database_wait_attempts" ]; then
        echo "Database did not become ready within ${database_wait_attempts} attempts." >&2
        exit 1
    fi
    attempt=$((attempt + 1))
    sleep 1
done

python manage.py collectstatic --noinput

exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "${GUNICORN_WORKERS:-2}" \
    --threads "${GUNICORN_THREADS:-2}" \
    --timeout "${GUNICORN_TIMEOUT:-60}" \
    --log-level "${GUNICORN_LOG_LEVEL:-info}" \
    --access-logfile - \
    --error-logfile - \
    --capture-output
