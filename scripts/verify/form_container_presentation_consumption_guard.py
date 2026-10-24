#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Guard that a declared container presentation facet is consumed, not dropped.

A native form arch declares container presentation with CSS classes.  The
projection publishes the product-declared ones on the renderer-neutral
``styleToken`` facet and drops the native rendering markup it also carries
(Bootstrap grid/spacing, Odoo structural and icon decoration) instead of
promoting it or failing the page.  The renderer implements the declared
vocabulary and merges the declared tokens into every container it renders.

The defect this guard prevents: the projection published the declaration, but
the renderer never consumed it (``containerClass()`` did not merge the declared
tokens and the product stylesheet implemented none of the vocabulary), so a
declared region rendered as an unstyled stack of full-width blocks.  Neither
layer reported an error, which is exactly why the region collapsed silently.

Checks (functional, negative-first):

1. The projection derives ``styleToken`` from the declared classes.
2. Native arch markup is dropped: never published, never fatal.
3. Native structural markers (``o_*``/``oe_*``) and exempt node types
   (field/button/widget) are not region presentation and never fail.
4. The renderer merges ``declaredPresentationTokens`` into the container class.
5. Every token the projection accepts has a rule in the renderer vocabulary.

Checks 4 and 5 are self-tested on a mutated renderer source, so the guard proves
it can fail rather than only pass.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
import types
from pathlib import Path
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[2]
HANDLERS = ROOT / "addons/smart_core/handlers"
RENDERER_PATH = ROOT / "frontend/apps/web/src/components/template/NativeFormTreeRenderer.vue"
FORM_SECTION_PATH = ROOT / "frontend/apps/web/src/components/template/FormSection.vue"
CHILD_SEQUENCE_PATH = ROOT / "frontend/apps/web/src/components/template/nativeChildSequence.ts"
NATIVE_TEXT_PATH = ROOT / "frontend/apps/web/src/components/template/nativeTextPresentation.ts"
VUE_LOGIN_PATH = ROOT / "addons/smart_construction_core/views/web_login_views.xml"
VUE_SIGNUP_PATH = ROOT / "addons/smart_construction_core/views/signup_templates.xml"
OCA_INJECTION_TEMPLATE_PATH = (
    ROOT / "addons_external/oca_server_ux/base_tier_validation/templates/tier_validation_templates.xml"
)
OCA_INJECTION_MODEL_PATH = ROOT / "addons_external/oca_server_ux/base_tier_validation/models/tier_validation.py"
OCA_COMPONENT_PATH = (
    ROOT / "addons_external/oca_server_ux/base_tier_validation/static/src/components/"
    "tier_review_widget/tier_review_widget.xml"
)
GENERATED_CONTRACT_PATH = ROOT / "contracts/generated/product_view_structure_contract.json"
VOCABULARY_MARKER = "Declared presentation vocabulary"
CONTAINER_MERGE = "...declaredPresentationTokens(node),"
LEGACY_ALERT_TOKENS = frozenset({
    "alert", "alert-info", "alert-warning", "alert-danger", "alert-link",
})
LEGACY_VUE_REJECTION_MARKER = "export function assertNativePresentationConsumption"
LEGACY_HIDDEN_VALIDATION_MARKER = "validateNativePresentationDeclarations(nodes);"
LEGACY_EXPLICIT_OWNER_MARKER = "if (node.nodeComponent) return;"
CONSUMER_CLASSES = {
    "vue_form": "Vue native form declaration; explicit feedback component or ContractGapError",
    "qweb_native": "server-rendered QWeb page outside the Vue native-form renderer",
    "oca_qweb_injection": "QWeb template rendered by get_view and injected into native form arch",
    "oca_component": "OCA Owl component outside the Vue native-form renderer",
    "odoo_legacy_widget": "native Odoo widget outside the Vue native-form renderer",
    "generated_historical_snapshot": "historical/generated evidence only",
}
KNOWN_CONSUMER_SOURCES = {
    "frontend/apps/web/src/components/template/nativeTextPresentation.ts": "vue_form",
    "frontend/apps/web/src/components/template/NativeFormTreeRenderer.vue": "vue_form",
    "addons/smart_construction_core/views/web_login_views.xml": "qweb_native",
    "addons/smart_construction_core/views/signup_templates.xml": "qweb_native",
    "addons_external/oca_server_ux/base_tier_validation/templates/tier_validation_templates.xml":
        "oca_qweb_injection",
    "addons_external/oca_server_ux/base_tier_validation/static/src/components/"
    "tier_review_widget/tier_review_widget.xml": "oca_component",
    "addons/smart_construction_core/static/src/js/insight/insight_widget.js": "odoo_legacy_widget",
    "contracts/generated/product_view_structure_contract.json": "generated_historical_snapshot",
}
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
FORM_SECTION_FRAMELESS_SELECTOR = ".template-form-section--frameless"
FORM_SECTION_FRAMELESS_REQUIRED = {"grid-column": "auto", "container-type": "normal"}


def _frameless_rule_matches(source: str):
    # This is a deliberately bounded static check for the SFC's standalone
    # rule, not a CSS cascade evaluator. Comments and other selectors cannot
    # supply declarations for this rule. Duplicate rules fail closed below.
    styles = "\n".join(re.findall(r"<style\b[^>]*>(.*?)</style>", source, re.S))
    styles = re.sub(r"/\*.*?\*/", "", styles, flags=re.S)
    return list(re.finditer(
        r"(?:^|(?<=[{}]))\s*" + re.escape(FORM_SECTION_FRAMELESS_SELECTOR)
        + r"\s*\{(?P<body>[^{}]*)\}", styles, re.S,
    ))


def _frameless_rule_errors(source: str) -> list[str]:
    rules = _frameless_rule_matches(source)
    if len(rules) != 1:
        return ["FormSection must declare exactly one standalone frameless rule"]
    declarations = {}
    for declaration in rules[0].group("body").split(";"):
        if ":" in declaration:
            key, value = declaration.split(":", 1)
            declarations[key.strip()] = value.strip()
    return [
        f"FormSection {FORM_SECTION_FRAMELESS_SELECTOR}: {key} must be {expected}, "
        f"got {declarations.get(key)!r}"
        for key, expected in FORM_SECTION_FRAMELESS_REQUIRED.items()
        if declarations.get(key) != expected
    ]



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


def _declared_layout_span_errors(module) -> list[str]:
    """The arch declares layout; the projection must publish one span unit.

    The defect this guards: the arch's ``col`` / ``col-*`` / low-code
    ``field_size`` declarations reached the renderer as an ``attributes.col``
    beside a fixed ``span`` of 24, so the renderer had no declared width to
    consume and fell back to a private class vocabulary (a one-column stack
    that wrapped every value into a 112px column).  Baseline first, then the
    declared cases, then a negative control proving the derivation is what
    publishes the span.
    """
    errors: list[str] = []

    def child_spans(tree: list) -> list:
        normalized = module.normalize_post_projected_container_tree({}, tree)
        return [child.get("span") for child in (normalized[0].get("children") or [])]

    baseline_tree = module.normalize_post_projected_container_tree({}, [{
        "type": "group",
        "name": "baseline",
        "attributes": {"class": "text-muted"},
        "children": [{"type": "field", "name": "name"}],
    }])
    baseline = [child.get("span") for child in baseline_tree[0]["children"]]
    # Formal contract: native_view_reuse_frontend_spec_v1.md, layout coordinate
    # registration (line 371): P0 default=2 columns on the 24-unit grid.
    # Keep an independent oracle, not a value imported from the implementation.
    if baseline_tree[0].get("columns") != 2 or baseline != [12]:
        errors.append(
            "baseline: the contract requires default columns=2 and leaf span=12; "
            f"got columns={baseline_tree[0].get('columns')}, spans={baseline}"
        )

    four_columns = child_spans([{
        "type": "group",
        "name": "sc_project_information_basic",
        "cols": 4,
        "attributes": {"col": "4"},
        "children": [{"type": "field", "name": name} for name in
                     ("name", "project_code", "partner_id", "project_type_id")],
    }])
    if four_columns != [6, 6, 6, 6]:
        errors.append(
            'a group declaring col="4" declares four field columns, so each leaf must '

            f"publish span 6 of 24; got {four_columns} (the renderer then has no declared "
            "width and invents one)"
        )

    single_column = child_spans([{
        "type": "group", "name": "sc_project_information_responsibility", "col": 1,
        "children": [{"type": "field", "name": "sc_responsibility_matrix"}],
    }])
    if single_column != [24]:
        errors.append(f'a col="1" group must publish a full-row leaf; got {single_column}')

    explicit = child_spans([{
        "type": "group", "name": "declared", "cols": 2,
        "children": [
            {"type": "field", "name": "name", "span": 16},
            {"type": "field", "name": "project_code"},
        ],
    }])
    if explicit != [16, 12]:
        errors.append(
            "an explicit declared span must win over the container declaration and a leaf "
            f"without one must take the container width; got {explicit}"
        )

    low_code_size = child_spans([{
        "type": "group", "name": "lowcode", "cols": 3,
        "children": [
            {"type": "field", "name": "a", "field_size": "full"},
            {"type": "field", "name": "b", "attributes": {"class": "field--wide"}},
            {"type": "field", "name": "c"},
        ],
    }])
    if low_code_size != [24, 16, 8]:
        errors.append(
            "the low-code field size is a declared layout facet and must resolve to the "
            f"same 24-unit span; got {low_code_size}"
        )

    row_children = child_spans([{
        "type": "container", "name": "sc-project-cards", "attributes": {"class": "row g-2"},
        "children": [
            {"type": "container", "name": "card.a", "attributes": {"class": "col-12 col-md-6 col-lg-3"}},
            {"type": "container", "name": "card.b", "attributes": {"class": "col-12"}},
        ],
    }])
    if row_children != [6, 24]:
        errors.append(
            "a declared col-* row child is a layout declaration and must publish the "
            f"24-unit equivalent (widest declared breakpoint); got {row_children}"
        )

    original = module.descendant_field_column_span
    module.descendant_field_column_span = lambda columns: None
    try:
        mutated = child_spans([{
            "type": "group", "name": "mutated", "cols": 4,
            "children": [{"type": "field", "name": "name"}],
        }])
    finally:
        module.descendant_field_column_span = original
    if mutated == [6]:
        errors.append(
            "self-test: removing the declared field-column derivation did not change the "
            "published leaf span, so this check does not bind the derivation"
        )
    return errors


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


def classify_presentation_consumer(path: str) -> str:
    """Classify a declaration site by its actual runtime owner.

    Source-directory ownership is not enough: OCA QWeb templates are rendered
    by ``get_view`` and injected into form arch, while the OCA review table is
    an Owl component.  Generated contracts remain evidence, never a current
    Vue consumer.
    """
    if (
        path.startswith("scripts/verify/")
        or "/tests/" in path
        or path.startswith("tests/")
        or "/scripts/" in path
    ):
        return "test_fixture"
    if path.startswith("contracts/generated/"):
        return "generated_historical_snapshot"
    expected = KNOWN_CONSUMER_SOURCES.get(path)
    if expected:
        return expected
    if path.startswith("frontend/apps/web/src/") and path.endswith((".vue", ".ts")):
        return "vue_form"
    if path.startswith("addons_external/") and "/static/src/" in path:
        return "oca_component"
    if path.startswith("addons_external/") and "/templates/" in path:
        return "oca_qweb_injection"
    if path.startswith("addons/") and path.endswith(".xml"):
        return "qweb_native" if "<template" in (ROOT / path).read_text(encoding="utf-8") else "vue_form"
    return "unclassified"


def _qweb_template_ids(path: Path) -> set[str]:
    root = ElementTree.parse(path).getroot()
    return {
        str(node.get("id"))
        for node in root.iter("template")
        if node.get("id")
    }


def _legacy_feedback_consumption_errors(module, renderer: str, native_text: str) -> list[str]:
    errors: list[str] = []
    projection_legacy = getattr(module, "FORM_PRESENTATION_LEGACY_FEEDBACK_TOKENS", frozenset())
    projection_layout = getattr(module, "FORM_PRESENTATION_LAYOUT_TOKENS", frozenset())
    if set(projection_legacy) != LEGACY_ALERT_TOKENS:
        errors.append(
            "the projection must explicitly recognize every legacy feedback token; "
            f"got {sorted(projection_legacy)}"
        )
    overlap = LEGACY_ALERT_TOKENS & set(projection_layout)
    if overlap:
        errors.append(
            "legacy feedback tokens must not be layout presentation tokens; "
            f"CSS rules cannot satisfy their semantic ownership: {sorted(overlap)}"
        )
    for token in sorted(LEGACY_ALERT_TOKENS):
        published = module.declared_presentation_tokens(
            {"type": "div", "attributes": {"class": token}}, f"guard.legacy.{token}",
        )
        if token not in published:
            errors.append(f"legacy feedback token {token!r} must remain visible to the Vue rejection rule")

    if LEGACY_VUE_REJECTION_MARKER not in native_text:
        errors.append("native text must expose one explicit legacy-alert rejection entry")
    if "LEGACY_NATIVE_ALERT_TOKENS" not in native_text:
        errors.append("native text must carry the five-token legacy alert vocabulary")
    missing_native_tokens = sorted(
        token for token in LEGACY_ALERT_TOKENS if f"'{token}'" not in native_text
    )
    if missing_native_tokens:
        errors.append(f"native text legacy vocabulary is incomplete: {missing_native_tokens}")
    if LEGACY_EXPLICIT_OWNER_MARKER not in native_text:
        errors.append("explicit feedback/navigation node components must own their declarations")
    if "role: 'status'" not in native_text:
        errors.append("role=status must remain distinct from legacy role=alert rejection")
    if LEGACY_HIDDEN_VALIDATION_MARKER not in renderer:
        errors.append(
            "NativeFormTreeRenderer must validate declarations recursively before visibility filtering"
        )

    expected_templates = {
        VUE_LOGIN_PATH: {"sc_web_login_inherit"},
        VUE_SIGNUP_PATH: {"sc_auth_signup_buttons_cn", "sc_auth_signup_reset_cn"},
    }
    for path, required in expected_templates.items():
        try:
            template_ids = _qweb_template_ids(path)
        except (OSError, ElementTree.ParseError) as exc:
            errors.append(f"cannot verify QWeb template ownership for {path.relative_to(ROOT)}: {exc}")
            continue
        missing = sorted(required - template_ids)
        if missing:
            errors.append(f"QWeb native consumer templates missing from {path.relative_to(ROOT)}: {missing}")

    try:
        oca_templates = _qweb_template_ids(OCA_INJECTION_TEMPLATE_PATH)
    except (OSError, ElementTree.ParseError) as exc:
        errors.append(f"cannot verify OCA QWeb injection template: {exc}")
    else:
        if "tier_validation_label" not in oca_templates:
            errors.append("OCA tier-validation label template is no longer identifiable")
    oca_model = OCA_INJECTION_MODEL_PATH.read_text(encoding="utf-8")
    for marker in (
        '"base_tier_validation.tier_validation_label"',
        "node.addprevious(new_element)",
        "def get_view(",
    ):
        if marker not in oca_model:
            errors.append(
                "OCA tier-validation QWeb content is rendered and injected into native form arch; "
                f"missing ownership evidence {marker!r}"
            )
    oca_component = OCA_COMPONENT_PATH.read_text(encoding="utf-8")
    if "'alert-danger'" not in oca_component or "'alert-success'" not in oca_component:
        errors.append("OCA review-widget status classes must remain owned by the OCA component")

    generated = json.loads(GENERATED_CONTRACT_PATH.read_text(encoding="utf-8"))
    if not generated:
        errors.append("generated contract snapshot must remain readable as historical evidence")
    generated_relative = str(GENERATED_CONTRACT_PATH.relative_to(ROOT))
    if classify_presentation_consumer(generated_relative) != "generated_historical_snapshot":
        errors.append("generated contract tokens must not be classified as current Vue consumption")
    for path, expected in KNOWN_CONSUMER_SOURCES.items():
        actual = classify_presentation_consumer(path)
        if actual != expected:
            errors.append(f"consumer classification drift for {path}: expected {expected}, got {actual}")
        if actual not in CONSUMER_CLASSES:
            errors.append(f"consumer class has no documented rule: {actual}")
    return errors


def _legacy_consumption_self_test(module, renderer: str, native_text: str, errors: list[str]) -> None:
    """Mutate each semantic ownership fact; a string-only gate cannot pass."""
    missing_token = native_text.replace("  'alert-link',\n", "", 1)
    if missing_token == native_text:
        errors.append("self-test could not mutate the legacy alert vocabulary")
    elif not _legacy_feedback_consumption_errors(module, renderer, missing_token):
        errors.append("self-test: a missing legacy token was not detected")

    no_explicit_owner = native_text.replace(LEGACY_EXPLICIT_OWNER_MARKER, "", 1)
    if no_explicit_owner == native_text:
        errors.append("self-test could not mutate explicit feedback ownership")
    elif not _legacy_feedback_consumption_errors(module, renderer, no_explicit_owner):
        errors.append("self-test: explicit component ownership was not detected")

    no_hidden_validation = renderer.replace(LEGACY_HIDDEN_VALIDATION_MARKER, "", 1)
    if no_hidden_validation == renderer:
        errors.append("self-test could not mutate pre-visibility validation")
    elif not _legacy_feedback_consumption_errors(module, no_hidden_validation, native_text):
        errors.append("self-test: hidden/empty legacy declarations could bypass validation")


def _projection_checks(module, errors: list[str]) -> None:
    vocabulary = getattr(module, "FORM_PRESENTATION_LAYOUT_TOKENS", frozenset())

    tokens = module.declared_presentation_tokens(
        {"type": "group", "attributes": {"class": "sc-project-overview d-flex mb-3"}}, "guard.c1",
    )
    for expected in ("sc-project-overview", "d-flex", "mb-3"):
        if expected not in tokens:
            errors.append(f"declared presentation class {expected!r} was not projected")

    try:
        native_markup = module.declared_presentation_tokens(
            {
                "type": "group",
                "attributes": {"class": "text-truncate col oi mx-3 o_form_label btn"},
            },
            "guard.c2",
        )
    except ValueError as exc:
        errors.append(
            "native arch markup classes are rendering implementation and must be dropped "
            f"by the projection instead of failing the page: {exc}"
        )
    else:
        if native_markup:
            errors.append(
                "native arch markup (Bootstrap grid/spacing, Odoo decoration) must not be "
                f"promoted into the contract presentation facet; got {native_markup!r}"
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
    errors.extend(_frameless_rule_errors(form_section))
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

    # Mutate the target rule, never the first matching declaration elsewhere.
    rules = _frameless_rule_matches(form_section)
    body = rules[0].group("body") if len(rules) == 1 else ""
    framed_section = re.sub(
        re.escape(FORM_SECTION_FRAMELESS_SELECTOR) + r"(\s*\{)" + re.escape(body) + r"\}",
        lambda match: match.group(0).replace("container-type: normal;", "container-type: inline-size;", 1),
        form_section, count=1,
    ) if body else form_section
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
    native_text = NATIVE_TEXT_PATH.read_text(encoding="utf-8")
    form_section = FORM_SECTION_PATH.read_text(encoding="utf-8")
    child_sequence = CHILD_SEQUENCE_PATH.read_text(encoding="utf-8")
    vocabulary = getattr(module, "FORM_PRESENTATION_LAYOUT_TOKENS", frozenset())
    legacy_vocabulary = getattr(module, "FORM_PRESENTATION_LEGACY_FEEDBACK_TOKENS", frozenset())

    _projection_checks(module, errors)
    _self_test(source, vocabulary, errors)
    _legacy_consumption_self_test(module, source, native_text, errors)
    errors.extend(_renderer_consumption_errors(source))
    errors.extend(_renderer_vocabulary_errors(source, vocabulary))
    errors.extend(_renderer_layout_wrapper_errors(source))
    errors.extend(_renderer_layout_item_errors(source, form_section, child_sequence))
    errors.extend(_legacy_feedback_consumption_errors(module, source, native_text))
    errors.extend(_declared_layout_span_errors(module))

    if errors:
        print("[form_container_presentation_consumption_guard] FAIL")
        for error in errors:
            print(f" - {error}")
        return 2
    print(
        "[form_container_presentation_consumption_guard] PASS "
        f"layout_vocabulary={len(vocabulary)} legacy_feedback={len(legacy_vocabulary)} "
        "vue_reject_or_explicit_component=true qweb_oca_ownership=verified"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
