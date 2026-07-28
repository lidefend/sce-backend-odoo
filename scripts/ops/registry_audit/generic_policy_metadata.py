"""Pure metadata projection for the governed registry audit.

The functions in this module never call an Odoo handler, policy predicate, or
model method.  Callers provide already-loaded class/registry metadata and
static policy containers; this module only normalizes and combines them.
"""

from __future__ import annotations

from typing import Any


GENERIC_INTENTS = (
    "api.data",
    "api.data.batch",
    "api.data.create",
    "api.data.unlink",
    "api.data.write",
    "api.onchange",
    "execute_button",
)

POLICY_REQUIRED_KEYS = {
    "generic_policy_id",
    "registry_key",
    "contribution_module",
    "source_file",
    "source_symbol",
    "canonical_handler",
    "aliases",
    "effective_implementation",
    "replaced_implementations",
    "load_order_index",
    "load_order_evidence",
    "policy_provider_type",
    "policy_metadata_source",
    "policy_metadata_statically_readable",
    "model_selector_type",
    "allowed_models",
    "denied_models",
    "default_model_decision",
    "model_operation_policies",
    "field_policies",
    "method_policies",
    "domain_policy",
    "context_policy",
    "project_id_input_sources",
    "model_default_injection",
    "dynamic_generator_source",
    "dynamic_inputs",
    "enumeration_status",
    "unresolved_reason",
}


def _strings(values) -> list[str]:
    return sorted(
        {
            str(value or "").strip()
            for value in (values or [])
            if str(value or "").strip()
        }
    )


def _mapping(value) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _canonical_aliases(aliases: list[dict[str, Any]], intent: str) -> tuple[str, list[str]]:
    canonical = intent
    for row in aliases:
        if str(row.get("alias") or "") == intent:
            canonical = str(row.get("canonical_intent") or intent)
            break
    names = sorted(
        str(row.get("alias") or "")
        for row in aliases
        if str(row.get("canonical_intent") or "") == canonical
        and str(row.get("alias") or "")
    )
    return canonical, names


def _base_policy(
    *,
    index: int,
    handler: dict[str, Any],
    aliases: list[dict[str, Any]],
    selector: str,
    allowed_models: list[str],
    denied_models: list[str] | None = None,
    default_decision: str,
    operations: dict[str, str],
    fields: dict[str, Any],
    methods: dict[str, Any],
    domain_policy: dict[str, Any],
    context_policy: dict[str, Any],
    provider_type: str,
    metadata_sources: list[str],
    dynamic_source: str = "",
    dynamic_inputs: list[str] | None = None,
    unresolved_reason: str = "",
) -> dict[str, Any]:
    intent = str(handler.get("intent") or "")
    canonical, alias_names = _canonical_aliases(aliases, intent)
    status = "PARTIALLY_ENUMERATED" if unresolved_reason else "ENUMERATED"
    record = {
        "generic_policy_id": f"GENERIC-POLICY-{index:03d}",
        "registry_key": intent,
        "contribution_module": (
            str(handler.get("handler_class") or "")
            .split(".handlers.", 1)[0]
            .rsplit(".", 1)[-1]
        ),
        "source_file": str(handler.get("source_file") or ""),
        "source_symbol": str(handler.get("handler_class") or ""),
        "canonical_handler": canonical,
        "aliases": alias_names,
        "effective_implementation": str(handler.get("handler_class") or ""),
        "replaced_implementations": [],
        "load_order_index": int(handler.get("registration_order") or index),
        "load_order_evidence": "effective HANDLER_REGISTRY insertion order",
        "policy_provider_type": provider_type,
        "policy_metadata_source": sorted(metadata_sources),
        "policy_metadata_statically_readable": True,
        "model_selector_type": selector,
        "allowed_models": sorted(allowed_models),
        "denied_models": sorted(denied_models or []),
        "default_model_decision": default_decision,
        "model_operation_policies": dict(sorted(operations.items())),
        "field_policies": fields,
        "method_policies": methods,
        "domain_policy": domain_policy,
        "context_policy": context_policy,
        "project_id_input_sources": [
            "params.current_project_id",
            "params.project_id",
            "params.context.current_project_id",
            "params.context.default_project_id",
            "request.context.current_project_id",
            "request.context.default_project_id",
        ],
        "model_default_injection": {
            "supported": intent in {"api.data", "api.data.create", "api.data.write", "api.onchange"},
            "sources": ["default_get", "context.default_*", "field.default"],
            "executed_during_audit": False,
        },
        "dynamic_generator_source": dynamic_source,
        "dynamic_inputs": _strings(dynamic_inputs),
        "enumeration_status": status,
        "unresolved_reason": unresolved_reason,
    }
    missing = POLICY_REQUIRED_KEYS - set(record)
    if missing:
        raise ValueError(f"generic policy record missing keys: {sorted(missing)}")
    return record


def build_generic_policy_metadata(
    *,
    handlers: list[dict[str, Any]],
    aliases: list[dict[str, Any]],
    runtime_models: list[dict[str, Any]],
    project_fields: list[dict[str, Any]],
    rpc_candidates: list[dict[str, Any]],
    write_allowlist: dict[str, Any],
    unlink_policies: dict[str, Any],
    mutation_policies: dict[str, Any],
    source_symbols: dict[str, str],
) -> dict[str, Any]:
    """Return deterministic effective generic policy metadata.

    Runtime ACLs, record rules, company-specific manual ``x_`` fields, and
    callable button predicates are deliberately described as per-object
    unresolved components rather than executed.
    """

    handler_map = {
        str(row.get("intent") or ""): row
        for row in handlers
        if str(row.get("intent") or "") in GENERIC_INTENTS
    }
    model_rows = {
        str(row.get("model") or ""): row
        for row in runtime_models
        if str(row.get("model") or "")
    }
    all_models = sorted(model_rows)
    write_map = {
        str(model): _strings(fields)
        for model, fields in _mapping(write_allowlist).items()
        if str(model or "").strip()
    }
    unlink_map = {
        str(model): _mapping(policy)
        for model, policy in _mapping(unlink_policies).items()
        if str(model or "").strip()
    }
    mutation_map = {
        str(model): _mapping(policy)
        for model, policy in _mapping(mutation_policies).items()
        if str(model or "").strip()
    }

    records = []
    for index, intent in enumerate(GENERIC_INTENTS, 1):
        handler = handler_map.get(intent)
        if not handler:
            continue
        common_domain = {
            "client_domain_supported": intent in {"api.data"},
            "domain_raw_supported": intent == "api.data",
            "record_scope_domain_applied": intent in {
                "api.data",
                "api.data.batch",
                "api.data.create",
                "api.data.write",
                "api.data.unlink",
            },
            "audit_execution": False,
        }
        common_context = {
            "client_context_supported": True,
            "merge_order": ["caller_env", "request_envelope", "payload"],
            "company_scope_normalized": True,
            "project_scope_keys_normalized": True,
            "audit_execution": False,
        }
        if intent == "api.data":
            record = _base_policy(
                index=index,
                handler=handler,
                aliases=aliases,
                selector="DEFAULT_ALLOW",
                allowed_models=all_models,
                denied_models=[],
                default_decision="ALLOW_REGISTERED_MODEL_SUBJECT_TO_ACL_AND_RECORD_RULE",
                operations={
                    "create": "ALLOWED_SUBJECT_TO_POLICY_ACL_RECORD_RULE",
                    "default_get": "ALLOWED_SUBJECT_TO_ACL",
                    "export_csv": "ALLOWED_SUBJECT_TO_ACL_RECORD_RULE",
                    "read": "ALLOWED_SUBJECT_TO_ACL_RECORD_RULE",
                    "search": "ALLOWED_SUBJECT_TO_ACL_RECORD_RULE",
                    "search_count": "ALLOWED_SUBJECT_TO_ACL_RECORD_RULE",
                    "search_read": "ALLOWED_SUBJECT_TO_ACL_RECORD_RULE",
                    "write": "ALLOWED_SUBJECT_TO_POLICY_ACL_RECORD_RULE",
                },
                fields={
                    "read": "REGISTERED_FIELDS_FILTERED_BY_FIELD_ACCESS",
                    "create": "REGISTERED_FIELDS_FILTERED_BY_ORM",
                    "write": "REGISTERED_FIELDS_FILTERED_BY_ORM",
                    "return": "REQUESTED_READABLE_FIELDS",
                },
                methods={"default_decision": "DENY", "allowed_methods": [], "denied_methods": ["*"]},
                domain_policy=common_domain,
                context_policy=common_context,
                provider_type="COMPOSED_POLICY",
                metadata_sources=[
                    "addons/smart_core/handlers/api_data.py",
                    source_symbols.get("mutation", ""),
                    source_symbols.get("create_execution", ""),
                ],
                dynamic_source=source_symbols.get("create_execution", ""),
                dynamic_inputs=["model", "vals", "context", "params", "ACL", "record_rules"],
                unresolved_reason=(
                    "account.tax quick-create execution policy and runtime ACL/record-rule "
                    "decisions require request or business-record inputs and were not executed"
                ),
            )
        elif intent == "api.data.batch":
            record = _base_policy(
                index=index,
                handler=handler,
                aliases=aliases,
                selector="DEFAULT_ALLOW",
                allowed_models=all_models,
                denied_models=[],
                default_decision="ALLOW_REGISTERED_MODEL_SUBJECT_TO_WRITE_ACL_AND_RECORD_RULE",
                operations={"write": "ALLOWED_SUBJECT_TO_ACL_RECORD_RULE"},
                fields={"write": "REGISTERED_FIELDS_FILTERED_BY_ORM"},
                methods={"default_decision": "DENY", "allowed_methods": [], "denied_methods": ["*"]},
                domain_policy=common_domain,
                context_policy=common_context,
                provider_type="INHERITED_POLICY",
                metadata_sources=["addons/smart_core/handlers/api_data_batch.py"],
                dynamic_inputs=["ACL", "record_rules"],
                unresolved_reason="runtime ACL and record-rule decisions were not executed",
            )
        elif intent in {"api.data.create", "api.data.write"}:
            operation = "create" if intent == "api.data.create" else "write"
            record = _base_policy(
                index=index,
                handler=handler,
                aliases=aliases,
                selector="EXPLICIT_ALLOWLIST",
                allowed_models=sorted(write_map),
                denied_models=sorted(set(all_models) - set(write_map)),
                default_decision="DENY",
                operations={operation: "ALLOWED_FOR_EXPLICIT_MODEL_AND_FIELD_ALLOWLIST"},
                fields={
                    operation: write_map,
                    "dynamic_manual_fields": "ACTIVE_VISIBLE_COMPANY_SCOPED_X_FIELDS",
                },
                methods={"default_decision": "DENY", "allowed_methods": [], "denied_methods": ["*"]},
                domain_policy=common_domain,
                context_policy=common_context,
                provider_type="COMPOSED_POLICY",
                metadata_sources=[
                    "addons/smart_core/handlers/api_data_write.py:ApiDataWriteHandler.ALLOWED_MODELS",
                    source_symbols.get("write_allowlist", ""),
                ],
                dynamic_source=(
                    "addons/smart_core/handlers/api_data_write.py:"
                    "ApiDataWriteHandler._merge_business_config_custom_fields"
                ),
                dynamic_inputs=[
                    "ui.form.field.policy company-scoped rows",
                    "ir.model.fields manual x_ fields",
                ],
                unresolved_reason=(
                    "company-scoped active manual x_ fields require business configuration "
                    "table reads and are reported per allowlisted model without being queried"
                ),
            )
        elif intent == "api.data.unlink":
            record = _base_policy(
                index=index,
                handler=handler,
                aliases=aliases,
                selector="EXPLICIT_ALLOWLIST",
                allowed_models=sorted(unlink_map),
                denied_models=sorted(set(all_models) - set(unlink_map)),
                default_decision="DENY",
                operations={"unlink": "ALLOWED_SUBJECT_TO_DELETE_POLICY_ACL_RECORD_RULE"},
                fields={"read_for_policy": _strings(
                    policy.get("state_field")
                    for policy in unlink_map.values()
                    if policy.get("state_field")
                )},
                methods={"default_decision": "DENY", "allowed_methods": [], "denied_methods": ["*"]},
                domain_policy=common_domain,
                context_policy=common_context,
                provider_type="EXPLICIT_ALLOWLIST",
                metadata_sources=[
                    "addons/smart_core/handlers/api_data_unlink.py",
                    source_symbols.get("unlink", ""),
                ],
                dynamic_inputs=["record state", "ACL", "record_rules"],
                unresolved_reason="record state, ACL, and record-rule decisions were not executed",
            )
        elif intent == "api.onchange":
            record = _base_policy(
                index=index,
                handler=handler,
                aliases=aliases,
                selector="DEFAULT_ALLOW",
                allowed_models=all_models,
                denied_models=[],
                default_decision="ALLOW_REGISTERED_MODEL_SUBJECT_TO_ACL_AND_SCOPE",
                operations={"onchange": "ALLOWED_FOR_REGISTERED_MODEL_FIELDS"},
                fields={
                    "input": "REGISTERED_FIELDS",
                    "output": "REGISTERED_FIELDS",
                },
                methods={
                    "default_decision": "PREDICATE",
                    "allowed_methods": ["declared onchange methods"],
                    "denied_methods": [],
                },
                domain_policy=common_domain,
                context_policy=common_context,
                provider_type="PREDICATE",
                metadata_sources=["addons/smart_core/handlers/api_onchange.py"],
                dynamic_source="Odoo model _onchange_methods metadata",
                dynamic_inputs=["changed_fields", "values", "onchange method graph"],
                unresolved_reason="onchange methods were inventoried but never invoked",
            )
        else:
            record = _base_policy(
                index=index,
                handler=handler,
                aliases=aliases,
                selector="DEFAULT_ALLOW",
                allowed_models=all_models,
                denied_models=[],
                default_decision="ALLOW_REGISTERED_MODEL_SUBJECT_TO_METHOD_AND_ACCESS_PREDICATES",
                operations={"method_call": "PREDICATE"},
                fields={"read_for_scope": ["id", "project_id when present"]},
                methods={
                    "default_decision": "PREDICATE",
                    "allowed_methods": "PUBLIC_CALLABLE_CANDIDATES_SUBJECT_TO_RUNTIME_ACCESS",
                    "denied_methods": [],
                },
                domain_policy=common_domain,
                context_policy=common_context,
                provider_type="PREDICATE",
                metadata_sources=[
                    "addons/smart_core/handlers/execute_button.py",
                    source_symbols.get("execute_button", ""),
                ],
                dynamic_source=source_symbols.get("execute_button", ""),
                dynamic_inputs=["model", "record ids", "method name", "button type", "ACL", "record_rules"],
                unresolved_reason=(
                    "method callability and access depend on request, record, and method metadata; "
                    "candidates are exported without invoking them"
                ),
            )
        records.append(record)

    rpc_by_model = {
        str(row.get("model") or ""): [
            {
                "method": str(method.get("method") or ""),
                "status": "UNRESOLVED_DYNAMIC",
                "policy_source": "execute_button method predicate",
            }
            for method in (row.get("methods") or [])
            if str(method.get("method") or "")
        ]
        for row in rpc_candidates
    }
    project_field_map: dict[str, list[dict[str, Any]]] = {}
    for field in project_fields:
        project_field_map.setdefault(str(field.get("model") or ""), []).append(field)

    project_model_decisions = []
    project_field_decisions = []
    for model in sorted(project_field_map):
        row = model_rows.get(model, {})
        field_names = _strings(row.get("field_names"))
        project_names = _strings(
            field.get("field")
            for field in project_field_map[model]
        )
        explicit_write_fields = write_map.get(model, [])
        operations = {
            "create": "ALLOWED_VIA_API_DATA_SUBJECT_TO_ACL_RECORD_RULE",
            "default_get": "ALLOWED_VIA_API_DATA_SUBJECT_TO_ACL",
            "method_call": "UNRESOLVED_DYNAMIC_VIA_EXECUTE_BUTTON",
            "onchange": "ALLOWED_VIA_API_ONCHANGE_SUBJECT_TO_SCOPE",
            "read": "ALLOWED_VIA_API_DATA_SUBJECT_TO_ACL_RECORD_RULE",
            "search": "ALLOWED_VIA_API_DATA_SUBJECT_TO_ACL_RECORD_RULE",
            "search_count": "ALLOWED_VIA_API_DATA_SUBJECT_TO_ACL_RECORD_RULE",
            "write": "ALLOWED_VIA_API_DATA_SUBJECT_TO_ACL_RECORD_RULE",
        }
        if model in unlink_map:
            operations["unlink"] = "ALLOWED_VIA_API_DATA_UNLINK_SUBJECT_TO_POLICY_ACL_RECORD_RULE"
        project_model_decisions.append(
            {
                "model": model,
                "generic_api_reachability": "PARTIALLY_ALLOWED",
                "effective_operations": operations,
                "readable_fields": field_names,
                "creatable_fields": field_names,
                "writable_fields": field_names,
                "explicit_write_handler_fields": explicit_write_fields,
                "callable_methods": rpc_by_model.get(model, []),
                "project_fields": project_names,
                "policy_source": [
                    "api.data DEFAULT_ALLOW registered-model policy",
                    "api.onchange DEFAULT_ALLOW registered-model policy",
                    "execute_button PREDICATE method policy",
                ],
                "policy_decision_trace": [
                    "model exists in runtime registry",
                    "api.data accepts registered model",
                    "requested fields are intersected with model fields",
                    "ACL/record rules remain runtime authority",
                ],
                "unresolved_components": [
                    "runtime ACL and record-rule result",
                    "execute_button method callability",
                    "company-scoped manual x_ field contribution",
                ],
            }
        )
        for field in sorted(project_field_map[model], key=lambda item: str(item.get("field") or "")):
            name = str(field.get("field") or "")
            project_field_decisions.append(
                {
                    "model": model,
                    "field": name,
                    "readable": True,
                    "creatable": True,
                    "writable": True,
                    "dedicated_write_handler_allowed": name in explicit_write_fields,
                    "policy_source": "api.data registered-field filtering",
                    "unresolved_components": ["runtime ACL, record rules, and ORM field semantics"],
                }
            )

    unresolved = []
    for record in records:
        if record["enumeration_status"] != "ENUMERATED":
            unresolved.append(
                {
                    "registry_key": record["registry_key"],
                    "provider_source": record["policy_metadata_source"],
                    "generator_symbol": record["dynamic_generator_source"],
                    "dynamic_inputs": record["dynamic_inputs"],
                    "affected_models": record["allowed_models"],
                    "affected_operations": sorted(record["model_operation_policies"]),
                    "reason": record["unresolved_reason"],
                }
            )

    return {
        "schema_version": 2,
        "policy_records": records,
        "project_model_decisions": project_model_decisions,
        "project_field_decisions": project_field_decisions,
        "dynamic_unresolved_items": unresolved,
        "static_policy_sources": {
            "write_allowlist": write_map,
            "unlink_policies": unlink_map,
            "mutation_policies": mutation_map,
        },
        "business_handlers_executed": False,
        "business_model_methods_executed": False,
        "policy_predicates_executed": False,
        "business_data_read": False,
    }
