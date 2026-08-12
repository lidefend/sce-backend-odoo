#!/usr/bin/env python3
from __future__ import annotations

import unittest

from scripts.verify.form_information_architecture_audit import _audit_record


def _record(*, sections: list[dict], fields: list[dict], title: str = "付款申请") -> dict:
    return {
        "record_id": "test_contract",
        "path": "test.xml",
        "model": "test.document",
        "action_ref": "test.action",
        "title": title,
        "columns": 2,
        "sections": sections,
        "fields": fields,
    }


class FormInformationArchitectureAuditTest(unittest.TestCase):
    def test_visible_trace_fields_are_p0(self) -> None:
        result = _audit_record(
            _record(
                sections=[
                    {"title": "付款事项", "fields": ["name", "amount"]},
                    {"title": "来源追溯", "fields": ["legacy_source_table", "active"]},
                    {"title": "附件凭证", "fields": ["attachment_ids"]},
                ],
                fields=[
                    {"name": "name"},
                    {"name": "amount"},
                    {"name": "legacy_source_table", "readonly": True},
                    {"name": "active"},
                    {"name": "attachment_ids"},
                ],
            )
        )
        self.assertEqual(result["severity"], "P0")
        self.assertIn("legacy_source_table", result["visible_technical_fields"])
        self.assertIn("来源追溯", result["visible_trace_sections"])

    def test_hidden_trace_fields_do_not_pollute_surface(self) -> None:
        result = _audit_record(
            _record(
                sections=[
                    {"title": "付款事项", "fields": ["name", "amount"]},
                    {"title": "附件凭证", "fields": ["attachment_ids"]},
                ],
                fields=[
                    {"name": "name"},
                    {"name": "amount"},
                    {"name": "attachment_ids"},
                    {"name": "legacy_source_table", "visible": False},
                ],
            )
        )
        self.assertEqual(result["severity"], "PASS")
        self.assertEqual(result["visible_technical_fields"], [])

    def test_generic_first_section_and_mixed_evidence_are_p1(self) -> None:
        result = _audit_record(
            _record(
                sections=[
                    {"title": "办理主信息", "fields": ["name", "state"]},
                    {"title": "说明与附件", "fields": ["note", "attachment_ids"]},
                ],
                fields=[
                    {"name": "name"},
                    {"name": "state"},
                    {"name": "note"},
                    {"name": "attachment_ids"},
                ],
            )
        )
        codes = {item["code"] for item in result["issues"]}
        self.assertEqual(result["severity"], "P1")
        self.assertIn("generic_first_section_not_entry_specific", codes)
        self.assertIn("attachments_and_long_text_mixed", codes)

    def test_task_oriented_document_can_pass(self) -> None:
        result = _audit_record(
            _record(
                sections=[
                    {"title": "付款对象与项目", "fields": ["name", "project_id", "partner_id"]},
                    {"title": "付款金额与日期", "fields": ["amount", "payment_date"]},
                    {"title": "办理说明", "fields": ["note"]},
                    {"title": "附件凭证", "fields": ["attachment_ids"]},
                ],
                fields=[
                    {"name": "name"},
                    {"name": "project_id"},
                    {"name": "partner_id"},
                    {"name": "amount"},
                    {"name": "payment_date"},
                    {"name": "note"},
                    {"name": "attachment_ids"},
                ],
            )
        )
        self.assertEqual(result["severity"], "PASS")
        self.assertEqual(result["issues"], [])


if __name__ == "__main__":
    unittest.main()
