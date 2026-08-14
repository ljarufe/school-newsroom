#!/bin/sh
set -eu

repository_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
filter="$repository_root/ops/staging_security/fail2ban/filter.d/school-newsroom-caddy-429.conf"
action="$repository_root/ops/staging_security/fail2ban/action.d/school-newsroom-docker-user-web.conf"
jail="$repository_root/tests/fixtures/staging_security/jail.local"
access_log="$repository_root/tests/fixtures/staging_security/caddy-access.json"

docker run --rm --cap-add NET_ADMIN \
    --volume "$filter:/etc/fail2ban/filter.d/school-newsroom-caddy-429.conf:ro" \
    --volume "$action:/etc/fail2ban/action.d/school-newsroom-docker-user-web.conf:ro" \
    --volume "$jail:/etc/fail2ban/jail.d/school-newsroom.local:ro" \
    --volume "$access_log:/tmp/school-newsroom-caddy-access.json:ro" \
    ubuntu:24.04 sh -ec '
        apt-get update >/dev/null
        DEBIAN_FRONTEND=noninteractive apt-get install -y fail2ban iptables >/dev/null
        fail2ban-client --version
        fail2ban-regex /tmp/school-newsroom-caddy-access.json /etc/fail2ban/filter.d/school-newsroom-caddy-429.conf
        fail2ban-client -t
        iptables -N DOCKER-USER
        fail2ban-client start
        fail2ban-client status school-newsroom-caddy-429
        fail2ban-client set school-newsroom-caddy-429 banip 192.0.2.55
        iptables -C DOCKER-USER -p tcp -m multiport --dports 80,443 -j f2b-sn-web
        iptables -C f2b-sn-web -s 192.0.2.55 -j DROP
        ! iptables -C DOCKER-USER -p tcp --dport 22 -j f2b-sn-web >/dev/null 2>&1
        fail2ban-client set school-newsroom-caddy-429 unbanip 192.0.2.55
        ! iptables -C f2b-sn-web -s 192.0.2.55 -j DROP >/dev/null 2>&1
        fail2ban-client stop school-newsroom-caddy-429
        ! iptables -L f2b-sn-web >/dev/null 2>&1
        iptables -L DOCKER-USER >/dev/null
        fail2ban-client stop
    '

echo "Fail2ban filter, configuration, web-only action, ban, unban, and jail-stop checks passed."
