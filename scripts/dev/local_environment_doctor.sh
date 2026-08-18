#!/usr/bin/env bash
set -euo pipefail

: "${ROOT_DIR:?ROOT_DIR is required}"
profile="${1:-}"
source "${ROOT_DIR}/scripts/common/env.sh"
source "${ROOT_DIR}/scripts/common/compose.sh"

case "${profile}" in
  persistent)
    [[ "${COMPOSE_PROJECT_NAME}" == "sc-local-dev" \
      && "${DB_NAME}" == "sc_dev_demo" \
      && "${ODOO_DBFILTER}" == '^sc_dev_demo$' \
      && "${DB_DATA}" == "sc_local_dev_db_data" \
      && "${REDIS_DATA}" == "sc_local_dev_redis_data" \
      && "${ODOO_DATA}" == "sc_local_dev_odoo_data" ]] || {
        echo "[local.env.doctor] DENY persistent identity mismatch" >&2
        exit 2
      }
    ;;
  sample)
    [[ "${TECHNICAL_SAMPLE_DATABASE:-0}" == "1" \
      && "${COMPOSE_PROJECT_NAME}" == "sc-local-sample" \
      && "${DB_NAME}" == "sc_dev_sample" \
      && "${ODOO_DBFILTER}" == '^sc_dev_sample$' \
      && "${DB_DATA}" == "sc_local_sample_db_data" \
      && "${REDIS_DATA}" == "sc_local_sample_redis_data" \
      && "${ODOO_DATA}" == "sc_local_sample_odoo_data" ]] || {
        echo "[local.env.doctor] DENY sample identity mismatch" >&2
        exit 2
      }
    ;;
  clean)
    [[ "${ISOLATED_REHEARSAL_DATABASE:-0}" == "1" \
      && "${COMPOSE_PROJECT_NAME}" == "sc-local-clean" \
      && "${DB_NAME}" == "sc_clean" \
      && "${ODOO_DBFILTER}" == '^sc_clean$' \
      && "${DB_DATA}" == "sc_local_clean_db_data" \
      && "${REDIS_DATA}" == "sc_local_clean_redis_data" \
      && "${ODOO_DATA}" == "sc_local_clean_odoo_data" ]] || {
        echo "[local.env.doctor] DENY clean identity mismatch" >&2
        exit 2
      }
    ;;
  *)
    echo "usage: $0 persistent|sample|clean" >&2
    exit 2
    ;;
esac

echo "[local.env.doctor] profile=${profile} project=${COMPOSE_PROJECT_NAME} db=${DB_NAME} dbfilter=${ODOO_DBFILTER}"
compose_dev ps -a
echo "[local.env.doctor] bounded service logs follow; environment values are not printed"
compose_dev logs --no-color --tail=120 db redis odoo nginx
if [[ "${profile}" == "persistent" ]] && docker volume inspect "${ODOO_DATA}" >/dev/null 2>&1; then
  echo "[local.env.doctor] bounded demo installation log follows"
  docker run --rm -v "${ODOO_DATA}:/data:ro" alpine:3.20 \
    sh -ceu '
      if [ -f /data/demo_install.log ]; then tail -n 80 /data/demo_install.log; else echo "demo installation stdout log is absent"; fi
      if [ -f /data/logs/odoo.log ]; then tail -n 200 /data/logs/odoo.log; else echo "Odoo runtime log is absent"; fi
    '
fi
