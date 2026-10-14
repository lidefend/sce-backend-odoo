#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fail-closed check that dictionary startup data never widens a scope silently.

``sc.dictionary`` carries ``scope_type`` values that are not all globally
deliverable. The startup projection used to publish every non-role row under the
``__global__`` bucket, so a company-scoped configuration row reached every
principal's contract. This guard reads source only and enforces the single scope
vocabulary:

* the projection bucket for ``global`` is ``__global__`` and for ``role`` is the
  row's own role code; any other scope has no bucket (it is dropped and counted,
  never promoted);
* the helper keeps that decision in one module instead of re-deriving it inline.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PROJECTION = REPO_ROOT / "addons" / "smart_core" / "core" / "dictionary_scope_projection.py"
HELPER = REPO_ROOT / "addons" / "smart_core" / "core" / "system_init_dictionary_data_helper.py"

FORBIDDEN_HELPER_TOKENS = (
    'else "__global__"',
    "else '__global__'",
)
REQUIRED_PROJECTION_TOKENS = (
    'GLOBAL_BUCKET = "__global__"',
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
        ("global", "anything"): "__global__",
        ("role", "role_manager"): "role_manager",
        ("role", ""): None,
        ("company", "8"): None,
        ("", "8"): None,
    }
    for (scope_type, scope_ref), expected in cases.items():
        actual = projection.projection_bucket(scope_type, scope_ref)
        if actual != expected:
            raise SystemExit(
                f"dictionary scope projection widened: {(scope_type, scope_ref)} -> {actual!r}, "
                f"expected {expected!r}"
            )
    if projection.DELIVERED_SCOPES != ("global", "role"):
        raise SystemExit(f"delivered scope vocabulary drifted: {projection.DELIVERED_SCOPES}")

    source = PROJECTION.read_text(encoding="utf-8")
    missing = sorted(token for token in REQUIRED_PROJECTION_TOKENS if token not in source)
    if missing:
        raise SystemExit(f"scope projection lost its declared vocabulary: {missing}")

    helper = HELPER.read_text(encoding="utf-8")
    widened = sorted(token for token in FORBIDDEN_HELPER_TOKENS if token in helper)
    if widened:
        raise SystemExit(f"startup helper still promotes an unknown scope to global: {widened}")
    if "projection_bucket(" not in helper:
        raise SystemExit("startup helper does not consume the single scope projection")
    print("OK system.init dictionary scope: global/role only, unknown scopes counted not published")


if __name__ == "__main__":
    main()
