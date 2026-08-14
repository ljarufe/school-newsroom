#!/bin/sh
set -eu

repository_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
image=school-newsroom-staging-proxy:epic8-005-test
container=school-newsroom-epic8-005-caddy-test
fixture="$repository_root/tests/fixtures/staging_security/Caddyfile"
temporary_directory=$(mktemp -d)
search_headers="$temporary_directory/search.headers"
login_headers="$temporary_directory/login.headers"
access_log="$temporary_directory/access.json"
general_headers="$temporary_directory/general.headers"

cleanup() {
    docker stop "$container" >/dev/null 2>&1 || true
    rm -f "$search_headers" "$login_headers" "$general_headers" "$access_log"
    rmdir "$temporary_directory" >/dev/null 2>&1 || true
}
trap cleanup EXIT HUP INT TERM

cd "$repository_root"
docker build --file docker/staging/Caddy.Dockerfile --tag "$image" .
docker run --rm "$image" caddy version | grep '^v2\.11\.4 '
docker run --rm "$image" caddy list-modules | grep '^http\.handlers\.rate_limit$'
docker run --rm \
    --volume "$repository_root/docker/staging/Caddyfile:/etc/caddy/Caddyfile:ro" \
    --env ACME_EMAIL=operator@example.invalid \
    --env STAGING_HOSTNAME=staging.example.invalid \
    --env CADDY_RATE_LIMIT_GENERAL_EVENTS=20 \
    --env CADDY_RATE_LIMIT_GENERAL_WINDOW=10s \
    --env CADDY_RATE_LIMIT_SEARCH_EVENTS=3 \
    --env CADDY_RATE_LIMIT_SEARCH_WINDOW=10s \
    --env CADDY_RATE_LIMIT_LOGIN_EVENTS=2 \
    --env CADDY_RATE_LIMIT_LOGIN_WINDOW=10s \
    "$image" caddy validate --config /etc/caddy/Caddyfile
if docker run --rm \
    --volume "$repository_root/docker/staging/Caddyfile:/etc/caddy/Caddyfile:ro" \
    --env ACME_EMAIL=operator@example.invalid \
    --env STAGING_HOSTNAME=staging.example.invalid \
    --env CADDY_RATE_LIMIT_GENERAL_EVENTS=not-an-integer \
    --env CADDY_RATE_LIMIT_GENERAL_WINDOW=10s \
    --env CADDY_RATE_LIMIT_SEARCH_EVENTS=3 \
    --env CADDY_RATE_LIMIT_SEARCH_WINDOW=10s \
    --env CADDY_RATE_LIMIT_LOGIN_EVENTS=2 \
    --env CADDY_RATE_LIMIT_LOGIN_WINDOW=10s \
    "$image" caddy validate --config /etc/caddy/Caddyfile >/dev/null 2>&1; then
    echo "Invalid rate-limit configuration unexpectedly validated." >&2
    exit 1
fi

docker run --rm --detach --name "$container" \
    --publish 127.0.0.1:18081:8080 \
    --volume "$fixture:/etc/caddy/Caddyfile:ro" \
    --volume "$temporary_directory:/tmp/caddy-test" \
    "$image" >/dev/null

attempt=0
until curl --fail --silent http://127.0.0.1:18081/ >/dev/null 2>&1; do
    attempt=$((attempt + 1))
    if [ "$attempt" -ge 20 ]; then
        docker logs --tail 50 "$container"
        exit 1
    fi
    sleep 0.25
done

sleep 2
curl --fail --silent --show-error 'http://127.0.0.1:18081/noticias/?buscar=normal' >/dev/null
curl --fail --silent --show-error 'http://127.0.0.1:18081/noticias/?buscar=normal' >/dev/null
curl --silent --show-error \
    --header 'Authorization: Bearer must-not-appear' \
    --header 'Cookie: sessionid=must-not-appear' \
    --header 'Proxy-Authorization: Bearer must-not-appear' \
    --referer 'http://staging.example.invalid/noticias/?buscar=fictional-referer-search-term' \
    --dump-header "$search_headers" --output /dev/null \
    'http://127.0.0.1:18081/noticias/?buscar=exceso'
grep -Eq '^HTTP/[0-9.]+ 429' "$search_headers"
grep -Eiq '^Retry-After: [1-9][0-9]*' "$search_headers"
attempt=0
until grep -q 'buscar=REDACTED' "$access_log" 2>/dev/null; do
    attempt=$((attempt + 1))
    if [ "$attempt" -ge 20 ]; then
        echo "Redacted access-log entry was not written." >&2
        exit 1
    fi
    sleep 0.25
done
if grep -Eq 'must-not-appear|fictional-referer-search-term|Authorization|Cookie|Proxy-Authorization|Referer' "$access_log"; then
    echo "Sensitive request data reached the access log." >&2
    exit 1
fi

sleep 2
curl --fail --silent --show-error --request POST http://127.0.0.1:18081/admin/login/ >/dev/null
curl --silent --show-error --request POST --dump-header "$login_headers" --output /dev/null \
    http://127.0.0.1:18081/admin/login/
grep -Eq '^HTTP/[0-9.]+ 429' "$login_headers"
grep -Eiq '^Retry-After: [1-9][0-9]*' "$login_headers"

sleep 2
curl --fail --silent --show-error http://127.0.0.1:18081/ >/dev/null
for ignored_media_request in 1 2 3 4 5 6; do
    curl --fail --silent --show-error http://127.0.0.1:18081/media/test.jpg >/dev/null
done

sleep 2
for allowed_general_request in 1 2 3 4; do
    curl --fail --silent --show-error http://127.0.0.1:18081/ >/dev/null
done
curl --silent --show-error --dump-header "$general_headers" --output /dev/null \
    http://127.0.0.1:18081/
grep -Eq '^HTTP/[0-9.]+ 429' "$general_headers"
grep -Eiq '^Retry-After: [1-9][0-9]*' "$general_headers"
sleep 2
curl --fail --silent --show-error http://127.0.0.1:18081/ >/dev/null

echo "Caddy module, valid/invalid configuration, three rate limits, Retry-After, recovery, media, and URI/Referer redacted-log checks passed."
echo "Run ops/validate_staging_fail2ban.sh for isolated host-action validation."
