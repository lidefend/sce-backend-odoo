# -*- coding: utf-8 -*-
"""Read-only Odoo shell gate: declared field-policy parity across form contracts.

Run with:
  ENV=dev DB_NAME=sc_dev_demo make verify.business_config.field_policy_declaration_parity

Rule
----
A *model-wide* form contract (no ``action_id``, so it governs every surface of
the model) must not declare an unconditional ``readonly: True`` fact on a field
that the model's action-scoped entry contracts declare and none of them declares
read-only.

Such a declaration disagrees with the entry that owns the surface.  The
orchestrator only ever tightens a field fact
(``view_orchestrator._apply_field_display_policy``), so the model-wide
``readonly: True`` flattens the delivered field node while
``statusContract.widgetStatus`` keeps the native modifier's answer (``auth=edit``).
The two projections of one delivered fact then disagree, and the renderer's
read-only fact rule (``readonlyFactIsPresentable``) can drop the field from the
body entirely.

The model-wide ``business_facts`` bodies are still the only carrier of the
read-only policy for the ``*_display`` mirror facts, which no entry contract
declares, so this gate narrows the contradicting declarations instead of
retiring a body.

The script expects the global ``env`` object from ``odoo shell``.
"""

import json
import os

from odoo.exceptions import UserError

REPORT_ENV = "BUSINESS_CONFIG_FIELD_POLICY_PARITY_REPORT_PATH"
DEFAULT_REPORT_PATH = "/tmp/business_config_field_policy_declaration_parity.json"


def _env():
    return globals()["env"]


def _declared_fields(contract):
    spec = (((contract.contract_json or {}).get("view_orchestration") or {}).get("views") or {}).get("form") or {}
    rows = spec.get("fields") or spec.get("field_slots") or []
    if not isinstance(rows, list):
        return {}
    out = {}
    for row in rows:
        if isinstance(row, dict) and row.get("name"):
            out[str(row["name"])] = row
    return out


def collect(env_obj):
    Contract = env_obj["ui.business.config.contract"]
    contracts = Contract.with_context(active_test=False).search([("view_type", "=", "form"), ("active", "=", True)])

    model_wide = {}
    entries = {}
    for contract in contracts:
        declared = _declared_fields(contract)
        if not declared:
            continue
        bucket = model_wide if not contract.action_id else entries
        bucket.setdefault(contract.model, []).append((contract, declared))

    contradictions = []
    for model in sorted(model_wide):
        model_entries = entries.get(model) or []
        if not model_entries:
            continue
        entry_declared = set()
        entry_readonly = set()
        for _contract, declared in model_entries:
            for name, row in declared.items():
                entry_declared.add(name)
                if row.get("readonly") is True:
                    entry_readonly.add(name)
        for contract, declared in model_wide[model]:
            for name, row in declared.items():
                if row.get("readonly") is not True:
                    continue
                if name not in entry_declared or name in entry_readonly:
                    continue
                editable_entries = [
                    entry.name for entry, entry_declared_rows in model_entries
                    if name in entry_declared_rows and entry_declared_rows[name].get("readonly") is not True
                ]
                contradictions.append({
                    "model": model,
                    "model_wide_contract": contract.name,
                    "model_wide_contract_id": contract.id,
                    "model_wide_priority": contract.priority,
                    "field": name,
                    "entry_contracts_declaring_editable": editable_entries,
                    "entry_contract_count": len(model_entries),
                })
    return {
        "database": env_obj.cr.dbname,
        "model_count_with_model_wide_policy": len(model_wide),
        "entry_model_count": len(entries),
        "contradiction_count": len(contradictions),
        "contradictions": contradictions,
    }


def main():
    env_obj = _env()
    report = collect(env_obj)
    report_path = os.getenv(REPORT_ENV, DEFAULT_REPORT_PATH)
    if report_path:
        report_dir = os.path.dirname(report_path)
        if report_dir:
            os.makedirs(report_dir, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    failed = report["contradictions"]
    print("[business_config_field_policy_declaration_parity] %s (contradictions=%d)"
          % ("FAIL" if failed else "PASS", report["contradiction_count"]))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if failed:
        summary = ", ".join("%s.%s@%s" % (row["model"], row["field"], row["model_wide_contract"])
                            for row in failed[:10])
        raise UserError(
            "模型级表单契约以无条件只读声明覆盖了入口契约声明的可编辑字段：%s" % summary
        )


main()
