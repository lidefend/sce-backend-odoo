#!/usr/bin/env python3
"""Guard app_config_engine as runtime contract plumbing, not product authority."""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
APP_ENGINE = ROOT / "addons" / "smart_core" / "app_config_engine"
DOC = APP_ENGINE / "docs" / "app_config_engine.md"
DOCS_DIR = APP_ENGINE / "docs"
CONTROLLER = APP_ENGINE / "controllers" / "contract_api.py"
SERVICE = APP_ENGINE / "services" / "contract_service.py"
NATIVE_PARSE = APP_ENGINE / "services" / "native_parse_service.py"
PAGE_ASSEMBLER = APP_ENGINE / "services" / "assemblers" / "page_assembler.py"
APP_VIEW_CONFIG = APP_ENGINE / "models" / "app_view_config.py"
APP_ACTION_CONFIG = APP_ENGINE / "models" / "app_action_config.py"
APP_PERMISSION_CONFIG = APP_ENGINE / "models" / "app_permission_config.py"
APP_SEARCH_CONFIG = APP_ENGINE / "models" / "app_search_config.py"
APP_WORKFLOW_CONFIG = APP_ENGINE / "models" / "app_workflow_config.py"
ACTION_RESOLVER = APP_ENGINE / "services" / "resolvers" / "action_resolver.py"
ACTION_DISPATCHER = APP_ENGINE / "services" / "dispatchers" / "action_dispatcher.py"
V2_ASSEMBLER = ROOT / "addons" / "smart_core" / "core" / "unified_page_contract_v2_assembler.py"
ODOO_VIEW_PARSER = APP_ENGINE / "services" / "view_Parser" / "contract_Parser.py"
VIEW_PARSER_DOC = APP_ENGINE / "services" / "view_Parser" / "readme — Contract 2.md"

def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _require(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def _industry_refs(source: str) -> set[str]:
    refs: set[str] = set()
    marker = "smart_construction_core."
    start = 0
    while True:
        idx = source.find(marker, start)
        if idx < 0:
            break
        end = idx
        while end < len(source) and (source[end].isalnum() or source[end] in "._"):
            end += 1
        refs.add(source[idx:end])
        start = end
    return refs


def _industry_doc_tokens(source: str) -> set[str]:
    tokens = {
        "实付登记",
        "智慧施工",
        "施工",
        "付款",
        "发票",
        "材料",
        "劳务",
    }
    return {token for token in tokens if token in source}


def _parse_python(path: Path, errors: list[str]) -> ast.Module | None:
    try:
        return ast.parse(_read(path), filename=path.as_posix())
    except SyntaxError as exc:
        errors.append(f"python parse failed closed for {path.relative_to(ROOT)}: {exc}")
        return None


def _function(tree: ast.Module | None, name: str) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    if tree is None:
        return None
    return next(
        (
            node for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name
        ),
        None,
    )


def _called_get_keys(function: ast.AST | None, receiver: str) -> set[str]:
    keys: set[str] = set()
    if function is None:
        return keys
    for node in ast.walk(function):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute) or node.func.attr != "get":
            continue
        if not isinstance(node.func.value, ast.Name) or node.func.value.id != receiver or not node.args:
            continue
        key = node.args[0]
        if isinstance(key, ast.Constant) and isinstance(key.value, str):
            keys.add(key.value)
    return keys


def _called_get_keys_without_false_guard(
    function: ast.AST | None,
    receiver: str,
    guard_name: str,
) -> set[str]:
    """Return receiver.get keys not proven to run with ``guard_name`` false."""
    unguarded: set[str] = set()

    def visit(node: ast.AST, guard_is_false: bool = False) -> None:
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if (
                node.func.attr == "get"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == receiver
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
                and not guard_is_false
            ):
                unguarded.add(node.args[0].value)
        if isinstance(node, ast.If):
            false_in_body = (
                isinstance(node.test, ast.UnaryOp)
                and isinstance(node.test.op, ast.Not)
                and isinstance(node.test.operand, ast.Name)
                and node.test.operand.id == guard_name
            )
            true_in_body = isinstance(node.test, ast.Name) and node.test.id == guard_name
            visit(node.test, guard_is_false)
            for child in node.body:
                visit(child, guard_is_false or false_in_body)
            for child in node.orelse:
                visit(child, guard_is_false or true_in_body)
            return
        for child in ast.iter_child_nodes(node):
            visit(child, guard_is_false)

    if function is not None:
        for statement in function.body:
            visit(statement)
    return unguarded


def _call_has_true_keyword(function: ast.AST | None, method_name: str, keyword: str) -> bool:
    if function is None:
        return False
    for node in ast.walk(function):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != method_name:
            continue
        for item in node.keywords:
            if item.arg == keyword and isinstance(item.value, ast.Constant) and item.value.value is True:
                return True
    return False


def _function_arg_names(function: ast.FunctionDef | ast.AsyncFunctionDef | None) -> set[str]:
    if function is None:
        return set()
    return {arg.arg for arg in (*function.args.posonlyargs, *function.args.args, *function.args.kwonlyargs)}


def _called_attribute_names(function: ast.AST | None) -> set[str]:
    if function is None:
        return set()
    return {
        node.func.attr
        for node in ast.walk(function)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }


def main() -> int:
    errors: list[str] = []
    doc = _read(DOC)
    controller = _read(CONTROLLER)
    service = _read(SERVICE)
    native_parse = _read(NATIVE_PARSE)
    page_assembler = _read(PAGE_ASSEMBLER)
    app_view_config = _read(APP_VIEW_CONFIG)
    odoo_view_parser = _read(ODOO_VIEW_PARSER)
    view_parser_doc = _read(VIEW_PARSER_DOC)
    action_tree = _parse_python(APP_ACTION_CONFIG, errors)
    permission_tree = _parse_python(APP_PERMISSION_CONFIG, errors)
    search_tree = _parse_python(APP_SEARCH_CONFIG, errors)
    workflow_tree = _parse_python(APP_WORKFLOW_CONFIG, errors)
    action_resolver_tree = _parse_python(ACTION_RESOLVER, errors)
    action_dispatcher_tree = _parse_python(ACTION_DISPATCHER, errors)
    page_tree = _parse_python(PAGE_ASSEMBLER, errors)
    v2_tree = _parse_python(V2_ASSEMBLER, errors)

    for token in (
        "Runtime Contract Plumbing",
        "No Business Fact Authority",
        "Native Odoo Parse Boundary",
        "View Orchestration Boundary",
        "Compatibility Models",
        "No Industry Defaults",
        "`ui.business.config.contract`",
        "`ViewOrchestrator`",
        "`UiContractV2Handler`",
        "`make verify.app_config_engine.boundary_guard`",
    ):
        _require(errors, token in doc, f"docs/app_config_engine.md missing boundary token: {token}")
    doc_industry_tokens = sorted(_industry_doc_tokens(doc))
    _require(
        errors,
        not doc_industry_tokens,
        "app_config_engine boundary doc must use platform-neutral examples, not industry terms: %s"
        % ", ".join(doc_industry_tokens),
    )

    scratch_docs = sorted(
        path.relative_to(ROOT).as_posix()
        for path in DOCS_DIR.glob("test*.json")
        if path.name.startswith("test")
    )
    _require(
        errors,
        not scratch_docs,
        "app_config_engine docs must not contain scratch test JSON files: %s" % ", ".join(scratch_docs),
    )

    _require(errors, "NO_BUSINESS_FACT_AUTHORITY = True" in controller, "controller must declare no business fact authority")
    _require(errors, "ContractService(request_env=request.env)" in controller, "controller must delegate to ContractService")
    _require(errors, "svc.handle_request()" in controller, "controller must keep request handling in ContractService")

    _require(errors, "NO_BUSINESS_FACT_AUTHORITY = True" in service, "ContractService must declare no business fact authority")
    _require(errors, "apply_contract_governance" in service, "ContractService must keep runtime governance filtering")
    _require(errors, '"runtime_carrier": "app_config_engine.contract_service"' in service, "ContractService source authority carrier missing")

    _require(errors, "NO_BUSINESS_FACT_AUTHORITY = True" in native_parse, "NativeParseService must declare no business fact authority")
    _require(errors, "odoo_native_view_parse_coordinator" in native_parse, "NativeParseService must keep native parse authority")
    _require(errors, "parse_odoo_view" in native_parse, "NativeParseService must use native parser entry")
    _require(errors, "LEGACY_MIXIN_MODULES" in odoo_view_parser, "Odoo view parser must centralize legacy mixin module names")
    _require(errors, "_load_legacy_mixin" in odoo_view_parser, "Odoo view parser must load legacy mixins through an explicit helper")
    _require(errors, "Legacy Filesystem Boundary" in view_parser_doc, "view parser doc must declare the legacy filesystem boundary")
    _require(errors, "services/view_Parser/" in view_parser_doc, "view parser doc must describe the actual filesystem path")
    _require(errors, "不能在解析入口默认 `sudo()`" in view_parser_doc, "view parser doc must forbid default sudo parsing")

    _require(errors, "NO_BUSINESS_FACT_AUTHORITY = True" in page_assembler, "PageAssembler must declare no business fact authority")
    _require(errors, "_inject_view_orchestration_summary" in page_assembler, "PageAssembler must expose view orchestration summary")
    _require(errors, "_current_view_orchestration_config_summary" in page_assembler, "PageAssembler must expose current orchestration config summary")
    _require(errors, "ui.business.config.contract" in page_assembler, "PageAssembler must read orchestration config as external authority")
    _require(errors, "ViewOrchestrator(self.env).compose" in app_view_config, "app.view.config must delegate orchestration to ViewOrchestrator")

    _require(errors, _function(action_tree, "_scan_view_buttons") is None, "app.action.config must not rescan raw ir.ui.view buttons")
    generate_actions = _function(action_tree, "_generate_from_ir_actions")
    action_generate_calls = {
        node.func.attr
        for node in ast.walk(generate_actions) if generate_actions is not None
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    _require(errors, "_scan_view_buttons" not in action_generate_calls, "app.action.config must only consume explicitly bound actions")
    assemble_page = _function(page_tree, "assemble_page_contract")
    _require(
        errors,
        _call_has_true_keyword(assemble_page, "get_action_contract", "check_model_acl"),
        "PageAssembler must intersect bound action projection with runtime model ACL",
    )
    _require(errors, _function(page_tree, "_native_action_needs_existing_record") is None, "PageAssembler must consume visible_profiles instead of inferring record scope")
    append_actions = _function(v2_tree, "_append_ui_contract_actions")
    duplicate_action_keys = _called_get_keys_without_false_guard(
        append_actions,
        "ui",
        "explicit_form_view",
    ) & {"business_actions", "action_groups"}
    _require(
        errors,
        not duplicate_action_keys,
        "Contract V2 explicit native form assembly must not re-consume parallel top-level action carriers: %s"
        % ", ".join(sorted(duplicate_action_keys)),
    )
    _require(errors, _function(workflow_tree, "_guess_to_state") is None, "app.workflow.config must not infer target state from method names")
    _require(errors, _function(action_resolver_tree, "materialize_server_action") is None, "contract reads must not execute server actions")
    _require(errors, _function(action_resolver_tree, "safe_probe_server_action") is None, "contract reads must not probe server actions")
    _require(
        errors,
        "materialize_server_action" not in _called_attribute_names(_function(action_dispatcher_tree, "dispatch")),
        "action dispatcher must fail closed for unmapped server actions",
    )
    permission_collect = _function(permission_tree, "_collect_record_rules")
    permission_constants = {
        node.value for node in ast.walk(permission_collect) if permission_collect is not None
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    _require(errors, "GLOBAL_AND_GROUP_OR" in permission_constants, "app.permission.config must preserve Odoo global-AND/group-OR rule algebra")
    search_get = _function(search_tree, "get_search_contract")
    search_collect = _function(search_tree, "_collect_ir_filters")
    _require(errors, "action_id" in _function_arg_names(search_get), "search contract runtime projection must accept action_id")
    _require(errors, "action_id" in _function_arg_names(search_collect), "saved-filter collector must be action scoped")

    found_refs: set[str] = set()
    sudo_parse_refs: list[str] = []
    for path in APP_ENGINE.rglob("*.py"):
        text = _read(path)
        found_refs.update(_industry_refs(text))
        if "sudo().parse_odoo_view" in text:
            sudo_parse_refs.append(path.relative_to(ROOT).as_posix())
    _require(
        errors,
        not found_refs,
        "app_config_engine has industry module references: %s" % ", ".join(sorted(found_refs)),
    )
    _require(
        errors,
        not sudo_parse_refs,
        "app_config_engine native parser must use request-user environment, not sudo().parse_odoo_view: %s"
        % ", ".join(sorted(sudo_parse_refs)),
    )

    if errors:
        print("[app_config_engine_boundary_guard] FAIL")
        for error in errors:
            print(error)
        return 2
    print("[app_config_engine_boundary_guard] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
