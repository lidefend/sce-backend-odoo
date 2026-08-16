# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any

from .request_params import parse_positive_int


MODIFIER_DEPENDENCY_KINDS = {"field_compare", "field_truthy"}
# Bounds opportunistic display hydration only. Fields referenced by normalized
# modifiers are correctness dependencies and are added independently.
FORM_RECORD_SNAPSHOT_FIELD_BUDGET = 80


def collect_modifier_dependency_fields(*sources: Any, known_fields: Any = None) -> list[str]:
    """Return the stable field dependency closure of normalized modifiers.

    The traversal intentionally accepts the complete normalized contract shape:
    actions added by late platform or industry extensions must contribute the
    same dependencies as native form buttons assembled earlier in the request.
    """

    allowed = set(known_fields or []) if known_fields is not None else None
    names: list[str] = []

    def walk(value: Any) -> None:
        if isinstance(value, (list, tuple)):
            for item in value:
                walk(item)
            return
        if not isinstance(value, dict):
            return
        kind = str(value.get("kind") or "").strip()
        field_name = str(value.get("field") or "").strip()
        if (
            kind in MODIFIER_DEPENDENCY_KINDS
            and field_name
            and (allowed is None or field_name in allowed)
            and field_name not in names
        ):
            names.append(field_name)
        for child in value.values():
            walk(child)

    for source in sources:
        walk(source)
    return names


def hydrate_final_modifier_dependencies(
    env: Any,
    contract_v2: dict[str, Any],
    *,
    model: str,
    record_id: Any,
    view_type: str,
    logger: Any = None,
) -> None:
    """Read missing scalar fields referenced by the final modifier graph.

    The normal record snapshot remains payload-budgeted. Modifier dependencies
    are correctness inputs and may arrive through extensions after that initial
    read, so they are hydrated from the final normalized contract instead.
    """

    if view_type != "form" or not model or not isinstance(contract_v2, dict):
        return
    record_id_int, _record_id_error = parse_positive_int(record_id, allow_empty=True)
    record_id_int = int(record_id_int or 0)
    if record_id_int <= 0:
        return
    try:
        Model = env[model]
    except Exception:
        return
    fields_map = getattr(Model, "_fields", {})
    if not isinstance(fields_map, dict):
        return
    data_contract = contract_v2.get("dataContract")
    if not isinstance(data_contract, dict):
        return
    main_data = data_contract.get("mainData")
    if not isinstance(main_data, dict):
        return
    dependencies = collect_modifier_dependency_fields(contract_v2, known_fields=fields_map)
    missing = []
    for field_name in dependencies:
        if field_name in main_data:
            continue
        field_type = str(getattr(fields_map.get(field_name), "type", "") or "")
        if field_type in {"one2many", "many2many", "binary", "html"}:
            continue
        missing.append(field_name)
    if not missing:
        return
    try:
        record = Model.browse(record_id_int).exists()
        if not record:
            return
        rows = record.read(missing)
        if rows and isinstance(rows[0], dict):
            for field_name in missing:
                if field_name in rows[0]:
                    main_data[field_name] = rows[0][field_name]
    except Exception:
        # Missing values leave modifier evaluation fail-closed. Never sudo or
        # manufacture permission truth to make an action visible.
        if logger is not None:
            logger.debug("ui.contract.v2 final modifier dependency hydration skipped", exc_info=True)
