#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "$0")/../.." && pwd)"
project="${CI_PROJECT_NAME:-}"
workspace="${GITHUB_WORKSPACE:-}"
runner_temp="${RUNNER_TEMP:-}"
run_id="${GITHUB_RUN_ID:-}"
run_attempt="${GITHUB_RUN_ATTEMPT:-}"
frontend_mode="${FRONTEND_MODE:-}"
allow_docker_cleanup=1

if [[ "${GITHUB_ACTIONS:-}" != "true" || "${GITHUB_REPOSITORY:-}" != "lidefend/sce-backend-odoo" ]]; then
  echo "[self_hosted_cleanup] invalid GitHub Actions identity" >&2
  exit 2
fi
if [[ ! "${run_id}" =~ ^[0-9]+$ || ! "${run_attempt}" =~ ^[1-9][0-9]*$ ]]; then
  echo "[self_hosted_cleanup] invalid run identity" >&2
  exit 2
fi
if [[ "${project}" != "sc-prof-${run_id}" && "${project}" != "sc-fe-release-${run_id}-${run_attempt}" ]]; then
  echo "[self_hosted_cleanup] invalid project scope" >&2
  exit 2
fi
if [[ "$(readlink -f "${workspace:-/nonexistent}")" != "$(readlink -f "$root_dir")" ]]; then
  echo "[self_hosted_cleanup] invalid workspace scope" >&2
  exit 2
fi
resolved_runner_temp="$(readlink -f "${runner_temp:-/nonexistent}")"
if [[ ! -d "$resolved_runner_temp" || "$(basename "$resolved_runner_temp")" != "_temp" \
  || "$resolved_runner_temp" == "/" || "$resolved_runner_temp" == "${HOME:-}" ]]; then
  echo "[self_hosted_cleanup] invalid runner temp scope" >&2
  exit 2
fi

if [[ "$project" == sc-fe-release-* ]]; then
  if [[ "$frontend_mode" == "full" ]]; then
    source "$root_dir/scripts/common/frontend_release_ci_identity.sh"
    verify_frozen_frontend_release_ci_identity "$root_dir"
    validate_frozen_frontend_release_ci_resources "$root_dir" optional
  else
    [[ "$frontend_mode" == "standard" || "$frontend_mode" == "skip" || -z "$frontend_mode" ]] || {
      echo "[self_hosted_cleanup] invalid frontend lane" >&2; exit 2;
    }
    if command -v docker >/dev/null 2>&1; then
      [[ -z "$(docker ps -aq --filter "label=com.docker.compose.project=${project}")" \
        && -z "$(docker volume ls -q --filter "label=com.docker.compose.project=${project}")" \
        && -z "$(docker network ls -q --filter "label=com.docker.compose.project=${project}")" ]] || {
        echo "[self_hosted_cleanup] unfrozen frontend lane owns resources" >&2; exit 2;
      }
    fi
    allow_docker_cleanup=0
  fi
fi

if [[ "$allow_docker_cleanup" == "1" ]] && command -v docker >/dev/null 2>&1; then
  docker compose -p "${project}" down -v --remove-orphans >/dev/null 2>&1 || true
  docker ps -aq --filter "label=com.docker.compose.project=${project}" |
    xargs -r docker rm -f >/dev/null 2>&1 || true
  docker volume ls -q --filter "label=com.docker.compose.project=${project}" |
    xargs -r docker volume rm -f >/dev/null 2>&1 || true
  docker network ls -q --filter "label=com.docker.compose.project=${project}" |
    xargs -r docker network rm >/dev/null 2>&1 || true
fi

if [[ "$project" == sc-fe-release-* ]]; then
  find "${resolved_runner_temp}" -mindepth 1 -maxdepth 1 \
    -name "sce-ci-${run_id}-${run_attempt}-*" -exec rm -rf -- {} +
else
  find "${resolved_runner_temp}" -mindepth 1 -maxdepth 1 \
    -name "sce-ci-${run_id}-*" -exec rm -rf -- {} +
fi

find "${workspace}" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
echo "[self_hosted_cleanup] PASS project=${project}"
