"""Read-only identities and business fingerprints for the bounded form journey."""
import hashlib
import json
import os
import inspect
from pathlib import Path

from odoo.addons.smart_core.identity.identity_resolver import IdentityResolver
from odoo.addons.smart_core.core import form_configuration_compiler

if env.cr.dbname != "sc_dev_demo":
    raise RuntimeError("expected governed local.dev database")
user = env["res.users"].sudo().search([("login", "=", "sc_test_admin"), ("active", "=", True)], limit=1)
if not user or not user.has_group("smart_core.group_smart_core_business_config_admin"):
    raise RuntimeError("governed sc_test_admin config authority unavailable")
principal = env(user=user, context={**env.context, "allowed_company_ids": [user.company_id.id]})
resolver = IdentityResolver(principal)
topic = os.environ.get("LOWCODE_FORM_TOPIC", "material")
# Read-only representative routes for the structure-consumption review.  Each
# topic is an (action, view, menu) triple that must resolve inside the governed
# database; the browser runner reuses the same environment/identity checks and
# performs no writes on these topics.
TOPIC_IDENTITIES = {
    "material": (
        ("action_sc_material_inbound_handling", "view_sc_material_inbound_form", "menu_sc_material_inbound"),
        ("action_sc_material_outbound", "view_sc_material_outbound_form", "menu_sc_material_outbound"),
    ),
    "document": (
        ("action_sc_certificate_registration", "view_sc_document_admin_document_form", "menu_sc_certificate_registration"),
        ("action_sc_product_policy_document_v1", "view_sc_document_admin_document_form", "menu_sc_product_policy_document_v1"),
    ),
    # U-C4 G02: four formal invoice entries (785 input, 786 output application,
    # 787 output registration, 788 prepaid tax) share model sc.invoice.registration
    # and form view 1651; the last two identities are the shared-form bypass
    # actions (789 input tax report, 639 invoice general ledger) which must keep
    # working on the rebuilt native form without legacy section projections.
    "invoice": (
        ("action_sc_invoice_input", "view_sc_invoice_registration_form", "menu_sc_invoice_input"),
        ("action_sc_invoice_registration_user", "view_sc_invoice_registration_form", "menu_sc_invoice_registration_user"),
        ("action_sc_invoice_application_user", "view_sc_invoice_registration_form", "menu_sc_invoice_application_user"),
        ("action_sc_invoice_prepaid_tax_user", "view_sc_invoice_registration_form", "menu_sc_invoice_prepaid_tax_user"),
        ("action_sc_invoice_input_report_user", "view_sc_invoice_registration_form", "menu_sc_invoice_input_report_user"),
        ("action_sc_invoice_registration", "view_sc_invoice_registration_form", "menu_sc_invoice_registration"),
    ),
    "payment": (
        ("action_payment_request_user_payment_apply", "view_payment_request_pay_form", "menu_sc_user_payment_apply"),
    ),
    "customer": (
        ("action_sc_customer_partner", "view_sc_customer_partner_form", "menu_sc_customer_partner"),
    ),
    "contract": (
        # The delivered route authority for the governed role carries the P1
        # contract entries (menus 660/661); the handling menu is not part of the
        # authorized navigation for this role.
        ("action_construction_contract_income", "view_construction_contract_income_form", "menu_sc_p1_income_contract"),
        ("action_construction_contract_expense", "view_construction_contract_expense_form", "menu_sc_p1_expense_contract"),
    ),
    "settlement": (
        # The delivered route authority for the governed role carries the P1
        # settlement entries (menus 664/665); the legacy 483/488 menus point at
        # the same actions but are not part of the authorized navigation.
        ("action_sc_settlement_order_income", "view_sc_settlement_order_form", "menu_sc_p1_income_settlement"),
        ("action_sc_settlement_order_expense", "view_sc_settlement_order_form", "menu_sc_p1_expense_settlement"),
    ),
}
TOPIC_SAMPLE_FIELDS = {
    "invoice": ["direction", "source_kind", "source_origin", "note"],
    "payment": ["amount", "state"],
    "customer": ["name", "active"],
    "contract": ["state"],
    "settlement": ["state"],
}
# Mechanism assertions for the read-only representative pass.  Names are the
# registered display copies / canonical sources of the same business fact; the
# checks verify that the copy stays declared outside the body while the body
# keeps exactly one presentation of the fact.
TOPIC_REPRESENTATIVE = {
    "payment": {
        "display_copy_out_of_body": ["payment_request_attachment_text_display"],
        "require_render": ["attachment_ids"],
        "suffix_display_must_render": ["payee_account_source_display"],
    },
    "customer": {"relations": True},
    # Relation collections guarded by container conditions such as
    # `invisible="not id"` can only be observed on an existing record, so these
    # topics additionally replay the same read-only battery on a governed sample.
    "contract": {"relations": True, "readonly_values": True, "record_surface": True},
    "settlement": {"relations": True, "readonly_values": True, "record_surface": True},
    "material": {"relations": True, "notebook": True, "full_width_detail": True, "section_navigation": True},
    # The invoice create form is the surface the sticky 章节导航 defect was
    # reported on: the contract-v2 driver path renders the same command bar
    # without `contract-form-native-shell`, so the navigation must pin below the
    # measured header there too.  Read-only; no change set is touched.
    "invoice": {"section_navigation": True},
}
if topic not in TOPIC_IDENTITIES:
    raise RuntimeError("unregistered formal form topic")
entries = []
identities = TOPIC_IDENTITIES[topic]
topic_sample_fields = TOPIC_SAMPLE_FIELDS.get(topic, [])
for action_xmlid, view_xmlid, menu_xmlid in identities:
    action, view, menu = [env.ref("smart_construction_core." + key) for key in (action_xmlid, view_xmlid, menu_xmlid)]
    if menu.action != action or view.model != action.res_model:
        raise RuntimeError("formal menu/action/view identity mismatch")
    model = principal[action.res_model]
    model.check_access_rights("read")
    rows = model.search([], order="id").read([name for name in ("write_date", "state") if name in model._fields])
    from odoo.tools.safe_eval import safe_eval
    domain = safe_eval(action.domain or "[]")
    sample_names = ["display_name"] + topic_sample_fields + (["legacy_document_no", "legacy_document_state", "legacy_source_table", "legacy_source_id"] if topic == "document" else [])
    samples = model.search(domain, order="id", limit=3).read([name for name in dict.fromkeys(sample_names) if name in model._fields])
    entries.append({"samples": samples, "action_groups": action.groups_id.get_external_id(), "action_context": action.context, "domain": action.domain, "model": action.res_model, "action_id": action.id, "view_id": view.id, "menu_id": menu.id,
                    "business_fingerprint": hashlib.sha256(json.dumps(rows, default=str, sort_keys=True).encode()).hexdigest()})
configuration_entry = None
if os.environ.get("LOWCODE_CONFIG_ENTRY") == "1":
    menu = env["ir.ui.menu"].browse(431).exists()
    action = menu.action
    if not menu or action.id != 737 or action.res_model != "ui.business.config.contract":
        raise RuntimeError("configuration entry identity mismatch")
    owned_sets = principal["ui.business.config.change.set"].sudo().search([("user_id", "=", user.id)], order="id")
    change_sets = owned_sets.read(["write_date", "state", "name"])
    for row, record in zip(change_sets, owned_sets):
        result = record.publish_result_json or {}
        row["rollback_of"] = result.get("rollback_of_change_set_id")
        row["rollback_verified"] = bool(row["rollback_of"] and result.get("published_content_verified") and result.get("runtime_verified"))
    configuration_entry = {"menu_id": menu.id, "menu_xmlid": menu.get_external_id().get(menu.id), "menu_name": menu.name,
                           "action_id": action.id, "action_xmlid": action.get_external_id().get(action.id), "context": action.context,
                           "model": action.res_model, "views": action.view_ids.read(["view_mode", "view_id"]),
                           "json_fields": [k for k, v in principal[action.res_model]._fields.items() if v.type == "json"],
                           "owner_change_sets": change_sets,
                           "configuration_fingerprint": hashlib.sha256(json.dumps(principal[action.res_model].with_context(active_test=False).search([], order="id").read(["write_date", "status", "version_no"]), default=str, sort_keys=True).encode()).hexdigest()}
if os.environ.get("LOWCODE_CONFIG_BATCH") == "1":
    if not configuration_entry or topic != "document":
        raise RuntimeError("configuration batch requires the registered document sample")
    other_action = env.ref("smart_construction_core.action_sc_material_inbound_handling")
    other_rows = principal[other_action.res_model].search([], order="id").read(["write_date", "state"])
    configuration_entry["other_business_fingerprint"] = hashlib.sha256(json.dumps(other_rows, default=str, sort_keys=True).encode()).hexdigest()
    target_name = "view_orchestration:%s:form:action:%s:view:%s:role:%s" % (
        entries[0]["model"], entries[0]["action_id"], entries[0]["view_id"], resolver.resolve_role_code(resolver.user_group_xmlids(user)))
    Contract = principal["ui.business.config.contract"].with_context(active_test=False)
    target = Contract.search([("name", "=", target_name), ("company_id", "=", user.company_id.id)])
    if len(target) != 1:
        raise RuntimeError("expected exactly one existing governed certificate test configuration")
    configuration_entry["configuration_fingerprint"] = hashlib.sha256(json.dumps(
        Contract.search([("id", "!=", target.id)], order="id").read(["write_date", "status", "version_no"]), default=str, sort_keys=True).encode()).hexdigest()
    configuration_entry["test_target_baseline"] = target.read(["name", "active", "status", "priority", "contract_json", "company_id", "role_key", "model", "action_id", "view_id"])
inventory = None
if os.environ.get("LOWCODE_CONFIG_INVENTORY") == "1":
    contracts = env["ui.business.config.contract"].sudo().with_context(active_test=False).search([], order="id")
    xmlids = contracts.get_external_id()
    inventory = []
    for rec in contracts:
        payload = rec.contract_json if isinstance(rec.contract_json, dict) else {}
        inventory.append({"id": rec.id, "name": rec.name, "xmlid": xmlids.get(rec.id, ""), "active": rec.active,
                          "status": rec.status, "version_no": rec.version_no, "model": rec.model, "view_type": rec.view_type,
                          "action_id": rec.action_id.id, "view_id": rec.view_id.id, "company_id": rec.company_id.id, "role_key": rec.role_key,
                          "declared_context": (payload.get("view_orchestration") or {}).get("context", {}),
                          "created_at": str(rec.create_date), "updated_at": str(rec.write_date)})
# Read-only inventory of the open configuration drafts that already exist for this
# run's designer targets. The designer resumes whichever draft the product considers
# active, so the run must be able to prove before and after that it did not consume a
# draft authored by somebody else.
from odoo.addons.smart_core.model.ui_business_config_change_set import ACTIVE_CHANGE_SET_STATES, stable_payload_hash

# Read-only inventory of every draft the product could resume for this run's designer
# targets. It mirrors `BusinessConfigChangeSetOpenHandler` instead of guessing: same owner
# /company/database scope, same active states, same expiry rule, and both resume rules the
# handler accepts (item target_key, or item model+action). Nothing is filtered by view or
# role so a superset is inventoried, and each item carries its payload digest so a later
# comparison can prove the content was not touched.
designer_scope = {
    "user_id": int(user.id),
    "company_id": int(user.company_id.id),
    "database_name": env.cr.dbname,
}
designer_target_prefixes = sorted({"view_orchestration:%s:form:action:%s:view:%s" % (e["model"], e["action_id"], e["view_id"]) for e in entries})
designer_target_pairs = sorted({(str(e["model"]), int(e["action_id"])) for e in entries})
designer_drafts = []
ChangeSet = principal["ui.business.config.change.set"].sudo()
for rec in ChangeSet.search([
    ("user_id", "=", user.id),
    ("company_id", "=", user.company_id.id),
    ("database_name", "=", env.cr.dbname),
    ("state", "in", tuple(sorted(ACTIVE_CHANGE_SET_STATES))),
], order="id"):
    if rec._is_expired():
        continue
    items = []
    matched = False
    for item in rec.item_ids.sorted("id"):
        target = str(item.target_key or "")
        pair = (str(item.model or ""), int(item.action_id or 0))
        hit = any(target.startswith(prefix) for prefix in designer_target_prefixes) or pair in designer_target_pairs
        matched = matched or hit
        items.append({
            "item_id": int(item.id), "target_key": target, "model": str(item.model or ""),
            "action_id": int(item.action_id or 0), "view_id": int(item.view_id or 0),
            "role_key": str(item.role_key or ""), "matches_run_target": bool(hit),
            "draft_payload_digest": stable_payload_hash(item.draft_payload if isinstance(item.draft_payload, dict) else {}),
        })
    if not matched:
        continue
    designer_drafts.append({
        "id": int(rec.id), "name": str(rec.name or ""), "state": str(rec.state or ""),
        "role_key": str(rec.role_key or ""), "expires_at": str(rec.expires_at or ""),
        "create_date": str(rec.create_date or ""), "write_date": str(rec.write_date or ""),
        "items": items,
    })

print("FORM_LOWCODE_SCOPE=" + json.dumps({
    "configuration_inventory": inventory, "configuration_entry": configuration_entry, "designer_scope": designer_scope, "topic": topic, "designer_drafts": designer_drafts, "database": env.cr.dbname, "company_id": user.company_id.id, "user_id": user.id, "login": user.login,
    "representative": TOPIC_REPRESENTATIVE.get(topic),
    "role_key": resolver.resolve_role_code(resolver.user_group_xmlids(user)), "entries": entries,
    "runtime_revision": os.environ.get("SC_SOURCE_REVISION", "unknown"),
    "compiler_sha256": hashlib.sha256(Path(inspect.getfile(form_configuration_compiler)).read_bytes()).hexdigest(),
}, default=str, sort_keys=True))
