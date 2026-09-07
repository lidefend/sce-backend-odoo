#!/usr/bin/env bash
set -euo pipefail

log() { printf '[%s] %s\n' "$(date +'%H:%M:%S')" "$*"; }

# ---- defaults to support manual sourcing (without Makefile RUN_ENV) ----
: "${COMPOSE_BIN:=}"
: "${COMPOSE_PROJECT_NAME:=sc-backend-odoo}"
: "${PROJECT:=${COMPOSE_PROJECT_NAME}}"
: "${COMPOSE_FILE_BASE:=docker-compose.yml}"
: "${COMPOSE_FILES:=-f ${COMPOSE_FILE_BASE}}"

# 把裸 tag 限定到目标模块；保留已经符合 Odoo
# [-][tag][/module][:class][.method] 语法的 selector。
normalize_test_tags() {
  local module="$1"
  local raw="${2:-}"
  raw="${raw// /}"          # 去空格
  raw="${raw#,}"            # 去头逗号
  raw="${raw%,}"            # 去尾逗号
  [[ -z "$raw" ]] && { echo ""; return 0; }

  IFS=',' read -r -a parts <<< "$raw"
  local out=()
  local p
  for p in "${parts[@]}"; do
    [[ -z "$p" ]] && continue
    if [[ "$p" == /* || "$p" == */* ]]; then
      out+=("$p")
    elif [[ "$p" == :* || "$p" == .* ]]; then
      out+=("/${module}${p}")
    else
      if [[ "$p" == -* ]]; then
        out+=("-${p#-}/${module}")
      else
        out+=("${p}/${module}")
      fi
    fi
  done

  local joined
  joined="$(IFS=','; echo "${out[*]}")"
  echo "$joined"
}

compose() {
  local cmd=()
  local proj="${PROJECT:-${COMPOSE_PROJECT_NAME:-sc-backend-odoo}}"
  local files="${COMPOSE_FILES:--f docker-compose.yml}"
  if [[ -n "${COMPOSE_BIN:-}" ]]; then
    read -r -a cmd <<<"${COMPOSE_BIN}"
  elif command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    cmd=(docker compose)
  elif command -v docker-compose >/dev/null 2>&1 && docker-compose version >/dev/null 2>&1; then
    cmd=(docker-compose)
  else
    echo "[FATAL] docker compose or docker-compose not available" >&2
    exit 127
  fi
  # preserve arguments (including embedded spaces/newlines)
  # shellcheck disable=SC2086
  "${cmd[@]}" -p "${proj}" ${files} "$@"
}
