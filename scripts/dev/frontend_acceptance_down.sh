#!/usr/bin/env bash
set -euo pipefail
PIDFILE="${FRONTEND_ACCEPTANCE_PIDFILE:-/tmp/sc-frontend-acceptance.pid}"
if [[ -f "$PIDFILE" ]]; then
  pid="$(cat "$PIDFILE")"
  if [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null; then
    kill -- "-$pid" 2>/dev/null || kill "$pid" 2>/dev/null || true
  fi
  rm -f "$PIDFILE"
fi
echo "[frontend.acceptance.down] PASS"
