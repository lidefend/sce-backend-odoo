"""P4 read-only daily adapter for the existing demo readiness assertions."""
import hashlib
import inspect
import json
import os
import unittest
from pathlib import Path


def run_check(name, callback):
    try:
        detail = callback()
        return {"name": name, "status": "PASS", "detail": detail}
    except Exception as exc:
        return {"name": name, "status": "FAIL", "error_type": type(exc).__name__,
                "error": str(exc)[:1000]}


def verdict(checks):
    return "PASS" if checks and all(row["status"] == "PASS" for row in checks) else "FAIL"


def data_inventory(env):
    """Resolve observed empty surfaces; counts are not permission acceptance."""
    user = env["res.users"].sudo().search([("login", "=", "demo_full")], limit=1)
    if not user or user.id == 1:
        raise RuntimeError("Declared demo_full business actor unavailable")
    rows = []
    # Models from the preserved partial browser observation, not new product rules.
    models = ("sc.operating.metrics.project", "mail.notification", "tender.opportunity",
              "tender.document", "sc.quality.acceptance", "sc.site.variation",
              "sc.labor.worker", "sc.labor.deduction", "sc.material.supplier.return",
              "sc.hr.salary.payment")
    for name in models:
        def measure():
            model = env[name]
            actor = model.with_user(user).sudo(False).with_context(allowed_company_ids=[user.company_id.id])
            total = model.sudo().with_context(active_test=False).search_count([])
            visible = actor.search_count([])
            return {"all_states_global": total, "actor_active_visible": visible,
                    "classification": "no_global_rows" if total == 0 else
                    "actor_scope_or_archived" if visible == 0 else "rows_present"}
        rows.append(run_check(name, measure))
    return {"schema": "daily_demo_data_inventory.v1", "status": verdict(rows),
            "database": env.cr.dbname, "database_uuid": env["ir.config_parameter"].sudo().get_param("database.uuid"),
            "actor_uid": user.id, "company_id": user.company_id.id, "models": rows,
            "database_writes": 0, "limits": "Counts classify missing-data versus actor-scope leads; no write or denial proof."}


def navigation_authority_mismatches(nav_pairs, authority, decision):
    if not nav_pairs:
        raise RuntimeError('Nonzero navigation required')
    return [{'menu_id': menu_id, 'action_id': action_id}
            for menu_id, action_id in sorted(nav_pairs)
            if decision(authority, menu_id, action_id) is not True]


def scenario_delivery(env):
    """Compare real startup and server entry authority for the existing demo actor."""
    from odoo import api
    from odoo.addons.smart_core.handlers.system_init import SystemInitHandler
    from odoo.addons.smart_core.delivery.runtime_route_authority import published_route_authority, menu_publication_decision
    from odoo.addons.smart_construction_core.services.scenario_surface_projection import runtime_menu_scope, flatten_authorized_nav_leaves
    user = env['res.users'].sudo().search([('login', '=', 'demo_full')])
    user.ensure_one()
    if user.id == 1 or not user.active or user.share:
        raise RuntimeError('Existing internal demo actor required')
    actor = api.Environment(env.cr, user.id, dict(env.context, allowed_company_ids=[user.company_id.id]), su=False)
    response = SystemInitHandler(actor).run({'intent': 'system.init', 'params': {}})
    data = response.data if hasattr(response, 'data') else response.get('data', {})
    navigation = data.get('navigation') or {}
    if navigation.get('source') != 'system_init.navigation':
        raise RuntimeError('Final startup navigation unavailable')
    leaves = flatten_authorized_nav_leaves(navigation['nav'], navigation['route_authority'])
    nav_pairs = {(row['menu_id'], row['action_id']) for row in leaves}
    authority = published_route_authority(actor)
    if not authority:
        raise RuntimeError('Server entry authority unavailable')
    index, by_id, _ = runtime_menu_scope(actor)
    rows = []
    for menu in actor['ir.ui.menu'].sudo().browse(list(by_id)):
        if not menu.action:
            continue
        location = index[by_id[menu.id]]['location']
        visible = (menu.id, menu.action.id) in nav_pairs
        allowed = menu_publication_decision(authority, menu.id, menu.action.id)
        rows.append({'menu_id': menu.id, 'menu_xmlid': by_id[menu.id], 'scope': location,
                     'navigation': visible, 'server_entry': allowed})
    mismatches = navigation_authority_mismatches(nav_pairs, authority, menu_publication_decision)
    if not nav_pairs or not rows:
        raise RuntimeError('Nonzero navigation and scoped entries required')
    expected = (431, 424, 445, 432, 720)
    maintained = [row for row in rows if row['menu_id'] in expected]
    if {row['menu_id'] for row in maintained} != set(expected):
        raise RuntimeError('Five maintenance entries are not fully observable')
    denied = [row for row in authority.get('denied_actions', []) if row.get('menu_id') in expected]
    missing_allowed = [row for row in rows if row['scope'] == 'missing' and row['server_entry']]
    return {'status': 'FAIL' if mismatches or missing_allowed else 'PASS', 'actor_uid': user.id,
            'company_id': user.company_id.id, 'su': actor.su, 'rows': rows,
            'mismatches': mismatches, 'missing_allowed': missing_allowed,
            'maintenance_entries': maintained, 'maintenance_denials': denied,
            'limits': 'Actual startup handler and server authority service. Navigable entries must authorize; missing entries must deny. Contextual server routes need not appear in navigation. Missing checks cover only current searchable action menus; no actionless scene anchors, HTTP authentication or browser journey.'}


def scenario_inventory(env):
    """Observe stored facts only; never infer exemption authority from absence."""
    menus = env["ir.ui.menu"].sudo().with_context(active_test=False)
    has_exemption = "sc_scenario_exempt" in menus._fields
    has_scenarios = "sc.product.scenario" in env
    scenarios = env["sc.product.scenario"].sudo().with_context(active_test=False).search([]) if has_scenarios else []
    entries = env["sc.product.scenario.entry"].sudo().search([]) if "sc.product.scenario.entry" in env else []
    bindings = {entry.menu_id.id: entry.scenario_id.code for entry in entries}
    # Include the scenario maintenance entry itself, not only the four initial defaults.
    names = ("menu_sc_business_config_workbench", "menu_sc_approval_policy",
             "menu_ui_form_field_policy_business_config", "menu_ui_menu_config_policy_business_config",
             "menu_sc_product_scenario_business_config")
    rows = []
    for name in names:
        xmlid = "smart_construction_core." + name
        menu = env.ref(xmlid, raise_if_not_found=False)
        rows.append({"xmlid": xmlid, "exists": bool(menu), "menu_id": menu.id if menu else None,
                     "scenario_code": bindings.get(menu.id) if menu else None,
                     "explicit_exemption": bool(menu.sc_scenario_exempt) if menu and has_exemption else None})
    params = env["ir.config_parameter"].sudo()
    markers = {key: params.get_param("smart_construction_core." + key)
               for key in ("scenario_seed.v1", "external_center_seed.v1", "scenario_entry_scope.v1")}
    return {"schema": "daily_demo_scenario_inventory.v1", "status": "PASS",
            "database": env.cr.dbname, "database_uuid": params.get_param("database.uuid"),
            "schema_available": {"scenarios": has_scenarios, "explicit_exemption": has_exemption},
            "scenarios": [{"id": row.id, "code": row.code, "active": row.active} for row in scenarios],
            "binding_count": len(entries), "configuration_entries": rows,
            "searchable_exempt_menu_ids": menus.search([("sc_scenario_exempt", "=", True)]).ids if has_exemption else None,
            "initialization_markers": markers, "database_writes": 0,
            "limits": "Stored facts only, not authorization acceptance. Menu search may remain role-filtered even under sudo; exemption IDs are not an exhaustive database inventory. Existing true values have unknown provenance; absent schema is not a missing-configuration verdict."}


def observe(env):
    if env.cr.dbname != "sc_demo":
        raise RuntimeError("Registered demo duty database required")
    env.cr.rollback()
    env.cr.execute("SET TRANSACTION READ ONLY")
    env.cr.execute("SET LOCAL statement_timeout = '25000'")
    original_commit = env.cr.commit

    def refuse_commit(*args, **kwargs):
        raise RuntimeError("Read-only business readiness forbids commit")

    env.cr.commit = refuse_commit
    try:
        if os.environ.get("DAILY_DEMO_OBSERVATION") == "inventory":
            return data_inventory(env)
        if os.environ.get("DAILY_DEMO_OBSERVATION") == "scenario":
            return scenario_inventory(env)
        if os.environ.get("DAILY_DEMO_OBSERVATION") == "scenario_delivery":
            return scenario_delivery(env)
        from odoo.addons.smart_construction_demo.tests.test_demo_baseline_readiness import (
            TestDemoBaselineReadiness, HARD_KEYS,
        )
        from odoo.addons.smart_construction_demo.tests.test_demo_golden_chain import TestDemoGoldenChain

        # Reuse only the read methods, never TransactionCase setup or fixture creation.
        class Reader(unittest.TestCase):
            pass

        for name in ("_company", "_exec_project", "_admin_separation", "_probes"):
            setattr(Reader, name, getattr(TestDemoBaselineReadiness, name))
        reader = Reader()
        reader.env = env
        probes = {}

        def readiness():
            probes.update(reader._probes())
            missing = sorted(key for key in HARD_KEYS if not probes.get(key))
            if missing:
                raise AssertionError("Missing hard prerequisites: " + ", ".join(missing))
            return {"hard_checks": len(HARD_KEYS), "observed_checks": len(probes)}

        checks = [run_check("G0_G4_readiness", readiness)]
        checks.append(run_check("golden_chain_readback", lambda:
            TestDemoGoldenChain.test_golden_chain_amount_state_and_role_relay(reader)))
        sources = {}
        for cls in (TestDemoBaselineReadiness, TestDemoGoldenChain):
            path = Path(inspect.getsourcefile(cls))
            sources[cls.__name__] = {"path": str(path),
                                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        return {"schema": "daily_demo_business_readiness.v1", "status": verdict(checks),
                "database": env.cr.dbname,
                "database_uuid": env["ir.config_parameter"].sudo().get_param("database.uuid"),
                "company_id": reader._company().id, "project_ids": reader._exec_project().ids,
                "probes": probes, "hard_keys": sorted(HARD_KEYS), "checks": checks,
                "sources": sources, "database_writes": 0,
                "limits": "Read-only data coherence; does not prove write, approval or permission-denial journeys."}
    finally:
        env.cr.rollback()
        env.cr.commit = original_commit


if "env" in globals():
    result = observe(env)
    print("DAILY_DEMO_BUSINESS_READINESS=" + json.dumps(result, ensure_ascii=False))
    if result["status"] != "PASS":
        raise RuntimeError("Daily demo observation failed; inspect structured result")
