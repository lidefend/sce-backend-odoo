"""Pure controller-route metadata projection for registry audits."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any, Callable


def _text(value) -> str:
    return str(value or "").strip()


def _symbol(value) -> str:
    return ".".join(
        part
        for part in (
            _text(getattr(value, "__module__", "")),
            _text(getattr(value, "__qualname__", "") or getattr(value, "__name__", "")),
        )
        if part
    )


def _routes(value) -> list[str]:
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, (list, tuple, set, frozenset)):
        return sorted({_text(item) for item in value if _text(item)})
    return []


def _methods(value) -> list[str]:
    if isinstance(value, str):
        value = [value]
    return sorted(
        {
            _text(item).upper()
            for item in (value or [])
            if _text(item)
        }
    )


def _route_surface(route: str, route_type: str, module: str) -> str:
    addon = module.split(".")[2] if module.startswith("odoo.addons.") else module
    if addon.startswith(("smart_", "sce_")):
        if route.startswith("/api/") or route_type in {"json", "jsonrpc"}:
            return "CUSTOM_FRONTEND_BACKEND_API"
        return "CUSTOM_FRONTEND_PAGE_ROUTE"
    if route_type in {"json", "jsonrpc"}:
        return "ODOO_NATIVE_RPC"
    return "ODOO_NATIVE_WEB_ROUTE"


def _conflict_id(route: str, methods: list[str]) -> str:
    digest = hashlib.sha256(
        f"{route}\0{','.join(methods)}".encode("utf-8")
    ).hexdigest()[:12].upper()
    return f"ADMIN_VIS_P3_ROUTE_{digest}"


def _rule_applies(rule: dict[str, Any], methods: list[str]) -> bool:
    rule_methods = set(rule.get("methods") or [])
    return not methods or not rule_methods or bool(set(methods) & rule_methods)


def _rules_overlap(
    rules: list[dict[str, Any]],
) -> tuple[str, list[str], list[str]]:
    """Classify request-match overlap without invoking Werkzeug matching."""

    if len(rules) < 2:
        return "FALSE_CONFLICT", [], []
    blockers = []
    unresolved = []
    for index, left in enumerate(rules):
        for right in rules[index + 1 :]:
            if not _rule_applies(left, list(right.get("methods") or [])):
                blockers.append("http_methods_do_not_overlap")
            for key in ("host", "subdomain", "websocket"):
                left_value = left.get("match_dimensions", {}).get(key)
                right_value = right.get("match_dimensions", {}).get(key)
                if left_value != right_value:
                    blockers.append(f"{key}_does_not_overlap")
            if (
                left.get("match_dimensions", {}).get("build_only") is True
                or right.get("match_dimensions", {}).get("build_only") is True
            ):
                blockers.append("build_only_rule_is_not_request_matchable")
            left_pattern = left.get("match_dimensions", {}).get("compiled_pattern")
            right_pattern = right.get("match_dimensions", {}).get("compiled_pattern")
            if left_pattern and right_pattern and left_pattern != right_pattern:
                blockers.append("compiled_matcher_patterns_do_not_overlap")
            elif not left_pattern or not right_pattern:
                unresolved.append(
                    "compiled matcher pattern is unavailable in the current framework"
                )
            left_converters = left.get("match_dimensions", {}).get("converters")
            right_converters = right.get("match_dimensions", {}).get("converters")
            if left_converters != right_converters:
                unresolved.append(
                    "converter domains differ and were not executed against request values"
                )
            elif left_converters or right_converters:
                unresolved.append(
                    "converter request values were not supplied or executed"
                )
            if (
                left.get("match_dimensions", {}).get("defaults")
                != right.get("match_dimensions", {}).get("defaults")
            ):
                unresolved.append(
                    "route defaults differ and request values were not supplied"
                )
    if blockers:
        return "FALSE_CONFLICT", sorted(set(blockers)), sorted(set(unresolved))
    if unresolved:
        return "UNRESOLVED_OVERLAP", [], sorted(set(unresolved))
    return "TRUE_RUNTIME_CONFLICT", [], []


def _reconcile_collision(
    route: str,
    methods: list[str],
    rows: list[dict[str, Any]],
    framework_rules: list[dict[str, Any]],
    matcher_order_proof: dict[str, Any],
) -> dict[str, Any]:
    matching_rules = [
        rule
        for rule in framework_rules
        if rule.get("route") == route and _rule_applies(rule, methods)
    ]
    matching_rules.sort(key=lambda rule: int(rule.get("routing_map_order", -1)))
    map_ids = sorted(
        {
            _text(rule.get("routing_map_id"))
            for rule in matching_rules
            if _text(rule.get("routing_map_id"))
        }
    )
    same_final_map = bool(matching_rules) and len(map_ids) == 1
    if not matching_rules:
        conflict_classification = "FALSE_CONFLICT"
        overlap_blockers = ["candidate declarations absent from final routing map"]
        overlap_unresolved = []
        false_conflict_reason = "NOT_REGISTERED_IN_FINAL_ROUTING_MAP"
    elif len(matching_rules) == 1:
        conflict_classification = "FALSE_CONFLICT"
        overlap_blockers = [
            "controller inheritance/decorator merge produced one final Rule"
        ]
        overlap_unresolved = []
        false_conflict_reason = "INHERITANCE_MERGED_TO_ONE_FINAL_RULE"
    elif not same_final_map:
        conflict_classification = "FALSE_CONFLICT"
        overlap_blockers = ["rules do not belong to one final routing map"]
        overlap_unresolved = []
        false_conflict_reason = "DIFFERENT_FINAL_ROUTING_MAPS"
    else:
        (
            conflict_classification,
            overlap_blockers,
            overlap_unresolved,
        ) = _rules_overlap(matching_rules)
        false_conflict_reason = (
            "COMPLETE_MATCH_DIMENSIONS_DO_NOT_OVERLAP"
            if conflict_classification == "FALSE_CONFLICT"
            else ""
        )
    winner_permitted = conflict_classification == "TRUE_RUNTIME_CONFLICT"
    winner = ""
    effective_endpoint = ""
    winner_decision_rule = ""
    winner_evidence = []
    winner_analysis_status = (
        "NOT_RUN_AFTER_TRUE_CONFLICT_GATE"
        if winner_permitted
        else "NOT_APPLICABLE"
    )
    unresolved_reason = ""
    if conflict_classification == "TRUE_RUNTIME_CONFLICT":
        ordering_keys = {
            _text(rule.get("ordering_key_repr")) for rule in matching_rules
        }
        proof_complete = (
            matcher_order_proof.get("analysis_stage")
            == "CURRENT_FRAMEWORK_LINEAR_ORDER_PROVEN"
            and matcher_order_proof.get("map_iter_rules_order_proven") is True
            and matcher_order_proof.get("map_stable_sort_proven") is True
            and matcher_order_proof.get("adapter_first_match_return_proven") is True
            and all(
                rule.get("ordering_key_executed") is True
                and _text(rule.get("ordering_key_repr"))
                for rule in matching_rules
            )
            and len(ordering_keys) == 1
        )
        if proof_complete:
            winner_rule = matching_rules[0]
            winner = _text(winner_rule.get("effective_implementation"))
            effective_endpoint = _text(winner_rule.get("endpoint_symbol"))
            winner_decision_rule = (
                "first_applicable_rule_in_current_framework_sorted_rule_sequence"
            )
            winner_evidence = [
                "candidate passed final-map and complete-match-overlap gates",
                "current container Map.iter_rules exposes the matcher rule sequence",
                "current container Map.update uses a stable ordering-key sort",
                "current container MapAdapter.match returns the first applicable rule",
                "candidate rules have the same current-framework ordering key",
                f"routing_map_order={winner_rule.get('routing_map_order')}",
                (
                    "map_adapter_match_source_sha256="
                    f"{matcher_order_proof.get('map_adapter_match_source_sha256')}"
                ),
            ]
            winner_analysis_status = "RESOLVED_NONINVASIVE"
        else:
            unresolved_reason = (
                "true runtime conflict established; current-framework source and "
                "ordering-key evidence does not prove an effective winner"
            )
    elif conflict_classification == "UNRESOLVED_OVERLAP":
        unresolved_reason = "; ".join(overlap_unresolved)
    contributions = [
        {
            "route_policy_id": row["route_policy_id"],
            "module": row["module"],
            "source_file": row["method_source_file"],
            "source_symbol": row["method_symbol"],
            "controller": row["controller"],
            "class_mro": row["override_chain"],
            "auth": row["auth"],
            "type": row["type"],
            "csrf": row["csrf"],
            "cors": row["cors"],
            "route_surface": row.get("route_surface", ""),
        }
        for row in rows
    ]
    security_shapes = {
        (
            row["auth"],
            row["type"],
            row["csrf"],
            row["cors"],
        )
        for row in rows
    }
    return {
        "route_conflict_id": _conflict_id(route, methods),
        "route_path": route,
        "http_methods": methods,
        "route_surfaces": sorted(
            {
                _text(row.get("route_surface"))
                for row in [*rows, *matching_rules]
                if _text(row.get("route_surface"))
            }
        ),
        "contributions": contributions,
        "contribution_modules": sorted({row["module"] for row in rows}),
        "source_files": sorted({row["method_source_file"] for row in rows}),
        "source_symbols": sorted({row["method_symbol"] for row in rows}),
        "controller_inheritance": [row["override_chain"] for row in rows],
        "module_dependency_order": [
            rule.get("module_order") for rule in matching_rules
        ],
        "controller_registration_order": [
            rule.get("controller_registration_order") for rule in matching_rules
        ],
        "routing_map_order": [
            rule.get("routing_map_order") for rule in matching_rules
        ],
        "final_routing_map_ids": map_ids,
        "same_final_routing_map": same_final_map,
        "final_rule_count": len(matching_rules),
        "final_rules": matching_rules,
        "rule_endpoints": [
            rule.get("endpoint_symbol") for rule in matching_rules
        ],
        "effective_endpoint": effective_endpoint,
        "effective_implementation": winner,
        "replaced_implementations": (
            sorted(
                implementation
                for implementation in {
                    _text(rule.get("effective_implementation"))
                    for rule in matching_rules
                }
                if implementation and implementation != winner
            )
            if winner
            else []
        ),
        "conflict_classification": conflict_classification,
        "false_conflict_reason": false_conflict_reason,
        "overlap_blockers": overlap_blockers,
        "overlap_unresolved_inputs": overlap_unresolved,
        "winner_analysis_permitted": winner_permitted,
        "winner_analysis_status": winner_analysis_status,
        "winner_decision_rule": winner_decision_rule,
        "winner_evidence": winner_evidence,
        "external_reachability": "ROUTING_MAP_REGISTERED" if matching_rules else "ABSENT",
        "policy_change_across_override": len(security_shapes) > 1,
        "security_relevant_differences": [
            {
                "source_symbol": row["method_symbol"],
                "auth": row["auth"],
                "type": row["type"],
                "csrf": row["csrf"],
                "cors": row["cors"],
            }
            for row in rows
        ],
        "enumeration_status": (
            "RESOLVED"
            if winner_analysis_status == "RESOLVED_NONINVASIVE"
            else (
                "UNRESOLVED_DYNAMIC"
                if conflict_classification
                in {"TRUE_RUNTIME_CONFLICT", "UNRESOLVED_OVERLAP"}
                else "FALSE_CONFLICT"
            )
        ),
        "unresolved_reason": unresolved_reason,
        "request_match_executed": False,
        "endpoint_executed": False,
    }


def _source_file(value, resolver: Callable[[Any], str]) -> str:
    try:
        return resolver(value)
    except (OSError, TypeError):
        return ""


def _endpoint_source(method, resolver: Callable[[Any], str]) -> str:
    endpoint = getattr(method, "original_endpoint", None)
    return _source_file(endpoint or method, resolver)


def _routing_metadata(method) -> Mapping:
    for attribute in ("routing", "original_routing"):
        routing = getattr(method, attribute, None)
        if isinstance(routing, Mapping):
            return routing
    return {}


def _routing_chain(controller, method_name: str) -> list[tuple[Any, dict[str, Any]]]:
    chain = []
    for owner in reversed(getattr(controller, "__mro__", ())):
        method = getattr(owner, "__dict__", {}).get(method_name)
        routing = _routing_metadata(method)
        if routing:
            chain.append((owner, dict(routing)))
    return chain


def project_route_policies(
    controller_classes: list[type],
    *,
    source_file_resolver: Callable[[Any], str],
    framework_rules: list[dict[str, Any]] | None = None,
    matcher_order_proof: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Project decorated controller metadata without invoking a route."""

    records = []
    unresolved = []
    controller_inventory = []
    for controller_index, controller in enumerate(
        sorted(set(controller_classes), key=_symbol),
        1,
    ):
        method_inventory = []
        for method_name in sorted(getattr(controller, "__dict__", {})):
            method = controller.__dict__.get(method_name)
            if callable(method):
                method_inventory.append(
                    {
                        "method": method_name,
                        "symbol": _symbol(method),
                        "metadata_keys": sorted(
                            _text(key)
                            for key in getattr(method, "__dict__", {})
                            if _text(key)
                        ),
                        "routing_metadata_type": _symbol(
                            type(getattr(method, "routing", None))
                        ),
                        "original_routing_metadata_type": _symbol(
                            type(getattr(method, "original_routing", None))
                        ),
                    }
                )
            if not _routing_metadata(method):
                continue
            chain = _routing_chain(controller, method_name)
            merged: dict[str, Any] = {}
            for _owner, routing in chain:
                merged.update(routing)
            route_values = _routes(
                merged.get("routes")
                if "routes" in merged
                else merged.get("route")
            )
            if not route_values:
                unresolved.append(
                    {
                        "controller": _symbol(controller),
                        "method": method_name,
                        "reason": "decorated method has no statically recoverable route path",
                        "override_chain": [_symbol(owner) for owner, _routing in chain],
                    }
                )
                continue
            methods = _methods(merged.get("methods"))
            for route in route_values:
                route_type = _text(merged.get("type") or "http")
                controller_module = _text(getattr(controller, "__module__", ""))
                records.append(
                    {
                        "route_policy_id": "",
                        "route": route,
                        "controller": _symbol(controller),
                        "controller_source_file": _source_file(
                            controller,
                            source_file_resolver,
                        ),
                        "method": method_name,
                        "method_symbol": _symbol(method),
                        "method_source_file": _endpoint_source(
                            method, source_file_resolver
                        ),
                        "module": controller_module,
                        "route_surface": _route_surface(
                            route,
                            route_type,
                            controller_module,
                        ),
                        "auth": _text(merged.get("auth") or "user"),
                        "type": route_type,
                        "methods": methods,
                        "csrf": bool(merged.get("csrf", True)),
                        "cors": _text(merged.get("cors")),
                        "readonly": bool(merged.get("readonly", False)),
                        "save_session": bool(merged.get("save_session", True)),
                        "routing_metadata": {
                            _text(key): value
                            for key, value in sorted(merged.items())
                            if key
                            not in {
                                "routes",
                                "route",
                                "auth",
                                "type",
                                "methods",
                                "csrf",
                                "cors",
                                "readonly",
                                "save_session",
                            }
                            and (
                                value is None
                                or isinstance(value, (str, int, float, bool))
                            )
                        },
                        "override_chain": [_symbol(owner) for owner, _routing in chain],
                        "registration_order": controller_index,
                        "registration_evidence": "loaded odoo.http.Controller subclass",
                        "executed_during_audit": False,
                    }
                )
        controller_inventory.append(
            {
                "controller": _symbol(controller),
                "source_file": _source_file(controller, source_file_resolver),
                "direct_callable_count": len(method_inventory),
                "direct_callables": method_inventory,
            }
        )
    records.sort(
        key=lambda row: (
            row["route"],
            row["methods"],
            row["controller"],
            row["method"],
        )
    )
    for index, record in enumerate(records, 1):
        record["route_policy_id"] = f"ROUTE-POLICY-{index:04d}"

    collisions = []
    framework_rules = list(framework_rules or [])
    matcher_order_proof = dict(matcher_order_proof or {})
    buckets: dict[tuple[str, tuple[str, ...]], list[dict[str, Any]]] = {}
    for record in records:
        key = (record["route"], tuple(record["methods"]))
        buckets.setdefault(key, []).append(record)
    for (route, methods), rows in sorted(buckets.items()):
        if len(rows) < 2:
            continue
        collisions.append(
            _reconcile_collision(
                route,
                list(methods),
                rows,
                framework_rules,
                matcher_order_proof,
            )
        )
    return {
        "schema_version": 4,
        "enumeration_source": "loaded odoo.http.Controller subclasses and decorator metadata",
        "records": records,
        "framework_rules": framework_rules,
        "matcher_order_proof": matcher_order_proof,
        "collisions": collisions,
        "unresolved_items": unresolved,
        "controller_inventory": controller_inventory,
        "controller_methods_executed": False,
        "http_requests_executed": False,
        "request_match_executed": False,
    }
