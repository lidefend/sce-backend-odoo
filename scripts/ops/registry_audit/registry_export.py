"""Read-only Odoo shell exporter for runtime registry metadata.

The script intentionally inspects registry/class/field/config metadata only.
It never invokes a handler, a public model method, default_get, onchange,
compute, create, write, or unlink.
"""

from __future__ import annotations

import ast
import hashlib
import importlib
import importlib.metadata
import importlib.util
import inspect
import json
import os
import textwrap
from pathlib import Path

import odoo


OUTPUT = Path(os.environ["REGISTRY_AUDIT_OUTPUT_FILE"])
RUN_ID = os.environ["REGISTRY_AUDIT_RUN_ID"]
GIT_HEAD = os.environ["REGISTRY_AUDIT_GIT_HEAD"]
GIT_TREE = os.environ["REGISTRY_AUDIT_GIT_TREE"]
MODULES = sorted(
    {
        item.strip()
        for item in os.environ.get("REGISTRY_AUDIT_MODULES", "").split(",")
        if item.strip()
    }
)


def load_audit_helper(name):
    path = Path("/mnt/registry-audit") / f"{name}.py"
    spec = importlib.util.spec_from_file_location(
        f"registry_audit_{name}",
        path,
    )
    if not spec or not spec.loader:
        raise RuntimeError(f"unable to load registry audit helper: {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GENERIC_POLICY_METADATA = load_audit_helper("generic_policy_metadata")
ROUTE_POLICY_METADATA = load_audit_helper("route_policy_metadata")


def text(value):
    return str(value or "").strip()


def symbol(value):
    module = text(getattr(value, "__module__", ""))
    name = text(
        getattr(value, "__qualname__", "")
        or getattr(value, "__name__", "")
    )
    return ".".join(part for part in (module, name) if part)


def source_file(value):
    try:
        path = inspect.getsourcefile(value) or inspect.getfile(value)
    except (OSError, TypeError):
        return ""
    marker = "/mnt/source-addons/"
    normalized = str(path or "")
    if marker in normalized:
        return "addons/" + normalized.split(marker, 1)[1]
    external_marker = "/mnt/addons_external/"
    if external_marker in normalized:
        return "addons_external/" + normalized.split(external_marker, 1)[1]
    return normalized


def json_safe(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {
            text(key): json_safe(item)
            for key, item in sorted(value.items(), key=lambda pair: text(pair[0]))
        }
    if isinstance(value, (list, tuple, set, frozenset)):
        return sorted(
            (json_safe(item) for item in value),
            key=lambda item: json.dumps(item, sort_keys=True, default=str),
        )
    return {"type": type(value).__name__, "symbol": symbol(value)}


def installed_modules():
    rows = env["ir.module.module"].search_read(
        [("state", "=", "installed")],
        ["name", "latest_version", "author", "application"],
        order="name",
    )
    return [
        {
            "name": text(row.get("name")),
            "version": text(row.get("latest_version")),
            "author": text(row.get("author")),
            "application": bool(row.get("application")),
        }
        for row in rows
    ]


def extension_modules():
    raw = env["ir.config_parameter"].get_param(
        "sc.core.extension_modules",
        "",
    )
    names = sorted({item.strip() for item in text(raw).split(",") if item.strip()})
    installed = {row["name"] for row in installed_modules()}
    return [
        {
            "module": name,
            "installed": name in installed,
            "source": "ir.config_parameter:sc.core.extension_modules",
        }
        for name in names
    ]


def extension_contributions(extension_rows):
    rows = []
    unresolved = []
    for item in extension_rows:
        name = item["module"]
        try:
            module = importlib.import_module(f"odoo.addons.{name}")
        except Exception as exc:
            unresolved.append(
                {
                    "kind": "extension_import",
                    "module": name,
                    "reason": type(exc).__name__,
                }
            )
            continue
        hooks = []
        for attr_name in sorted(dir(module)):
            if not (
                attr_name == "smart_core_register"
                or attr_name.startswith("smart_core_")
            ):
                continue
            candidate = getattr(module, attr_name)
            if callable(candidate):
                hooks.append(
                    {
                        "hook": attr_name,
                        "symbol": symbol(candidate),
                        "source_file": source_file(candidate),
                        "executed": False,
                    }
                )
        registration = {}
        hook = getattr(module, "smart_core_register", None)
        if callable(hook):
            scratch = {}
            hook(scratch)
            registration = {
                text(intent): {
                    "handler": symbol(handler),
                    "source_file": source_file(handler),
                }
                for intent, handler in sorted(scratch.items())
            }
            for row in hooks:
                if row["hook"] == "smart_core_register":
                    row["executed"] = True
        rows.append(
            {
                "module": name,
                "installed": item["installed"],
                "hooks": hooks,
                "handler_contributions": registration,
            }
        )
    return rows, unresolved


def handler_registry():
    registry_module = importlib.import_module(
        "odoo.addons.smart_core.core.handler_registry"
    )
    registry = getattr(registry_module, "HANDLER_REGISTRY", {}) or {}
    canonical = {}
    aliases = []
    for registration_order, (intent, handler) in enumerate(
        registry.items(),
        1,
    ):
        declared = text(getattr(handler, "INTENT_TYPE", ""))
        record = {
            "intent": text(intent),
            "declared_intent": declared,
            "handler_class": symbol(handler),
            "source_file": source_file(handler),
            "auth_mode": text(getattr(handler, "ACL_MODE", "")),
            "required_groups": sorted(
                text(group)
                for group in (getattr(handler, "REQUIRED_GROUPS", None) or [])
                if text(group)
            ),
            "business_mutation_capable": any(
                token in text(intent).lower()
                for token in (
                    "create",
                    "write",
                    "unlink",
                    "delete",
                    "execute",
                    "advance",
                    "transition",
                    "approve",
                )
            ),
            "registration_order": registration_order,
        }
        canonical[text(intent)] = record
        if declared and declared != text(intent):
            aliases.append(
                {
                    "alias": text(intent),
                    "canonical_intent": declared,
                    "handler_class": symbol(handler),
                }
            )
    return (
        sorted(canonical.values(), key=lambda row: row["intent"]),
        sorted(aliases, key=lambda row: row["alias"]),
    )


def _route_surface(route, route_type, module, build_only):
    if build_only:
        return "INTERNAL_ROUTE"
    if module.startswith(("smart_", "sce_")):
        if route.startswith("/api/") or route_type in {"json", "jsonrpc"}:
            return "CUSTOM_FRONTEND_BACKEND_API"
        return "CUSTOM_FRONTEND_PAGE_ROUTE"
    if route_type in {"json", "jsonrpc"}:
        return "ODOO_NATIVE_RPC"
    return "ODOO_NATIVE_WEB_ROUTE"


def _routing_map_identity(routing_map, rules):
    material = {
        "map_class": symbol(type(routing_map)),
        "map_source_file": source_file(type(routing_map)),
        "rules": [
            {
                "route": text(getattr(rule, "rule", "")),
                "methods": sorted(getattr(rule, "methods", None) or []),
                "endpoint": symbol(getattr(rule, "endpoint", None)),
            }
            for rule in rules
        ],
    }
    return "ROUTING-MAP-" + hashlib.sha256(
        json.dumps(material, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16].upper()


def _converter_metadata(rule):
    return [
        {
            "variable": text(name),
            "class": symbol(type(converter)),
            "regex": text(getattr(converter, "regex", "")),
            "weight": json_safe(getattr(converter, "weight", None)),
        }
        for name, converter in sorted(
            (getattr(rule, "_converters", {}) or {}).items()
        )
    ]


def _source_and_tree(value):
    try:
        source = textwrap.dedent(inspect.getsource(value))
        return source, ast.parse(source)
    except (OSError, TypeError, IndentationError, SyntaxError):
        return "", ast.parse("pass")


def _contains_attribute(node, attribute):
    return any(
        isinstance(child, ast.Attribute) and child.attr == attribute
        for child in ast.walk(node)
    )


def _matcher_order_proof(routing_map):
    routing = importlib.import_module("werkzeug.routing")
    map_class = type(routing_map)
    map_update = getattr(map_class, "update", None)
    map_iter_rules = getattr(map_class, "iter_rules", None)
    adapter_match = getattr(
        getattr(routing, "MapAdapter", None),
        "match",
        None,
    )
    update_source, update_tree = _source_and_tree(map_update)
    iter_source, iter_tree = _source_and_tree(map_iter_rules)
    match_source, match_tree = _source_and_tree(adapter_match)
    stable_sort_detected = any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "sort"
        and _contains_attribute(node, "match_compare_key")
        for node in ast.walk(update_tree)
    )
    iter_calls_update = any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "update"
        for node in ast.walk(iter_tree)
    )
    iter_returns_rules = any(
        isinstance(node, ast.Return) and _contains_attribute(node, "_rules")
        for node in ast.walk(iter_tree)
    )
    adapter_iterates_rules = any(
        isinstance(node, ast.For) and _contains_attribute(node.iter, "_rules")
        for node in ast.walk(match_tree)
    )
    adapter_calls_rule_match = any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "match"
        for node in ast.walk(match_tree)
    )
    adapter_returns_rule = any(
        isinstance(node, ast.Return)
        and any(
            isinstance(child, ast.Name) and child.id == "rule"
            for child in ast.walk(node)
        )
        for node in ast.walk(match_tree)
    )
    complete = all(
        (
            stable_sort_detected,
            iter_calls_update,
            iter_returns_rules,
            adapter_iterates_rules,
            adapter_calls_rule_match,
            adapter_returns_rule,
        )
    )
    return {
        "analysis_stage": (
            "CURRENT_FRAMEWORK_LINEAR_ORDER_PROVEN"
            if complete
            else "CURRENT_FRAMEWORK_ORDER_UNRESOLVED"
        ),
        "odoo_version": text(getattr(odoo.release, "version", "")),
        "werkzeug_version": text(importlib.metadata.version("werkzeug")),
        "python_version": ".".join(map(str, __import__("sys").version_info[:3])),
        "routing_map_class": symbol(map_class),
        "routing_map_source_file": source_file(map_class),
        "map_update_symbol": symbol(map_update),
        "map_update_source_file": source_file(map_update),
        "map_update_source_sha256": (
            hashlib.sha256(update_source.encode("utf-8")).hexdigest()
            if update_source
            else ""
        ),
        "map_iter_rules_symbol": symbol(map_iter_rules),
        "map_iter_rules_source_file": source_file(map_iter_rules),
        "map_iter_rules_source_sha256": (
            hashlib.sha256(iter_source.encode("utf-8")).hexdigest()
            if iter_source
            else ""
        ),
        "map_adapter_match_symbol": symbol(adapter_match),
        "map_adapter_match_source_file": source_file(adapter_match),
        "map_adapter_match_source_sha256": (
            hashlib.sha256(match_source.encode("utf-8")).hexdigest()
            if match_source
            else ""
        ),
        "map_stable_sort_proven": stable_sort_detected,
        "map_iter_rules_order_proven": (
            iter_calls_update and iter_returns_rules
        ),
        "adapter_first_match_return_proven": (
            adapter_iterates_rules
            and adapter_calls_rule_match
            and adapter_returns_rule
        ),
        "ordering_key_methods_executed": True,
        "request_match_executed": False,
        "source_executed": False,
        "matcher_executed": False,
    }


def _framework_route_rules(
    routing_map,
    module_order,
    *,
    ordering_paths=frozenset(),
):
    module_positions = {
        module: index for index, module in enumerate(module_order)
    }
    final_rules = list(routing_map.iter_rules())
    routing_map_id = _routing_map_identity(routing_map, final_rules)
    rows = []
    for rule_order, rule in enumerate(final_rules):
        endpoint = getattr(rule, "endpoint", None)
        bound_method = getattr(endpoint, "func", None)
        controller = getattr(bound_method, "__self__", None)
        controller_class = type(controller) if controller is not None else None
        implementation = (
            getattr(endpoint, "original_endpoint", None)
            or getattr(bound_method, "original_endpoint", None)
            or bound_method
            or endpoint
        )
        implementation_module = text(getattr(implementation, "__module__", ""))
        parts = implementation_module.split(".")
        addon_module = (
            parts[2]
            if len(parts) > 2 and parts[:2] == ["odoo", "addons"]
            else ""
        )
        methods = sorted(
            method
            for method in (getattr(rule, "methods", None) or [])
            if method != "OPTIONS"
        )
        routing = getattr(endpoint, "routing", {}) or {}
        route = text(getattr(rule, "rule", ""))
        route_type = text(routing.get("type") or "http")
        build_only = bool(getattr(rule, "build_only", False))
        compiled_matcher = getattr(rule, "_regex", None)
        ordering_key_method = getattr(rule, "match_compare_key", None)
        execute_ordering_key = (
            route in ordering_paths and callable(ordering_key_method)
        )
        ordering_key = (
            repr(ordering_key_method()) if execute_ordering_key else ""
        )
        rows.append(
            {
                "routing_map_id": routing_map_id,
                "routing_map_class": symbol(type(routing_map)),
                "routing_map_order": rule_order,
                "route": route,
                "methods": methods,
                "endpoint_symbol": symbol(endpoint),
                "effective_implementation": symbol(implementation),
                "source_file": source_file(implementation),
                "module": addon_module,
                "module_order": module_positions.get(addon_module, -1),
                "controller_class": symbol(controller_class),
                "controller_mro": [
                    symbol(owner)
                    for owner in (getattr(controller_class, "__mro__", ()) or ())
                    if symbol(owner)
                ],
                "controller_registration_order": rule_order,
                "route_surface": _route_surface(
                    route,
                    route_type,
                    addon_module,
                    build_only,
                ),
                "auth": text(routing.get("auth") or "user"),
                "type": route_type,
                "csrf": bool(routing.get("csrf", True)),
                "cors": text(routing.get("cors")),
                "match_dimensions": {
                    "route": route,
                    "methods": methods,
                    "host": text(getattr(rule, "host", "")),
                    "subdomain": text(getattr(rule, "subdomain", "")),
                    "converters": _converter_metadata(rule),
                    "compiled_pattern": text(
                        getattr(compiled_matcher, "pattern", "")
                    ),
                    "arguments": sorted(getattr(rule, "arguments", None) or []),
                    "defaults": json_safe(getattr(rule, "defaults", None) or {}),
                    "redirect_to": json_safe(getattr(rule, "redirect_to", None)),
                    "alias": bool(getattr(rule, "alias", False)),
                    "build_only": build_only,
                    "websocket": bool(getattr(rule, "websocket", False)),
                    "strict_slashes": bool(getattr(rule, "strict_slashes", False)),
                    "merge_slashes": bool(getattr(rule, "merge_slashes", False)),
                },
                "dispatch_dimensions": {
                    "endpoint": symbol(endpoint),
                    "effective_implementation": symbol(implementation),
                    "type": route_type,
                },
                "security_dimensions": {
                    "auth": text(routing.get("auth") or "user"),
                    "csrf": bool(routing.get("csrf", True)),
                    "cors": text(routing.get("cors")),
                    "readonly": bool(routing.get("readonly", False)),
                    "save_session": bool(routing.get("save_session", True)),
                },
                "ordering_key_repr": ordering_key,
                "ordering_key_executed": execute_ordering_key,
                "endpoint_executed": False,
                "matcher_executed": False,
            }
        )
    return rows


def route_policies():
    http = importlib.import_module("odoo.http")
    root = getattr(http, "Controller")
    classes = []
    seen = set()

    def add_candidate(value):
        if isinstance(value, type):
            try:
                is_controller = issubclass(value, root)
            except TypeError:
                is_controller = False
            if is_controller and value is not root and value not in seen:
                seen.add(value)
                classes.append(value)
            return
        if isinstance(value, dict):
            for item in value.values():
                add_candidate(item)
            return
        if isinstance(value, (list, tuple, set, frozenset)):
            for item in value:
                add_candidate(item)

    controller_registry = getattr(http, "controllers_per_module", {}) or {}
    add_candidate(controller_registry)
    pending = list(root.__subclasses__())
    while pending:
        controller = pending.pop()
        add_candidate(controller)
        pending.extend(controller.__subclasses__())
    installed_route_modules = sorted(
        set(getattr(env.registry, "_init_modules", set()) or set())
        | set(getattr(odoo.conf, "server_wide_modules", []) or [])
    )
    routing_map = env["ir.http"].routing_map()
    framework_rules = _framework_route_rules(
        routing_map,
        installed_route_modules,
    )
    matcher_order_proof = {
        "analysis_stage": "NOT_RUN_BEFORE_TRUE_CONFLICT_GATE",
        "source_executed": False,
        "matcher_executed": False,
    }
    payload = ROUTE_POLICY_METADATA.project_route_policies(
        classes,
        source_file_resolver=source_file,
        framework_rules=framework_rules,
        matcher_order_proof=matcher_order_proof,
    )
    true_conflict_paths = {
        item["route_path"]
        for item in payload.get("collisions", [])
        if item.get("conflict_classification") == "TRUE_RUNTIME_CONFLICT"
    }
    if true_conflict_paths:
        matcher_order_proof = _matcher_order_proof(routing_map)
        framework_rules = _framework_route_rules(
            routing_map,
            installed_route_modules,
            ordering_paths=true_conflict_paths,
        )
        payload = ROUTE_POLICY_METADATA.project_route_policies(
            classes,
            source_file_resolver=source_file,
            framework_rules=framework_rules,
            matcher_order_proof=matcher_order_proof,
        )
    payload["enumeration_source"] = (
        "odoo.http.controllers_per_module plus loaded Controller subclasses"
    )
    payload["controller_registry_module_count"] = (
        len(controller_registry) if isinstance(controller_registry, dict) else 0
    )
    payload["controller_class_count"] = len(classes)
    payload["module_load_order"] = installed_route_modules
    payload["framework_routing_map_read"] = True
    payload["business_model_methods_executed"] = False
    return payload


def generic_api_policies(handler_rows, alias_rows, model_rows):
    policy_maps = importlib.import_module(
        "odoo.addons.smart_construction_core.core_extension_policy_maps"
    )
    unlink_policies = {
        str(model_name): json_safe(policy)
        for model_name, policy in (
            getattr(policy_maps, "API_DATA_UNLINK_POLICIES", {}) or {}
        ).items()
    }
    unlink_policies["project.project"] = {
        "allowed": True,
        "delete_mode": "unlink",
        "dependency_guard": "project.project._raise_project_unlink_blockers",
        "reason_code": "PROJECT_MASTER_DELETE_ALLOWED",
        "source": "smart_construction_core",
    }
    return GENERIC_POLICY_METADATA.build_generic_policy_metadata(
        handlers=handler_rows,
        aliases=alias_rows,
        runtime_models=model_rows["runtime_models"],
        project_fields=model_rows["project_field_definitions"],
        rpc_candidates=model_rows["public_rpc_candidates"],
        write_allowlist=json_safe(
            getattr(policy_maps, "API_DATA_WRITE_ALLOWLIST", {}) or {}
        ),
        unlink_policies=unlink_policies,
        mutation_policies=json_safe(
            getattr(policy_maps, "API_DATA_MUTATION_POLICIES", {}) or {}
        ),
        source_symbols={
            "write_allowlist": (
                "addons/smart_construction_core/core_extension_policy_maps.py:"
                "API_DATA_WRITE_ALLOWLIST"
            ),
            "mutation": (
                "addons/smart_construction_core/core_extension_policy_maps.py:"
                "API_DATA_MUTATION_POLICIES"
            ),
            "create_execution": (
                "addons/smart_construction_core/core_extension_policy_accessors.py:"
                "get_api_data_create_execution_policy_contribution"
            ),
            "unlink": (
                "addons/smart_construction_core/core_extension_policy_maps.py:"
                "API_DATA_UNLINK_POLICIES"
            ),
            "execute_button": (
                "addons/smart_construction_core/core_extension.py:"
                "smart_core_build_portal_execute_button_contract"
            ),
        },
    )


def model_metadata():
    runtime_models = []
    project_models = []
    project_fields = []
    defaults = []
    overrides = []
    rpc_candidates = []
    for model_name in sorted(env.registry.models):
        model = env.registry.models[model_name]
        module = text(getattr(model, "__module__", ""))
        fields = getattr(model, "_fields", {}) or {}
        runtime_models.append(
            {
                "model": model_name,
                "class": symbol(model),
                "module": module,
                "source_file": source_file(model),
                "abstract": bool(getattr(model, "_abstract", False)),
                "transient": bool(getattr(model, "_transient", False)),
                "field_names": sorted(fields),
            }
        )
        project_named_fields = [
            field_name
            for field_name in sorted(fields)
            if field_name
            in {
                "project_id",
                "project_ids",
                "selected_project_id",
                "current_project_id",
                "default_project_id",
                "active_project_id",
                "allowed_project_ids",
            }
        ]
        if project_named_fields:
            project_models.append(model_name)
        for field_name in project_named_fields:
            field = fields[field_name]
            default = getattr(field, "default", None)
            project_fields.append(
                {
                    "model": model_name,
                    "field": field_name,
                    "type": text(getattr(field, "type", "")),
                    "comodel_name": text(getattr(field, "comodel_name", "")),
                    "required": bool(getattr(field, "required", False)),
                    "readonly": bool(getattr(field, "readonly", False)),
                    "definition_module": text(
                        getattr(field, "_module", "")
                        or getattr(field, "module", "")
                    ),
                    "default_symbol": symbol(default) if callable(default) else "",
                    "default_literal": (
                        json_safe(default) if default is not None and not callable(default) else None
                    ),
                }
            )
            if default is not None:
                defaults.append(
                    {
                        "model": model_name,
                        "field": field_name,
                        "callable": callable(default),
                        "source": symbol(default) if callable(default) else "literal",
                        "source_file": source_file(default) if callable(default) else "",
                    }
                )
        for method_name in ("create", "write", "unlink", "default_get"):
            method = getattr(model, method_name, None)
            owner = getattr(method, "__func__", method)
            if callable(owner):
                overrides.append(
                    {
                        "model": model_name,
                        "method": method_name,
                        "symbol": symbol(owner),
                        "source_file": source_file(owner),
                    }
                )
        public = []
        for method_name in sorted(dir(model)):
            if method_name.startswith("_"):
                continue
            candidate = getattr(model, method_name, None)
            if not callable(candidate):
                continue
            api_kind = text(getattr(candidate, "_api", ""))
            public.append(
                {
                    "method": method_name,
                    "symbol": symbol(candidate),
                    "api": api_kind,
                }
            )
        rpc_candidates.append({"model": model_name, "methods": public})
    return {
        "runtime_models": runtime_models,
        "project_models": project_models,
        "project_field_definitions": project_fields,
        "model_default_sources": defaults,
        "overridden_create_write_unlink": overrides,
        "public_rpc_candidates": rpc_candidates,
    }


module_rows = installed_modules()
extension_rows = extension_modules()
extension_details, extension_unresolved = extension_contributions(extension_rows)
handlers, aliases = handler_registry()
models = model_metadata()
routes = route_policies()

payload = {
    "run_metadata": {
        "run_id": RUN_ID,
        "git_head": GIT_HEAD,
        "git_tree": GIT_TREE,
        "database_role": "ephemeral_noncustomer_registry_audit",
        "modules": MODULES,
        "business_handlers_executed": False,
        "business_model_methods_executed": False,
        "default_get_executed": False,
        "onchange_executed": False,
        "compute_executed": False,
    },
    "installed_modules": module_rows,
    "extension_modules": extension_rows,
    "extension_contributions": extension_details,
    "handler_registry": handlers,
    "aliases": aliases,
    "route_policies": routes,
    "generic_api_policies": generic_api_policies(handlers, aliases, models),
    **models,
    "unresolved_runtime_nodes": sorted(
        [
            *extension_unresolved,
            *(
                [
                    {
                        "kind": "route_policy_effective_winner",
                        "reason": (
                            f"{sum(item.get('enumeration_status') == 'UNRESOLVED_DYNAMIC' for item in (routes.get('collisions') or []))} "
                            "duplicate route/method "
                            "shapes require noninvasive routing-map order proof"
                        ),
                    }
                ]
                if any(
                    item.get("enumeration_status") == "UNRESOLVED_DYNAMIC"
                    for item in (routes.get("collisions") or [])
                )
                else []
            ),
            *(
                [
                    {
                        "kind": "route_policy_decorator_path",
                        "reason": (
                            f"{len(routes.get('unresolved_items') or [])} decorated methods "
                            "lack a statically recoverable route path"
                        ),
                    }
                ]
                if routes.get("unresolved_items")
                else []
            ),
            {
                "kind": "generic_api_dynamic_policy_values",
                "reason": (
                    "effective static policy metadata is exported per registry key; "
                    "request-, ACL-, record-rule-, and business-configuration-dependent "
                    "items remain explicit per-policy unresolved records"
                ),
            },
            {
                "kind": "public_rpc_reachability",
                "reason": "candidates exported; reachability requires source/decorator classification",
            },
        ],
        key=lambda row: (text(row.get("kind")), text(row.get("module")), text(row.get("reason"))),
    ),
}

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
temporary = OUTPUT.with_suffix(".tmp")
temporary.write_text(
    json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
temporary.replace(OUTPUT)
