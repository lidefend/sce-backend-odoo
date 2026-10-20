#!/usr/bin/env python3
"""Read-only demo baseline readiness manifest + verifier (P4 delivery tooling).

The manifest is a delivery checklist, not product semantics. Each requirement's
``authority`` names the product-layer owner; the verifier only classifies
``ready`` / ``partial`` / ``blocked`` / ``not_applicable`` from declared
presence facts. It never writes a database and never re-implements a product
rule: a missing hard prerequisite is ``blocked``, a missing conditional one is
``partial``, and an undeclared or unobserved key fails closed.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCHEMA_VERSION = 1
VALID_KINDS = ("hard", "conditional")
VALID_STATUSES = ("ready", "partial", "blocked", "not_applicable")


class ManifestError(ValueError):
    pass


class ObservationError(ValueError):
    pass


def _read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ManifestError(f"unreadable JSON {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ManifestError(f"expected a JSON object: {path}")
    return data


def validate_manifest(data: dict) -> None:
    if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
        raise ManifestError(f"manifest must be an object with schema_version={SCHEMA_VERSION}")
    if not isinstance(data.get("id"), str) or not data["id"]:
        raise ManifestError("manifest id must be a non-empty string")
    gates = data.get("gates")
    if not isinstance(gates, list) or not gates:
        raise ManifestError("manifest gates must be a non-empty list")
    seen_gates: set[str] = set()
    seen_keys: set[str] = set()
    for gate in gates:
        if not isinstance(gate, dict):
            raise ManifestError("each gate must be an object")
        gid = gate.get("gate")
        if not isinstance(gid, str) or not gid:
            raise ManifestError("gate must declare a non-empty 'gate' id")
        if gid in seen_gates:
            raise ManifestError(f"duplicate gate id {gid!r}")
        seen_gates.add(gid)
        if not isinstance(gate.get("title"), str) or not gate["title"]:
            raise ManifestError(f"gate {gid} must declare a non-empty title")
        if gate.get("applicable") is not None and not isinstance(gate.get("applicable"), bool):
            raise ManifestError(f"gate {gid} 'applicable' must be boolean")
        reqs = gate.get("requirements")
        if not isinstance(reqs, list) or not reqs:
            raise ManifestError(f"gate {gid} requirements must be a non-empty list")
        for req in reqs:
            if not isinstance(req, dict):
                raise ManifestError(f"gate {gid} has a non-object requirement")
            key = req.get("key")
            if not isinstance(key, str) or not key:
                raise ManifestError(f"gate {gid} requirement key must be a non-empty string")
            if key in seen_keys:
                raise ManifestError(f"duplicate requirement key {key!r}")
            seen_keys.add(key)
            if req.get("kind") not in VALID_KINDS:
                raise ManifestError(f"requirement {key!r} kind must be one of {VALID_KINDS}")
            if not isinstance(req.get("authority"), str) or not req["authority"]:
                raise ManifestError(f"requirement {key!r} must declare a non-empty authority")
            if not isinstance(req.get("owner_layer"), str) or not req["owner_layer"]:
                raise ManifestError(f"requirement {key!r} must declare a non-empty owner_layer")
            if not isinstance(req.get("repair_hint"), str):
                raise ManifestError(f"requirement {key!r} repair_hint must be a string")


def load_manifest(path: Path) -> dict:
    data = _read_json(path)
    validate_manifest(data)
    return data


def _declared_keys(manifest: dict) -> set[str]:
    return {r["key"] for gate in manifest["gates"] for r in gate["requirements"]}


def _applicable_keys(manifest: dict) -> set[str]:
    return {
        r["key"]
        for gate in manifest["gates"]
        if gate.get("applicable", True)
        for r in gate["requirements"]
    }


def validate_observation(manifest: dict, observation: dict) -> None:
    if not isinstance(observation, dict):
        raise ObservationError("observation must be an object")
    observed = set(observation)
    missing = _applicable_keys(manifest) - observed
    extra = observed - _declared_keys(manifest)
    if missing:
        raise ObservationError(f"observation missing declared keys: {sorted(missing)}")
    if extra:
        raise ObservationError(f"observation has undeclared keys: {sorted(extra)}")
    for key, value in observation.items():
        if not isinstance(value, bool):
            raise ObservationError(
                f"observation key {key!r} must be boolean, got {type(value).__name__}"
            )


def evaluate_gate(gate: dict, observation: dict) -> dict:
    gid = gate["gate"]
    if gate.get("applicable", True) is False:
        return {
            "gate": gid,
            "title": gate["title"],
            "applicable": False,
            "status": "not_applicable",
            "required": [],
            "present": [],
            "missing": [],
            "owner_layer": ["P4"],
            "authority": [],
            "repair_hints": [],
        }
    reqs = gate["requirements"]
    required = [r["key"] for r in reqs]
    present = [k for k in required if observation[k] is True]
    missing = [k for k in required if observation[k] is False]
    hard_missing = [
        r["key"] for r in reqs if r["kind"] == "hard" and observation[r["key"]] is False
    ]
    if hard_missing:
        status = "blocked"
    elif not missing:
        status = "ready"
    else:
        status = "partial"
    return {
        "gate": gid,
        "title": gate["title"],
        "applicable": True,
        "status": status,
        "required": required,
        "present": present,
        "missing": missing,
        "owner_layer": sorted({r["owner_layer"] for r in reqs}),
        "authority": sorted({r["authority"] for r in reqs}),
        "repair_hints": [r["repair_hint"] for r in reqs if r["key"] in missing],
    }


def evaluate(manifest: dict, observation: dict) -> dict:
    validate_manifest(manifest)
    validate_observation(manifest, observation)
    gates = [evaluate_gate(gate, observation) for gate in manifest["gates"]]
    applicable = [g for g in gates if g["applicable"]]
    statuses = [g["status"] for g in applicable]
    if any(s == "blocked" for s in statuses):
        overall = "blocked"
    elif any(s == "partial" for s in statuses):
        overall = "partial"
    elif statuses and all(s == "ready" for s in statuses):
        overall = "ready"
    else:
        overall = "not_applicable"
    summary = {s: statuses.count(s) for s in VALID_STATUSES}
    return {
        "schema_version": SCHEMA_VERSION,
        "id": manifest["id"],
        "owner_layer": manifest.get("owner_layer", "P4"),
        "overall_status": overall,
        "summary": summary,
        "gates": gates,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--observation", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        manifest = load_manifest(args.manifest)
        observation = _read_json(args.observation)
        report = evaluate(manifest, observation)
    except (ManifestError, ObservationError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
