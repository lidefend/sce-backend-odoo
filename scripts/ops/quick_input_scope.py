#!/usr/bin/env python3
"""Content-addressed input scope for the ci.local.quick target DAG.

Script-reference discovery is an advisory inventory. Execution reuse is limited
to reviewed complete offline scopes, bound to committed inputs and execution
identity. Undeclared targets always run at a new head. The shared evidence_scope
engine owns RUN/REUSE decisions; this adapter performs no execution or writes.
"""

from __future__ import annotations

import hashlib
import json
import os
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


# Only these offline Python tests have reviewed complete scopes. Script-reference
# discovery above remains an inventory, never authority to skip a target.
BOUNDED_TARGETS = frozenset({"verify.quick.evidence.unit", "verify.quick.input_scope.unit"})
BOUNDED_PREFIXES = ("scripts/", "make/")
BOUNDED_FILES = frozenset({"Makefile", "scripts/dev/local_dev_frontend_quick.py"})


def _fingerprint_rows(rows: list[str], target: str, head: str) -> str:
    if target not in BOUNDED_TARGETS:
        # No complete dependency declaration: never carry a target to a new head.
        return hashlib.sha256(f"undeclared:{target}:{head}".encode()).hexdigest()
    files = {}
    names = []
    for row in rows:
        path = row.partition("\t")[2]
        names.append(path)
        if path.startswith(BOUNDED_PREFIXES) or path in BOUNDED_FILES:
            files[path] = row
    # The inventory tests inspect path existence. Names (including additions and
    # deletions), all Make definitions and imported Python helpers are inputs.
    return hashlib.sha256(json.dumps({"files": files, "names": names},
                                     sort_keys=True).encode()).hexdigest()


def target_fingerprint(head: str, target: str, inputs=None, *, root: Path = ROOT) -> str:
    """Use committed blobs, including historical recipes and helper dependencies."""
    rows = git(root, "ls-tree", "-r", "--full-tree", head).splitlines()
    return _fingerprint_rows(rows, target, head)


def execution_identity() -> dict:
    # Do not persist environment values (they can contain credentials). Bind
    # their digest, Python runtime, and executable instead. Make's process-local
    # recursion counters and working-directory aliases are not test inputs.
    ignored = {"PWD", "OLDPWD", "SHLVL", "_", "MAKELEVEL", "MAKEFLAGS", "MFLAGS",
               "MAKEOVERRIDES", "SC_QUICK_SCAN_COVERAGE_DIR"}
    environment = {key: value for key, value in os.environ.items() if key not in ignored}
    return {"python": sys.version, "executable": str(Path(sys.executable).resolve()),
            "executable_sha256": hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),
            "environment_sha256": hashlib.sha256(json.dumps(environment, sort_keys=True).encode()).hexdigest()}


def execution_units(root: Path, head: str, targets: list[str]) -> dict:
    rows = git(root, "ls-tree", "-r", "--full-tree", head).splitlines()
    return {"schema": "evidence_scope.units.v1", "check": "ci.local.quick",
            "identity": execution_identity(),
            "units": [{"id": target, "fingerprint": _fingerprint_rows(rows, target, head),
                       "required": True} for target in targets]}


def plan_execution(current: dict, source: dict) -> dict:
    import evidence_scope
    ledger = {"check": current["check"], "identity": source["identity"],
              "units": {unit["id"]: {"fingerprint": unit["fingerprint"], "status": "passed"}
                        for unit in source["units"]}}
    return evidence_scope.plan_units(current, ledger)


def affected_targets(base: str, head: str) -> dict[str, str]:
    """Advisory plan; execution additionally requires a verified source receipt."""
    targets = quick_targets()
    plan = plan_execution(execution_units(ROOT, head, targets), execution_units(ROOT, base, targets))
    return {target: "REUSE" if target in plan["reusable"] else "RUN" for target in targets}
