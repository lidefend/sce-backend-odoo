#!/usr/bin/env python3
"""Every raw workflow state a profile can meet is mapped to a business phase.

``WorkflowContractService.describe_record`` derives the published phase with::

    business_phase = profile["state_phase"].get(raw_state, raw_state or "unknown")

so a raw state the profile does not map is not an error: it silently becomes the
raw token and is then handed to ``_editability``, ``_approval_phase`` and the
statusbar projection.  A model whose ``Selection`` grew a value therefore keeps
looking healthy while a real business phase falls through the fallback path --
the same "silent subset" failure this family already hit once, when a regex read
only the inline half of the profile registry.

The guard closes the set in both directions, statically from the addon sources:

* **coverage** -- every value the profile's ``state_field`` Selection can take
  must be a key of ``state_phase``; a missing key is FAIL;
* **dead entries** -- a ``state_phase`` or ``state_actions`` key the Selection can
  never produce is dead configuration.  It is not deleted by the guard (that is a
  profile edit, not a guard decision) but it must be registered in
  ``config/contract/workflow_state_phase_dead_entries.v1.json`` with a reason, so
  the set cannot grow unnoticed.

The state set follows ``_inherit`` mixins, ``_inherits`` delegates and
``ScStateMachine.*_STATES``; it never comes from a generated report and it is
never skipped.  A model whose Selection cannot be resolved is FAIL with its own
message, because a guard that quietly narrows its own scope is exactly the
defect this file exists to prevent.
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "config/contract/workflow_state_phase_dead_entries.v1.json"
STATE_MACHINE = ROOT / "addons/smart_construction_core/models/support/state_machine.py"

sys.path.insert(0, str(Path(__file__).resolve().parent))
import workflow_contract_profile_loader as profile_loader  # noqa: E402


class StateSetError(RuntimeError):
    """A model's raw state set could not be resolved; the scan must not continue."""


def registry_label() -> str:
    """Path label that survives a redirected ``ROOT`` in tests."""
    try:
        return str(REGISTRY.relative_to(ROOT))
    except ValueError:
        return REGISTRY.name


class _Unknown:
    """Sentinel for an expression the literal evaluator does not understand."""

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return "<unknown>"


UNKNOWN = _Unknown()


def _const(node: ast.AST, consts: dict[str, Any]) -> Any:
    """Evaluate the literal subset used by state definitions and state machines."""
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.List):
        return [_const(item, consts) for item in node.elts]
    if isinstance(node, ast.Tuple):
        return tuple(_const(item, consts) for item in node.elts)
    if isinstance(node, ast.Name):
        return consts.get(node.id, UNKNOWN)
    if isinstance(node, ast.Call):
        func = node.func
        if isinstance(func, ast.Name) and func.id in ("_", "gettext") and node.args:
            return _const(node.args[0], consts)
        return UNKNOWN
    return UNKNOWN


def _string_list(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, (ast.List, ast.Tuple)):
        out = []
        for item in node.elts:
            if isinstance(item, ast.Constant) and isinstance(item.value, str):
                out.append(item.value)
        return out
    return []


def _delegate_bases(node: ast.AST) -> list[str]:
    """``_inherits`` keys: the models a delegating model reuses fields from."""
    return _string_list_keys(node)


def _string_list_keys(node: ast.AST) -> list[str]:
    if not isinstance(node, ast.Dict):
        return []
    out = []
    for key in node.keys:
        if isinstance(key, ast.Constant) and isinstance(key.value, str):
            out.append(key.value)
    return out


def _state_machine_states() -> dict[str, list[str]]:
    """``{'CONTRACT': ['draft', ...]}`` from ``ScStateMachine.*_STATES``."""
    try:
        tree = ast.parse(STATE_MACHINE.read_text(encoding="utf-8"))
    except OSError as exc:
        raise StateSetError(f"cannot read the state machine module: {exc}") from exc
    states: dict[str, list[str]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or node.name != "ScStateMachine":
            continue
        for stmt in node.body:
            if not isinstance(stmt, ast.Assign):
                continue
            for target in stmt.targets:
                if not isinstance(target, ast.Name) or not target.id.endswith("_STATES"):
                    continue
                values = _const(stmt.value, {})
                if not isinstance(values, list):
                    continue
                keys = [row[0] for row in values if isinstance(row, (list, tuple)) and row]
                states[target.id[: -len("_STATES")]] = keys
    if not states:
        raise StateSetError("no ScStateMachine.*_STATES list was found")
    return states


def _selection_keys(node: ast.AST, consts: dict[str, Any], machine: dict[str, list[str]]) -> list[str] | None:
    """Keys of a ``fields.Selection(...)`` assignment, or ``None`` if not one."""
    if not isinstance(node, ast.Call):
        return None
    func = node.func
    if not isinstance(func, ast.Attribute) or func.attr != "Selection":
        return None
    argument: ast.AST | None = node.args[0] if node.args else None
    if argument is None:
        for keyword in node.keywords:
            if keyword.arg == "selection":
                argument = keyword.value
    if argument is None:
        return None
    if isinstance(argument, ast.Call):
        inner = argument.func
        if isinstance(inner, ast.Attribute) and inner.attr == "selection" and argument.args:
            reference = argument.args[0]
            if isinstance(reference, ast.Attribute) and reference.attr in machine:
                return list(machine[reference.attr])
        return []
    values = _const(argument, consts)
    if not isinstance(values, list):
        return []
    keys = []
    for row in values:
        if isinstance(row, (list, tuple)) and row and isinstance(row[0], str):
            keys.append(row[0])
        else:
            return []
    return keys


def _state_keys_from_class(cls: ast.ClassDef, machine: dict[str, list[str]]) -> list[str]:
    consts: dict[str, Any] = {}
    for stmt in cls.body:
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Name):
                    consts[target.id] = _const(stmt.value, {})
    found: list[str] = []
    for stmt in cls.body:
        if not isinstance(stmt, ast.Assign):
            continue
        if not any(getattr(target, "id", None) == "state" for target in stmt.targets):
            continue
        keys = _selection_keys(stmt.value, consts, machine)
        if keys:
            found.extend(keys)
    return found


def _model_index() -> tuple[dict[str, list[ast.ClassDef]], dict[str, list[ast.ClassDef]]]:
    """``(by _name, by _inherit without _name)`` over the addon sources."""
    by_name: dict[str, list[ast.ClassDef]] = defaultdict(list)
    extensions: dict[str, list[ast.ClassDef]] = defaultdict(list)
    for path in sorted(ROOT.glob("addons/**/*.py")):
        parts = path.parts
        if "tests" in parts or "migrations" in parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            name: str | None = None
            inherits: list[str] = []
            delegates: list[str] = []
            for stmt in node.body:
                if not isinstance(stmt, ast.Assign):
                    continue
                for target in stmt.targets:
                    if not isinstance(target, ast.Name):
                        continue
                    if target.id == "_name":
                        value = _const(stmt.value, {})
                        if isinstance(value, str):
                            name = value
                    elif target.id == "_inherit":
                        inherits = _string_list(stmt.value)
                    elif target.id == "_inherits":
                        delegates = _delegate_bases(stmt.value)
            if name:
                by_name[name].append(node)
            elif inherits or delegates:
                # A class without ``_name`` extends its base in place.  A class
                # with its own ``_name`` only *uses* the base as a mixin; counting
                # it as an extension would pull that model's own state values into
                # the base's state set.
                for inherited in inherits + delegates:
                    extensions[inherited].append(node)
    return by_name, extensions


def _resolve_state_keys(
    model: str,
    index: tuple[dict[str, list[ast.ClassDef]], dict[str, list[ast.ClassDef]]],
    machine: dict[str, list[str]],
    seen: frozenset[str] | None = None,
) -> set[str]:
    """All raw state values ``model``'s ``state`` field can hold.

    The union is deliberate: it can only over-report a state (a visible FAIL),
    never under-report one (a silent PASS).
    """
    by_name, extensions = index
    seen = seen or frozenset()
    if model in seen:
        return set()
    seen = seen | {model}
    direct = list(by_name.get(model, ())) + list(extensions.get(model, ()))
    found: set[str] = set()
    bases: list[str] = []
    for cls in direct:
        found |= set(_state_keys_from_class(cls, machine))
        for stmt in cls.body:
            if not isinstance(stmt, ast.Assign):
                continue
            for target in stmt.targets:
                if not isinstance(target, ast.Name):
                    continue
                if target.id == "_inherit":
                    bases.extend(_string_list(stmt.value))
                elif target.id == "_inherits":
                    bases.extend(_delegate_bases(stmt.value))
    if found:
        return found
    for base in bases:
        if base == model:
            continue
        found |= _resolve_state_keys(base, index, machine, seen)
    return found


def registry_entries(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    entries: dict[str, dict[str, Any]] = {}
    for entry in payload.get("entries") or []:
        if isinstance(entry, dict) and str(entry.get("model") or "").strip():
            entries[str(entry["model"])] = entry
    return entries


def scan(profiles: dict[str, dict[str, Any]]) -> tuple[list[str], dict[str, list[str]], int]:
    """Return ``(coverage errors, dead entries by model, scanned models)``."""
    machine = _state_machine_states()
    index = _model_index()
    errors: list[str] = []
    dead: dict[str, list[str]] = {}
    for model in sorted(profiles):
        profile = profiles[model]
        field = str(profile.get("state_field") or "state")
        keys = _resolve_state_keys(model, index, machine)
        if not keys:
            errors.append(
                f"{model}: the {field!r} selection could not be resolved from the addon sources; "
                "the guard refuses to skip a model it cannot read"
            )
            continue
        phase = profile.get("state_phase")
        if not isinstance(phase, dict) or not phase:
            errors.append(f"{model}: the profile declares no state_phase mapping")
            continue
        missing = sorted(key for key in keys if key not in phase)
        if missing:
            errors.append(
                f"{model}: raw state {missing} is absent from state_phase, so the published "
                "businessPhase would silently fall back to the raw token"
            )
        state_actions = profile.get("state_actions")
        keys_dead = sorted(
            {f"phase:{key}" for key in phase if key not in keys}
            | {
                f"actions:{key}"
                for key in (state_actions if isinstance(state_actions, dict) else {})
                if key not in keys
            }
        )
        if keys_dead:
            dead[model] = keys_dead
    return errors, dead, len(profiles)


def validate(payload: dict[str, Any], profiles: dict[str, dict[str, Any]]) -> list[str]:
    if not profiles:
        return ["no workflow contract profile was found; the scan would be vacuous"]
    errors, dead, scanned = scan(profiles)
    if scanned != len(profiles):
        return ["the guard did not scan every profile; the scan would be a partial one"]
    registered = registry_entries(payload)
    for model in sorted(set(dead) - set(registered)):
        errors.append(
            f"{model}: {dead[model]} can never be produced by the model's Selection (dead profile "
            f"configuration); register it in {registry_label()} or drop it from the profile"
        )
    for model in sorted(set(registered) - set(dead)):
        errors.append(
            f"{model}: registered as carrying dead state entries but none were found "
            f"(now {dead.get(model, [])}); drop the stale entry"
        )
    for model in sorted(set(registered) & set(dead)):
        if [str(key) for key in registered[model].get("keys") or []] != dead[model]:
            errors.append(
                f"{model}: the registered dead entries do not match the computed ones "
                f"({dead[model]}); update the entry"
            )
        if not str(registered[model].get("reason") or "").strip():
            errors.append(f"{model}: registered without a reason")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    args = parser.parse_args()
    payload = json.loads(args.registry.read_text(encoding="utf-8"))
    try:
        profiles = profile_loader.load_profiles()
        errors = validate(payload, profiles)
    except (profile_loader.ProfileSourceError, StateSetError) as exc:
        print("Workflow state_phase coverage guard failed:")
        print(f"- a source could not be read in full: {exc}")
        return 1
    if errors:
        print("Workflow state_phase coverage guard failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    _, dead, scanned = scan(profiles)
    print(
        "Workflow state_phase coverage guard passed: "
        f"models={scanned} covered={scanned} dead_registered={len(dead)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
