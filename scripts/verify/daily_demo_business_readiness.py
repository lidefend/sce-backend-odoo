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
