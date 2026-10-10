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
FORM_SECTION_PATH = ROOT / "frontend/apps/web/src/components/template/FormSection.vue"
CHILD_SEQUENCE_PATH = ROOT / "frontend/apps/web/src/components/template/nativeChildSequence.ts"
VOCABULARY_MARKER = "Declared presentation vocabulary"
CONTAINER_MERGE = "...declaredPresentationTokens(node),"
# A declared layout container must reach its declared children.  The recursive
# child renderer inserts one wrapper node between a container and its children;
# the renderer must keep that wrapper transparent for every layout-container
# token it accepts, otherwise the declared grid/flex context is consumed by the
# wrapper (the overview cards collapsed to one full-width card per row).
LAYOUT_CONTAINER_WRAPPER_TOKENS = ("row", "d-flex", "d-inline-flex")
LAYOUT_CONTAINER_WRAPPER_MARKER = (
    ".native-container.row > .native-form-tree,\n"
    ".native-container.d-flex > .native-form-tree,\n"
    ".native-container.d-inline-flex > .native-form-tree {\n"
    "  display: contents;\n"
    "}"
)

# A declared layout container declares how its declared children are arranged.
# The renderer must therefore render each declared child as its own layout item
# instead of batching contiguous fields into one section card: the card carried
# `grid-column: 1/-1` plus inline-size containment, which collapsed a declared
# flex child to 0 width (the project stage row rendered as nothing).
LAYOUT_CONTAINER_SEGMENT_MARKER = "in renderSegments(node)"
LAYOUT_CONTAINER_ITEM_MARKER = ':frame="!isDeclaredLayoutContainer(node)"'
LAYOUT_CONTAINER_POLICY_MARKER = "declaredLayoutChildSegments(children, nodeType)"
LAYOUT_CONTAINER_POLICY_DECL = "export function declaredLayoutChildSegments<T>(nodes: readonly T[], typeOf: (node: T) => string) {"
LAYOUT_CONTAINER_TOKENS_DECL = "export const DECLARED_LAYOUT_CONTAINER_TOKENS = ['row', 'd-flex', 'd-inline-flex'];"
FORM_SECTION_FRAMELESS_REQUIRED = (
    ".template-form-section--frameless",
    "grid-column: auto",
    "container-type: normal",
)



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


def _renderer_layout_wrapper_errors(source: str) -> list[str]:
    if LAYOUT_CONTAINER_WRAPPER_MARKER in source:
        return []
    return [
        "every declared layout container token "
        f"{list(LAYOUT_CONTAINER_WRAPPER_TOKENS)} must make the recursive child wrapper "
        "transparent (`display: contents`); otherwise the wrapper consumes the declared "
        "layout context and the declared children fall outside it"
    ]


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

    # Native icon glyphs (``<i class="fa fa-lightbulb-o pe-2"/>``) are structural
    # decoration: the icon font supplies the glyph, so the marker classes are
    # classified explicitly and never published nor treated as unclassifiable,
    # while a real layout token declared on the same node must still survive.
    try:
        icon_tokens = module.declared_presentation_tokens(
            {"type": "i", "attributes": {"class": "fa fa-lightbulb-o pe-2"}}, "guard.c6",
        )
    except ValueError as exc:
        errors.append(f"an icon node must classify its glyph markers, not fail closed: {exc}")
        icon_tokens = None
    if icon_tokens is not None and icon_tokens != ["pe-2"]:
        errors.append(
            "an icon node must classify its glyph markers without publishing them and keep "
            f"the layout tokens declared beside them; got {icon_tokens!r}"
        )
    try:
        icon_only = module.declared_presentation_tokens(
            {"type": "i", "attributes": {"class": "fa fa-lightbulb-o"}}, "guard.c7",
        )
    except ValueError as exc:
        errors.append(f"an icon-only node must classify its glyph markers, not fail closed: {exc}")
        icon_only = None
    if icon_only:
        errors.append(
            "icon-only nodes declare no region presentation token and must publish none"
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


def _renderer_layout_item_errors(source: str, form_section: str, child_sequence: str) -> list[str]:
    errors: list[str] = []
    if LAYOUT_CONTAINER_TOKENS_DECL not in child_sequence:
        errors.append(
            "one declared layout-container vocabulary must be shared by the renderer and "
            f"the guard ({list(LAYOUT_CONTAINER_WRAPPER_TOKENS)}); expected "
            f"{LAYOUT_CONTAINER_TOKENS_DECL!r} in {CHILD_SEQUENCE_PATH.name}"
        )
    if LAYOUT_CONTAINER_POLICY_DECL not in child_sequence:
        errors.append(
            "the declared layout child policy must exist as one shared pure rule "
            f"({LAYOUT_CONTAINER_POLICY_DECL!r}) so both the renderer and its test bind it"
        )
    if LAYOUT_CONTAINER_SEGMENT_MARKER not in source:
        errors.append(
            "a declared layout container must render its declared children as declared "
            "items (one segment per declared child); batching them into one section card "
            "replaces the declared layout with a renderer-invented grid"
        )
    if LAYOUT_CONTAINER_POLICY_MARKER not in source:
        errors.append(
            "the renderer must consume the shared declared-layout child policy "
            f"({LAYOUT_CONTAINER_POLICY_MARKER!r}) for a declared layout container"
        )
    if LAYOUT_CONTAINER_ITEM_MARKER not in source:
        errors.append(
            "a declared layout container item must render without a section frame "
            f"({LAYOUT_CONTAINER_ITEM_MARKER}); a framed section card carries inline-size "
            "containment and collapses to 0 width inside the declared flex container"
        )
    missing = [marker for marker in FORM_SECTION_FRAMELESS_REQUIRED if marker not in form_section]
    if missing:
        errors.append(
            "FormSection must implement the declared layout item frame "
            f"(missing {missing}): without it the declared child keeps the card grid track "
            "and the inline-size containment that collapsed it"
        )
    return errors


def _self_test(source: str, vocabulary: frozenset, errors: list[str]) -> None:
    """Prove the renderer checks fail on the exact defect they guard."""
    form_section = FORM_SECTION_PATH.read_text(encoding="utf-8")
    child_sequence = CHILD_SEQUENCE_PATH.read_text(encoding="utf-8")
    dropped_facet = source.replace(CONTAINER_MERGE, "", 1)
    if dropped_facet == source:
        errors.append("self-test could not mutate the container class builder")
    elif not _renderer_consumption_errors(dropped_facet):
        errors.append("self-test: the dropped declared facet was not detected")

    dropped_wrapper = source.replace(LAYOUT_CONTAINER_WRAPPER_MARKER, "", 1)
    if dropped_wrapper == source:
        errors.append("self-test could not mutate the declared layout wrapper rule")
    elif not _renderer_layout_wrapper_errors(dropped_wrapper):
        errors.append("self-test: a declared layout wrapper that consumes the layout was not detected")

    batched_children = source.replace(LAYOUT_CONTAINER_SEGMENT_MARKER, "in childSegments(node)", 1)
    if batched_children == source:
        errors.append("self-test could not mutate the declared layout container segment rule")
    elif not _renderer_layout_item_errors(batched_children, form_section, child_sequence):
        errors.append(
            "self-test: a declared layout container that batches its declared children "
            "was not detected"
        )

    framed_item = source.replace(LAYOUT_CONTAINER_ITEM_MARKER, ':frame="true"', 1)
    if framed_item == source:
        errors.append("self-test could not mutate the declared layout container item frame")
    elif not _renderer_layout_item_errors(framed_item, form_section, child_sequence):
        errors.append(
            "self-test: a declared layout item that keeps the section frame was not detected"
        )

    framed_section = form_section.replace("container-type: normal;", "container-type: inline-size;", 1)
    if framed_section == form_section:
        errors.append("self-test could not mutate the frameless section rule")
    elif not _renderer_layout_item_errors(source, framed_section, child_sequence):
        errors.append(
            "self-test: a frameless section that keeps inline-size containment was not detected"
        )

    partial_vocabulary = child_sequence.replace(
        LAYOUT_CONTAINER_TOKENS_DECL, "export const DECLARED_LAYOUT_CONTAINER_TOKENS = ['row'];", 1,
    )
    if partial_vocabulary == child_sequence:
        errors.append("self-test could not mutate the declared layout-container vocabulary")
    elif not _renderer_layout_item_errors(source, form_section, partial_vocabulary):
        errors.append("self-test: a narrowed declared layout-container vocabulary was not detected")

    dropped_policy = child_sequence.replace(
        LAYOUT_CONTAINER_POLICY_DECL,
        "export function batchedLayoutChildSegments<T>(nodes: readonly T[], typeOf: (node: T) => string) {",
        1,
    )
    if dropped_policy == child_sequence:
        errors.append("self-test could not mutate the shared declared-layout child policy")
    elif not _renderer_layout_item_errors(source, form_section, dropped_policy):
        errors.append("self-test: a dropped shared declared-layout child policy was not detected")

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
    form_section = FORM_SECTION_PATH.read_text(encoding="utf-8")
    child_sequence = CHILD_SEQUENCE_PATH.read_text(encoding="utf-8")
    vocabulary = getattr(module, "FORM_PRESENTATION_LAYOUT_TOKENS", frozenset())

    _projection_checks(module, errors)
    _self_test(source, vocabulary, errors)
    errors.extend(_renderer_consumption_errors(source))
    errors.extend(_renderer_vocabulary_errors(source, vocabulary))
    errors.extend(_renderer_layout_wrapper_errors(source))
    errors.extend(_renderer_layout_item_errors(source, form_section, child_sequence))

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
