#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${ROOT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
export ROOT_DIR

source "$ROOT_DIR/scripts/common/env.sh"
source "$ROOT_DIR/scripts/common/guard_prod.sh"
guard_prod_forbid

mode="${1:-}"
case "$mode" in
  ensure|verify|revoke|revoke_deactivate) ;;
  *) echo "usage: local_clean_dependency_fixture.sh {ensure|verify|revoke|revoke_deactivate}" >&2; exit 2 ;;
esac

if [[ "${ENV:-}" != "dev" || "${DB_NAME:-}" != "sc_clean" || "${ISOLATED_REHEARSAL_DATABASE:-0}" != "1" ]]; then
  echo "[DENY] local.clean dependency fixture requires dev / sc_clean / isolated rehearsal" >&2
  exit 3
fi

if [[ "$mode" == "ensure" && -z "${SC_DEPENDENCY_FIXTURE_PASSWORD:-}" ]]; then
  echo "[DENY] SC_DEPENDENCY_FIXTURE_PASSWORD is required" >&2
  exit 24
fi

export ROLE_DEP_FIXTURE_MODE="$mode"
ODOO_SHELL_RUN_ISOLATED=1 DB_NAME="sc_clean" bash scripts/ops/odoo_shell_exec.sh <<'PY'
import json
import os

mode = os.environ.get("ROLE_DEP_FIXTURE_MODE")
login = "fixture_role_finance_dependency_creator"
group_name = "Fixture Finance Dependency Creator"
models = ("project.project", "res.partner")

Group = env["res.groups"].sudo()
group = Group.search([("name", "=", group_name)], limit=1)
User = env["res.users"].sudo()
user = User.search([("login", "=", login)], limit=1)

if mode == "ensure":
    if not group:
        cat = env["ir.module.category"].sudo().search([("name", "=", "Hidden")], limit=1)
        if not cat:
            cat = env["ir.module.category"].sudo().create({"name": "Hidden"})
        group = Group.create({
            "name": group_name,
            "category_id": cat.id,
            "implied_ids": [(6, 0, [env.ref("base.group_user").id])],
        })
    password = os.environ["SC_DEPENDENCY_FIXTURE_PASSWORD"]
    company = env.ref("base.main_company", raise_if_not_found=False)
    values = {
        "login": login,
        "name": "P4 Finance Dependency Creator",
        "active": True,
        "password": password,
        "groups_id": [(6, 0, [env.ref("base.group_user").id, group.id])],
    }
    if company:
        values["company_id"] = company.id
        values["company_ids"] = [(6, 0, [company.id])]
    if user:
        user.write(values)
    else:
        user = User.create(values)

    Access = env["ir.model.access"].sudo()
    for model_name in models:
        model = env["ir.model"].sudo().search([("model", "=", model_name)], limit=1)
        if not model:
            raise RuntimeError("missing model %s" % model_name)
        row = Access.search([("model_id", "=", model.id), ("group_id", "=", group.id)], limit=1)
        vals = {
            "name": "fixture_dependency_creator_%s" % model_name.replace(".", "_"),
            "model_id": model.id,
            "group_id": group.id,
            "perm_read": True,
            "perm_write": False,
            "perm_create": True,
            "perm_unlink": False,
            "active": True,
        }
        if row:
            row.write(vals)
        else:
            Access.create(vals)
    env.cr.commit()

elif mode == "revoke":
    if not group or not user:
        raise RuntimeError("dependency fixture role is not present")
    Access = env["ir.model.access"].sudo()
    for model_name in models:
        model = env["ir.model"].sudo().search([("model", "=", model_name)], limit=1)
        Access.search([("model_id", "=", model.id), ("group_id", "=", group.id)]).write({"perm_create": False})
    env.cr.commit()

elif mode == "revoke_deactivate":
    if not group or not user:
        raise RuntimeError("dependency fixture role is not present")
    pre_env = env(user=user.id)
    pre_access = {}
    for model_name in ("project.project", "res.partner", "project.task.type"):
        Model = pre_env.get(model_name)
        pre_access[model_name] = {
            "read": bool(Model.check_access_rights("read", raise_exception=False)),
            "create": bool(Model.check_access_rights("create", raise_exception=False)),
        }
    Access = env["ir.model.access"].sudo()
    for model_name in models:
        model = env["ir.model"].sudo().search([("model", "=", model_name)], limit=1)
        Access.search([("model_id", "=", model.id), ("group_id", "=", group.id)]).write({"perm_create": False})
    # Remove only this account's binding to the temporary group; keep base.group_user.
    user.write({"groups_id": [(6, 0, [env.ref("base.group_user").id])], "active": False})
    env.cr.commit()
    pre_access_record = pre_access

if not user or not group:
    raise RuntimeError("dependency fixture role is not present")

user_id = user.id
user_env = env(user=user_id)
access = {}
for model_name in models:
    Model = user_env.get(model_name)
    access[model_name] = {
        "read": bool(Model.check_access_rights("read", raise_exception=False)),
        "create": bool(Model.check_access_rights("create", raise_exception=False)),
        "write": bool(Model.check_access_rights("write", raise_exception=False)),
        "unlink": bool(Model.check_access_rights("unlink", raise_exception=False)),
    }
other_create = []
for model_name in ("payment.request", "sc.payment.execution", "sc.receipt.income", "construction.contract"):
    Model = user_env.get(model_name)
    if Model is not None and Model.check_access_rights("create", raise_exception=False):
        other_create.append(model_name)

admin = bool(user_env.user.has_group("base.group_system"))
report = {
    "mode": mode,
    "db": env.cr.dbname,
    "login": login,
    "uid": user_id,
    "is_admin": admin,
    "active": bool(user.active),
    "groups": [g.name for g in user.groups_id],
    "model_access": access,
    "other_models_with_create": other_create,
}
if mode == "revoke_deactivate":
    report["pre_access_project_partner_stage"] = pre_access_record
print(json.dumps(report, ensure_ascii=False, indent=2))
PY
