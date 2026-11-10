#!/usr/bin/env python3
"""Validate the five-gate frontend systemic convergence registry."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "docs/architecture/frontend_systemic_convergence_gates.json"
MAKEFILE = ROOT / "make/frontend.mk"
EXPECTED = {
    "text_containment": "verify.frontend.text_containment.guard",
    "inline_style": "verify.frontend.inline_style.guard",
    "semantic_split": "verify.frontend.split_usage.guard",
    "rich_text": "verify.frontend.rich_text.guard",
    "console": "verify.frontend.console.guard",
}


def inspect(root: Path = ROOT, registry_path: Path | None = None, makefile_path: Path | None = None) -> dict:
    registry_path = registry_path or root / "docs/architecture/frontend_systemic_convergence_gates.json"
    makefile_path = makefile_path or root / "make/frontend.mk"
    errors: list[str] = []
    try:
        payload = json.loads(registry_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return {"errors": [f"invalid gate registry: {exc}"], "gates": 0}
    if payload.get("schema_version") != 1:
        errors.append("gate registry schema_version must be 1")
    rows = payload.get("gates")
    if not isinstance(rows, list):
        return {"errors": ["gate registry gates must be an array"], "gates": 0}

    found: dict[str, str] = {}
    make_text = makefile_path.read_text(encoding="utf-8") if makefile_path.is_file() else ""
    for row in rows:
        if not isinstance(row, dict):
            errors.append("gate registry row must be an object")
            continue
        gate_id = str(row.get("id", "")).strip()
        target = str(row.get("target", "")).strip()
        authority = str(row.get("authority", "")).strip()
        if gate_id in found:
            errors.append(f"duplicate gate id: {gate_id}")
        found[gate_id] = target
        if not authority or not (root / authority).exists():
            errors.append(f"gate authority is missing: {gate_id}: {authority}")
        if target and f"{target}:" not in make_text:
            errors.append(f"gate target is not defined: {gate_id}: {target}")

    if found != EXPECTED:
        errors.append(f"gate registry mismatch: expected={EXPECTED} actual={found}")
    return {"errors": errors, "gates": len(rows)}


def main() -> int:
    result = inspect()
    if result["errors"]:
        print("[frontend_systemic_convergence_gate_guard] FAIL")
        for error in result["errors"]:
            print(f"- {error}")
        return 1
    print("[frontend_systemic_convergence_gate_guard] PASS")
    print(f"gates={result['gates']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
