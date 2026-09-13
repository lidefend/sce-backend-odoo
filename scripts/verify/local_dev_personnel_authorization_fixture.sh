#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${ROOT_DIR:?ROOT_DIR is required}"
ENV_FILE="${ENV_FILE:?ENV_FILE is required}"
MODE="${P4_PERSONNEL_AUTH_MODE:?P4_PERSONNEL_AUTH_MODE is required}"
BATCH="${P4_PERSONNEL_AUTH_BATCH:?P4_PERSONNEL_AUTH_BATCH is required}"
CONFIRM="${P4_PERSONNEL_AUTH_CONFIRM:?P4_PERSONNEL_AUTH_CONFIRM is required}"
CANDIDATE_SHA="${CANDIDATE_GIT_HEAD:?CANDIDATE_GIT_HEAD is required}"

source "${ROOT_DIR}/scripts/common/env.sh"
source "${ROOT_DIR}/scripts/common/guard_prod.sh"
guard_prod_forbid

[[ "${COMPOSE_PROJECT_NAME:-}" == "sc-local-dev" ]] || { echo "[DENY] expected sc-local-dev" >&2; exit 2; }
[[ "${DB_NAME:-}" == "sc_dev_demo" ]] || { echo "[DENY] expected sc_dev_demo" >&2; exit 2; }
[[ "${ODOO_DBFILTER:-}" == "^sc_dev_demo$" ]] || { echo "[DENY] expected exact sc_dev_demo dbfilter" >&2; exit 2; }
[[ "${SC_ENVIRONMENT:-}" == "dev" ]] || { echo "[DENY] expected SC_ENVIRONMENT=dev" >&2; exit 2; }
[[ "${MODE}" =~ ^(inspect|dry-run|prepare|retire)$ ]] || { echo "[DENY] invalid mode" >&2; exit 2; }
case "${MODE}" in
  inspect) [[ "${CONFIRM}" == "INSPECT" ]] || { echo "[DENY] inspect requires INSPECT" >&2; exit 2; } ;;
  dry-run) [[ "${CONFIRM}" == "DRY_RUN" ]] || { echo "[DENY] dry-run requires DRY_RUN" >&2; exit 2; } ;;
  prepare) [[ "${CONFIRM}" == "PREPARE" ]] || { echo "[DENY] prepare requires PREPARE" >&2; exit 2; } ;;
  retire) [[ "${CONFIRM}" == "RETIRE" ]] || { echo "[DENY] retire requires RETIRE" >&2; exit 2; } ;;
esac

export SC_ENVIRONMENT DB_NAME ODOO_DBFILTER P4_PERSONNEL_AUTH_BATCH P4_PERSONNEL_AUTH_CONFIRM
export CANDIDATE_GIT_HEAD="${CANDIDATE_SHA}"
export P4_PERSONNEL_AUTH_MODE="${MODE}"
bash "${ROOT_DIR}/scripts/ops/odoo_shell_exec.sh" < "${ROOT_DIR}/scripts/verify/local_dev_personnel_authorization_fixture.py"
