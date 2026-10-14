#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fail-closed check that dictionary startup data never widens a scope silently.

``sc.dictionary`` carries three deliverable scopes: ``global`` (platform and
industry-module reference sets), ``company`` (one customer company) and
``role``. The startup projection used to publish every non-role row under the
``__global__`` bucket, so a company-scoped configuration row reached every
principal's contract.

The single vocabulary now lives in ``dictionary_scope_projection``:

* ``global`` maps to ``__global__`` and ``role`` to the row's own role code;
* ``company`` maps to ``__global__`` **only** when ``scope_ref`` names a company
  in the caller's authorized company reference set, and is withheld otherwise;
* any other scope has no bucket (it is dropped and counted, never promoted).

This guard reads source only and enforces that both producers consume that one
decision instead of re-deriving it inline, and that no producer can reintroduce
the ``company -> __global__`` promotion.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PROJECTION = REPO_ROOT / "addons" / "smart_core" / "core" / "dictionary_scope_projection.py"
HELPER = REPO_ROOT / "addons" / "smart_core" / "core" / "system_init_dictionary_data_helper.py"
INDUSTRY_ROWS = (
    REPO_ROOT / "addons" / "smart_construction_core" / "core_extension_system_init_rows.py"
)

PRODUCERS = {
    "system_init_dictionary_data_helper.py": HELPER,
    "core_extension_system_init_rows.py": INDUSTRY_ROWS,
}
FORBIDDEN_PRODUCER_TOKENS = (
    'else "__global__"',
    "else '__global__'",
    '"__global__"',
    "'__global__'",
)
REQUIRED_PROJECTION_TOKENS = (
    'GLOBAL_BUCKET = "__global__"',
    'COMPANY_SCOPE = "company"',
    "return None",
)


def load_projection():
    spec = importlib.util.spec_from_file_location("dictionary_scope_projection", PROJECTION)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    projection = load_projection()
    cases = {
        ("global", "anything", ()): "__global__",
        ("role", "role_manager", ()): "role_manager",
        ("role", "", ()): None,
        ("company", "8", ()): None,
        ("company", "8", ("8",)): "__global__",
        ("company", "", ("8",)): None,
        ("company", "9", ("8",)): None,
        ("", "8", ()): None,
    }
    for (scope_type, scope_ref, authorized), expected in cases.items():
        actual = projection.projection_bucket(scope_type, scope_ref, authorized)
        if actual != expected:
            raise SystemExit(
                f"dictionary scope projection drifted: {(scope_type, scope_ref, authorized)} "
                f"-> {actual!r}, expected {expected!r}"
            )
    if projection.DELIVERED_SCOPES != ("global", "company", "role"):
        raise SystemExit(f"delivered scope vocabulary drifted: {projection.DELIVERED_SCOPES}")

    source = PROJECTION.read_text(encoding="utf-8")
    missing = sorted(token for token in REQUIRED_PROJECTION_TOKENS if token not in source)
    if missing:
        raise SystemExit(f"scope projection lost its declared vocabulary: {missing}")

    for label, path in PRODUCERS.items():
        text = path.read_text(encoding="utf-8")
        widened = sorted(token for token in FORBIDDEN_PRODUCER_TOKENS if token in text)
        if widened:
            raise SystemExit(f"{label} still derives a global bucket inline: {widened}")
        if "scope_disposition(" not in text:
            raise SystemExit(f"{label} does not consume the single scope projection")
    print(
        "OK system.init dictionary scope: global/company/role via one projection; "
        "company delivery requires the caller's authorized company reference"
    )


if __name__ == "__main__":
    main()
