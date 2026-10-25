"""One-shot repair of the observed Demo project manager; no ACL or seed replay."""
import json
import os


def validate_checkpoint(facts):
    expected = {"database": "sc_demo", "uuid": "c7ffe700-ce02-11f1-9a86-a213133df790",
                "project_id": 2, "project_code": "DEMO-PJ-001", "company_id": 1,
                "old_manager_id": 1, "root_id": 1, "actor_id": 40,
                "target_id": 8, "target_login": "pm1", "target_active": True,
                "target_company_id": 1, "project_user_id": 8}
    if facts != expected or any(type(facts.get(key)) is not type(value) for key, value in expected.items()):
        raise RuntimeError("Demo manager checkpoint differs; no write or replay permitted")


def repair(env):
    from odoo import api
    if os.environ.get("SC_DEMO_MANAGER_REPAIR_CONFIRM") != "BIND_DEMO_PJ_001_MANAGER_TO_PM1":
        raise RuntimeError("Exact Demo repair confirmation required")
    if env.cr.dbname != "sc_demo":
        raise RuntimeError("Wrong database")
    project = env.ref("smart_construction_demo.sc_demo_project_001")
    # Serialize only this row. The checkpoint is re-read under the lock.
    env.cr.execute("SELECT id FROM project_project WHERE id = %s FOR UPDATE", (project.id,))
    project.invalidate_recordset()
    actor = env["res.users"].search([("login", "=", "demo_full")])
    target = env["res.users"].search([("login", "=", "pm1")])
    actor.ensure_one()
    target.ensure_one()
    facts = {"database": env.cr.dbname,
             "uuid": env["ir.config_parameter"].sudo().get_param("database.uuid"),
             "project_id": project.id, "project_code": project.project_code,
             "company_id": project.company_id.id, "old_manager_id": project.manager_id.id,
             "root_id": env.ref("base.user_root").id, "actor_id": actor.id,
             "target_id": target.id, "target_login": target.login, "target_active": target.active,
             "target_company_id": target.company_id.id, "project_user_id": project.user_id.id}
    validate_checkpoint(facts)
    business = api.Environment(env.cr, actor.id, {"allowed_company_ids": [1]}, su=False)
    record = business["project.project"].browse(project.id)
    record.write({"manager_id": target.id})
    assert record.manager_id.id == target.id
    env.cr.commit()
    with env.registry.cursor() as cursor:
        fresh = api.Environment(cursor, actor.id, {"allowed_company_ids": [1]}, su=False)
        observed = fresh["project.project"].browse(project.id).read(
            ["project_code", "company_id", "manager_id", "user_id"])[0]
        assert observed["manager_id"][0] == target.id
    return {"status": "PASS", "before": facts, "after": observed,
            "sudo_write": False, "changed_fields": ["manager_id"],
            "recovery": "Paired Demo backup checked by Make; no automatic replay or rollback after commit."}


if "env" in globals():
    print("DEMO_MANAGER_REPAIR " + json.dumps(repair(env), ensure_ascii=False))
