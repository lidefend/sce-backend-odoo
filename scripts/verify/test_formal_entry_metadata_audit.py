#!/usr/bin/env python3
"""Lock the runtime formal-entry audit to the declared contract surface.

The audit must verify the declared ``FORMAL_ENTRY_METADATA_MODELS`` contract,
not a prefix sweep of every user model. This locks both the consumption
(the audit binds its required set to the declaration) and the declaration
itself (it cannot silently shrink).
"""

import ast
import hashlib
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
EXTENSIONS = (
    ROOT
    / "addons"
    / "smart_construction_core"
    / "models"
    / "support"
    / "formal_entry_metadata_extensions.py"
)
AUDIT = ROOT / "scripts" / "verify" / "formal_entry_metadata_audit.py"

# Frozen declaration of the formal-entry metadata contract.
CONTRACT_MODEL_COUNT = 92
CONTRACT_MODEL_DIGEST = "4a8e18fccf3e01c5be4b5ec1234845c68084605179b4818bdaf7fc426506313c"
CONTRACT_MODEL_SAMPLES = ("construction.contract", "sc.settlement.order", "tender.bid")


def _assignments(path: Path) -> dict[str, ast.AST]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.targets[0].id: node.value
        for node in tree.body
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
    }


class FormalEntryMetadataAuditTest(unittest.TestCase):
    def declared_models(self) -> tuple:
        value = ast.literal_eval(_assignments(EXTENSIONS)["FORMAL_ENTRY_METADATA_MODELS"])
        self.assertIsInstance(value, tuple)
        return value

    def test_audit_binds_required_models_to_the_declared_contract(self) -> None:
        assignments = _assignments(AUDIT)
        default = assignments["DEFAULT_REQUIRED_MODELS"]
        self.assertIsInstance(
            default,
            ast.Name,
            "required models must derive from FORMAL_ENTRY_METADATA_MODELS, not a literal sweep",
        )
        self.assertEqual(default.id, "FORMAL_ENTRY_METADATA_MODELS")
        source = AUDIT.read_text(encoding="utf-8")
        self.assertIn("FORMAL_ENTRY_METADATA_MODELS", source)

    def test_declared_contract_cannot_silently_shrink(self) -> None:
        declared = self.declared_models()
        self.assertEqual(len(declared), CONTRACT_MODEL_COUNT)
        self.assertEqual(len(set(declared)), CONTRACT_MODEL_COUNT)
        self.assertEqual(
            hashlib.sha256("\n".join(declared).encode()).hexdigest(),
            CONTRACT_MODEL_DIGEST,
        )
        for sample in CONTRACT_MODEL_SAMPLES:
            self.assertIn(sample, declared)

    def test_audit_keeps_full_sweep_available_as_explicit_override(self) -> None:
        source = AUDIT.read_text(encoding="utf-8")
        self.assertIn('"__all__"', source)
        self.assertIn("FORMAL_ENTRY_METADATA_REQUIRED_MODELS", source)


if __name__ == "__main__":
    unittest.main()
