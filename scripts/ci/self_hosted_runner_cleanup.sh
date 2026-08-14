#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "$0")/../.." && pwd)"
project="${CI_PROJECT_NAME:-}"
workspace="${GITHUB_WORKSPACE:-}"
runner_temp="${RUNNER_TEMP:-}"
run_id="${GITHUB_RUN_ID:-}"

if [[ ! "${run_id}" =~ ^[0-9]+$ ]] || { [[ "${project}" != "sc-prof-${run_id}" ]] && [[ "${project}" != "sc-fe-release-${run_id}" ]]; }; then
  echo "[self_hosted_cleanup] invalid project scope" >&2
  exit 2
fi
if [[ "${GITHUB_ACTIONS:-}" != "true" || "${GITHUB_REPOSITORY:-}" != "lidefend/sce-backend-odoo" ]]; then
  echo "[self_hosted_cleanup] invalid GitHub Actions identity" >&2
  exit 2
fi
if [[ "$(readlink -f "${workspace:-/nonexistent}")" != "$(readlink -f "$root_dir")" ]]; then
  echo "[self_hosted_cleanup] invalid workspace scope" >&2
  exit 2
fi
resolved_runner_temp="$(readlink -f "${runner_temp:-/nonexistent}")"
if [[ ! -d "$resolved_runner_temp" || "$(basename "$resolved_runner_temp")" != "_temp" || "$resolved_runner_temp" == "/" || "$resolved_runner_temp" == "${HOME:-}" ]]; then
  echo "[self_hosted_cleanup] invalid runner temp scope" >&2
  exit 2
fi

if command -v docker >/dev/null 2>&1; then
  docker compose -p "${project}" down -v --remove-orphans >/dev/null 2>&1 || true
  docker ps -aq --filter "label=com.docker.compose.project=${project}" |
    xargs -r docker rm -f >/dev/null 2>&1 || true
  docker volume ls -q --filter "label=com.docker.compose.project=${project}" |
    xargs -r docker volume rm -f >/dev/null 2>&1 || true
  docker network ls -q --filter "label=com.docker.compose.project=${project}" |
    xargs -r docker network rm >/dev/null 2>&1 || true
fi

if [[ -n "${run_id}" ]]; then
  find "${resolved_runner_temp}" -mindepth 1 -maxdepth 1 \
    -name "sce-ci-${run_id}-*" -exec rm -rf -- {} +
fi

find "${workspace}" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
echo "[self_hosted_cleanup] PASS project=${project}"
