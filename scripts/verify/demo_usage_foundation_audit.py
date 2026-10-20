#!/usr/bin/env python3
"""Read-only demo usage-foundation manifest audit (P4 delivery tooling).

This is a declaration-coverage audit, not a database readback. It classifies
every canonical user action and every declared requirement as ``observed``,
``missing``, or ``blocked`` using only the manifest and its registered gaps:

* ``observed``: the user action has at least one declared requirement and no
  open registered gap blocks that requirement;
* ``missing``: a canonical user action has no declared requirement at all
  (a contract gap in the manifest itself; fail closed);
* ``blocked``: the requirement exists but references an open gap whose owning
  layer must be fixed before the consuming batch can proceed.

It never writes a database, never re-implements a product rule, and never
substitutes for F2-F8 data or runtime readback.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCHEMA_VERSION = 1
VALID_LAYERS = ("U0", "U1", "U2", "U3", "U4", "U5", "U6")
VALID_OWNER_LAYERS = ("P0", "P1", "P2", "P3", "P4")
VALID_PREREQUISITES = ("hard", "conditional")
VALID_BATCHES = ("F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8")
VALID_GAP_STATUSES = ("open", "closed")


class ManifestError(ValueError):
    pass


def _read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ManifestError(f"unreadable JSON {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ManifestError(f"expected a JSON object: {path}")
    return data


def _require_nonempty_string(value, field: str, ctx: str) -> str:
    if not isinstance(value, str) or not value:
        raise ManifestError(f"{ctx}: {field} must be a non-empty string")
    return value


def validate_manifest(data: dict) -> None:
    if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
        raise ManifestError(f"manifest must be an object with schema_version={SCHEMA_VERSION}")
    _require_nonempty_string(data.get("id"), "id", "manifest")
    if data.get("owner_layer") not in VALID_OWNER_LAYERS:
        raise ManifestError(f"manifest owner_layer must be one of {VALID_OWNER_LAYERS}")
    _require_nonempty_string(data.get("authority"), "authority", "manifest")

    layers = data.get("layers")
    if not isinstance(layers, dict) or not layers:
        raise ManifestError("manifest layers must be a non-empty object")
    for layer_id, layer in layers.items():
        if layer_id not in VALID_LAYERS:
            raise ManifestError(f"layer {layer_id!r} must be one of {VALID_LAYERS}")
        if not isinstance(layer, dict):
            raise ManifestError(f"layer {layer_id} must be an object")
        _require_nonempty_string(layer.get("title"), "title", f"layer {layer_id}")
        if layer.get("blocking_batch") not in VALID_BATCHES:
            raise ManifestError(
                f"layer {layer_id} blocking_batch must be one of {VALID_BATCHES}"
            )
        if not isinstance(layer.get("seedable"), bool):
            raise ManifestError(f"layer {layer_id} seedable must be boolean")
        owner_layers = layer.get("owner_layers")
        if not isinstance(owner_layers, list) or not owner_layers:
            raise ManifestError(f"layer {layer_id} owner_layers must be a non-empty list")
        for ol in owner_layers:
            if ol not in VALID_OWNER_LAYERS:
                raise ManifestError(
                    f"layer {layer_id} owner_layer {ol!r} must be one of {VALID_OWNER_LAYERS}"
                )

    actions = data.get("user_actions")
    if not isinstance(actions, list) or not actions:
        raise ManifestError("manifest user_actions must be a non-empty list")
    seen_actions: set[str] = set()
    for action in actions:
        if not isinstance(action, dict):
            raise ManifestError("each user_action must be an object")
        akey = _require_nonempty_string(action.get("key"), "key", "user_action")
        if akey in seen_actions:
            raise ManifestError(f"duplicate user_action key {akey!r}")
        seen_actions.add(akey)
        _require_nonempty_string(action.get("title"), "title", f"user_action {akey}")
        if action.get("layer") not in layers:
            raise ManifestError(
                f"user_action {akey} layer must reference a declared layer"
            )
        if action.get("blocking_batch") not in VALID_BATCHES:
            raise ManifestError(
                f"user_action {akey} blocking_batch must be one of {VALID_BATCHES}"
            )
        if "derived_only" in action and not isinstance(action.get("derived_only"), bool):
            raise ManifestError(f"user_action {akey} derived_only must be boolean")

    gaps = data.get("gaps")
    if not isinstance(gaps, list):
        raise ManifestError("manifest gaps must be a list")
    seen_gaps: set[str] = set()
    for gap in gaps:
        if not isinstance(gap, dict):
            raise ManifestError("each gap must be an object")
        gid = _require_nonempty_string(gap.get("id"), "id", "gap")
        if gid in seen_gaps:
            raise ManifestError(f"duplicate gap id {gid!r}")
        seen_gaps.add(gid)
        _require_nonempty_string(gap.get("title"), "title", f"gap {gid}")
        if gap.get("owner_layer") not in VALID_OWNER_LAYERS:
            raise ManifestError(f"gap {gid} owner_layer must be one of {VALID_OWNER_LAYERS}")
        batches = gap.get("blocking_batches")
        if not isinstance(batches, list) or not batches:
            raise ManifestError(f"gap {gid} blocking_batches must be a non-empty list")
        for batch in batches:
            if batch not in VALID_BATCHES:
                raise ManifestError(
                    f"gap {gid} blocking_batch {batch!r} must be one of {VALID_BATCHES}"
                )
        _require_nonempty_string(gap.get("repair_hint"), "repair_hint", f"gap {gid}")
        if gap.get("status") not in VALID_GAP_STATUSES:
            raise ManifestError(f"gap {gid} status must be one of {VALID_GAP_STATUSES}")

    reqs = data.get("requirements")
    if not isinstance(reqs, list) or not reqs:
        raise ManifestError("manifest requirements must be a non-empty list")
    seen_reqs: set[str] = set()
    for req in reqs:
        if not isinstance(req, dict):
            raise ManifestError("each requirement must be an object")
        rkey = _require_nonempty_string(req.get("key"), "key", "requirement")
        if rkey in seen_reqs:
            raise ManifestError(f"duplicate requirement key {rkey!r}")
        seen_reqs.add(rkey)
        if req.get("layer") not in layers:
            raise ManifestError(
                f"requirement {rkey} layer must reference a declared layer"
            )
        if req.get("user_action") not in seen_actions:
            raise ManifestError(
                f"requirement {rkey} user_action must reference a declared user_action"
            )
        if req.get("prerequisite") not in VALID_PREREQUISITES:
            raise ManifestError(
                f"requirement {rkey} prerequisite must be one of {VALID_PREREQUISITES}"
            )
        if req.get("owner_layer") not in VALID_OWNER_LAYERS:
            raise ManifestError(
                f"requirement {rkey} owner_layer must be one of {VALID_OWNER_LAYERS}"
            )
        _require_nonempty_string(req.get("read_entry"), "read_entry", f"requirement {rkey}")
        _require_nonempty_string(req.get("scope"), "scope", f"requirement {rkey}")
        _require_nonempty_string(req.get("repair_hint"), "repair_hint", f"requirement {rkey}")
        _require_nonempty_string(
            req.get("acceptance_method"), "acceptance_method", f"requirement {rkey}"
        )
        gap_ref = req.get("gap_ref")
        if gap_ref is not None and gap_ref not in seen_gaps:
            raise ManifestError(
                f"requirement {rkey} gap_ref {gap_ref!r} must reference a declared gap"
            )


def load_manifest(path: Path) -> dict:
    data = _read_json(path)
    validate_manifest(data)
    return data


def _gap_statuses(manifest: dict) -> dict[str, str]:
    return {gap["id"]: gap["status"] for gap in manifest.get("gaps", [])}


def audit(manifest: dict) -> dict:
    validate_manifest(manifest)
    statuses = _gap_statuses(manifest)
    reqs = manifest["requirements"]
    by_action: dict[str, list[dict]] = {a["key"]: [] for a in manifest["user_actions"]}
    for req in reqs:
        by_action[req["user_action"]].append(req)

    actions = []
    for action in manifest["user_actions"]:
        akey = action["key"]
        owned = by_action[akey]
        if not owned:
            actions.append(
                {
                    "key": akey,
                    "title": action["title"],
                    "layer": action["layer"],
                    "status": "missing",
                    "requirement_keys": [],
                    "open_gaps": [],
                }
            )
            continue
        open_gaps = sorted(
            {r["gap_ref"] for r in owned if r.get("gap_ref") and statuses[r["gap_ref"]] == "open"}
        )
        actions.append(
            {
                "key": akey,
                "title": action["title"],
                "layer": action["layer"],
                "status": "blocked" if open_gaps else "observed",
                "requirement_keys": [r["key"] for r in owned],
                "open_gaps": open_gaps,
            }
        )

    requirements = [
        {
            "key": r["key"],
            "layer": r["layer"],
            "user_action": r["user_action"],
            "prerequisite": r["prerequisite"],
            "owner_layer": r["owner_layer"],
            "status": (
                "blocked"
                if r.get("gap_ref") and statuses[r["gap_ref"]] == "open"
                else "observed"
            ),
            "gap_ref": r.get("gap_ref"),
        }
        for r in reqs
    ]

    gaps = [
        {
            "id": g["id"],
            "owner_layer": g["owner_layer"],
            "blocking_batches": g["blocking_batches"],
            "repair_hint": g["repair_hint"],
            "status": g["status"],
        }
        for g in manifest.get("gaps", [])
    ]

    batch_blockers: dict[str, list[str]] = {}
    for g in manifest.get("gaps", []):
        if g["status"] == "open":
            for batch in g["blocking_batches"]:
                batch_blockers.setdefault(batch, []).append(g["id"])
    for blockers in batch_blockers.values():
        blockers.sort()

    action_statuses = [a["status"] for a in actions]
    coverage_complete = "missing" not in action_statuses
    if not coverage_complete:
        overall = "missing"
    elif "blocked" in action_statuses:
        overall = "blocked"
    else:
        overall = "ready"

    return {
        "schema_version": SCHEMA_VERSION,
        "id": manifest["id"],
        "owner_layer": manifest.get("owner_layer", "P4"),
        "audit_kind": manifest.get("audit_kind", "declaration_coverage"),
        "data_readback": "not_run",
        "coverage_complete": coverage_complete,
        "overall_status": overall,
        "summary": {
            "observed": action_statuses.count("observed"),
            "missing": action_statuses.count("missing"),
            "blocked": action_statuses.count("blocked"),
        },
        "actions": actions,
        "requirements": requirements,
        "gaps": gaps,
        "batch_blockers": {
            batch: sorted(ids) for batch, ids in sorted(batch_blockers.items())
        },
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        manifest = load_manifest(args.manifest)
        report = audit(manifest)
    except ManifestError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["coverage_complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
