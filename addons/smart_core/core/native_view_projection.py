# -*- coding: utf-8 -*-
"""Canonical Native View Projection (BNVA-004..007).

This module is the single, thin projection of an Odoo native view arch into an
internal structure.  It is NOT a parallel public schema: downstream contract
assembly consumes this structure instead of re-parsing the arch string.

Rules enforced here:
- the merged arch is parsed exactly once per projection call;
- container identity is the native ``<group name>`` (or a stable structural
  path for unnamed containers, never a per-call array index);
- the same field appearing multiple times keeps one occurrence per appearance;
- modifiers are projected raw (record/context expressions are NOT evaluated
  here; static literals may be noted by callers).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from lxml import etree

_STRUCTURAL_TAGS = frozenset({"form", "sheet", "group", "notebook", "page", "div"})


@dataclass
class NativeFieldOccurrence:
    field_code: str
    occurrence_index: int
    container_ref: str
    native_locator: str
    modifiers_raw: dict[str, str] = field(default_factory=dict)
    field_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class NativeContainer:
    container_ref: str
    native_name: str
    native_type: str
    parent_ref: str | None = None
    native_locator: str = ""
    children: list["NativeContainer"] = field(default_factory=list)


@dataclass
class NativeView:
    model: str
    action_id: int
    view_id: int
    view_type: str
    containers: list[NativeContainer] = field(default_factory=list)
    fields: list[NativeFieldOccurrence] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        def container_to_dict(node: NativeContainer) -> dict[str, Any]:
            return {
                "container_ref": node.container_ref,
                "native_name": node.native_name,
                "native_type": node.native_type,
                "parent_ref": node.parent_ref,
                "native_locator": node.native_locator,
                "children": [container_to_dict(child) for child in node.children],
            }

        return {
            "identity": {
                "model": self.model,
                "action_id": self.action_id,
                "view_id": self.view_id,
                "view_type": self.view_type,
            },
            "containers": [container_to_dict(item) for item in self.containers],
            "fields": [
                {
                    "field_code": item.field_code,
                    "occurrence_index": item.occurrence_index,
                    "container_ref": item.container_ref,
                    "native_locator": item.native_locator,
                    "modifiers_raw": item.modifiers_raw,
                    "field_metadata": item.field_metadata,
                }
                for item in self.fields
            ],
            "provenance": self.provenance,
        }


def _structural_identity(tag: str, name: str, parent_ref: str | None, position: int) -> str:
    if name:
        return name
    if parent_ref:
        return f"{parent_ref}/{tag}[{position}]"
    return tag


def _native_locator(parent_locator: str, tag: str, position: int) -> str:
    return f"{parent_locator}/{tag}[{position}]"


def project_native_view(
    env: Any,
    model_name: str,
    *,
    action_id: int = 0,
    view_id: int = 0,
    view_type: str = "form",
) -> NativeView:
    """Parse one merged Odoo view arch exactly once into a Canonical AST."""
    model = env[model_name]
    view_data = model.get_view(view_id=view_id or False, view_type=view_type)
    arch = str((view_data or {}).get("arch") or "")
    if not arch:
        raise ValueError(f"native view projection requires a resolved arch for {model_name}")
    root = etree.fromstring(arch.encode("utf-8"))

    field_meta = model.fields_get()

    result = NativeView(
        model=model_name,
        action_id=int(action_id or 0),
        view_id=int((view_data or {}).get("id") or view_id or 0),
        view_type=view_type,
        provenance={
            "source_view_id": int((view_data or {}).get("id") or view_id or 0),
            "runtime_context": {
                key: str(value)
                for key, value in (dict(env.context or {}) or {}).items()
                if key in {"lang", "tz", "allowed_company_ids", "contract_action_id"}
            },
        },
    )

    occurrence_counter: dict[str, int] = {}
    position_counter: dict[tuple[str, str], int] = {}

    def position_of(parent_locator: str, tag: str) -> int:
        key = (parent_locator, tag)
        position_counter[key] = position_counter.get(key, 0) + 1
        return position_counter[key]

    def walk(element: Any, parent_container: NativeContainer | None, parent_locator: str) -> None:
        tag = str(element.tag or "").split("}")[-1]
        name = str(element.get("name") or "").strip()
        position = position_of(parent_locator, tag)
        locator = _native_locator(parent_locator, tag, position)

        if tag in _STRUCTURAL_TAGS:
            parent_ref = parent_container.container_ref if parent_container else None
            container = NativeContainer(
                container_ref=_structural_identity(tag, name, parent_ref, position),
                native_name=name,
                native_type=tag,
                parent_ref=parent_ref,
                native_locator=locator,
            )
            if parent_container is None:
                result.containers.append(container)
            else:
                parent_container.children.append(container)
            for child in element:
                walk(child, container, locator)
            return

        if tag == "field":
            field_code = str(element.get("name") or "").strip()
            if field_code:
                occurrence_counter[field_code] = occurrence_counter.get(field_code, 0) + 1
                result.fields.append(
                    NativeFieldOccurrence(
                        field_code=field_code,
                        occurrence_index=occurrence_counter[field_code],
                        container_ref=parent_container.container_ref if parent_container else "form",
                        native_locator=locator,
                        modifiers_raw={
                            key: str(element.get(key))
                            for key in ("invisible", "readonly", "required")
                            if element.get(key) is not None
                        },
                        field_metadata=dict(field_meta.get(field_code) or {}),
                    )
                )
            return

        for child in element:
            walk(child, parent_container, locator)

    walk(root, None, "")
    return result


def derive_native_field_ownership(
    native_view: NativeView,
    *,
    identity_fields: tuple[str, ...] | list[str] = (),
) -> dict[str, dict[str, str]]:
    """Derive unique primary field ownership from native field position.

    The first occurrence of a field wins as its primary owner; later
    occurrences are legal projections that must be declared explicitly by a
    caller, never auto-selected by name/type/order.

    The owner slot is the field's top-level sheet; the owner group is the
    native ``<group name>`` that contains the field (falling back to the sheet
    itself for sheet-level fields).
    """
    containers_by_ref: dict[str, NativeContainer] = {}

    def index_containers(nodes: list[NativeContainer]) -> None:
        for node in nodes:
            containers_by_ref[node.container_ref] = node
            index_containers(node.children)

    index_containers(native_view.containers)

    def top_sheet_ref(container_ref: str | None) -> str:
        node = containers_by_ref.get(container_ref) if container_ref else None
        while node is not None:
            if node.native_type == "sheet":
                return node.container_ref
            node = containers_by_ref.get(node.parent_ref) if node.parent_ref else None
        return "sheet"

    ownership: dict[str, dict[str, str]] = {}
    seen: set[str] = set()
    identity_set = set(str(item).strip() for item in identity_fields if str(item).strip())
    for occurrence in native_view.fields:
        code = occurrence.field_code
        if code in seen:
            continue
        seen.add(code)
        owner_group = occurrence.container_ref
        if not containers_by_ref.get(owner_group):
            owner_group = "sheet"
        owner_slot = top_sheet_ref(occurrence.container_ref)
        entry: dict[str, str] = {
            "ownerSlotRef": f"slot:{owner_slot}",
            "ownerGroupRef": f"group:{owner_group}",
        }
        if code in identity_set:
            entry["role"] = "identity"
        ownership[f"field:{code}"] = entry
    return ownership
