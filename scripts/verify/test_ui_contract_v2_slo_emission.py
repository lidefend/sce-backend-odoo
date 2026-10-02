#!/usr/bin/env python3
"""Offline lock for the contract SLO emission call site.

The runtime delivery boundary cannot be reached from an offline test, so this
suite loads the real ``ui_contract_v2_authority`` module (with a package shim for
its relative imports) and *executes* the real ``seal_runtime_contract`` chokepoint
with an injected sink. The emission is therefore proven by behaviour -- an
observation with the sealed contract's own identity arrives at the sink, and a
broken sink cannot break the delivery -- rather than by finding a string in the
source.
"""
from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
import sys
import types
import unittest


ROOT = Path(__file__).resolve().parents[2]
HANDLERS = ROOT / "addons/smart_core/handlers"
CORE = ROOT / "addons/smart_core/core"
AUTHORITY_PATH = HANDLERS / "ui_contract_v2_authority.py"
HANDLER_PATH = HANDLERS / "ui_contract_v2.py"
PACKAGE = "sc_slo_emission_probe"


def _install_package() -> None:
    # ``ui_contract_v2_authority`` imports ``..core.<module>``, so it must sit two
    # levels below the shim root exactly as it does inside ``smart_core``.
    for name, path in (
        (PACKAGE, ROOT / "addons"),
        (PACKAGE + ".smart_core", ROOT / "addons/smart_core"),
        (PACKAGE + ".smart_core.core", CORE),
        (PACKAGE + ".smart_core.handlers", HANDLERS),
    ):
        module = types.ModuleType(name)
        module.__path__ = [str(path)]
        sys.modules[name] = module


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader
    spec.loader.exec_module(module)
    return module


_install_package()
LIFECYCLE = _load(PACKAGE + ".smart_core.core.contract_lifecycle", CORE / "contract_lifecycle.py")
SLO = _load(PACKAGE + ".smart_core.core.contract_slo_telemetry", CORE / "contract_slo_telemetry.py")
AUTHORITY = _load(PACKAGE + ".smart_core.handlers.ui_contract_v2_authority", AUTHORITY_PATH)

STAGE = "runtime_delivery"


class Owner:
    """Minimal stand-in for the handler instance the chokepoint is given."""

    SOURCE_KIND = "unified_page_contract_v2"
    VERSION = "17.0.1.1.9"

    def source_authority_contract(self) -> dict:
        return {"kind": self.SOURCE_KIND, "version": self.VERSION}


def draft_contract() -> dict:
    return {
        "schemaVersion": "2.2.0",
        "page": {"id": "project.list", "containers": []},
        "meta": {"etag": "draft"},
    }


def seal(*, sink=None, source_sha_model="project.project", request_id="req-1", client_type="web_pc"):
    """Seal through the real chokepoint and hand back what it delivered."""
    contract = draft_contract()
    sealed = AUTHORITY.seal_runtime_contract(
        Owner(),
        contract,
        {"model": source_sha_model, "viewType": "list"},
        "scene_contract",  # keeps the chokepoint off env-backed saved-search refresh
        request_id,
        "",
        client_type,
        sink=sink,
    )
    return sealed


class DeliveryBoundaryEmissionTest(unittest.TestCase):
    def test_the_cusp_contract_carries_lifecycle_evidence(self):
        sealed = seal()
        lifecycle = sealed["meta"]["lifecycle"]
        self.assertEqual(lifecycle["stage"], STAGE)
        self.assertEqual(lifecycle["generation"]["generator"], Owner.SOURCE_KIND)

    def test_the_boundary_emits_exactly_one_observation(self):
        lines = []
        seal(sink=lines.append)
        self.assertEqual(len(lines), 1)

    def test_the_emitted_identity_is_the_sealed_contracts_own_evidence(self):
        lines = []
        sealed = seal(sink=lines.append)
        lifecycle = sealed["meta"]["lifecycle"]
        observation = SLO.parse_observation_line(lines[0])
        self.assertIsNotNone(observation)
        self.assertEqual(observation["outcome"], SLO.OUTCOME_SUCCESS)
        self.assertEqual(observation["identity"]["schemaId"], lifecycle["definition"]["schemaId"])
        self.assertEqual(observation["identity"]["schemaVersion"], lifecycle["definition"]["schemaVersion"])
        self.assertEqual(observation["identity"]["sourceSha256"], lifecycle["generation"]["sourceSha256"])
        self.assertEqual(observation["identity"]["stage"], lifecycle["stage"])
        self.assertEqual(observation["identity"]["sourceType"], "scene_contract")
        self.assertEqual(observation["requestId"], lifecycle["runtime"]["requestId"])
        self.assertEqual(observation["clientType"], lifecycle["runtime"]["clientType"])

    def test_a_broken_sink_never_breaks_the_delivery(self):
        def sink(_line):
            raise RuntimeError("telemetry backend is down")

        sealed = seal(sink=sink)
        self.assertIn("meta", sealed)
        self.assertIn("lifecycle", sealed["meta"])
        self.assertTrue(sealed["meta"]["etag"].startswith("upc-v2-sha256-"))

    def test_emission_does_not_alter_the_delivered_contract(self):
        plain = seal()
        sniffed = seal(sink=lambda _line: None)
        self.assertEqual(sniffed, plain)

    def test_a_tampered_delivery_is_reported_as_an_integrity_failure(self):
        lines = []
        sealed = seal(sink=lines.append)
        sealed["page"]["containers"] = [{"tampered": True}]
        self.assertTrue(
            AUTHORITY.emit_delivery_observation(
                sealed, request_id="req-1", client_type="web_pc", sink=lines.append
            )
        )
        observation = SLO.parse_observation_line(lines[-1])
        self.assertEqual(observation["outcome"], SLO.OUTCOME_INTEGRITY_FAILURE)

    def test_a_delivery_with_no_identity_is_never_aggregated_under_a_guess(self):
        lines = []
        AUTHORITY.emit_delivery_observation({}, request_id="req-9", client_type="web_pc", sink=lines.append)
        self.assertEqual(lines, [], "a delivery with no identity must not be aggregated under a guess")

    def test_the_default_sink_is_used_when_none_is_supplied(self):
        self.assertTrue(
            AUTHORITY.emit_delivery_observation(
                seal(), request_id="req-1", client_type="web_pc"
            )
        )

    def test_the_emitter_is_fail_open_for_every_bad_input(self):
        for bad in (None, [], {}, {"meta": "not a dict"}, {"meta": {"lifecycle": "nope"}}):
            with self.subTest(sealed=bad):
                self.assertFalse(
                    AUTHORITY.emit_delivery_observation(
                        bad, request_id="req-1", client_type="web_pc", sink=lambda _line: None
                    )
                )


class BoundaryStructureTest(unittest.TestCase):
    def test_the_handler_reaches_the_seal_only_through_the_authority_chokepoint(self):
        tree = ast.parse(HANDLER_PATH.read_text(encoding="utf-8"))
        direct = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "seal_unified_page_contract"
        ]
        self.assertEqual(direct, [], "the handler must seal through the authority chokepoint")
        chokepoint = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "seal_runtime_contract"
        ]
        self.assertGreaterEqual(len(chokepoint), 1, "the handler must seal somewhere")

    def test_the_chokepoint_emits_before_it_returns(self):
        source = AUTHORITY_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        function = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "seal_runtime_contract"
        )
        calls = [
            node.func.id
            for node in ast.walk(function)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        ]
        self.assertIn("emit_delivery_observation", calls)
        self.assertIn("seal_unified_page_contract", calls)


if __name__ == "__main__":
    unittest.main()
