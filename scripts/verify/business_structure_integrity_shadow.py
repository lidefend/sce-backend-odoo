# -*- coding: utf-8 -*-
"""Shadow report for business structure integrity (BNVA-02B-02A).

Diagnostic-only.  It runs the pure validator against the five known samples
extracted from addons/smart_construction_core/data/
view_orchestration_form_section_contract_data.xml at the BNVA-02B-01 head.
It never changes publication behaviour and writes one JSON report.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "addons"))

from smart_core.core.business_structure_integrity import (  # noqa: E402
    validate_business_structure,
    extract_compatibility,
    publication_gate,
)


SAMPLES = {
    "project.project 590/1776": {
        "model_fields": {"name": {}, "project_code": {}, "user_id": {}, "manager_id": {}, "owner_id": {}},
        "configs": [
            {
                "name": "project_project_form_structure_v1",
                "payload": {"view_orchestration": {"views": {"form": {
                    "title": "项目立项", "composition_mode": "native_semantic_surface",
                }}}},
            },
            {
                "name": "project_project_overview_form_structure_v1",
                "payload": {"view_orchestration": {"views": {"form": {
                    "identity_fields": ["name", "project_code", "user_id", "manager_id", "owner_id"],
                }}}},
            },
        ],
    },
    "project.project 652/944": {
        "model_fields": {"name": {}, "project_code": {}},
        "configs": [],
    },
    "payment.request 649/1773": {
        "model_fields": {"name": {}, "partner_id": {}, "project_id": {}, "amount": {}},
        "configs": [
            {
                "name": "payment_request_form_sections_v1",
                "payload": {"view_orchestration": {"views": {"form": {}}}},
            },
        ],
    },
    "sc.payment.execution 709/1658": {
        "model_fields": {"name": {}, "amount": {}},
        "configs": [
            {
                "name": "sc_payment_execution_form_sections_v1",
                "payload": {"view_orchestration": {"views": {"form": {
                    "composition_mode": "entry_semantic_surface",
                    "sections": [
                        {"title": "办理类型"}, {"title": "付款依据"}, {"title": "付款金额"},
                        {"title": "收款账户"}, {"title": "付款账户"}, {"title": "办理说明"},
                        {"title": "公司-承包人资金责任"}, {"title": "来源与系统追溯"},
                    ],
                }}}},
            },
        ],
    },
    "sc.receipt.income 708/1655": {
        "model_fields": {"name": {}, "amount": {}},
        "configs": [
            {
                "name": "sc_receipt_income_form_sections_v1",
                "payload": {"view_orchestration": {"views": {"form": {
                    "composition_mode": "entry_semantic_surface",
                    "sections": [
                        {"title": "工程款确认"}, {"title": "代扣代缴明细"}, {"title": "施工队明细"},
                    ],
                }}}},
            },
        ],
    },
}


def _form_spec(payload):
    return ((payload.get("view_orchestration") or {}).get("views") or {}).get("form") or {}


def _merge(configs):
    spec: dict = {}
    sections: list = []
    identity_fields: list = []
    for config in configs:
        form = _form_spec(config["payload"])
        for key in ("composition_mode", "compositionMode", "title"):
            if form.get(key) and key not in spec:
                spec[key] = form[key]
        if isinstance(form.get("sections"), list):
            sections.extend(form["sections"])
        if isinstance(form.get("identity_fields"), list):
            identity_fields.extend(form["identity_fields"])
    if sections:
        spec["sections"] = sections
    if identity_fields:
        spec["identity_fields"] = identity_fields
    return spec


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(ROOT / "artifacts" / "backend" / "business_structure_integrity_shadow.json"))
    args = parser.parse_args()

    report = {"schema_version": 1, "samples": []}
    for sample, data in SAMPLES.items():
        rows = []
        for config in data["configs"]:
            rows.append({
                "config": config["name"],
                "diagnostics": validate_business_structure(
                    config["payload"], model_fields=data["model_fields"],
                ),
            })
        merged_diagnostics = []
        merged_gate = None
        if data["configs"]:
            merged_diagnostics = validate_business_structure(
                {"view_orchestration": {"views": {"form": _merge(data["configs"])}}},
                model_fields=data["model_fields"],
            )
            merged_gate = publication_gate(
                merged_diagnostics,
                compatibility=extract_compatibility(
                    {"view_orchestration": {"views": {"form": _merge(data["configs"])}}}
                ),
            )
        report["samples"].append({
            "sample": sample,
            "configs": rows,
            "merged_diagnostics": merged_diagnostics,
            "merged_gate": merged_gate,
        })

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("[business_structure_integrity_shadow] wrote %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
