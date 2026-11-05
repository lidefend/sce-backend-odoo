"""Owner-approved five-menu maintenance; use the registered demo duty only."""
import json
import os

EXPECTED_UUID = "d7c7f68c-d280-11f1-a914-0a0d1da8b8b8"
MENUS = {
    "smart_construction_core.menu_sc_business_config_workbench": 431,
    "smart_construction_core.menu_sc_approval_policy": 424,
    "smart_construction_core.menu_ui_form_field_policy_business_config": 445,
    "smart_construction_core.menu_ui_menu_config_policy_business_config": 432,
    "smart_construction_core.menu_sc_product_scenario_business_config": 720,
}


def validate_checkpoint(database, uuid, rows):
    if database != "sc_demo" or uuid != EXPECTED_UUID:
        raise RuntimeError("Approved demo database identity differs")
    if len(rows) != len(MENUS) or {r['xmlid']: r['id'] for r in rows} != MENUS:
        raise RuntimeError("Approved menu identities differ")
    if any(not r['action'] or r['bound'] or type(r['exempt']) is not bool for r in rows):
        raise RuntimeError("Menu action, binding or exemption checkpoint differs")


def configure(env):
    phase = os.environ.get("SC_SCENARIO_CONFIGURATION_PHASE", "readback")
    if phase not in {"apply", "readback"}:
        raise RuntimeError("Unsupported phase")
    if phase == "apply" and os.environ.get("SC_SCENARIO_CONFIGURATION_CONFIRM") != "EXEMPT_FIVE_APPROVED_DEMO_MAINTENANCE_MENUS":
        raise RuntimeError("Exact five-menu approval required")
    if env.cr.dbname != "sc_demo":
        raise RuntimeError("Wrong database")
    if phase == "readback":
        env.cr.rollback()
        env.cr.execute("SET TRANSACTION READ ONLY")
    uuid = env['ir.config_parameter'].sudo().get_param('database.uuid')
    if uuid != EXPECTED_UUID:
        raise RuntimeError("Approved demo database identity differs")
    menus = [env.ref(xmlid).sudo() for xmlid in MENUS]
    if any(menu._name != "ir.ui.menu" for menu in menus):
        raise RuntimeError("Approved references must resolve to menus")
    if phase == "apply":
        env.cr.execute("SELECT id FROM ir_ui_menu WHERE id IN %s ORDER BY id FOR UPDATE", (tuple(MENUS.values()),))
        for menu in menus:
            menu.invalidate_recordset()
    def rows():
        return [{"xmlid": xmlid, "id": menu.id, "action": str(menu.action) if menu.action else None,
                 "bound": bool(env['sc.product.scenario.entry'].sudo().search_count([('menu_id', '=', menu.id)])),
                 "exempt": menu.sc_scenario_exempt, "groups": sorted(menu.groups_id.ids)}
                for xmlid, menu in zip(MENUS, menus)]
    before = rows()
    validate_checkpoint(env.cr.dbname, uuid, before)
    if phase == "apply":
        print("SCENARIO_CONFIGURATION_BEFORE=" + json.dumps(before), flush=True)
        for menu in menus:
            if not menu.sc_scenario_exempt:
                menu.write({'sc_scenario_exempt': True})
    after = rows()
    validate_checkpoint(env.cr.dbname, uuid, after)
    if not all(r['exempt'] for r in after):
        raise RuntimeError("Approved exemptions are not persisted")
    if [r['groups'] for r in before] != [r['groups'] for r in after]:
        raise RuntimeError("Menu roles unexpectedly changed")
    if phase == "apply":
        env.cr.commit()
    else:
        env.cr.rollback()
    return {"status": "PASS", "phase": phase, "before": before, "after": after,
            "database_uuid": uuid, "changed_fields": ['sc_scenario_exempt'] if phase == 'apply' else [],
            "limits": "Model maintenance and persistence only; no claim of native publication or end-user authorization acceptance."}


if 'env' in globals():
    try:
        print('SCENARIO_CONFIGURATION=' + json.dumps(configure(env), ensure_ascii=False))
    except Exception:
        env.cr.rollback()
        raise
