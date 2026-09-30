#!/usr/bin/env python3
"""Every native object button on a workflow-adopted model is accounted for.

The workflow contract publishes a subset of the native form actions.  Anything
the contract does not publish stays invisible to the Web -- which is the right
default for a business action whose meaning nobody has declared, but a silent
one: a button that really drives a state transition would simply disappear from
the adopted page with no record that it was ever there.

This guard makes that set explicit and fail-closed:

* a native ``type="object"`` button on an adopted model whose method no profile
  declares must be registered in
  ``config/contract/native_view_undeclared_actions.v1.json`` with its nature;
* an entry that no longer appears in any native view is stale and must go;
* an entry whose method is now declared by a contract profile is stale too --
  the registration must not outlive the gap it records.

Scope note: the model set and the declared-method set both come from statically
evaluating ``PROFILE_BY_MODEL`` (see ``workflow_contract_profile_loader``).  The
registry mixes inline literals with helper calls such as
``**_simple_approval_profiles((...))``; a regex over the source text sees only the
inline half and silently scans a subset of the contract.  Declared methods are
bound to their own model: a same-named method on another model cannot cover
a missing business action.

The guard never proposes a meaning.  Deciding whether a native transition needs
a declared purpose is a business call; the registry records where that has not
happened yet, so the gap is visible instead of silent.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "config/contract/native_view_undeclared_actions.v1.json"

sys.path.insert(0, str(Path(__file__).resolve().parent))
import workflow_contract_profile_loader as profile_loader  # noqa: E402

CLASSES = {
    "state_transition_undeclared",
    "navigation",
    "document_helper",
}

RECORD_RE = re.compile(r'<record[^>]*model="ir\.ui\.view"[^>]*>(.*?)</record>', re.S)
MODEL_RE = re.compile(r'<field name="model">\s*([A-Za-z0-9_.]+)\s*</field>')
BUTTON_RE = re.compile(r"<button\b([^>]*)>", re.S)
NAME_RE = re.compile(r'\bname="([^"]+)"')


def adopted_models() -> set[str]:
    """Models the contract actually publishes a profile for.

    Helper-built profiles count: the registry is evaluated, not pattern-matched.
    """
    return profile_loader.adopted_models(profile_loader.load_profiles())


def declared_methods() -> set[tuple[str, str]]:
    """Model-bound methods; another model cannot supply an action declaration."""
    return {
        (model, method)
        for model, profile in profile_loader.load_profiles().items()
        for method in profile_loader.declared_methods({model: profile})
    }


def native_object_buttons(models: set[str]) -> dict[tuple[str, str], int]:
    """(model, method) -> occurrence count for native form-view object buttons."""
    found: dict[tuple[str, str], int] = defaultdict(int)
    for path in ROOT.glob("addons/**/views/**/*.xml"):
        text = path.read_text(encoding="utf-8", errors="replace")
        for body in RECORD_RE.findall(text):
            match = MODEL_RE.search(body)
            if not match:
                continue
            model = match.group(1)
            if model not in models:
                continue
            for attrs in BUTTON_RE.findall(body):
                if 'type="object"' not in attrs:
                    continue
                name = NAME_RE.search(attrs)
                if not name:
                    continue
                found[(model, name.group(1))] += 1
    return dict(found)


def load_registry() -> dict[str, Any]:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def registered_entries(payload: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    entries: dict[tuple[str, str], dict[str, Any]] = {}
    for entry in payload.get("entries") or []:
        if not isinstance(entry, dict):
            continue
        entries[(str(entry.get("model") or ""), str(entry.get("method") or ""))] = entry
    return entries


def validate(payload: dict[str, Any]) -> list[str]:
    models = adopted_models()
    if not models:
        return ["no workflow projection profile was found; the scan would be vacuous"]
    declared = declared_methods()
    buttons = native_object_buttons(models)
    if not buttons:
        return ["no native object button was found on an adopted model; the scan would be vacuous"]

    expected = {key for key in buttons if key not in declared}
    entries = registered_entries(payload)
    errors: list[str] = []

    for key in sorted(expected - set(entries)):
        errors.append(
            f"{key[0]}: native button {key[1]!r} drives an object method the workflow contract "
            f"does not declare; register its nature in {REGISTRY.relative_to(ROOT)}"
        )
    for key in sorted(set(entries) - expected):
        if key in declared:
            errors.append(
                f"{key[0]}: {key[1]!r} is registered as undeclared but a contract profile now "
                f"declares it; drop the stale entry"
            )
        else:
            errors.append(
                f"{key[0]}: {key[1]!r} is registered but no native form view uses it anymore; "
                f"drop the stale entry"
            )
    for key, entry in sorted(entries.items()):
        classification = str(entry.get("class") or "")
        if classification not in CLASSES:
            errors.append(
                f"{key[0]}: {key[1]!r} has class {classification!r}; expected one of {sorted(CLASSES)}"
            )
        if not str(entry.get("reason") or "").strip():
            errors.append(f"{key[0]}: {key[1]!r} is registered without a reason")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    args = parser.parse_args()
    payload = json.loads(args.registry.read_text(encoding="utf-8"))
    try:
        errors = validate(payload)
    except profile_loader.ProfileSourceError as exc:
        print("Native view workflow action coverage guard failed:")
        print(f"- the workflow contract profile registry could not be read: {exc}")
        return 1
    if errors:
        print("Native view workflow action coverage guard failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    counts: dict[str, int] = defaultdict(int)
    for entry in (payload.get("entries") or []):
        counts[str(entry.get("class"))] += 1
    print(
        "Native view workflow action coverage guard passed: "
        f"registered={sum(counts.values())} "
        + " ".join(f"{name}={counts[name]}" for name in sorted(counts))
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
