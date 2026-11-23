#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from scripts.verify.identity_architecture_audit_guard import (
    BASELINE,
    load_inputs,
    validate_matrix,
    validate_product_source_read_only,
)


class IdentityArchitectureAuditGuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.matrix, cls.doc, cls.graph = load_inputs()

    def validate(self, matrix):
        return validate_matrix(matrix, doc_text=self.doc, graph_text=self.graph)

    def test_current_audit_artifacts_are_consistent(self):
        self.assertEqual(self.validate(self.matrix), [])

    def test_duplicate_domain_identity_is_rejected(self):
        matrix = deepcopy(self.matrix)
        matrix["domains"][1]["id"] = matrix["domains"][0]["id"]
        self.assertTrue(any("domain ids must be unique" in item for item in self.validate(matrix)))

    def test_unknown_domain_reference_is_rejected(self):
        matrix = deepcopy(self.matrix)
        matrix["domains"][0]["allowedReferences"].append("identity.unknown")
        self.assertTrue(any("unknown domain identity.unknown" in item for item in self.validate(matrix)))

    def test_unknown_finding_domain_is_rejected(self):
        matrix = deepcopy(self.matrix)
        matrix["findings"][0]["baselineDomain"] = "identity.unknown"
        self.assertTrue(any("baselineDomain is unknown" in item for item in self.validate(matrix)))

    def test_missing_finding_document_identity_is_rejected(self):
        matrix = deepcopy(self.matrix)
        matrix["findings"][0]["id"] = "ID-F-999"
        errors = self.validate(matrix)
        self.assertTrue(any("missing findings" in item for item in errors))
        self.assertTrue(any("does not mention ID-F-999" in item for item in errors))

    def test_global_identity_registry_is_rejected(self):
        matrix = deepcopy(self.matrix)
        matrix["decision"]["globalIdentityRegistry"] = "allowed"
        self.assertTrue(any("globalIdentityRegistry must be forbidden" in item for item in self.validate(matrix)))

    def test_missing_evidence_path_is_rejected(self):
        matrix = deepcopy(self.matrix)
        matrix["domains"][0]["evidence"] = ["addons/smart_core/missing_identity_source.py"]
        self.assertTrue(any("evidence path does not exist" in item for item in self.validate(matrix)))

    def test_unknown_work_package_finding_is_rejected(self):
        matrix = deepcopy(self.matrix)
        matrix["workPackages"][0]["findingIds"].append("ID-F-999")
        self.assertTrue(any("unknown finding ID-F-999" in item for item in self.validate(matrix)))

    def test_graph_missing_domain_is_rejected(self):
        graph = self.graph.replace('"odoo.record"', '"odoo.record.missing"')
        errors = validate_matrix(self.matrix, doc_text=self.doc, graph_text=graph)
        self.assertTrue(any("graph does not declare domain odoo.record" in item for item in errors))

    def test_baseline_identity_is_fixed(self):
        self.assertEqual(BASELINE, "8b46984d2b896eb104c26348788883993d260beb")

    def test_read_only_scope_uses_exact_baseline(self):
        self.assertEqual(validate_product_source_read_only(), [])


if __name__ == "__main__":
    unittest.main()
