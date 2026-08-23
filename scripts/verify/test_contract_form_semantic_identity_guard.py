#!/usr/bin/env python3

from __future__ import annotations

import unittest
from pathlib import Path

from scripts.verify.contract_form_semantic_identity_guard import (
    validate_semantic_identity_projection,
)


ROOT = Path(__file__).resolve().parents[2]
PRESENTER = ROOT / "frontend/apps/web/src/app/presentation/contractFormPresenter.ts"


VALID = """
function semanticIdentity(value: unknown) {
  const structure = asDict(value);
  return { role: semanticRole(structure), slot: text(structure.slot), group: text(structure.group) };
}
function fieldSemanticIdentity(widget: Widget, container: Container) {
  const widgetIdentity = semanticIdentity(widget.formStructureRole);
  const containerIdentity = semanticIdentity(container.formStructureRole);
  return {
    role: widgetIdentity.role || containerIdentity.role,
    slot: widgetIdentity.slot || containerIdentity.slot,
    group: widgetIdentity.group || containerIdentity.group,
  };
}
function zoneRole() { return ''; }
function fieldFromWidget(widget: Widget, container: Container) {
  const fieldSemantics = fieldSemanticIdentity(widget, container);
  return {
    semanticRole: fieldSemantics.role,
    semanticSlot: fieldSemantics.slot,
    semanticGroup: fieldSemantics.group,
  };
}
function presentNode(container: Container) {
  const nodeSemantics = semanticIdentity(container.formStructureRole);
  return {
    semanticRole: nodeSemantics.role,
    semanticSlot: nodeSemantics.slot,
    semanticGroup: nodeSemantics.group,
  };
}
function actionTier() { return ''; }
"""


class ContractFormSemanticIdentityGuardTests(unittest.TestCase):
    def test_current_production_presenter_passes(self) -> None:
        source = PRESENTER.read_text(encoding="utf-8")
        self.assertEqual(validate_semantic_identity_projection(source), [])

    def test_equivalent_structural_projection_passes(self) -> None:
        self.assertEqual(validate_semantic_identity_projection(VALID), [])

    def test_comments_and_strings_cannot_fake_projection(self) -> None:
        fake = f"/* {VALID} */\nconst marker = `{VALID}`;\n"
        errors = validate_semantic_identity_projection(fake)
        self.assertTrue(errors)
        self.assertIn("canonical field projection does not consume fieldSemanticIdentity", errors)

    def test_missing_identity_dimensions_fail_closed(self) -> None:
        for member in ("slot", "group"):
            with self.subTest(member=member):
                suffix = "," if member == "slot" else ""
                broken = VALID.replace(
                    f"{member}: text(structure.{member}){suffix}",
                    "",
                )
                self.assertIn(
                    f"semanticIdentity does not preserve {member}",
                    validate_semantic_identity_projection(broken),
                )

    def test_widget_first_container_fallback_is_required_for_every_dimension(self) -> None:
        broken = VALID.replace(
            "slot: widgetIdentity.slot || containerIdentity.slot,",
            "slot: widgetIdentity.slot,",
        )
        self.assertIn(
            "field semantics do not preserve widget-first slot authority",
            validate_semantic_identity_projection(broken),
        )

    def test_field_and_node_outputs_must_consume_identity(self) -> None:
        broken_field = VALID.replace("semanticGroup: fieldSemantics.group,", "")
        self.assertIn(
            "canonical field projection loses semanticGroup",
            validate_semantic_identity_projection(broken_field),
        )
        broken_node = VALID.replace("semanticSlot: nodeSemantics.slot,", "")
        self.assertIn(
            "canonical node projection loses semanticSlot",
            validate_semantic_identity_projection(broken_node),
        )

    def test_dead_identity_helper_without_production_consumers_fails(self) -> None:
        dead = VALID.replace(
            "const fieldSemantics = fieldSemanticIdentity(widget, container);",
            "const fieldSemantics = { role: '', slot: '', group: '' };",
        ).replace(
            "const nodeSemantics = semanticIdentity(container.formStructureRole);",
            "const nodeSemantics = { role: '', slot: '', group: '' };",
        )
        errors = validate_semantic_identity_projection(dead)
        self.assertIn("canonical field projection does not consume fieldSemanticIdentity", errors)
        self.assertIn("canonical node projection does not consume container formStructureRole", errors)


if __name__ == "__main__":
    unittest.main()
