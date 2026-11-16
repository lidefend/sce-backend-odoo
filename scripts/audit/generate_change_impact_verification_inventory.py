#!/usr/bin/env python3
"""Build the P4-00 verification-system inventory from executable evidence.

This is a read-only repository audit. It does not execute verification targets,
change product behavior, write databases, or refresh generated evidence. It
combines the existing Make graph, workflow definitions, guard lifecycle
registry, acceptance-evolution binding and lane coverage instrument so the four
P4-00 artifacts share one measurable surface.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable

import yaml

ROOT = Path(__file__).resolve().parents[2]
AUDIT_DIR = ROOT / "scripts/audit"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(AUDIT_DIR) not in sys.path:
    sys.path.insert(0, str(AUDIT_DIR))
if str(ROOT / "scripts/ci") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts/ci"))

import verification_lane_coverage as coverage  # noqa: E402
import ci_risk_classifier as risk  # noqa: E402
from scripts.verify import acceptance_evolution_binding_guard as binding  # noqa: E402


SCHEMA = "change_impact_verification.inventory.v1"
OUTPUT_DIR = ROOT / "docs/audit/change-impact-verification"
GUARD_REGISTRY = ROOT / "docs/audit/guard_registry/guard_registry.json"
EXECUTABLE_RE = re.compile(
    r"(?<![A-Za-z0-9_./-])"
    r"((?:scripts|frontend|addons|demo_addons|customer_addons)/"
    r"[A-Za-z0-9_./@+-]+\.(?:py|sh|js|mjs|cjs|ts|tsx))"
)
EVIDENCE_RE = re.compile(
    r"(?<![A-Za-z0-9_./-])((?:artifacts|\.runtime)/[A-Za-z0-9_./-]+)"
)
SIM_IDENTIFIER_RE = re.compile(r"(?<![A-Za-z0-9_.-])((?:make|pnpm|node|python3?)\s+[^\n`]+)")


RESOURCE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("browser", re.compile(r"\b(playwright|chromium|browser\.new|page\.goto|page\.locator|aria)\b", re.I)),
    ("database", re.compile(r"\b(psycopg|postgres|DB_NAME|ODOO_DBFILTER|self\.env|TransactionCase|cursor\(\))", re.I)),
    ("container", re.compile(r"\b(docker compose|docker-compose|podman|bwrap|container)\b", re.I)),
    ("frontend_toolchain", re.compile(r"\b(esbuild|vue-tsc|pnpm|node_modules|vite)\b", re.I)),
    ("network", re.compile(r"\b(https?://|gh api|curl|ssh|requests\.|urlopen)\b", re.I)),
    ("filesystem_evidence", re.compile(r"\b(artifacts/|\.runtime/|--output|--report)\b", re.I)),
)

LAYER_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "L1",
        re.compile(
            r"\b(contract|schema|decoder|producer|consumer|semantic|normaliz|compatib|"
            r"action.view|view.contract|relation.field|field.semantic|identity)\b",
            re.I,
        ),
    ),
    (
        "L2",
        re.compile(
            r"\b(renderer|render|presentation|component|layout|visual|responsive|aria|"
            r"focus|keyboard|browser|viewport|page.interaction|style|focus)\b",
            re.I,
        ),
    ),
    (
        "L3",
        re.compile(
            r"\b(orm|acl|record.rule|permission|approval|state.transition|transaction|"
            r"persist|write|create|delete|workflow|business|domain|company|role|"
            r"settlement|payment)\b",
            re.I,
        ),
    ),
    (
        "L4",
        re.compile(
            r"\b(ci|workflow|security|scan|lint|typecheck|build|dependency|release|"
            r"merge|evidence|fingerprint|quick|git|artifact|publish)\b",
            re.I,
        ),
    ),
)

WORKFLOW_PROFILES: dict[str, dict[str, Any]] = {
    "backend_test_suite.yml:plan": {
        "verifies": "backend module scope, reuse decision and frozen execution-plan identity",
        "layers": ["L4"],
        "cannot": ["test correctness", "runtime contract or business behavior"],
    },
    "backend_test_suite.yml:verify_coverage": {
        "verifies": "planned module identities equal executed plus independently authorized reused test evidence",
        "layers": ["L4"],
        "cannot": ["the product semantics of a reused test", "frontend or deployment behavior"],
    },
    "public_guard.yml:classify": {
        "verifies": "selects the public-guard lane from the candidate change set",
        "layers": ["L4"],
        "cannot": ["product behavior"],
    },
    "merge_policy_gate.yml:classify": {
        "verifies": "selects and publishes the merge-policy lane from the candidate change set",
        "layers": ["L4"],
        "cannot": ["product behavior"],
    },
    "merge_policy_gate.yml:wait_for_fact_checks": {
        "verifies": "exact-head completion of public_guard, professional_quality_gate and frontend_release_gate",
        "layers": ["L4"],
        "cannot": ["product behavior beyond the waited workflows"],
    },
    "release_candidate_gate.yml:classify": {
        "verifies": "identity of the explicit release-candidate head",
        "layers": ["L4"],
        "cannot": ["product behavior"],
    },
    "release_candidate_gate.yml:wait_for_candidate_checks": {
        "verifies": "exact-head completion of all merge and candidate workflows",
        "layers": ["L4"],
        "cannot": ["product behavior beyond those workflows"],
    },
    "professional_quality_gate.yml:professional_quality_gate": {
        "verifies": "all required professional jobs ran and their selected outcomes agree with the impact plan",
        "layers": ["L4"],
        "cannot": ["product behavior not executed by the required child jobs"],
    },
    "merge_policy_gate.yml:merge_policy_gate": {
        "verifies": "exact-head completion of the declared fact workflows and final merge-policy aggregation",
        "layers": ["L4"],
        "cannot": ["any product layer beyond the conclusions of the workflows it waits for"],
    },
    "public_guard_classify": {
        "verifies": "classifies the candidate into FAST or required lanes from path ownership and risk policy",
        "layers": ["L4"],
        "cannot": ["contract correctness", "presentation behavior", "business persistence"],
    },
    "public_guard": {
        "verifies": "repository history hygiene, workflow security policy, protected guard tests and clean product boundary",
        "layers": ["L4"],
        "cannot": ["L1 contract runtime consumption", "L2 rendered page", "L3 business write outcome"],
    },
    "merge_policy_gate": {
        "verifies": "exact-head completion of the declared fact workflows and final merge-policy aggregation",
        "layers": ["L4"],
        "cannot": ["any product layer beyond the conclusions of the workflows it waits for"],
    },
    "fast": {
        "verifies": "cheap governance, security and release-version integrity for the FAST lane",
        "layers": ["L4"],
        "cannot": ["product contract, page or business behavior"],
    },
    "professional_authorization": {
        "verifies": "repository/actor authorization, risk classification and backend impact planning",
        "layers": ["L4"],
        "cannot": ["the selected product tests themselves"],
    },
    "backend_impact_suite": {
        "verifies": "the reusable backend suite selected from exact base/head trees",
        "layers": ["L1", "L3", "L4"],
        "cannot": ["real frontend presentation", "production data authority"],
    },
    "python310_runtime_compatibility": {
        "verifies": "selected release tools compile and preserve negative guards on Python 3.10",
        "layers": ["L4"],
        "cannot": ["product contract or business behavior"],
    },
    "professional_quality_checks": {
        "verifies": "mode-selected static, contract, backend, generated-report and governance checks",
        "layers": ["L1", "L3", "L4"],
        "cannot": ["L2 browser behavior unless separately covered by frontend_release_gate"],
    },
    "professional_quality_gate": {
        "verifies": "all required professional jobs ran and their selected outcomes agree with the impact plan",
        "layers": ["L4"],
        "cannot": ["product behavior not executed by the required child jobs"],
    },
    "frontend_release_gate": {
        "verifies": "frontend lint, strict types, unit tests, build, release browser suite and exact-head release evidence in full mode",
        "layers": ["L1", "L2", "L4"],
        "cannot": ["L3 persistence unless the specific journey observes the durable business result"],
    },
    "managed_orm": {
        "verifies": "selected managed Odoo ORM regressions in an isolated frontend acceptance runtime",
        "layers": ["L1", "L3", "L4"],
        "cannot": ["real browser rendering", "operator-data authority not present in the fixture"],
    },
    "release_candidate_gate": {
        "verifies": "exact-head merge eligibility and explicit candidate workflow completion",
        "layers": ["L4"],
        "cannot": ["deployment or user acceptance", "any product assertion omitted by candidate workflows"],
    },
    "frontend_release_evidence_bundle": {
        "verifies": "a current-main frontend artifact and its exact check/run/artifact/branch-protection provenance",
        "layers": ["L4"],
        "cannot": ["new product behavior; it packages and verifies existing evidence"],
    },
    "infra_stage_gate": {
        "verifies": "manually dispatched legacy Compose startup, stage gates, E2E contract/scene and navigation audits",
        "layers": ["L1", "L3"],
        "cannot": ["ordinary PR merge eligibility", "full modern frontend release presentation"],
    },
    "smoke": {
        "verifies": "manual disposable-container sc_smoke backend test; the data validator is non-blocking",
        "layers": ["L3"],
        "cannot": ["merge gate status", "L2 frontend presentation", "blocking proof of the validator"],
    },
    "demo_ci": {
        "verifies": "manual disposable demo scenario setup, frontend build identity and scenario command",
        "layers": ["L3", "L4"],
        "cannot": ["ordinary PR gates", "general product acceptance beyond the selected scenario"],
    },
    "backend_suite_plan": {
        "verifies": "backend module scope, reuse decision and frozen execution-plan identity",
        "layers": ["L4"],
        "cannot": ["test correctness", "runtime contract or business behavior"],
    },
    "backend_suite": {
        "verifies": "planned Odoo/Python module tests in isolated databases and records non-zero execution receipts",
        "layers": ["L1", "L3", "L4"],
        "cannot": ["L2 rendered behavior", "dynamic contract/fact closure when receipt blockers remain open"],
    },
    "backend_suite_verify_coverage": {
        "verifies": "planned module identities equal executed plus independently authorized reused test evidence",
        "layers": ["L4"],
        "cannot": ["the product semantics of a reused test", "frontend or deployment behavior"],
    },
}


def sha256_text(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_workflows() -> list[dict[str, Any]]:
    workflows = []
    for path in sorted((ROOT / ".github/workflows").glob("*.yml")):
        document = yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
        if not isinstance(document, dict):
            continue
        triggers = document.get("on") or {}
        jobs = []
        for job_id, job in sorted((document.get("jobs") or {}).items()):
            steps = []
            for index, step in enumerate(job.get("steps") or [], start=1):
                if not isinstance(step, dict):
                    continue
                run = str(step.get("run") or "")
                steps.append(
                    {
                        "index": index,
                        "name": str(step.get("name") or step.get("uses") or f"step-{index}"),
                        "if": str(step.get("if") or ""),
                        "uses": str(step.get("uses") or ""),
                        "run": run,
                        "env_keys": sorted((step.get("env") or {}).keys()),
                        "working_directory": str(step.get("working-directory") or ""),
                        "scripts": sorted(set(EXECUTABLE_RE.findall(run))),
                        "make_targets": sorted(
                            {
                                target
                                for line in run.splitlines()
                                for match in coverage.WF_MAKE_RE.finditer(line)
                                for target in match.group(1).split()
                            }
                        ),
                        "commands": sorted(set(SIM_IDENTIFIER_RE.findall(run)))[:40],
                        "resources": detect_resources(run),
                    }
                )
            jobs.append(
                {
                    "id": job_id,
                    "name": str(job.get("name") or job_id),
                    "if": str(job.get("if") or ""),
                    "needs": job.get("needs") or [],
                    "uses": str(job.get("uses") or ""),
                    "runs_on": str(job.get("runs-on") or ""),
                    "timeout_minutes": job.get("timeout-minutes"),
                    "steps": steps,
                }
            )
        workflows.append(
            {
                "id": path.name,
                "path": str(path.relative_to(ROOT)),
                "triggers": triggers,
                "permissions": document.get("permissions") or {},
                "jobs": jobs,
            }
        )
    return workflows


def module_summary(path: Path) -> str:
    if not path.is_file():
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    if path.suffix == ".py":
        try:
            doc = ast.get_docstring(ast.parse(text))
            if doc:
                return " ".join(doc.split())[:1200]
            return ""
        except SyntaxError:
            pass
    block = re.search(r'^\s*/\*\*?(.*?)\*/', text, re.S)
    if block:
        cleaned = re.sub(r"^\s*\* ?", "", block.group(1), flags=re.M)
        return " ".join(cleaned.split())[:1200]
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(("#!", "#!/")):
            continue
        if stripped.startswith(("# -*-", "# coding", "# Coding")):
            continue
        if stripped.startswith("#"):
            lines.append(stripped.lstrip("#").strip())
            if len(lines) >= 8:
                break
            continue
        if stripped:
            break
    return " ".join(lines)[:1200]


def detect_resources(text: str) -> list[dict[str, list[str]]]:
    found = []
    for name, pattern in RESOURCE_PATTERNS:
        values = sorted(set(match.group(0) for match in pattern.finditer(text)))[:20]
        if values:
            found.append({"kind": name, "evidence_tokens": values})
    return found


def infer_layers(text: str) -> list[str]:
    return [name for name, pattern in LAYER_PATTERNS if pattern.search(text)]


def script_inventory(path: Path) -> dict[str, Any]:
    text = ""
    if path.is_file():
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            pass
    summary = module_summary(path)
    combined = f"{path.as_posix()}\n{summary}\n{text[:200000]}"
    return {
        "summary": summary,
        "summary_source": "module docstring/header comment" if summary else "not_declared",
        "resources": detect_resources(combined),
        "layer_hints": infer_layers(combined),
        "line_count": len(text.splitlines()),
    }


def command_evidence(root: Path, commands: Iterable[str]) -> dict[str, Any]:
    texts: list[str] = []
    referenced: set[str] = set()
    for command in commands:
        texts.append(command)
        for rel in EXECUTABLE_RE.findall(command):
            path = root / rel
            if path.is_file() and path.stat().st_size <= 2_000_000:
                referenced.add(rel)
                try:
                    texts.append(path.read_text(encoding="utf-8", errors="replace"))
                except OSError:
                    pass
    combined = "\n".join(texts)
    return {
        "referenced_executables": sorted(referenced),
        "resources": detect_resources(combined),
        "layer_hints": infer_layers(combined),
        "evidence_paths": sorted(set(EVIDENCE_RE.findall(combined)))[:100],
    }


def executable_role(path: str) -> str:
    name = Path(path).name
    if "/tests/" in path or name.startswith("test_") or ".test." in name or "_test." in name:
        return "test"
    if path.startswith("scripts/verify/"):
        return "guard_or_probe"
    if path.startswith(("scripts/ci/", "scripts/ops/", "scripts/release/", "scripts/dev/")):
        return "tool_or_orchestrator"
    return "implementation_or_fixture"


def execution_modes(path: str, commands: Iterable[str]) -> list[str]:
    modes = set()
    for command in commands:
        if path not in command:
            continue
        if "py_compile" in command:
            modes.add("compiled")
        elif re.search(r"\bpython3?\b", command):
            modes.add("python_executed")
        elif re.search(r"\bnode\b", command):
            modes.add("node_executed")
        elif re.search(r"\b(?:bash|sh)\b", command):
            modes.add("shell_executed")
        else:
            modes.add("referenced")
    return sorted(modes) or ["referenced"]


def boundary_answers(
    *,
    subject: str,
    summary: str,
    triggers: dict[str, Any],
    actual_execution: list[str],
    resources: list[dict[str, list[str]]],
    layer_hints: list[str],
    automatic: bool,
) -> dict[str, Any]:
    resource_names = {item["kind"] for item in resources}
    layers = sorted(set(layer_hints), key=lambda value: int(value[1:]))
    cannot = []
    if "L1" not in layers:
        cannot.append("it does not execute a contract/schema/decoder assertion for this surface")
    if "L2" not in layers or "browser" not in resource_names:
        cannot.append("it does not prove real browser rendering or interaction for this surface")
    if "L3" not in layers or "database" not in resource_names:
        cannot.append("it does not prove ORM persistence, permissions or business-state outcome")
    if "L4" not in layers:
        cannot.append("it does not by itself establish delivery governance")
    cannot.extend(
        [
            "it does not prove behavior outside the assertions encoded by the executed files",
            "it does not make historical PASS evidence current when declared inputs, identity or environment changed",
        ]
    )
    verdict = (
        "When the named entry exits successfully, the executed commands and their non-zero assertions passed "
        "under the declared trigger and prerequisites."
        if automatic
        else "Only an explicit manual invocation can prove its encoded assertions; it is not dispatched by the automated gate graph."
    )
    return {
        "what_it_verifies": summary or f"{subject}: no stable semantic summary is declared; assertion scope requires source tracing",
        "what_triggers_it": triggers,
        "what_it_actually_executes": actual_execution,
        "services_and_database_dependencies": resources or [
            {"kind": "not_statically_detected", "evidence_tokens": []}
        ],
        "defects_it_can_detect": (
            "A violation of the assertions or nonzero command exit in the executed files"
        ),
        "what_it_can_prove": verdict,
        "what_it_cannot_prove": cannot,
        "duplicate_or_overlap": [],
    }


def make_inventory() -> tuple[dict[str, Any], dict[str, Any]]:
    measured = coverage.measure(
        ROOT,
        coverage.DEFAULT_EXEMPTIONS,
        coverage.DEFAULT_DISPOSITIONS,
    )
    targets, recipes, prereqs, phony = coverage.parse_make(ROOT)
    edges, make_ref, script_ref = coverage.build_graph(targets, recipes, prereqs)
    anchors = coverage.read_anchors(ROOT)
    anchor_targets = {anchor: coverage.closure([anchor], edges) for anchor in anchors}
    anchor_union = set().union(*(set(values) for values in anchor_targets.values()))
    lane_targets = {lane: coverage.closure(seeds, edges) for lane, seeds in coverage.LANES.items()}
    lane_for_target: dict[str, set[str]] = defaultdict(set)
    for lane, reached in lane_targets.items():
        for target in reached:
            lane_for_target[target].add(lane)
    anchor_for_target: dict[str, set[str]] = defaultdict(set)
    for anchor, reached in anchor_targets.items():
        for target in reached:
            anchor_for_target[target].add(anchor)

    workflow_calls = coverage.read_workflow_invocations(ROOT, targets)
    target_items = []
    all_real_targets = {
        target
        for target in targets
        if targets.get(target) is not None or target in phony
    }
    real_anchor_targets = {
        target
        for target in anchor_union
        if targets.get(target) is not None or target in phony
    }
    for target in sorted(real_anchor_targets):
        direct_commands = list(recipes.get(target, []))
        evidence = command_evidence(ROOT, direct_commands)
        triggered_by = {
            "gate_anchors": sorted(anchor_for_target.get(target, set())),
            "lanes": sorted(lane_for_target.get(target, set())),
            "workflow_invocations": sorted(workflow_calls.get(target, set())),
        }
        item = {
            "id": f"make:{target}",
            "type": "make_target",
            "entrypoint": f"make {target}",
            "source": targets.get(target),
            "automatic_gate": bool(anchor_for_target.get(target)),
            "prerequisites": sorted(set(prereqs.get(target, []))),
            "recursive_make_references": sorted(set(make_ref.get(target, []))),
            "direct_commands": direct_commands,
            "direct_executables": sorted(
                {
                    rel
                    for line in direct_commands
                    for rel in EXECUTABLE_RE.findall(line)
                }
            ),
            "resource_dependencies": evidence["resources"],
            "layer_hints": evidence["layer_hints"],
            "evidence_paths": evidence["evidence_paths"],
        }
        item["boundary_answers"] = boundary_answers(
            subject=target,
            summary="; ".join(module_summary(ROOT / rel) for rel in item["direct_executables"] if module_summary(ROOT / rel))[:1600],
            triggers=triggered_by,
            actual_execution=[f"make {target}", *direct_commands],
            resources=evidence["resources"],
            layer_hints=evidence["layer_hints"],
            automatic=True,
        )
        target_items.append(item)

    script_to_targets: dict[str, set[str]] = defaultdict(set)
    for target in real_anchor_targets:
        for line in recipes.get(target, []):
            for rel in EXECUTABLE_RE.findall(line):
                script_to_targets[rel].add(target)

    script_items = []
    for rel in sorted(script_to_targets):
        path = ROOT / rel
        details = script_inventory(path)
        using_targets = sorted(script_to_targets[rel])
        lane_names = sorted({lane for target in using_targets for lane in lane_for_target.get(target, set())})
        anchor_names = sorted({anchor for target in using_targets for anchor in anchor_for_target.get(target, set())})
        item = {
            "id": f"script:{rel}",
            "type": "executed_file",
            "path": rel,
            "execution_role": executable_role(rel),
            "execution_modes": execution_modes(
                rel,
                [
                    line
                    for target in using_targets
                    for line in recipes.get(target, [])
                ],
            ),
            "summary": details["summary"],
            "summary_source": details["summary_source"],
            "line_count": details["line_count"],
            "automatic_gate": True,
            "invoked_by_make_targets": using_targets,
            "gate_anchors": anchor_names,
            "lanes": lane_names,
            "resource_dependencies": details["resources"],
            "layer_hints": details["layer_hints"],
        }
        item["boundary_answers"] = boundary_answers(
            subject=rel,
            summary=details["summary"],
            triggers={"gate_anchors": anchor_names, "lanes": lane_names, "make_targets": using_targets},
            actual_execution=[
                f"{mode}: {rel} through " + ", ".join(f"make {target}" for target in using_targets)
                for mode in item["execution_modes"]
            ],
            resources=details["resources"],
            layer_hints=details["layer_hints"],
            automatic=True,
        )
        script_items.append(item)
    for item in script_items:
        shared = [
            other["id"]
            for other in script_items
            if other is not item
            and set(other["invoked_by_make_targets"]) & set(item["invoked_by_make_targets"])
        ]
        item["boundary_answers"]["duplicate_or_overlap"] = shared[:20]

    return {
        "targets": target_items,
        "scripts": script_items,
        "anchor_targets": {
            anchor: sorted(set(reached) & real_anchor_targets)
            for anchor, reached in anchor_targets.items()
        },
        "lane_targets": {lane: sorted(reached) for lane, reached in lane_targets.items()},
        "all_real_targets": all_real_targets,
        "raw": {
            "all_targets": targets,
            "recipes": recipes,
            "prereqs": prereqs,
            "edges": edges,
            "script_ref": script_ref,
            "phony": phony,
        },
        "measured": measured,
    }, measured


def script_lifecycle(measured: dict[str, Any], gate_scripts: set[str]) -> list[dict[str, Any]]:
    registry = read_json(GUARD_REGISTRY)
    by_path = {row.get("path"): row for row in registry.get("scripts", []) if isinstance(row, dict)}
    rows = []
    for path, entry in sorted(by_path.items()):
        if not path:
            continue
        target_refs = sorted(entry.get("referenced_by_make_targets") or [])
        workflow_refs = sorted(entry.get("referenced_by_workflows") or [])
        gate_enforced = path in gate_scripts
        if gate_enforced:
            lifecycle = "gate_enforced"
        elif entry.get("status") == "retired":
            lifecycle = "retired"
        elif entry.get("status") == "orphan":
            lifecycle = "orphan"
        elif entry.get("status") == "unwired":
            lifecycle = "unwired"
        elif target_refs or workflow_refs:
            lifecycle = "manual_or_non_gate_dispatch"
        else:
            lifecycle = "file_reference_only"
        details = script_inventory(ROOT / path)
        boundary = boundary_answers(
            subject=path,
            summary=details["summary"],
            triggers={
                "gate_enforced": gate_enforced,
                "make_targets": target_refs,
                "workflows": workflow_refs,
            },
            actual_execution=[path] if target_refs or workflow_refs else [],
            resources=details["resources"],
            layer_hints=details["layer_hints"],
            automatic=gate_enforced,
        )
        rows.append(
            {
                "path": path,
                "status": entry.get("status"),
                "lifecycle": lifecycle,
                "execution_role": executable_role(path),
                "referenced_by_make_targets": target_refs,
                "referenced_by_workflows": workflow_refs,
                "referenced_by_files": sorted((entry.get("referenced_by_files") or [])[:30]),
                "summary": details["summary"],
                "layer_hints": details["layer_hints"],
                "resources": details["resources"],
                "boundary_answers": boundary,
            }
        )
    return rows


def workflow_items(workflows: list[dict[str, Any]], valid_targets: set[str]) -> list[dict[str, Any]]:
    items = []
    for workflow in workflows:
        for job in workflow["jobs"]:
            profile = (
                WORKFLOW_PROFILES.get(f"{workflow['id']}:{job['id']}")
                or WORKFLOW_PROFILES.get(job["id"], {})
            )
            scripts = sorted({script for step in job["steps"] for script in step["scripts"]})
            make_targets = sorted(
                {
                    target
                    for step in job["steps"]
                    for target in step["make_targets"]
                    if target in valid_targets
                }
            )
            resources = [
                {"kind": kind, "evidence_tokens": sorted(tokens)}
                for kind, tokens in {
                    kind: set()
                    for kind in ("browser", "database", "container", "frontend_toolchain", "network")
                }.items()
                if tokens
            ]
            resource_map: dict[str, set[str]] = defaultdict(set)
            for step in job["steps"]:
                for resource in step["resources"]:
                    resource_map[resource["kind"]].update(resource["evidence_tokens"])
            resources = [
                {"kind": kind, "evidence_tokens": sorted(tokens)}
                for kind, tokens in sorted(resource_map.items())
            ]
            trigger = {
                "workflow": workflow["path"],
                "on": workflow["triggers"],
                "job_if": job["if"],
                "runs_on": job["runs_on"],
                "timeout_minutes": job["timeout_minutes"],
                "needs": job["needs"],
            }
            item = {
                "id": f"workflow:{workflow['id']}:{job['id']}",
                "type": "workflow_job",
                "workflow": workflow["path"],
                "job_id": job["id"],
                "job_name": job["name"],
                "uses": job["uses"],
                "trigger": trigger,
                "steps": [
                    {
                        "index": step["index"],
                        "name": step["name"],
                        "if": step["if"],
                        "uses": step["uses"],
                        "make_targets": step["make_targets"],
                        "scripts": step["scripts"],
                        "commands": step["commands"],
                        "env_keys": step["env_keys"],
                        "resources": step["resources"],
                    }
                    for step in job["steps"]
                ],
                "make_targets": make_targets,
                "scripts": scripts,
                "resources": resources,
                "layer_hints": sorted(set(profile.get("layers", []))),
            }
            item["boundary_answers"] = {
                "what_it_verifies": profile.get(
                    "verifies",
                    "the exact steps declared by this workflow job; no semantic profile is registered",
                ),
                "what_triggers_it": trigger,
                "what_it_actually_executes": {
                    "steps": [step["name"] for step in job["steps"]],
                    "make_targets": make_targets,
                    "scripts": scripts,
                    "uses": job["uses"],
                },
                "services_and_database_dependencies": resources,
                "defects_it_can_detect": (
                    "A failure in any executed command, selector, evidence adapter or declared exact-head condition"
                ),
                "what_it_can_prove": (
                    "The selected workflow job completed its actual commands under its job condition and exact checked-out source."
                ),
                "what_it_cannot_prove": profile.get(
                    "cannot",
                    ["any assertion or behavior not executed by its explicit steps"],
                )
                + [
                    "a passing job does not override a failed/skipped prerequisite or an identity drift",
                    "workflow green does not mean deployment or user acceptance",
                ],
                "duplicate_or_overlap": [],
            }
            items.append(item)
    return items


def acceptance_inventory() -> dict[str, Any]:
    registry = binding.load_registry(binding.DEFAULT_REGISTRY)
    suites = []
    layer_map = {
        "backend_contract": ["L1", "L3", "L4"],
        "frontend_contract": ["L1", "L2", "L4"],
        "frontend_presentation": ["L2"],
        "governance_static": ["L4"],
        "daily_runtime_entry": ["L3", "L4"],
        "path_namespace_identity": ["L2", "L3", "L4"],
        "list_surface_structure": ["L1", "L2"],
        "relation_roundtrip": ["L1", "L2", "L3"],
    }
    for suite_id, suite in registry["suites"].items():
        suites.append(
            {
                "id": suite_id,
                "description": suite.get("description"),
                "entrypoints": suite.get("entrypoints") or [],
                "stages": suite.get("stages") or [],
                "inputs": suite.get("inputs") or [],
                "make_inputs": suite.get("make_inputs") or [],
                "evidence": suite.get("evidence"),
                "layer_hints": layer_map.get(suite_id, []),
                "boundary_answers": {
                    "what_it_verifies": suite.get("description") or "no suite description",
                    "what_triggers_it": "acceptance-evolution first-match rule for changed paths plus the selected stage",
                    "what_it_actually_executes": suite.get("entrypoints") or [],
                    "services_and_database_dependencies": (
                        "runtime/browser/database dependencies are encoded by the entrypoint; inspect the graph nodes for this suite"
                    ),
                    "defects_it_can_detect": "a failure in the suite evidence adapter, required check set or bound input fingerprint",
                    "what_it_can_prove": "the declared evidence adapter accepted a current exact-head record for this suite",
                    "what_it_cannot_prove": [
                        "behavior outside the adapter's required checks",
                        "a different stage or environment",
                        "pass during another head when suite inputs or identity changed",
                    ],
                    "duplicate_or_overlap": [],
                },
            }
        )
    return {
        "schema": registry.get("schema"),
        "policy": registry.get("policy"),
        "suites": suites,
        "rules": registry.get("rules") or [],
    }


def classification_probes() -> list[dict[str, Any]]:
    paths = [
        "frontend/apps/web/src/app/contracts/v2/schema.ts",
        "frontend/apps/web/src/app/contracts/v2/legacyLayoutNormalizer.ts",
        "frontend/apps/web/src/app/presentation/professionalComponentRegistry.ts",
        "frontend/apps/web/src/app/presentation/contractFormPresenter.ts",
        "frontend/apps/web/src/pages/contractForm/ContractForm.vue",
        "frontend/apps/web/src/pages/listPage/ListPage.vue",
        "frontend/apps/web/src/components/product-page-header/ProductPageHeader.vue",
        "frontend/apps/web/src/app/runtime/businessListQueryRuntime.ts",
        "addons/smart_core/contracts/schema.py",
        "addons/smart_construction_core/models/project.py",
        "addons/smart_construction_core/data/approval_policy_seed.xml",
        "scripts/verify/frontend_page_contract_boundary_guard.py",
        "docs/audit/change-impact-verification/README.md",
    ]
    registry = binding.load_registry(binding.DEFAULT_REGISTRY)
    head = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    plan = binding.build_plan(registry, paths, head, head)
    rows = []
    for path in paths:
        try:
            risk_result = asdict(
                risk.classify([path], event_name="pull_request", ref="refs/pull/1/head")
            )
        except Exception as exc:  # pragma: no cover - diagnostic surface
            risk_result = {"error": str(exc)}
        rule_id = plan["matched_rules"].get(path)
        rule = next((item for item in registry["rules"] if item["id"] == rule_id), None)
        suites = list(rule["suites"]) if rule else []
        rows.append(
            {
                "path": path,
                "risk_classifier": risk_result,
                "acceptance_rule": rule_id,
                "acceptance_suites": suites,
                "evidence_suites": [
                    suite_id for suite_id in suites if registry["suites"][suite_id].get("evidence")
                ],
            }
        )
    return rows


def build_inventory() -> dict[str, Any]:
    workflows = load_workflows()
    make_data, measured = make_inventory()
    gate_scripts = {item["path"] for item in make_data["scripts"]}
    lifecycle = script_lifecycle(measured, gate_scripts)
    result = {
        "schema": SCHEMA,
        "source_head": subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
        ).strip(),
        "source_tree": subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD^{tree}"], text=True
        ).strip(),
        "method": {
            "verification_item": (
                "A workflow job, automated make anchor/target, gate-enforced executable, "
                "acceptance suite, or explicitly classified long-tail guard."
            ),
            "make_graph": "Parsed by scripts/audit/verification_lane_coverage.py from Makefile and make/*.mk",
            "workflow_graph": "Parsed from all .github/workflows/*.yml jobs and steps",
            "resource_inference": (
                "Keyword/resource signals are evidence hints, not proof of execution. "
                "not_statically_detected means the repository metadata does not establish the dependency."
            ),
            "semantic_inference": (
                "Module docstrings/header comments and executable commands are cited. "
                "No verification responsibility is accepted from a filename alone."
            ),
        },
        "workflow_jobs": workflow_items(workflows, set(make_data["raw"]["all_targets"])),
        "make_targets": make_data["targets"],
        "gate_scripts": make_data["scripts"],
        "script_lifecycle": lifecycle,
        "acceptance_binding": acceptance_inventory(),
        "classification_probes": classification_probes(),
        "surface_summary": {
            **{
                key: measured[key]
                for key in (
                    "targets_defined",
                    "phony_targets",
                    "gate_anchors",
                    "anchor_reachable_targets",
                    "anchor_union_targets",
                    "targets_unreached_from_anchor",
                    "lanes",
                    "scripts_on_disk",
                    "scripts_owned_surface",
                    "scripts_verify_lifecycle_owned",
                    "scripts_retired",
                    "targets_missing_asset",
                    "local_only_scripts",
                    "remote_only_scripts",
                )
            },
            "targets_zero_reference": measured["targets_zero_reference"],
            "scripts_unreferenced_anywhere": measured["scripts_unreferenced_anywhere"],
            "normalized_anchor_targets": len(make_data["targets"]),
            "anchor_parser_non_target_nodes": measured["anchor_union_targets"] - len(make_data["targets"]),
            "normalized_all_targets": len(make_data["all_real_targets"]),
            "parser_non_target_nodes_all": measured["targets_defined"] - len(make_data["all_real_targets"]),
        },
        "long_tail_boundary": {
            "definition": (
                "Make targets or scripts not reachable from the four declared gate anchors. "
                "They may be manual, diagnostic, runtime, deployment, legacy or dead surface."
            ),
            "cannot_support_claim": (
                "A long-tail script cannot support merge or delivery evidence until a workflow or "
                "governed lane actually dispatches it and its receipt is current."
            ),
        },
    }
    return result


def build_execution_graph(inventory: dict[str, Any]) -> dict[str, Any]:
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, str]] = []

    def add_node(identifier: str, kind: str, **attributes: Any) -> None:
        nodes[identifier] = {"id": identifier, "kind": kind, **attributes}

    def add_edge(source: str, target: str, relation: str) -> None:
        edges.append({"from": source, "to": target, "relation": relation})

    for workflow in load_workflows():
        wid = f"workflow:{workflow['id']}"
        add_node(wid, "workflow", path=workflow["path"], triggers=workflow["triggers"])
        for job in workflow["jobs"]:
            jid = f"job:{workflow['id']}:{job['id']}"
            add_node(
                jid,
                "workflow_job",
                workflow=workflow["path"],
                name=job["name"],
                runs_on=job["runs_on"],
                timeout_minutes=job["timeout_minutes"],
                uses=job["uses"],
            )
            add_edge(wid, jid, "contains_job")
            for need in job["needs"] if isinstance(job["needs"], list) else [job["needs"]]:
                if need:
                    add_edge(jid, f"job:{workflow['id']}:{need}", "needs")
            for step in job["steps"]:
                sid = f"step:{workflow['id']}:{job['id']}:{step['index']}"
                add_node(
                    sid,
                    "workflow_step",
                    name=step["name"],
                    condition=step["if"],
                    uses=step["uses"],
                    resources=step["resources"],
                )
                add_edge(jid, sid, "contains_step")
                for target in step["make_targets"]:
                    add_edge(sid, f"make:{target}", "invokes_make")
                for script in step["scripts"]:
                    add_edge(sid, f"script:{script}", "executes_script")

    for item in inventory["make_targets"]:
        tid = item["id"]
        add_node(
            tid,
            "make_target",
            entrypoint=item["entrypoint"],
            source=item["source"],
            automatic_gate=item["automatic_gate"],
            layer_hints=item["layer_hints"],
        )
        for prerequisite in item["prerequisites"]:
            add_edge(tid, f"make:{prerequisite}", "prerequisite")
        for command in item["direct_commands"]:
            for match in coverage.MAKE_CALL_RE.finditer(command):
                for target in match.group(1).split():
                    add_edge(tid, f"make:{target}", "recursive_make")
            for script in EXECUTABLE_RE.findall(command):
                add_edge(tid, f"script:{script}", "executes_script")
        for resource in item["resource_dependencies"]:
            rid = f"resource:{resource['kind']}"
            add_node(rid, "resource", resource_kind=resource["kind"])
            add_edge(tid, rid, "observed_dependency")
        for evidence_path in item["evidence_paths"]:
            eid = f"evidence:{evidence_path}"
            add_node(eid, "evidence_path", path=evidence_path)
            add_edge(tid, eid, "may_write_or_read_evidence")

    for item in inventory["gate_scripts"]:
        sid = item["id"]
        add_node(
            sid,
            "executable_check",
            path=item["path"],
            summary=item["summary"],
            layer_hints=item["layer_hints"],
            resources=item["resource_dependencies"],
        )
        for resource in item["resource_dependencies"]:
            add_edge(sid, f"resource:{resource['kind']}", "observed_dependency")

    for target, targets in inventory["surface_summary"]["anchor_reachable_targets"].items():
        pass
    for suite in inventory["acceptance_binding"]["suites"]:
        sid = f"acceptance_suite:{suite['id']}"
        add_node(sid, "acceptance_suite", **suite["boundary_answers"])
        add_edge(sid, "authority:acceptance_evolution_binding", "bound_by")
        for entry in suite["entrypoints"]:
            for target in coverage.WF_MAKE_RE.findall(entry) if isinstance(entry, str) else []:
                add_edge(sid, f"make:{target}", "declared_entrypoint")

    for authority in (
        "agent_run_context",
        "acceptance_evolution_binding",
        "evidence_scope",
        "local_quick_receipt",
        "backend_test_receipt",
        "validation_delivery_plan",
    ):
        add_node(f"authority:{authority}", "evidence_authority", name=authority)

    return {
        "schema": "change_impact_verification.execution_graph.v1",
        "source_head": inventory["source_head"],
        "nodes": sorted(nodes.values(), key=lambda row: row["id"]),
        "edges": sorted(edges, key=lambda row: (row["from"], row["relation"], row["to"])),
    }


def build_cost_baseline(inventory: dict[str, Any]) -> dict[str, Any]:
    resource_counts = Counter()
    layer_counts = Counter()
    target_classes = Counter()
    for item in inventory["make_targets"]:
        resources = {row["kind"] for row in item["resource_dependencies"]}
        if "database" in resources:
            target_class = "database_or_orm"
        elif "browser" in resources:
            target_class = "browser"
        elif "container" in resources:
            target_class = "container"
        elif "frontend_toolchain" in resources:
            target_class = "frontend_toolchain"
        elif "network" in resources:
            target_class = "network"
        else:
            target_class = "static_or_unknown"
        target_classes[target_class] += 1
        resource_counts.update(resources)
        layer_counts.update(item["layer_hints"])

    lifecycle_counts = Counter(row["lifecycle"] for row in inventory["script_lifecycle"])
    lane = inventory["surface_summary"]["lanes"]
    return {
        "schema": "change_impact_verification.cost_baseline.v1",
        "source_head": inventory["source_head"],
        "measurement_policy": {
            "seconds": (
                "No fabricated seconds. Only lane telemetry observations and explicit documented "
                "typical-method estimates may be reported as durations."
            ),
            "resource_classes": (
                "Heuristic static classes from actual commands and referenced source. "
                "static_or_unknown is not a claim that execution is cheap."
            ),
        },
        "surface": {
            "workflow_jobs": len(inventory["workflow_jobs"]),
            "workflow_steps": sum(len(item["steps"]) for item in inventory["workflow_jobs"]),
            "gate_anchor_targets": inventory["surface_summary"]["anchor_union_targets"],
            "gate_enforced_make_targets": len(inventory["make_targets"]),
            "gate_enforced_executables": len(inventory["gate_scripts"]),
            "all_make_targets": inventory["surface_summary"]["targets_defined"],
            "normalized_all_make_targets": inventory["surface_summary"]["normalized_all_targets"],
            "all_scripts_on_disk": inventory["surface_summary"]["scripts_on_disk"],
            "zero_reference_targets": len(inventory["surface_summary"]["targets_zero_reference"]),
            "unreferenced_scripts": len(inventory["surface_summary"]["scripts_unreferenced_anywhere"]),
            "missing_asset_targets": len(inventory["surface_summary"]["targets_missing_asset"]),
        },
        "lane_static_cost": {
            lane_id: {
                **values,
                "relative_weight": (
                    "very_high"
                    if lane_id in {"local.quick", "remote.frontend.full", "remote.professional.backend.verify"}
                    else "high"
                    if lane_id.startswith("remote.")
                    else "bounded"
                ),
            }
            for lane_id, values in lane.items()
        },
        "resource_class_counts": dict(sorted(resource_counts.items())),
        "target_class_counts": dict(sorted(target_classes.items())),
        "layer_hint_counts": dict(sorted(layer_counts.items())),
        "script_lifecycle_counts": dict(sorted(lifecycle_counts.items())),
        "documented_typical_minutes": {
            "source": "docs/ops/ci_feedback_latency_v1.md",
            "public_guard": "4-5",
            "professional_quality_gate": "9-14",
            "frontend_release_gate": "10-16",
            "merge_policy_gate_critical_path": "14-16",
        },
        "observed_lane_telemetry": {
            "source": "make lane.telemetry.report",
            "observations": 0,
            "note": "Current checkout has no recorded lane telemetry; no runtime duration is inferred.",
        },
        "dominant_costs": [
            "trusted full-history and security scans when scan authority changes",
            "managed ORM containers, disposable databases and fixture preparation",
            "full frontend release: pnpm toolchain, Playwright browser, build and browser journeys",
            "duplicated target/script execution across local.quick and remote professional lanes",
        ],
    }


def markdown_report(inventory: dict[str, Any], graph: dict[str, Any], cost: dict[str, Any]) -> str:
    summary = inventory["surface_summary"]
    workflow_rows = "\n".join(
        f"| `{item['workflow']}` | `{item['job_id']}` | {item['boundary_answers']['what_it_verifies']} | "
        f"{', '.join(item['layer_hints']) or 'unknown'} |"
        for item in inventory["workflow_jobs"]
    )
    lane_rows = "\n".join(
        f"| `{lane}` | {values['targets']} | {values['scripts']} | "
        f"{cost['lane_static_cost'][lane]['relative_weight']} |"
        for lane, values in summary["lanes"].items()
    )
    suite_rows = "\n".join(
        f"| `{suite['id']}` | {suite['description']} | {', '.join(suite['stages'])} | "
        f"{suite['evidence']['adapter'] if suite['evidence'] else 'no evidence adapter'} |"
        for suite in inventory["acceptance_binding"]["suites"]
    )
    gate_script_rows = "\n".join(
        f"| `{row['path']}` | {row['lifecycle']} | {', '.join(row['layer_hints']) or 'unknown'} | "
        f"{row['summary'][:180] or 'no docstring'} |"
        for row in inventory["script_lifecycle"]
        if row["lifecycle"] == "gate_enforced"
    )
    probe_rows = "\n".join(
        f"| `{row['path']}` | `{row['risk_classifier'].get('lane', 'unknown')}` | "
        f"`{row['acceptance_rule'] or 'none'}` | {', '.join(row['acceptance_suites']) or 'none'} |"
        for row in inventory["classification_probes"]
    )
    return f"""# 验证体系全量盘点与边界

## 1. 身份与口径

- 源码 HEAD：`{inventory['source_head']}`
- 源码 tree：`{inventory['source_tree']}`
- 类型：P4 只读审计，不执行产品门禁、不写数据库、不改变断言。
- 验证项：workflow job、四个 gate anchor 可达的 Make target、其实际执行的脚本、
  acceptance suite，以及 guard registry 中的完整脚本生命周期。
- “实际执行”来自 Make recipe、workflow step、脚本路径和资源关键词；名称本身不构成
  验证责任证明。没有稳定 docstring 的项目明确记为需要源码追踪。

## 2. 全量规模

| 指标 | 数量 |
| --- | ---: |
| 原 Make 解析器定义计数 | {summary['targets_defined']} |
| 归一化后的真实 Make target | {summary['normalized_all_targets']} |
| 原解析器非 target 变量形状节点 | {summary['parser_non_target_nodes_all']} |
| `.PHONY` target | {summary['phony_targets']} |
| gate anchor | {len(summary['gate_anchors'])} |
| 原仪器 anchor 可达节点并集 | {summary['anchor_union_targets']} |
| 归一化后的真实 target | {summary['normalized_anchor_targets']} |
| 原仪器非 target 变量形状节点 | {summary['anchor_parser_non_target_nodes']} |
| 非 anchor 可达 target | {summary['targets_unreached_from_anchor']} |
| 零引用 target | {len(summary['targets_zero_reference'])} |
| `scripts/**` 在盘脚本 | {summary['scripts_on_disk']} |
| guard registry 脚本 | {len(inventory['script_lifecycle'])} |
| anchor 可达实际脚本项 | {len(inventory['gate_scripts'])} |
| 全仓零引用脚本 | {len(summary['scripts_unreferenced_anywhere'])} |
| recipe 引用不存在资产的 target | {len(summary['targets_missing_asset'])} |

四个 gate anchor：

{chr(10).join(f"- `{anchor}`：{count} 个可达 target" for anchor, count in summary['anchor_reachable_targets'].items())}

## 3. Lane 结构与实际覆盖面

| lane | 可达 target | 脚本 | 静态成本等级 |
| --- | ---: | ---: | --- |
{lane_rows}

同一 target 可以同时属于多个 lane。lane 数量是“实际调度面”，不是唯一测试数。
`local.quick` 与远端 professional lane 的交集可以复用同一脚本，但只有在输入、环境和
证据身份均等价时才能复用结果。

## 4. Workflow job 边界

| workflow | job | 它证明什么 | 推断层 |
| --- | --- | --- | --- |
{workflow_rows}

workflow 的 final gate job 通常只聚合子 job，不自行执行产品断言。父 workflow 成功不能扩张
子 job 的证明边界；skip、required=false、non-blocking step 也不能被写成产品 PASS。

## 5. 产品验证层

### L1 Contract Verification

只证明 Schema、Strict Decoder、Producer/Consumer、Action/View/Search Identity、关系字段规范化
和契约兼容性。静态 schema guard 能证明声明/结构约束，不能单独证明真实前端已经消费该契约，
也不能证明业务状态正确。

### L2 Presentation Verification

只证明真实 Renderer 选择、组件装配、布局/视觉、字段列顺序、响应式、键盘/焦点/ARIA 和页面
交互。浏览器出现、页面可打开或选择器命中不等于契约正确；浏览器签名也不能替代 L1。

### L3 Business Acceptance

只证明业务状态转换、ORM 写入/持久化、权限正负例、审批执行、跨模型关系、事务并发和端到端
业务结果。后端单元测试若不是通过真实 Odoo runtime/数据库执行，不能声称持久化或 ACL 证明。

### L4 Delivery Governance

只证明代码质量、安全、类型、依赖、构建、变更范围、精确 HEAD、CI 与合并前审查。L4 可以阻断
交付，但不能替代 L1/L2/L3 的产品行为证明。

## 6. 当前触发与分类事实

### 6.1 风险分类和验收绑定的代表路径

| 路径 | risk lane | acceptance rule | 验收 suites |
| --- | --- | --- | --- |
{probe_rows}

当前已确认两个方向的结构性问题：

1. `frontend/apps/web/src/app/contracts/v2/**` 被 `frontend-contract-form-consumer` 同时归入
   `frontend_contract` 和带真实浏览器证据的 `frontend_presentation`，因此契约/Decoder 修改会
   要求页面验收。
2. `professionalComponentRegistry.ts` 当前只命中通用 `frontend-runtime -> frontend_contract`，
   没有自动进入 presentation evidence；Renderer 注册变化可能只得到通用前端验证，无法证明
   受影响页面实际呈现了变化。

这两项是“路径分类不能代表实际能力影响”的直接证据，不是对整个 PR 的唯一标签结论。

### 6.2 混合变更

分类必须按文件和符号取并集。一个候选同时修改 Search Contract、搜索栏组件和业务 Domain 时，
L1、L2、L3 风险同时存在，不能因为主要路径属于一类而降级其他层。未知路径必须保守处理。

## 7. Acceptance Evolution 边界

| suite | 描述 | stage | evidence |
| --- | --- | --- | --- |
{suite_rows}

`acceptance_evolution` 只决定路径需要哪些 suite 和证据 adapter；实际命令仍由 suite
entrypoint 执行。`validation_delivery_plan` 是只读计划/证据诊断，不是执行器、不是通过回执，
也不替代远端 required CI。

## 8. 证据生命周期

| 权威 | 绑定什么 | 允许复用的最小条件 | 不能证明什么 |
| --- | --- | --- | --- |
| `agent_run_context` | run、check、声明输入哈希、原始日志哈希、source head、环境 | 所有声明输入、上游输入、环境和日志未变；offline 或带权威 readback 的 runtime check | 未声明依赖、当前远端 CI、产品行为越出断言 |
| `acceptance_evolution` | suite descriptor、匹配输入及 Make target/variable 指纹、exact head evidence | suite 输入指纹与当前 revision 相同，adapter 验证 record 绑定当前 head | suite 未覆盖的页面、角色或业务结果 |
| `evidence_scope` | 每个声明 unit 的 fingerprint 和 runtime identity | unit fingerprint、identity 和成功状态均未变 | 未声明 unit，或由部署版本号本身推断行为 |
| `local_quick_receipt` | clean exact head/tree、target coverage、scan coverage | 精确 head；或 bookkeeping-only 祖先且 runtime tree digest 与扫描权威不变 | 未在 Quick 内的远端检查、数据库升级或浏览器旅程 |
| `backend_test_receipt` | source/context、执行定义、readback、依赖闭包、平台认证 | 只有独立认证的隔离执行或六维闭合可授权 REUSE | 生产者自报 `reuse_ready=true`；缺失契约/事实 readback 的 ORM |
| `frontend_release_evidence_bundle` | 当前 main artifact、check/run/artifact/ruleset 与 tree | bundle 校验当前 SHA/tree 且来源 run/artifact 可核验 | 新候选、部署或用户验收 |

统一规则：

- HEAD 是来源身份，不自动是复用有效性键。
- 输入、断言、工具、依赖或环境变化使相关证据失效。
- 文档变化不自动使页面行为证据失效；运行时/chrome/artifact 变化必须触发对应失效。
- `PASS`、`skip`、`not_run`、`unknown` 必须分开；零测试不是 PASS。
- 历史证据只有在独立复用权威验证后才可引用，不能复制成当前执行回执。

## 9. 执行依赖与成本边界

| 资源类 | anchor target 数 |
| --- | ---: |
{chr(10).join(f"| `{name}` | {count} |" for name, count in cost['target_class_counts'].items())}

仓库当前 lane telemetry 没有实际运行记录，所以本基线不编造 target 耗时。可引用的实测历史区间
仅限 `docs/ops/ci_feedback_latency_v1.md`：

- `public_guard`：4–5 分钟
- `professional_quality_gate`：9–14 分钟
- `frontend_release_gate`：10–16 分钟
- `merge_policy_gate` 关键路径：14–16 分钟

高成本来源主要是：扫描权威变化导致的 trusted full scan、ORM 容器/新库/fixture、Playwright
安装与完整页面矩阵、以及同一脚本在 local/remote lanes 的重复调度。

## 10. 不得自动放行的边界

以下情况必须 BLOCK 或 RUN，不能靠路径/历史 PASS 放行：

- 路径未分类、unknown、rename/delete 只取单端。
- 修改了执行器、选择器、断言、fixture、schema、生成器、锁文件或 Make/workflow 权威，相关回执未失效。
- suite/evidence adapter 没有 required checks，或 required check 缺失/失败/未知。
- ORM receipt 缺平台来源、执行定义、动态契约、事实范围、目标依赖或关联权限闭包。
- 浏览器页面只是 HTTP 200、元素出现或控制台无错，却没有对应 Renderer/交互/业务结果断言。
- CI 绿但目标变更集只经过路径规则；没有实际执行受影响的 L1/L2/L3 断言。
- 结构扫描、生成报告一致、类型检查或构建通过，被描述成页面或业务验收完成。

## 11. 长尾与不可执行面

guard registry 生命周期统计：

{chr(10).join(f"- `{name}`：{count}" for name, count in cost['script_lifecycle_counts'].items())}

- `manual_or_non_gate_dispatch`、`file_reference_only`、`orphan`、`unwired` 不是 merge gate。
- 零引用 target、零引用脚本和 missing-asset target 只能说明“当前没有自动执行路径”，不能说明
  验证已覆盖或产品已通过。
- 本轮没有删除、接线、豁免或退役任何长尾项；P4-00 只建立边界和基线。

## 12. Gate-enforced 脚本责任索引

下表只列四个 anchor 可达、实际被执行脚本中的一部分元数据。完整八问责任、调用 target、
资源信号、层提示和重叠关系在 `verification_mapping_matrix.json`。

| script | lifecycle | inferred layers | declared summary |
| --- | --- | --- | --- |
{gate_script_rows}

## 13. 执行图

`verification_execution_graph.json` 包含 workflow → job → step → make target → script →
resource/evidence 的有向边，并保留 Make prerequisite、recursive make、acceptance suite entrypoint
和证据权威节点。共 {len(graph['nodes'])} 个节点、{len(graph['edges'])} 条边。

## 14. 结论边界

现有体系不是缺少几个 guard，而是没有把“调度入口、执行体、行为责任、证据权威”四者统一到
同一变更影响模型。P4-00 的证据支持以下结论：

1. 路径分类可以用于路由候选检查，但不可作为产品影响或验证充分性的证明。
2. L1、L2、L3 必须分别绑定实际执行体和行为断言；L4 只做交付治理。
3. 未执行、未覆盖、未知依赖和环境失败都不得由历史 PASS、skip 或父 workflow 成功替代。
4. 当前契约消费者路径的 presentation 过度触发，与 Renderer 注册表的 presentation 欠触发
   同时存在，必须由符号/字段/依赖影响模型修复。
5. 长尾手工验证不能继续被叙述为自动门禁；先建立接线或明确“不适用”的证据责任，再谈复用。

本报告不声称当前验证体系已经完成重构，也不声称任何产品行为或交付已经通过。
"""


def write_outputs(inventory: dict[str, Any], graph: dict[str, Any], cost: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "verification_mapping_matrix.json": inventory,
        "verification_execution_graph.json": graph,
        "verification_cost_baseline.json": cost,
    }
    for name, payload in outputs.items():
        (output_dir / name).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    (output_dir / "verification_system_inventory.md").write_text(
        markdown_report(inventory, graph, cost),
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--json-summary", action="store_true")
    args = parser.parse_args(argv)

    inventory = build_inventory()
    graph = build_execution_graph(inventory)
    cost = build_cost_baseline(inventory)
    if args.write:
        write_outputs(inventory, graph, cost, args.output_dir)
    summary = {
        "status": "PASS",
        "source_head": inventory["source_head"],
        "workflow_jobs": len(inventory["workflow_jobs"]),
        "gate_make_targets": len(inventory["make_targets"]),
        "gate_scripts": len(inventory["gate_scripts"]),
        "script_lifecycle": len(inventory["script_lifecycle"]),
        "graph_nodes": len(graph["nodes"]),
        "graph_edges": len(graph["edges"]),
        "output_dir": str(args.output_dir) if args.write else None,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
