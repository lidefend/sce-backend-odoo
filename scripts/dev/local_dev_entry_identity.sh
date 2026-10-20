#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${ROOT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
cd "$ROOT_DIR"

source "$ROOT_DIR/scripts/common/env.sh"

mode="${1:-}"
case "$mode" in
  ensure|verify) ;;
  *)
    echo "usage: local_dev_entry_identity.sh {ensure|verify}" >&2
    exit 2
    ;;
esac

[[ "${COMPOSE_PROJECT_NAME:-}" == "sc-local-dev" ]] || {
  echo "LOCAL_DEV_ENTRY_PROJECT_INVALID" >&2
  exit 40
}
[[ "${DB_NAME:-}" == "sc_dev_demo" ]] || {
  echo "LOCAL_DEV_ENTRY_DATABASE_INVALID" >&2
  exit 41
}
[[ "${ODOO_DBFILTER:-}" == "^sc_dev_demo$" ]] || {
  echo "LOCAL_DEV_ENTRY_DBFILTER_INVALID" >&2
  exit 42
}

if [[ "$mode" == "ensure" ]]; then
  {
    cat "$ROOT_DIR/scripts/dev/local_dev_entry_identity_core.py"
    cat <<'PY'
import json

database = str(env.cr.dbname or "")
if database != "sc_dev_demo":
    raise RuntimeError("local.dev entry identity refuses database %s" % database)

Alias = env["sc.platform.namespace.alias"].sudo()
Namespace = env["sc.platform.namespace"].sudo()

aliases = [
    {
        "alias": row.alias,
        "alias_kind": row.alias_kind,
        "namespace_id": row.namespace_id.namespace_id,
        "retired": bool(row.retired_at),
    }
    for row in Alias.search([("alias", "=", "demo"), ("alias_kind", "=", "path")])
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
            "display_name": "本地开发租户",
            "lifecycle_state": "active",
            "database_name": database,
            "duty_key": "local_dev",
            "audience": "tenant",
        }
    )
elif len(target) != 1:
    raise RuntimeError("namespace %s does not resolve uniquely" % target_id)

if action == "update_database":
    target.write({"database_name": database, "lifecycle_state": "active", "audience": "tenant"})
elif action == "reassign_alias":
    Alias.search([("alias", "=", "demo"), ("alias_kind", "=", "path")]).write(
        {"namespace_id": target.id, "retired_at": False}
    )
elif action == "reactivate_alias":
    Alias.search([("alias", "=", "demo"), ("alias_kind", "=", "path")]).write(
        {"namespace_id": target.id, "retired_at": False}
    )
elif action == "create_alias":
    Alias.create(
        {
            "alias": "demo",
            "alias_kind": "path",
            "namespace_id": target.id,
            "is_primary": True,
        }
    )
elif action != "noop":
    raise RuntimeError("unsupported local.dev entry binding action: %s" % action)

if target.lifecycle_state != "active":
    target.write({"lifecycle_state": "active"})
if target.audience != "tenant":
    target.write({"audience": "tenant"})

env.cr.commit()
resolved = Namespace.resolve_alias("demo")
if resolved.database_name != database:
    raise RuntimeError("demo alias still resolves to %s" % resolved.database_name)
print(
    "LOCAL_DEV_ENTRY_IDENTITY="
    + json.dumps(
        {
            "action": action,
            "alias": "demo",
            "namespace_id": resolved.namespace_id,
            "database_name": resolved.database_name,
            "lifecycle_state": resolved.lifecycle_state,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
)
PY
  } | ENV=dev ENV_FILE="${ENV_FILE:-.env.dev}" DB_NAME="$DB_NAME" \
      bash scripts/ops/odoo_shell_exec.sh
  exit 0
fi

namespace_output="$(
  ENV=dev ENV_FILE="${ENV_FILE:-.env.dev}" DB_NAME="$DB_NAME" \
    bash scripts/ops/odoo_shell_exec.sh <<'PY'
import json

namespace = env["sc.platform.namespace"].sudo().resolve_alias("demo")
print(
    "LOCAL_DEV_ENTRY_NAMESPACE="
    + json.dumps(
        {
            "alias": "demo",
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
namespace_json="$(printf '%s\n' "$namespace_output" | sed -n 's/^LOCAL_DEV_ENTRY_NAMESPACE=//p' | tail -1)"
[[ -n "$namespace_json" ]] || {
  echo "LOCAL_DEV_ENTRY_NAMESPACE_READBACK_MISSING" >&2
  printf '%s\n' "$namespace_output" >&2
  exit 43
}

base_url="http://127.0.0.1:${NGINX_PORT:-18081}"
runtime_body="$(python3 - "$base_url" <<'PY'
import sys
import urllib.error
import urllib.request

url = sys.argv[1].rstrip("/") + "/t/demo/api/runtime-version"
try:
    with urllib.request.urlopen(url, timeout=10) as response:
        print(response.read().decode("utf-8"))
except urllib.error.HTTPError as exc:
    body = exc.read().decode("utf-8", errors="replace")
    raise SystemExit(
        "LOCAL_DEV_ENTRY_HTTP_ERROR status=%s body=%s" % (exc.code, body[:300])
    )
except Exception as exc:
    raise SystemExit("LOCAL_DEV_ENTRY_HTTP_UNREACHABLE url=%s error=%s" % (url, exc))
PY
)" || {
  echo "LOCAL_DEV_ENTRY_HTTP_UNREACHABLE url=${base_url}/t/demo/api/runtime-version" >&2
  exit 44
}

python3 - "$namespace_json" "$runtime_body" <<'PY'
import json
import sys

namespace = json.loads(sys.argv[1])
try:
    runtime = json.loads(sys.argv[2])
except Exception:
    raise SystemExit("LOCAL_DEV_ENTRY_HTTP_NON_JSON: " + sys.argv[2][:300])

def find_database(value):
    if isinstance(value, dict):
        for key in ("database", "db", "database_name", "served_database"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate:
                return candidate
        for candidate in value.values():
            found = find_database(candidate)
            if found:
                return found
    elif isinstance(value, list):
        for candidate in value:
            found = find_database(candidate)
            if found:
                return found
    return ""

served = find_database(runtime)
if namespace.get("database_name") != "sc_dev_demo":
    raise SystemExit(
        "LOCAL_DEV_ENTRY_NAMESPACE_DATABASE_MISMATCH: namespace=%s"
        % namespace.get("database_name")
    )
if served != "sc_dev_demo":
    raise SystemExit(
        "LOCAL_DEV_ENTRY_SERVED_DATABASE_MISMATCH: served=%s namespace=%s"
        % (served or "<missing>", namespace.get("database_name"))
    )
print(
    "[local.dev.entry_identity] PASS alias=demo namespace=%s database=%s"
    % (namespace.get("namespace_id"), served)
)
PY
