"""P4 bounded HTTP approval of the existing UI acceptance contract.

Run through Make's existing demo recovery gate. No retries, sudo, ACL changes,
creation, or terminal-record replay. Every actor consumes its fresh work item.
"""
import json
import os
from pathlib import Path

from scripts.ops.dev_acceptance_release_probe import _HttpSession

ROOT = Path(__file__).resolve().parents[2]
MODEL = "sc.general.contract"
RECORD = 6
KEY = "DEMO-DELIVERY-20261025-UI01"
CONTEXT = {"allowed_company_ids": [1]}


def validate_finance_resume(prior, reviews):
    if (prior.get("record_id") != RECORD or prior.get("business_key") != KEY
            or prior.get("status") != "BLOCKED_NOT_ACCEPTED" or prior.get("pending_mutation")
            or prior.get("failure", {}).get("actor") != "fin_mgr"):
        raise ValueError("Prior attempt is not the known pre-finance checkpoint")
    completed = [(r.get("actor"), r.get("origin", {}).get("id"))
                 for r in prior.get("completed_api_actions", [])]
    if completed != [("ct1", 688), ("sc_demo_operation", 689)]:
        raise ValueError("Prior successful review identities differ")
    expected = {688: "approved", 689: "approved", 690: "pending", 691: "waiting"}
    if len(reviews) != 4 or {r.get("id"): r.get("status") for r in reviews} != expected:
        raise ValueError("Live review checkpoint changed; do not replay")
    if any(r.get("model") != MODEL or r.get("res_id") != RECORD for r in reviews):
        raise ValueError("Review target differs")


def released_contract_entry(data):
    pending = list(data.get("navigation", {}).get("nav", []))
    matches = []
    while pending:
        node = pending.pop()
        meta = node.get("meta") or {}
        if (node.get("menu_xmlid") or node.get("xmlid") or meta.get("menu_xmlid")) == "smart_construction_core.menu_sc_p1_daily_contract":
            action = node.get("action_id") or node.get("actionId") or node.get("action") or meta.get("action_id") or meta.get("actionId")
            menu = node.get("menu_id") or node.get("menuId") or meta.get("menu_id") or meta.get("menuId")
            if type(action) is not int or type(menu) is not int or min(action, menu) <= 0:
                raise ValueError("Released contract entry identity invalid")
            matches.append({"action_id": action, "menu_id": menu})
        pending.extend(node.get("children") or [])
    if len(matches) != 1:
        raise ValueError("Unique released contract entry required")
    return matches[0]


def validate_sign_entry_resume(failed):
    steps = failed.get("steps") or []
    last = steps[-1] if steps else {}
    if (failed.get("status") != "BLOCKED_NOT_ACCEPTED" or failed.get("record_id") != RECORD
            or failed.get("business_key") != KEY or failed.get("completed_api_actions")
            or last.get("actor") != "demo_full" or last.get("intent") != "execute_button"
            or last.get("http_status") != 403
            or last.get("response", {}).get("error", {}).get("message") != "ACTION_CONTRACT_AUTHORITY_MISSING"
            or failed.get("pending_mutation", {}).get("button", {}).get("name") != "action_signed"):
        raise ValueError("Only the confirmed missing-entry rejection may resume")


def validate_sign_checkpoint(prior, record, reviews):
    if (prior.get("status") != "API_APPROVAL_EXECUTED_FINAL_SIGN_PENDING"
            or prior.get("record_id") != RECORD or prior.get("business_key") != KEY
            or prior.get("pending_mutation") or prior.get("failure")
            or prior.get("reused_reviews") != [688, 689]):
        raise ValueError("Completed approval receipt required")
    actions = prior.get("completed_api_actions", [])
    if [(a.get("actor"), a.get("origin", {}).get("id")) for a in actions] != [
            ("fin_mgr", 690), ("demo_role_executive", 691)]:
        raise ValueError("Final approval provenance differs")
    if (record.get("id") != RECORD or record.get("state") != "confirmed"
            or record.get("validation_status") != "validated"):
        raise ValueError("Confirmed validated contract required; do not replay signing")
    if len(reviews) != 4 or {r.get("id"): r.get("status") for r in reviews} != {
            i: "approved" for i in (688, 689, 690, 691)}:
        raise ValueError("All four exact approvals required")
    if any(r.get("model") != MODEL or r.get("res_id") != RECORD for r in reviews):
        raise ValueError("Review target differs")


def approval_button(contract, action_name="validate_tier"):
    if action_name not in ("validate_tier", "action_signed"):
        raise ValueError("Unsupported acceptance action")
    rows = [r for r in contract.get("actionContract", {}).get("actionRuleList", [])
            if r.get("button", {}).get("name") == action_name]
    if len(rows) != 1:
        raise ValueError("Approval authority must be unique")
    row = rows[0]
    if not (row.get("allowed") is True and row.get("enabled") is True
            and row.get("disabled") is False and row.get("entitlementEvaluated") is True):
        raise ValueError("Approval not authorized by current contract")
    if row["button"].get("type") != "object" or not all(row.get(k) for k in (
            "actionId", "backendIdentity", "sourceWidgetId")):
        raise ValueError("Incomplete native action identity")
    return {**row["button"], "action_id": row["actionId"],
            "backend_identity": row["backendIdentity"], "source_widget_id": row["sourceWidgetId"]}


def target_origin(data):
    workspace = data.get("product_workspace", {})
    matches = [item["target"] for section in workspace.get("sections", [])
               if section.get("key") == "todo" for item in section.get("items", [])
               if item.get("target", {}).get("model") == MODEL
               and item["target"].get("record_id") == RECORD]
    if len(matches) != 1:
        raise ValueError("Exact assigned actionable work item unavailable")
    origin = matches[0].get("work_item_origin", {})
    if set(origin) != {"source", "id"} or origin["source"] != "tier.review" or type(origin["id"]) is not int or origin["id"] <= 0:
        raise ValueError("Invalid review provenance")
    return origin


def main():
    if (os.environ.get("SC_DEMO_WRITE_CONFIRM") != "CREATE_AND_SUBMIT_DEMO_ACCEPTANCE_CONTRACT"
            or os.environ.get("SC_DEMO_CONTRACT_KEY") != KEY
            or os.environ.get("SC_DEMO_CONTRACT_RECORD_ID") != str(RECORD)):
        raise RuntimeError("Exact existing demo document required")
    output = ROOT / ".runtime/final-acceptance/user-delivery-baseline/contract-api-approval.json"
    mode = os.environ.get("SC_DEMO_API_MODE", "initial")
    if mode not in ("initial", "resume_finance", "sign", "sign_entry_resume"):
        raise RuntimeError("Unknown API acceptance mode")
    prior = json.loads(output.read_text()) if mode == "resume_finance" else None
    if prior is not None:
        output = output.with_name("contract-api-approval-resume.json")
    if mode in ("sign", "sign_entry_resume"):
        prior = json.loads(output.with_name("contract-api-approval-resume.json").read_text())
        output = output.with_name("contract-api-sign.json")
        if mode == "sign_entry_resume":
            validate_sign_entry_resume(json.loads(output.read_text()))
            output = output.with_name("contract-api-sign-entry-resume.json")
    if output.exists():
        raise RuntimeError("Prior attempt exists; inspect checkpoint instead of replay")
    password = json.loads((ROOT / "config/acceptance/daily_demo_credential.v1.json").read_text())["password"]
    report = {"status": "RUNNING", "model": MODEL, "record_id": RECORD,
              "business_key": KEY, "transport": "HTTP /t/demo/api/v1/intent", "steps": []}

    def save():
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")

    def session(login, uid):
        client = _HttpSession("http://1.95.85.92:18081/t/demo", "", 30)
        code, body = client.login(login, password)
        identity = json.loads(body)["result"]
        if code != 200 or not client.token or identity["uid"] != uid or identity["db"] != "sc_demo":
            raise RuntimeError("Actor or namespace mismatch")
        return client

    def call(client, intent, params, meta=None):
        payload = {"intent": intent, "params": params, "context": CONTEXT}
        if meta is not None:
            payload["meta"] = meta
        code, raw = client.post("/api/v1/intent", payload)
        body = json.loads(raw)
        report["steps"].append({"actor": current_actor, "intent": intent, "http_status": code, "response": body})
        save()
        if code != 200 or body.get("ok") is not True:
            raise RuntimeError(f"{intent} failed with HTTP {code}")
        return body["data"]

    def readback(reader):
        data = call(reader, "api.data", {"op": "read", "model": MODEL, "ids": [RECORD],
            "fields": ["id", "contract_name", "state", "amount_total", "company_id", "review_ids", "validation_status"], "context": CONTEXT})
        row, = data["records"]
        if row["contract_name"] != KEY or row["company_id"][0] != 1 or row["amount_total"] != 12600:
            raise RuntimeError("Business identity drift")
        return row

    current_actor = "demo_full"
    try:
        reader = session(current_actor, 40)
        initial = readback(reader)
        if mode in ("sign", "sign_entry_resume"):
            live = call(reader, "api.data", {"op": "read", "model": "tier.review",
                "ids": initial["review_ids"], "fields": ["id", "status", "model", "res_id"], "context": CONTEXT})
            validate_sign_checkpoint(prior, initial, live["records"])
            entry = released_contract_entry(call(reader, "system.init", {}))
            report["released_entry"] = entry
            contract = call(reader, "ui.contract.v2", {"op": "model", "model": MODEL, **entry,
                "view_type": "form", "record_id": RECORD, "render_profile": "readonly",
                "delivery_profile": "full", "client_type": "web_pc", "accepted_contract_versions": ["2.0.x"],
                "client_contract_capabilities": ["container_tree.v2", "data_source.v2", "action_rule.v2", "relation_entry.v2", "status_contract.v2"]})
            button = approval_button(contract, "action_signed")
            report["pending_mutation"] = {"actor": current_actor, "button": button}
            save()
            call(reader, "execute_button", {"model": MODEL, "res_id": RECORD, "button": button, "context": CONTEXT}, entry)
            observed = readback(reader)
            if observed["state"] != "signed" or observed["validation_status"] != "validated":
                raise RuntimeError("Signed validated state did not persist")
            report["completed_api_actions"] = [{"actor": current_actor, "action": "action_signed", "readback": observed}]
            report.pop("pending_mutation")
            report["status"] = "API_SIGN_EXECUTED"
            save()
            print(json.dumps({"status": report["status"], "record_id": RECORD}))
            return 0
        if initial["state"] != "draft" or initial["validation_status"] != "pending":
            raise RuntimeError("Existing pending document required")
        actors = [("ct1", 14), ("sc_demo_operation", 6), ("fin_mgr", 13), ("demo_role_executive", 49)]
        if prior is not None:
            live = call(reader, "api.data", {"op": "read", "model": "tier.review",
                "ids": initial["review_ids"], "fields": ["id", "status", "model", "res_id"], "context": CONTEXT})
            validate_finance_resume(prior, live["records"])
            report["reused_reviews"] = [688, 689]
            actors = actors[2:]
        for login, uid in actors:
            current_actor = login
            client = session(login, uid)
            workspace = call(client, "my.work.summary", {"product_workspace": True})
            origin = target_origin(workspace)
            contract = call(client, "ui.contract.v2", {"op": "model", "model": MODEL,
                "view_type": "form", "record_id": RECORD, "render_profile": "readonly",
                "delivery_profile": "full", "client_type": "web_pc", "accepted_contract_versions": ["2.0.x"],
                "client_contract_capabilities": ["container_tree.v2", "data_source.v2", "action_rule.v2", "relation_entry.v2", "status_contract.v2"]})
            button = approval_button(contract)
            report["pending_mutation"] = {"actor": login, "origin": origin, "button": button}
            save()
            call(client, "execute_button", {"model": MODEL, "res_id": RECORD, "button": button,
                "context": CONTEXT}, {"work_item_origin": origin})
            current_actor = "demo_full"
            observed = readback(reader)
            reviews = call(reader, "api.data", {"op": "read", "model": "tier.review",
                "ids": [origin["id"]], "fields": ["id", "status", "model", "res_id"], "context": CONTEXT})
            reviewed, = reviews["records"]
            if (reviewed["id"] != origin["id"] or reviewed["status"] != "approved"
                    or reviewed["model"] != MODEL or reviewed["res_id"] != RECORD):
                raise RuntimeError("Approval did not persist on the exact review instance")
            report.setdefault("completed_api_actions", []).append({"actor": login, "origin": origin, "readback": observed})
            report.pop("pending_mutation", None)
            save()
        report["status"] = "API_APPROVAL_EXECUTED_FINAL_SIGN_PENDING"
    except Exception as exc:
        report["status"] = "BLOCKED_NOT_ACCEPTED"
        report["failure"] = {"actor": current_actor, "type": type(exc).__name__, "message": str(exc)}
    save()
    print(json.dumps({k: report[k] for k in ("status", "record_id")}, ensure_ascii=False))
    if report.get("failure"):
        print(json.dumps(report["failure"], ensure_ascii=False))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
