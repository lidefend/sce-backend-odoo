#!/usr/bin/env python3
"""Guard the v2+ backend assembler without requiring an Odoo runtime."""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import sys
import types
from copy import deepcopy
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
CORE_DIR = ROOT / "addons/smart_core/core"
ASSEMBLER_PATH = ROOT / "addons/smart_core/core/unified_page_contract_v2_assembler.py"
P1_PROJECT_LAYOUT_PATH = ROOT / "addons/smart_construction_core/core_extension_project_layout.py"

# The assembled-contract response cache serves a whole assembled contract, so a
# code change that is not reflected in its version literal keeps the previous
# assembly on the delivery face (the layout declaration this round adds would
# never reach a client that already has a cached contract).  The pin below binds
# the version literal the handler serves to a digest of the code that produces
# the assembled contract; on drift this guard fails closed and the author
# re-pins both values deliberately instead of the cache hiding the change.
ASSEMBLED_CACHE_VERSION = "ui-contract-v2-analysis-field-metadata-v1"
ASSEMBLED_CACHE_HANDLER = "addons/smart_core/handlers/ui_contract_v2.py"
ASSEMBLED_CACHE_MODULE = "addons/smart_core/utils/load_contract_response_cache.py"
ASSEMBLED_CACHE_INPUTS = (
    ASSEMBLED_CACHE_HANDLER,
    ASSEMBLED_CACHE_MODULE,
    "addons/smart_core/core/node_component_validation.py",
    "addons/smart_core/core/native_advisory.py",
    "addons/smart_core/core/node_component_capabilities.py",
    "addons/smart_core/core/record_error_proof.py",
    "addons/smart_core/core/field_presentation_usage.py",
    "addons/smart_core/core/unified_page_contract_v2_assembler.py",
    "addons/smart_core/handlers/ui_contract_v2_projection.py",
    "addons/smart_core/core/unified_page_contract_v2_client.py",
    # The v2 handler assembles the page through ``PageAssembler`` itself: business
    # category policy, relation entry contracts and the relation search-dialog
    # materialization are injected into the contract before it is assembled and
    # cached, so an edit there changes the served assembled contract. The
    # pre-assembly source contract is a different layer, covered by the persisted
    # runtime source asset token instead of this assembly-code fingerprint.
    "addons/smart_core/app_config_engine/services/assemblers/page_assembler.py",
    # The assembler resolves component keys through the contract registry, so the
    # resolver and its generated carrier决定 assembled contract 的组件键。它们是运行时
    # 输入，必须一并纳入指纹；否则声明改动会留下被缓存的旧装配。
    "addons/smart_core/core/contract_runtime/semantic_resolver.py",
    "addons/smart_core/core/contract_runtime/semantic_registry_generated.py",
    # The resolver also annotates a field with the entity semantics projected out
    # of the parsed model/view facts, so that carrier changes the assembled
    # component keys too and has to be part of the same fingerprint.
    "addons/smart_core/core/contract_runtime/domain_field_semantics_generated.py",
    # The assembler imports the permission resolver directly, and the collection
    # capabilities it publishes are produced by the governance surfaces through the
    # single capability rule.  All of them are runtime inputs of the assembled
    # contract, so a change to any of them must invalidate the served cache.
    "addons/smart_core/core/unified_page_contract_v2_permissions.py",
    "addons/smart_core/utils/collection_action_capability.py",
    "addons/smart_core/utils/contract_governance.py",
    "addons/smart_core/utils/contract_governance_list_surface.py",
    "addons/smart_core/utils/contract_governance_user_surface.py",
)
ASSEMBLED_CACHE_INPUTS_SHA256 = "a226242ed1f542e0c4534a16a4081e44d3c884ed63021bd3832882b6f3be873d"

# Cache layers are deliberately separated:
#   * dynamic per-request computation owns record facts, permission verdicts and
#     entitlement;
#   * the process-local hot cache may keep the record-independent source and,
#     only for record-free requests, the assembled contract;
#   * the persistent asset stores the source projection only;
#   * the browser may cache only a record-free create contract.
# The checks below fail closed if a future change lets a record-bound contract
# enter any of those layers.
FRONTEND_CONTRACT_CLIENT = "frontend/apps/web/src/app/contracts/v2/client.ts"


def _assembled_cache_digest() -> str:
    digest = hashlib.sha256()
    digest.update(ASSEMBLED_CACHE_VERSION.encode("utf-8"))
    for relative in ASSEMBLED_CACHE_INPUTS:
        digest.update(relative.encode("utf-8"))
        digest.update((ROOT / relative).read_bytes())
    return digest.hexdigest()


def check_assembled_contract_cache_pin(errors: list[str]) -> None:
    handler_path = ROOT / ASSEMBLED_CACHE_HANDLER
    if not handler_path.is_file():
        fail(errors, f"assembled contract cache handler is missing: {ASSEMBLED_CACHE_HANDLER}")
        return
    handler_text = handler_path.read_text(encoding="utf-8")
    if f'ASSEMBLED_CONTRACT_CACHE_VERSION = "{ASSEMBLED_CACHE_VERSION}"' not in handler_text:
        fail(
            errors,
            "the handler does not serve the recorded assembled contract cache version "
            f"{ASSEMBLED_CACHE_VERSION}: re-pin ASSEMBLED_CACHE_VERSION here and in "
            f"{ASSEMBLED_CACHE_HANDLER}",
        )


def _enclosing_if_test(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> str:
    current = parents.get(node)
    while current is not None:
        if isinstance(current, ast.If):
            return ast.unparse(current.test)
        current = parents.get(current)
    return ""


def _call_attr_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            names.add(node.func.attr)
    return names


def _function_def(tree: ast.AST, name: str) -> ast.FunctionDef | None:
    return next(
        (
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == name
        ),
        None,
    )


def _call_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Attribute):
            names.add(node.func.attr)
        elif isinstance(node.func, ast.Name):
            names.add(node.func.id)
    return names


def _string_constants(tree: ast.AST) -> set[str]:
    return {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }


def _dict_keys(tree: ast.AST) -> set[str]:
    keys: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        keys.update(
            key.value
            for key in node.keys
            if isinstance(key, ast.Constant) and isinstance(key.value, str)
        )
    return keys


def check_cache_layer_boundaries(errors: list[str]) -> None:
    handler_path = ROOT / ASSEMBLED_CACHE_HANDLER
    try:
        tree = ast.parse(handler_path.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        fail(errors, f"cannot parse {ASSEMBLED_CACHE_HANDLER}: {exc}")
        return
    parents: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent
    calls = _call_attr_names(tree)
    forbidden = {"get_record_assembled", "put_record_generated"}
    leaked = sorted(forbidden & calls)
    if leaked:
        fail(
            errors,
            "record-bound contracts must not enter a cache: found "
            f"{leaked} in {ASSEMBLED_CACHE_HANDLER}; compute record and permission "
            "state per request and reuse static structure only",
        )
    expected_gate = "not runtime_record_id and (not is_create_request) and cache_key and source_token"
    store_nodes = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "put_generated"
    ]
    if not store_nodes:
        fail(errors, "the handler no longer writes the record-independent assembled cache")
    for node in store_nodes:
        gate = _enclosing_if_test(node, parents)
        if gate != expected_gate:
            fail(
                errors,
                "assembled contract cache write must stay gated by "
                f"'{expected_gate}', found '{gate or '<no if gate>'}'",
            )
    shared_read_nodes = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "get_assembled"
    ]
    if not shared_read_nodes:
        fail(errors, "the handler no longer performs the shared assembled-cache read")
    expected_read_gate = "not runtime_record_id and (not is_create_request)"
    for node in shared_read_nodes:
        gate = _enclosing_if_test(node, parents)
        if gate != expected_read_gate:
            fail(
                errors,
                "assembled contract cache read must stay gated by "
                f"'{expected_read_gate}', found '{gate or '<no if gate>'}'",
            )
    text = handler_path.read_text(encoding="utf-8")
    if "_assembled_v2" in text and "if not runtime_record_id and isinstance(cached_source, dict)" not in text:
        fail(errors, "the assembled cache read must stay restricted to record-free requests")
    if "apply_runtime_record_overlay(" not in text:
        fail(errors, "record forms must still compute the record overlay per request")

    # I9: the assembled hit returns after re-sealing and MUST NOT reach the
    # entitlement/policy/action/modifier/trim projection below. The hit is a
    # cache reuse of a previously authorized record-free projection, not a new
    # authorization decision; a re-seal must never be presented as one.
    hit_branch = next(
        (
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.If)
            and any(
                isinstance(descendant, ast.Constant)
                and descendant.value == "assembled_v2_hot_cache_hit"
                for descendant in ast.walk(node)
            )
        ),
        None,
    )
    if hit_branch is None:
        fail(errors, "the handler no longer declares the record-free assembled hit branch")
    else:
        hit_calls = _call_names(hit_branch)
        forbidden_hit_calls = {
            "_project_action_group_entitlements",
            "_apply_field_policies_to_v2_status",
            "project_runtime_business_actions",
            "project_workflow_action_semantics",
            "hydrate_final_modifier_dependencies",
            "hydrate_final_action_modifier_status",
            "trim_unified_page_contract_v2",
        }
        leaked_hit_calls = sorted(hit_calls & forbidden_hit_calls)
        if leaked_hit_calls:
            fail(
                errors,
                "the assembled hit must return before entitlement/policy/action/"
                f"modifier/trim projection; found {leaked_hit_calls} inside the hit branch",
            )
        if "seal_runtime_contract" not in hit_calls:
            fail(errors, "the assembled hit must re-seal the request identity before returning")
        if not any(isinstance(node, ast.Return) for node in ast.walk(hit_branch)):
            fail(errors, "the assembled hit branch must terminate the request with a return")
        enclosing = next(
            (
                node
                for node in ast.walk(tree)
                if isinstance(node, ast.FunctionDef)
                and any(child is hit_branch for child in ast.walk(node))
            ),
            None,
        )
        if enclosing is None:
            fail(errors, "cannot resolve the function containing the assembled hit branch")
        else:
            hit_line = int(getattr(hit_branch, "lineno", 0))
            later_markers = {
                "_project_action_group_entitlements",
                "_apply_field_policies_to_v2_status",
                "project_runtime_business_actions",
                "hydrate_final_modifier_dependencies",
                "trim_unified_page_contract_v2",
            }
            for node in ast.walk(enclosing):
                if not isinstance(node, ast.Call):
                    continue
                name = (
                    node.func.attr
                    if isinstance(node.func, ast.Attribute)
                    else node.func.id
                    if isinstance(node.func, ast.Name)
                    else ""
                )
                if name in later_markers and int(getattr(node, "lineno", 0)) < hit_line:
                    fail(
                        errors,
                        f"{name} is projected before the assembled hit branch; the hit "
                        "would then be indistinguishable from a per-request recomputation",
                    )

    assembler_tree = ast.parse(ASSEMBLER_PATH.read_text(encoding="utf-8"))
    base_contract = next(
        (
            node
            for node in ast.walk(assembler_tree)
            if isinstance(node, ast.FunctionDef) and node.name == "_base_contract"
        ),
        None,
    )
    if base_contract is None:
        fail(errors, "the assembler no longer declares _base_contract")
    else:
        base_calls = _call_attr_names(base_contract) | {
            node.func.id
            for node in ast.walk(base_contract)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        if "_fingerprint" in base_calls:
            fail(
                errors,
                "_base_contract must not fingerprint the whole source graph: its meta "
                "placeholders are overwritten by the seal, and the seal hashes the "
                "source again; use a stable page identity",
            )
        base_strings = {
            node.value
            for node in ast.walk(base_contract)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        }
        if not any("upc.base" in value for value in base_strings):
            fail(errors, "_base_contract must derive its placeholders from a stable page identity")
    asset_read = ROOT / "addons/smart_core/core/ui_base_contract_asset_repository.py"
    if asset_read.is_file():
        asset_text = asset_read.read_text(encoding="utf-8")
        if "_assembled_v2" in asset_text or "contract_v2" in asset_text:
            fail(
                errors,
                "the persistent runtime asset must store the source projection only; "
                "an assembled or record-bound contract belongs to the hot cache/dynamic layer",
            )

    # I10: the hit path does not recompute permission or policy. Its validity
    # must therefore rest on identity: the cache key binds the principal's group
    # set, and the source token binds ACL/rule/user rows plus the *definition* of
    # every business/field policy. Removing either half would let a re-seal
    # outlive a revoked role or a changed policy.
    cache_path = ROOT / ASSEMBLED_CACHE_MODULE
    try:
        cache_tree = ast.parse(cache_path.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        fail(errors, f"cannot parse {ASSEMBLED_CACHE_MODULE}: {exc}")
        cache_tree = None
    if cache_tree is not None:
        role_code = _function_def(cache_tree, "projection_role_code")
        if role_code is None:
            fail(errors, "projection_role_code is missing; the cache key cannot bind principal groups")
        else:
            role_text = ast.unparse(role_code)
            if "env.user.groups_id.ids" not in role_text or "sha256" not in role_text:
                fail(
                    errors,
                    "projection_role_code must derive a stable digest from the principal's "
                    "group set; uid alone is not a permission identity",
                )
        cache_key = _function_def(cache_tree, "build_projection_cache_key")
        if cache_key is None:
            fail(errors, "build_projection_cache_key is missing")
        else:
            key_names = _call_names(cache_key)
            key_keys = _dict_keys(cache_key)
            for marker in ("role", "company_id", "allowed_company_ids", "params"):
                if marker not in key_keys:
                    fail(
                        errors,
                        "the projection cache key must bind role/company/context and semantic "
                        f"params ({marker!r} is missing)",
                    )
            if "projection_role_code" not in key_names:
                fail(
                    errors,
                    "the projection cache key must derive its principal component through "
                    "projection_role_code(env)",
                )
        source_token = _function_def(cache_tree, "build_projection_source_token")
        if source_token is None:
            fail(errors, "build_projection_source_token is missing")
        else:
            token_text = ast.unparse(source_token)
            token_strings = _string_constants(source_token)
            for marker in (
                "ir.model.access",
                "ir.rule",
                "res.users",
                "ui.business.config.contract",
                "ui.form.field.policy",
            ):
                if marker not in token_strings:
                    fail(
                        errors,
                        "the projection source token must bind ACL/rule/user/policy-definition "
                        f"authorities ({marker!r} is missing)",
                    )
            for marker in ("definition_sha256", "role_group_ids"):
                if marker not in token_text:
                    fail(
                        errors,
                        "the projection source token must bind policy definitions and field-policy "
                        f"role scopes ({marker} is missing)",
                    )
    client_path = ROOT / FRONTEND_CONTRACT_CLIENT
    if client_path.is_file():
        client_text = client_path.read_text(encoding="utf-8")
        required = (
            "const cacheable = renderProfile === 'create'",
            "&& !normalizedRecordId(options.recordId)",
            "&& !String(options.previewToken || '').trim()",
        )
        for marker in required:
            if marker not in client_text:
                fail(
                    errors,
                    "the frontend contract cache must stay limited to record-free create "
                    f"contracts ({marker!r} is missing)",
                )
        if "createContractCache.set(key" not in client_text:
            fail(errors, "the frontend create-contract cache write is missing")
        for marker in ("currentContextEpoch()", "session.sessionDb", "session.token"):
            if marker not in client_text:
                fail(
                    errors,
                    "the frontend create-contract cache key must stay bound to the "
                    f"session database, token and context epoch ({marker!r} is missing)",
                )
    else:
        fail(errors, f"frontend contract client is missing: {FRONTEND_CONTRACT_CLIENT}")
    digests = _assembled_cache_digest()
    if digests != ASSEMBLED_CACHE_INPUTS_SHA256:
        fail(
            errors,
            "the assembled contract cache inputs changed without re-pinning: set "
            f"ASSEMBLED_CACHE_INPUTS_SHA256 = {digests!r} and bump "
            "ASSEMBLED_CONTRACT_CACHE_VERSION in the handler, or a stale assembled "
            "contract stays served from cache",
        )


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_assembler():
    sys.modules.setdefault("odoo", types.ModuleType("odoo"))
    sys.modules.setdefault("odoo.addons", types.ModuleType("odoo.addons"))
    smart_core_pkg = sys.modules.setdefault("odoo.addons.smart_core", types.ModuleType("odoo.addons.smart_core"))
    smart_core_pkg.__path__ = [str(CORE_DIR.parent)]
    core_pkg = sys.modules.setdefault("odoo.addons.smart_core.core", types.ModuleType("odoo.addons.smart_core.core"))
    core_pkg.__path__ = [str(CORE_DIR)]
    spec = importlib.util.spec_from_file_location(
        "odoo.addons.smart_core.core.unified_page_contract_v2_assembler_guard_target",
        ASSEMBLER_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load assembler from {ASSEMBLER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def walk(value: Any, path: str = "$"):
    yield path, value
    if isinstance(value, dict):
        for key, child in value.items():
            yield from walk(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk(child, f"{path}[{index}]")


def registry_path(value: dict[str, Any], path: tuple[str, ...]) -> Any:
    node: Any = value
    for item in path:
        if not isinstance(node, dict):
            return None
        node = node.get(item)
    return node


def validate_contract(
    payload: dict[str, Any],
    *,
    expected_source_type: str,
    snapshot: dict[str, Any],
    registry: dict[str, Any],
    errors: list[str],
    schema_validator: Draft202012Validator,
) -> None:
    for error in sorted(schema_validator.iter_errors(payload), key=lambda item: list(item.absolute_path)):
        location = "$" + "".join(
            f"[{part}]" if isinstance(part, int) else f".{part}"
            for part in error.absolute_path
        )
        fail(errors, f"{expected_source_type}: schema {location}: {error.message}")
    required = {
        "pageInfo",
        "layoutContract",
        "statusContract",
        "actionContract",
        "dataContract",
        "runtimeContract",
        "meta",
    }
    optional = {"formStructureContract", "searchContract", "workflowContract"}
    payload_keys = set(payload.keys())
    if not required <= payload_keys or payload_keys - required - optional:
        fail(errors, f"contract top-level mismatch: {sorted(payload.keys())}")
    if payload.get("pageInfo", {}).get("contractVersion") != "2.2.0":
        fail(errors, "contractVersion must be 2.2.0")
    meta = payload.get("meta", {}) if isinstance(payload.get("meta"), dict) else {}
    if meta.get("sourceType") != expected_source_type:
        fail(errors, f"meta.sourceType must be {expected_source_type}")
    if "compat" in meta:
        fail(errors, "meta.compat must be removed")
    page_info = payload.get("pageInfo", {}) if isinstance(payload.get("pageInfo"), dict) else {}
    layout = payload.get("layoutContract", {}) if isinstance(payload.get("layoutContract"), dict) else {}
    enum_checks = (
        ("pageInfo.clientType", page_info.get("clientType"), ("clientType", "stable")),
        ("pageInfo.viewType", page_info.get("viewType"), ("viewType",)),
        ("pageInfo.layoutType", page_info.get("layoutType"), ("layoutType",)),
        ("pageInfo.renderMode", page_info.get("renderMode"), ("renderMode",)),
        ("layoutContract.layoutType", layout.get("layoutType"), ("layoutType",)),
        ("layoutContract.adaptMode", layout.get("adaptMode"), ("adaptMode",)),
    )
    for label, value, registry_key_path in enum_checks:
        if value not in (registry_path(registry, registry_key_path) or []):
            fail(errors, f"{expected_source_type}: {label} must be listed in enum_registry.{'.'.join(registry_key_path)}")
    container_count = len(payload.get("layoutContract", {}).get("containerTree") or [])
    widget_status = payload.get("statusContract", {}).get("widgetStatus") or []
    widget_status_count = len(widget_status)
    action_count = len(payload.get("actionContract", {}).get("actionRuleList") or [])
    if container_count < int(snapshot.get("minContainerCount") or 0):
        fail(errors, f"{expected_source_type}: container snapshot below baseline")
    if widget_status_count < int(snapshot.get("minWidgetStatusCount") or 0):
        fail(errors, f"{expected_source_type}: widget status snapshot below baseline")
    expected_widget_ids = [
        str(item)
        for item in snapshot.get("expectedWidgetIds") or []
        if str(item)
    ]
    if expected_widget_ids:
        actual_widget_ids = {
            str(row.get("widgetId"))
            for row in widget_status
            if isinstance(row, dict) and str(row.get("widgetId"))
        }
        for widget_id in expected_widget_ids:
            if widget_id not in actual_widget_ids:
                fail(errors, f"{expected_source_type}: expected widgetStatus {widget_id!r} missing")
    if action_count < int(snapshot.get("minActionCount") or 0):
        fail(errors, f"{expected_source_type}: action snapshot below baseline")
    expected_form_structure = snapshot.get("requiresFormStructureContract") is True
    if expected_form_structure:
        structure = payload.get("formStructureContract") if isinstance(payload.get("formStructureContract"), dict) else {}
        if structure.get("source") != "ui.contract.v2.form_structure_contract":
            fail(errors, f"{expected_source_type}: formStructureContract source missing")
        slots = structure.get("slots") if isinstance(structure.get("slots"), list) else []
        if not slots:
            fail(errors, f"{expected_source_type}: formStructureContract slots missing")
        if not _layout_has_form_structure(payload.get("layoutContract", {}).get("containerTree") or []):
            fail(errors, f"{expected_source_type}: layout projection missing formStructure metadata")
    for legacy_key in ("scene_contract", "page_orchestration", "ui_contract", "api_onchange"):
        if legacy_key in payload:
            fail(errors, f"legacy key leaked at top-level: {legacy_key}")
    for node_path, node in walk(payload):
        if isinstance(node, dict):
            for key in node:
                if str(key).lower() in {"script", "function", "eval", "jsonlogic", "workflowdsl", "frontendprivate"}:
                    fail(errors, f"forbidden executable/private key {key!r} at {node_path}")
            if (
                "containerType" in node
                and "children" in node
                and "widgetList" in node
                and node["containerType"] not in (registry_path(registry, ("containerType",)) or [])
            ):
                fail(errors, f"{node_path}.containerType must be listed in enum_registry.containerType")
            if "widgetType" in node and node["widgetType"] not in (registry_path(registry, ("widgetType",)) or []):
                fail(errors, f"{node_path}.widgetType must be listed in enum_registry.widgetType")
            if _owns_direct_field_child(node) and not _declared_positive_int(node.get("columns")):
                fail(
                    errors,
                    f"{node_path}.columns must declare the field-grid column count of a "
                    "container that owns direct field children",
                )


def _declared_positive_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    return value if isinstance(value, int) and value > 0 else None


def _owns_direct_field_child(node: dict[str, Any]) -> bool:
    children = node.get("children")
    if not isinstance(children, list) or "widgetList" not in node:
        return False
    return any(
        str(child.get("containerType") or child.get("type") or child.get("kind") or "").strip().lower() == "field"
        for child in children
        if isinstance(child, dict)
    )


def _layout_has_form_structure(rows: list[Any]) -> bool:
    for row in rows:
        if not isinstance(row, dict):
            continue
        if isinstance(row.get("formStructure"), dict) or isinstance(row.get("formStructureRole"), dict):
            return True
        for key in ("children", "pages", "tabs", "nodes", "items"):
            if _layout_has_form_structure(row.get(key) if isinstance(row.get(key), list) else []):
                return True
    return False


def validate_patch(payload: dict[str, Any], snapshot: dict[str, Any], errors: list[str]) -> None:
    if payload.get("updateType") != "partial":
        fail(errors, "patch updateType must be partial")
    if snapshot.get("updateType") and payload.get("updateType") != snapshot.get("updateType"):
        fail(errors, "patch updateType does not match snapshot")
    for key in ("layoutPatch", "statusPatch", "dataPatch", "runtimePatch", "meta"):
        if key not in payload:
            fail(errors, f"patch missing {key}")
    meta = payload.get("meta", {})
    if meta.get("contractVersion") != "2.2.0":
        fail(errors, "patch contractVersion must be 2.2.0")
    if meta.get("sourceType") != "api.onchange":
        fail(errors, "patch meta.sourceType must be api.onchange")
    if "compat" in meta:
        fail(errors, "patch meta.compat must be removed")
    if "api_onchange" in payload:
        fail(errors, "api_onchange leaked at patch top-level")
    if len(payload.get("dataPatch") or {}) < int(snapshot.get("minDataPatchKeys") or 0):
        fail(errors, "patch dataPatch snapshot below baseline")
    widget_status = payload.get("statusPatch", {}).get("widgetStatus") or []
    if len(widget_status) < int(snapshot.get("minWidgetStatusCount") or 0):
        fail(errors, "patch widgetStatus snapshot below baseline")


# --- Declared layout capability floor ---------------------------------------
# Owner direction 2026-10-12: the layout contract keeps its declared capability
# set (one 24-unit span dialect, declared container field-grid columns, declared
# container zone) and no consumer is required to consume all of it.  This guard
# is the non-regression side of that ruling: a consumer may map or ignore a
# declared facet, but the assembler must not stop declaring it.
LAYOUT_GRID_UNITS = 24
LAYOUT_LEAF_KINDS = frozenset({"field", "widget", "button", "action"})


def declared_layout_capability_errors(contract: Any, label: str) -> list[str]:
    errors: list[str] = []
    layout = contract.get("layoutContract") if isinstance(contract, dict) else None
    tree = layout.get("containerTree") if isinstance(layout, dict) else None
    if not isinstance(tree, list) or not tree:
        return [f"{label}: layoutContract.containerTree must be a non-empty array"]

    def walk_declared(nodes: Any, path: str) -> None:
        if not isinstance(nodes, list):
            errors.append(f"{label}: {path} must be an array")
            return
        for index, node in enumerate(nodes):
            here = f"{path}[{index}]"
            if not isinstance(node, dict):
                errors.append(f"{label}: {here} must be an object")
                continue
            if not str(node.get("zone") or "").strip():
                errors.append(f"{label}: {here} must declare its layout zone")
            span = node.get("span")
            if span is not None and (
                isinstance(span, bool) or not isinstance(span, int) or not 1 <= span <= LAYOUT_GRID_UNITS
            ):
                errors.append(
                    f"{label}: {here} declares span {span!r} outside the 1..{LAYOUT_GRID_UNITS} layout grid"
                )
            kind = str(node.get("containerType") or node.get("type") or "").lower()
            owns_field_child = any(
                str(child.get("containerType") or child.get("type") or "").lower() == "field"
                for child in (node.get("children") or [])
                if isinstance(child, dict)
            )
            if kind not in LAYOUT_LEAF_KINDS and owns_field_child:
                columns = node.get("columns")
                if isinstance(columns, bool) or not isinstance(columns, int) or not 1 <= columns <= LAYOUT_GRID_UNITS:
                    errors.append(
                        f"{label}: {here} owns field children but declares no "
                        f"1..{LAYOUT_GRID_UNITS} field-grid columns"
                    )
            walk_declared(node.get("children") or [], here)

    walk_declared(tree, "layoutContract.containerTree")
    return errors


def check_declared_layout_capability(
    contracts: list[tuple[str, Any]],
    errors: list[str],
) -> None:
    for label, contract in contracts:
        for message in declared_layout_capability_errors(contract, label):
            fail(errors, message)


def self_check_declared_layout_capability() -> list[str]:
    """The capability checker must fail closed, so prove it on stripped copies."""
    verdicts: list[str] = []
    baseline = {
        "layoutContract": {
            "containerTree": [
                {
                    "containerType": "group",
                    "zone": "detail_zone",
                    "columns": 2,
                    "span": 24,
                    "children": [{"containerType": "field", "zone": "detail_zone"}],
                }
            ]
        }
    }
    if declared_layout_capability_errors(baseline, "self-check baseline"):
        verdicts.append("the capability checker must accept a fully declared layout tree")
    for mutation, expected in (
        (lambda node: node.pop("zone", None), "zone"),
        (lambda node: node.pop("columns", None), "columns"),
        (lambda node: node.update({"span": 40}), "span"),
    ):
        stripped = deepcopy(baseline)
        mutation(stripped["layoutContract"]["containerTree"][0])
        messages = declared_layout_capability_errors(stripped, "self-check mutation")
        if not messages or not any(expected in message for message in messages):
            verdicts.append(f"the capability checker must reject a tree missing its {expected} declaration")
    return verdicts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixtures", required=True, type=Path)
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--enum-registry", required=True, type=Path)
    parser.add_argument("--schema", required=True, type=Path)
    args = parser.parse_args()
    target = load_assembler()
    p1_layout = load_module(P1_PROJECT_LAYOUT_PATH, "smart_construction_core_project_layout_guard_target")
    errors: list[str] = []
    check_assembled_contract_cache_pin(errors)
    check_cache_layer_boundaries(errors)
    snapshot = load_json(args.snapshot)
    registry = load_json(args.enum_registry)
    schema_validator = Draft202012Validator(load_json(args.schema))
    if snapshot.get("contractVersion") != target.CONTRACT_VERSION:
        fail(
            errors,
            "snapshot contractVersion must match assembler contractVersion "
            f"{target.CONTRACT_VERSION}",
        )
    source_snapshots = snapshot.get("sources") if isinstance(snapshot.get("sources"), dict) else {}

    scene_source = load_json(args.fixtures / "scene_contract_source.json")
    page_source = load_json(args.fixtures / "page_orchestration_source.json")
    ui_source = load_json(args.fixtures / "ui_contract_source.json")
    onchange_source = load_json(args.fixtures / "api_onchange_source.json")

    scene_contract = target.assemble_unified_page_contract_v2(scene_source, source_type="scene_contract")
    page_contract = target.assemble_unified_page_contract_v2(page_source, source_type="page_orchestration")
    ui_contract = target.assemble_unified_page_contract_v2(ui_source, source_type="ui.contract")
    onchange_patch = target.assemble_unified_page_patch_v2(onchange_source, action_id="project.name.change")

    widget_projection_cases = (
        ({"name": "state", "type": "selection", "widget": "selection"}, "select", "sc.select.remote"),
        ({"name": "active", "type": "boolean", "widget": "boolean"}, "checkbox", "sc.input.boolean"),
        ({"name": "line_ids", "type": "one2many", "widget": "one2many_list", "relation": "x.line"}, "table", "sc.relation.table"),
        ({"name": "amount", "type": "monetary", "widget": "monetary"}, "number", "sc.value.money"),
        ({"name": "state", "type": "selection", "widget": "statusbar"}, "display", "sc.display.status"),
        ({"name": "quick_encoding_vals", "type": "json", "widget": "json"}, "display", "sc.display.text"),
    )
    for field, expected_widget, expected_component in widget_projection_cases:
        projected = target._field_widget(field, layout_type="form")
        if projected.get("widgetType") != expected_widget:
            fail(errors, f"native widget {field['widget']} must normalize to {expected_widget}")
        if projected.get("componentKey") != expected_component:
            fail(errors, f"native widget {field['widget']} must resolve component {expected_component}")
        if projected.get("componentConfig", {}).get("nativeWidget") != field["widget"]:
            fail(errors, f"native widget {field['widget']} must remain available as presentation metadata")

    validate_contract(
        scene_contract,
        expected_source_type="scene_contract",
        snapshot=source_snapshots.get("scene_contract") or {},
        registry=registry,
        errors=errors,
        schema_validator=schema_validator,
    )
    validate_contract(
        page_contract,
        expected_source_type="page_orchestration",
        snapshot=source_snapshots.get("page_orchestration") or {},
        registry=registry,
        errors=errors,
        schema_validator=schema_validator,
    )
    validate_contract(
        ui_contract,
        expected_source_type="ui.contract",
        snapshot=source_snapshots.get("ui_contract") or {},
        registry=registry,
        errors=errors,
        schema_validator=schema_validator,
    )
    for self_check_message in self_check_declared_layout_capability():
        fail(errors, self_check_message)
    check_declared_layout_capability(
        (("scene_contract", scene_contract), ("page_orchestration", page_contract), ("ui.contract", ui_contract)),
        errors,
    )
    p1_contract = deepcopy(ui_contract)
    # The pure P1 helper authors the group; the platform rule declares its grid,
    # exactly as the runtime wrapper does for a container appended after the
    # post-projection boundary.
    p1_group = p1_layout.sc_append_project_responsibility_group(p1_contract, include_collaborators=True)
    if p1_group is None or not target.declare_container_columns(p1_group):
        fail(errors, "P1 late-appended grid container must be declared by the assembler column rule")
    validate_contract(
        p1_contract,
        expected_source_type="ui.contract",
        snapshot=source_snapshots.get("ui_contract") or {},
        registry=registry,
        errors=errors,
        schema_validator=schema_validator,
    )
    p1_container_status = p1_contract.get("statusContract", {}).get("containerStatus") or []
    if "sc_project_responsibility_collaboration" not in {
        str(row.get("containerId") or "") for row in p1_container_status if isinstance(row, dict)
    }:
        fail(errors, "P1 project responsibility group must have canonical containerStatus")
    for node_path, node in walk(p1_contract.get("layoutContract", {}).get("containerTree") or []):
        if isinstance(node, dict) and "field_info" in node:
            fail(errors, f"P1 project layout must not emit field_info alias at {node_path}")
    validate_patch(onchange_patch, source_snapshots.get("api_onchange") or {}, errors)

    if not scene_contract.get("layoutContract", {}).get("containerTree"):
        fail(errors, "scene_contract mapping must produce containerTree")
    if not page_contract.get("actionContract", {}).get("actionRuleList"):
        fail(errors, "page_orchestration mapping must produce actionRuleList")
    if not ui_contract.get("statusContract", {}).get("widgetStatus"):
        fail(errors, "ui.contract mapping must produce widgetStatus")
    source_context = (
        ui_contract.get("dataContract", {}).get("dataMeta", {}).get("sourceContext", {})
    )
    if source_context.get("contextRaw") != "{'allowed_company_ids': [7]}":
        fail(errors, "ui.contract sourceContext must preserve canonical contextRaw")
    if source_context.get("domainRaw") != "[('company_id', '=', 7)]":
        fail(errors, "ui.contract sourceContext must preserve canonical domainRaw")
    if source_context.get("renderProfile") != "edit":
        fail(errors, "ui.contract sourceContext must preserve canonical renderProfile")
    for forbidden in ("context_raw", "domain_raw", "render_profile"):
        if forbidden in source_context:
            fail(errors, f"ui.contract sourceContext must not emit alias {forbidden}")
    search_contract = ui_contract.get("searchContract", {})
    if (search_contract.get("filters") or [{}])[0].get("key") != "active":
        fail(errors, "ui.contract searchContract must normalize filter name to key")
    if (search_contract.get("group_by") != [{"key": "stage_id", "field": "stage_id", "label": "stage_id"}]):
        fail(errors, "ui.contract searchContract must normalize group_by field names")
    if search_contract.get("fields") != [{"name": "name", "label": "Name"}]:
        fail(errors, "ui.contract searchContract must normalize search_fields")
    if search_contract.get("search_panel") != {"enabled": True}:
        fail(errors, "ui.contract searchContract must normalize searchpanel alias")
    for forbidden in ("searchpanel", "group_by_fields", "search_fields"):
        if forbidden in search_contract:
            fail(errors, f"ui.contract searchContract must not emit alias {forbidden}")
    if not onchange_patch.get("dataPatch"):
        fail(errors, "api.onchange mapping must produce dataPatch")

    if errors:
        print("Unified Page Contract v2+ assembler guard failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Unified Page Contract v2+ assembler guard passed: sources=4")
    return 0


if __name__ == "__main__":
    sys.exit(main())
