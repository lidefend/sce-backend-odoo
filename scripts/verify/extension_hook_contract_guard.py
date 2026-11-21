#!/usr/bin/env python3
"""Validate explicit invocation and provider contracts for smart_core hooks."""
from __future__ import annotations

import ast
import importlib.util
import sys
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SMART_CORE = ROOT / "addons" / "smart_core"
CONTRACT_PATH = SMART_CORE / "core" / "extension_hook_contracts.py"
FIRST_CALLS = {
    "call_extension_hook_first",
    "call_extension_hook_first_compatible",
}


def load_contract_module(path: Path = CONTRACT_PATH):
    spec = importlib.util.spec_from_file_location("arch_close_hook_contracts", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("extension hook contract module cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def first_call_names(root: Path) -> set[str]:
    names: set[str] = set()
    parsed: list[tuple[ast.AST, dict[str, set[str]]]] = []
    paths = (
        list((root / "addons").rglob("*.py"))
        + list((root / "scripts").rglob("*.py"))
    )
    for path in sorted(paths):
        text_path = path.as_posix()
        if "/tests/" in text_path or path.name.startswith("test_"):
            continue
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, SyntaxError):
            continue
        if not any(name in source for name in FIRST_CALLS):
            continue
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        assigned_strings: dict[str, set[str]] = defaultdict(set)
        for node in ast.walk(tree):
            if (
                isinstance(node, (ast.Assign, ast.AnnAssign))
                and node.value is not None
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)
            ):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    if isinstance(target, ast.Name):
                        assigned_strings[target.id].add(node.value.value)
        parsed.append((tree, assigned_strings))

    # A wrapper is any function that forwards one of its parameters as the
    # Hook name. Resolve wrapper specs to a fixed point so multi-hop wrappers
    # remain explicit without depending on function naming conventions.
    wrapper_param_index: dict[str, int] = {}
    changed = True
    while changed:
        changed = False
        for tree, _assigned_strings in parsed:
            for function in (
                node for node in ast.walk(tree)
                if isinstance(node, ast.FunctionDef)
            ):
                positional = {
                    arg.arg: index
                    for index, arg in enumerate(function.args.args)
                }
                for call in (
                    node for node in ast.walk(function)
                    if isinstance(node, ast.Call)
                ):
                    callee = (
                        call.func.id
                        if isinstance(call.func, ast.Name)
                        else call.func.attr
                        if isinstance(call.func, ast.Attribute)
                        else ""
                    )
                    if callee in FIRST_CALLS:
                        hook_index = 1
                    elif callee in wrapper_param_index:
                        hook_index = wrapper_param_index[callee]
                    else:
                        continue
                    if len(call.args) <= hook_index:
                        continue
                    argument = call.args[hook_index]
                    if (
                        isinstance(argument, ast.Name)
                        and argument.id in positional
                    ):
                        index = positional[argument.id]
                        if wrapper_param_index.get(function.name) != index:
                            wrapper_param_index[function.name] = index
                            changed = True

    for tree, assigned_strings in parsed:
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            function = node.func
            function_name = (
                function.id
                if isinstance(function, ast.Name)
                else function.attr
                if isinstance(function, ast.Attribute)
                else ""
            )
            if (
                "hook" in function_name.lower()
                and function_name != "run_extension_hooks"
            ):
                for value in (
                    list(node.args)
                    + [keyword.value for keyword in node.keywords]
                ):
                    if (
                        isinstance(value, ast.Constant)
                        and isinstance(value.value, str)
                        and value.value.startswith("smart_core_")
                    ):
                        names.add(value.value)
            if function_name in FIRST_CALLS:
                hook_index = 1
            elif function_name in wrapper_param_index:
                hook_index = wrapper_param_index[function_name]
            else:
                continue
            if len(node.args) <= hook_index:
                continue
            hook_arg = node.args[hook_index]
            if isinstance(hook_arg, ast.Constant) and isinstance(hook_arg.value, str):
                names.add(hook_arg.value)
            elif isinstance(hook_arg, ast.Name):
                names.update(assigned_strings.get(hook_arg.id, set()))
    return names


def exported_providers(root: Path) -> dict[str, set[str]]:
    providers: dict[str, set[str]] = defaultdict(set)
    for init_path in sorted((root / "addons").glob("*/__init__.py")):
        module_name = init_path.parent.name
        manifest = init_path.parent / "__manifest__.py"
        if manifest.exists() and not ast.literal_eval(manifest.read_text()).get("installable", True):
            continue
        try:
            tree = ast.parse(init_path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            for alias in node.names:
                name = alias.asname or alias.name
                if name.startswith(("smart_core_", "get_")):
                    providers[name].add(module_name)
    return dict(providers)


def collect_failures(root: Path = ROOT, contract_module=None) -> list[str]:
    contracts = contract_module or load_contract_module()
    called = first_call_names(root)
    providers = exported_providers(root)
    registered = set(contracts.SINGLE_OWNER_HOOKS) | set(contracts.ORDERED_MERGE_HOOKS)
    failures = []

    overlapping = sorted(
        set(contracts.SINGLE_OWNER_HOOKS)
        & (set(contracts.ORDERED_MERGE_HOOKS) | set(contracts.RUN_ALL_HOOKS))
    )
    if overlapping:
        failures.append("hooks have multiple modes: %s" % ", ".join(overlapping))

    undeclared = sorted(called - registered)
    if undeclared:
        failures.append("first-wins hooks missing contracts: %s" % ", ".join(undeclared))

    for hook_name in sorted(contracts.SINGLE_OWNER_HOOKS):
        found = sorted(providers.get(hook_name, set()))
        if len(found) > 1:
            failures.append(
                "single_owner hook %s has providers: %s"
                % (hook_name, ", ".join(found))
            )

    for hook_name, contract in sorted(contracts.ORDERED_MERGE_HOOKS.items()):
        found = set(providers.get(hook_name, set()))
        expected = set(contract.providers)
        if found != expected:
            failures.append(
                "ordered_merge hook %s providers differ: expected=%s actual=%s"
                % (hook_name, sorted(expected), sorted(found))
            )
    run_all = contracts.RUN_ALL_HOOKS
    for hook_name, contract in (run_all.items() if isinstance(run_all, dict) else ()):
        expected = set(contract.providers)
        final_providers = set(getattr(contract, "final_providers", ()))
        if not final_providers.issubset(expected):
            failures.append(
                "run_all hook %s final providers are not declared: %s"
                % (hook_name, sorted(final_providers - expected))
            )
        actual = set(providers.get(hook_name, set()))
        missing = expected - actual
        unexpected = actual - expected
        allow_undeclared = bool(getattr(contract, "allow_undeclared", False))
        if expected and (missing or (unexpected and not allow_undeclared)):
            failures.append(
                "run_all hook %s providers differ: expected=%s actual=%s "
                "missing=%s unexpected=%s"
                % (
                    hook_name,
                    sorted(expected),
                    sorted(actual),
                    sorted(missing),
                    sorted(unexpected),
                )
            )
    return failures


def main() -> int:
    failures = collect_failures()
    if failures:
        print("[extension_hook_contract_guard] FAIL", file=sys.stderr)
        for failure in failures:
            print("- %s" % failure, file=sys.stderr)
        return 2
    contracts = load_contract_module()
    calls = first_call_names(ROOT)
    print(
        "[extension_hook_contract_guard] PASS "
        "first_calls=%s single_owner=%s ordered_merge=%s run_all=%s"
        % (
            len(calls),
            len(contracts.SINGLE_OWNER_HOOKS),
            len(contracts.ORDERED_MERGE_HOOKS),
            len(contracts.RUN_ALL_HOOKS),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
