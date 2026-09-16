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
if topic not in {"material", "document"}:
    raise RuntimeError("unregistered formal form topic")
entries = []
identities = (
    ("action_sc_material_inbound_handling", "view_sc_material_inbound_form", "menu_sc_material_inbound"),
    ("action_sc_material_outbound", "view_sc_material_outbound_form", "menu_sc_material_outbound"),
)
if topic == "document":
    identities = (("action_sc_certificate_registration", "view_sc_document_admin_document_form", "menu_sc_certificate_registration"),
                  ("action_sc_product_policy_document_v1", "view_sc_document_admin_document_form", "menu_sc_product_policy_document_v1"))
for action_xmlid, view_xmlid, menu_xmlid in identities:
    action, view, menu = [env.ref("smart_construction_core." + key) for key in (action_xmlid, view_xmlid, menu_xmlid)]
    if menu.action != action or view.model != action.res_model:
        raise RuntimeError("formal menu/action/view identity mismatch")
    model = principal[action.res_model]
    model.check_access_rights("read")
    rows = model.search([], order="id").read(["write_date", "state"])
    from odoo.tools.safe_eval import safe_eval
    domain = safe_eval(action.domain or "[]")
    samples = model.search(domain, order="id", limit=3).read(["display_name", "state"] + (["legacy_document_no", "legacy_document_state", "legacy_source_table", "legacy_source_id"] if topic == "document" else []))
    entries.append({"samples": samples, "action_groups": action.groups_id.get_external_id(), "action_context": action.context, "domain": action.domain, "model": action.res_model, "action_id": action.id, "view_id": view.id, "menu_id": menu.id,
                    "business_fingerprint": hashlib.sha256(json.dumps(rows, default=str, sort_keys=True).encode()).hexdigest()})
print("FORM_LOWCODE_SCOPE=" + json.dumps({
    "topic": topic, "database": env.cr.dbname, "company_id": user.company_id.id, "user_id": user.id, "login": user.login,
    "role_key": resolver.resolve_role_code(resolver.user_group_xmlids(user)), "entries": entries,
    "runtime_revision": os.environ.get("SC_SOURCE_REVISION", "unknown"),
    "compiler_sha256": hashlib.sha256(Path(inspect.getfile(form_configuration_compiler)).read_bytes()).hexdigest(),
}, sort_keys=True))
