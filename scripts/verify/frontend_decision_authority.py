#!/usr/bin/env python3
"""Single authority for the frontend decision-authority ledger.

Why this module exists
----------------------
The product goal is: "a customised frontend derives everything except rendering
and interaction from the runtime contract."  That sentence only becomes
decidable when it is turned into a finite, reviewable check:

* every decision-shaped expression inside the frontend decision scopes
  (``pages`` / ``views`` / ``app``) is detected by a named rule;
* every detection is either declared render/interaction, registered in this
  ledger with an explicit classification and an evidence pointer, or a failure;
* ``contract-derived`` intent literals are verified against the *published*
  contract export (``docs/contract/exports/intent_catalog.json``) instead of a
  frozen string list, so the check stays structural rather than literal;
* ``contract-projectable-gap`` entries are the actionable backlog -- frontend
  decisions that have no contract carrier yet but can be projected by the
  backend.  They are the only legitimate remaining distance to the goal;
* ``frontend-logic-defect`` entries are frontend business logic that contradicts
  or bypasses the contract.

The ledger is regenerated from this module (single source of truth) and
committed as ``docs/frontend_productization/decision-authority-inventory-v1.json``
so a reviewer can read it in a diff.  ``frontend_decision_authority_guard.py``
fails closed when the live scan and the committed ledger disagree in either
direction, when an invariant rule is violated, or when a ``contract-derived``
claim is not backed by the published contract export.

This module is provenance/verification only.  It never edits product code.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

DECISION_SCOPES = (
    "frontend/apps/web/src/pages",
    "frontend/apps/web/src/views",
    "frontend/apps/web/src/app",
)
SOURCE_SUFFIXES = (".vue", ".ts", ".js")
EXCLUDED_PATH_PARTS = ("node_modules",)

INVENTORY_PATH = ROOT / "docs/frontend_productization/decision-authority-inventory-v1.json"
INTENT_CATALOG_PATH = ROOT / "docs/contract/exports/intent_catalog.json"

CLASSIFICATIONS = (
    "contract-derived",
    "contract-projectable-gap",
    "frontend-logic-defect",
    "excluded-render-interaction",
)
UNCLASSIFIED = "unclassified"

OWNER_LAYER_BY_CLASSIFICATION = {
    "contract-derived": "P0_frontend_renderer_consumer",
    "contract-projectable-gap": "P0_backend_contract_projector + P0_frontend_renderer_consumer",
    "frontend-logic-defect": "P0_frontend_renderer_owner + P0_backend_contract_projector",
    "excluded-render-interaction": "P0_frontend_renderer",
    UNCLASSIFIED: "unresolved",
}


@dataclass(frozen=True)
class Detector:
    key: str
    pattern: str
    mode: str
    rationale: str
    suggestion: str


RULES: tuple[Detector, ...] = (
    Detector(
        key="R1_capability_literal_gate",
        pattern=r"\bhasCapability\(\s*['\"]([^'\"]+)['\"]",
        mode="invariant_zero",
        rationale=(
            "A capability gate keyed by a frontend literal is frontend-owned "
            "authorisation logic; capability requirements must come from the "
            "declared contract source of the surface."
        ),
        suggestion=(
            "Read the required capabilities from the contract/provider "
            "declaration instead of naming a capability literal in the renderer."
        ),
    ),
    Detector(
        key="R2_intent_literal",
        pattern=r"\bintent\s*:\s*['\"]([^'\"]+)['\"]",
        mode="ledger",
        rationale=(
            "An intent identifier selects a backend behaviour.  Every intent "
            "literal must resolve to the published intent contract."
        ),
        suggestion=(
            "Use a published contract intent, or register the literal in this "
            "ledger as a projectable gap when no contract intent exists yet."
        ),
    ),
    Detector(
        key="R3_router_literal_destination",
        pattern=(
            r"\brouter\.(?:push|replace)\(\s*\{\s*(?:name|path)\s*:\s*['\"]([^'\"]*)['\"]"
            r"|\brouter\.(?:push|replace)\(\s*['\"]([^'\"]*)['\"]"
        ),
        mode="render_interaction_class",
        rationale=(
            "A navigation destination is part of the frontend shell; the router "
            "table and page shell are frontend-owned by definition."
        ),
        suggestion=(
            "No contract carrier is required.  Record the destination as a shell "
            "navigation decision rather than projecting it."
        ),
    ),
    Detector(
        key="R4_business_state_literal",
        pattern=r"\b(?:state|status)\s*===\s*['\"]([^'\"]+)['\"]",
        mode="ledger_or_declared_ui",
        rationale=(
            "A comparison against a state/status literal is a decision.  UI state "
            "machine values are declared render/interaction; any other value is a "
            "business decision that needs a contract authority."
        ),
        suggestion=(
            "Consume the business state from the contract projection, or register "
            "a projectable gap if the backend does not publish it yet."
        ),
    ),
    Detector(
        key="R5_action_id_literal",
        pattern=r"\baction_?[Ii]d\s*:\s*['\"]([^'\"]+)['\"]",
        mode="invariant_zero",
        rationale=(
            "A frontend-literal action/XML id selects backend metadata directly "
            "and bypasses the published action surface."
        ),
        suggestion="Read the action identity from the contract action surface.",
    ),
)

RULES_BY_KEY = {rule.key: rule for rule in RULES}
INVARIANT_RULES = frozenset(rule.key for rule in RULES if rule.mode == "invariant_zero")

# The render/interaction half of the sentence, declared once.  A state value in
# this set is a UI state-machine value (loading/idle/empty/...), i.e. the visible
# feedback of the renderer, not a business decision.  Adding a new value here is
# a conscious, reviewable act.
DECLARED_UI_STATE_LITERALS = frozenset(
    {
        "error",
        "loading",
        "idle",
        "pending",
        "empty",
        "ready",
        "saved",
        "saving",
        "editing",
        "ok",
        "success",
        "warning",
        "notice",
        "blocked",
        "failed",
        "denied",
        "forbidden",
        "not-found",
        "not_found",
        "preview",
        "pass",
    }
)

# Whole rules that are render/interaction by construction.
DECLARED_RENDER_INTERACTION_RULES = {
    "R3_router_literal_destination": "shell_navigation_destination",
}


def _derived(evidence: str) -> dict:
    return {"classification": "contract-derived", "evidence": evidence}


def _gap(evidence: str, gap: str) -> dict:
    return {
        "classification": "contract-projectable-gap",
        "evidence": evidence,
        "gap": gap,
    }


# R4 literals that look like business states but are pure UI/edit-session state.
_EXCLUDED = {
    "R4_business_state_literal|reverted": {
        "classification": "excluded-render-interaction",
        "reason": (
            "form-designer local operation-log status (client-side undo/pending "
            "ledger); it never leaves the browser and encodes no business rule."
        ),
        "evidence": "frontend/apps/web/src/pages/contractForm/types.ts:220",
    },
}

AUTHORITY: dict[str, dict] = {
    # --- R2: intent literals, verified against the published intent catalog ---
    "R2_intent_literal|api.data": _derived("docs/contract/exports/intent_catalog.json"),
    "R2_intent_literal|chatter.post": _derived("docs/contract/exports/intent_catalog.json"),
    "R2_intent_literal|release.operator.surface": _derived(
        "addons/smart_core/handlers/release_operator.py:82"
    ),
    "R2_intent_literal|search.favorite.delete": _derived(
        "addons/smart_core/handlers/search_favorite_set.py:174"
    ),
    "R2_intent_literal|system.init": _derived("docs/contract/exports/intent_catalog.json"),
    "R2_intent_literal|ui.contract": _derived("docs/contract/exports/intent_catalog.json"),
    "R2_intent_literal|ui.contract.v2": _derived("docs/contract/exports/intent_catalog.json"),
    "R2_intent_literal|projection.refresh": _gap(
        "frontend/apps/web/src/app/projectionRefreshRuntime.ts:42",
        (
            "`projection.refresh` is emitted as a local projection-refresh trace "
            "label but is not declared in the published intent catalog; either "
            "declare it in the contract/telemetry vocabulary or rename the trace "
            "key so it cannot be mistaken for a contract intent."
        ),
    ),
    # --- R4: business state literals with a backend authority ---
    "R4_business_state_literal|active": _derived(
        "addons/smart_core/models/auth_credential_policy.py:24"
    ),
    "R4_business_state_literal|allow": _derived(
        "addons/smart_core/utils/contract_governance_capabilities.py:120"
    ),
    "R4_business_state_literal|archived": _derived(
        "addons/smart_core/models/ui_base_contract_asset.py:46"
    ),
    "R4_business_state_literal|coming_soon": _derived(
        "addons/smart_core/utils/contract_governance_capabilities.py:133"
    ),
    "R4_business_state_literal|deny": _derived(
        "addons/smart_core/utils/contract_governance_capabilities.py:131"
    ),
    "R4_business_state_literal|disabled": _derived(
        "frontend/apps/web/src/stores/session.ts:406"
    ),
    "R4_business_state_literal|discarded": _derived(
        "addons/smart_core/model/ui_business_config_change_set.py:63"
    ),
    "R4_business_state_literal|draft": _derived(
        "addons/smart_core/models/release_management.py:24"
    ),
    "R4_business_state_literal|expired": _derived(
        "addons/smart_core/models/auth_credential_policy.py:24"
    ),
    "R4_business_state_literal|hidden": _derived(
        "addons/smart_core/handlers/menu_configuration.py:268"
    ),
    "R4_business_state_literal|LOCKED": _derived(
        "addons/smart_core/governance/scene_normalizer.py:385"
    ),
    "R4_business_state_literal|overdue": _derived(
        "addons/smart_core/handlers/chatter_activity_update.py:39"
    ),
    "R4_business_state_literal|published": _derived(
        "addons/smart_core/core/view_contract_presence.py:60"
    ),
    "R4_business_state_literal|READY": _derived(
        "addons/smart_core/governance/scene_normalizer.py:371"
    ),
    "R4_business_state_literal|released": _derived(
        "addons/smart_core/delivery/release_audit_trail_service.py:167"
    ),
    "R4_business_state_literal|superseded": _derived(
        "addons/smart_core/model/ui_business_config_change_set.py:64"
    ),
    "R4_business_state_literal|visible": _derived(
        "addons/smart_core/handlers/menu_configuration.py:249"
    ),
    # --- R4: frontend-owned vocabulary that should be projected ---
    "R4_business_state_literal|disabled_capability": _gap(
        "frontend/apps/web/src/app/capabilityPolicyCore.js:7",
        (
            "capability state vocabulary is computed in the renderer "
            "(`evaluateCapabilityPolicy`); the backend publishes reason codes "
            "(e.g. PERMISSION_DENIED, capability states allow/readonly/deny/"
            "pending/coming_soon) but not this renderer state name.  Project a "
            "capability state/reason from the contract and consume it here."
        ),
    ),
    "R4_business_state_literal|disabled_permission": _gap(
        "frontend/apps/web/src/app/capabilityPolicyCore.js:12",
        (
            "the renderer decides a permission denial from group membership; the "
            "backend already publishes PERMISSION_DENIED reason codes, so the "
            "decision should be projected instead of recomputed in the browser."
        ),
    ),
    "R4_business_state_literal|enabled": _gap(
        "frontend/apps/web/src/app/runtime/actionViewLoadGuardRuntime.ts:23",
        (
            "the load-guard consumes the renderer-computed capability policy state "
            "(`CapabilityPolicyState`); it should consume a projected capability "
            "state/reason from the contract instead."
        ),
    ),
    "R4_business_state_literal|unconfigured": _gap(
        "addons/smart_core/model/ui_menu_config_policy.py:446",
        (
            "the menu handling state `unconfigured` is derived in the renderer "
            "from the presence of a local policy id; the backend publishes "
            "unconfigured_hidden_count but not a per-menu state.  Project the "
            "per-menu handling state so the renderer only renders it."
        ),
    ),
    # --- R4: chatter activity status consumed from the contract ---
    (
        "R4_business_state_literal|pending|"
        "frontend/apps/web/src/pages/contractForm/professionalCollaborationModel.ts"
    ): _derived("addons/smart_core/handlers/chatter_activity_update.py:39"),
}
AUTHORITY.update(_EXCLUDED)


@dataclass(frozen=True)
class Finding:
    rule: str
    path: str
    line: int
    literal: str

    @property
    def key(self) -> str:
        return f"{self.rule}|{self.literal}"

    @property
    def path_key(self) -> str:
        return f"{self.rule}|{self.literal}|{self.path}"


def _strip_comment(line: str) -> str:
    stripped = line.strip()
    if stripped.startswith("*") or stripped.startswith("/*") or stripped.startswith("//"):
        return ""
    if "//" in line:
        line = line.split("//", 1)[0]
    return line


def _iter_sources(root: Path):
    for scope in DECISION_SCOPES:
        base = root / scope
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if path.suffix not in SOURCE_SUFFIXES:
                continue
            if any(part in EXCLUDED_PATH_PARTS for part in path.parts):
                continue
            yield path


def scan(read_text=None, root: Path = ROOT) -> list[Finding]:
    """Apply every detector to the declared scopes (line-level, comment-stripped)."""
    if read_text is None:

        def read_text(rel_path: str) -> str:
            return (root / rel_path).read_text(encoding="utf-8", errors="ignore")

    findings: list[Finding] = []
    for path in _iter_sources(root):
        rel = path.relative_to(root).as_posix()
        text = read_text(rel)
        for number, raw_line in enumerate(text.splitlines(), 1):
            line = _strip_comment(raw_line)
            if not line:
                continue
            for rule in RULES:
                for match in re.finditer(rule.pattern, line):
                    literal = next((g for g in match.groups() if g is not None), "")
                    if literal == "":
                        continue
                    findings.append(Finding(rule.key, rel, number, literal))
    return findings


def _classify(finding: Finding) -> dict:
    if finding.rule in INVARIANT_RULES:
        rule = RULES_BY_KEY[finding.rule]
        return {
            "classification": "frontend-logic-defect",
            "defect": f"invariant rule {finding.rule} must have zero occurrences",
            "remediation": rule.suggestion,
        }
    entry = AUTHORITY.get(finding.path_key) or AUTHORITY.get(finding.key)
    if entry is not None:
        return dict(entry)
    if finding.rule in DECLARED_RENDER_INTERACTION_RULES:
        return {
            "classification": "excluded-render-interaction",
            "reason": DECLARED_RENDER_INTERACTION_RULES[finding.rule],
            "declaredClass": "navigation_shell",
        }
    if (
        finding.rule == "R4_business_state_literal"
        and finding.literal in DECLARED_UI_STATE_LITERALS
    ):
        return {
            "classification": "excluded-render-interaction",
            "reason": "declared UI state-machine value",
            "declaredClass": "ui_state_machine",
        }
    return {
        "classification": UNCLASSIFIED,
        "remediation": (
            "register this decision in scripts/verify/frontend_decision_authority.py "
            "with a classification and an authority pointer, or make it "
            "render/interaction by declaring the class explicitly"
        ),
    }


def build_inventory(read_text=None, root: Path = ROOT) -> dict:
    findings = scan(read_text=read_text, root=root)
    grouped: dict[tuple[str, str, str], dict] = {}
    for finding in findings:
        key = (finding.rule, finding.path, finding.literal)
        row = grouped.setdefault(
            key,
            {
                "decisionKey": finding.path_key,
                "rule": finding.rule,
                "literal": finding.literal,
                "path": finding.path,
                "lines": [],
                "occurrences": 0,
            },
        )
        row["occurrences"] += 1
        if finding.line not in row["lines"]:
            row["lines"].append(finding.line)

    decisions = []
    for (_, _, _), row in sorted(grouped.items()):
        finding = Finding(row["rule"], row["path"], row["lines"][0], row["literal"])
        row["lines"] = sorted(row["lines"])
        row.update(_classify(finding))
        row["ownerLayer"] = OWNER_LAYER_BY_CLASSIFICATION[row["classification"]]
        decisions.append(row)

    by_classification: dict[str, int] = {}
    by_rule: dict[str, int] = {}
    for row in decisions:
        by_classification[row["classification"]] = (
            by_classification.get(row["classification"], 0) + row["occurrences"]
        )
        by_rule[row["rule"]] = by_rule.get(row["rule"], 0) + row["occurrences"]

    return {
        "schemaVersion": 1,
        "kind": "frontend_decision_authority_inventory",
        "goal": "customised frontend derives everything except rendering/interaction from the runtime contract",
        "decisionScopes": list(DECISION_SCOPES),
        "rules": [
            {
                "key": rule.key,
                "mode": rule.mode,
                "pattern": rule.pattern,
                "rationale": rule.rationale,
                "suggestion": rule.suggestion,
            }
            for rule in RULES
        ],
        "renderInteractionClasses": {
            "ui_state_machine": {
                "literals": sorted(DECLARED_UI_STATE_LITERALS),
                "scope": "R4_business_state_literal",
            },
            "navigation_shell": {
                "rules": sorted(DECLARED_RENDER_INTERACTION_RULES),
            },
        },
        "invariants": [
            {"rule": rule.key, "expectedOccurrences": 0, "suggestion": rule.suggestion}
            for rule in RULES
            if rule.key in INVARIANT_RULES
        ],
        "decisions": decisions,
        "summary": {
            "totalFindings": len(findings),
            "distinctDecisions": len(decisions),
            "byRule": dict(sorted(by_rule.items())),
            "byClassification": dict(sorted(by_classification.items())),
            "unclassified": by_classification.get(UNCLASSIFIED, 0),
            "contractDerived": by_classification.get("contract-derived", 0),
            "contractProjectableGaps": by_classification.get("contract-projectable-gap", 0),
            "frontendLogicDefects": by_classification.get("frontend-logic-defect", 0),
            "excludedRenderInteraction": by_classification.get(
                "excluded-render-interaction", 0
            ),
        },
    }


def load_intent_catalog(path: Path = INTENT_CATALOG_PATH) -> set[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    intents = data.get("intents", data)
    if isinstance(intents, dict):
        return set(intents.keys())
    out = set()
    for item in intents:
        if isinstance(item, str):
            out.add(item)
        elif isinstance(item, dict):
            value = item.get("intent") or item.get("name") or item.get("id")
            if value:
                out.add(value)
    return out


def reconcile(read_text=None, root: Path = ROOT, compare_committed: bool = False) -> dict:
    inventory = build_inventory(read_text=read_text, root=root)
    failures: list[str] = []

    for row in inventory["decisions"]:
        if row["classification"] == UNCLASSIFIED:
            failures.append(
                f"unregistered decision {row['decisionKey']} at "
                f"{row['path']}:{row['lines'][0]} -- frontend decision with no "
                "declared render/interaction class and no ledger entry"
            )
            continue
        if row["classification"] not in CLASSIFICATIONS:
            failures.append(
                f"{row['decisionKey']} has invalid classification "
                f"{row['classification']!r}"
            )
            continue
        if row["rule"] in INVARIANT_RULES:
            failures.append(
                f"invariant rule {row['rule']} matched {row['literal']!r} at "
                f"{row['path']}:{row['lines'][0]} -- expected zero occurrences"
            )
        evidence = row.get("evidence")
        if evidence:
            evidence_path = str(evidence).split(":", 1)[0]
            if not (root / evidence_path).exists():
                failures.append(
                    f"{row['decisionKey']} cites missing evidence file {evidence_path}"
                )

    catalog: set[str] | None = None
    for row in inventory["decisions"]:
        if (
            row["rule"] == "R2_intent_literal"
            and row["classification"] == "contract-derived"
        ):
            if catalog is None:
                catalog = load_intent_catalog(INTENT_CATALOG_PATH)
            if row["literal"] not in catalog:
                failures.append(
                    f"intent literal {row['literal']!r} at {row['path']} is "
                    "classified contract-derived but is not declared in the "
                    "published intent catalog"
                )

    if compare_committed:
        if not INVENTORY_PATH.exists():
            failures.append(
                "committed decision-authority ledger is missing; run "
                "`python3 scripts/verify/frontend_decision_authority.py --export`"
            )
        else:
            committed = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
            if committed != inventory:
                failures.append(
                    "committed decision-authority ledger is out of sync with the "
                    "live scan; re-export it and review the diff"
                )

    return {"inventory": inventory, "failures": failures}


def export(path: Path = INVENTORY_PATH) -> None:
    result = reconcile()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(result["inventory"], ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def main(argv=None) -> int:
    import sys

    argv = list(sys.argv[1:] if argv is None else argv)
    if "--export" in argv:
        export()
        print(f"[frontend.decision_authority] exported {INVENTORY_PATH}")
        return 0
    result = reconcile(compare_committed=True)
    summary = result["inventory"]["summary"]
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    for failure in result["failures"]:
        print(f"[FAIL] {failure}")
    return 1 if result["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
