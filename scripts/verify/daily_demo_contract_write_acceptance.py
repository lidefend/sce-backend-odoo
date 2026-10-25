"""Bounded real demo contract creation/edit/submission, with non-sudo actors.

The Make entry first validates this database generation's paired recovery point.
Keeps the new document for browser/approval follow-up; never resets seed records.
"""
import json
import os


def execute(env):
    from odoo import api
    from odoo.exceptions import AccessError
    if env.cr.dbname != "sc_demo" or os.environ.get("SC_DEMO_WRITE_CONFIRM") != "CREATE_AND_SUBMIT_DEMO_ACCEPTANCE_CONTRACT":
        raise RuntimeError("Exact demo write authorization required")
    env.cr.rollback()
    uuid = env["ir.config_parameter"].sudo().get_param("database.uuid")
    if uuid != os.environ.get("SC_DEMO_EXPECTED_UUID"):
        raise RuntimeError("Database generation differs from recovery point")
    key = os.environ["SC_DEMO_CONTRACT_KEY"]
    phase = os.environ.get("SC_DEMO_CONTRACT_PHASE", "create")
    if phase not in ("create", "approve", "reject", "cross_company", "readback"):
        raise RuntimeError("Unknown contract acceptance phase")
    if not key.startswith("DEMO-DELIVERY-") or not key.replace("-", "").isalnum():
        raise RuntimeError("Invalid bounded business key")
    user = env["res.users"].sudo().search([("login", "=", "demo_full"), ("active", "=", True)], limit=1)
    denied = env["res.users"].sudo().search([("login", "=", "demo_role_project_read"), ("active", "=", True)], limit=1)
    if not user or not denied or 1 in (user.id, denied.id) or user.id == denied.id:
        raise RuntimeError("Existing distinct non-superuser actors required")
    company = user.company_id
    actor = api.Environment(env.cr, user.id, {"allowed_company_ids": [company.id], "lang": "zh_CN"}, su=False)
    model = actor["sc.general.contract"]
    existing = model.search([("contract_name", "=", key)])
    if phase in ("create", "cross_company") and env["sc.general.contract"].sudo().search_count([("contract_name", "=", key)]):
        raise RuntimeError("Document already exists; inspect evidence instead of replaying writes")
    if phase in ("approve", "reject", "readback") and (len(existing) != 1 or existing.id != int(os.environ["SC_DEMO_CONTRACT_RECORD_ID"])):
        raise RuntimeError("Follow-up record identity differs")
    template = actor.ref("smart_construction_demo.sc_demo_general_contract_087_service")
    if template.company_id != company or not template.project_id or not template.partner_id:
        raise RuntimeError("Declared demo business anchors are incomplete")
    result = {"schema": "daily_demo_contract_write_acceptance.v1", "status": "RUNNING",
              "database_uuid": uuid, "business_key": key, "actor_uid": user.id,
              "denied_uid": denied.id, "company_id": company.id, "sudo_writes": False,
              "steps": [], "limits": "Backend user-authority journey; UI creation/edit and full approval remain separate gates."}

    def readback(record_id, company_id=None):
        with env.registry.cursor() as cursor:
            fresh = api.Environment(cursor, user.id, {"allowed_company_ids": [company_id or company.id]}, su=False)
            rec = fresh["sc.general.contract"].browse(record_id)
            data = rec.read(["contract_name", "name", "state", "amount_total", "note", "company_id"])[0]
            data["reviews"] = [{"id": x.id, "status": x.status,
                                "reviewer_ids": x.reviewer_ids.ids} for x in rec.review_ids]
            return data

    try:
        if phase == "readback":
            result["record_id"] = existing.id
            result["steps"].append({"action": "independent_backend_readback", "status": "PASS", "observed": readback(existing.id)})
            result["status"] = "READBACK_ONLY"
            env.cr.rollback()
            return result
        if phase == "cross_company":
            registered = env["sc.tenant.company.registration"].sudo().search([
                ("active", "=", True), ("data_purpose", "=", "demo")]).company_id
            targets = (registered & user.company_ids) - company
            if len(targets) != 1:
                raise RuntimeError("One existing authorized secondary demo company required")
            other = targets
            owner = api.Environment(env.cr, user.id, {"allowed_company_ids": [other.id]}, su=False)
            record = owner["sc.general.contract"].create({"contract_name": key,
                "partner_name_text": template.partner_name_text or template.partner_id.name,
                "amount_total": 13000, "note": "首次交付验收：跨公司权限边界，保留为草稿。"})
            env.cr.commit()
            result["record_id"] = record.id
            observed = readback(record.id, other.id)
            assert observed["company_id"][0] == other.id
            result["steps"].append({"action": "authorized_secondary_company_create_readback", "status": "PASS", "observed": observed})
            writer = env.ref("smart_construction_demo.user_sc_contract_01")
            assert writer.id != 1
            limited = record.with_user(writer).sudo(False).with_context(allowed_company_ids=[company.id])
            assert limited.check_access_rights("read", raise_exception=False)
            assert limited.check_access_rights("write", raise_exception=False)
            assert limited.search_count([("id", "=", record.id)]) == 0
            for operation in ("read", "write"):
                refused = False
                try:
                    with env.cr.savepoint():
                        if operation == "read":
                            limited.read(["contract_name"])
                        else:
                            limited.write({"note": "CROSS-COMPANY-WRITE-MUST-NOT-PERSIST"})
                        raise AssertionError("Cross-company " + operation + " unexpectedly succeeded")
                except AccessError:
                    refused = True
                assert refused
                env.cr.rollback()
                result["steps"].append({"action": "cross_company_" + operation + "_denied", "status": "PASS",
                    "actor_uid": writer.id, "allowed_company_ids": [company.id], "target_company_id": other.id,
                    "model_acl_granted": True, "exception": "AccessError"})
            observed = readback(record.id, other.id)
            assert "MUST-NOT-PERSIST" not in observed["note"]
            result["steps"].append({"action": "owner_readback_after_denied_writes", "status": "PASS", "observed": observed})
            result["status"] = "PASS_FOR_EXECUTED_BACKEND_STEPS"
            return result
        if phase != "create":
            from odoo.addons.smart_construction_demo.tools.scenario_loader import _DEMO_APPROVAL_ACTORS
            record = existing
            result["record_id"] = record.id
            if record.state != "draft" or record.validation_status not in ("waiting", "pending"):
                raise RuntimeError("Follow-up requires the actual pending approval instance")
            for _ in range(20):
                record.invalidate_recordset()
                if record.validation_status not in ("waiting", "pending"):
                    break
                review = record.review_ids.filtered(lambda r: r.status in ("waiting", "pending")).sorted("sequence")[:1]
                group = review.reviewer_group_id
                xmlid = group.get_external_id().get(group.id)
                seat = _DEMO_APPROVAL_ACTORS.get(xmlid)
                if not seat:
                    raise RuntimeError("No declared demo approval seat for pending tier")
                reviewer = env.ref(seat)
                if reviewer.id == 1 or not reviewer.active:
                    raise RuntimeError("Non-superuser active approval seat required")
                acting = record.with_user(reviewer).sudo(False).with_context(allowed_company_ids=[company.id])
                if not acting.can_review:
                    raise RuntimeError("Declared approval seat cannot review")
                before = review.status
                method = "reject_tier" if phase == "reject" else "validate_tier"
                getattr(acting, method)()
                env.cr.commit()
                observed = readback(record.id)
                result["steps"].append({"action": method, "status": "PASS", "actor_uid": reviewer.id,
                                         "actor_xmlid": seat, "review_id": review.id,
                                         "status_before": before, "observed": observed})
                if phase == "reject":
                    assert any(r["status"] == "rejected" for r in observed["reviews"])
                    record.action_cancel()
                    env.cr.commit()
                    observed = readback(record.id)
                    assert observed["state"] == "cancel"
                    result["steps"].append({"action": "formal_cancel_after_rejection", "status": "PASS", "observed": observed})
                    result["status"] = "PASS_FOR_EXECUTED_BACKEND_STEPS"
                    return result
            observed = readback(record.id)
            assert observed["state"] == "confirmed", "Approval did not confirm contract"
            record.action_signed()
            env.cr.commit()
            observed = readback(record.id)
            assert observed["state"] == "signed"
            result["steps"].append({"action": "formal_sign_and_independent_readback", "status": "PASS", "observed": observed})
            result["status"] = "PASS_FOR_EXECUTED_BACKEND_STEPS"
            return result
        record = model.create({"contract_name": key, "project_id": template.project_id.id,
                               "partner_id": template.partner_id.id, "amount_total": 12000,
                               "contract_direction": "expense", "contract_type": "现场服务",
                               "note": "首次交付验收：正式业务创建，保留用于后续审批和界面验收。"})
        env.cr.commit()
        result["record_id"] = record.id
        observed = readback(record.id)
        assert observed["state"] == "draft" and observed["amount_total"] == 12000
        result["steps"].append({"action": "create_and_independent_readback", "status": "PASS", "observed": observed})
        record.write({"amount_total": 12100, "note": "首次交付验收：编辑保存已回读，待正式审批。"})
        env.cr.commit()
        observed = readback(record.id)
        assert observed["amount_total"] == 12100
        result["steps"].append({"action": "edit_and_independent_readback", "status": "PASS", "observed": observed})
        # Always rollback the negative attempt, including an unexpected success.
        refused = False
        try:
            with env.cr.savepoint():
                record.with_user(denied).sudo(False).with_context(allowed_company_ids=[company.id]).write({"note": "DENIED-WRITE-MUST-NOT-PERSIST"})
                raise AssertionError("Read-only actor unexpectedly wrote the contract")
        except AccessError:
            refused = True
        assert refused
        env.cr.rollback()
        observed = readback(record.id)
        assert "DENIED-WRITE" not in (observed["note"] or "")
        result["steps"].append({"action": "readonly_actor_backend_write_denied", "status": "PASS", "exception": "AccessError"})
        record = actor["sc.general.contract"].browse(record.id)
        record.action_confirm()
        env.cr.commit()
        observed = readback(record.id)
        submitted = observed["state"] == "confirmed" or bool(observed["reviews"])
        assert submitted, "Submission neither confirmed nor created review records"
        result["steps"].append({"action": "formal_submit_and_independent_readback", "status": "PASS", "observed": observed})
        result["status"] = "PASS_FOR_EXECUTED_BACKEND_STEPS"
        result["approval_status"] = "PENDING" if observed["state"] == "draft" else "NO_SEPARATE_REVIEW_OBSERVED"
    except Exception as exc:
        env.cr.rollback()
        result.update({"status": "FAIL", "error_type": type(exc).__name__, "error": str(exc)[:1600]})
    return result


if "env" in globals():
    result = execute(env)
    print("DAILY_DEMO_CONTRACT_WRITE=" + json.dumps(result, ensure_ascii=False))
    if result["status"] == "FAIL":
        raise RuntimeError("Contract acceptance failed; preserve structured evidence and record")
