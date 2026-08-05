#!/usr/bin/env bash
set -euo pipefail
PIDFILE="${FRONTEND_ACCEPTANCE_PIDFILE:-/tmp/sc-frontend-acceptance.pid}"
PORT="${FRONTEND_ACCEPTANCE_PORT:-5175}"

port_open() {
  (exec 3<>"/dev/tcp/127.0.0.1/${PORT}") >/dev/null 2>&1
}

if [[ -f "$PIDFILE" ]]; then
  pid="$(cat "$PIDFILE")"
  if [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null; then
    kill -- "-$pid" 2>/dev/null || kill "$pid" 2>/dev/null || true
    for _ in $(seq 1 50); do
      kill -0 "$pid" 2>/dev/null || break
      sleep 0.1
    done
    if kill -0 "$pid" 2>/dev/null; then
      kill -KILL -- "-$pid" 2>/dev/null || kill -KILL "$pid" 2>/dev/null || true
    fi
  fi
  rm -f "$PIDFILE"
fi
for _ in $(seq 1 50); do
  port_open || { echo "[frontend.acceptance.down] PASS"; exit 0; }
  sleep 0.1
done
echo "[frontend.acceptance.down] FAIL port=$PORT remained occupied after shutdown" >&2
exit 2
