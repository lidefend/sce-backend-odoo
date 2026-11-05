#!/usr/bin/env bash
# Exact disposable writer identity shared by governed upgrade and snapshot.
acceptance_attempt_args=()
if [[ -n "${SC_ACCEPTANCE_UPGRADE_CONTAINER_NAME:-}" || -n "${SC_ACCEPTANCE_MODULE_UPGRADE_ID:-}" ]]; then
  [[ "${SC_FRONTEND_ACCEPTANCE_RUNTIME_ENTRY:-}" == operation_entry_v1 \
    && "${SC_ACCEPTANCE_RUNTIME_PROFILE:-}" == local \
    && "${SC_ACCEPTANCE_MODULE_UPGRADE_ID:-}" =~ ^[0-9a-f]{32}$ \
    && "${SC_ACCEPTANCE_UPGRADE_CONTAINER_NAME:-}" == "${COMPOSE_PROJECT_NAME}-module-upgrade-${SC_ACCEPTANCE_MODULE_UPGRADE_ID}" ]] || {
    echo "DENY invalid governed module upgrade attempt identity" >&2; exit 2;
  }
  acceptance_attempt_args=(--name "$SC_ACCEPTANCE_UPGRADE_CONTAINER_NAME"
    --label "sce.acceptance.module-upgrade=$SC_ACCEPTANCE_MODULE_UPGRADE_ID")
fi

