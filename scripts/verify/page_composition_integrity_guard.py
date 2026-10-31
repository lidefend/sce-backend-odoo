#!/usr/bin/env python3
"""Independent Page Composition Integrity Guard (shadow mode).

Aligned with ARCH-DECISION-004: business composition (slots + fieldGroups +
fieldOwnership) and layout topology (layoutContract.containerTree) are separate
authorities. The guard consumes verifiable Evidence Contract items and only
reports PASS when the evidence is both trusted (VERIFIED + scope-matched) and
sufficient for the rule.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

GUARD_VERSION = "1.1.0"
RULES = [
    "PC-001", "PC-002", "PC-003", "PC-004", "PC-005",
    "PC-006", "PC-007", "PC-008", "PC-009", "PC-010", "PC-011",
]

REMEDIATION_HINTS = {
    "PC-001": "declare business composition (slots) and layout topology (containerTree) in backend contract",
    "PC-002": "declare identity slot and bind identity fields via fieldOwnership.ownerSlotRef",
    "PC-003": "declare business section slots and bind fields to slot + group",
    "PC-004": "provide one valid primary ownership record per field; remove duplicate keys",
    "PC-005": "declare auxiliary projections through slot roles; fix fieldRefs types and ref prefixes",
    "PC-006": "keep classification within the four allowed page classes",
    "PC-007": "prove runtime fallback consumption; source existence is not runtime proof",
    "PC-008": "provide independent server permission tests covering authorized and unauthorized paths",
    "PC-009": "provide real old-consumer regression test evidence",
    "PC-010": "provide traceable before/after historical node identity mapping",
    "PC-011": "provide containerTree integrity and slots<->container mapping evidence",
}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _as_list(value: Any) -> list[dict]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _slot_ref(value: Any) -> str:
    text = _text(value)
    return text[len("slot:"):] if text.startswith("slot:") else text


def _group_ref(value: Any) -> str:
    text = _text(value)
    return text[len("group:"):] if text.startswith("group:") else text


def _slot_id(slot: dict) -> str:
    return _slot_ref(_text(slot.get("slot") or slot.get("id")))


def _slot_role(slot: dict) -> str:
    return _text(slot.get("role")).lower()


def _scope_matches(item: dict, page: dict) -> bool:
    for key in ("model", "action_id", "view_id"):
        item_value = _text(item.get(key))
        page_value = _text(page.get(key))
        if not item_value or not page_value or item_value != page_value:
            return False
    return True


def _trusted_items(value: Any, page: dict) -> list[dict]:
    trusted: list[dict] = []
    for item in value if isinstance(value, list) else []:
        if (
            isinstance(item, dict)
            and item.get("verification_status") == "VERIFIED"
            and _scope_matches(item, page)
        ):
            trusted.append(item)
    return trusted


def _sufficient_items(
    value: Any,
    page: dict,
    required_types: set[str] | None = None,
    required_coverage: set[str] | None = None,
) -> list[dict]:
    sufficient: list[dict] = []
    for item in _trusted_items(value, page):
        if required_types and item.get("evidence_type") not in required_types:
            continue
        coverage = item.get("coverage")
        coverage_set = set(coverage) if isinstance(coverage, list) else set()
        if required_coverage and not required_coverage.issubset(coverage_set):
            continue
        sufficient.append(item)
    return sufficient


def _container_tree(page: dict) -> Any:
    layout_contract = page.get("layoutContract") or {}
    if not isinstance(layout_contract, dict):
        return None
    return layout_contract.get("containerTree")


def _flatten_tree(tree: Any) -> list[dict]:
    nodes: list[dict] = []
    stack = list(tree) if isinstance(tree, list) else []
    while stack:
        node = stack.pop()
        if not isinstance(node, dict):
            continue
        nodes.append(node)
        children = node.get("children")
        if isinstance(children, list):
            stack.extend(children)
    return nodes


def _owner_slot(owner: dict) -> str:
    return _slot_ref(owner.get("ownerSlotRef"))


def _owner_group(owner: dict) -> str:
    return _group_ref(owner.get("ownerGroupRef"))


def _ownership_refs_valid(
    owner: dict, slot_ids: set[str], group_ids: set[str], require_group: bool = False
) -> bool:
    slot_ref = _owner_slot(owner)
    if not slot_ref or slot_ref not in slot_ids:
        return False
    group_ref = _owner_group(owner)
    if require_group and not group_ref:
        return False
    if group_ref and group_ref not in group_ids:
        return False
    return True


def _rule(rule_id: str, status: str, reason: str, evidence: str, **scope: Any) -> dict:
    return {
        "rule_id": rule_id,
        "status": status,
        "reason": reason,
        "evidence": evidence,
        "scope": scope,
        "remediation_hint": REMEDIATION_HINTS.get(rule_id, ""),
    }


def _load_json_detect_duplicates(text: str) -> tuple[Any, list[dict]]:
    duplicates: list[dict] = []

    def hook(pairs):
        out: dict = {}
        for key, value in pairs:
            if key in out:
                duplicates.append({"key": key, "first_value": out[key], "second_value": value})
            else:
                out[key] = value
        return out

    obj = json.loads(text, object_pairs_hook=hook)
    return obj, duplicates


def evaluate(payload: dict[str, Any], parse_diagnostics: dict[str, Any] | None = None) -> dict[str, Any]:
    page = payload.get("page") or {}
    evidence = payload.get("evidence") or {}
    composition = page.get("pageComposition") or {}
    form_structure = page.get("formStructureContract") or {}
    slots = _as_list(form_structure.get("slots"))
    field_groups = page.get("fieldGroups") or {}
    groups = _as_list(field_groups.get("groups")) if isinstance(field_groups, dict) else []
    ownership = page.get("fieldOwnership") or {}
    if not isinstance(ownership, dict):
        ownership = {}
    page_class = _text(composition.get("class"))
    container_tree = _container_tree(page)

    slot_ids = {_slot_id(slot) for slot in slots if _slot_id(slot)}
    group_ids = {_group_ref(_text(group.get("group") or group.get("id"))) for group in groups}
    for slot in slots:
        for group in _as_list(slot.get("groups")):
            group_identity = _text(group.get("name") or group.get("id") or group.get("group"))
            if group_identity:
                group_ids.add(_group_ref(group_identity))
    group_ids = {g for g in group_ids if g}

    results: list[dict] = []

    # PC-001 structure authority (two layers)
    business_authority = bool(slots)
    layout_authority = container_tree is not None
    if business_authority and layout_authority:
        results.append(_rule("PC-001", "PASS", "business composition and layout topology declared", "slots+containerTree"))
    elif not business_authority:
        results.append(_rule("PC-001", "NOT_VERIFIED", "business composition authority (slots) not declared; containerTree cannot substitute", "formStructureContract.slots"))
    else:
        results.append(_rule("PC-001", "NOT_VERIFIED", "layout topology authority (containerTree) not evidenced", "layoutContract.containerTree"))

    # PC-002 identity
    identity_slots = [slot for slot in slots if _slot_id(slot) == "identity"]
    identity_owned = [
        field for field, owner in ownership.items()
        if _owner_slot(owner) == "identity" or _owner_group(owner) == "identity"
    ]
    if identity_owned:
        invalid = [
            field for field in identity_owned
            if not _ownership_refs_valid(ownership[field], slot_ids, group_ids, require_group=False)
        ]
        if invalid:
            results.append(_rule("PC-002", "FAIL", "identity field ownership references invalid", "group:identity", fields=invalid))
        else:
            results.append(_rule("PC-002", "PASS", "identity fields bound to identity group", "group:identity"))
    else:
        results.append(_rule("PC-002", "NOT_VERIFIED", "identity group not evidenced", "group:identity"))

    # PC-003 business section
    business_slots = [slot for slot in slots if _slot_id(slot) != "identity"]
    business_owned = [
        field for field, owner in ownership.items()
        if _owner_slot(owner) != "identity" and _owner_group(owner) != "identity"
    ]
    if not business_slots:
        results.append(_rule("PC-003", "NOT_VERIFIED", "no business section slots declared", "slots+groups"))
    elif not group_ids:
        results.append(_rule("PC-003", "NOT_VERIFIED", "field groups not declared", "slots+groups"))
    elif not business_owned:
        results.append(_rule("PC-003", "NOT_VERIFIED", "no business field ownership bound", "slots+groups"))
    else:
        invalid = [
            field for field in business_owned
            if not _ownership_refs_valid(ownership[field], slot_ids, group_ids, require_group=True)
        ]
        if invalid:
            results.append(_rule("PC-003", "FAIL", "business field slot/group references invalid", "slots+groups", fields=invalid))
        else:
            results.append(_rule("PC-003", "PASS", "business fields bound to slot and group", "slots+groups"))

    # PC-004 ownership uniqueness and validity
    duplicate_keys = (parse_diagnostics or {}).get("duplicate_keys") or []
    field_duplicates = [d for d in duplicate_keys if _text(d.get("key")).startswith("field:")]
    if field_duplicates:
        results.append(_rule("PC-004", "FAIL", "duplicate field ownership keys in raw input", "fieldOwnership", duplicates=[d["key"] for d in field_duplicates]))
    elif ownership and not slot_ids:
        results.append(_rule("PC-004", "NOT_VERIFIED", "ownership declared but no slot evidence to validate refs", "fieldOwnership"))
    elif ownership:
        invalid = [
            field for field, owner in ownership.items()
            if not _ownership_refs_valid(owner, slot_ids, group_ids, require_group=False)
        ]
        if invalid:
            results.append(_rule("PC-004", "FAIL", "ownership references invalid", "fieldOwnership", fields=invalid))
        else:
            results.append(_rule("PC-004", "PASS", "unique and valid primary ownership", "fieldOwnership"))
    else:
        results.append(_rule("PC-004", "NOT_VERIFIED", "ownership not declared", "fieldOwnership"))

    # PC-005 duplicate projection
    projection_errors: list[str] = []
    projection_unverified: list[str] = []
    allowed_aux_roles = {_text(role).lower() for role in (evidence.get("allowed_slot_roles") or []) if _text(role)}
    schema_roles_provided = bool(allowed_aux_roles)
    slot_fields: dict[str, set[str]] = {}
    for slot in slots:
        slot_id = _slot_id(slot)
        refs: list[str] = []
        field_refs = slot.get("fieldRefs")
        if field_refs is None:
            pass
        elif isinstance(field_refs, list):
            for raw_ref in field_refs:
                ref = _text(raw_ref)
                if ref:
                    refs.append(ref)
        else:
            projection_errors.append(f"slot {slot_id} fieldRefs is not a list ({type(field_refs).__name__})")

        groups_raw = slot.get("groups")
        if groups_raw is None:
            pass
        elif isinstance(groups_raw, list):
            for group in groups_raw:
                if not isinstance(group, dict):
                    continue
                group_field_refs = group.get("fieldRefs")
                if group_field_refs is None:
                    continue
                if isinstance(group_field_refs, list):
                    for raw_ref in group_field_refs:
                        ref = _text(raw_ref)
                        if ref:
                            refs.append(ref)
                else:
                    projection_errors.append(f"slot {slot_id} group fieldRefs is not a list ({type(group_field_refs).__name__})")
        else:
            projection_errors.append(f"slot {slot_id} groups is not a list ({type(groups_raw).__name__})")

        slot_fields[slot_id] = set(refs)

    field_slot_map: dict[str, set[str]] = {}
    for slot_id, refs in slot_fields.items():
        for ref in refs:
            field_slot_map.setdefault(ref, set()).add(slot_id)

    for field_ref, multi_slot_ids in field_slot_map.items():
        if len(multi_slot_ids) <= 1:
            continue
        ownership_key = field_ref if field_ref.startswith("field:") else "field:%s" % field_ref
        owner = ownership.get(ownership_key)
        if not owner:
            projection_unverified.append(f"{field_ref} no ownership")
            continue
        primary_slot = _owner_slot(owner)
        other_slots = multi_slot_ids - {primary_slot}
        if not other_slots:
            continue
        other_roles = {_slot_role(slot) for slot in slots if _slot_id(slot) in other_slots}
        if not schema_roles_provided:
            projection_unverified.append(f"{field_ref} slot role schema not provided")
            continue
        if other_roles - allowed_aux_roles:
            projection_errors.append(f"{field_ref} ambiguous auxiliary slots {sorted(other_slots)}")
        else:
            projection_unverified.append(f"{field_ref} auxiliary role semantics not proven")

    if projection_errors:
        results.append(_rule("PC-005", "FAIL", "ambiguous duplicate projection or malformed fieldRefs", "slots.fieldRefs", errors=projection_errors))
    elif projection_unverified:
        results.append(_rule("PC-005", "NOT_VERIFIED", "projection semantics incomplete", "slots.fieldRefs", fields=projection_unverified))
    elif slot_fields:
        results.append(_rule("PC-005", "PASS", "projection ownership consistent", "slots.fieldRefs"))
    else:
        results.append(_rule("PC-005", "NOT_VERIFIED", "slot fieldRefs not available", "slots.fieldRefs"))

    # PC-006 legacy classification
    allowed_classes = {"formal", "legacy_compatible", "unclassified_historical", "incomplete"}
    if page_class in allowed_classes:
        results.append(_rule("PC-006", "PASS", f"class={page_class}", "pageComposition.class"))
    else:
        results.append(_rule("PC-006", "FAIL", f"invalid class={page_class!r}", "pageComposition.class"))

    # PC-007 legacy fallback (runtime consumption only)
    fallback_verified = _trusted_items(evidence.get("legacy_fallback_sources"), page)
    runtime_fallback = [item for item in fallback_verified if item.get("evidence_grade") == "RUNTIME_VERIFIED"]
    if page_class == "formal" and runtime_fallback:
        results.append(_rule("PC-007", "FAIL", "formal page consumes legacy fallback at runtime", "legacy_fallback_sources", sources=runtime_fallback))
    elif runtime_fallback:
        results.append(_rule("PC-007", "WARNING", "verified runtime legacy fallback present", "legacy_fallback_sources"))
    elif fallback_verified:
        results.append(_rule("PC-007", "NOT_VERIFIED", "fallback evidence is source/static; runtime consumption unproven", "legacy_fallback_sources"))
    else:
        results.append(_rule("PC-007", "NOT_VERIFIED", "verified fallback evidence missing", "legacy_fallback_sources"))

    # PC-008 permissions (sufficient evidence only)
    permission_sufficient = _sufficient_items(
        evidence.get("permission_evidence"),
        page,
        required_types={"TEST_EXECUTION", "RUNTIME_OBSERVATION"},
        required_coverage={"server_permission_mechanism", "authorized_access", "unauthorized_denied"},
    )
    permission_verified = _trusted_items(evidence.get("permission_evidence"), page)
    if permission_sufficient:
        results.append(_rule("PC-008", "PASS", "server permission boundary verified", "permission_evidence"))
    elif permission_verified:
        results.append(_rule("PC-008", "NOT_VERIFIED", "verified permission evidence exists but does not prove server boundary", "permission_evidence"))
    else:
        results.append(_rule("PC-008", "NOT_VERIFIED", "verified permission evidence missing; declaration alone is not proof", "permission_evidence"))

    # PC-009 version compatibility
    version_sufficient = _sufficient_items(
        evidence.get("version_compatibility_evidence"),
        page,
        required_types={"TEST_EXECUTION"},
        required_coverage={"old_consumer_regression"},
    )
    if version_sufficient:
        results.append(_rule("PC-009", "PASS", "old-consumer regression verified", "version_compatibility_evidence"))
    else:
        results.append(_rule("PC-009", "NOT_VERIFIED", "old-consumer regression evidence missing", "version_compatibility_evidence"))

    # PC-010 historical node identity
    history_sufficient = _sufficient_items(
        evidence.get("historical_node_identity_evidence"),
        page,
        required_types={"HISTORICAL_REFERENCE"},
        required_coverage={"before_after_mapping"},
    )
    if history_sufficient:
        results.append(_rule("PC-010", "PASS", "historical node identity mapping verified", "historical_node_identity_evidence"))
    else:
        results.append(_rule("PC-010", "NOT_VERIFIED", "historical node identity mapping evidence missing", "historical_node_identity_evidence"))

    # PC-011 layout integrity
    tree_nodes = _flatten_tree(container_tree)
    if container_tree is None:
        results.append(_rule("PC-011", "NOT_VERIFIED", "containerTree not evidenced", "layoutContract.containerTree"))
    elif not tree_nodes:
        results.append(_rule("PC-011", "NOT_VERIFIED", "containerTree empty", "layoutContract.containerTree"))
    else:
        node_ids = {_text(node.get("id")) for node in tree_nodes if _text(node.get("id"))}
        dangling: list[str] = []
        for node in tree_nodes:
            children = node.get("children")
            if isinstance(children, list):
                for child in children:
                    if isinstance(child, str) and child not in node_ids:
                        dangling.append(child)
            parent = node.get("parentId")
            if parent and _text(parent) not in node_ids:
                dangling.append(_text(parent))

        ownership_conflicts: list[str] = []
        for node in tree_nodes:
            region = _slot_ref(node.get("businessRegionRef"))
            node_refs = node.get("fieldRefs")
            refs = [ref for ref in node_refs if isinstance(ref, str)] if isinstance(node_refs, list) else []
            for ref in refs:
                owner = ownership.get(ref)
                if owner and region and _owner_slot(owner) != region:
                    ownership_conflicts.append(f"{ref} container region {region} conflicts with ownership {_owner_slot(owner)}")

        mapping = evidence.get("slot_container_mapping")
        mapping_items = [m for m in mapping if isinstance(m, dict)] if isinstance(mapping, list) else []
        if dangling:
            results.append(_rule("PC-011", "FAIL", "containerTree dangling references", "layoutContract.containerTree", refs=dangling))
        elif ownership_conflicts:
            results.append(_rule("PC-011", "FAIL", "containerTree assigns business ownership conflicting with fieldOwnership", "layoutContract.containerTree", conflicts=ownership_conflicts))
        elif not mapping_items:
            results.append(_rule("PC-011", "NOT_VERIFIED", "slots<->container mapping not evidenced", "slot_container_mapping"))
        else:
            invalid_mapping = [
                m for m in mapping_items
                if _slot_ref(m.get("slot_ref")) not in slot_ids or _text(m.get("container_id")) not in node_ids
            ]
            if invalid_mapping:
                results.append(_rule("PC-011", "FAIL", "slots<->container mapping references invalid", "slot_container_mapping", invalid=invalid_mapping))
            else:
                results.append(_rule("PC-011", "PASS", "containerTree layout integrity and mapping consistent", "layoutContract.containerTree"))

    statuses = [r["status"] for r in results]
    if "FAIL" in statuses:
        overall = "FAIL"
    elif "NOT_VERIFIED" in statuses:
        overall = "NOT_VERIFIED"
    elif "WARNING" in statuses:
        overall = "WARNING"
    else:
        overall = "PASS"

    summary = {r["rule_id"]: r["status"] for r in results}

    trust_keys = (
        "legacy_fallback_sources",
        "permission_evidence",
        "version_compatibility_evidence",
        "historical_node_identity_evidence",
    )
    evidence_trust: dict[str, dict[str, int]] = {}
    for key in trust_keys:
        value = evidence.get(key)
        total = len(value) if isinstance(value, list) else 0
        trusted = len(_trusted_items(value, page))
        evidence_trust[key] = {"trusted": trusted, "total": total, "untrusted": total - trusted}

    evidence_summary: dict[str, dict[str, int]] = {}
    for key in trust_keys:
        value = evidence.get(key)
        total = len(value) if isinstance(value, list) else 0
        trusted = len(_trusted_items(value, page))
        sufficient = 0
        if key == "legacy_fallback_sources":
            sufficient = len([i for i in _trusted_items(value, page) if i.get("evidence_grade") == "RUNTIME_VERIFIED"])
        elif key == "permission_evidence":
            sufficient = len(_sufficient_items(value, page, {"TEST_EXECUTION", "RUNTIME_OBSERVATION"}, {"server_permission_mechanism", "authorized_access", "unauthorized_denied"}))
        elif key == "version_compatibility_evidence":
            sufficient = len(_sufficient_items(value, page, {"TEST_EXECUTION"}, {"old_consumer_regression"}))
        elif key == "historical_node_identity_evidence":
            sufficient = len(_sufficient_items(value, page, {"HISTORICAL_REFERENCE"}, {"before_after_mapping"}))
        evidence_summary[key] = {
            "total": total,
            "trusted": trusted,
            "sufficient": sufficient,
            "verified_insufficient": trusted - sufficient,
            "untrusted": total - trusted,
        }

    return {
        "guard_version": GUARD_VERSION,
        "contract_version": payload.get("contract_version"),
        "execution_timestamp": datetime.now(timezone.utc).isoformat(),
        "repository_sha": payload.get("repository_sha"),
        "overall_status": overall,
        "page_classification": page_class,
        "page_classification_summary": {page_class: 1} if page_class else {},
        "rule_results": results,
        "summary": summary,
        "evidence_trust": evidence_trust,
        "evidence_summary": evidence_summary,
        "parse_diagnostics": parse_diagnostics or {},
    }


def _render_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"# Page Composition Integrity Guard {report['guard_version']}")
    lines.append("")
    lines.append(f"- overall: {report['overall_status']}")
    lines.append(f"- executed_at: {report['execution_timestamp']}")
    lines.append(f"- repository_sha: {report.get('repository_sha') or ''}")
    lines.append(f"- page_classification: {report['page_classification']}")
    lines.append("")

    counts = Counter(r["status"] for r in report["rule_results"])
    lines.append("## Status counts")
    lines.append("")
    lines.append("| status | count |")
    lines.append("| --- | --- |")
    for status in ("PASS", "FAIL", "WARNING", "NOT_VERIFIED", "NOT_APPLICABLE"):
        lines.append(f"| {status} | {counts.get(status, 0)} |")
    lines.append("")

    not_verified = [r for r in report["rule_results"] if r["status"] == "NOT_VERIFIED"]
    if not_verified:
        lines.append("## NOT_VERIFIED")
        lines.append("")
        for result in not_verified:
            lines.append(f"- {result['rule_id']}: {result['reason']}")
        lines.append("")

    failed = [r for r in report["rule_results"] if r["status"] == "FAIL"]
    if failed:
        lines.append("## FAIL")
        lines.append("")
        for result in failed:
            lines.append(f"- {result['rule_id']}: {result['reason']}")
        lines.append("")

    lines.append("## Rules")
    lines.append("")
    lines.append("| rule | status | evidence |")
    lines.append("| --- | --- | --- |")
    for result in report["rule_results"]:
        lines.append(f"| {result['rule_id']} | {result['status']} | {result['evidence']} |")
    lines.append("")

    lines.append("## Evidence trust")
    lines.append("")
    lines.append("| key | trusted | untrusted | total |")
    lines.append("| --- | --- | --- | --- |")
    for key, counts_trust in report["evidence_trust"].items():
        lines.append(f"| {key} | {counts_trust['trusted']} | {counts_trust['untrusted']} | {counts_trust['total']} |")
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-json", default="-")
    parser.add_argument("--output-markdown", default="-")
    args = parser.parse_args()
    payload, duplicates = _load_json_detect_duplicates(Path(args.input).read_text(encoding="utf-8"))
    report = evaluate(payload, parse_diagnostics={"duplicate_keys": duplicates})
    json_text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output_json == "-":
        print(json_text)
    else:
        Path(args.output_json).write_text(json_text + "\n", encoding="utf-8")
    markdown = _render_markdown(report)
    if args.output_markdown == "-":
        print(markdown)
    else:
        Path(args.output_markdown).write_text(markdown, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
