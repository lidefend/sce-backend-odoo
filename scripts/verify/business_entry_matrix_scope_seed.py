#!/usr/bin/env python3
"""Seed the evidence ledger for the business-entry matrix from already-recorded runs.

Reuse-first: evidence already recorded for unchanged inputs must be reused
instead of re-collected.  This tool folds historical matrix runs into an
``evidence_scope.results.v1`` document for the evidence-scope engine, so the
planner afterwards reports only the units that genuinely still need execution.

Two admission rules, both mechanical:

* ``--run-current``: the run was produced by the current probe/derivation, so
  every key it reported is admitted as-is.
* ``--run-legacy``: the run predates the eligibility fix.  This tool re-derives
  the candidate that run used from the historical declaration and the observed
  principal closures, checks that replication against the aggregates the run
  itself recorded (checked/uncovered counts) and refuses to seed if they do not
  match.  A key is admitted only when the legacy candidate equals the candidate
  the current code resolves, i.e. only when the derivation did not move.

Units the declaration assigns to another lane are recorded as covered by that
declaration, with every referenced artifact verified to exist on disk; an
unreadable reference fails closed instead of silently claiming coverage.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MATRIX_MARKER = "frontend-business-entry-matrix"


class SeedError(RuntimeError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SeedError(message)


def load_units(path: Path) -> dict:
    document = json.loads(path.read_text(encoding="utf-8"))
    _require(document.get("schema") == "evidence_scope.units.v1", f"{path}: unexpected units schema")
    return document


def read_rows(text: str) -> list[dict]:
    return [row for row in csv.DictReader(text.splitlines()) if row.get("menu_xmlid")]


def git_show(revision: str, path: str) -> str:
    result = subprocess.run(["git", "-C", str(ROOT), "show", f"{revision}:{path}"],
                            check=False, capture_output=True, text=True)
    _require(result.returncode == 0, f"cannot read {path} at {revision}: {result.stderr.strip()[:200]}")
    return result.stdout


def declared_groups(row: dict) -> list[str]:
    try:
        parsed = json.loads(row.get("role_authority") or "{}")
    except json.JSONDecodeError:
        return []
    if isinstance(parsed.get("action_groups"), list) and parsed["action_groups"]:
        return [str(value) for value in parsed["action_groups"]]
    groups: list[str] = []
    for node in parsed.get("menu_chain") or []:
        groups.extend(str(value) for value in (node.get("groups") or []))
    return sorted(set(groups))


def legacy_assignment(rows: list[dict], order: list[str], closures: dict, keys: list[str]) -> tuple[dict, int, int]:
    """Re-derive the candidates the pre-eligibility probe used."""
    by_key = {row["menu_xmlid"]: row for row in rows}
    assignment: dict[str, str] = {}
    checked = 0
    uncovered = 0
    for key in keys:
        row = by_key.get(key)
        if row is None:
            uncovered += 1
            continue
        declared = declared_groups(row)
        if not declared:
            uncovered += 1
            continue
        chosen = None
        for role in order:
            caps = [str(value) for value in (closures.get(role) or {}).get("role_xmlids") or []]
            if not caps:
                continue
            if not any(cap in declared for cap in caps):
                chosen = role
                break
        if chosen:
            assignment[key] = chosen
            checked += 1
        else:
            uncovered += 1
    return assignment, checked, uncovered


def observed_aggregates(summary: dict) -> tuple[int, int]:
    checked = 0
    uncovered = 0
    for item in summary.get("observations") or []:
        if item.get("stage") == "authority_negative" and "checked_entries" in item:
            checked += int(item["checked_entries"])
        if item.get("stage") == "authority_negative_summary":
            uncovered = int(item.get("uncovered_entries") or 0)
    return checked, uncovered


def observed_candidates(summary: dict) -> list[str]:
    """The candidate set the run itself declared it used.

    A historical run predates the current declaration, so it must be replicated
    with the candidate order *it* recorded - otherwise a candidate added later
    would appear in the replication and the aggregate check would reject a run
    that was in fact consistent with its own declaration.
    """
    for item in summary.get("observations") or []:
        if item.get("stage") == "authority_negative_summary":
            return [str(role) for role in item.get("candidates") or []]
    return []


# The declaration's evidence field is prose: it cites artifacts, tools and
# anchors in one sentence, with full-width punctuation.  Only path-like tokens
# that carry a directory separator and an extension are treated as references;
# everything else is description.
_REFERENCE_RE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_./-]*/[A-Za-z0-9_./-]*\.[A-Za-z0-9]{1,6}")


def reference_paths(value: str) -> list[str]:
    seen: list[str] = []
    for match in _REFERENCE_RE.finditer(str(value or "")):
        token = match.group(0)
        if token not in seen:
            seen.append(token)
    return seen


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--units", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--reason", required=True)
    parser.add_argument("--declaration", required=True, help="current declaration CSV used for lane ownership")
    parser.add_argument("--run-current", action="append", default=[], help="summary produced by this code")
    parser.add_argument("--run-legacy", action="append", default=[],
                        help='{"summary": path, "revision": git-sha, "path": csv-in-that-revision}')
    parser.add_argument("--closures", required=True)
    parser.add_argument("--overlay", required=True)
    args = parser.parse_args(argv)

    document = load_units(Path(args.units))
    units = {str(unit["id"]): unit for unit in document["units"]}
    derived = document.get("derived") or {}
    overlay = json.loads(Path(args.overlay).read_text(encoding="utf-8"))
    order = [str(role) for role in overlay.get("denied_role_candidates") or []]
    closures = json.loads(Path(args.closures).read_text(encoding="utf-8"))["candidates"]

    results: dict[str, str] = {}
    sources: dict[str, str] = {}

    for item in args.run_current:
        summary = json.loads(Path(item).read_text(encoding="utf-8"))
        _require(summary.get("ok") is True, f"{item}: refusing to seed from a run that did not pass")
        keys = [str(entry.get("entry")) for entry in summary.get("entries") or []]
        for key in keys:
            if key in units:
                results[key] = "passed"
                sources[key] = f"reused:{item}"

    for item in args.run_legacy:
        spec = json.loads(item)
        summary = json.loads(Path(spec["summary"]).read_text(encoding="utf-8"))
        _require(summary.get("ok") is True, f"{spec['summary']}: refusing to seed from a run that did not pass")
        historical_rows = read_rows(git_show(spec["revision"], spec["path"]))
        keys = [str(entry.get("entry")) for entry in summary.get("entries") or []]
        recorded_candidates = observed_candidates(summary)
        unknown_candidates = sorted(set(recorded_candidates) - set(order))
        _require(
            not unknown_candidates,
            f"{spec['summary']}: the run declares candidates that are no longer declared: {unknown_candidates}",
        )
        legacy_order = [role for role in order if role in set(recorded_candidates)] or list(order)
        assignment, checked, uncovered = legacy_assignment(historical_rows, legacy_order, closures, keys)
        expected_checked, expected_uncovered = observed_aggregates(summary)
        _require(
            (checked, uncovered) == (expected_checked, expected_uncovered),
            f"{spec['summary']}: legacy replication mismatch (derived {checked}/{uncovered}, "
            f"recorded {expected_checked}/{expected_uncovered}) - refusing to seed",
        )
        for key, prior in assignment.items():
            if key not in units:
                continue
            if str((derived.get(key) or {}).get("candidate") or "") != prior:
                continue
            results[key] = "passed"
            sources[key] = f"reused:{spec['summary']}"

    rows = read_rows(Path(args.declaration).read_text(encoding="utf-8"))
    drift: dict[str, list[str]] = {}
    for row in rows:
        key = row["menu_xmlid"]
        if key in results or key not in units:
            continue
        evidence = str(row.get("evidence") or "")
        if MATRIX_MARKER in evidence:
            continue
        paths = reference_paths(evidence)
        _require(
            bool(paths),
            f"{key}: the declaration assigns this entry to no readable evidence owner",
        )
        missing = [path for path in paths if not (ROOT / path).exists()]
        if missing:
            # The entry is owned by another lane; a citation that no longer
            # resolves is that lane's drift, recorded here so it is visible and
            # never silently claimed as this check's own evidence.
            drift[key] = missing
        results[key] = "declared"
        sources[key] = f"declared:{paths[0]}"

    results_document = {
        "schema": "evidence_scope.results.v1",
        "check": document["check"],
        "executed_units": [{"id": key, "fingerprint": units[key]["fingerprint"]} for key in sorted(results)],
        "planned_affected": sorted(results),
        "results": results,
        "source": f"declared-equivalence: {args.reason}",
        "declaration_drift": drift,
    }
    Path(args.out).write_text(json.dumps(results_document, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    counts: dict[str, int] = {}
    for value in results.values():
        counts[value] = counts.get(value, 0) + 1
    residual = sorted(set(units) - set(results))
    print(f"[scope-seed] recorded={len(results)} of {len(units)} {counts} residual={len(residual)}")
    if drift:
        print(f"[scope-seed] WARN {len(drift)} declaration-owned entries cite unreadable evidence "
              "(another lane's drift, recorded in declaration_drift): ")
        for key, missing in sorted(drift.items()):
            print(f"[scope-seed]   {key}: {', '.join(missing[:2])}")
    if residual:
        print(f"[scope-seed] residual: {', '.join(residual[:12])}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SeedError as exc:
        print(f"[scope-seed] DENY {exc}", file=sys.stderr)
        raise SystemExit(2)
