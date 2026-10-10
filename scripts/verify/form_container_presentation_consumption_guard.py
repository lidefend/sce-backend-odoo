#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Guard that a declared container presentation facet is consumed, not dropped.

A native form arch declares container presentation with CSS classes.  The
projection publishes them on the renderer-neutral ``styleToken`` facet and fails
closed on a class it cannot classify.  The renderer implements that vocabulary
and merges the declared tokens into every container it renders.

The defect this guard prevents: the projection published the declaration, but
the renderer never consumed it (``containerClass()`` did not merge the declared
tokens and the product stylesheet implemented none of the vocabulary), so a
declared region rendered as an unstyled stack of full-width blocks.  Neither
layer reported an error, which is exactly why the region collapsed silently.

Checks (functional, negative-first):

1. The projection derives ``styleToken`` from the declared classes.
2. A class the renderer has no token for fails closed instead of shipping.
3. Native structural markers (``o_*``/``oe_*``) and exempt node types
   (field/button/widget) are not region presentation and never fail.
4. The renderer merges ``declaredPresentationTokens`` into the container class.
5. Every token the projection accepts has a rule in the renderer vocabulary.

Checks 4 and 5 are self-tested on a mutated renderer source, so the guard proves
it can fail rather than only pass.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HANDLERS = ROOT / "addons/smart_core/handlers"
RENDERER_PATH = ROOT / "frontend/apps/web/src/components/template/NativeFormTreeRenderer.vue"
VOCABULARY_MARKER = "Declared presentation vocabulary"
CONTAINER_MERGE = "...declaredPresentationTokens(node),"


def _load_projection():
    base = "sce_presentation_guard"
    root_package = sys.modules.setdefault(base, types.ModuleType(base))
    root_package.__path__ = [str(ROOT / "addons/smart_core")]
    for sub in ("handlers", "core"):
        package = sys.modules.setdefault(f"{base}.{sub}", types.ModuleType(f"{base}.{sub}"))
        package.__path__ = [str(ROOT / f"addons/smart_core/{sub}")]

    def _load(module_name: str):
        name = f"{base}.handlers.{module_name}"
        spec = importlib.util.spec_from_file_location(name, HANDLERS / f"{module_name}.py")
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module

    _load("ui_contract_v2_adapters")
    return _load("ui_contract_v2_projection")


def _renderer_consumption_errors(source: str) -> list[str]:
    errors: list[str] = []
    if CONTAINER_MERGE not in source:
        errors.append(
            "NativeFormTreeRenderer.containerClass must merge the declared presentation "
            "tokens; a declared facet that reaches the renderer and is dropped again "
            "reproduces the whole-region collapse"
        )
    return errors


def _renderer_vocabulary_errors(source: str, vocabulary: frozenset) -> list[str]:
    errors: list[str] = []
    if VOCABULARY_MARKER not in source:
        errors.append(
            "NativeFormTreeRenderer must carry the declared presentation vocabulary block "
            "that implements the tokens the projection publishes"
        )
        return errors
    missing = sorted(
        token for token in vocabulary
        if f".native-form-tree.native-form-tree .{token}" not in source
    )
    if missing:
        errors.append(
            "the renderer accepts these declared tokens but implements no rule for them: "
            f"{missing}"
        )
    return errors


def _projection_checks(module, errors: list[str]) -> None:
    vocabulary = getattr(module, "FORM_PRESENTATION_LAYOUT_TOKENS", frozenset())

    tokens = module.declared_presentation_tokens(
        {"type": "group", "attributes": {"class": "sc-project-overview d-flex mb-3"}}, "guard.c1",
    )
    for expected in ("sc-project-overview", "d-flex", "mb-3"):
        if expected not in tokens:
            errors.append(f"declared presentation class {expected!r} was not projected")

    try:
        module.declared_presentation_tokens(
            {"type": "group", "attributes": {"class": "text-truncate"}}, "guard.c2",
        )
    except ValueError:
        pass
    else:
        errors.append(
            "an unclassifiable declared presentation class must fail closed, not be "
            "silently dropped by the projection"
        )

    for node_type in ("field", "button", "widget"):
        try:
            module.declared_presentation_tokens(
                {"type": node_type, "attributes": {"class": "no-such-token"}}, "guard.c3",
            )
        except ValueError:
            errors.append(
                f"a {node_type} node declares its presentation elsewhere and must not be "
                "classified as region presentation"
            )

    if module.declared_presentation_tokens(
        {"type": "group", "attributes": {"class": "o_form_label oe_title btn btn-primary"}}, "guard.c4",
    ):
        errors.append(
            "native structural markers and control-btn classes are not region presentation"
        )

    unclassifiable = sorted(
        token for token in vocabulary
        if token not in module.declared_presentation_tokens(
            {"type": "group", "attributes": {"class": token}}, "guard.c5",
        )
    )
    if unclassifiable:
        errors.append(f"declared layout vocabulary is not classifiable: {unclassifiable}")

    tree = [{
        "type": "group",
        "name": "overview",
        "attributes": {"class": "sc-project-overview d-flex"},
        "children": [{"type": "field", "name": "partner_id"}],
    }]
    normalized = module.normalize_post_projected_container_tree({}, tree)
    if not normalized or normalized[0].get("styleToken") != "sc-project-overview d-flex":
        errors.append(
            "normalized container tree must publish the declared presentation on the "
            f"styleToken facet, got {normalized[0].get('styleToken') if normalized else None!r}"
        )


def _self_test(source: str, vocabulary: frozenset, errors: list[str]) -> None:
    """Prove the renderer checks fail on the exact defect they guard."""
    dropped_facet = source.replace(CONTAINER_MERGE, "", 1)
    if dropped_facet == source:
        errors.append("self-test could not mutate the container class builder")
    elif not _renderer_consumption_errors(dropped_facet):
        errors.append("self-test: the dropped declared facet was not detected")

    dropped_rule = source.replace(
        ".native-form-tree.native-form-tree .d-flex { display: flex; }", "", 1,
    )
    if dropped_rule == source:
        errors.append("self-test could not mutate a declared vocabulary rule")
    else:
        detected = _renderer_vocabulary_errors(dropped_rule, vocabulary)
        if not detected:
            errors.append("self-test: a declared token with no implementation was not detected")
    del vocabulary


def main() -> int:
    errors: list[str] = []
    module = _load_projection()
    source = RENDERER_PATH.read_text(encoding="utf-8")
    vocabulary = getattr(module, "FORM_PRESENTATION_LAYOUT_TOKENS", frozenset())

    _projection_checks(module, errors)
    _self_test(source, vocabulary, errors)
    errors.extend(_renderer_consumption_errors(source))
    errors.extend(_renderer_vocabulary_errors(source, vocabulary))

    if errors:
        print("[form_container_presentation_consumption_guard] FAIL")
        for error in errors:
            print(f" - {error}")
        return 2
    print(
        "[form_container_presentation_consumption_guard] PASS "
        f"vocabulary={len(vocabulary)} tokens"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
