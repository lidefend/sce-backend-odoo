#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${ROOT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
export ROOT_DIR

source "$ROOT_DIR/scripts/common/frontend_acceptance_guard.sh"
guard_frontend_acceptance_scope
acquire_frontend_acceptance_lock lifecycle

source "$ROOT_DIR/scripts/common/env.sh"
source "$ROOT_DIR/scripts/common/guard_prod.sh"
guard_prod_forbid

# The isolated acceptance runtime is its own entry: the static preview proxy
# stamps the same namespace the database registers here, and Odoo verifies the
# shared secret/route version from ir.config_parameter.  This keeps Batch C's
# "entry decides the database" contract active in acceptance instead of
# re-enabling a database-hint bypass for tests.
source "$ROOT_DIR/config/acceptance/isolated_entry_identity.v1.env"
export SC_ENTRY_NAMESPACE SC_ENTRY_AUDIENCE SC_ENTRY_SHARED_SECRET SC_ENTRY_ROUTE_VERSION

export DB_NAME SC_ENVIRONMENT SC_ALLOW_DEMO_DATA

# shellcheck source=../common/frontend_acceptance_make_identity.sh
source "$ROOT_DIR/scripts/common/frontend_acceptance_make_identity.sh"

create_output="$(frontend_acceptance_make db.create 2>&1)"
printf '%s\n' "$create_output"
if grep -Fqx "[db] created: ${DB_NAME}" <<<"$create_output"; then
  database_created=1
elif grep -Fqx "[db] exists: ${DB_NAME}" <<<"$create_output"; then
  database_created=0
else
  echo "[frontend.acceptance.ensure] DENY unexpected db.create result for ${DB_NAME}" >&2
  exit 2
fi
frontend_acceptance_make mod.install \
  MODULE=smart_construction_bootstrap,smart_construction_bundle,smart_construction_seed,smart_construction_acceptance_fixture \
  DB_NAME="$DB_NAME"
if [[ "$database_created" == "1" ]]; then
  # This database was created in this run and installed from the exact current
  # source. Prove the clean install completed the same baselines before
  # skipping the two persistent-database upgrade passes.
  ODOO_SHELL_RUN_ISOLATED=1 DB_NAME="$DB_NAME" bash scripts/ops/odoo_shell_exec.sh <<'PY'
required_modules = (
    "smart_core",
    "smart_construction_core",
    "smart_construction_bootstrap",
    "smart_construction_bundle",
    "smart_construction_seed",
    "smart_construction_acceptance_fixture",
)
from odoo.modules.module import load_information_from_description_file

rows = {
    row.name: row
    for row in env["ir.module.module"].sudo().search([
        ("name", "in", list(required_modules)),
    ])
}
for name in required_modules:
    module = rows.get(name)
    if not module or module.state != "installed":
        raise RuntimeError("fresh acceptance module is not installed: %s" % name)
    current = str(module.latest_version or "")
    source = str(load_information_from_description_file(name).get("version") or "")
    if not source or current != source:
        raise RuntimeError(
            "fresh acceptance module version drifted: %s current=%s source=%s"
            % (name, current, source)
        )

required_xmlids = (
    "smart_core.namespace_platform",
    "smart_construction_bundle.param_construction_bundle_product_key",
    "smart_construction_seed.seed_dict_contract_type_out",
)
missing_xmlids = [
    xmlid
    for xmlid in required_xmlids
    if env.ref(xmlid, raise_if_not_found=False) is None
]
if missing_xmlids:
    raise RuntimeError("fresh acceptance XMLIDs are missing: %s" % ",".join(missing_xmlids))

product_keys = env["ir.config_parameter"].sudo().get_param(
    "smart_core.release_operator.product_base_keys", ""
)
if "construction" not in [value.strip() for value in product_keys.split(",") if value.strip()]:
    raise RuntimeError("fresh acceptance product baseline is missing construction")
print(
    "[frontend.acceptance.fresh-install] PASS modules=%s xmlids=%s product_base_keys=%s"
    % (",".join(required_modules), ",".join(required_xmlids), product_keys)
)
PY
else
  # A persistent acceptance database may predate the current source. Refresh
  # the two governed product baselines before fixture reset and acceptance.
  frontend_acceptance_make mod.upgrade \
    MODULE=smart_core \
    CODEX_NEED_UPGRADE=1 \
    CODEX_MODULES=smart_core,smart_construction_core
  frontend_acceptance_make mod.upgrade \
    MODULE=smart_construction_core \
    CODEX_NEED_UPGRADE=1 \
    CODEX_MODULES=smart_core,smart_construction_core
fi
ODOO_SHELL_RUN_ISOLATED=1 DB_NAME="$DB_NAME" bash scripts/ops/odoo_shell_exec.sh <<'PY'
import hashlib
import os

database = env.cr.dbname
namespace = env["sc.platform.namespace"].sudo().search(
    [("database_name", "=", database)], limit=1
)
if not namespace:
    namespace = env["sc.platform.namespace"].sudo().create({
        "namespace_id": "ns_" + hashlib.sha256(database.encode("utf-8")).hexdigest()[:12],
        "display_name": "隔离验收租户",
        "lifecycle_state": "active",
        "database_name": database,
        "duty_key": "frontend_acceptance",
        "audience": os.environ["SC_ENTRY_AUDIENCE"],
    })
if str(namespace.audience) != os.environ["SC_ENTRY_AUDIENCE"]:
    raise RuntimeError("acceptance namespace audience drifted")
alias = env["sc.platform.namespace.alias"].sudo().search([
    ("alias", "=", os.environ["SC_ENTRY_NAMESPACE"]),
    ("alias_kind", "=", "path"),
], limit=1)
if not alias:
    env["sc.platform.namespace.alias"].sudo().create({
        "alias": os.environ["SC_ENTRY_NAMESPACE"],
        "alias_kind": "path",
        "namespace_id": namespace.id,
        "is_primary": True,
    })
elif alias.namespace_id.id != namespace.id:
    raise RuntimeError("acceptance alias is bound to another namespace")
params = env["ir.config_parameter"].sudo()
params.set_param("sc.entry.shared_secret", os.environ["SC_ENTRY_SHARED_SECRET"])
params.set_param("sc.entry.route_version", os.environ["SC_ENTRY_ROUTE_VERSION"])
env.cr.commit()
print("[frontend.acceptance.entry] PASS namespace=%s alias=%s db=%s" % (
    namespace.namespace_id, os.environ["SC_ENTRY_NAMESPACE"], database,
))
PY
ODOO_SHELL_RUN_ISOLATED=1 DB_NAME="$DB_NAME" bash scripts/ops/odoo_shell_exec.sh <<'PY'
param = env['ir.config_parameter'].sudo().get_param('smart_core.release_operator.product_base_keys', '')
states = {
    row.name: row.state
    for row in env['ir.module.module'].sudo().search([
        ('name', 'in', [
            'smart_construction_bundle',
            'smart_construction_seed',
            'smart_construction_acceptance_fixture',
            'smart_construction_demo',
        ])
    ])
}
if states.get('smart_construction_bundle') != 'installed' or 'construction' not in [v.strip() for v in param.split(',') if v.strip()]:
    raise RuntimeError('acceptance product baseline is not initialized')
if states.get('smart_construction_seed') != 'installed':
    raise RuntimeError('acceptance product seed is not installed')
if states.get('smart_construction_acceptance_fixture') != 'installed':
    raise RuntimeError('acceptance fixture carrier is not installed')
if states.get('smart_construction_demo') == 'installed':
    raise RuntimeError('acceptance module set must not install smart_construction_demo')
print('[frontend.acceptance.ensure] product_base_keys=%s states=%s' % (param, states))
PY

echo "[db.frontend.acceptance.ensure] PASS db=${DB_NAME}"
