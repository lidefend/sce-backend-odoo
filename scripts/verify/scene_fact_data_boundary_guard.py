#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fail-closed guard for ARCH-DECISION-009/010: the fact layer is the only
maintenance source for scenario-ization.

The scenario surface (scene entries, workspace layout, enablement) must be a
read-only projection of the native model/view/permission/group fact layer. This
guard locks the four mechanism-layer carriers that historically held scene
configuration fact data, binding each to an exact content SHA in the boundary
ledger so any new, removed, or changed carrier fails closed until the ledger is
re-pinned by a governed convergence change.
"""
from __future__ import annotations

import hashlib
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LEDGER_PATH = ROOT / "docs/architecture/scene_fact_data_boundary_ledger.json"
SCENE_REGISTRY = ROOT / "addons/smart_construction_scene/profiles/scene_registry_content.py"
SCENE_SETUP_XML = ROOT / "addons/smart_construction_scene/data/sc_scene_enterprise_setup.xml"
PROVIDER = ROOT / "addons/smart_construction_scene/providers/enterprise_setup_provider.py"
ENABLEMENT_WRITERS = [
    ROOT / "addons/smart_construction_scene/handlers/scenario_activation.py",
    ROOT / "addons/smart_construction_scene/services/tenant_scene_activation.py",
    ROOT / "addons/smart_construction_scene/services/enterprise_readiness_diagnosis.py",
]


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _hardcoded_enterprise_codes() -> str:
    """Canonicalized hardcoded enterprise.* scene registry codes."""
    text = SCENE_REGISTRY.read_text(encoding="utf-8")
    codes = sorted(re.findall(r'"code":\s*"(enterprise\.[^"]+)"', text))
    return "\n".join(codes)


def _hardcoded_provider_layout() -> str:
    """The hardcoded layout block in the enterprise setup provider, if present."""
    text = PROVIDER.read_text(encoding="utf-8") if PROVIDER.is_file() else ""
    match = re.search(r'"layout"\s*:\s*\{[^}]*\}', text)
    return match.group(0) if match else ""


def _scene_enablement_writes() -> str:
    """Lines that write sc.scene.company.enablement as scene fact data."""
    lines = []
    for path in ENABLEMENT_WRITERS:
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if "sc.scene.company.enablement" in line and any(
                token in line for token in ("create(", "write(", "set_enabled(")
            ):
                lines.append(line.strip())
    return "\n".join(lines)


def _current_violations() -> dict[str, str | None]:
    """Return the live violation signature. A missing carrier yields None."""
    registry_codes = _hardcoded_enterprise_codes()
    provider_layout = _hardcoded_provider_layout()
    enablement_writes = _scene_enablement_writes()
    return {
        "hardcoded_scene_registry_enterprise_entries": _sha(registry_codes) if registry_codes else None,
        "independent_scene_version_payload": _sha(SCENE_SETUP_XML.read_text(encoding="utf-8")) if SCENE_SETUP_XML.is_file() else None,
        "scene_enablement_fact_writes": _sha(enablement_writes) if enablement_writes else None,
        "hardcoded_provider_layout": _sha(provider_layout) if provider_layout else None,
    }


class SceneFactDataBoundaryGuard(unittest.TestCase):
    def test_boundary_carriers_match_ledger_pin(self):
        ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
        if ledger.get("schema") != "scene_fact_data_boundary.v1":
            self.fail("scene fact-data boundary ledger schema is invalid")
        violations = ledger.get("violations") or {}
        live = _current_violations()

        missing = sorted(set(live) - set(violations))
        self.assertFalse(
            missing,
            f"new scene-fact-data carriers are not registered in the boundary ledger: {missing}",
        )

        for key, live_sha in live.items():
            record = violations.get(key) or {}
            pinned = record.get("sha256")
            converged = bool(record.get("converged"))
            if live_sha is None:
                if not converged:
                    self.fail(
                        f"carrier '{key}' was removed without being marked converged in the ledger"
                    )
                continue
            if pinned != live_sha:
                self.fail(
                    f"carrier '{key}' diverged from its ledger pin; re-pin after a governed convergence change"
                )

        for key, record in violations.items():
            if record.get("converged") and live.get(key) is not None:
                self.fail(f"carrier '{key}' is marked converged but is still present")


if __name__ == "__main__":
    unittest.main()
