"""Read the real startup navigation for every existing internal user/company.

Executed only by local.dev.menu_facts.snapshot in the registered demo DB.
Startup may initialize transactional caches. Commit is forbidden and every
actor evaluation is rolled back; no persistent product or user changes occur.
"""
import json
import os
from odoo import api
from odoo.addons.smart_core.handlers.system_init import SystemInitHandler

assert env.cr.dbname == "sc_dev_demo", "snapshot requires governed local.dev database"
env.cr.rollback()
original_commit = env.cr.commit
def refuse_commit(*args, **kwargs):
    raise RuntimeError("snapshot forbids transaction commit")
env.cr.commit = refuse_commit
principals = [(user.id, list(user.company_ids.ids)) for user in env["res.users"].sudo().search([
    ("active", "=", True), ("share", "=", False),
])]
requested = os.environ.get("PRODUCT_MENU_FACT_USER_IDS", "")
if requested:
    requested_ids = {int(value) for value in requested.split(",")}
    assert requested_ids and requested_ids <= {uid for uid, _ in principals}, "unknown snapshot user scope"
    principals = [(uid, companies) for uid, companies in principals if uid in requested_ids]
edition_facts = {}
for product in env["sc.product.policy"].sudo().search([("product_key", "in", ["construction.standard", "construction.preview"]), ("active", "=", True)]):
    entries = [row for group in product.menu_groups for row in group.get("menus", [])]
    edition_facts[product.product_key] = {state: [row["menu_xmlid"] for row in entries if row.get("release_state") == state] for state in ("released", "preview")}
rows = []
errors = []


def flatten(nodes, ancestors=()):
    result = []
    for node in nodes:
        label = str(node.get("label") or node.get("title") or "")
        path = (*ancestors, label)
        meta = node.get("meta") or {}
        result.append({"key": node.get("key"), "label_path": list(path),
                       "target": node.get("target"), "route": node.get("route"),
                       "menu_id": node.get("menu_id") or meta.get("menu_id"),
                       "action_id": node.get("action_id") or meta.get("action_id")})
        result.extend(flatten(node.get("children") or [], path))
    return result


for uid, companies in principals:
    for company_id in companies:
        try:
            actor = api.Environment(env.cr, uid, {"allowed_company_ids": [company_id], "lang": "zh_CN"})
            reply = SystemInitHandler(env=actor).handle(payload={"params": {}})
            if not reply.ok:
                raise ValueError(str(reply.error))
            data = reply.data
            nav = data["navigation"]["nav"]
            rows.append({"user_id": uid, "company_id": company_id,
                         "groups": sorted(actor.user.groups_id.ids),
                         "nodes": flatten(nav), "route_authority": data["navigation"]["route_authority"]})
            print("MENU_FACT_PROGRESS user_id=%s company_id=%s nodes=%s" % (uid, company_id, len(rows[-1]["nodes"])), flush=True)
        except Exception as exc:
            errors.append({"user_id": uid, "company_id": company_id, "error": str(exc)})
        finally:
            env.cr.rollback()
            env.invalidate_all()

print("MENU_FACT_SNAPSHOT=" + json.dumps({"database":"sc_dev_demo", "principals":rows, "edition_facts":edition_facts, "errors":errors, "status":"passed" if rows and not errors else "failed"}, ensure_ascii=False, default=str), flush=True)
env.cr.rollback()
env.cr.commit = original_commit
if errors or not rows:
    raise RuntimeError("menu fact snapshot incomplete")
