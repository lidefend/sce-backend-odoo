from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.verify import frontend_systemic_convergence_gate_guard as guard


class FrontendSystemicConvergenceGateGuardTest(unittest.TestCase):
    def make_root(self, mutate=None) -> Path:
        root = Path(tempfile.mkdtemp())
        registry = root / "docs/architecture/frontend_systemic_convergence_gates.json"
        registry.parent.mkdir(parents=True)
        payload = {
            "schema_version": 1,
            "gates": [
                {"id": gate_id, "target": target, "authority": "authority.txt"}
                for gate_id, target in guard.EXPECTED.items()
            ],
        }
        if mutate:
            mutate(payload)
        registry.write_text(json.dumps(payload), encoding="utf-8")
        (root / "authority.txt").write_text("authority", encoding="utf-8")
        makefile = root / "make/frontend.mk"
        makefile.parent.mkdir(parents=True)
        makefile.write_text("\n".join(f"{target}:" for target in guard.EXPECTED.values()), encoding="utf-8")
        return root

    def test_complete_registry_passes(self) -> None:
        self.assertEqual(guard.inspect(self.make_root())["errors"], [])

    def test_missing_gate_fails(self) -> None:
        root = self.make_root(lambda payload: payload["gates"].pop())
        errors = guard.inspect(root, root / "docs/architecture/frontend_systemic_convergence_gates.json", root / "make/frontend.mk")["errors"]
        self.assertTrue(any("mismatch" in error for error in errors))

    def test_missing_target_fails(self) -> None:
        root = self.make_root()
        makefile = root / "make/frontend.mk"
        makefile.write_text("", encoding="utf-8")
        errors = guard.inspect(root, root / "docs/architecture/frontend_systemic_convergence_gates.json", makefile)["errors"]
        self.assertTrue(any("target is not defined" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
