#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${ROOT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
cd "$ROOT_DIR"

source "$ROOT_DIR/scripts/common/env.sh"
source "$ROOT_DIR/scripts/common/guard_prod.sh"
guard_prod_forbid

mode="${1:-}"
case "$mode" in
  ensure|verify) ;;
  *)
    echo "usage: local_clean_entry_identity.sh {ensure|verify}" >&2
    exit 2
    ;;
esac

[[ "${COMPOSE_PROJECT_NAME:-}" == "sc-local-clean" ]] || {
  echo "LOCAL_CLEAN_ENTRY_PROJECT_INVALID" >&2
  exit 40
}
[[ "${DB_NAME:-}" == "sc_clean" ]] || {
  echo "LOCAL_CLEAN_ENTRY_DATABASE_INVALID" >&2
  exit 41
}
[[ "${ODOO_DBFILTER:-}" == "^sc_clean$" ]] || {
  echo "LOCAL_CLEAN_ENTRY_DBFILTER_INVALID" >&2
  exit 42
}

if [[ "$mode" == "ensure" ]]; then
  {
    cat "$ROOT_DIR/scripts/dev/local_clean_entry_identity_core.py"
    cat <<'PY'
import json

database = str(env.cr.dbname or "")
if database != "sc_clean":
    raise RuntimeError("local.clean entry identity refuses database %s" % database)

Alias = env["sc.platform.namespace.alias"].sudo()
Namespace = env["sc.platform.namespace"].sudo()

aliases = [
    {
        "alias": row.alias,
        "alias_kind": row.alias_kind,
        "namespace_id": row.namespace_id.namespace_id,
        "retired": bool(row.retired_at),
    }
    for row in Alias.search([("alias", "=", "clean"), ("alias_kind", "=", "path")])
]
namespaces = [
    {
        "namespace_id": row.namespace_id,
        "database_name": row.database_name,
        "lifecycle_state": row.lifecycle_state,
    }
    for row in Namespace.search([])
]
plan = plan_binding(aliases, namespaces, database)
action = plan["action"]
target_id = plan["namespace_id"]

target = Namespace.search([("namespace_id", "=", target_id)], limit=2)
if action == "create_namespace":
    if target:
        raise RuntimeError("namespace %s appeared during binding" % target_id)
    target = Namespace.create(
        {
            "namespace_id": target_id,
            "display_name": "本地干净安装租户",
            "lifecycle_state": "active",
            "database_name": database,
            "duty_key": "local_clean",
            "audience": "tenant",
        }
    )
    Alias.create(
        {
            "alias": "clean",
            "alias_kind": "path",
            "namespace_id": target.id,
            "is_primary": True,
        }
    )
elif len(target) != 1:
    raise RuntimeError("namespace %s does not resolve uniquely" % target_id)

if action == "update_database":
    target.write({"database_name": database, "lifecycle_state": "active", "audience": "tenant"})
elif action == "reassign_alias":
    Alias.search([("alias", "=", "clean"), ("alias_kind", "=", "path")]).write(
        {"namespace_id": target.id, "retired_at": False}
    )
elif action == "reactivate_alias":
    Alias.search([("alias", "=", "clean"), ("alias_kind", "=", "path")]).write(
        {"namespace_id": target.id, "retired_at": False}
    )
elif action == "create_alias":
    Alias.create(
        {
            "alias": "clean",
            "alias_kind": "path",
            "namespace_id": target.id,
            "is_primary": True,
        }
    )
elif action not in ("noop", "create_namespace"):
    raise RuntimeError("unsupported local.clean entry binding action: %s" % action)

if target.lifecycle_state != "active":
    target.write({"lifecycle_state": "active"})
if target.audience != "tenant":
    target.write({"audience": "tenant"})

env.cr.commit()
resolved = Namespace.resolve_alias("clean")
if resolved.database_name != database:
    raise RuntimeError("clean alias still resolves to %s" % resolved.database_name)

# The demo/platform bindings are product facts and must remain untouched.
demo = Namespace.resolve_alias("demo")
platform = Namespace.resolve_alias("platform")
print(
    "LOCAL_CLEAN_ENTRY_IDENTITY="
    + json.dumps(
        {
            "action": action,
            "alias": "clean",
            "namespace_id": resolved.namespace_id,
            "database_name": resolved.database_name,
            "lifecycle_state": resolved.lifecycle_state,
            "demo_database_name": demo.database_name,
            "platform_database_name": platform.database_name,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
)
PY
  } | ODOO_SHELL_RUN_ISOLATED=1 DB_NAME="sc_clean" \
      bash scripts/ops/odoo_shell_exec.sh
  exit 0
fi

namespace_output="$(
  ODOO_SHELL_RUN_ISOLATED=1 DB_NAME="sc_clean" \
    bash scripts/ops/odoo_shell_exec.sh <<'PY'
import json

namespace = env["sc.platform.namespace"].sudo().resolve_alias("clean")
print(
    "LOCAL_CLEAN_ENTRY_NAMESPACE="
    + json.dumps(
        {
            "alias": "clean",
            "namespace_id": namespace.namespace_id,
            "database_name": namespace.database_name,
            "lifecycle_state": namespace.lifecycle_state,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
)
PY
)"
namespace_json="$(printf '%s\n' "$namespace_output" | sed -n 's/^LOCAL_CLEAN_ENTRY_NAMESPACE=//p' | tail -1)"
[[ -n "$namespace_json" ]] || {
  echo "LOCAL_CLEAN_ENTRY_NAMESPACE_READBACK_MISSING" >&2
  printf '%s\n' "$namespace_output" >&2
  exit 43
}
printf '%s\n' "$namespace_json"
