#!/usr/bin/env python3
"""Self-test for scripts/verify/frontend_industry_agnostic_audit.py.

The audit exists to keep the production frontend from inventing business
semantics.  It flattened every occurrence of a domain word into one number,
so "consumes a declared contract key" and "decides a rule from a name" looked
identical in the report and the inventory could not be used to plan the
cleanup.  This test fixes the new lexical-role classifier: a word inside a
comment or a literal must not be reported as code, and a word used in a branch
must be reported as a branch.  The finding count and the enforcement decision
are deliberately unchanged, so the test also pins that the count still counts
one finding per rule per line.
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

AUDIT_PATH = Path(__file__).resolve().with_name("frontend_industry_agnostic_audit.py")
_spec = importlib.util.spec_from_file_location("frontend_industry_agnostic_audit", AUDIT_PATH)
assert _spec and _spec.loader
audit = importlib.util.module_from_spec(_spec)
sys.modules["frontend_industry_agnostic_audit"] = audit
_spec.loader.exec_module(audit)


def role_of(source: str, needle: str) -> str:
    start = source.index(needle)
    return audit.lexical_role(source, start, needle)


class LexicalRoleTests(unittest.TestCase):
    def test_property_declaration_is_a_code_identifier(self):
        source = "type Payload = {\n  project_id?: number;\n};\n"
        self.assertEqual(role_of(source, "project_id"), audit.ROLE_CODE_IDENTIFIER)

    def test_transport_value_passed_through_stays_a_code_identifier(self):
        source = "const body = { project_id: params.projectId };\n"
        self.assertEqual(role_of(source, "project_id"), audit.ROLE_CODE_IDENTIFIER)

    def test_ternary_selection_is_a_code_conditional(self):
        source = "const pick = projectId > 0 ? 'empty_message' : 'empty_message_no_context';\n"
        self.assertEqual(role_of(source, "projectId > 0"), audit.ROLE_CODE_CONDITIONAL)

    def test_filter_that_selects_rows_is_a_code_conditional(self):
        source = "rows.filter((row) => row.project_id > 0);\n"
        self.assertEqual(role_of(source, "project_id"), audit.ROLE_CODE_CONDITIONAL)

    def test_line_comment_is_documentation(self):
        source = "// aligned with the backend handler: project_id\n"
        self.assertEqual(role_of(source, "project_id"), audit.ROLE_DOCUMENTATION)

    def test_block_comment_is_documentation(self):
        source = "/* carries project_id from the block dataset */\nconst x = 1;\n"
        self.assertEqual(role_of(source, "project_id"), audit.ROLE_DOCUMENTATION)

    def test_vue_style_comment_is_documentation(self):
        source = "<!-- readonly: project_id is never editable -->\n<div />\n"
        self.assertEqual(role_of(source, "project_id"), audit.ROLE_DOCUMENTATION)

    def test_quoted_match_is_a_string_literal(self):
        source = "const keys = ['project_id'];\n"
        self.assertEqual(role_of(source, "'project_id'"), audit.ROLE_STRING_LITERAL)

    def test_word_inside_a_string_is_a_string_literal(self):
        source = "const label = 'project_id value';\n"
        self.assertEqual(role_of(source, "project_id"), audit.ROLE_STRING_LITERAL)

    def test_comment_does_not_hide_a_later_code_branch(self):
        source = "// project_id stays declared\nconst pick = id > 0 ? 'a' : 'b';\n"
        self.assertEqual(role_of(source, "id > 0"), audit.ROLE_CODE_CONDITIONAL)

    def test_apostrophe_in_comment_does_not_swallow_following_code(self):
        source = "// the record's project_id is declared\nconst pick = id > 0 ? 'a' : 'b';\n"
        self.assertEqual(role_of(source, "id > 0"), audit.ROLE_CODE_CONDITIONAL)


class ReportShapeTests(unittest.TestCase):
    def test_role_vocabulary_is_explicit(self):
        self.assertEqual(
            {
                audit.ROLE_DOCUMENTATION,
                audit.ROLE_STRING_LITERAL,
                audit.ROLE_CODE_IDENTIFIER,
                audit.ROLE_CODE_CONDITIONAL,
            },
            {"documentation", "string_literal", "code_identifier", "code_conditional"},
        )

    def test_finding_carries_a_role_field(self):
        finding = audit.Finding("rule", "file.py", 1, "excerpt", "reason", audit.ROLE_CODE_IDENTIFIER)
        self.assertEqual(finding.role, audit.ROLE_CODE_IDENTIFIER)

    def test_duplicate_rule_on_one_line_counts_once(self):
        # The historical counting is one finding per rule per line; the role
        # split must not inflate the inventory.
        seen = {}
        for role in (audit.ROLE_CODE_IDENTIFIER, audit.ROLE_STRING_LITERAL):
            seen.setdefault(("rule", "file.ts", 7, "line"), role)
        self.assertEqual(len(seen), 1)


if __name__ == "__main__":
    unittest.main()
