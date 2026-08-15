#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
    echo "Run this host bootstrap as root." >&2
    exit 1
fi

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 /path/to/rendered-school-newsroom.local" >&2
    exit 1
fi

rendered_jail=$1
if [ ! -f "$rendered_jail" ]; then
    echo "The rendered jail configuration does not exist." >&2
    exit 1
fi
if awk '
    /^[[:space:]]*([#;]|$)/ { next }
    /CALIBRATE_/ { unresolved = 1 }
    END { exit !unresolved }
' "$rendered_jail"; then
    echo "Replace every active CALIBRATE_* value before bootstrap." >&2
    exit 1
fi

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
fail2ban_source="$script_dir/fail2ban"

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install --yes fail2ban

fail2ban_version=$(fail2ban-client --version)
case "$fail2ban_version" in
    *v1.0.*) ;;
    *)
        echo "Expected Fail2ban 1.0.x; found: $fail2ban_version" >&2
        exit 1
        ;;
esac

iptables -w -n -L DOCKER-USER >/dev/null

install -d -o root -g adm -m 0750 /var/log/school-newsroom/caddy
if [ ! -e /var/log/school-newsroom/caddy/access.json ]; then
    touch /var/log/school-newsroom/caddy/access.json
fi
chown root:adm /var/log/school-newsroom/caddy/access.json
chmod 0640 /var/log/school-newsroom/caddy/access.json

install -o root -g root -m 0644 \
    "$fail2ban_source/filter.d/school-newsroom-caddy-429.conf" \
    /etc/fail2ban/filter.d/school-newsroom-caddy-429.conf
install -o root -g root -m 0644 \
    "$fail2ban_source/action.d/school-newsroom-docker-user-web.conf" \
    /etc/fail2ban/action.d/school-newsroom-docker-user-web.conf
install -o root -g root -m 0640 "$rendered_jail" \
    /etc/fail2ban/jail.d/school-newsroom.local

fail2ban-client -t
systemctl enable --now fail2ban
systemctl restart fail2ban
readiness_attempt=0
until fail2ban-client status school-newsroom-caddy-429 >/dev/null 2>&1; do
    readiness_attempt=$((readiness_attempt + 1))
    if [ "$readiness_attempt" -ge 20 ]; then
        echo "Fail2ban did not become ready within 10 seconds." >&2
        exit 1
    fi
    sleep 0.5
done
fail2ban-client status school-newsroom-caddy-429
