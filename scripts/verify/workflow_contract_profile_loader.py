#!/usr/bin/env python3
"""Single static reader for the workflow contract profile registry.

``workflow_contract_service.PROFILE_BY_MODEL`` mixes inline literals with
helper-generated entries::

    PROFILE_BY_MODEL = {
        "payment.request": {...},
        **_simple_approval_profiles(("sc.equipment.plan", ...)),
    }

A regex over the source text only sees the inline half.  A consumer that
trusted such a pattern silently scanned a subset of the contract -- the failure
mode that hid seven native buttons on the 25 helper-built models.

This module evaluates the dict expression instead, so every profile is present
however it was written.  Only literal expressions are supported: an unsupported
node raises :class:`ProfileSourceError` rather than returning a partial mapping,
because a consumer must never silently scan a subset of the contract.
"""
from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SERVICE = ROOT / "addons/smart_construction_core/models/support/workflow_contract_service.py"
PROFILE_ATTR = "PROFILE_BY_MODEL"

# Builtins a profile helper may use. ``dict`` covers the ``dict(profile)`` copy
# idiom; nothing here can reach the filesystem or the network.
_SAFE_BUILTINS = {
    "dict": dict,
    "list": list,
    "set": set,
    "tuple": tuple,
    "frozenset": frozenset,
    "str": str,
    "int": int,
    "bool": bool,
    "len": len,
    "sorted": sorted,
}


class ProfileSourceError(RuntimeError):
    """The registry could not be read in full; consumers must not proceed."""


def _eval(node: ast.AST, helpers: dict[str, Any]) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Dict):
        out: dict[Any, Any] = {}
        for key, value in zip(node.keys, node.values):
            if key is None:
                expanded = _eval(value, helpers)
                try:
                    out.update(expanded)
                except (TypeError, ValueError) as exc:
                    raise ProfileSourceError(f"unsupported ** mapping: {value!r}") from exc
                continue
            out[_eval(key, helpers)] = _eval(value, helpers)
        return out
    if isinstance(node, (ast.List, ast.Tuple)):
        return [_eval(item, helpers) for item in node.elts]
    if isinstance(node, ast.Name):
        if node.id == "_":
            return lambda text: text
        if node.id in helpers:
            return helpers[node.id]
        if node.id in _SAFE_BUILTINS:
            return _SAFE_BUILTINS[node.id]
        raise ProfileSourceError(f"unsupported name in profile registry: {node.id!r}")
    if isinstance(node, ast.Call):
        func = _eval(node.func, helpers)
        args = [_eval(arg, helpers) for arg in node.args]
        kwargs = {kw.arg: _eval(kw.value, helpers) for kw in node.keywords}
        try:
            return func(*args, **kwargs)
        except ProfileSourceError:
            raise
        except Exception as exc:  # noqa: BLE001 - surfaced as a source error
            raise ProfileSourceError(f"profile helper {ast.unparse(node)!r} failed: {exc}") from exc
    raise ProfileSourceError(f"unsupported expression in profile registry: {type(node).__name__}")


def _helper_namespace(tree: ast.Module) -> dict[str, Any]:
    namespace: dict[str, Any] = {"__builtins__": _SAFE_BUILTINS}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name.startswith("_"):
            module = ast.Module(body=[node], type_ignores=[])
            try:
                exec(compile(ast.fix_missing_locations(module), "<workflow_contract_service>", "exec"), namespace)  # noqa: S102
            except Exception as exc:  # noqa: BLE001
                raise ProfileSourceError(f"profile helper {node.name!r} could not be compiled: {exc}") from exc
    return namespace


def load_profiles(service: Path = DEFAULT_SERVICE) -> dict[str, dict[str, Any]]:
    """Return every declared profile, inline and helper-built alike."""
    try:
        tree = ast.parse(service.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ProfileSourceError(f"cannot read workflow contract service: {exc}") from exc

    helpers = _helper_namespace(tree)
    target: ast.AST | None = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            getattr(t, "id", None) == PROFILE_ATTR for t in node.targets
        ):
            target = node.value
            break
    if target is None:
        raise ProfileSourceError(f"{PROFILE_ATTR} assignment not found in {service}")

    profiles = _eval(target, helpers)
    if not isinstance(profiles, dict) or not profiles:
        raise ProfileSourceError(f"{PROFILE_ATTR} did not evaluate to a non-empty mapping")
    for model, profile in profiles.items():
        if not isinstance(model, str) or not isinstance(profile, dict):
            raise ProfileSourceError(
                f"{PROFILE_ATTR} contains a non-profile entry: {model!r} -> {type(profile).__name__}"
            )
    return profiles


def adopted_models(profiles: dict[str, dict[str, Any]]) -> set[str]:
    """Models the contract actually publishes a profile for."""
    return set(profiles)


def declared_methods(profiles: dict[str, dict[str, Any]]) -> set[str]:
    """Every method any profile binds to a contract action."""
    methods: set[str] = set()
    for profile in profiles.values():
        binding = profile.get("method_by_action")
        if not isinstance(binding, dict):
            continue
        methods |= {value for value in binding.values() if isinstance(value, str) and value}
    return methods
