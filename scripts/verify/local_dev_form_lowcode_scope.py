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
    # U-C4 G03: 公司收入 (637 / menu 545) and 收入 (806 / menu 907) are the two
    # formal entries; 工程进度款收入登记 (807 / menu 908) is the shared-form
    # bypass entry and reaches form view 1644 through its action view_ids.  All
    # three consume the same rebuilt native form, so the read-only route keeps
    # them together.
    "receipt_income": (
        ("action_sc_receipt_income", "view_sc_receipt_income_form", "menu_sc_company_income"),
        ("action_sc_receipt_income_user_income", "view_sc_receipt_income_form", "menu_sc_user_income"),
        ("action_sc_receipt_income_engineering_progress", "view_sc_receipt_income_form", "menu_sc_engineering_progress_income"),
    ),
    # U-C4 G04: 实付登记 (837 / menu 339) and 公司财务支出 (808 / menu 547) are
    # the two formal entries; 往来单位付款 (811 / menu 561) is the shared-form
    # bypass entry and reaches form view 1647 through its action view_ids.  All
    # three consume the same rebuilt native form.
    "payment_execution": (
        ("action_sc_payment_execution_actual_outflow", "view_sc_payment_execution_form", "menu_sc_payment_execution"),
        ("action_sc_payment_execution_company_finance_expense", "view_sc_payment_execution_form", "menu_sc_company_finance_expense"),
        ("action_sc_payment_execution_partner_payment", "view_sc_payment_execution_form", "menu_sc_partner_payment"),
    ),
    # U-C4 G05: 报销申请 (792 / menu 578 / view 1633), 扣款登记 (798 / menu 563 /
    # view 1632) and 备用金 (793 / menu 575 / default view 1632) are the three
    # registered consumers of model sc.expense.claim.  Two of them carry a
    # released configuration; 备用金 has none and consumes the model-wide sparse
    # annotation over the shared native deduction form, so it is registered to
    # keep the shared-form reachability fact instead of being assumed.  Menu 543
    # (费用与保证金) reaches the same 1633 surface through a bypass route and is
    # tracked as a bypass consumer in the batch ledger rather than as an entry.
    "expense_claim": (
        ("action_sc_expense_claim_reimbursement_request", "view_sc_expense_claim_form", "menu_sc_reimbursement_request"),
        ("action_sc_expense_claim_deduction_bill", "view_sc_expense_claim_deduction_registration_form", "menu_sc_deduction_bill"),
        ("action_sc_expense_claim_advance_fund", "view_sc_expense_claim_deduction_registration_form", "menu_sc_advance_fund"),
    ),
    # U-C4 G06: 抵扣登记 (790 / menu 538) and 项目专项抵扣 (879 / menu 701) are the
    # two registered consumers of model sc.tax.deduction.registration.  Neither
    # action fixes a form view, so both resolve the model primary form
    # view_sc_tax_deduction_registration_form.  Action 852 (扣款单) reaches the
    # same primary form with records but fixes only a tree view, carries no
    # release of its own and has no menu of its own, so it is tracked as a
    # bypass consumer in the batch ledger instead of being registered as a
    # route that cannot be reached read-only.
    "tax_deduction": (
        ("action_sc_tax_deduction_registration_user", "view_sc_tax_deduction_registration_form", "menu_sc_tax_deduction_registration_user"),
        ("action_sc_product_project_tax_deduction_v1", "view_sc_tax_deduction_registration_form", "menu_sc_product_project_tax_deduction_v1"),
    ),
    # U-C4 G07: the 人事薪酬 group shares model sc.hr.payroll.document and the
    # native primary form view_sc_hr_payroll_document_form; 874 consumes
    # sc.hr.salary.payment and view_sc_hr_salary_payment_form.  Entry 858
    # (工资薪酬 / menu 673) carried no release of its own and used to fall back
    # to the model-wide sparse annotation while its siblings consumed the
    # business task surface; 660/661/662/663/664 are the archived entries that
    # reach the same shared body through their own menus.  Registered read-only
    # so the representative pass observes every entry consuming one shared body.
    "payroll": (
        ("action_sc_payroll_management", "view_sc_hr_payroll_document_form", "menu_sc_payroll_management"),
        ("action_sc_product_project_payroll_v1", "view_sc_hr_payroll_document_form", "menu_sc_product_project_payroll_v1"),
        ("action_sc_product_social_fund_v1", "view_sc_hr_payroll_document_form", "menu_sc_product_social_fund_v1"),
        ("action_sc_salary_registration", "view_sc_hr_payroll_document_form", "menu_sc_salary_registration"),
        ("action_sc_social_person_registration", "view_sc_hr_payroll_document_form", "menu_sc_social_person_registration"),
        ("action_sc_social_registration", "view_sc_hr_payroll_document_form", "menu_sc_social_registration"),
        ("action_sc_subsidy", "view_sc_hr_payroll_document_form", "menu_sc_subsidy"),
        ("action_sc_bonus", "view_sc_hr_payroll_document_form", "menu_sc_bonus"),
        ("action_sc_product_project_salary_payment_v1", "view_sc_hr_salary_payment_form", "menu_sc_product_project_salary_payment_v1"),
    ),
}
TOPIC_SAMPLE_FIELDS = {
    "invoice": ["direction", "source_kind", "source_origin", "note"],
    "payment": ["amount", "state"],
    "customer": ["name", "active"],
    "contract": ["state"],
    "settlement": ["state"],
    "receipt_income": ["state", "source_origin", "source_kind"],
    "payment_execution": ["state", "source_kind", "payment_family"],
    "expense_claim": ["state", "source_origin", "claim_type", "claim_flow_label"],
    "tax_deduction": ["state", "deduction_scope", "deduction_flow_label", "source_origin"],
    "payroll": ["state", "fact_type", "period_year", "period_month", "legacy_document_no"],
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
    # U-C4 G03: the receipt/income rebuild adds `data-sc-anchor` groups and moves
    # the source-trace facts into one section, so the same read-only battery is
    # the mechanism assertion for this topic: every 章节入口 must resolve and
    # reveal its target, and the command bar / navigation / body bands must stay
    # separated at 1088 and 390.
    # `record_surface` additionally replays the same battery on the governed
    # sample so the container conditions that can only resolve on an existing
    # record (责任余额 page keyed on the responsibility summary, 台账 page keyed
    # on the treasury ledger) are observed as legal hiding instead of being
    # reported as a lost fact.  Read-only.
    "receipt_income": {"section_navigation": True, "record_surface": True},
    # U-C4 G04: the payment-execution rebuild adds nine `data-sc-anchor`
    # business sections (one of them conditional on the legacy source state) and
    # keeps three untitled column containers as layout wrappers.  The same
    # read-only battery is the mechanism assertion: every 章节入口 resolves and
    # reveals its target, and the command bar / navigation / body bands stay
    # separated at 1088 and 390.  `record_surface` replays it on the governed
    # sample so the conditional source-trace section is observed as legal hiding
    # instead of a lost fact.  Read-only; no change set is touched.
    "payment_execution": {"section_navigation": True, "record_surface": True},
    # U-C4 G05: the expense-claim rebuild adds nine `data-sc-anchor` sections to
    # the shared deduction form and ten to the claim form, recovers the declared
    # facts the retired entry bodies owned, and keeps the two untitled column
    # wrappers and the tab-owned sections as layout.  The same read-only battery
    # is the mechanism assertion; `record_surface` replays it on the governed
    # sample so the conditional source-trace page and the hidden deposit section
    # are observed as legal hiding instead of a lost fact.  Read-only; no change
    # set is touched.
    "expense_claim": {"section_navigation": True, "record_surface": True},
    # U-C4 G06: the tax-deduction rebuild adds eight `data-sc-anchor` business
    # sections to the shared primary form (seven titled sections plus the source
    # trace inside the conditional 迁移来源 page), recovers the declared facts the
    # retired entry bodies owned, and keeps the untitled column wrapper as
    # layout.  The same read-only battery is the mechanism assertion: every
    # 章节入口 must resolve and reveal its target, and the command bar /
    # navigation / body bands must stay separated.  The responsibility page and
    # the provenance page are conditional on the record itself, so
    # `record_surface` replays the battery on the governed sample of the same
    # action; action 879 has an empty domain and is recorded as an uncovered
    # record surface instead of being silently shortened.  Read-only; no change
    # set is touched.
    #
    # G06 正文整改: the two attachment expressions the retired legacy bill bodies
    # declared repeated the attachment fact inside the same 办理说明与附件
    # context the native carrier `attachment_ids` already presents, so they are
    # excluded from the body while staying declared for the scenarios that own
    # them (`deduction_bill_attachment_text` sums on the formal deduction bill
    # tree; `message_attachment_count` is the mail counter the collaboration
    # panel presents).  The check asserts the behaviour - the copy is neither a
    # render-tree field node nor a rendered DOM field, the copy stays declared
    # in the contract, and the canonical carrier keeps its single entry - so a
    # later regression that unions either copy back into the body fails here
    # instead of relying on a name/suffix guess.  Read-only.
    "tax_deduction": {
        "section_navigation": True,
        "record_surface": True,
        "display_copy_out_of_body": ["deduction_bill_attachment_text", "message_attachment_count"],
        "require_render": ["attachment_ids"],
        # G06 空态整改: the empty collection and the create entry have to
        # describe the same capability.  Action 879 has an empty action domain,
        # so its list route is the surface that showed a copy claiming the
        # account had no create right while the page header still opened the
        # create form.  The check reads the delivered list page: while a usable
        # create entry is present the empty copy must not claim the account
        # cannot create, and without one it must not invite the user to create.
        # Read-only; no record is written.
        "empty_list_state": True,
        # G06 字段职责: the retired model-wide P1 fact declaration
        # (`sc_tax_deduction_registration_p1_form_business_facts_v1`) marked
        # `invoice_no`, `deduction_amount`, `deduction_tax_amount`,
        # `deduction_surcharge_amount` and `note` unconditionally read-only,
        # while the rebuilt native body declares them read-only only at
        # `state == 'legacy_confirmed'`.  That body is retired now, so this is a
        # regression guard: the browser check asks the rendered page instead of
        # the declarations, and a fact the delivered create profile requires has
        # to expose a control the user can actually fill.
        "required_fillable": True,
    },
    # U-C4 G07: the payroll/social-fund/shared-payment rebuild gives one shared
    # native body `data-sc-anchor` identities for the fact_type groups (社保 /
    # 工资 / 公积金 / 补助奖金), the personnel and handling facts, the
    # conditionally declared provenance section and the payment form's three
    # sections.  The same read-only battery is the mechanism assertion: every
    # 章节入口 must resolve and reveal its target, and the command bar /
    # navigation / body bands must stay separated at 1088 and 390.
    # `record_surface` replays the battery on the governed sample so the
    # conditional 历史来源 section is observed as legal hiding instead of a lost
    # fact.  Read-only; no change set is touched.
    "payroll": {"section_navigation": True, "record_surface": True},
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
    # A registered record surface can only be replayed on a sample this identity is
    # allowed to read.  Report why a sample is missing instead of letting the
    # representative pass skip the route silently: an action domain with zero rows is
    # a data fact, a non-empty domain the identity cannot read is a record-rule fact,
    # and both must stay distinguishable in the report and in the remaining-gap ledger.
    domain_rows = model.sudo().search_count(domain)
    sample_state = {
        "state": "available" if samples else ("record_rule_denied" if domain_rows else "empty_action_domain"),
        "domain_rows": domain_rows,
        "readable_samples": len(samples),
    }
    entries.append({"samples": samples, "sample_state": sample_state, "business_row_count": len(rows), "action_groups": action.groups_id.get_external_id(), "action_context": action.context, "domain": action.domain, "model": action.res_model, "action_id": action.id, "view_id": view.id, "menu_id": menu.id,
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
