#!/usr/bin/env bash

frontend_acceptance_make() {
  local required
  for required in \
    COMPOSE_PROJECT_NAME ENV_FILE DB_USER DB_PASSWORD DB_NAME \
    ODOO_DBFILTER ODOO_PORT DB_DATA REDIS_DATA ODOO_DATA \
    SC_ENVIRONMENT SC_ALLOW_DEMO_DATA; do
    [[ -n "${!required:-}" ]] || {
      echo "[acceptance.make] DENY missing managed identity: $required" >&2
      return 2
    }
  done
  [[ -z "${ODOO_DB+x}" || "$ODOO_DB" == "$DB_NAME" ]] || {
    echo "[acceptance.make] DENY ODOO_DB alias differs from DB_NAME" >&2
    return 2
  }
  [[ -z "${LIST_DB+x}" || "$LIST_DB" == "false" ]] || {
    echo "[acceptance.make] DENY LIST_DB alias must remain false" >&2
    return 2
  }
  [[ "$DB_NAME" == "sc_frontend_acceptance" \
    && "$ODOO_DBFILTER" == "^${DB_NAME}$" \
    && "$SC_ENVIRONMENT" == "acceptance" \
    && "$SC_ALLOW_DEMO_DATA" == "1" ]] || {
    echo "[acceptance.make] DENY managed acceptance identity drift" >&2
    return 2
  }
  make --no-print-directory \
    "PROJECT=$COMPOSE_PROJECT_NAME" \
    "COMPOSE_PROJECT_NAME=$COMPOSE_PROJECT_NAME" \
    "ENV_FILE=$ENV_FILE" \
    "DB_USER=$DB_USER" \
    "DB_PASSWORD=$DB_PASSWORD" \
    "DB_NAME=$DB_NAME" \
    "DB=$DB_NAME" \
    "ODOO_DB=$DB_NAME" \
    "ODOO_DBFILTER=$ODOO_DBFILTER" \
    "ODOO_PORT=$ODOO_PORT" \
    "DB_DATA=$DB_DATA" \
    "REDIS_DATA=$REDIS_DATA" \
    "ODOO_DATA=$ODOO_DATA" \
    "LIST_DB=false" \
    "SC_ENVIRONMENT=$SC_ENVIRONMENT" \
    "SC_ALLOW_DEMO_DATA=$SC_ALLOW_DEMO_DATA" \
    "$@"
}
