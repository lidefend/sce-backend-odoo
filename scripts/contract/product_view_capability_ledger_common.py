#!/usr/bin/env python3
"""Deterministic native capability classification primitives."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

import yaml

from scripts.contract.product_view_structure_common import sha256_json, structure_segment


@dataclass(frozen=True)
class NativeCandidate:
    kind: str
    view_type: str
    tag: str
    attribute: str
    locator: str
    native_locator: str
    occurrence_index: int
    resolved_view_ref: str
    ancestors: tuple[str, ...]
    canonical_value: Any
    source_selector: str = ""


def load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a YAML object")
    return value


def _pointer_escape(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


STATIC_FORM_MODIFIERS = {
    "modifier.readonly", "modifier.required", "modifier.invisible", "modifier.column_invisible",
}
STATIC_FORM_BEHAVIORS = {"form.create", "form.edit", "form.delete"}
READY_FORM_BEHAVIORS = {"form.create", "form.edit"}
FORM_BEHAVIOR_FIELDS = {
    "form.create": ("create", "can_create"),
    "form.edit": ("edit", "can_write"),
    "form.delete": ("delete", "can_delete"),
}


def static_boolean_value(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true"}:
            return True
        if normalized in {"0", "false"}:
            return False
    return None


def _walk_json(value: Any, pointer: str = "") -> Iterator[tuple[str, Any]]:
    yield pointer, value
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _walk_json(child, f"{pointer}/{_pointer_escape(str(key))}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk_json(child, f"{pointer}/{index}")


def match_normalized_atom(
    atom: dict[str, Any], mapping: dict[str, Any], carrier_entry: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return exact occurrence/value matches for implemented normalized mappings."""
    if mapping.get("mapping_status") != "proven":
        return []
    if mapping.get("matcher") == "surface_identity" and atom.get("capability_key") in STATIC_FORM_BEHAVIORS:
        raw_key, semantic_key = FORM_BEHAVIOR_FIELDS[atom["capability_key"]]
        for carrier in carrier_entry.get("normalized_carriers", []):
            if carrier.get("source_selector") not in mapping.get("source_selectors", []):
                continue
            try:
                capabilities = pointer_get(carrier.get("value"), "/capabilities")
            except (KeyError, ValueError):
                continue
            raw = capabilities.get("native_root_attributes") if isinstance(capabilities, dict) else None
            if not isinstance(raw, dict) or raw.get(raw_key) != atom.get("canonical_value"):
                continue
            if semantic_key not in capabilities:
                continue
            expected_semantic = static_boolean_value(atom.get("canonical_value"))
            if expected_semantic is None or capabilities[semantic_key] is not expected_semantic:
                continue
            base = str(carrier.get("artifact_selector") or "") + "/capabilities"
            return [{
                "raw_selector": f"{base}/native_root_attributes/{raw_key}",
                "raw_value": raw[raw_key],
                "semantic_selector": f"{base}/{semantic_key}",
                "semantic_value": capabilities[semantic_key],
            }]
        return []
    if mapping.get("matcher") != "recursive_native_occurrence":
        return []
    if atom.get("capability_key") not in STATIC_FORM_MODIFIERS or atom.get("view_type") != "form":
        return []
    attribute = str(atom.get("attribute") or "")
    matches: list[dict[str, Any]] = []
    for carrier in carrier_entry.get("normalized_carriers", []):
        if carrier.get("source_selector") not in mapping.get("source_selectors", []):
            continue
        value = carrier.get("value")
        for region in mapping.get("value_regions", []):
            try:
                region_value = pointer_get(value, str(region))
            except (KeyError, ValueError):
                continue
            for relative_pointer, row in _walk_json(region_value, str(region)):
                if not isinstance(row, dict):
                    continue
                if row.get("native_locator") != atom.get("native_locator"):
                    continue
                if row.get("occurrence_index") != atom.get("occurrence_index"):
                    continue
                attributes = row.get("attributes") if isinstance(row.get("attributes"), dict) else {}
                modifiers = row.get("modifiers") if isinstance(row.get("modifiers"), dict) else {}
                if attribute not in attributes or attributes[attribute] != atom.get("canonical_value"):
                    continue
                if attribute not in modifiers:
                    continue
                base = str(carrier.get("artifact_selector") or "") + relative_pointer
                matches.append({
                    "raw_selector": f"{base}/attributes/{_pointer_escape(attribute)}",
                    "raw_value": attributes[attribute],
                    "semantic_selector": f"{base}/modifiers/{_pointer_escape(attribute)}",
                    "semantic_value": modifiers[attribute],
                })
    return matches


def pointer_get(value: Any, pointer: str) -> Any:
    if pointer == "":
        return value
    if not pointer.startswith("/"):
        raise ValueError("RFC 6901 pointer must be empty or start with slash")
    current = value
    for raw in pointer[1:].split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict) and token in current:
            current = current[token]
        elif isinstance(current, list) and token.isdigit() and int(token) < len(current):
            current = current[int(token)]
        else:
            raise KeyError(pointer)
    return current


def iter_native_candidates(surface: dict[str, Any]) -> Iterator[NativeCandidate]:
    structure = surface.get("resolved_structure")
    if not isinstance(structure, dict):
        raise ValueError(f"{surface.get('contract_ref')}: resolved_structure is required")
    view_ref = str(surface.get("view_ref") or "")
    view_type = str(surface.get("view_type") or "")

    def emit(
        node: dict[str, Any], locator: str, native_locator: str, occurrence: int,
        ancestors: tuple[str, ...], pointer: str,
    ):
        tag = str(node.get("tag") or "")
        node_value = {"tag": tag}
        if "text" in node:
            node_value["text"] = node["text"]
        yield NativeCandidate("node", view_type, tag, "", locator, native_locator, occurrence, view_ref, ancestors, node_value, pointer)
        attrs = node.get("attrs") if isinstance(node.get("attrs"), dict) else {}
        for attribute, value in sorted(attrs.items()):
            yield NativeCandidate(
                "attribute", view_type, tag, str(attribute), f"{locator}/@{attribute}", native_locator,
                occurrence, view_ref, ancestors, value, f"{pointer}/attrs/{_pointer_escape(str(attribute))}",
            )
        children = [child for child in node.get("children") or [] if isinstance(child, dict)]
        totals: dict[str, int] = {}
        for child in children:
            base = structure_segment(child)
            totals[base] = totals.get(base, 0) + 1
        seen: dict[str, int] = {}
        tag_seen: dict[str, int] = {}
        for child_index, child in enumerate(children):
            base = structure_segment(child)
            seen[base] = seen.get(base, 0) + 1
            child_tag = str(child.get("tag") or "")
            tag_seen[child_tag] = tag_seen.get(child_tag, 0) + 1
            suffix = f"#{seen[base]}" if totals[base] > 1 else ""
            yield from emit(
                child, f"{locator}/{base}{suffix}", f"{native_locator}/{child_tag}[{tag_seen[child_tag]}]",
                seen[base], ancestors + (tag,), f"{pointer}/children/{child_index}",
            )

    root_locator = f"resolved:{view_ref}/{structure_segment(structure)}"
    root_tag = str(structure.get("tag") or "")
    yield from emit(structure, root_locator, f"/{root_tag}[1]", 1, (), "/resolved_structure")


def _tags(rule: dict[str, Any], taxonomy: dict[str, Any]) -> set[str] | None:
    value = rule.get("tags")
    if value == "*":
        return None
    if isinstance(value, str):
        tag_set = (taxonomy.get("tag_sets") or {}).get(value)
        if not isinstance(tag_set, list):
            raise ValueError(f"rule {rule.get('id')}: unknown tag set {value!r}")
        return {str(item) for item in tag_set}
    exact = rule.get("tags_exact")
    return {str(item) for item in exact} if isinstance(exact, list) else set()


def _matches(rule: dict[str, Any], candidate: NativeCandidate, taxonomy: dict[str, Any]) -> bool:
    tags = _tags(rule, taxonomy)
    if tags is not None and candidate.tag not in tags:
        return False
    view_types = rule.get("view_types")
    if isinstance(view_types, list) and candidate.view_type not in view_types:
        return False
    required = set(rule.get("ancestor_tags") or [])
    if required and not required.intersection(candidate.ancestors):
        return False
    absent = set(rule.get("absent_ancestor_tags") or [])
    if absent.intersection(candidate.ancestors):
        return False
    if candidate.kind == "attribute":
        exact = set(rule.get("attributes") or [])
        prefixes = tuple(rule.get("attribute_prefixes") or [])
        if candidate.attribute not in exact and not any(candidate.attribute.startswith(prefix) for prefix in prefixes):
            return False
    return True


def classify_candidate(candidate: NativeCandidate, taxonomy: dict[str, Any]) -> list[dict[str, str]]:
    rules = taxonomy.get("node_rules") if candidate.kind == "node" else taxonomy.get("attribute_rules")
    if not isinstance(rules, list):
        raise ValueError(f"taxonomy has no {candidate.kind} rules")
    matches = []
    for rule in rules:
        if not isinstance(rule, dict) or not _matches(rule, candidate, taxonomy):
            continue
        key = str(rule.get("capability_key") or rule.get("capability_key_template") or "")
        key = key.replace("{attribute}", candidate.attribute).replace("{view_type}", candidate.view_type).replace("{tag}", candidate.tag)
        matches.append({"rule_id": str(rule.get("id") or ""), "capability_key": key})
    return matches


def atom_identity(contract_ref: str, capability_key: str, candidate: NativeCandidate) -> str:
    return sha256_json({
        "contract_ref": contract_ref, "capability_key": capability_key,
        "resolved_view_ref": candidate.resolved_view_ref, "locator": candidate.locator,
        "occurrence_index": candidate.occurrence_index,
    })


def classify_structure(structure: dict[str, Any], taxonomy: dict[str, Any]) -> dict[str, Any]:
    atoms, unknown, ambiguous = [], [], []
    seen_ids: set[str] = set()
    entries = structure.get("entries") if isinstance(structure.get("entries"), list) else []
    for entry_index, entry in enumerate(entries):
        for surface_index, surface in enumerate(entry.get("surfaces") or []):
            contract_ref = str(surface.get("contract_ref") or "")
            for candidate in iter_native_candidates(surface):
                matches = classify_candidate(candidate, taxonomy)
                diagnostic = {"contract_ref": contract_ref, "locator": candidate.locator, "tag": candidate.tag, "attribute": candidate.attribute}
                if not matches:
                    unknown.append(diagnostic)
                    continue
                if len(matches) != 1:
                    ambiguous.append({**diagnostic, "rules": matches})
                    continue
                capability_key = matches[0]["capability_key"]
                atom_id = atom_identity(contract_ref, capability_key, candidate)
                if atom_id in seen_ids:
                    ambiguous.append({**diagnostic, "rules": matches, "error": "duplicate atom_id"})
                    continue
                seen_ids.add(atom_id)
                atoms.append({
                    "atom_id": atom_id, "contract_ref": contract_ref,
                    "capability_key": capability_key, "rule_id": matches[0]["rule_id"],
                    "view_type": candidate.view_type, "tag": candidate.tag,
                    "attribute": candidate.attribute, "locator": candidate.locator,
                    "native_locator": candidate.native_locator,
                    "occurrence_index": candidate.occurrence_index,
                    "resolved_view_ref": candidate.resolved_view_ref,
                    "canonical_value": candidate.canonical_value,
                    "value_hash": sha256_json(candidate.canonical_value),
                    "source_selector": f"/entries/{entry_index}/surfaces/{surface_index}{candidate.source_selector}",
                })
    return {"atoms": atoms, "unknown": unknown, "ambiguous": ambiguous}
