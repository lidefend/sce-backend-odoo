#!/usr/bin/env python3
"""Read-only audit for formal business form information architecture.

The existing productization audit proves that an entry has fields, sections and
status context.  This audit answers the stricter product question: whether the
ordinary handler sees a task-oriented business document instead of a complete
technical record.
"""

from __future__ import annotations

import ast
import json
import re
from collections import Counter
from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = ROOT / "artifacts" / "frontend-form-information-architecture"

CONTRACT_GLOBS = (
    "addons/smart_construction_core/data/*form_productization_contract*.xml",
    "addons/smart_construction_core/data/view_orchestration_form_section_contract_data.xml",
)

ENTRY_SURFACE_MODES = {"entry_semantic_surface", "semantic_entry_surface"}
GENERIC_SECTION_TITLES = {
    "办理主信息",
    "基本信息",
    "主信息",
    "其它信息",
    "其他信息",
    "补充信息",
    "详情",
    "表单信息",
    "相关数据",
}
TRACE_SECTION_TOKENS = ("来源", "追溯", "迁移", "系统", "审计", "技术")
ATTACHMENT_TOKENS = ("attachment", "附件", "凭证", "影像", "图片", "文件")
LONG_TEXT_TOKENS = (
    "note",
    "remark",
    "description",
    "summary",
    "reason",
    "comment",
    "memo",
    "说明",
    "备注",
    "原因",
    "意见",
)
WORKFLOW_FIELD_NAMES = {
    "state",
    "status",
    "validation_status",
    "document_state",
    "workflow_state",
    "approval_status",
    "claim_flow_label",
    "payment_state",
}
TECHNICAL_EXACT_FIELDS = {
    "id",
    "active",
    "create_uid",
    "create_date",
    "write_uid",
    "write_date",
    "__last_update",
    "display_name",
    "can_review",
    "reviewer_ids",
    "review_ids",
    "next_review",
    "need_validation",
    "validated",
    "rejected",
    "has_comment",
}
TECHNICAL_PREFIXES = (
    "legacy_",
    "carrier_",
    "migration_",
    "replay_",
    "technical_",
    "audit_",
)


def _norm(value: object) -> str:
    return re.sub(r"\s+", "", str(value or "").strip())


def _is_visible(field: dict) -> bool:
    return field.get("visible", True) is not False


def _is_technical_field(name: str) -> bool:
    normalized = str(name or "").strip().lower()
    return normalized in TECHNICAL_EXACT_FIELDS or normalized.startswith(TECHNICAL_PREFIXES)


def _has_token(value: object, tokens: tuple[str, ...]) -> bool:
    lowered = str(value or "").strip().lower()
    return any(token.lower() in lowered for token in tokens)


def _contract_records() -> list[dict]:
    paths: set[Path] = set()
    for pattern in CONTRACT_GLOBS:
        paths.update(ROOT.glob(pattern))
    records: list[dict] = []
    for path in sorted(paths):
        root = ET.parse(path).getroot()
        for record in root.findall(".//record"):
            if record.attrib.get("model") != "ui.business.config.contract":
                continue
            fields = {node.attrib.get("name"): node for node in record.findall("field")}
            contract_node = fields.get("contract_json")
            if contract_node is None:
                continue
            raw = contract_node.attrib.get("eval") or contract_node.text or ""
            try:
                payload = ast.literal_eval(raw)
            except (SyntaxError, ValueError):
                continue
            orchestration = payload.get("view_orchestration") if isinstance(payload, dict) else None
            if not isinstance(orchestration, dict):
                continue
            context = orchestration.get("context") if isinstance(orchestration.get("context"), dict) else {}
            if "product_release" not in str(context.get("source") or "") and context.get("source_status") != "product_release":
                continue
            views = orchestration.get("views") if isinstance(orchestration.get("views"), dict) else {}
            form = views.get("form") if isinstance(views.get("form"), dict) else {}
            mode = str(form.get("composition_mode") or form.get("compositionMode") or "").strip()
            sections = form.get("sections") if isinstance(form.get("sections"), list) else []
            form_fields = form.get("fields") if isinstance(form.get("fields"), list) else []
            if mode not in ENTRY_SURFACE_MODES or not sections or not form_fields:
                continue
            model_node = fields.get("model")
            action_node = fields.get("action_id")
            records.append(
                {
                    "record_id": record.attrib.get("id") or "",
                    "path": str(path.relative_to(ROOT)),
                    "model": (model_node.text or "").strip() if model_node is not None else "",
                    "action_ref": action_node.attrib.get("ref", "") if action_node is not None else "",
                    "title": str(form.get("title") or "").strip(),
                    "columns": form.get("columns"),
                    "sections": sections,
                    "fields": form_fields,
                }
            )
    return records


def _audit_record(record: dict) -> dict:
    fields = [row for row in record["fields"] if isinstance(row, dict) and str(row.get("name") or "").strip()]
    field_map = {str(row["name"]).strip(): row for row in fields}
    visible_fields = [name for name, row in field_map.items() if _is_visible(row)]
    sections = [row for row in record["sections"] if isinstance(row, dict)]
    section_rows: list[dict] = []
    assigned: list[str] = []
    visible_technical: list[str] = []
    visible_trace_sections: list[str] = []
    attachment_sections: list[str] = []
    long_text_sections: list[str] = []
    mixed_evidence_text_sections: list[str] = []

    for index, section in enumerate(sections):
        title = str(section.get("title") or "").strip()
        names = [str(item).strip() for item in section.get("fields", []) if str(item).strip()]
        assigned.extend(names)
        visible_names = [name for name in names if name in field_map and _is_visible(field_map[name])]
        technical = [name for name in visible_names if _is_technical_field(name)]
        attachment_names = [name for name in visible_names if _has_token(name, ATTACHMENT_TOKENS)]
        long_text_names = [name for name in visible_names if _has_token(name, LONG_TEXT_TOKENS)]
        trace_named = _has_token(title, TRACE_SECTION_TOKENS)
        if technical:
            visible_technical.extend(technical)
        if trace_named and visible_names:
            visible_trace_sections.append(title)
        if attachment_names:
            attachment_sections.append(title)
        if long_text_names:
            long_text_sections.append(title)
        if attachment_names and long_text_names:
            mixed_evidence_text_sections.append(title)
        section_rows.append(
            {
                "index": index,
                "title": title,
                "field_count": len(names),
                "visible_field_count": len(visible_names),
                "visible_fields": visible_names,
                "visible_technical_fields": technical,
                "attachment_fields": attachment_names,
                "long_text_fields": long_text_names,
            }
        )

    first = section_rows[0] if section_rows else {}
    first_visible = list(first.get("visible_fields") or [])
    first_workflow_count = sum(1 for name in first_visible if name in WORKFLOW_FIELD_NAMES)
    unassigned_visible = [name for name in visible_fields if name not in assigned]
    generic_first = str(first.get("title") or "") in GENERIC_SECTION_TITLES
    trace_exposure = sorted(set(visible_technical))
    issues: list[dict] = []

    def add(code: str, severity: str, evidence: object) -> None:
        issues.append({"code": code, "severity": severity, "evidence": evidence})

    if trace_exposure:
        add("ordinary_surface_exposes_technical_fields", "P0", trace_exposure)
    if visible_trace_sections:
        add("ordinary_surface_contains_trace_section", "P0", sorted(set(visible_trace_sections)))
    if generic_first:
        add("generic_first_section_not_entry_specific", "P1", first.get("title"))
    if first_workflow_count >= 2:
        add("workflow_metadata_crowds_first_section", "P1", first_workflow_count)
    if len(first_visible) > 8:
        add("first_section_overloaded", "P1", len(first_visible))
    if len(sections) > 7:
        add("section_fragmentation", "P1", len(sections))
    if mixed_evidence_text_sections:
        add("attachments_and_long_text_mixed", "P1", sorted(set(mixed_evidence_text_sections)))
    if not attachment_sections:
        add("no_first_class_attachment_section", "P1", [])
    if unassigned_visible:
        add("visible_fields_outside_declared_sections", "P1", unassigned_visible)
    if not record.get("title"):
        add("missing_entry_title", "P1", record["record_id"])

    severity = "PASS"
    if any(item["severity"] == "P0" for item in issues):
        severity = "P0"
    elif any(item["severity"] == "P1" for item in issues):
        severity = "P1"

    return {
        "record_id": record["record_id"],
        "path": record["path"],
        "model": record["model"],
        "action_ref": record["action_ref"],
        "title": record["title"],
        "severity": severity,
        "field_count": len(fields),
        "visible_field_count": len(visible_fields),
        "section_count": len(sections),
        "first_section": first,
        "visible_technical_fields": trace_exposure,
        "visible_trace_sections": sorted(set(visible_trace_sections)),
        "attachment_sections": sorted(set(attachment_sections)),
        "long_text_sections": sorted(set(long_text_sections)),
        "mixed_evidence_text_sections": sorted(set(mixed_evidence_text_sections)),
        "unassigned_visible_fields": unassigned_visible,
        "issues": issues,
    }


def _write_markdown(payload: dict) -> None:
    summary = payload["summary"]
    rows = payload["rows"]
    lines = [
        "# Form Information Architecture Audit",
        "",
        "> Read-only static audit. A PASS here would mean task-oriented presentation; it does not merely mean that sections exist.",
        "",
        "## Summary",
        "",
        f"- audited product-release entry contracts: `{summary['entry_contract_count']}`",
        f"- P0: `{summary['by_severity'].get('P0', 0)}`",
        f"- P1: `{summary['by_severity'].get('P1', 0)}`",
        f"- PASS: `{summary['by_severity'].get('PASS', 0)}`",
        f"- visible technical/source-trace field occurrences: `{summary['visible_technical_field_occurrences']}`",
        f"- entries with ordinary trace sections: `{summary['entries_with_trace_sections']}`",
        f"- entries with generic first sections: `{summary['entries_with_generic_first_sections']}`",
        f"- entries mixing attachments and long text: `{summary['entries_mixing_attachments_and_long_text']}`",
        f"- entries without first-class attachments: `{summary['entries_without_first_class_attachments']}`",
        "",
        "## P0/P1 Queue",
        "",
        "| severity | entry | model | sections | visible fields | issues |",
        "|---|---|---|---:|---:|---|",
    ]
    for row in rows:
        if row["severity"] == "PASS":
            continue
        issue_codes = ", ".join(item["code"] for item in row["issues"])
        lines.append(
            f"| {row['severity']} | {row['title'] or row['record_id']} | `{row['model']}` | {row['section_count']} | {row['visible_field_count']} | {issue_codes} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- A dedicated source-trace section is still ordinary-user exposure unless a role/mode visibility policy proves otherwise.",
            "- A section title such as `办理主信息` is structural, not entry semantics; the first section must identify the actual task.",
            "- Attachments and long narrative text have different reading and action behavior and should not be treated as one generic field group.",
            "- Readonly presentation is audited separately at renderer/runtime level because current product-release contracts do not declare a readonly-specific information hierarchy.",
            "",
        ]
    )
    (OUT_ROOT / "form_information_architecture_audit.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    rows = [_audit_record(record) for record in _contract_records()]
    rows.sort(key=lambda row: ({"P0": 0, "P1": 1, "PASS": 2}[row["severity"]], row["model"], row["title"]))
    issue_counts = Counter(item["code"] for row in rows for item in row["issues"])
    summary = {
        "entry_contract_count": len(rows),
        "by_severity": dict(Counter(row["severity"] for row in rows)),
        "by_issue": dict(issue_counts.most_common()),
        "visible_technical_field_occurrences": sum(len(row["visible_technical_fields"]) for row in rows),
        "entries_with_trace_sections": sum(bool(row["visible_trace_sections"]) for row in rows),
        "entries_with_generic_first_sections": issue_counts.get("generic_first_section_not_entry_specific", 0),
        "entries_mixing_attachments_and_long_text": issue_counts.get("attachments_and_long_text_mixed", 0),
        "entries_without_first_class_attachments": issue_counts.get("no_first_class_attachment_section", 0),
    }
    payload = {
        "scope": "formal_product_release_form_information_architecture",
        "audit_mode": "static_read_only",
        "summary": summary,
        "global_findings": [
            {
                "severity": "P0",
                "code": "readonly_has_no_dedicated_projection_contract",
                "evidence": "render_profile changes editability, while the same layout node tree and field order are rendered for readonly mode",
            },
            {
                "severity": "P1",
                "code": "existing_gate_treats_section_presence_as_productization_pass",
                "evidence": "business_form_productization_audit records productized sections and source_trace_sectioned as acceptance evidence without ordinary-role visibility proof",
            },
        ],
        "rows": rows,
    }
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    (OUT_ROOT / "form_information_architecture_audit.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_markdown(payload)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    print(f"FORM_INFORMATION_ARCHITECTURE_AUDIT={OUT_ROOT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
