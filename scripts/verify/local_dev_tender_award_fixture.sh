#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${ROOT_DIR:?ROOT_DIR is required}"
ENV_FILE="${ENV_FILE:?ENV_FILE is required}"
MODE="${P4_TENDER_AWARD_MODE:?P4_TENDER_AWARD_MODE is required}"
BATCH="${P4_TENDER_AWARD_BATCH:?P4_TENDER_AWARD_BATCH is required}"
CONFIRM="${P4_TENDER_AWARD_CONFIRM:?P4_TENDER_AWARD_CONFIRM is required}"
CANDIDATE_SHA="${CANDIDATE_GIT_HEAD:?CANDIDATE_GIT_HEAD is required}"

source "${ROOT_DIR}/scripts/common/env.sh"
source "${ROOT_DIR}/scripts/common/guard_prod.sh"
guard_prod_forbid

[[ "${COMPOSE_PROJECT_NAME:-}" == "sc-local-dev" ]] || { echo "[DENY] expected sc-local-dev" >&2; exit 2; }
[[ "${DB_NAME:-}" == "sc_dev_demo" ]] || { echo "[DENY] expected sc_dev_demo" >&2; exit 2; }
[[ "${ODOO_DBFILTER:-}" == "^sc_dev_demo$" ]] || { echo "[DENY] expected exact sc_dev_demo dbfilter" >&2; exit 2; }
[[ "${SC_ENVIRONMENT:-}" == "dev" ]] || { echo "[DENY] expected SC_ENVIRONMENT=dev" >&2; exit 2; }
[[ "${BATCH}" =~ ^[a-z0-9][a-z0-9-]{2,31}$ ]] || { echo "[DENY] invalid batch" >&2; exit 2; }
[[ "${CANDIDATE_SHA}" =~ ^[0-9a-f]{40}$ ]] || { echo "[DENY] candidate SHA must be full" >&2; exit 2; }
[[ "${MODE}" =~ ^(inspect|dry-run|prepare|cleanup)$ ]] || { echo "[DENY] invalid mode" >&2; exit 2; }
case "${MODE}" in
  inspect) [[ "${CONFIRM}" == "INSPECT" ]] || { echo "[DENY] inspect requires INSPECT" >&2; exit 2; } ;;
  dry-run) [[ "${CONFIRM}" == "DRY_RUN" ]] || { echo "[DENY] dry-run requires DRY_RUN" >&2; exit 2; } ;;
  prepare) [[ "${CONFIRM}" == "PREPARE" ]] || { echo "[DENY] prepare requires PREPARE" >&2; exit 2; } ;;
  cleanup) [[ "${CONFIRM}" == "CLEANUP" ]] || { echo "[DENY] cleanup requires CLEANUP" >&2; exit 2; } ;;
esac

P4_TENDER_AWARD_BATCH="${BATCH}"
P4_TENDER_AWARD_CONFIRM="${CONFIRM}"
export SC_ENVIRONMENT DB_NAME ODOO_DBFILTER P4_TENDER_AWARD_BATCH P4_TENDER_AWARD_CONFIRM
export CANDIDATE_GIT_HEAD="${CANDIDATE_SHA}"
export P4_TENDER_AWARD_MODE="${MODE}"
bash "${ROOT_DIR}/scripts/ops/odoo_shell_exec.sh" < "${ROOT_DIR}/scripts/verify/local_dev_tender_award_fixture.py"
