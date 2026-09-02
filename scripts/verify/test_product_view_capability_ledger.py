from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts.contract.product_view_capability_ledger_common import (
    classify_structure, match_final_field_descriptor, match_final_object_action,
    match_normalized_atom, static_boolean_value,
)
from scripts.contract.product_view_contract_carriers_common import with_manifest
from scripts.contract.product_view_structure_common import file_sha256, sha256_json
from scripts.verify.product_view_capability_ledger_guard import (
    NATIVE_ORIGIN_REASON, NORMALIZED_REASON, _expected_authority, _pointer_get,
    validate_evidence_ref, validate_ledger,
)


class ProductViewCapabilityLedgerTests(unittest.TestCase):
    def _ledger_fixture(self, root: Path):
        fingerprint = {
            "algorithm": "codex_complete_worktree_fingerprint/v1", "git_head": "1" * 40,
            "baseline_sha": "2" * 40, "scope_manifest_sha256": "3" * 64,
            "digest": "4" * 64, "branch": "feature/test", "entries": [],
        }
        structure = with_manifest({
            "authority": {
                "branch": "feature/test", "candidate_fingerprint": {},
                "database_policy_path": "db.md", "database_policy_sha256": "5" * 64,
                "formal_menu_policy_path": "menu.json", "formal_menu_policy_sha256": "6" * 64,
                "runtime_profile": "local.clean", "compose_project": "sc-local-clean", "database": "sc_clean",
                "database_filter": "^sc_clean$", "demo_data": False, "module_set": ["base"],
                "module_set_sha256": sha256_json(["base"]), "user": "system", "company": "main",
                "language": "en_US", "group_profile": "system",
            },
            "summary": {"formal_menu_count": 1, "model_count": 1, "resolved_surface_count": 1, "view_type_counts": {"form": 1}},
            "entries": [{"surfaces": [{
                "contract_ref": "menu::form", "menu_xmlid": "menu", "action_xmlid": "action", "model": "x.model",
                "view_type": "form", "view_ref": "view", "source_kind": "database_view",
                "hashes": {"source_graph_sha256": "7" * 64, "resolved_arch_sha256": "8" * 64, "semantic_structure_sha256": "9" * 64},
                "source_graph": {"contributors": [{"view_ref": "view", "applicability": "applied"}]},
                "parse_outcome": {"status": "success"}, "resolved_structure": {"tag": "form"},
            }]}],
        })
        carrier = with_manifest({"entries": [{
            "contract_ref": "menu::form", "normalized_carriers": [{
                "source_selector": "/data/views/form", "artifact_selector": "/entries/0/normalized_carriers/0/value",
                "value": {"view_type": "form"}, "value_hash": sha256_json({"view_type": "form"}),
            }],
        }]})
        taxonomy = {"node_rules": [{"id": "root", "tags": "*", "capability_key": "structure.view_root"}], "attribute_rules": []}
        normalized_map = {"mappings": [{"id": "root", "view_types": ["form"], "capability_keys": ["structure.view_root"], "mapping_status": "mapping_unproven"}]}
        frontend_mapping = {
            "id": "root", "view_types": ["form"], "capability_keys": ["structure.view_root"],
            "frontend_status": "unproven", "consumer_symbol": "consumer", "renderer_key": "renderer",
            "interaction_symbol": "interaction",
        }
        frontend_map = {"mappings": [frontend_mapping]}
        reasons = {"entries": [
            {"code": NORMALIZED_REASON, "stage": "normalized", "status": "unsupported", "gate_effect": "classified_gap", "exit_condition": "prove mapping"},
            {"code": NATIVE_ORIGIN_REASON, "stage": "native", "status": "unsupported", "gate_effect": "classified_gap", "exit_condition": "prove origin"},
        ]}
        documents = {
            "structure.json": structure, "carrier.json": carrier, "fingerprint.json": fingerprint,
            "taxonomy.yaml": taxonomy, "normalized.yaml": normalized_map, "frontend.yaml": frontend_map, "reasons.yaml": reasons,
        }
        for name, value in documents.items():
            (root / name).write_text(json.dumps(value), encoding="utf-8")
        for name in ("product-view-contract-carriers-v1.yaml", "native-view-normalized-capability-map-v1.yaml"):
            path = root / "contracts/schemas" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{}\n", encoding="utf-8")
        interaction_path = root / "frontend/apps/web/scripts/canonical_form_presenter_test.ts"
        interaction_path.parent.mkdir(parents=True, exist_ok=True)
        interaction_path.write_text("validateCanonicalFormActionExecutors();\n", encoding="utf-8")
        paths = {
            "structure": Path("structure.json"), "carrier": Path("carrier.json"), "fingerprint": Path("fingerprint.json"),
            "taxonomy": Path("taxonomy.yaml"), "normalized_map": Path("normalized.yaml"),
            "frontend_map": Path("frontend.yaml"), "reasons": Path("reasons.yaml"),
        }
        atom = classify_structure(structure, taxonomy)["atoms"][0]
        evidence = [
            {"path": "structure.json", "sha256": file_sha256(root / "structure.json"), "candidate_fingerprint": fingerprint["digest"], "stage": "native", "selector": f"json-pointer:{atom['source_selector']}"},
            {"path": "carrier.json", "sha256": file_sha256(root / "carrier.json"), "candidate_fingerprint": fingerprint["digest"], "stage": "normalized", "selector": "json-pointer:/entries/0/normalized_carriers/0/value"},
            {"path": "normalized.yaml", "sha256": file_sha256(root / "normalized.yaml"), "candidate_fingerprint": fingerprint["digest"], "stage": "normalized", "selector": "json-pointer:/mappings/0"},
            {"path": "frontend.yaml", "sha256": file_sha256(root / "frontend.yaml"), "candidate_fingerprint": fingerprint["digest"], "stage": "frontend", "selector": "json-pointer:/mappings/0"},
        ]
        ledger = with_manifest({
            "authority": _expected_authority(structure, carrier, fingerprint, paths, root),
            "summary": {"formal_menu_count": 1, "model_count": 1, "resolved_surface_count": 1, "native_candidate_count": 1, "classified_atom_count": 1, "excluded_native_count": 0, "unclassified_native_count": 0, "ambiguous_native_count": 0, "capability_atom_count": 1, "ready_count": 0, "fallback_count": 0, "unsupported_count": 1, "silent_loss_count": 0, "view_type_counts": {"form": 1}},
            "entries": [{
                "contract_ref": "menu::form", "menu_xmlid": "menu", "action_xmlid": "action", "model": "x.model",
                "view_type": "form", "view_ref": "view", "hashes": structure["entries"][0]["surfaces"][0]["hashes"],
                "source_graph": structure["entries"][0]["surfaces"][0]["source_graph"], "parse_outcome": {"status": "success"},
                "atoms": [{
                    "atom_id": atom["atom_id"], "capability_key": atom["capability_key"],
                    "native": {"occurrence_index": 1, "resolved_view_ref": "view", "origin_view_ref": "view", "origin_status": "proven", "locator": atom["locator"], "native_locator": atom["native_locator"], "canonical_value": atom["canonical_value"], "value_hash": atom["value_hash"]},
                    "normalized": {"status": "unproven", "count": 0, "carrier_refs": ["/data/views/form"], "value_hash": "", "source_authority": "normalized_contract"},
                    "semantic": {"status": "missing", "count": 0, "carrier_refs": [], "value_hash": "", "source_authority": "none"},
                    "frontend": {"status": "unproven", "canonical_atom_ref": atom["atom_id"], "projection_atom_ref": "", "consumer_symbol": "consumer", "renderer_key": "renderer", "interaction_symbol": "interaction", "value_hash": sha256_json(frontend_mapping), "source_authority": "compatibility_projection", "source_count": 1},
                    "terminal_status": "unsupported", "reason_code": NORMALIZED_REASON, "evidence_refs": evidence,
                }],
            }],
        })
        return ledger, fingerprint, structure, carrier, taxonomy, normalized_map, frontend_map, reasons, paths

    def _full_errors(self, root: Path, ledger):
        ledger, fingerprint, structure, carrier, taxonomy, normalized_map, frontend_map, reasons, paths = ledger
        with patch("scripts.verify.product_view_capability_ledger_guard.validate_fingerprint", return_value=[]), patch("scripts.verify.product_view_capability_ledger_guard.validate_carriers", return_value=[]), patch("scripts.verify.product_view_capability_ledger_guard.validate_normalized_map", return_value=([], {})), patch("scripts.verify.product_view_capability_ledger_guard.validate_frontend_map", return_value=([], {})):
            return validate_ledger(ledger, {}, fingerprint, fingerprint, structure, carrier, taxonomy, normalized_map, frontend_map, reasons, paths, root)

    def test_terminal_reasons_preserve_first_loss(self) -> None:
        self.assertEqual(NATIVE_ORIGIN_REASON, "CAPABILITY_NATIVE_OCCURRENCE_ORIGIN_UNPROVEN")
        self.assertEqual(NORMALIZED_REASON, "CAPABILITY_NORMALIZED_MAPPING_UNPROVEN")

    def test_pointer_supports_escaped_attribute(self) -> None:
        self.assertEqual(_pointer_get({"a/b": {"~x": 7}}, "/a~1b/~0x"), 7)

    def test_pointer_rejects_missing_value(self) -> None:
        with self.assertRaises(KeyError):
            _pointer_get({}, "/missing")

    def test_static_modifier_match_is_occurrence_and_value_exact(self) -> None:
        atom = {
            "view_type": "form", "capability_key": "modifier.readonly", "attribute": "readonly",
            "native_locator": "/form[1]/field[1]", "occurrence_index": 1, "canonical_value": "1",
        }
        mapping = {
            "mapping_status": "proven", "matcher": "recursive_native_occurrence",
            "source_selectors": ["/data/views/form"], "value_regions": ["/layout"],
        }
        carrier = {"normalized_carriers": [{
            "source_selector": "/data/views/form", "artifact_selector": "/entries/0/normalized_carriers/0/value",
            "value": {"layout": [{"native_locator": "/form[1]/field[1]", "occurrence_index": 1, "attributes": {"readonly": "1"}, "modifiers": {"readonly": True}}]},
        }]}
        matches = match_normalized_atom(atom, mapping, carrier)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["semantic_value"], True)
        self.assertEqual(static_boolean_value(atom["canonical_value"]), True)
        carrier["normalized_carriers"][0]["value"]["layout"][0]["occurrence_index"] = 2
        self.assertEqual(match_normalized_atom(atom, mapping, carrier), [])

    def test_form_root_capability_match_preserves_raw_and_semantic_values(self) -> None:
        atom = {
            "view_type": "form", "capability_key": "form.edit", "attribute": "edit",
            "native_locator": "/form[1]", "occurrence_index": 1, "canonical_value": "0",
        }
        mapping = {
            "mapping_status": "proven", "matcher": "surface_identity",
            "source_selectors": ["/data/views/form"], "value_regions": ["/capabilities"],
        }
        carrier = {"normalized_carriers": [{
            "source_selector": "/data/views/form", "artifact_selector": "/entries/0/normalized_carriers/0/value",
            "value": {"capabilities": {"native_root_attributes": {"edit": "0"}, "can_write": False}},
        }]}
        matches = match_normalized_atom(atom, mapping, carrier)
        self.assertEqual(matches, [{
            "raw_selector": "/entries/0/normalized_carriers/0/value/capabilities/native_root_attributes/edit",
            "raw_value": "0",
            "semantic_selector": "/entries/0/normalized_carriers/0/value/capabilities/can_write",
            "semantic_value": False,
        }])
        carrier["normalized_carriers"][0]["value"]["capabilities"]["can_write"] = True
        self.assertEqual(match_normalized_atom(atom, mapping, carrier), [])

    def test_form_action_match_requires_exact_authoritative_occurrence_and_value(self) -> None:
        atom = {
            "view_type": "form", "capability_key": "action.identity", "attribute": "name",
            "native_locator": "/form[1]/header[1]/button[2]", "occurrence_index": 2,
            "canonical_value": "action_approve",
        }
        mapping = {
            "mapping_status": "proven", "matcher": "native_action_identity",
            "source_selectors": ["/data/views/form"],
            "value_regions": ["/layout", "/header_buttons", "/stat_buttons"],
        }
        carrier = {"normalized_carriers": [{
            "source_selector": "/data/views/form",
            "artifact_selector": "/entries/0/normalized_carriers/0/value",
            "value": {"layout": [], "stat_buttons": [], "header_buttons": [{
                "native_identity": {
                    "native_locator": atom["native_locator"], "occurrence_index": 2,
                    "authoritative": True, "name": "action_approve",
                },
            }]},
        }]}

        matches = match_normalized_atom(atom, mapping, carrier)

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["raw_value"], "action_approve")
        carrier["normalized_carriers"][0]["value"]["header_buttons"][0]["native_identity"]["authoritative"] = False
        self.assertEqual(match_normalized_atom(atom, mapping, carrier), [])
        carrier["normalized_carriers"][0]["value"]["header_buttons"][0]["native_identity"]["authoritative"] = True
        carrier["normalized_carriers"][0]["value"]["header_buttons"][0]["native_identity"]["occurrence_index"] = 1
        self.assertEqual(match_normalized_atom(atom, mapping, carrier), [])

    def test_form_field_descriptor_match_requires_exact_occurrence_and_value(self) -> None:
        atom = {
            "view_type": "form", "capability_key": "field.relation", "attribute": "relation",
            "native_locator": "/form[1]/sheet[1]/field[2]", "occurrence_index": 1,
            "canonical_value": "project.project",
        }
        mapping = {
            "mapping_status": "proven", "matcher": "native_field_descriptor_identity",
            "source_selectors": ["/data/views/form"], "value_regions": ["/layout"],
        }
        carrier = {"normalized_carriers": [{
            "source_selector": "/data/views/form",
            "artifact_selector": "/entries/0/normalized_carriers/0/value",
            "value": {"layout": [{
                "native_locator": atom["native_locator"], "occurrence_index": 1,
                "fieldInfo": {"name": "project_id", "type": "many2one", "relation": "project.project"},
            }]},
        }]}

        matches = match_normalized_atom(atom, mapping, carrier)

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["semantic_value"], "project.project")
        carrier["normalized_carriers"][0]["value"]["layout"][0]["occurrence_index"] = 2
        self.assertEqual(match_normalized_atom(atom, mapping, carrier), [])

    def test_form_field_identity_uses_descriptor_name_not_capability_suffix(self) -> None:
        atom = {
            "view_type": "form", "capability_key": "field.identity", "attribute": "name",
            "native_locator": "/form[1]/field[1]", "occurrence_index": 1,
            "canonical_value": "partner_id",
        }
        mapping = {
            "mapping_status": "proven", "matcher": "native_field_descriptor_identity",
            "source_selectors": ["/data/views/form"], "value_regions": ["/layout"],
        }
        carrier = {"normalized_carriers": [{
            "source_selector": "/data/views/form",
            "artifact_selector": "/entries/0/normalized_carriers/0/value",
            "value": {"layout": [{
                "native_locator": atom["native_locator"], "occurrence_index": 1,
                "fieldInfo": {"name": "partner_id"},
            }]},
        }]}

        matches = match_normalized_atom(atom, mapping, carrier)

        self.assertEqual(len(matches), 1)
        self.assertTrue(matches[0]["semantic_selector"].endswith("/fieldInfo/name"))
        carrier["normalized_carriers"][0]["value"]["layout"][0]["fieldInfo"]["name"] = "company_id"
        self.assertEqual(match_normalized_atom(atom, mapping, carrier), [])

    def test_form_field_options_require_safe_literal_and_structured_equivalence(self) -> None:
        atom = {
            "view_type": "form", "capability_key": "field.options", "attribute": "options",
            "native_locator": "/form[1]/field[1]", "occurrence_index": 1,
            "canonical_value": "{'no_create': True}",
        }
        mapping = {
            "mapping_status": "proven", "matcher": "native_field_descriptor_identity",
            "source_selectors": ["/data/views/form"], "value_regions": ["/layout"],
        }
        carrier = {"normalized_carriers": [{
            "source_selector": "/data/views/form",
            "artifact_selector": "/entries/0/normalized_carriers/0/value",
            "value": {"layout": [{
                "native_locator": atom["native_locator"], "occurrence_index": 1,
                "attributes": {"options": "{'no_create': True}"},
                "fieldInfo": {"widget_options": {"no_create": True}},
            }]},
        }]}

        matches = match_normalized_atom(atom, mapping, carrier)

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["raw_value"], "{'no_create': True}")
        self.assertEqual(matches[0]["semantic_value"], {"no_create": True})
        atom["canonical_value"] = "dict(no_create=True)"
        self.assertEqual(match_normalized_atom(atom, mapping, carrier), [])

    def test_final_field_descriptor_match_requires_contract_v2_projection_equivalence(self) -> None:
        atom = {
            "view_type": "form", "capability_key": "field.type", "attribute": "type",
            "native_locator": "/form[1]/sheet[1]/field[2]", "occurrence_index": 1,
            "canonical_value": "many2one",
        }
        carrier = {"final_contract_capture": {"status": "complete", "carriers": [{
            "source_selector": "/data/layoutContract/containerTree",
            "artifact_selector": "/entries/0/final_contract_capture/carriers/0/value",
            "value": [{
                "type": "field", "name": "project_id", "nativeLocator": atom["native_locator"],
                "occurrenceIndex": 1, "fieldInfo": {"type": "many2one", "relation": "project.project"},
                "componentConfig": {"fieldType": "many2one", "relation": "project.project"},
            }],
        }]}}

        matches = match_final_field_descriptor(atom, carrier)

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["semantic_value"], "many2one")
        carrier["final_contract_capture"]["carriers"][0]["value"][0]["componentConfig"]["fieldType"] = "char"
        self.assertEqual(match_final_field_descriptor(atom, carrier), [])

    def test_final_field_widget_requires_native_widget_projection_equivalence(self) -> None:
        atom = {
            "view_type": "form", "capability_key": "field.widget", "attribute": "widget",
            "native_locator": "/form[1]/field[1]", "occurrence_index": 1,
            "canonical_value": "many2many_tags",
        }
        carrier = {"final_contract_capture": {"status": "complete", "carriers": [{
            "source_selector": "/data/layoutContract/containerTree",
            "artifact_selector": "/entries/0/final_contract_capture/carriers/0/value",
            "value": [{
                "type": "field", "name": "tag_ids", "label": "Tags",
                "nativeLocator": atom["native_locator"], "occurrenceIndex": 1,
                "fieldInfo": {"name": "tag_ids", "label": "Tags", "widget": "many2many_tags"},
                "componentConfig": {"nativeWidget": "many2many_tags"},
            }],
        }]}}

        matches = match_final_field_descriptor(atom, carrier)

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["semantic_value"], "many2many_tags")
        carrier["final_contract_capture"]["carriers"][0]["value"][0]["componentConfig"]["nativeWidget"] = "select"
        self.assertEqual(match_final_field_descriptor(atom, carrier), [])

    def test_final_field_identity_requires_top_level_and_descriptor_agreement(self) -> None:
        atom = {
            "view_type": "form", "capability_key": "field.identity", "attribute": "name",
            "native_locator": "/form[1]/field[1]", "occurrence_index": 1,
            "canonical_value": "partner_id",
        }
        carrier = {"final_contract_capture": {"status": "complete", "carriers": [{
            "source_selector": "/data/layoutContract/containerTree",
            "artifact_selector": "/entries/0/final_contract_capture/carriers/0/value",
            "value": [{
                "type": "field", "name": "partner_id",
                "nativeLocator": atom["native_locator"], "occurrenceIndex": 1,
                "fieldInfo": {"name": "partner_id"}, "componentConfig": {},
            }],
        }]}}

        self.assertEqual(len(match_final_field_descriptor(atom, carrier)), 1)
        carrier["final_contract_capture"]["carriers"][0]["value"][0]["name"] = "company_id"
        self.assertEqual(match_final_field_descriptor(atom, carrier), [])

    def test_final_field_options_require_descriptor_and_component_agreement(self) -> None:
        atom = {
            "view_type": "form", "capability_key": "field.options", "attribute": "options",
            "native_locator": "/form[1]/field[1]", "occurrence_index": 1,
            "canonical_value": "{'no_create': True}",
        }
        carrier = {"final_contract_capture": {"status": "complete", "carriers": [{
            "source_selector": "/data/layoutContract/containerTree",
            "artifact_selector": "/entries/0/final_contract_capture/carriers/0/value",
            "value": [{
                "type": "field", "name": "partner_id",
                "nativeLocator": atom["native_locator"], "occurrenceIndex": 1,
                "fieldInfo": {"widget_options": {"no_create": True}},
                "componentConfig": {"widgetOptions": {"no_create": True}},
            }],
        }]}}

        self.assertEqual(len(match_final_field_descriptor(atom, carrier)), 1)
        carrier["final_contract_capture"]["carriers"][0]["value"][0]["componentConfig"]["widgetOptions"] = {}
        self.assertEqual(match_final_field_descriptor(atom, carrier), [])

    def test_final_object_action_match_requires_exact_rule_and_status(self) -> None:
        atom = {
            "view_type": "form", "capability_key": "action.identity", "attribute": "name",
            "native_locator": "/form[1]/header[1]/button[2]", "occurrence_index": 2,
            "canonical_value": "action_approve",
        }
        backend_identity = "native_button:object:action_approve:/form[1]/header[1]/button[2]:2"
        carrier = {"final_contract_capture": {"status": "complete", "carriers": [
            {"source_selector": "/data/actionContract/actionRuleList", "artifact_selector": "/entries/0/final_contract_capture/carriers/0/value", "value": [{
                "actionId": "action.approve", "actionKey": "action.approve", "label": "Approve",
                "backendIdentity": backend_identity,
                "button": {"name": "action_approve", "type": "object"},
                "nativeIdentity": {"authoritative": True, "native_locator": atom["native_locator"], "occurrence_index": 2, "name": "action_approve", "type": "object"},
            }]},
            {"source_selector": "/data/statusContract/buttonStatus", "artifact_selector": "/entries/0/final_contract_capture/carriers/1/value", "value": [{
                "btnId": "btn.action.approve", "backendIdentity": backend_identity, "visible": True, "disabled": False,
            }]},
        ]}}
        matches = match_final_object_action(atom, carrier)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["semantic_value"], "action_approve")
        carrier["final_contract_capture"]["carriers"][1]["value"][0]["backendIdentity"] = "wrong"
        self.assertEqual(match_final_object_action(atom, carrier), [])

    def test_final_action_type_only_promotes_object(self) -> None:
        atom = {"view_type": "form", "capability_key": "action.type", "canonical_value": "action"}
        self.assertEqual(match_final_object_action(atom, {"final_contract_capture": {"status": "complete", "carriers": []}}), [])

    def test_final_object_action_preserves_supported_native_icon(self) -> None:
        atom = {
            "view_type": "form", "capability_key": "action.icon", "attribute": "icon",
            "native_locator": "/form[1]/header[1]/button[2]", "occurrence_index": 2,
            "canonical_value": "fa-check",
        }
        backend_identity = "native_button:object:action_approve:/form[1]/header[1]/button[2]:2"
        rule = {
            "actionId": "action.approve", "actionKey": "action.approve", "label": "Approve",
            "backendIdentity": backend_identity,
            "button": {"name": "action_approve", "type": "object"},
            "nativeIdentity": {
                "authoritative": True, "native_locator": atom["native_locator"],
                "occurrence_index": 2, "name": "action_approve", "type": "object", "icon": "fa-check",
            },
            "presentation": {"tier": "primary", "icon": "fa-check"},
        }
        carrier = {"final_contract_capture": {"status": "complete", "carriers": [
            {"source_selector": "/data/actionContract/actionRuleList", "artifact_selector": "/entries/0/final_contract_capture/carriers/0/value", "value": [rule]},
            {"source_selector": "/data/statusContract/buttonStatus", "artifact_selector": "/entries/0/final_contract_capture/carriers/1/value", "value": [{
                "btnId": "btn.action.approve", "backendIdentity": backend_identity,
                "visible": True, "disabled": False,
            }]},
        ]}}

        self.assertEqual(len(match_final_object_action(atom, carrier)), 1)
        rule["presentation"]["icon"] = "fa-times"
        self.assertEqual(match_final_object_action(atom, carrier), [])
        atom["canonical_value"] = "oi-check"
        rule["presentation"]["icon"] = "oi-check"
        self.assertEqual(match_final_object_action(atom, carrier), [])

    def test_final_object_action_preserves_explicit_confirm(self) -> None:
        atom = {
            "view_type": "form", "capability_key": "action.confirm", "attribute": "confirm",
            "native_locator": "/form[1]/header[1]/button[2]", "occurrence_index": 2,
            "canonical_value": "Submit this document?",
        }
        backend_identity = "native_button:object:action_approve:/form[1]/header[1]/button[2]:2"
        rule = {
            "actionId": "action.approve", "actionKey": "action.approve", "label": "Approve",
            "backendIdentity": backend_identity,
            "button": {"name": "action_approve", "type": "object"},
            "nativeIdentity": {
                "authoritative": True, "native_locator": atom["native_locator"],
                "occurrence_index": 2, "name": "action_approve", "type": "object",
                "confirm_raw": "Submit this document?",
            },
            "actionSafety": {
                "classification": "danger", "requires_confirm": True,
                "confirm_message": "Submit this document?",
            },
        }
        carrier = {"final_contract_capture": {"status": "complete", "carriers": [
            {"source_selector": "/data/actionContract/actionRuleList", "artifact_selector": "/entries/0/final_contract_capture/carriers/0/value", "value": [rule]},
            {"source_selector": "/data/statusContract/buttonStatus", "artifact_selector": "/entries/0/final_contract_capture/carriers/1/value", "value": [{
                "btnId": "btn.action.approve", "backendIdentity": backend_identity,
                "visible": True, "disabled": False,
            }]},
        ]}}

        self.assertEqual(len(match_final_object_action(atom, carrier)), 1)
        rule["actionSafety"]["confirm_message"] = "Different message"
        self.assertEqual(match_final_object_action(atom, carrier), [])

    def test_native_source_selector_resolves_exact_occurrence(self) -> None:
        structure = {"entries": [{"surfaces": [{"contract_ref": "m::form", "view_ref": "v", "view_type": "form", "resolved_structure": {"tag": "form", "children": [{"tag": "field", "attrs": {"name": "x", "a/b": "value"}}]}}]}]}
        taxonomy = {"node_rules": [{"id": "nodes", "tags": "*", "capability_key_template": "node.{tag}"}], "attribute_rules": [{"id": "attrs", "tags": "*", "attribute_prefixes": [""], "capability_key_template": "attr.{attribute}"}]}
        classified = classify_structure(structure, taxonomy)
        atom = next(item for item in classified["atoms"] if item["attribute"] == "a/b")
        self.assertEqual(atom["source_selector"], "/entries/0/surfaces/0/resolved_structure/children/0/attrs/a~1b")
        self.assertEqual(atom["native_locator"], "/form[1]/field[1]")
        self.assertEqual(_pointer_get(structure, atom["source_selector"]), "value")

    def test_evidence_checks_hash_fingerprint_and_selector(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "fixture.json"
            path.write_text(json.dumps({"value": [3]}), encoding="utf-8")
            ref = {"path": "fixture.json", "sha256": file_sha256(path), "candidate_fingerprint": "f", "selector": "json-pointer:/value/0"}
            errors, selected = validate_evidence_ref(ref, "f", root)
            self.assertEqual(errors, [])
            self.assertEqual(selected, 3)
            ref["sha256"] = "0" * 64
            self.assertIn("evidence file hash mismatch", validate_evidence_ref(ref, "f", root)[0])

    def test_evidence_rejects_path_escape(self) -> None:
        with TemporaryDirectory() as directory:
            errors, _ = validate_evidence_ref({"path": "../outside", "sha256": "", "candidate_fingerprint": "f", "selector": "json-pointer:"}, "f", Path(directory))
            self.assertEqual(errors, ["evidence path is not a governed file"])

    def test_symbol_evidence_requires_exact_identifier(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "fixture.ts"
            path.write_text("function validateCanonicalFormActionExecutors() {}\n", encoding="utf-8")
            ref = {"path": "fixture.ts", "sha256": file_sha256(path), "candidate_fingerprint": "f", "selector": "symbol:validateCanonicalFormActionExecutors"}
            self.assertEqual(validate_evidence_ref(ref, "f", root), ([], "validateCanonicalFormActionExecutors"))
            ref["selector"] = "symbol:missingExecutor"
            self.assertIn("evidence symbol is not resolvable", validate_evidence_ref(ref, "f", root)[0])

    def test_complete_ledger_and_mutations_are_fail_closed(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = self._ledger_fixture(root)
            self.assertEqual(self._full_errors(root, fixture), [])
            mutations = (
                ("authority", lambda value: value["authority"].update(runtime_profile="local.dev")),
                ("surface", lambda value: value["entries"][0].update(model="other.model")),
                ("native", lambda value: value["entries"][0]["atoms"][0]["native"].update(origin_view_ref="other.view")),
                ("frontend", lambda value: value["entries"][0]["atoms"][0]["frontend"].update(consumer_symbol="other")),
                ("evidence", lambda value: value["entries"][0]["atoms"][0]["evidence_refs"][1].update(selector="json-pointer:/entries/0")),
                ("summary", lambda value: value["summary"].update(model_count=2)),
            )
            for label, mutate in mutations:
                with self.subTest(label=label):
                    changed = deepcopy(fixture[0])
                    mutate(changed)
                    changed.pop("manifest_sha256")
                    changed = with_manifest(changed)
                    changed_fixture = (changed, *fixture[1:])
                    self.assertTrue(self._full_errors(root, changed_fixture), label)


if __name__ == "__main__":
    unittest.main()
