import json


if env.cr.dbname != "sc_frontend_acceptance":
    raise RuntimeError("collection view browser fixture is restricted to sc_frontend_acceptance")

def target(action_xmlid, menu_xmlid):
    action = env.ref(action_xmlid)
    menu = env.ref(menu_xmlid)
    return {"action_id": action.id, "menu_id": menu.id, "model": action.res_model}


payload = {
    "ledger": target("smart_construction_core.action_sc_project_list", "smart_construction_core.menu_sc_project_project"),
    "overview": {
        "action_id": env.ref("smart_construction_core.action_sc_project_overview").id,
        "menu_id": 0,
        "model": "project.project",
    },
    "non_project": target("smart_construction_core.action_construction_contract_handling", "smart_construction_core.menu_sc_construction_contract"),
}
print("COLLECTION_VIEW_SEMANTICS_TARGETS_JSON=" + json.dumps(payload, ensure_ascii=False, sort_keys=True))
