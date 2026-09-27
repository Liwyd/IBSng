#!/usr/bin/env bash
#
# IBSng container entrypoint (PID 1).
#
#   1. runs install.sh --yes on first boot (idempotent; skipped afterwards)
#   2. sources /etc/ibsng/ibsng.env
#   3. starts the IBSng engine (ibs.py forks; parent exits once up)
#   4. runs apache in the foreground, forwarding SIGTERM/SIGINT to both
set -euo pipefail

PREFIX="${IBS_PREFIX:-/usr/local/IBSng}"
INSTALL_SH="/opt/ibsng/install.sh"

if [ ! -f /etc/ibsng/ibsng.env ] || [ ! -x "$PREFIX/ibs.py" ]; then
    echo "[ibsng] first boot - running installer"
    "$INSTALL_SH" --yes
else
    echo "[ibsng] already installed - skipping setup"
fi

set -a
# shellcheck disable=SC1091
. /etc/ibsng/ibsng.env
set +a

ENGINE_PID=""
APACHE_PID=""

stop_all() {
    trap - TERM INT
    if [ -n "$ENGINE_PID" ] && kill -0 "$ENGINE_PID" 2>/dev/null; then
        echo "[ibsng] stopping engine (pid $ENGINE_PID)"
        kill -TERM "$ENGINE_PID" 2>/dev/null || true
        for _ in $(seq 1 30); do
            kill -0 "$ENGINE_PID" 2>/dev/null || break
            sleep 1
        done
        kill -KILL "$ENGINE_PID" 2>/dev/null || true
    fi
    if [ -n "$APACHE_PID" ] && kill -0 "$APACHE_PID" 2>/dev/null; then
        echo "[ibsng] stopping apache (pid $APACHE_PID)"
        kill -TERM "$APACHE_PID" 2>/dev/null || true
    fi
}
trap 'stop_all; exit 0' TERM INT

echo "[ibsng] starting engine"
set +e
"$PREFIX/ibs.py" &
IBSPY_PID=$!
wait "$IBSPY_PID"
RC=$?
set -e
if [ "$RC" -ne 0 ]; then
    echo "[ibsng] engine failed to start (rc=$RC)" >&2
    stop_all
    exit "$RC"
fi
ENGINE_PID="$(cat /run/IBSng.pid 2>/dev/null || true)"

echo "[ibsng] starting apache"
apachectl -D FOREGROUND &
APACHE_PID=$!

set +e
wait "$APACHE_PID"
RC=$?
set -e
stop_all
exit "$RC"
