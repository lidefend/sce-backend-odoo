from __future__ import annotations

import unittest

from scripts.verify.guard_registry_audit import (
    build_reference_index,
    disposition_failures,
    gate_anchor_failures,
    gate_reachability,
    gate_required_failures,
    parse_make_graph,
    reachable_targets,
    resolve_external_hits,
)


class GuardRegistryAuditIndexTest(unittest.TestCase):
    def test_resolve_external_hits_matches_filename_references(self) -> None:
        parts = {
            "scripts/verify/example_guard.py": "print('self')\n",
            "make/dev.mk": "python3 scripts/verify/example_guard.py\n",
            "scripts/ci/helper.py": "target = 'scripts/verify/example_guard.py'\n",
        }

        filename_hits, import_hits, module_hits = build_reference_index(parts)
        hits = resolve_external_hits(
            "scripts/verify/example_guard.py",
            "example_guard.py",
            parts,
            filename_hits,
            import_hits,
            module_hits,
        )

        self.assertEqual(hits, ["make/dev.mk", "scripts/ci/helper.py"])

    def test_resolve_external_hits_matches_import_references(self) -> None:
        parts = {
            "scripts/verify/frontend_professional_extension_guard.py": "print('self')\n",
            "scripts/ci/test_frontend_professional_extension_guard.py": (
                "from frontend_professional_extension_guard import validate\n"
            ),
            "scripts/ci/other.py": "from scripts.verify import unrelated\n",
        }

        filename_hits, import_hits, module_hits = build_reference_index(parts)
        hits = resolve_external_hits(
            "scripts/verify/frontend_professional_extension_guard.py",
            "frontend_professional_extension_guard.py",
            parts,
            filename_hits,
            import_hits,
            module_hits,
        )

        self.assertEqual(
            hits, ["scripts/ci/test_frontend_professional_extension_guard.py"]
        )

    def test_resolve_external_hits_matches_module_invocation(self) -> None:
        parts = {
            "scripts/verify/test_module_guard.py": "print('self')\n",
            "make/dev.mk": (
                "target:\n"
                "\t@python3 -m unittest scripts.verify.test_module_guard\n"
            ),
            "make/other.mk": "\t@python3 -m unittest scripts.verify.unrelated\n",
        }

        filename_hits, import_hits, module_hits = build_reference_index(parts)
        hits = resolve_external_hits(
            "scripts/verify/test_module_guard.py",
            "test_module_guard.py",
            parts,
            filename_hits,
            import_hits,
            module_hits,
        )

        self.assertEqual(hits, ["make/dev.mk"])


class GuardRegistryDispositionTest(unittest.TestCase):
    """Wire-or-retire disposition rules for unwired active scripts."""

    @staticmethod
    def _item(make_targets=None, workflows=None, files=None):
        return {
            "referenced_by_make_targets": make_targets or [],
            "referenced_by_workflows": workflows or [],
            "referenced_by_files": files or [],
        }

    def test_unwired_script_without_disposition_fails(self) -> None:
        failures = disposition_failures(
            "helper_guard.py", None, self._item(files=["scripts/ci/x.py"])
        )
        self.assertEqual(len(failures), 1)
        self.assertIn("lacks a wire-or-retire disposition", failures[0])
        self.assertIn("helper_guard.py", failures[0])

    def test_file_consumed_with_file_references_passes(self) -> None:
        entry = {"script": "helper_guard.py", "wire_or_retire": "file-consumed"}
        failures = disposition_failures(
            "helper_guard.py", entry, self._item(files=["scripts/ci/x.py"])
        )
        self.assertEqual(failures, [])

    def test_wired_script_needs_no_disposition(self) -> None:
        failures = disposition_failures(
            "wired_guard.py",
            None,
            self._item(make_targets=["verify.wired_guard.unit"]),
        )
        self.assertEqual(failures, [])

    def test_wired_script_with_stale_disposition_fails(self) -> None:
        entry = {"script": "wired_guard.py", "wire_or_retire": "file-consumed"}
        failures = disposition_failures(
            "wired_guard.py",
            entry,
            self._item(
                make_targets=["verify.wired_guard.unit"],
                files=["scripts/ci/x.py"],
            ),
        )
        self.assertEqual(len(failures), 1)
        self.assertIn("stale entry", failures[0])

    def test_wire_pending_requires_review_by(self) -> None:
        entry = {"script": "helper_guard.py", "wire_or_retire": "wire-pending"}
        failures = disposition_failures(
            "helper_guard.py", entry, self._item(files=["scripts/ci/x.py"])
        )
        self.assertEqual(len(failures), 1)
        self.assertIn("lacks a review_by deadline", failures[0])
        entry["review_by"] = "2026-12-31"
        self.assertEqual(
            disposition_failures("helper_guard.py", entry, self._item(files=["scripts/ci/x.py"])),
            [],
        )

    def test_unknown_disposition_value_fails(self) -> None:
        entry = {"script": "helper_guard.py", "wire_or_retire": "maybe"}
        failures = disposition_failures(
            "helper_guard.py", entry, self._item(files=["scripts/ci/x.py"])
        )
        self.assertEqual(len(failures), 1)
        self.assertIn("unknown wire_or_retire 'maybe'", failures[0])

    def test_file_consumed_without_file_references_fails(self) -> None:
        entry = {"script": "helper_guard.py", "wire_or_retire": "file-consumed"}
        failures = disposition_failures("helper_guard.py", entry, self._item())
        self.assertEqual(len(failures), 1)
        self.assertIn("claims file-consumed but no file reference", failures[0])


class GuardRegistryMakeGraphTest(unittest.TestCase):
    """Reachability must follow declared prerequisites, never recipe text."""

    def setUp(self) -> None:
        import scripts.verify.guard_registry_audit as audit

        self.audit = audit
        self._original_make_files = audit.MAKE_FILES

    def tearDown(self) -> None:
        self.audit.MAKE_FILES = self._original_make_files

    def _graph(self, text: str) -> dict[str, set[str]]:
        import tempfile
        from pathlib import Path as _Path

        tmp = _Path(tempfile.mkdtemp()) / "fixture.mk"
        tmp.write_text(text, encoding="utf-8")
        self.audit.MAKE_FILES = [tmp]
        return self.audit.parse_make_graph()

    def test_prerequisites_are_transitive_and_accumulate(self) -> None:
        graph = self._graph(
            "gate: leaf\n"
            "gate: other\n"
            "leaf: deep\n"
            "other:\n"
            "\t@echo other\n"
            "deep:\n"
            "\t@echo deep\n"
        )
        self.assertEqual(graph["gate"], {"leaf", "other"})
        self.assertEqual(
            reachable_targets(graph, ["gate"]), {"gate", "leaf", "deep", "other"}
        )
        self.assertEqual(reachable_targets(graph, ["missing"]), set())

    def test_recipe_text_is_not_a_gate(self) -> None:
        graph = self._graph("runner:\n\t@python3 scripts/verify/hidden.py\n")
        self.assertEqual(graph["runner"], set())
        self.assertEqual(reachable_targets(graph, ["runner"]), {"runner"})

    def test_variable_and_pattern_prerequisites_are_dropped(self) -> None:
        graph = self._graph(
            "gate: $(SUB) %.pattern plain\n"
            "plain:\n"
            "\t@echo plain\n"
        )
        self.assertEqual(graph["gate"], {"plain"})

    def test_continuation_lines_are_followed(self) -> None:
        graph = self._graph("gate: one \\\n    two\none:\n\t@echo one\ntwo:\n\t@echo two\n")
        self.assertEqual(graph["gate"], {"one", "two"})

    def test_reachability_separates_wired_from_unrun_lanes(self) -> None:
        import tempfile
        from pathlib import Path as _Path

        makefile = _Path(tempfile.mkdtemp()) / "fixture.mk"
        makefile.write_text(
            "anchor: guard.unit\n"
            "guard.unit:\n"
            "\t@python3 scripts/verify/guard.py\n"
            "orphan.aggregate: guard.unit\n",
            encoding="utf-8",
        )
        self.audit.MAKE_FILES = [makefile]
        inventory = [
            {
                "script": "guard.py",
                "path": "scripts/verify/guard.py",
                "status": "active",
                "referenced_by_make_targets": ["guard.unit"],
                "referenced_by_workflows": [],
            }
        ]
        _, enforced = gate_reachability(
            {"gate_anchors": [{"target": "anchor"}]}, inventory
        )
        self.assertTrue(enforced["guard.py"])
        _, not_enforced = gate_reachability(
            {"gate_anchors": [{"target": "unrelated"}]}, inventory
        )
        self.assertFalse(not_enforced["guard.py"])

    def test_gate_required_failure_message_names_the_defect(self) -> None:
        self.assertEqual(gate_required_failures("guard.py", True), [])
        failures = gate_required_failures("guard.py", False)
        self.assertEqual(len(failures), 1)
        self.assertIn("claims gate enforcement", failures[0])
        self.assertIn("guard.py", failures[0])


class GuardRegistryAnchorTest(unittest.TestCase):
    """A declared gate anchor must be substantiated by a real invocation."""

    def test_missing_anchor_declaration_fails(self) -> None:
        failures = gate_anchor_failures({}, {"gate": set()})
        self.assertEqual(len(failures), 1)
        self.assertIn("declares no gate_anchors", failures[0])

    def test_undeclared_target_fails(self) -> None:
        doc = {"gate_anchors": [{"target": "nope", "invoked_by": ["x"]}]}
        failures = gate_anchor_failures(doc, {"gate": set()})
        self.assertEqual(len(failures), 1)
        self.assertIn("is not a make target", failures[0])

    def test_anchor_without_invocation_source_fails(self) -> None:
        doc = {"gate_anchors": [{"target": "gate"}]}
        failures = gate_anchor_failures(doc, {"gate": set()})
        self.assertEqual(len(failures), 1)
        self.assertIn("declares no invoked_by source", failures[0])

    def test_stale_invocation_source_fails(self) -> None:
        doc = {
            "gate_anchors": [
                {"target": "gate", "invoked_by": ["scripts/verify/__absent__.txt"]}
            ]
        }
        failures = gate_anchor_failures(doc, {"gate": set()})
        self.assertEqual(len(failures), 1)
        self.assertIn("is not invoked by any declared source", failures[0])


class GuardRegistryShippedDeclarationTest(unittest.TestCase):
    """The shipped registry must stay consistent with the shipped make graph."""

    def test_every_declared_anchor_is_substantiated(self) -> None:
        import scripts.verify.guard_registry_audit as audit

        doc = audit.load_registry()
        self.assertEqual(audit.gate_anchor_failures(doc, audit.parse_make_graph()), [])

    def test_every_gate_required_script_is_actually_gate_reachable(self) -> None:
        import scripts.verify.guard_registry_audit as audit

        doc = audit.load_registry()
        inventory = audit.classify(audit.collect_scripts())
        by_name = {item["script"] for item in inventory}
        _, enforced = audit.gate_reachability(doc, inventory)
        required = [name for name in (doc.get("gate_required") or []) if name]
        self.assertTrue(required)
        for name in required:
            self.assertIn(name, by_name)
            self.assertTrue(
                enforced.get(name),
                f"declared gate_required script '{name}' is not reachable from a "
                f"declared gate anchor",
            )


if __name__ == "__main__":
    unittest.main()
