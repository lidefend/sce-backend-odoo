#!/usr/bin/env python3
"""Content-addressed input scope for the ci.local.quick target DAG.

The Quick lane is a monolithic exact-head gate today: a change to any script it
verifies re-runs all 128 targets. This module maps each Quick target to its
declared input files (referenced scripts plus recipe flag paths) and computes a
per-target fingerprint, so a future reuse engine can re-run only affected
targets. It performs no execution and no writes.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "audit"))
import verification_lane_coverage as lanes


QUICK_ENTRY = "ci.local.quick.run"
# Recipe arguments that name a repository file: --flag path or KEY=path.
FLAG_PATH_RE = re.compile(r"(?:--[a-z-]+|(?:PATH|FILE|INPUT))=([A-Za-z0-9_./-]+)")


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def _parse():
    targets, recipes, prereqs, phony = lanes.parse_make(ROOT)
    edges, make_ref, script_ref = lanes.build_graph(targets, recipes, prereqs)
    return targets, recipes, edges, script_ref


def quick_targets() -> list[str]:
    _, _, edges, _ = _parse()
    return sorted(lanes.closure([QUICK_ENTRY], edges))


def target_inputs() -> dict[str, list[str]]:
    """Map each Quick target to its declared input files.

    Inputs are the scripts a target's recipe/prerequisite references plus the
    repository files named by that recipe's flag arguments. This is a bounded,
    conservative scope: a change to any listed file marks the target affected.
    """
    _, recipes, _, script_ref = _parse()
    targets = quick_targets()
    scripts_of_target: dict[str, set[str]] = {}
    for script, refs in script_ref.items():
        for ref in refs:
            target = ref.split(":", 1)[1]
            scripts_of_target.setdefault(target, set()).add(script)
    result = {}
    for target in targets:
        files = set(scripts_of_target.get(target, ()))
        for line in recipes.get(target, ()):
            for path in FLAG_PATH_RE.findall(line):
                if (ROOT / path).is_file():
                    files.add(path)
        result[target] = sorted(files)
    return result


def target_fingerprint(head: str, target: str, inputs: dict[str, list[str]] | None = None) -> str:
    """Hash the target's input blobs at an exact head, recipe included."""
    _, recipes, _, _ = _parse()
    inputs = inputs if inputs is not None else target_inputs()
    recipe = "\n".join(recipes.get(target, ()))
    material = {"recipe_sha256": hashlib.sha256(recipe.encode()).hexdigest(), "files": {}}
    for path in inputs.get(target, ()):
        entry = git(ROOT, "ls-tree", head, "--", path).strip()
        if not entry:
            continue
        material["files"][path] = entry
    payload = json.dumps(material, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def affected_targets(base: str, head: str) -> dict[str, str]:
    """Decide RUN vs REUSE per Quick target between two exact commits.

    A target is affected (RUN) only when its input fingerprint differs; targets
    with no declared inputs fail closed to RUN.
    """
    inputs = target_inputs()
    decisions = {}
    for target in quick_targets():
        old = target_fingerprint(base, target, inputs)
        new = target_fingerprint(head, target, inputs)
        if not inputs.get(target):
            decisions[target] = "RUN"
        elif old != new:
            decisions[target] = "RUN"
        else:
            decisions[target] = "REUSE"
    return decisions
