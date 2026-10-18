#!/usr/bin/env python3
"""Bind the acceptance surface to every code change.

A change is only "covered" when the paths it touches are declared in the
acceptance evolution registry and the acceptance suites that registry requires
are either:

* executed by the same governed lane (contract/governance suites), or
* backed by an exact-head evidence manifest produced by a real runtime run.

The plan half is deterministic and runs in every PR/local lane. The evidence
half is fail-closed and is required by ``make pr.merge``: a merge through the
governed path cannot reuse acceptance evidence from another commit.

Exit codes: 0 pass, 1 binding/evidence failure, 2 usage or registry error.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY = ROOT / "config" / "acceptance" / "evolution_binding.v1.json"
DEFAULT_PLAN = ROOT / ".runtime" / "acceptance-evolution" / "plan.json"
REGISTRY_SCHEMA = "acceptance_evolution_binding.v1"
PLAN_SCHEMA = "acceptance_evolution_plan.v1"
EVIDENCE_SCHEMA = "acceptance_evolution_evidence.v1"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
GLOB_CACHE: dict[str, re.Pattern[str]] = {}


class BindingError(RuntimeError):
    """A change, registry entry or evidence record cannot be trusted."""


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise BindingError(
            "git " + " ".join(args) + " failed: " + (result.stderr or "").strip()
        )
    return result.stdout.strip()


def glob_regex(pattern: str) -> re.Pattern[str]:
    compiled = GLOB_CACHE.get(pattern)
    if compiled:
        return compiled
    parts: list[str] = ["^"]
    index = 0
    while index < len(pattern):
        char = pattern[index]
        if char == "*":
            if index + 1 < len(pattern) and pattern[index + 1] == "*":
                index += 2
                if index < len(pattern) and pattern[index] == "/":
                    index += 1
                    parts.append("(?:.*/)?")
                else:
                    parts.append(".*")
                continue
            parts.append("[^/]*")
        elif char == "?":
            parts.append("[^/]")
        else:
            parts.append(re.escape(char))
        index += 1
    parts.append("$")
    compiled = re.compile("".join(parts))
    GLOB_CACHE[pattern] = compiled
    return compiled


def path_matches(pattern: str, path: str) -> bool:
    return bool(glob_regex(pattern).match(path))


def load_registry(path: Path) -> dict:
    try:
        registry = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise BindingError(f"registry unreadable: {path}: {exc}") from exc
    if registry.get("schema") != REGISTRY_SCHEMA:
        raise BindingError(f"registry schema must be {REGISTRY_SCHEMA}")
    suites = registry.get("suites")
    rules = registry.get("rules")
    if not isinstance(suites, dict) or not suites:
        raise BindingError("registry.suites must be a non-empty object")
    if not isinstance(rules, list) or not rules:
        raise BindingError("registry.rules must be a non-empty array")
    seen_rules: set[str] = set()
    for suite_id, suite in suites.items():
        if not isinstance(suite, dict):
            raise BindingError(f"suite {suite_id!r} must be an object")
        entrypoints = suite.get("entrypoints")
        if not isinstance(entrypoints, list) or not entrypoints:
            raise BindingError(f"suite {suite_id!r} needs at least one entrypoint")
        evidence = suite.get("evidence")
        if evidence is not None:
            adapter = evidence.get("adapter") if isinstance(evidence, dict) else None
            if adapter not in ADAPTERS:
                raise BindingError(f"suite {suite_id!r} has unknown evidence adapter {adapter!r}")
    for rule in rules:
        if not isinstance(rule, dict):
            raise BindingError("every rule must be an object")
        rule_id = rule.get("id")
        if not rule_id or rule_id in seen_rules:
            raise BindingError(f"rule id missing or duplicated: {rule_id!r}")
        seen_rules.add(rule_id)
        paths = rule.get("paths")
        if not isinstance(paths, list) or not paths or not all(isinstance(p, str) and p for p in paths):
            raise BindingError(f"rule {rule_id!r} needs non-empty path globs")
        suites_for_rule = rule.get("suites")
        if not isinstance(suites_for_rule, list):
            raise BindingError(f"rule {rule_id!r} suites must be an array")
        unknown = sorted(set(suites_for_rule) - set(suites))
        if unknown:
            raise BindingError(f"rule {rule_id!r} references unknown suites: {unknown}")
    policy = registry.get("policy") or {}
    if policy.get("unmapped_changes") not in {"fail", "warn"}:
        raise BindingError("policy.unmapped_changes must be 'fail' or 'warn'")
    return registry


def resolve_head(head: str | None) -> str:
    resolved = head or os.environ.get("HEAD_SHA") or _git("rev-parse", "HEAD")
    if not SHA_RE.match(resolved):
        raise BindingError(f"head must be a full 40-character SHA: {resolved!r}")
    _git("cat-file", "-e", f"{resolved}^{{commit}}")
    return resolved


def resolve_base(base: str | None, head: str) -> str:
    if base:
        candidate = base
    elif os.environ.get("BASE_SHA"):
        candidate = os.environ["BASE_SHA"]
    else:
        candidate = ""
        for ref in ("origin/main", "main"):
            result = subprocess.run(
                ["git", "merge-base", ref, head],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                candidate = result.stdout.strip()
                break
        if not candidate:
            candidate = _git("rev-parse", f"{head}^")
    if not SHA_RE.match(candidate):
        raise BindingError(f"base must be a full 40-character SHA: {candidate!r}")
    _git("cat-file", "-e", f"{candidate}^{{commit}}")
    return candidate


def changed_files(base: str, head: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=ACMRTD", f"{base}...{head}"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        result = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=ACMRTD", base, head],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
    if result.returncode != 0:
        raise BindingError("unable to compute changed files: " + (result.stderr or "").strip())
    return sorted({line.strip() for line in result.stdout.splitlines() if line.strip()})


def build_plan(registry: dict, changed: list[str], base: str, head: str) -> dict:
    suites = registry["suites"]
    rules = registry["rules"]
    matched: dict[str, str] = {}
    unclassified: list[str] = []
    required: list[str] = []
    for path in changed:
        rule = next(
            (item for item in rules if any(path_matches(glob, path) for glob in item["paths"])),
            None,
        )
        if rule is None:
            unclassified.append(path)
            continue
        matched[path] = rule["id"]
        for suite_id in rule["suites"]:
            if suite_id not in required:
                required.append(suite_id)
    ordered = [suite_id for suite_id in suites if suite_id in required]
    evidence_suites = [suite_id for suite_id in ordered if suites[suite_id].get("evidence")]
    status = "FAIL" if unclassified else "PASS"
    return {
        "schema": PLAN_SCHEMA,
        "base_sha": base,
        "head_sha": head,
        "changed_file_count": len(changed),
        "changed_files": changed,
        "matched_rules": matched,
        "required_suites": ordered,
        "required_evidence_suites": evidence_suites,
        "unclassified": unclassified,
        "status": status,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise BindingError(message)


def _adapter_entry_verify(data: dict, head: str) -> dict:
    _require(str(data.get("status", "")).upper() == "PASS", "entry verify status is not PASS")
    observed = {data.get("expected_sha"), data.get("head")}
    _require(head in observed, f"entry verify is bound to another head: {sorted(map(str, observed))}")
    checks = data.get("checks")
    _require(isinstance(checks, list) and checks, "entry verify has no checks")
    passed = sum(1 for check in checks if check.get("passed") is True)
    failed = len(checks) - passed
    _require(failed == 0 and passed > 0, f"entry verify checks failed={failed}")
    return {"counts": {"total": len(checks), "passed": passed, "failed": failed}}


def _adapter_path_ns_c(data: dict, head: str) -> dict:
    _require(data.get("schema") == "path-ns-c.acceptance.v1", "unexpected path namespace schema")
    summary = data.get("summary") or {}
    _require(str(summary.get("status", "")).upper() == "PASS", "path namespace status is not PASS")
    total = int(summary["total"]) if summary.get("total") is not None else 0
    passed = int(summary["passed"]) if summary.get("passed") is not None else 0
    failed = int(summary["failed"]) if summary.get("failed") is not None else -1
    _require(total > 0 and passed == total and failed == 0, "path namespace counts are not all-pass")
    provenance = data.get("provenance") or {}
    observed = provenance.get("expected_sha") or (data.get("target") or {}).get("expected_sha")
    _require(observed == head, f"path namespace evidence is bound to {observed!r}, expected {head}")
    return {"counts": {"total": total, "passed": passed, "failed": failed}}


def _adapter_list_surface(data: dict, head: str) -> dict:
    _require(
        data.get("schema") == "frontend_list_surface_structure_browser.v1",
        "unexpected list surface schema",
    )
    _require(data.get("passed") is True, "list surface did not pass")
    _require(int(data.get("failures") or 0) == 0, "list surface recorded failures")
    summary = data.get("summary") or {}
    _require(int(summary.get("runtime_errors") or 0) == 0, "list surface recorded runtime errors")
    acceptance = ((data.get("source") or {}).get("acceptance") or {})
    observed = (acceptance.get("provenance") or {}).get("expectedSha")
    _require(observed == head, f"list surface evidence is bound to {observed!r}, expected {head}")
    return {
        "counts": {
            "observations": int(summary.get("observations") or 0),
            "gated": (summary.get("gated") or {}).get("total")
            if isinstance(summary.get("gated"), dict)
            else summary.get("gated"),
            "failures": 0,
            "runtime_errors": 0,
        }
    }


def _adapter_relation_roundtrip(data: dict, head: str) -> dict:
    _require(
        data.get("schema") == "record-relation-roundtrip-acceptance.v1",
        "unexpected relation roundtrip schema",
    )
    _require(str(data.get("status", "")).lower() == "pass", "relation roundtrip status is not pass")
    _require(not (data.get("failures") or []), "relation roundtrip recorded failures")
    observed = data.get("expected_sha") or data.get("served_revision")
    _require(observed == head, f"relation roundtrip evidence is bound to {observed!r}, expected {head}")
    return {
        "counts": {
            "declared_entries": int(data.get("declared_entry_count") or 0),
            "openable_entries": len(data.get("declared_openable") or []),
        }
    }


ADAPTERS = {
    "entry_verify": _adapter_entry_verify,
    "path_ns_c": _adapter_path_ns_c,
    "list_surface": _adapter_list_surface,
    "relation_roundtrip": _adapter_relation_roundtrip,
}


def validate_evidence_file(path: Path, adapter: str, head: str) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise BindingError(f"evidence unreadable: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise BindingError(f"evidence must be a JSON object: {path}")
    return ADAPTERS[adapter](data, head)


def validate_manifest(registry: dict, plan: dict, manifest_path: Path, head: str) -> dict:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise BindingError(f"evidence manifest unreadable: {manifest_path}: {exc}") from exc
    _require(manifest.get("schema") == EVIDENCE_SCHEMA, f"manifest schema must be {EVIDENCE_SCHEMA}")
    _require(manifest.get("head_sha") == head, "manifest head_sha does not match the evaluated head")
    recorded_at = manifest.get("recorded_at")
    _require(isinstance(recorded_at, str) and recorded_at.endswith("Z"), "manifest recorded_at is invalid")
    try:
        recorded = datetime.datetime.fromisoformat(recorded_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise BindingError(f"manifest recorded_at is not ISO 8601: {exc}") from exc
    max_age = int((registry.get("policy") or {}).get("evidence_max_age_hours") or 72)
    age = datetime.datetime.now(datetime.timezone.utc) - recorded
    _require(age.total_seconds() <= max_age * 3600, f"manifest is older than {max_age}h")
    suites = manifest.get("suites")
    _require(isinstance(suites, dict), "manifest suites must be an object")
    unknown = sorted(set(suites) - set(registry["suites"]))
    _require(not unknown, f"manifest contains unknown suites: {unknown}")
    validated: dict[str, dict] = {}
    for suite_id in plan["required_evidence_suites"]:
        record = suites.get(suite_id)
        _require(isinstance(record, dict), f"manifest is missing required suite {suite_id}")
        _require(str(record.get("status", "")).lower() == "pass", f"suite {suite_id} is not passing")
        items = record.get("evidence")
        _require(isinstance(items, list) and items, f"suite {suite_id} has no evidence records")
        adapter = registry["suites"][suite_id]["evidence"]["adapter"]
        checked = []
        for item in items:
            _require(isinstance(item, dict), f"suite {suite_id} evidence entry must be an object")
            raw_path = item.get("path")
            _require(isinstance(raw_path, str) and raw_path, f"suite {suite_id} evidence path missing")
            path = Path(raw_path)
            if not path.is_absolute():
                path = ROOT / raw_path
            _require(path.is_file(), f"suite {suite_id} evidence file missing: {raw_path}")
            expected_sha = item.get("sha256")
            actual_sha = _sha256(path)
            _require(actual_sha == expected_sha, f"suite {suite_id} evidence changed after recording")
            counts = validate_evidence_file(path, adapter, head)
            checked.append({"path": raw_path, "sha256": actual_sha, "adapter": adapter, **counts})
        validated[suite_id] = {"status": "pass", "evidence": checked}
    return {"status": "PASS", "suites": validated}


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    parser.add_argument("--base", help="base commit; defaults to BASE_SHA or origin/main merge-base")
    parser.add_argument("--head", help="head commit; defaults to HEAD_SHA or HEAD")
    parser.add_argument("--output", default=str(DEFAULT_PLAN), help="plan artifact path")
    parser.add_argument("--manifest", help="exact-head acceptance evidence manifest")
    parser.add_argument(
        "--require-evidence",
        action="store_true",
        help="fail when the plan requires evidence and no manifest is supplied",
    )
    args = parser.parse_args(argv)
    try:
        registry = load_registry(Path(args.registry))
        head = resolve_head(args.head)
        base = resolve_base(args.base, head)
        changed = changed_files(base, head)
        plan = build_plan(registry, changed, base, head)
        write_json(Path(args.output), plan)
        if plan["status"] != "PASS":
            print(f"[acceptance_evolution] FAIL unclassified_files={len(plan['unclassified'])}")
            for path in plan["unclassified"]:
                print(f"  unclassified: {path}")
            print("  declare the path in config/acceptance/evolution_binding.v1.json first")
            return 1
        print(
            f"[acceptance_evolution] plan PASS files={plan['changed_file_count']} "
            f"suites={','.join(plan['required_suites']) or 'none'}"
        )
        if plan["required_evidence_suites"]:
            print(
                "[acceptance_evolution] runtime evidence required: "
                + ",".join(plan["required_evidence_suites"])
            )
        if args.manifest:
            result = validate_manifest(registry, plan, Path(args.manifest), head)
            print(
                f"[acceptance_evolution] evidence PASS suites={','.join(result['suites']) or 'none'} "
                f"head={head[:12]}"
            )
        elif args.require_evidence and plan["required_evidence_suites"]:
            print(
                "[acceptance_evolution] FAIL evidence manifest required for head "
                + head
            )
            return 1
        return 0
    except BindingError as exc:
        print(f"[acceptance_evolution] FAIL {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
