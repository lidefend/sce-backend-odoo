# -*- coding: utf-8 -*-
"""Contract Admission Policy (BNVA-019).

An internal, testable policy module for the Native-to-Contract information
boundary.  It is NOT a new public schema and does not carry business semantics;
it makes the admission decision of :file:`unified_page_contract_v2_assembler`
explicit and checkable.

Principles:
- native facts are captured once;
- business semantics are declared once;
- a contract is projected once;
- the renderer consumes once.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, FrozenSet

# Layered, one-way dependency. A downstream layer must not re-derive what an
# upstream layer already established.
NATIVE_SOURCE_FACTS = "native_source_facts"
CANONICAL_PROJECTION = "canonical_projection"
CONTRACT_ADMISSION = "contract_admission"
CONSUMER_PROJECTION = "consumer_projection"

ADMISSION_LAYERS: FrozenSet[str] = frozenset({
    NATIVE_SOURCE_FACTS,
    CANONICAL_PROJECTION,
    CONTRACT_ADMISSION,
    CONSUMER_PROJECTION,
})

# Information that must reach the contract when the current page needs it.
ADMITTED_FIELDS: FrozenSet[str] = frozenset({
    "container_identity",
    "container_hierarchy",
    "field_occurrences",
    "native_locator",
    "field_code",
    "field_type",
    "label",
    "widget",
    "placeholder",
    "relation",
    "modifiers_raw",
})

# Information that may enter only when its declaring condition is satisfied.
CONDITIONAL_FIELDS: FrozenSet[str] = frozenset({
    "group_identity",
    "sheet_slot",
    "notebook_page_hierarchy",
    "identity_semantics",
    "section_semantics",
    "field_ownership",
    "readonly_required_invisible",
    "visibility_groups",
    "technical_dependency",
})

# Inferences the platform must never make from structure, name or ORM type.
FORBIDDEN_INFERENCE: FrozenSet[str] = frozenset({
    "identity_from_field_name",
    "business_role_from_orm_type",
    "primary_owner_from_occurrence_order",
    "permission_from_frontend_visibility",
})


@dataclass(frozen=True)
class AdmissionResult:
    admitted: FrozenSet[str] = field(default_factory=frozenset)
    excluded: FrozenSet[str] = field(default_factory=frozenset)


NOT_DECLARED = object()


def classify_field_lifecycle(
    *,
    in_view: bool,
    in_named_group: bool,
    needs_hydration: bool,
    is_technical_dependency: bool,
    has_relation_capability: bool,
) -> FrozenSet[str]:
    """Classify a native field occurrence into its lifecycle sets.

    ``ViewField`` is the base fact; the other labels are orthogonal additions,
    never inferred from ORM type or occurrence order.
    """
    labels: set[str] = set()
    if not in_view:
        return frozenset()
    labels.add("ViewField")
    if in_named_group:
        labels.add("BusinessField")
    if needs_hydration:
        labels.add("HydrationField")
    if is_technical_dependency:
        labels.add("TechnicalDependency")
    if has_relation_capability:
        labels.add("RelationField")
    return frozenset(labels)


def business_role_for(
    *,
    native_group: str,
    declared_semantics: dict[str, Any] | None,
) -> Any:
    """Return the declared business role for a native group, never a guess.

    ``declared_semantics`` maps a native group identity to an explicit role.
    When the mapping is absent, return :data:`NOT_DECLARED` so the caller can
    emit NOT_VERIFIED instead of fabricating ``context`` from a name fragment.
    """
    mapping = declared_semantics or {}
    if native_group in mapping:
        return mapping[native_group]
    return NOT_DECLARED


def validate_admission(
    *,
    field_code: str,
    in_view: bool,
    in_named_group: bool,
    business_role_declared: bool,
) -> AdmissionResult:
    """Admit native facts and reject undeclared business semantics.

    A field outside the view is excluded.  A field inside the view is admitted
    as a ViewField, but its business ownership is only admitted when it lives in
    a named group AND a business role was explicitly declared.
    """
    if not in_view:
        return AdmissionResult(excluded=frozenset({field_code}))
    admitted = {"ViewField"}
    if in_named_group and business_role_declared:
        admitted.add("BusinessField")
    return AdmissionResult(admitted=frozenset(admitted))

