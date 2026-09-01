from __future__ import annotations

import unittest

from scripts.verify.guard_registry_audit import (
    build_reference_index,
    resolve_external_hits,
)


class GuardRegistryAuditIndexTest(unittest.TestCase):
    def test_resolve_external_hits_matches_filename_references(self) -> None:
        parts = {
            "scripts/verify/example_guard.py": "print('self')\n",
            "make/dev.mk": "python3 scripts/verify/example_guard.py\n",
            "scripts/ci/helper.py": "target = 'scripts/verify/example_guard.py'\n",
        }

        filename_hits, import_hits = build_reference_index(parts)
        hits = resolve_external_hits(
            "scripts/verify/example_guard.py",
            "example_guard.py",
            parts,
            filename_hits,
            import_hits,
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

        filename_hits, import_hits = build_reference_index(parts)
        hits = resolve_external_hits(
            "scripts/verify/frontend_professional_extension_guard.py",
            "frontend_professional_extension_guard.py",
            parts,
            filename_hits,
            import_hits,
        )

        self.assertEqual(
            hits, ["scripts/ci/test_frontend_professional_extension_guard.py"]
        )


if __name__ == "__main__":
    unittest.main()
