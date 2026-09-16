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
if topic not in {"material", "document", "invoice"}:
    raise RuntimeError("unregistered formal form topic")
entries = []
identities = (
    ("action_sc_material_inbound_handling", "view_sc_material_inbound_form", "menu_sc_material_inbound"),
    ("action_sc_material_outbound", "view_sc_material_outbound_form", "menu_sc_material_outbound"),
)
if topic == "document":
    identities = (("action_sc_certificate_registration", "view_sc_document_admin_document_form", "menu_sc_certificate_registration"),
                  ("action_sc_product_policy_document_v1", "view_sc_document_admin_document_form", "menu_sc_product_policy_document_v1"))
if topic == "invoice":
    # U-C4 G02: four formal invoice entries (785 input, 786 output application,
    # 787 output registration, 788 prepaid tax) share model sc.invoice.registration
    # and form view 1651; the last two identities are the shared-form bypass
    # actions (789 input tax report, 639 invoice general ledger) which must keep
    # working on the rebuilt native form without legacy section projections.
    identities = (
        ("action_sc_invoice_input", "view_sc_invoice_registration_form", "menu_sc_invoice_input"),
        ("action_sc_invoice_registration_user", "view_sc_invoice_registration_form", "menu_sc_invoice_registration_user"),
        ("action_sc_invoice_application_user", "view_sc_invoice_registration_form", "menu_sc_invoice_application_user"),
        ("action_sc_invoice_prepaid_tax_user", "view_sc_invoice_registration_form", "menu_sc_invoice_prepaid_tax_user"),
        ("action_sc_invoice_input_report_user", "view_sc_invoice_registration_form", "menu_sc_invoice_input_report_user"),
        ("action_sc_invoice_registration", "view_sc_invoice_registration_form", "menu_sc_invoice_registration"),
    )
invoice_sample_fields = ["direction", "source_kind", "source_origin"] if topic == "invoice" else []
for action_xmlid, view_xmlid, menu_xmlid in identities:
    action, view, menu = [env.ref("smart_construction_core." + key) for key in (action_xmlid, view_xmlid, menu_xmlid)]
    if menu.action != action or view.model != action.res_model:
        raise RuntimeError("formal menu/action/view identity mismatch")
    model = principal[action.res_model]
    model.check_access_rights("read")
    rows = model.search([], order="id").read(["write_date", "state"])
    from odoo.tools.safe_eval import safe_eval
    domain = safe_eval(action.domain or "[]")
    samples = model.search(domain, order="id", limit=3).read(["display_name", "state"] + invoice_sample_fields + (["legacy_document_no", "legacy_document_state", "legacy_source_table", "legacy_source_id"] if topic == "document" else []))
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
print("FORM_LOWCODE_SCOPE=" + json.dumps({
    "configuration_inventory": inventory, "configuration_entry": configuration_entry, "topic": topic, "database": env.cr.dbname, "company_id": user.company_id.id, "user_id": user.id, "login": user.login,
    "role_key": resolver.resolve_role_code(resolver.user_group_xmlids(user)), "entries": entries,
    "runtime_revision": os.environ.get("SC_SOURCE_REVISION", "unknown"),
    "compiler_sha256": hashlib.sha256(Path(inspect.getfile(form_configuration_compiler)).read_bytes()).hexdigest(),
}, default=str, sort_keys=True))
