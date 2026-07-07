#!/bin/sh
set -eu

if [ "$(id -u)" = "0" ]; then
    target_uid="$(stat -c "%u" /app)"
    target_gid="$(stat -c "%g" /app)"

    if [ "$target_uid" != "0" ]; then
        target_home="$(getent passwd "$target_uid" | cut -d: -f6 || true)"
        if [ -n "$target_home" ]; then
            export HOME="$target_home"
        else
            export HOME="/tmp"
        fi

        exec setpriv --reuid "$target_uid" --regid "$target_gid" --clear-groups -- "$@"
    fi
fi

exec "$@"
