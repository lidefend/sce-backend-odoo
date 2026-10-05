#!/usr/bin/env python3
"""Guard formal visible field ownership across core and custom modules.

Business operation model fields and released business list views belong to
smart_construction_core. User-specific preferences, history, and customer-only
acceptance surfaces belong to smart_construction_custom. Each audited surface
declares its owner explicitly so boundary changes are intentional.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


ADDON_ROOT_CANDIDATES = [
    Path("/mnt/source-addons"),
    Path("/mnt/customer-addons"),
    Path("/mnt/extra-addons"),
    Path.cwd() / "addons",
]
REPO_ROOT_CANDIDATES = [Path.cwd()]
CORE_ADDON = Path("smart_construction_core")
CUSTOM_ADDON = Path("smart_construction_custom")

BOUNDARY_CASES = [
    {
        "name": "付款还保证金",
        "model": "tender.guarantee",
        "owner": "core",
        "action_xmlid": "smart_construction_core.action_tender_guarantee_formal_payment_deposit_return",
        "expected_view_xmlid": "smart_construction_core.view_tender_guarantee_formal_payment_deposit_return_tree",
        "fields": [
            "deposit_status_display",
            "deposit_push_result",
            "deposit_kingdee_document_no",
            "deposit_document_no",
            "deposit_bid_project_name",
            "deposit_engineering_project_name",
            "deposit_type_display",
            "deposit_company_name",
            "deposit_amount_display",
            "deposit_returned_amount_display",
            "deposit_unreturned_amount_display",
            "deposit_need_return_text",
            "deposit_payee_unit",
            "deposit_payment_account",
            "deposit_note_display",
            "deposit_attachment_text",
            "deposit_source_created_by",
            "deposit_source_created_at",
        ],
    },
    {
        "name": "报价单",
        "model": "sc.material.rfq",
        "owner": "core",
        "action_xmlid": "smart_construction_core.action_sc_material_quote_user_confirmed",
        "expected_view_xmlid": "smart_construction_core.view_sc_material_rfq_quote_formal_tree",
        "fields": [
            "state",
            "name",
            "selected_supplier_id",
            "rfq_date",
            "due_date",
            "project_id",
            "owner_id",
            "contact_name",
            "contact_phone",
            "attachment_ids",
        ],
    },
    {
        "name": "往来单位付款",
        "model": "sc.payment.execution",
        "owner": "core",
        "action_xmlid": "smart_construction_core.action_sc_payment_execution_partner_payment",
        "expected_view_xmlid": "smart_construction_core.view_sc_payment_execution_partner_formal_tree",
        "fields": [
            "partner_payment_status_display",
            "partner_payment_date_display",
            "partner_payment_payee_unit",
            "partner_payment_actual_payee_unit",
            "partner_payment_amount_display",
            "partner_payment_category_display",
            "partner_payment_content_display",
            "partner_payment_method_display",
            "partner_payment_cost_type_display",
            "partner_payment_account_name_display",
            "partner_payment_attachment_text",
            "partner_payment_voucher_no",
            "partner_payment_writer",
            "partner_payment_source_created_by",
            "partner_payment_project_name",
            "partner_payment_source_text",
            "partner_payment_document_no",
        ],
    },
    {
        "name": "公司财务支出",
        "model": "sc.payment.execution",
        "owner": "core",
        "action_xmlid": "smart_construction_core.action_sc_payment_execution_company_finance_expense",
        "expected_view_xmlid": "smart_construction_core.view_sc_payment_execution_formal_company_finance_expense_tree",
        "fields": [
            "company_finance_status_display",
            "company_finance_push_result",
            "company_finance_document_no",
            "company_finance_amount_display",
            "company_finance_cost_type_display",
            "company_finance_payee_unit",
            "company_finance_payment_account_name",
            "company_finance_note_display",
            "company_finance_source_created_by",
            "company_finance_source_created_at",
            "company_finance_attachment_text",
        ],
    },
    {
        "name": "扣款单",
        "model": "sc.tax.deduction.registration",
        "owner": "core",
        "action_xmlid": "smart_construction_core.action_sc_tax_deduction_registration_deduction_bill_acceptance",
        "expected_view_xmlid": "smart_construction_core.view_sc_tax_deduction_registration_formal_deduction_bill_tree",
        "fields": [
            "deduction_bill_status_display",
            "deduction_bill_document_no",
            "deduction_bill_project_name",
            "deduction_bill_unit_name",
            "deduction_bill_amount_display",
            "deduction_bill_reason_display",
            "deduction_bill_date_display",
            "deduction_bill_attachment_text",
            "deduction_bill_source_created_by",
            "deduction_bill_source_created_at",
        ],
    },
]


def _find_addon_root(addon: Path) -> Path | None:
    for candidate in ADDON_ROOT_CANDIDATES:
        if (candidate / addon).exists():
            return candidate
    return None


def _addon_root(addon: Path) -> Path:
    root = _find_addon_root(addon)
    if root is not None:
        return root
    raise FileNotFoundError(f"Cannot locate addon root for {addon}")


def _display_path(path: Path) -> str:
    addon_roots = [
        root
        for addon in (CORE_ADDON, CUSTOM_ADDON)
        if (root := _find_addon_root(addon)) is not None
    ]
    for candidate in [*_repo_root_candidates(), *addon_roots]:
        try:
            return str(path.relative_to(candidate))
        except ValueError:
            continue
    return str(path)


def _repo_root_candidates() -> list[Path]:
    roots = []
    for candidate in REPO_ROOT_CANDIDATES:
        if (candidate / "addons" / CORE_ADDON).exists():
            roots.append(candidate)
    return roots


def _iter_source_files(base: Path):
    for suffix in ("*.py", "*.xml"):
        yield from base.rglob(suffix)


# A boundary field is owned by exactly one module. Presence is proven by a real
# field declaration or a view field reference, never by a bare substring: the
# generic names used on user-confirmed surfaces (`name`, `state`, `note`, ...)
# otherwise collide with unrelated metadata such as a manifest's ``name`` key.
PYTHON_FIELD_DECLARATION = r"(?m)^\s*{field}\s*=\s*fields\."
XML_FIELD_REFERENCE = r"<field\b[^>]*\bname\s*=\s*[\"']{field}[\"']"


def _field_reference_pattern(field_name: str, suffix: str) -> re.Pattern[str]:
    template = XML_FIELD_REFERENCE if suffix == ".xml" else PYTHON_FIELD_DECLARATION
    return re.compile(template.format(field=re.escape(field_name)))


_SOURCE_TEXT_CACHE: dict[Path, str] = {}


def _source_text(path: Path) -> str:
    if path not in _SOURCE_TEXT_CACHE:
        _SOURCE_TEXT_CACHE[path] = path.read_text(encoding="utf-8", errors="ignore")
    return _SOURCE_TEXT_CACHE[path]


def _field_present_in_files(files: list[Path], field_name: str) -> list[Path]:
    return [
        path
        for path in files
        if _field_reference_pattern(field_name, path.suffix).search(_source_text(path))
    ]


def _scan_static(
    core_addon_root: Path,
    custom_addon_root: Path | None,
    cases: list[dict] | None = None,
) -> list[dict]:
    failures = []
    cases = BOUNDARY_CASES if cases is None else cases
    core = core_addon_root / CORE_ADDON
    custom = custom_addon_root / CUSTOM_ADDON if custom_addon_root else None
    custom_files = list(_iter_source_files(custom)) if custom else []
    if custom is None and any(case.get("owner") == "custom" for case in cases):
        failures.append({
            "type": "custom_source_unavailable",
            "message": "custom-owned boundary cases require smart_construction_custom source",
        })
    core_files = list(_iter_source_files(core))

    for case in cases:
        owner = case.get("owner")
        for field_name in case["fields"]:
            if owner == "custom":
                if not _field_present_in_files(custom_files, field_name):
                    failures.append({
                        "type": "missing_custom_owner",
                        "case": case["name"],
                        "field": field_name,
                    })
                for path in _field_present_in_files(core_files, field_name):
                    failures.append({
                        "type": "core_user_field_leak",
                        "case": case["name"],
                        "field": field_name,
                        "path": _display_path(path),
                    })
            elif owner == "core":
                if not _field_present_in_files(core_files, field_name):
                    failures.append({
                        "type": "missing_core_owner",
                        "case": case["name"],
                        "field": field_name,
                    })
                for path in _field_present_in_files(custom_files, field_name):
                    failures.append({
                        "type": "custom_business_field_leak",
                        "case": case["name"],
                        "field": field_name,
                        "path": _display_path(path),
                    })
            else:
                failures.append({
                    "type": "unknown_owner",
                    "case": case["name"],
                    "owner": owner,
                })
    return failures


def _runtime_rows() -> tuple[list[dict], list[dict]]:
    if "env" not in globals():
        return [], []

    rows = []
    failures = []
    for case in BOUNDARY_CASES:
        action = env.ref(case["action_xmlid"])  # noqa: F821
        view_xmlid = action.view_id.get_external_id().get(action.view_id.id, "") if action.view_id else ""
        model = env[case["model"]]  # noqa: F821
        missing_fields = [field for field in case["fields"] if field not in model._fields]
        rows.append({
            "case": case["name"],
            "action_xmlid": case["action_xmlid"],
            "runtime_view_xmlid": view_xmlid,
            "expected_view_xmlid": case["expected_view_xmlid"],
            "missing_fields": missing_fields,
            "owner": case["owner"],
        })
        if view_xmlid != case["expected_view_xmlid"]:
            failures.append({
                "type": "runtime_action_view_owner_mismatch",
                "case": case["name"],
                "actual": view_xmlid,
                "expected": case["expected_view_xmlid"],
            })
        for field_name in missing_fields:
            failures.append({
                "type": "runtime_missing_custom_field",
                "case": case["name"],
                "field": field_name,
            })
    return rows, failures


def main() -> None:
    core_addon_root = _addon_root(CORE_ADDON)
    custom_addon_root = _find_addon_root(CUSTOM_ADDON)
    failures = _scan_static(core_addon_root, custom_addon_root)
    runtime_rows, runtime_failures = _runtime_rows()
    failures.extend(runtime_failures)

    payload = {
        "audit": "user_formal_field_module_boundary_audit",
        "status": "PASS" if not failures else "FAIL",
        "failure_count": len(failures),
        "failures": failures,
        "runtime_rows": runtime_rows,
        "source_roots": {
            "core": str(core_addon_root),
            "custom": str(custom_addon_root) if custom_addon_root else None,
        },
    }
    print("USER_FORMAL_FIELD_MODULE_BOUNDARY_AUDIT=" + json.dumps(payload, ensure_ascii=False, sort_keys=True))
    if failures:
        raise RuntimeError(payload)


if __name__ == "__main__":
    main()
