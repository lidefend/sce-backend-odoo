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

from .form_structure_authority import TECHNICAL_FIELD_CODES

# Structural tags whose native ``name`` gives a stable business identity.
_STRUCTURAL_TAGS = frozenset({"form", "sheet", "group", "notebook", "page"})
# Named business containers that can own fields; layout tags such as ``div``,
# ``header``, ``label`` or ``span`` are kept as containers for a complete
# layout tree but never become a business group owner.
_NAMED_BUSINESS_CONTAINER_TAGS = frozenset({"group", "notebook", "page"})

# Curated native attributes that a downstream adapter may need.  We do not
# capture every XML attribute: each entry below has a concrete consumer.  All
# values are plain strings, so the model stays JSON-serializable and never
# holds an lxml Element reference.
_CONTAINER_ATTRIBUTE_KEYS = frozenset({
    "class", "colspan", "col", "span", "groups", "attrs",
})
_FIELD_ATTRIBUTE_KEYS = frozenset({
    "string", "widget", "options", "placeholder", "nolabel", "colspan",
    "sum", "attrs", "invisible", "readonly", "required", "groups",
})

# ORM field types that carry a native relation target model.
_RELATION_FIELD_TYPES = frozenset({"many2one", "one2many", "many2many"})


@dataclass
class NativeFieldOccurrence:
    field_code: str
    occurrence_index: int
    container_ref: str
    native_locator: str
    modifiers_raw: dict[str, str] = field(default_factory=dict)
    field_metadata: dict[str, Any] = field(default_factory=dict)
    native_attributes: dict[str, str] = field(default_factory=dict)
    relation_descriptor: dict[str, Any] | None = None


@dataclass
class NativeContainer:
    container_ref: str
    native_name: str
    native_type: str
    native_string: str = ""
    parent_ref: str | None = None
    native_locator: str = ""
    children: list["NativeContainer"] = field(default_factory=list)
    native_attributes: dict[str, str] = field(default_factory=dict)


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
                "native_string": node.native_string,
                "parent_ref": node.parent_ref,
                "native_locator": node.native_locator,
                "native_attributes": node.native_attributes,
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
                    "native_attributes": item.native_attributes,
                    "relation_descriptor": item.relation_descriptor,
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


def _nearest_ancestor_ref(
    containers_by_ref: dict[str, NativeContainer],
    container_ref: str | None,
    tags: frozenset[str],
) -> str | None:
    """Return the nearest ancestor (inclusive) whose native_type is in ``tags``."""
    node = containers_by_ref.get(container_ref) if container_ref else None
    while node is not None:
        if node.native_type in tags:
            return node.container_ref
        node = containers_by_ref.get(node.parent_ref) if node.parent_ref else None
    return None


def _relation_descriptor(field_metadata: dict[str, Any]) -> dict[str, Any] | None:
    """Describe a field's native relation target, never its access authority.

    ``relation_descriptor`` records the ORM relation capability derived from
    ``fields_get()`` metadata.  It is a description, not a permission grant:
    being ``openable`` is still resolved by the server-side relation entry
    contract and record rules, not by this descriptor.
    """
    field_type = str(field_metadata.get("type") or "").strip()
    if field_type not in _RELATION_FIELD_TYPES:
        return None
    relation_model = str(field_metadata.get("relation") or "").strip() or None
    return {
        "field_type": field_type,
        "relation_type": field_type,
        "relation_model": relation_model,
    }


def project_native_view(
    env: Any,
    model_name: str,
    *,
    action_id: int = 0,
    view_id: int = 0,
    view_type: str = "form",
    root: Any | None = None,
    carrier: Any | None = None,
) -> NativeView:
    """Parse one merged Odoo view arch exactly once into a Canonical AST."""
    model = env[model_name]
    normalized_view_id = int(view_id or 0)
    view_data = None
    if root is None:
        cached = carrier.fetch(env, model_name, view_type, normalized_view_id) if carrier is not None else None
        if cached is not None and cached.get("_arch_root") is not None:
            view_data = cached
            root = cached["_arch_root"]
    if root is None:
        view_data = model.get_view(view_id=view_id or False, view_type=view_type)
        arch = str((view_data or {}).get("arch") or "")
        if not arch:
            raise ValueError(f"native view projection requires a resolved arch for {model_name}")
        root = etree.fromstring(arch.encode("utf-8"))

    fields_meta = model.fields_get()
    resolved_view_id = int(
        (view_data or {}).get("id")
        or (view_data or {}).get("_source_view_id")
        or view_id
        or 0
    )

    result = NativeView(
        model=model_name,
        action_id=int(action_id or 0),
        view_id=resolved_view_id,
        view_type=view_type,
        provenance={
            "source_view_id": resolved_view_id,
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
        if not isinstance(element.tag, str):
            # Comments / processing instructions carry no structure identity.
            return
        tag = str(element.tag).split("}")[-1]
        name = str(element.get("name") or "").strip()
        position = position_of(parent_locator, tag)
        locator = _native_locator(parent_locator, tag, position)

        if tag == "field":
            field_code = str(element.get("name") or "").strip()
            if field_code:
                occurrence_counter[field_code] = occurrence_counter.get(field_code, 0) + 1
                occurrence_meta = dict(fields_meta.get(field_code) or {})
                native_attributes = {
                    key: str(element.get(key))
                    for key in _FIELD_ATTRIBUTE_KEYS
                    if element.get(key) is not None
                }
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
                        field_metadata=occurrence_meta,
                        native_attributes=native_attributes,
                        relation_descriptor=_relation_descriptor(occurrence_meta),
                    )
                )
            return

        # Every non-field element becomes a container so the full Odoo layout
        # hierarchy (div / header / label / notebook / page / group ...) is
        # preserved, not flattened away.
        parent_ref = parent_container.container_ref if parent_container else None
        container = NativeContainer(
            container_ref=_structural_identity(tag, name, parent_ref, position),
            native_name=name,
            native_type=tag,
            native_string=str(element.get("string") or "").strip(),
            parent_ref=parent_ref,
            native_locator=locator,
            native_attributes={
                key: str(element.get(key))
                for key in _CONTAINER_ATTRIBUTE_KEYS
                if element.get(key) is not None
            },
        )
        if parent_container is None:
            result.containers.append(container)
        else:
            parent_container.children.append(container)
        for child in element:
            walk(child, container, locator)

    walk(root, None, "")
    return result


def derive_native_field_ownership(
    native_view: NativeView,
    *,
    identity_fields: tuple[str, ...] | list[str] = (),
) -> dict[str, dict[str, str]]:
    """Derive candidate primary field ownership from native group membership.

    A field earns a candidate primary owner only when it appears in exactly one
    named native group.  A field present in several named groups is an
    undeclared duplicate projection and must NOT be auto-selected by XML order;
    it stays unowned so the downstream guard reports NOT_VERIFIED instead of
    fabricating a business fact from node ordering.
    """
    containers_by_ref: dict[str, NativeContainer] = {}
    named_group_refs: set[str] = set()

    def index_containers(nodes: list[NativeContainer]) -> None:
        for node in nodes:
            containers_by_ref[node.container_ref] = node
            if node.native_name and node.native_type in _NAMED_BUSINESS_CONTAINER_TAGS:
                named_group_refs.add(node.container_ref)
            index_containers(node.children)

    index_containers(native_view.containers)

    def top_sheet_ref(container_ref: str | None) -> str:
        node = containers_by_ref.get(container_ref) if container_ref else None
        while node is not None:
            if node.native_type == "sheet":
                return node.native_name or "sheet"
            node = containers_by_ref.get(node.parent_ref) if node.parent_ref else None
        return "sheet"

    named_occurrences: dict[str, list[NativeFieldOccurrence]] = {}
    for occurrence in native_view.fields:
        code = occurrence.field_code
        if code in TECHNICAL_FIELD_CODES:
            continue
        owner_group = _nearest_ancestor_ref(
            containers_by_ref,
            occurrence.container_ref,
            _NAMED_BUSINESS_CONTAINER_TAGS,
        )
        if not owner_group or owner_group not in named_group_refs:
            continue
        named_occurrences.setdefault(code, []).append(occurrence)

    ownership: dict[str, dict[str, str]] = {}
    for code, occurrences in named_occurrences.items():
        owner_groups = list(dict.fromkeys(
            _nearest_ancestor_ref(
                containers_by_ref,
                occurrence.container_ref,
                _NAMED_BUSINESS_CONTAINER_TAGS,
            )
            for occurrence in occurrences
        ))
        if len(owner_groups) != 1:
            continue
        owner_group = owner_groups[0]
        if not containers_by_ref.get(owner_group):
            owner_group = "sheet"
        owner_slot = top_sheet_ref(owner_group)
        entry: dict[str, str] = {
            "ownerSlotRef": f"slot:{owner_slot}",
            "ownerGroupRef": f"group:{owner_group}",
        }
        ownership[f"field:{code}"] = entry
    return ownership


def build_native_form_structure_contract(
    native_view: NativeView,
    *,
    model: str,
    identity_fields: tuple[str, ...] | list[str] = (),
    field_labels: dict[str, str] | None = None,
    navigation_title: str = "",
) -> dict[str, Any]:
    """Build a formStructureContract from the canonical native projection.

    The sheet is the slot; its native ``<group name>`` children are the groups;
    field ownership derives from each field's container membership.  Identity
    is only taken from the explicit ``identity_fields`` declaration.
    """
    containers_by_ref: dict[str, NativeContainer] = {}

    def index_containers(nodes: list[NativeContainer]) -> None:
        for node in nodes:
            containers_by_ref[node.container_ref] = node
            index_containers(node.children)

    index_containers(native_view.containers)

    labels = {str(k): str(v) for k, v in (field_labels or {}).items()}
    identity_set = set(str(item).strip() for item in identity_fields if str(item).strip())

    def group_role(native_name: str) -> str:
        lowered = native_name.lower()
        if "collaboration" in lowered or "approval" in lowered:
            return "activity"
        if "trace" in lowered or "source" in lowered:
            return "audit"
        if "readiness" in lowered or "summary" in lowered:
            return "summary"
        if "responsibility" in lowered and "responsible" not in lowered:
            return "audit"
        return "context"

    def field_role(occurrence: NativeFieldOccurrence, group_native_name: str) -> str:
        # The native group is the business-structure authority. A field's
        # semantic role follows its owning group, never its ORM field type:
        # a many2one like ``manager_id`` inside a ``context`` group is a
        # primary business fact, not a subordinate relation collection.
        # Relation navigation is driven by the field descriptor type, which
        # the frontend already consumes independently of this role.
        return group_role(group_native_name)

    def field_label(code: str) -> str:
        return labels.get(code) or str(code)

    def business_home_ref(container_ref: str | None) -> str | None:
        """Nearest named business container, otherwise the enclosing sheet."""
        node = containers_by_ref.get(container_ref) if container_ref else None
        while node is not None:
            if node.native_type in _NAMED_BUSINESS_CONTAINER_TAGS and node.native_name:
                return node.container_ref
            if node.native_type == "sheet":
                return node.container_ref
            node = containers_by_ref.get(node.parent_ref) if node.parent_ref else None
        return None

    def collect_business_containers(node: NativeContainer) -> list[NativeContainer]:
        found: list[NativeContainer] = []
        for child in node.children:
            if child.native_type in _NAMED_BUSINESS_CONTAINER_TAGS:
                found.append(child)
            found.extend(collect_business_containers(child))
        return found

    slots: list[dict[str, Any]] = []
    field_roles: dict[str, dict[str, str]] = {}
    seen_fields: set[str] = set()
    all_sheets: list[NativeContainer] = []

    def collect_sheets(nodes: list[NativeContainer]) -> None:
        for node in nodes:
            if node.native_type == "sheet":
                all_sheets.append(node)
            collect_sheets(node.children)

    collect_sheets(native_view.containers)

    for sheet in all_sheets:
        groups: list[dict[str, Any]] = []
        slot_identity = sheet.native_name or "sheet"
        group_containers: list[NativeContainer] = collect_business_containers(sheet)
        for group in group_containers:
            group_identity = group.native_name or group.container_ref
            group_fields = [
                occurrence
                for occurrence in native_view.fields
                if business_home_ref(occurrence.container_ref) == group.container_ref
            ]
            field_refs: list[str] = []
            for occurrence in group_fields:
                code = occurrence.field_code
                if code in TECHNICAL_FIELD_CODES:
                    continue
                if code in seen_fields:
                    continue
                seen_fields.add(code)
                field_refs.append(code)
                role = field_role(occurrence, group.native_name)
                field_roles[code] = {
                    "role": role,
                    "slot": slot_identity,
                    "group": group_identity,
                }
            groups.append(
                {
                    "name": group_identity,
                    "title": group.native_string or group_identity,
                    "role": group_role(group.native_name),
                    "fieldRefs": field_refs,
                    "fieldLabels": {code: field_label(code) for code in field_refs},
                }
            )
        # sheet-level fields (not inside a group)
        sheet_fields = [
            occurrence
            for occurrence in native_view.fields
            if business_home_ref(occurrence.container_ref) == sheet.container_ref
        ]
        sheet_field_refs: list[str] = []
        for occurrence in sheet_fields:
            code = occurrence.field_code
            if code in TECHNICAL_FIELD_CODES:
                continue
            if code in seen_fields:
                continue
            seen_fields.add(code)
            sheet_field_refs.append(code)
            field_roles[code] = {
                "role": "context",
                "slot": slot_identity,
                "group": slot_identity,
            }
        slots.append(
            {
                "slot": slot_identity,
                "title": sheet.native_string or "业务表单",
                "role": "context",
                "fieldRefs": sheet_field_refs,
                "groups": [item for item in groups if item.get("fieldRefs")],
            }
        )

    ownership = derive_native_field_ownership(native_view, identity_fields=identity_fields)
    return {
        "source": "ui.contract.v2.form_structure_contract",
        "structureVersion": "1.1",
        "model": model,
        "viewType": "form",
        "mode": "native_structured_form",
        "presentationMode": "workspace",
        "structureSource": "native_view",
        "structureAuthority": "native_form_slots",
        "objectProfile": {
            "model": model,
            "kind": "business_form",
            "factAuthority": "business_object_model_and_view",
        },
        "navigation": {"title": navigation_title or "业务办理"},
        "slots": slots,
        "fieldRoles": field_roles,
        "fieldOwnership": ownership,
        "surfaces": [],
        "sourceAuthority": {
            "kind": "unified_page_contract_v2",
            "runtime_carrier": "ui.contract.v2.form_structure_contract",
            "projection_only": True,
            "no_business_fact_authority": True,
            "governed_form_structure": True,
            "governance_source": {
                "source": "native_view_projection",
                "formStructureAuthority": "native_form_slots",
            },
        },
    }
