from __future__ import annotations

import unittest

from scripts.verify.guard_registry_audit import (
    build_reference_index,
    disposition_failures,
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


if __name__ == "__main__":
    unittest.main()
