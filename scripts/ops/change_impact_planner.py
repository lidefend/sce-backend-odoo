#!/usr/bin/env python3
"""Build a shadow verification plan from semantic change impact.

This planner is deliberately not wired into a required gate. It emits
RUN/REUSE/BLOCK decisions over explicit obligations and assertion coverage so
the design can be replayed against historical changes before cutover.
"""

from __future__ import annotations

import argparse
import ast
import difflib
import hashlib
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
TS_FACTS = ROOT / "scripts/ops/typescript_change_facts.mjs"
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
LAYER_ORDER = ("L1", "L2", "L3", "L4")
CHANGE_IMPACT_TOOL_PATHS = frozenset(
    {
        "scripts/ops/change_impact_planner.py",
        "scripts/ops/test_change_impact_planner.py",
        "scripts/ops/typescript_change_facts.mjs",
    }
)
DELIVERY_TOOL_PATHS = CHANGE_IMPACT_TOOL_PATHS | frozenset(
    {
        "scripts/verify/frontend_dev_incremental.py",
        "scripts/verify/test_frontend_dev_incremental.py",
    }
)


OBLIGATIONS: dict[str, dict[str, Any]] = {
    "L1.schema_contract": {
        "layer": "L1",
        "assertions": ["schema.identity", "schema.field_compatibility"],
    },
    "L1.decoder": {
        "layer": "L1",
        "assertions": ["decoder.accept_old", "decoder.accept_new", "decoder.reject_invalid"],
    },
    "L1.producer": {
        "layer": "L1",
        "assertions": ["producer.shape", "producer.identity"],
    },
    "L1.consumer": {
        "layer": "L1",
        "assertions": ["consumer.contract_identity", "consumer.compile"],
    },
    "L1.renderer_identity": {
        "layer": "L1",
        "assertions": ["renderer.contract_key", "renderer.registry_identity"],
    },
    "L1.action_view_identity": {
        "layer": "L1",
        "assertions": ["action.view.search.identity"],
    },
    "L1.relation_contract": {
        "layer": "L1",
        "assertions": ["relation.identity", "relation.normalized_value"],
    },
    "L2.renderer_selection": {
        "layer": "L2",
        "assertions": ["renderer.selected_for_contract"],
    },
    "L2.page_presentation": {
        "layer": "L2",
        "assertions": ["page.affected_surface_rendered", "page.no_contract_gap"],
    },
    "L2.layout_responsive": {
        "layer": "L2",
        "assertions": ["layout.target_viewport", "layout.no_overflow"],
    },
    "L2.page_interaction": {
        "layer": "L2",
        "assertions": ["interaction.real_page_behavior", "interaction.focus_and_feedback"],
    },
    "L3.orm_persistence": {
        "layer": "L3",
        "assertions": ["orm.persisted_result", "orm.failure_recovery"],
    },
    "L3.acl_positive": {
        "layer": "L3",
        "assertions": ["acl.allowed_principal_result"],
    },
    "L3.acl_negative": {
        "layer": "L3",
        "assertions": ["acl.denied_principal_result"],
    },
    "L3.business_outcome": {
        "layer": "L3",
        "assertions": ["business.valid_transition", "business.invalid_transition"],
    },
    "L4.delivery": {
        "layer": "L4",
        "assertions": ["delivery.tool_behavior", "delivery.workflow_contract"],
    },
    "L4.planner_self": {
        "layer": "L4",
        "assertions": [
            "planner.deterministic",
            "planner.unknown_policy",
            "planner.assertion_closure",
        ],
    },
    "L4.docs": {
        "layer": "L4",
        "assertions": ["docs.links_and_governance"],
    },
}


CHECKS: dict[str, dict[str, Any]] = {
    "contract.unified_v2": {
        "entrypoint": "make verify.unified_page_contract.v2",
        "kind": "make",
        "cost": 8,
        "evidence_kind": "contract-static",
        "covers": [
            "schema.identity",
            "schema.field_compatibility",
            "producer.shape",
            "producer.identity",
            "action.view.search.identity",
            "relation.identity",
            "relation.normalized_value",
        ],
    },
    "frontend.contract_unit": {
        "entrypoint": "make verify.frontend.pr.unit",
        "kind": "make",
        "cost": 5,
        "evidence_kind": "unit",
        "covers": [
            "schema.identity",
            "schema.field_compatibility",
            "decoder.accept_old",
            "decoder.accept_new",
            "decoder.reject_invalid",
            "consumer.contract_identity",
            "consumer.compile",
        ],
    },
    "frontend.renderer_registry_unit": {
        "entrypoint": "make verify.frontend.professional_component_registry.unit",
        "kind": "make",
        "cost": 3,
        "evidence_kind": "unit",
        "covers": [
            "renderer.contract_key",
            "renderer.registry_identity",
            "renderer.selected_for_contract",
        ],
    },
    "frontend.presentation_browser": {
        "entrypoint": "make verify.frontend.presentation.browser",
        "kind": "make-runtime",
        "cost": 13,
        "evidence_kind": "browser",
        "covers": [
            "page.affected_surface_rendered",
            "page.no_contract_gap",
            "layout.target_viewport",
            "layout.no_overflow",
            "interaction.real_page_behavior",
            "interaction.focus_and_feedback",
        ],
    },
    "backend.contract_suite": {
        "entrypoint": ".github/workflows/backend_test_suite.yml",
        "kind": "workflow-runtime",
        "cost": 13,
        "evidence_kind": "orm-and-contract",
        "covers": [
            "orm.persisted_result",
            "orm.failure_recovery",
            "acl.allowed_principal_result",
            "acl.denied_principal_result",
            "business.valid_transition",
            "business.invalid_transition",
        ],
    },
    "delivery.ci_workflow_contract": {
        "entrypoint": "make verify.ci.workflow.contract",
        "kind": "make",
        "cost": 4,
        "evidence_kind": "unit",
        "covers": ["delivery.tool_behavior", "delivery.workflow_contract"],
    },
    "delivery.change_impact_planner": {
        "entrypoint": "make verify.change_impact.plan.unit",
        "kind": "make",
        "cost": 2,
        "evidence_kind": "unit",
        "covers": [
            "planner.deterministic",
            "planner.unknown_policy",
            "planner.assertion_closure",
        ],
    },
    "delivery.docs_links": {
        "entrypoint": "ENV=dev make verify.docs.links",
        "kind": "make",
        "cost": 1,
        "evidence_kind": "docs",
        "covers": ["docs.links_and_governance"],
    },
}


SEMANTIC_OBLIGATIONS: dict[str, tuple[str, ...]] = {
    "decoder": ("L1.schema_contract", "L1.decoder", "L1.consumer"),
    "schema_field": ("L1.schema_contract", "L1.decoder", "L1.consumer"),
    "contract_producer": ("L1.schema_contract", "L1.producer", "L1.consumer"),
    "action_view_contract": ("L1.action_view_identity", "L1.consumer"),
    "renderer_registry": (
        "L1.renderer_identity",
        "L2.renderer_selection",
        "L2.page_presentation",
    ),
    "presentation_component": ("L2.page_presentation",),
    "layout_style": ("L2.layout_responsive",),
    "page_interaction": ("L1.action_view_identity", "L2.page_interaction"),
    "orm_field": ("L1.schema_contract", "L3.orm_persistence"),
    "orm_business": (
        "L1.schema_contract",
        "L3.orm_persistence",
        "L3.business_outcome",
    ),
    "acl": ("L1.action_view_identity", "L3.acl_positive", "L3.acl_negative"),
    "business_workflow": ("L1.relation_contract", "L3.business_outcome"),
    "migration": ("L3.orm_persistence", "L4.delivery"),
    "delivery_tool": ("L4.delivery",),
    "change_impact_tool": ("L4.planner_self",),
    "docs": ("L4.docs",),
}


@dataclass(frozen=True)
class Symbol:
    name: str
    kind: str
    start_line: int
    end_line: int

    @property
    def object(self) -> dict[str, Any]:
        return asdict(self)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _line_ranges(before: str, after: str) -> tuple[set[int], set[int]]:
    old_lines = before.splitlines()
    new_lines = after.splitlines()
    old_ranges: set[int] = set()
    new_ranges: set[int] = set()
    matcher = difflib.SequenceMatcher(a=old_lines, b=new_lines, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        old_ranges.update(range(i1 + 1, i2 + 1))
        new_ranges.update(range(j1 + 1, j2 + 1))
    return old_ranges, new_ranges


def _changed_symbols(symbols: list[Symbol], lines: set[int]) -> list[Symbol]:
    return [
        symbol
        for symbol in symbols
        if any(symbol.start_line <= line <= symbol.end_line for line in lines)
    ]


def python_facts(text: str) -> dict[str, Any]:
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return {"ok": False, "error": str(exc), "symbols": [], "classes": [], "imports": []}
    symbols: list[Symbol] = []
    classes: list[dict[str, Any]] = []
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                imports.add(alias.name)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            base_names = [
                ast.unparse(base)
                for base in getattr(node, "bases", [])
            ]
            symbol = Symbol(
                node.name,
                "class" if isinstance(node, ast.ClassDef) else "function",
                node.lineno,
                getattr(node, "end_lineno", node.lineno),
            )
            symbols.append(symbol)
            if isinstance(node, ast.ClassDef):
                fields = [
                    item.targets[0].id
                    for item in node.body
                    if isinstance(item, ast.Assign)
                    and len(item.targets) == 1
                    and isinstance(item.targets[0], ast.Name)
                    and isinstance(item.value, ast.Call)
                ]
                classes.append(
                    {
                        "name": node.name,
                        "bases": base_names,
                        "fields": sorted(set(fields)),
                        "methods": sorted(
                            item.name
                            for item in node.body
                            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                        ),
                    }
                )
    return {
        "ok": True,
        "symbols": [symbol.object for symbol in symbols],
        "classes": classes,
        "imports": sorted(imports),
    }


def xml_facts(text: str) -> dict[str, Any]:
    if not text.strip():
        return {"ok": True, "models": [], "fields": [], "tags": []}
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        return {"ok": False, "error": str(exc)}
    records = []
    fields = []
    tags = []
    for element in root.iter():
        tag = element.tag.rsplit("}", 1)[-1]
        tags.append(tag)
        if tag == "record":
            records.append(element.attrib.get("model", ""))
        if tag == "field":
            name = element.attrib.get("name")
            if name:
                fields.append(name)
    return {
        "ok": True,
        "models": sorted(set(filter(None, records))),
        "fields": sorted(set(fields)),
        "tags": sorted(set(tags)),
    }


def _coerce_symbols(values: Iterable[dict[str, Any]]) -> list[Symbol]:
    return [
        Symbol(
            str(value["name"]),
            str(value["kind"]),
            int(value["start_line"]),
            int(value["end_line"]),
        )
        for value in values
        if value.get("name")
    ]


def classify_document(
    *,
    path: str,
    before: str,
    after: str,
    ts_facts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    semantic_kinds: set[str] = set()
    unknown: list[str] = []
    basis: list[str] = []
    old_lines, new_lines = _line_ranges(before, after)
    suffix = Path(path).suffix.lower()
    normalized = path.replace("\\", "/")

    if normalized in CHANGE_IMPACT_TOOL_PATHS:
        semantic_kinds.add("change_impact_tool")
        basis.append("change_impact_tool_path")
    elif normalized in DELIVERY_TOOL_PATHS:
        semantic_kinds.add("delivery_tool")
        basis.append("bounded_delivery_tool_path")
    elif normalized.startswith(("docs/", ".agent/")) or suffix == ".md":
        semantic_kinds.add("docs")
        basis.append("documentation_path")
    elif normalized.startswith("scripts/verify/"):
        basename = Path(normalized).name
        if "unified_page_contract_v2" in basename or basename == "test_native_action_view_set.py":
            semantic_kinds.add("contract_producer")
            basis.append("contract_verification_resource")
        elif "browser" in basename or basename.startswith("frontend_"):
            semantic_kinds.add("presentation_component")
            if "interaction" in basename or "workflow" in basename:
                semantic_kinds.add("page_interaction")
            basis.append("frontend_verification_resource")
        else:
            semantic_kinds.add("delivery_tool")
            basis.append("verification_tool_resource")
    elif normalized.startswith("scripts/test/"):
        semantic_kinds.add("delivery_tool")
        basis.append("test_runner_resource")
    elif normalized.startswith((".github/workflows/", "make/", "scripts/ci/", "scripts/audit/")):
        semantic_kinds.add("delivery_tool")
        basis.append("delivery_tool_path")
    elif suffix in {".css", ".scss", ".less"}:
        semantic_kinds.add("layout_style")
        basis.append("stylesheet_extension")
    elif suffix in {".ts", ".tsx", ".vue", ".js", ".mjs", ".cjs"}:
        before_facts = (ts_facts or {}).get("before") or {}
        after_facts = (ts_facts or {}).get("after") or {}
        if ts_facts is None or not (
            ts_facts.get("ok")
            or (
                before_facts.get("ok", False)
                and after_facts.get("ok", False)
            )
        ):
            unknown.append("typescript_symbol_analysis_unavailable")
        before_symbols = _changed_symbols(
            _coerce_symbols(before_facts.get("symbols") or []), old_lines
        )
        after_symbols = _changed_symbols(
            _coerce_symbols(after_facts.get("symbols") or []), new_lines
        )
        changed_names = {symbol.name for symbol in [*before_symbols, *after_symbols]}
        fields_before = set(before_facts.get("fields") or [])
        fields_after = set(after_facts.get("fields") or [])
        changed_fields = fields_before ^ fields_after
        if before_facts.get("dynamic_dependency_possible") or after_facts.get(
            "dynamic_dependency_possible"
        ):
            unknown.append("dynamic_dependency_unresolved")
        if "/app/contracts/v2/" in normalized:
            if changed_names or changed_fields or fields_after:
                semantic_kinds.add("decoder")
                if changed_fields:
                    semantic_kinds.add("schema_field")
                basis.extend(["compiler_symbols", "contract_path", "compiler_fields"])
            else:
                unknown.append("contract_change_symbol_unresolved")
        elif normalized.endswith("professionalComponentRegistry.ts"):
            semantic_kinds.add("renderer_registry")
            basis.extend(["compiler_symbols", "renderer_registry_path"])
        elif "/app/presentation/" in normalized:
            semantic_kinds.add("presentation_component")
            basis.extend(["compiler_symbols", "presentation_path"])
        elif normalized.startswith(
            (
                "frontend/apps/web/src/pages/",
                "frontend/apps/web/src/views/",
                "frontend/apps/web/src/components/",
                "frontend/apps/web/src/layouts/",
            )
        ):
            semantic_kinds.add("presentation_component")
            if any(
                token in name.lower()
                for name in changed_names
                for token in ("interaction", "submit", "save", "action", "click")
            ):
                semantic_kinds.add("page_interaction")
            basis.extend(["compiler_symbols", "frontend_surface_path"])
        elif changed_names:
            semantic_kinds.add("presentation_component")
            basis.extend(["compiler_symbols", "frontend_runtime_symbols"])
        else:
            unknown.append("frontend_change_symbol_unresolved")
    elif normalized.startswith(("addons/", "demo_addons/", "customer_addons/")):
        if "/security/" in normalized or "ir.model.access" in normalized:
            semantic_kinds.add("acl")
            basis.append("security_declaration_path")
        elif "/migrations/" in normalized:
            semantic_kinds.add("migration")
            basis.append("migration_path")
        elif suffix == ".xml":
            parsed = xml_facts(after or before)
            models = parsed.get("models") or []
            if any("ir.rule" in model or "ir.model.access" in model for model in models):
                semantic_kinds.add("acl")
            elif any("act_window" in model or "menu" in model for model in models):
                semantic_kinds.add("action_view_contract")
            else:
                semantic_kinds.add("contract_producer")
            basis.append("xml_declaration_parse")
        elif suffix == ".py":
            py = python_facts(after or before)
            if not py.get("ok"):
                unknown.append("python_symbol_analysis_failed")
            classes = py.get("classes") or []
            model_classes = [
                row
                for row in classes
                if any("Model" in base for base in row.get("bases", []))
            ]
            if model_classes:
                semantic_kinds.add("orm_field")
                if any(
                    any(
                        token in method
                        for token in ("action_", "button_", "write", "create", "unlink", "transition")
                    )
                    for row in model_classes
                    for method in row.get("methods", [])
                ):
                    semantic_kinds.add("orm_business")
            else:
                semantic_kinds.add("contract_producer")
            basis.append("python_ast")
        else:
            unknown.append("backend_file_semantics_unresolved")
    else:
        unknown.append("unsupported_change_semantics")

    obligations = sorted(
        {
            obligation
            for kind in semantic_kinds
            for obligation in SEMANTIC_OBLIGATIONS.get(kind, ())
        },
        key=lambda value: (LAYER_ORDER.index(OBLIGATIONS[value]["layer"]), value),
    )
    confidence = "high" if semantic_kinds and not unknown else (
        "partial" if semantic_kinds else "unknown"
    )
    return {
        "path": normalized,
        "change_kind": "added" if not before else "deleted" if not after else "modified",
        "semantic_kinds": sorted(semantic_kinds),
        "obligation_ids": obligations,
        "layers": sorted(
            {OBLIGATIONS[item]["layer"] for item in obligations},
            key=LAYER_ORDER.index,
        ),
        "confidence": confidence,
        "basis": sorted(set(basis)),
        "unknown_reasons": sorted(set(unknown)),
        "changed_lines": {"old": len(old_lines), "new": len(new_lines)},
    }


def _obligation_records(ids: Iterable[str], sources: list[str]) -> list[dict[str, Any]]:
    rows = []
    for identifier in sorted(
        set(ids), key=lambda value: (LAYER_ORDER.index(OBLIGATIONS[value]["layer"]), value)
    ):
        spec = OBLIGATIONS[identifier]
        rows.append(
            {
                "id": identifier,
                "layer": spec["layer"],
                "required_assertions": spec["assertions"],
                "sources": sorted(sources),
            }
        )
    return rows


def _select_checks(obligations: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    required = {
        assertion
        for obligation in obligations
        for assertion in obligation["required_assertions"]
    }
    uncovered = set(required)
    selected: list[str] = []
    while uncovered:
        candidates = []
        for check_id, check in CHECKS.items():
            gain = uncovered & set(check["covers"])
            if gain:
                candidates.append(
                    (
                        -(len(gain) / max(1, int(check["cost"]))),
                        check_id,
                        gain,
                    )
                )
        if not candidates:
            break
        _, check_id, gain = min(candidates)
        selected.append(check_id)
        uncovered -= gain
    rows = [
        {
            "id": check_id,
            **CHECKS[check_id],
            "covered_assertions": sorted(set(CHECKS[check_id]["covers"]) & required),
        }
        for check_id in selected
    ]
    return rows, sorted(uncovered)


def _evidence_decisions(
    facts: list[dict[str, Any]],
    checks: list[dict[str, Any]],
    evidence: dict[str, Any],
) -> list[dict[str, Any]]:
    fact_digest = _sha(json.dumps(facts, ensure_ascii=False, sort_keys=True))
    rows = []
    for check in checks:
        fingerprint = _sha(
            json.dumps(
                {
                    "change_facts": fact_digest,
                    "check": check["id"],
                    "assertions": check["covered_assertions"],
                    "entrypoint": check["entrypoint"],
                },
                sort_keys=True,
            )
        )
        record = (evidence.get("checks") or {}).get(check["id"]) or {}
        reusable = (
            record.get("status") in {"passed", "checked", "reused"}
            and record.get("input_fingerprint") == fingerprint
            and record.get("assertion_closure") is True
        )
        rows.append(
            {
                "check_id": check["id"],
                "decision": "REUSE" if reusable else "RUN",
                "input_fingerprint": fingerprint,
                "source_fingerprint": record.get("input_fingerprint"),
                "assertion_closure": record.get("assertion_closure") is True,
                "reason": (
                    "matching authorized evidence"
                    if reusable
                    else "no matching current evidence"
                ),
            }
        )
    return rows


def analyze_change_set(
    items: list[dict[str, Any]],
    *,
    base: str,
    head: str,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    facts = [
        classify_document(
            path=item["path"],
            before=item.get("before", ""),
            after=item.get("after", ""),
            ts_facts=item.get("ts_facts"),
        )
        for item in items
    ]
    if not facts:
        return {
            "schema": "change_impact_plan.v1",
            "identity": {"base": base, "head": head},
            "mode": "shadow",
            "change_facts": [],
            "obligations": [],
            "checks": [],
            "decisions": [],
            "unknowns": [],
            "coverage": {
                "required_obligations": 0,
                "covered_obligations": 0,
                "required_assertions": 0,
                "covered_assertions": 0,
            },
            "status": "passed",
            "cutover_eligible": False,
        }
    sources = sorted({item["path"] for item in facts})
    sources_by_obligation: dict[str, set[str]] = {}
    for fact in facts:
        for obligation in fact["obligation_ids"]:
            sources_by_obligation.setdefault(obligation, set()).add(fact["path"])
    all_obligation_ids = sorted(
        sources_by_obligation,
        key=lambda value: (LAYER_ORDER.index(OBLIGATIONS[value]["layer"]), value),
    )
    obligations = []
    for obligation_id in all_obligation_ids:
        obl_spec = OBLIGATIONS[obligation_id]
        obligations.append(
            {
                "id": obligation_id,
                "layer": obl_spec["layer"],
                "required_assertions": obl_spec["assertions"],
                "sources": sorted(sources_by_obligation[obligation_id]),
            }
        )
    checks, uncovered_assertions = _select_checks(obligations)
    unknowns = sorted(
        {
            f"{fact['path']}: {reason}"
            for fact in facts
            for reason in fact["unknown_reasons"]
        }
    )
    decisions = _evidence_decisions(facts, checks, evidence or {})
    required_assertions = {
        assertion
        for obligation in obligations
        for assertion in obligation["required_assertions"]
    }
    covered_assertions = {
        assertion
        for check in checks
        for assertion in check["covered_assertions"]
    }
    blocked = bool(unknowns or uncovered_assertions)
    return {
        "schema": "change_impact_plan.v1",
        "identity": {"base": base, "head": head},
        "mode": "shadow",
        "change_facts": facts,
        "obligations": obligations,
        "checks": checks,
        "decisions": decisions,
        "unknowns": unknowns,
        "uncovered_assertions": uncovered_assertions,
        "coverage": {
            "required_obligations": len(obligations),
            "covered_obligations": len(obligations) if not uncovered_assertions else 0,
            "required_assertions": len(required_assertions),
            "covered_assertions": len(covered_assertions & required_assertions),
            "assertion_closure": not uncovered_assertions,
        },
        "status": "blocked" if blocked else "planned",
        "cutover_eligible": False,
        "boundaries": {
            "browser_only_for_L2_runtime_change": True,
            "backend_contract_default": "L1 with conditional L3",
            "unknown_policy": "BLOCK",
            "plan_is_not_execution_evidence": True,
        },
    }


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True)


def _revision_text(revision: str, path: str) -> str:
    result = subprocess.run(
        ["git", "show", f"{revision}:{path}"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.stdout if result.returncode == 0 else ""


def _typescript_facts(items: list[dict[str, Any]]) -> dict[str, Any]:
    ts_items = [
        item
        for item in items
        if Path(item["path"]).suffix in {".ts", ".tsx", ".vue", ".js", ".mjs", ".cjs"}
    ]
    if not ts_items:
        return {}
    process = subprocess.run(
        ["node", str(TS_FACTS)],
        cwd=ROOT,
        input=json.dumps(
            {
                "files": [
                    {key: item.get(key, "") for key in ("path", "before", "after")}
                    for item in ts_items
                ]
            }
        ),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if process.returncode:
        return {
            item["path"]: {
                "ok": False,
                "error": process.stderr.strip() or "typescript fact extraction failed",
            }
            for item in ts_items
        }
    return json.loads(process.stdout or "{}")


def plan_from_git(
    *,
    base: str,
    head: str,
    paths: list[str] | None = None,
    worktree: bool = False,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not FULL_SHA.fullmatch(base):
        raise ValueError("base must be a full lowercase SHA")
    if worktree:
        head = _git("rev-parse", "HEAD").strip()
        changed = _git("diff", "--no-renames", "--name-only", "-z", base, head).split("\0")
        changed += _git("diff", "--no-renames", "--name-only", "-z", head).split("\0")
        changed += _git("ls-files", "--others", "--exclude-standard", "-z").split("\0")
        selected_paths = sorted({path for path in changed if path})
        after_revision = None
    else:
        if not FULL_SHA.fullmatch(head):
            raise ValueError("head must be a full lowercase SHA")
        selected_paths = paths or sorted(
            path
            for path in _git(
                "diff", "--no-renames", "--name-only", base, head
            ).splitlines()
            if path
        )
        after_revision = head
    items = []
    for path in selected_paths:
        before = _revision_text(base, path)
        after = (
            (ROOT / path).read_text(encoding="utf-8", errors="replace")
            if after_revision is None and (ROOT / path).is_file()
            else _revision_text(after_revision, path)
        )
        items.append({"path": path, "before": before, "after": after})
    ts = _typescript_facts(items)
    for item in items:
        item["ts_facts"] = ts.get(item["path"])
    return analyze_change_set(items, base=base, head=head, evidence=evidence)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--worktree", action="store_true")
    parser.add_argument("--path", action="append", default=[])
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        base = _git("rev-parse", args.base).strip()
        head = _git("rev-parse", args.head).strip() if not args.worktree else _git("rev-parse", "HEAD").strip()
        evidence = (
            json.loads(args.evidence.read_text(encoding="utf-8"))
            if args.evidence
            else {}
        )
        plan = plan_from_git(
            base=base,
            head=head,
            paths=args.path or None,
            worktree=args.worktree,
            evidence=evidence,
        )
        text = json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text, encoding="utf-8")
        print(
            json.dumps(
                {
                    "status": plan["status"],
                    "mode": plan["mode"],
                    "base": plan["identity"]["base"],
                    "head": plan["identity"]["head"],
                    "change_facts": len(plan["change_facts"]),
                    "obligations": len(plan["obligations"]),
                    "checks": len(plan["checks"]),
                    "unknowns": len(plan["unknowns"]),
                    "cutover_eligible": plan["cutover_eligible"],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1 if plan["status"] == "blocked" else 0
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(json.dumps({"status": "error", "reason": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
