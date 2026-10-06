#!/usr/bin/env python3
"""Static architecture guard for the production scene-component bridge."""

from __future__ import annotations

import hashlib
import json
import posixpath
import re
import ast
import unicodedata
from pathlib import Path

from contract_form_semantic_identity_guard import validate_semantic_identity_projection
from scene_audit_disclosure_guard import audit_disclosure_is_governed


ROOT = Path(__file__).resolve().parents[2]
WEB_SRC = ROOT / "frontend/apps/web/src"
UI_SRC = ROOT / "frontend/packages/ui/src"


def source_files(root: Path):
    yield from root.rglob("*.ts")
    yield from root.rglob("*.vue")


_CHECKS = 0


def require(condition: bool, message: str) -> None:
    global _CHECKS
    _CHECKS += 1
    if not condition:
        raise SystemExit(f"[verify.frontend.scene_component_bridge.guard] FAIL {message}")


_HTML_VOID_ELEMENTS = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)


def _scan_tags(source: str) -> list[tuple[str, str, int, int, bool]]:
    """`(kind, name, start, end, self_closing)` for every tag, read quote-aware.

    A `<` inside a quoted attribute value cannot open a tag: the enclosing start
    tag is read to the first `>` *outside quotes* and the scan resumes after it.
    That matters for the element spans below - a decoy such as
    `:data="'<ObjectTaskPage>'"` used to be counted as a second opening tag, which
    made the span of the flag-carrying element swallow the rest of the template and
    adopt a region slot that had already been moved out of it.

    Two further decoys are excluded.  A `{{ ... }}` interpolation is not markup:
    Vue reads it as an expression, so `{{ '' /* '</CanonicalActionBar>' */ }}` used
    to close an element for this scanner while the compiled render function kept the
    slot inside it.  And an HTML void element (`<br>`, `<img>`, `<input>`, ...) has
    no closing tag, so treating it as an unterminated child made a legal direct-child
    layout look like a slot nested under that child.
    """
    tokens: list[tuple[str, str, int, int, bool]] = []
    index = 0
    length = len(source)
    while index < length:
        start = source.find("<", index)
        interpolation = source.find("{{", index)
        if interpolation != -1 and (start == -1 or interpolation < start):
            interpolation_end = source.find("}}", interpolation + 2)
            index = length if interpolation_end == -1 else interpolation_end + 2
            continue
        if start == -1:
            break
        if source.startswith("<!--", start):
            comment_end = source.find("-->", start + 4)
            index = length if comment_end == -1 else comment_end + 3
            continue
        if source.startswith("<!", start):
            declaration_end = source.find(">", start + 2)
            index = length if declaration_end == -1 else declaration_end + 1
            continue
        closing = source.startswith("</", start)
        cursor = start + (2 if closing else 1)
        if cursor >= length or not source[cursor].isalpha():
            index = start + 1
            continue
        name_match = re.match(r"[A-Za-z][\w:.-]*", source[cursor:])
        assert name_match is not None
        name = name_match.group(0)
        cursor += len(name)
        if closing:
            while cursor < length and source[cursor] != ">":
                cursor += 1
            tokens.append(("close", name, start, min(cursor + 1, length), False))
            index = cursor + 1
            continue
        quote = ""
        while cursor < length:
            character = source[cursor]
            if quote:
                if character == quote:
                    quote = ""
            elif character in ("'", '"'):
                quote = character
            elif character == ">":
                cursor += 1
                break
            cursor += 1
        tag = source[start:cursor]
        tokens.append(
            (
                "open",
                name,
                start,
                cursor,
                tag.rstrip().endswith("/>") or name.lower() in _HTML_VOID_ELEMENTS,
            )
        )
        index = cursor
    return tokens


def _template_before_script(source: str) -> str:
    """The source up to the first real `<script>` start tag.

    `source.split("<script", 1)[0]` is not that.  A bare `<script` inside a quoted
    attribute value (`data-note="<script"`) or inside an HTML comment was read as the
    start of the script block, the template was cut short, and the surface call that
    follows the attribute was reported missing.  The shared tag scan skips comments
    and reads a start tag to the first `>` outside quotes, so the boundary is the
    script block the SFC parser would see.
    """
    for kind, name, start, _end, _self_closing in _scan_tags(source):
        if kind == "open" and name.lower() == "script":
            return source[:start]
    return source


def native_surface_bridge_errors(host: str, surface: str) -> list[str]:
    """Check the extracted surface's live input/output bindings, not old host markers."""
    def calls(source: str, tag: str) -> list[dict[str, str]]:
        # The template is everything before the first *real* `<script` start tag.
        # Splitting on the raw substring read `<!-- <script> -->` and a
        # `data-note="<script"` attribute value as the start of the script block,
        # handed the check an empty template and rejected a file that renders.
        template = _template_before_script(source)
        return [
            {name: value for name, _, value in re.findall(r'''([:@\w-]+)\s*=\s*(["'])(.*?)\2''', call, re.S)}
            for call in re.findall(r"<" + tag + r"\b[\s\S]*?/>", template)
        ]

    errors = []
    host_calls = calls(host, "CanonicalNativeFormSurface")
    bindings = {
        ":native-bridge": "nativeBridge", ":section-links": "workspaceSectionLinks",
        ":render-mode": "renderModel.identity.mode", ":relation-adapter": "relationAdapter",
        **{f"@{event}": f"emit('{event}', $event)" for event in ("field-change", "field-action", "action-ref")},
    }
    if len(host_calls) != 2 or any(any(call.get(key) != value for key, value in bindings.items()) for call in host_calls):
        errors.append("task and workspace surfaces must forward the canonical bridge, mode and events")
    if "from './CanonicalNativeFormSurface.vue'" not in host or "nativeBridge.value?.sectionLinks" not in host:
        errors.append("host must import the surface and consume bridge-owned navigation")
    renderers = calls(surface, "NativeFormTreeRenderer")
    required = {
        ":field-schemas-for-nodes": "nativeBridge.fieldSchemasForNodes",
        ":is-node-visible": "nativeBridge.nodeVisible",
        ":relation-adapter": "relationAdapter",
        ":native-action-handler": "runNativeCanonicalAction",
        ":native-action-state-resolver": "nativeBridge.actionStateForNode",
        ":prefer-readonly-facts": "renderMode === 'readonly'",
        **{f"@{event}": f"emit('{event}', $event)" for event in ("field-change", "field-action")},
    }
    if (len(renderers) != 2
            or [call.get(":nodes") for call in renderers] != ["nativeBridge.primaryNodes", "nativeBridge.subordinateNodes"]
            or any(any(call.get(key) != value for key, value in required.items()) for call in renderers)):
        errors.append("native surface must preserve both zones, field schemas, visibility and action authority")
    navigation = calls(surface, "FormSectionNavigation")
    if len(navigation) != 1 or navigation[0].get(":items") != "sectionLinks":
        errors.append("native navigation must consume the supplied section links")
    if "props.nativeBridge?.actionForPayload(payload)" not in surface or "if (action) emit('action-ref', action)" not in surface:
        errors.append("native actions must resolve through bridge authority before forwarding")
    return errors


vendor_import = re.compile(r"(?:from\s+|import\s*\()['\"](?:tdesign-vue-next)")
web_vendor_hits = [
    str(path.relative_to(ROOT))
    for path in source_files(WEB_SRC)
    if vendor_import.search(path.read_text(encoding="utf-8"))
]
require(not web_vendor_hits, f"vendor imports escaped driver package: {web_vendor_hits}")

business_tokens = ("payment.request", "sc.payment.execution", "付款申请")
ui_business_hits = [
    str(path.relative_to(ROOT))
    for path in source_files(UI_SRC)
    if any(token in path.read_text(encoding="utf-8") for token in business_tokens)
]
require(not ui_business_hits, f"business-specific knowledge entered generic UI package: {ui_business_hits}")

web_package = json.loads((ROOT / "frontend/apps/web/package.json").read_text(encoding="utf-8"))
require(web_package.get("dependencies", {}).get("@sc/ui") == "workspace:*", "web workspace dependency missing")

ui_package = json.loads((ROOT / "frontend/packages/ui/package.json").read_text(encoding="utf-8"))
exports = ui_package.get("exports", {})
require(exports.get("./bridge") == "./src/bridge.ts", "pure bridge export missing")
require(exports.get("./collection") == "./src/collection.ts", "collection export missing")
require(exports.get("./form") == "./src/form.ts", "form export missing")

wrapper = (WEB_SRC / "components/action/SceneReadonlyCollectionRenderer.vue").read_text(encoding="utf-8")
require("from '@sc/ui/collection'" in wrapper, "renderer must use narrow collection export")
require(
    "data-scene-driver-chooser" not in wrapper
    and "scene-driver-chooser" not in wrapper,
    "component supplier chooser returned to the ordinary collection product surface",
)
form_host = (WEB_SRC / "pages/contractForm/ContractFormDriverHost.vue").read_text(encoding="utf-8")
native_surface = (WEB_SRC / "pages/contractForm/CanonicalNativeFormSurface.vue").read_text(encoding="utf-8")
contract_form_page = (WEB_SRC / "pages/ContractFormPage.vue").read_text(encoding="utf-8")
web_index = (ROOT / "frontend/apps/web/index.html").read_text(encoding="utf-8")
object_task_page = (WEB_SRC / "pages/contractForm/ObjectTaskPage.vue").read_text(encoding="utf-8")
contract_form_vm = (WEB_SRC / "pages/contractForm/contractRuntimeVm.ts").read_text(encoding="utf-8")
frontend_makefile = (ROOT / "make/frontend.mk").read_text(encoding="utf-8")
# The target can also be redefined from another included `.mk`, so the definition
# count and the variable-composed-target scan run over the whole make surface.
other_make_sources = tuple(
    path.read_text(encoding="utf-8")
    for path in [ROOT / "Makefile", *sorted((ROOT / "make").glob("*.mk"))]
    if path.name != "frontend.mk"
)
professional_audit_timeline = (WEB_SRC / "pages/contractForm/ProfessionalAuditTimeline.vue").read_text(encoding="utf-8")
canonical_action_bar = (WEB_SRC / "pages/contractForm/CanonicalActionBar.vue").read_text(encoding="utf-8")
form_floorplan = (WEB_SRC / "app/presentation/canonicalFormFloorplan.ts").read_text(encoding="utf-8")
canonical_native_bridge = (WEB_SRC / "pages/contractForm/canonicalNativeFormBridge.ts").read_text(encoding="utf-8")
action_executor = (WEB_SRC / "pages/contractForm/canonicalFormActionExecutor.ts").read_text(encoding="utf-8")
presenter = (WEB_SRC / "app/presentation/contractFormPresenter.ts").read_text(encoding="utf-8")
v2_assembler = (ROOT / "addons/smart_core/core/unified_page_contract_v2_assembler.py").read_text(encoding="utf-8")
v2_handler = (ROOT / "addons/smart_core/handlers/ui_contract_v2.py").read_text(encoding="utf-8")
v2_projection = (ROOT / "addons/smart_core/handlers/ui_contract_v2_projection.py").read_text(encoding="utf-8")
require("from '@sc/ui/form'" in form_host, "form driver host must use narrow form export")
require(
    "SceneUiProvider" in form_host
    and "ObjectTaskPage" in form_host
    and "buildCanonicalNativeFormBridge" in form_host
    and not native_surface_bridge_errors(form_host, native_surface),
    "form driver does not retain the product floorplan plus governed native surface bridge: "
    + "; ".join(native_surface_bridge_errors(form_host, native_surface)),
)
require(
    "composeCanonicalFormFloorplan" in form_host
    and '<TaskFormPattern v-if="renderModel.identity.presentationMode === \'task\'"' in form_host
    and '<WorkspaceFormPattern v-else' in form_host
    and '<article class="sc-native-contract-page" data-native-contract-structure>' in native_surface
    and "nativeBridge.primaryNodes" in native_surface
    and "nativeBridge.subordinateNodes" in native_surface,
    "semantic readonly forms must use the canonical floorplan while native structure remains an explicit fallback",
)
require("CanonicalFormNodeRenderer" in object_task_page, "object-task floorplan does not render canonical form nodes")
require("renderModel.zones" in form_floorplan, "floorplan does not consume canonical zones")
require(
    "renderModel.zones.primary.map(mapNode)" in canonical_native_bridge
    and "renderModel.zones.subordinate" in canonical_native_bridge
    and "canonicalFieldToFormSection(field" in canonical_native_bridge
    and ("name: field.widgetId" in canonical_native_bridge or "canonicalWidgetId: field.widgetId" in canonical_native_bridge)
    and "name: field.fieldCode" in canonical_native_bridge,
    "canonical native bridge does not preserve normalized hierarchy and field occurrence identity",
)
for forbidden_floorplan_fact in ("payment.request", "sc.payment.execution", "付款申请", "财务经理"):
    require(
        forbidden_floorplan_fact not in form_floorplan
        and forbidden_floorplan_fact not in object_task_page
        and forbidden_floorplan_fact not in canonical_native_bridge,
        f"generic object-task floorplan contains business inference: {forbidden_floorplan_fact}",
    )
require("SceneObjectPageContract" not in form_host, "ContractForm driver host must not consume the UI-internal SceneObjectPage DTO")
require("data-contract-form-driver-error" in form_host, "invalid normalized form contract does not fail closed")
require(
    "floorplan.value.decisionMode ? 'tdesign-modern' : activeKit.value" in form_host
    and ':kit="renderKit"' in form_host
    and 'fallback-kit="sc-native"' in form_host,
    "semantic readonly product pages must default to TDesign with native fallback",
)
require(
    "showUserDriverChooser?: boolean" in form_host
    and "props.driverConfig?.showUserDriverChooser === true" in form_host,
    "user-visible component supplier chooser is not default-closed behind an explicit product exposure",
)
require(
    "showUserDriverChooser: false" in (WEB_SRC / "pages/contractForm/useContractFormComponentDriverRuntime.ts").read_text(encoding="utf-8"),
    "ContractForm runtime exposes the component supplier chooser by default",
)
require(
    "['primary', 'secondary'].includes(action.tier)" in form_host
    and "['overflow', 'configuration'].includes(action.tier)" in form_host
    and ":data-action-tier=\"action.key === effectivePrimaryKey ? 'primary' : action.tier\"" in canonical_action_bar
    and ":data-normalized-action-tier=\"action.tier\"" in canonical_action_bar,
    "form driver does not mechanically preserve normalized action tiers",
)
require(
    "canonicalFormActionIconClass(action.icon)" in canonical_action_bar
    and "canonical-action-bar__icon" in canonical_action_bar
    and "SceneButton" in canonical_action_bar
    and "action.actionRef" in canonical_action_bar
    and "workflowDisabledReason(action)" in canonical_action_bar
    and "action.presentation?.icon" in presenter,
    "native and semantic action bars do not preserve canonical action identity and icon",
)
require(
    '/web/static/lib/fontawesome/css/font-awesome.css' not in web_index
    and '<ScIcon v-if="canonicalFormActionIconClass(action.icon)"' in canonical_action_bar,
    "canonical action icons must render locally without coupling the product shell to an Odoo web asset",
)
require(
    "var(--sc-semantic-surface-interactive)" in form_host
    and "var(--sc-semantic-text-on-interactive) !important" in form_host,
    "primary action does not consume the registered interactive contrast tokens",
)
require("normalizeActionSemantics" in action_executor and "?.executor === 'record.save'" in action_executor and "!actionRef.actionSemanticsInvalid" in action_executor, "canonical persistence intent is not bridged to the unified save executor")
canonical_node_renderer = (WEB_SRC / "pages/contractForm/CanonicalFormNodeRenderer.vue").read_text(encoding="utf-8")
native_renderer = (WEB_SRC / "components/template/NativeFormTreeRenderer.vue").read_text(encoding="utf-8")
require(
    "mode === 'readonly'" in presenter and "normalizeActionSemantics(action))?.kind === 'persistence'" in presenter,
    "iteration one must retain the cb6e276 readonly save boundary",
)
require(
    "relationParts" in presenter and "displayName" in presenter and "relationModel(widget)" in presenter,
    "canonical relation fields do not retain normalized business display identity",
)
require(
    (
        "filter(isFormActionBarAction)" in presenter
        or "isFormActionBarAction(action.actionRef)" in presenter
    )
    and "primaryResolution).winner" in presenter
    and "retainAuthoritativeActionOccurrences(actionCandidates, primaryWinnerIdentity)" in presenter
    and "demotedActionIds.has(action.actionRef.actionId)" not in presenter
    and "sourceWidgetId === 'page.root'" in presenter
    and "targetScope === 'footer'" in presenter,
    "canonical form action collection does not retain demoted secondary actions while honoring the backend winner",
)
require(
    "actionsByIdentity.get(actionIdentity)" in presenter
    and "node.action.actionRef" in canonical_node_renderer,
    "native body action occurrences must reuse canonical action references",
)
recursive_node_call = canonical_node_renderer[
    canonical_node_renderer.index("<CanonicalFormNodeRenderer"):
    canonical_node_renderer.index("</section>")
]
require(
    '@action-ref="emit(\'action-ref\', $event)"' in recursive_node_call,
    "recursive canonical node actions do not reach the unified executor adapter",
)
require(
    'action_id = "form.save"' in v2_assembler
    and 'required_right = "create" if render_profile == "create" else "write"' in v2_assembler,
    "normalized form.save is not derived from exact create/write permission",
)
require("_apply_normalized_action_surface_policy" not in v2_assembler, "iteration one must not repartition canonical actions")
require(
    "apply_product_field_roles(container_tree)" in v2_projection
    and "business_config_group_" not in v2_projection
    and "native_subordinate_relations" not in v2_projection
    and "remove_fields(" not in v2_projection,
    "post-assembly projection can still delete, move, or manufacture native form nodes",
)
require("sourceSectionKey" not in v2_projection, "sparse product intent added an unversioned terminal section identity")
for forbidden_action_inference in ("actionRef.label", "candidate.methodName", "candidate.targetModel", "payment.request"):
    require(forbidden_action_inference not in action_executor, f"canonical action executor infers forbidden fact: {forbidden_action_inference}")
for legacy_structure_input in (
    "ContractFormNativeCanvas",
    "layoutNodes",
    "isNodeVisible",
    'v-bind="$attrs"',
):
    require(legacy_structure_input not in form_host, f"form driver retains legacy structure authority: {legacy_structure_input}")
for canonical_input in ("renderModel.actionBar", "action.actionRef", "data-canonical-action-bar"):
    require(
        canonical_input in form_host or canonical_input in canonical_action_bar,
        f"form driver does not consume canonical authority: {canonical_input}",
    )
require("data-canonical-form-zones" in object_task_page, "object-task floorplan does not expose canonical zone evidence")
for semantic_region in ("summary", "current-task", "business-context", "relation", "activity", "audit"):
    require(
        f'data-floorplan-region="{semantic_region}"' in object_task_page,
        f"object-task floorplan does not expose {semantic_region} semantic region",
    )
require(
    "<ProfessionalAuditTimeline" in object_task_page
    and 'data-floorplan-region="audit"' in object_task_page
    and audit_disclosure_is_governed(professional_audit_timeline),
    "audit region must be content-backed and default-collapsed",
)
require(
    not validate_semantic_identity_projection(presenter),
    "normalized form semantic roles do not survive the canonical mechanical mapping",
)
_JS_REGEX_PRECEDING_CHARS = frozenset("(,=:[!&|?{};+-*%^~<")
# `>` is the one operator the walk cannot place.  It ends a type-argument list as
# well as comparing, and the two readings hide different statements: read as a
# comparison, `/` opens a literal (and the quote inside its character class would
# otherwise open a *string* that runs to the next quote down the line); read as a
# type-argument close, the same `/` divides and the text after it is ordinary code
# whose quotes and braces have to stay visible.  The walk refuses rather than picks
# - the guard has no reading to offer, so it offers a refusal.
_JS_REGEX_AMBIGUOUS_PRECEDING_CHARS = frozenset(">")
# A `/` after one of these words opens a regular expression, not a division.
_JS_REGEX_PRECEDING_WORDS = frozenset(
    {
        "await",
        "case",
        "delete",
        "do",
        "else",
        "in",
        "instanceof",
        "new",
        "of",
        "return",
        "throw",
        "typeof",
        "void",
        "yield",
    }
)


# A `/` after the `)` of one of these words opens a regular expression, not a
# division: `if (ready) /[']/.test(text)` and `for (const item of list) /[']/.test(item)`
# are operands, while `Math.round(x) / factor` divides.  The parenthesis has to carry the
# keyword it belongs to, because the character walk cannot tell the two `)` apart.
_JS_REGEX_PRECEDING_BLOCK_KEYWORDS = frozenset({"if", "for", "while", "switch", "catch"})

# The TypeScript lexer continues an identifier with characters Python's `\w` does not:
# the combining marks (`Mn`/`Mc`), the two `Other_ID_Continue` punctuation marks and the
# two joiners.  Reading `extends\u0301:` as the *keyword* `extends` followed by something
# else glued the label's block into the type alias above it - `export type gA = (x:
# number) => void` followed by `extends\u0301: { (Array.prototype as any).includes = ()
# => false }` reported one alias, its head matched the shape rule, and the block ran while
# the module loaded in the browser.  A continuation word has a spelling the lexer may
# *extend*, so `extends\u0301` is a different name from `extends` and carries nothing.
_JS_IDENTIFIER_MARK_CHARACTERS = frozenset("\u00b7\u0387")
_JS_IDENTIFIER_JOINERS = frozenset("\u200c\u200d")
# The connector punctuation (`Pc`) the lexer continues an identifier with.  `isalnum`
# and the combining categories cover most of `ID_Continue`, but nine connectors are
# neither - `extends\u203f:` read as the keyword `extends` followed by something else
# glued the label's block into the alias above it, exactly as `extends\u0301` did.
_JS_IDENTIFIER_CONNECTORS = frozenset(
    "\u203f\u2040\u2054\ufe33\ufe34\ufe4d\ufe4e\ufe4f\uff3f"
)
# The `Other_ID_Continue` / `Other_ID_Start` marks that are neither alphanumeric nor
# combining: the katakana middle dots the continuation adds, and the four symbols the
# start set adds (a continued name may hold them even though an ASCII walk cannot open
# one).  Both lists are the whole of those two derived properties.
_JS_IDENTIFIER_CONTINUE_SYMBOLS = frozenset("\u30fb\uff65\u2118\u212e\u309b\u309c")
# The two of those six that the lexer may also *open* a name with (`Other_ID_Start`);
# the other four continue a name but cannot begin one.
_JS_IDENTIFIER_START_SYMBOLS = frozenset("\u2118\u212e")


def _js_identifier_continue(character: str) -> bool:
    """Whether the TypeScript lexer continues an identifier with this character."""
    return (
        character.isalnum()
        or character in "_$"
        or character in _JS_IDENTIFIER_MARK_CHARACTERS
        or character in _JS_IDENTIFIER_JOINERS
        or character in _JS_IDENTIFIER_CONNECTORS
        or character in _JS_IDENTIFIER_CONTINUE_SYMBOLS
        or unicodedata.category(character) in {"Mn", "Mc", "Pc"}
        # A code point this interpreter's tables do not know may still be one the
        # browser's lexer continues a name with; the safe reading of an unknown is the
        # longer name, which refuses the continuation.
        or (character > "\u007f" and unicodedata.category(character) == "Cn")
    )


def _js_identifier_start(character: str) -> bool:
    """Whether the walk reads an identifier from this character.

    ASCII only, deliberately: every word the continuation table tests is ASCII, and a
    statement that opens with a non-ASCII name is reported as *that* character - it is
    still reported, and the ladders still refuse to carry it.
    """
    return character.isascii() and (character.isalpha() or character in "_$")


def _js_identifier_start_non_ascii(character: str) -> bool:
    """Whether the TypeScript lexer may *open* a name with this character.

    The walk keeps `_js_identifier_start()` ASCII-only on purpose: a statement that
    opens with a non-ASCII name is still reported, as that character, and the ladders
    still refuse to carry it.  A declaration *head* cannot stay that narrow, because
    `export function \u540d` broken before `<T>` is a head that has named its subject -
    the parser continues the declaration across the break.  So the other half of the
    lexer's start rule is read here and only here: the letters and letter numbers a name
    may open with, the two `Other_ID_Start` symbols, and the code points this
    interpreter's tables do not know (read as the longer name - the fail-closed
    direction the continuation table above already takes).
    """
    return character > "\u007f" and (
        character.isalpha()
        or unicodedata.category(character) == "Nl"
        or character in _JS_IDENTIFIER_START_SYMBOLS
        or unicodedata.category(character) == "Cn"
    )


def _js_identifier_at(source: str, index: int) -> str | None:
    """The identifier the walk reads at `index`, or `None` where none begins."""
    if index >= len(source) or not _js_identifier_start(source[index]):
        return None
    end = index + 1
    while end < len(source) and _js_identifier_continue(source[end]):
        end += 1
    return source[index:end]


def _js_identifier_words(text: str) -> list[str]:
    """Every identifier in `text`, read the way the lexer reads one.

    The head tests below pick a statement's first words, and the word a *name* splits
    into is exactly what they must not get wrong: `export type gA` and `export typegA`
    are different statements.
    """
    words: list[str] = []
    index = 0
    while index < len(text):
        identifier = _js_identifier_at(text, index)
        if identifier is not None:
            words.append(identifier)
            index += len(identifier)
            continue
        index += 1
    return words


def _js_word_may_extend(character: str) -> bool:
    """Whether this character can only *continue* an identifier - never begin one.

    A character of this kind right where the walk ended a word is proof the walk read a
    shorter word than the lexer does, so the word is not the keyword under test.
    """
    return (
        character in _JS_IDENTIFIER_MARK_CHARACTERS
        or character in _JS_IDENTIFIER_JOINERS
        or character in _JS_IDENTIFIER_CONNECTORS
        or character in _JS_IDENTIFIER_CONTINUE_SYMBOLS
        or unicodedata.category(character) in {"Mn", "Mc", "Pc"}
        or (character > "\u007f" and unicodedata.category(character) == "Cn")
    )


def _js_preceding_word(source: str, index: int) -> str:
    """The identifier that ends at `index`, read back the way the lexer reads it."""
    start = index
    while start > 0 and _js_identifier_continue(source[start - 1]):
        start -= 1
    return source[start:index]


def _js_next_token(source: str, index: int) -> tuple[str, int]:
    """The next significant token at or after `index`, and the offset it ends at.

    Blanks are stepped over and an identifier is read as the lexer reads it, so the
    token the continuation table tests is the token the lexer would test - `extends`
    padded with spaces is `extends`, and `extends\u0301` is neither.
    """
    scan = index
    while scan < len(source) and source[scan].isspace():
        scan += 1
    if scan >= len(source):
        return "", scan
    identifier = _js_identifier_at(source, scan)
    if identifier is not None:
        return identifier, scan + len(identifier)
    return source[scan], scan + 1


def _js_opaque_spans(source: str) -> list[tuple[int, int, str, bool, bool]]:
    """Every comment, string, template literal and regular expression literal.

    `(start, end, kind, terminated)` per span, with `kind` one of `line`, `block`,
    `string`, `template` and `regex`.  Offsets are the ones in `source`, so callers
    can blank a span in place.

    A regular expression literal has to be recognised as one, because `//` and `/*`
    inside it are text: `return /[']/g` used to open a *string* at the quote in the
    character class and close it at the next quote anywhere below, and that span
    swallowed whole top-level statements - including the load-time gates the module
    checks exist to see.  Which `/` opens a regex is decided by the token before it;
    `terminated` reports a span that never closed, so a caller can refuse to read a
    file it cannot segment instead of silently reading a window that is not there.

    Two of those tokens are not single characters and are read as the token they spell.
    `=>` is one arrow, so the `/` after it is an operand position
    (`() => /[']/.test(item)`, the spelling that used to open a phantom string at the
    quote in the class and blank the `if` gate below it); and the `)` that closes the
    head of `if`/`for`/`while`/`switch`/`catch` ends a statement head, so a `/` after it
    is an operand position too - while the `)` that closes `Math.round(x)` is not, and
    the division after it must stay a division.  The parenthesis carries the keyword it
    belongs to, because nothing else tells the two apart.

    `crossed` is the fifth field: a `'`/`"` literal that only closed *below* the line it
    opened on.  No string literal may hold a raw line break, so such a span is not a
    literal at all - it is the text between a quote the regular-expression guess missed
    and the next quote anywhere down the file - and a caller can refuse the file instead
    of reading a statement list with that text taken out of it.
    """
    spans: list[tuple[int, int, str, bool, bool]] = []
    index = 0
    length = len(source)
    previous = ""
    word = ""
    # Whether the `(` just read opened a *statement head*, and whether the character
    # just consumed is one a regular expression may follow.
    paren_heads: list[bool] = []
    regex_preceding = False
    while index < length:
        char = source[index]
        nxt = source[index + 1] if index + 1 < length else ""
        # The blanks here are the lexer's, not this interpreter's: `str.isspace()` is
        # false for the byte-order mark `U+FEFF`, which the TypeScript lexer reads as
        # whitespace, so a `>` padded with one stopped being the token before a `/` and
        # the ambiguous span below was never produced - a one-character bypass of the
        # refusal this same walk relies on.  `_js_is_blank()` is that same reading, and
        # the statement walk already takes it.
        if _js_is_blank(char):
            index += 1
            continue
        if char == "/" and nxt == "/":
            end = source.find("\n", index)
            end = length if end == -1 else end
            spans.append((index, end, "line", True, False))
            index = end
            continue
        if char == "/" and nxt == "*":
            found = source.find("*/", index + 2)
            end = length if found == -1 else found + 2
            spans.append((index, end, "block", found != -1, False))
            index = end
            continue
        if char in ("'", '"', "`"):
            end = index + 1
            closed = False
            crossed_line = False
            while end < length:
                if source[end] == "\\":
                    # A `\\` at the end of a line continues the literal *on* the next
                    # one and is not a line break inside it, so the escape is stepped
                    # over before the break test can see it.
                    end += 2
                    continue
                if source[end] == char:
                    end += 1
                    closed = True
                    break
                if source[end] in "\n\u2028\u2029":
                    crossed_line = True
                end += 1
            end = min(end, length)
            spans.append(
                (
                    index,
                    end,
                    "template" if char == "`" else "string",
                    closed,
                    crossed_line and char != "`",
                )
            )
            index = end
            previous = char
            word = ""
            regex_preceding = False
            continue
        if (
            char == "/"
            and previous in _JS_REGEX_AMBIGUOUS_PRECEDING_CHARS
            and not regex_preceding
        ):
            spans.append((index, index + 1, "ambiguous", False, False))
            index += 1
            previous = char
            word = ""
            regex_preceding = False
            continue
        if char == "/" and (
            previous in _JS_REGEX_PRECEDING_CHARS
            or word in _JS_REGEX_PRECEDING_WORDS
            or regex_preceding
        ):
            end = index + 1
            in_class = False
            closed = False
            while end < length:
                current = source[end]
                if current == "\\":
                    end += 2
                    continue
                if current == "\n":
                    break
                if current == "[":
                    in_class = True
                elif current == "]":
                    in_class = False
                elif current == "/" and not in_class:
                    end += 1
                    closed = True
                    break
                end += 1
            # A literal that does not close on its own line is not a literal: `v-else />`
            # in a template has `else` before a slash that opens nothing.  Rolling the
            # guess back keeps every span a real one - and a real unterminated regular
            # expression is a file that does not compile, so nothing runs it.
            if closed:
                spans.append((index, min(end, length), "regex", True, False))
                index = min(end, length)
                previous = "/"
                word = ""
                regex_preceding = False
                continue
        if _js_identifier_start(char):
            start = index
            while index < length and _js_identifier_continue(source[index]):
                index += 1
            word = source[start:index]
            previous = source[index - 1]
            regex_preceding = False
            continue
        if char == "(":
            paren_heads.append(word in _JS_REGEX_PRECEDING_BLOCK_KEYWORDS)
            regex_preceding = False
        elif char == ")":
            regex_preceding = bool(paren_heads.pop()) if paren_heads else False
        else:
            # `=>` is a single arrow.  Read as the operator `>` alone, the `/` after it
            # was a division, the quote in the regular expression that followed opened a
            # *string*, and the span it closed ran down to the next quote in the file -
            # which is where the `if` gate that the literal guards was standing.
            regex_preceding = char == ">" and previous == "="
        previous = char
        word = ""
        index += 1
    return spans


def _js_unsegmentable_spans(source: str) -> list[tuple[int, int, str, bool, bool]]:
    """The opaque spans that make a statement list unsafe to read.

    Two kinds of span qualify.  One never closed - a real unterminated literal or
    comment is a file that does not compile, so nothing runs it, and the caller refuses
    rather than reads a window that is not there.  The other is a `'`/`"` literal that
    only closed *below* the line it opened on: no string literal may hold a raw line
    break, so that span is not a literal at all, it is the text between a quote the
    regular-expression guess missed and the next quote anywhere down the file, and the
    statements inside it were read as absent while the module ran them at load time -
    `const matches = (text: string): boolean => /[']/.test(text);` opened exactly such a
    span at the quote in the character class, and it closed on the quote in the
    `typeof Element !== 'undefined'` gate below, so the gate was erased from the text
    the walk reads and the poisoned `Array.prototype.includes` it guards loaded in the
    browser while the guard stayed green.  Both are refusals rather than readings.
    """
    return [span for span in _js_opaque_spans(source) if not span[3] or span[4]]


def _blank_spans(source: str, kinds: tuple[str, ...]) -> str:
    """Blank the spans of `kinds`, keeping every offset.

    A template literal keeps its opening delimiter.  Blanking one whole - which is
    what erasing the text between the backticks meant, interpolations included - made
    a template literal in *statement* position look like no statement at all, so
    `` `${probe()}`; `` at the module's own level ran at load time while the
    statement walk reported nothing and the environment probe inside `${...}` was
    erased along with the text around it.  The backtick is not text: it is the token
    the statement begins with, and keeping it lets the ordinary "a statement at this
    level must be a declaration" rule see the statement and refuse it.

    A literal also keeps its *last* position.  The blanked text is what the statement
    walk reads, and blanking a literal right through its closing quote took the
    literal's ending away with it: `export type A = 'x'` left the `=` in charge of the
    newline, `_can_end_statement()` read `=` and said no statement could end there,
    and the line below was absorbed into the alias - the shape rule matched its head,
    and `(Array.prototype as any).includes = () => true` ran while the module loaded
    in every domain the gate's own node process never sees.  One character of the span
    stands in for the literal's end, and it stands in as a *digit*: `0` cannot spell a
    keyword or join an identifier, and `_can_end_statement()` reads it the way it
    reads any name, so the statement ends where the literal ended.
    """
    out = list(source)
    for start, end, kind, _terminated, _crossed in _js_opaque_spans(source):
        if kind in kinds:
            for position in range(start, end):
                if kind == "template" and position == start:
                    continue
                out[position] = " "
            if kind in ("string", "template") and end > start:
                out[end - 1] = "0"
    return "".join(out)


def _blank_comments(source: str) -> str:
    """Blank out line and block comments, preserving every offset.

    String, template and regular expression literals are stepped over rather than
    read through.  `const a = "x//y"` used to open a *line comment* at the `//`
    inside the string, `export type T = 'x/*y'` used to open a block comment that
    never closed, and `return /[']/g` used to open a *string* at the quote in the
    character class - each of them swallowed whole top-level statements, including
    the load-time gates the module checks exist to see.  All three are opaque spans
    now.
    """
    return _blank_spans(source, ("line", "block"))


def _blank_string_literals(source: str) -> str:
    """Blank out string and template literals, preserving every offset.

    Comments and regular expression literals are stepped over: a quote inside either
    is not a string delimiter, so `// don't` and `/[']/` no longer open a span that
    ends somewhere else and takes the statements in between out of view.
    """
    return _blank_spans(source, ("string", "template"))


def _normalize_bracket_property_access(source: str) -> str:
    """Rewrite `x['member']` as `x.member` so bracket spellings compare as dot spellings.

    Only identifier-shaped literals are rewritten, so a decoy such as
    `"hasCollaborationNode.value"` keeps its shape and is still blanked afterwards.
    """
    source = re.sub(r"\[\s*'([A-Za-z_$][\w$]*)'\s*\]", r".\1", source)
    return re.sub(r'\[\s*"([A-Za-z_$][\w$]*)"\s*\]', r".\1", source)


def _blank_comments_and_strings(source: str) -> str:
    """Blank both, so a decoy token inside either cannot satisfy an expression guard.

    Offset preservation is part of the contract, not an implementation detail: the
    four authority bodies are *located* on this text and then *read back out of the
    original* source, so a blanking that changes the length hands back a window from
    somewhere else entirely.  `_normalize_bracket_property_access` is length
    changing and is deliberately not applied here any more; the one caller that
    wants the two spellings to compare equal (`_sole_return_expression`) applies it
    itself.  One bracket property access ahead of the authority used to shift every
    later window, so a body whose real text was a leaf gated on the runtime
    environment was never read while both layers stayed green.
    """
    return _blank_string_literals(_blank_comments(source))


def _paren_matched(source: str, start: int) -> str | None:
    """Return the text between `source[start]` and its matching parenthesis."""
    depth = 1
    index = start + 1
    while index < len(source):
        char = source[index]
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return source[start + 1:index]
        index += 1
    return None


def _computed_argument(source: str, name: str) -> str | None:
    """Return the argument text of `const <name> = computed(...)`, paren balanced."""
    match = re.search(rf"const\s+{re.escape(name)}\s*=\s*computed\s*\(", source)
    if match is None:
        return None
    return _paren_matched(source, match.end() - 1)


def _function_body_span(source: str, name: str) -> tuple[int, int] | None:
    """`(start, end)` of the body of `function <name>(...) { ... }`, brace balanced."""
    match = re.search(rf"function\s+{re.escape(name)}\s*\(", source)
    if match is None:
        return None
    arguments = _paren_matched(source, match.end() - 1)
    if arguments is None:
        return None
    opening = source.find("{", match.end() - 1 + len(arguments) + 1)
    if opening == -1:
        return None
    depth = 1
    index = opening + 1
    while index < len(source):
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return opening + 1, index
        index += 1
    return None


def _body_window(source: str, name: str) -> tuple[str | None, str | None]:
    """`(body, failure)` for `function <name>(...) { ... }`, read out of the original.

    The body is located on the blanked source - so a decoy copy of the function
    parked in a string literal or a comment cannot be found first - and the located
    window is then *proved* aligned before it is read back out of the original text.
    The proof is the point: reading the window without proving it is what let a
    single bracket property access anywhere earlier in the file shift every later
    window, so a body whose real text was a leaf gated on the runtime environment
    was never read while the guard and the executable proof both stayed green.  A
    window whose blanking does not reproduce it character for character is reported
    instead of being read, because a locator that cannot prove its window has no
    body to hand to the expression checks.
    """
    blanked = _blank_comments_and_strings(source)
    span = _function_body_span(blanked, name)
    if span is None:
        return None, "is gone"
    window = blanked[span[0]:span[1]]
    if _blank_comments_and_strings(source[span[0]:span[1]]) != window:
        return None, "has a misaligned read window"
    return source[span[0]:span[1]], None


def _parens_balanced(text: str) -> bool:
    depth = 0
    for char in text:
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def _strip_outer_parens(text: str) -> str:
    while text.startswith("(") and text.endswith(")") and _parens_balanced(text[1:-1]):
        text = text[1:-1]
    return text


def _condense(source: str) -> str:
    return re.sub(r"\s+", "", source)


def _sole_return_expression(body: str) -> tuple[str | None, str | None]:
    """`(expression, failure)` for a body whose only statement is a `return`.

    The authorities are single expressions, so the structure is checked here and the
    *value* is checked by the callers against the canonical expression.  Structure
    alone is not the assertion: `if (typeof window !== 'undefined') return false;
    return <rule>;` keeps every token, returns a boolean and is dead in the browser
    while the node-run proof never sees the branch; `return false` followed by an
    ASI-separated second statement has the same effect one statement later.  The
    returned expression is normalized (comments blanked, `x['m']` written as
    `x.m`) so a spelling variant cannot compare equal to the canonical text.
    """
    normalized = _blank_comments(_normalize_bracket_property_access(body))
    keyword = re.match(r"return\b", normalized.strip())
    if keyword is None:
        return None, "must be exactly one `return` statement"
    expression = _condense(normalized.strip()[keyword.end():])
    remainder = expression[:-1] if expression.endswith(";") else expression
    if not remainder or ";" in remainder:
        return None, "must be exactly one `return` statement"
    return remainder, None


def _authority_expression_failures(
    source: str, name: str, canonical: str, subject: str
) -> list[str]:
    """The named authority must be exactly one `return` of the canonical expression.

    Location and value are checked separately so that a body the locator could not
    prove it read is reported as a locator failure rather than as a value mismatch:
    "the rule is not the canonical expression" and "the rule was never read" are
    different facts about the gate, and conflating them hides the second one.
    """
    body, locator_failure = _body_window(source, name)
    if locator_failure is not None:
        return [f"{subject} {locator_failure}"]
    return _expression_failures(body, canonical, subject)


_COLLABORATION_AUTHORITY = "resolveCollaborationVisibility"
_COLLABORATION_CAPABILITY_PROP = "props.showCollaborationPanel"
# The panel's own gate.  The region slot renders the native panel only under the host's
# panel visibility, so the slot can be wired and still render nothing: the panel gate is
# compared against this authority like the flag delegation is, instead of only being
# tested for literal falsiness.
#
# The page-region contract made the gate a derived authority: a contract that
# declares its regions decides from the declaration, and only the legacy contract
# (no declaration at all) still needs the runtime capability conjunct, so the
# panel gate moved from the raw prop to `collaborationPanelVisible`.  The two
# reviewed expressions behind it are `hasCollaboration` above and the
# declaration-aware predicate the guard pins in the runtime VM, so this is a
# recorded review of the same single authority rather than a second one.
_COLLABORATION_PANEL_GATE = "collaborationPanelVisible"
_COLLABORATION_SUPPRESSION_PROP = "props.suppressCollaboration"
_COLLABORATION_SUBORDINATE_ZONE = "props.renderModel?.zones.subordinate"
_COLLABORATION_KINDS_CONSTANT = "COLLABORATION_SURFACE_KINDS"
_COLLABORATION_KIND_PREDICATE = "isCollaborationSurfaceKind"
_COLLABORATION_NODE_AUTHORITY = "hasCollaborationNode"
_COLLABORATION_DECLARED_KINDS = ("chatter", "activity")
_COLLABORATION_REGION_SLOT = "#collaboration"
_COLLABORATION_AUTHORITY_TEST = (
    "frontend/apps/web/scripts/contract_form_collaboration_authority_test.ts"
)
_COLLABORATION_AUTHORITY_TEST_TARGET = (
    "verify.frontend.contract_form_collaboration_authority.unit"
)
_COLLABORATION_AUTHORITY_TEST_MODULE_IMPORT = (
    "from '../src/pages/contractForm/contractRuntimeVm'"
)
_COLLABORATION_AUTHORITY_TEST_SHA256 = (
    "802487b7eb6843d64e8417476014f996568eca039e35a43d4bce29dd64a149af"
)
_COLLABORATION_HOST = "frontend/apps/web/src/pages/contractForm/ContractFormDriverHost.vue"
_COLLABORATION_VM_MODULE = "frontend/apps/web/src/pages/contractForm/contractRuntimeVm"
_COLLABORATION_VM_IMPORT_SPECIFIER = "./contractRuntimeVm"
# The three authorities are single expressions, and the guard binds them by exact
# (whitespace- and bracket-normalized) equality rather than by token presence.  A
# blacklist of environment-probe spellings was defeated by `globalThis['window']`,
# `typeof(window)`, `typeof(self)` and `('window' in globalThis)`: each kept every
# token, turned the region off in the browser, and stayed invisible to the
# node-run proof.  Equality rejects the whole family structurally; the canonical
# texts below are the reviewed expressions, and changing them is a review event.
_COLLABORATION_CANONICAL_KIND_PREDICATE = (
    "(COLLABORATION_SURFACE_KINDSasreadonlystring[]).includes("
    "String(kind||'').trim().toLowerCase(),)"
)
_COLLABORATION_CANONICAL_NODE_AUTHORITY = (
    "Boolean(nodes?.some((node)=>isCollaborationSurfaceKind(node.kind)))"
)
_COLLABORATION_CANONICAL_VISIBILITY_RULE = (
    "Boolean(input.capability)||(!input.suppressed&&hasCollaborationNode(input.nodes))"
)
# The page-side props: the attribute names, and the single page authority each one
# must bind.  They are read as an attribute table (both quote styles, entities
# decoded) rather than by a double-quoted regular expression, because a
# single-quoted `:show-collaboration-panel='false'` next to a double-quoted decoy
# used to leave the guard green while Vue took the literal.
_COLLABORATION_PANEL_ATTRIBUTE = "show-collaboration-panel"
_COLLABORATION_PANEL_AUTHORITY = "showNativeCollaborationPanel"
_COLLABORATION_SUPPRESSION_ATTRIBUTE = "suppress-collaboration"
_COLLABORATION_SUPPRESSION_AUTHORITY = "dispatchContextCollaboration"
# The reviewed gates on the path each subject sits on.  Every element between the
# template root and the panel carries some condition, and the guard has to be able to
# tell a condition the product reviewed from one that was added afterwards, so the
# inventory is written out rather than inferred: changing any of these is a review
# event and the guard refuses until the new text is recorded here.
# An entry is the expression the attribute carries with its whitespace removed,
# because that is the form `_dead_gate_failures` compares against - so the recorded
# text is condensed here rather than spelled out in a second dialect.
#
# host side - `ContractFormDriverHost.vue` wraps the carrier in
# `ScErrorState v-if="error || !renderModel"` / `section v-else`, gates the carrier on
# `!preserveAuthoritativeBusinessSections` and the task pattern on the presentation
# mode; the region template is gated on the flag and the panel on its own derived
# authority.  `showCollaborationPanel` is no longer a template gate - the contract
# made the panel gate the derived `collaborationPanelVisible`, so it is replaced here
# rather than kept as a second accepted spelling (the panel has its own exact-gate
# check just below).
_COLLABORATION_HOST_TEMPLATE_GATES = frozenset(
    {
        "!preserveAuthoritativeBusinessSections",
        _condense("renderModel.identity.presentationMode === 'task'"),
        "hasCollaboration",
        "collaborationPanelVisible",
    }
)
_COLLABORATION_HOST_ELSE_ELEMENTS = frozenset({"section"})
# page side - `ContractFormPage.vue` gates the driver host on the form-field-config
# scope and reaches it through a page section that is itself reviewed.
_COLLABORATION_PAGE_TEMPLATE_GATES = frozenset(
    {
        "!showCurrentFormFieldConfigScope",
        _condense(
            "pageSectionEnabled('details_fallback', true)"
            " && pageSectionTagIs('details_fallback', 'section')"
        ),
    }
)
_COLLABORATION_PAGE_ELSE_ELEMENTS = frozenset({"ScCard"})
# The authority module is its own file, and the three bodies are not the whole of
# it: a statement *outside* them is invisible both to the body checks above and to
# the executable proof, because the proof's browser-domain replay installs `window`
# only after the module has already been imported.  A gate evaluated during module
# load therefore ran in neither domain and left both layers green while the rule was
# dead in the browser.  The module may not name a runtime-environment global at all
# - the list is deliberately wider than the spelling that was used, and the real
# `contractRuntimeVm.ts` contains no hit for any of them - and a top-level statement
# must be a declaration: an `if`/`for`/`while`/`throw`/... at the module's own level
# is the shape a load-time gate needs.
_COLLABORATION_ENVIRONMENT_GLOBALS = (
    "window",
    "document",
    "globalThis",
    "self",
    "navigator",
    "location",
    "localStorage",
    "sessionStorage",
    "indexedDB",
    "XMLHttpRequest",
    "requestAnimationFrame",
    "getComputedStyle",
    "matchMedia",
    "Worker",
    "MutationObserver",
    "ResizeObserver",
    "performance",
    "history",
    "alert",
    "confirm",
    "prompt",
    "process",
    "global",
    "require",
    "Function",
    "eval",
    # The browser/node discriminators a load-time gate reaches for.  They are the
    # spellings the guard's own fixtures already treat as "the environment probe"
    # (`typeof screen !== 'undefined'`), and every one of them is a name that cannot
    # collide with ordinary product identifiers.  Names such as `top`, `parent`,
    # `name`, `status`, `origin` and `fetch` are deliberately *not* here: the first
    # four are common identifiers, `fetch` is already reached for by an honest
    # closure module (`fieldUtils.ts`), and a word-boundary scan for them would
    # refuse real code.  The *shape* rule the closure walk applies is what closes the
    # family at load time - a reviewed import target carries no module-level binding,
    # no class body and no export assignment - while the enumeration covers the names
    # a gate can still reach for once the module is running, inside a function body,
    # which no shape rule can see.  It therefore only has to cover the spellings no
    # product code would otherwise mention.
    "screen",
    "frames",
    "devicePixelRatio",
    "isSecureContext",
    "crossOriginIsolated",
    "visualViewport",
    "speechSynthesis",
    "crypto",
    "queueMicrotask",
    "structuredClone",
    "atob",
    "btoa",
    "HTMLElement",
    "CustomEvent",
    "IntersectionObserver",
    "PerformanceObserver",
    "Notification",
    "WebSocket",
    "EventSource",
    "Deno",
    "Bun",
    "Buffer",
)
_COLLABORATION_MODULE_DECLARATIONS = frozenset(
    {
        "import",
        "export",
        "type",
        "interface",
        "const",
        "let",
        "var",
        "function",
    }
)
# Only the shapes the real `contractRuntimeVm.ts` actually uses stay on this list.
# `declare`, `abstract` and `async` leave it for the same reason the resource
# declarations left the exported list below: a whitelist entry is a promise that the
# shape cannot run load-time code, and `abstract class X { static y = <expression> }`
# is a statement whose first token is `abstract` while its static field initializer
# runs while the module loads.  A shape the module does not use is not worth that
# promise.
# `}` does not end a statement when it closes an import's named-binding list, an
# object type in an `extends` clause, or the body of a `do`/`try`: what follows the
# brace decides.  Which words may decide that now depends on the statement's own head
# - see `_JS_CONTINUATION_HEADS` beside `_statement_continues()` below, where the same
# check serves the line-break path.  Read as continuations *everywhere*, the words
# glued the following statement on to the one above: `type gN3 = { a: number }`
# followed by a line `from: { (Array.prototype as any).includes = () => true }`
# reported a single type alias, the shape rule matched its head, and the label's block
# ran while the module loaded - skipped in node, live in the browser, guard green.
# What an `export` at the module's own level may introduce.  `export { x } from
# './y'` and `export * from './y'` are re-exports: they evaluate another module while
# loading, which is a load-time hook the guard cannot see into.
_COLLABORATION_EXPORT_DECLARATION = (
    r"export\s+(?:const|let|var|function|type|interface|async)\b"
)
# `export class|enum|namespace|abstract class|declare ...` are the same load-time hook
# as their bare spellings: the declaration's own body or initializer is evaluated
# while the module loads, and the statement walk never enters a declaration body.  So
# removing `enum`/`namespace`/`using` from the bare whitelist was only half the rule -
# the exported spelling was still matched by the pattern above and passed.
_COLLABORATION_EXPORT_LOAD_TIME_DECLARATION = (
    r"export\s+(?:enum|class|namespace|abstract|declare|using|module)\b"
)
# A module-level binding is the same load-time hook spelled as a declaration: its
# initializer is evaluated while the module loads, and the environment name it reaches
# for is not one the enumeration happens to list - `Element`, `module`, `setImmediate`,
# `__dirname`, `exports`, `Image`, `FileReader` and `onmessage` all passed it.  The
# real closure carries no module-level binding at all (four modules of functions and
# types), so the shape is refused rather than judged.
_COLLABORATION_EXPORT_BINDING = r"export\s+(?:const|let|var)\b"
_COLLABORATION_MODULE_BINDING_TOKENS = frozenset({"const", "let", "var"})
# `type` and `interface` are *contextual* keywords, not reserved words: the same
# spelling that opens a type alias is also a legal identifier, so
# `type(typeof customElements !== 'undefined' && (Array.prototype.includes = () => false));`
# is an ordinary call that the first-token walk read as a declaration and passed -
# and the call is load-time code that never executes in the gate's node domain, so
# the rule stayed green while it died in the browser.  A declaration is the shape that
# names something; anything else spelled `type` or `interface` is a statement that
# runs.  `function` cannot be an identifier, so its entry is belt-and-braces rather
# than a bypass being closed.
_COLLABORATION_DECLARATION_SHAPES = {
    # The parameter list is read to its *last* `>` rather than its first: `[^>]*`
    # stopped at the inner bracket of `type Wrapped<T extends Box<number>> = T`, so a
    # declaration whose generic nests was refused as if it were a call.  The delimiter
    # is the statement's own `;`, which the text never crosses.
    "type": re.compile(r"^type\s+[A-Za-z_$][\w$]*(?:\s*<[^;]*>)?\s*="),
    "interface": re.compile(r"^interface\s+[A-Za-z_$][\w$]*"),
    "function": re.compile(
        r"^(?:async\s+)?function\s*\*?\s*[A-Za-z_$][\w$]*(?:\s*<[^;]*>)?\s*\("
    ),
}
# The same asymmetry applied to re-exports: `import { x } from 'pkg'` was refused
# because the guard cannot open a package, but `export * from 'pkg'`,
# `export * as ns from 'pkg'` and `export { a } from 'pkg'` evaluate that same package
# at load time while `relative_edges()` only ever follows a `.`-prefixed specifier.
# A re-export the guard cannot open is refused rather than skipped, exactly as the
# import beside it is.
# `export default` is refused whatever stands behind it.  The allow-list that waved
# `export default class` through is where the load-time initializer got back in:
# `export default class RouteProbe { static x = (((Array.prototype as any).includes =
# () => true), 1); }` poisoned `[].includes` while the module loaded, so the authority
# answered `true` in every domain and the guard stayed green.  A closure member
# carries no default export to judge.
_COLLABORATION_EXPORT_DEFAULT = r"export\s+default\b"
_COLLABORATION_EXPORT_DEFAULT_DECLARATION = (
    r"export\s+default\s+(?:abstract\s+)?(?:class|enum|namespace)\b"
)
# TypeScript's `export = <expression>` exports a value computed while the module
# loads, and its `export` head kept it on the declaration side of the whitelist.
_COLLABORATION_EXPORT_ASSIGNMENT = r"export\s*="
# Every runtime import evaluates another file's top-level code inside the gate's own
# import, so a reviewed list is the only honest rule: `import { x } from './y'` binds
# a name and runs `./y` exactly like the `import './y'` the check below rejects.
# Type-only imports are erased and need no entry.  These are the runtime imports of
# the real `contractRuntimeVm.ts`.
_COLLABORATION_MODULE_IMPORT_SPECIFIERS = (
    "../../app/contracts/v2/store",
    "./valueUtils",
)
# A `const` at the module's own level is still evaluated while the module loads, so
# its initializer is load-time code even though its statement *is* a declaration.
# The statement whitelist above lets
# `export const degraded = typeof screen !== 'undefined' && (COLLABORATION_SURFACE_KINDS as unknown as string[]).splice(0);`
# through: `screen` is one of the browser-only globals the token list deliberately
# does not enumerate, the declaration shape satisfies the whitelist, and the
# truth-table proof replays its browser domain *after* the import, so the mutation
# ran in neither domain while the region was dead in the browser.  Enumerating one
# more global would only move the hole to the next spelling, so the rule is a
# *shape*: the module's only binding is the kind list, and its initializer may hold
# nothing but string literals, which cannot read anything at all.
# `enum`, `namespace` and `using` leave the declaration whitelist for the same
# reason - each can carry an initializer the module would evaluate while it loads -
# and none of them appears in the real `contractRuntimeVm.ts`.
_COLLABORATION_STRING_LITERAL = r"'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\""
_COLLABORATION_MODULE_BINDING = re.compile(r"^export (?:const|let|var) ")
_COLLABORATION_MODULE_KINDS_DECLARATION = re.compile(
    r"^export const "
    + _COLLABORATION_KINDS_CONSTANT
    + r" = \[\s*(?:"
    + _COLLABORATION_STRING_LITERAL
    + r")(?:\s*,\s*(?:"
    + _COLLABORATION_STRING_LITERAL
    + r"))*\s*,?\s*\] as const$"
)


def _blank_html_comments(source: str) -> str:
    """Blank out `<!-- ... -->`, preserving every offset.

    `_blank_comments` only knows the script-level `//` and `/* */` forms, so a
    template decoy would otherwise satisfy a wiring assertion.
    """
    out = list(source)
    for match in re.finditer(r"<!--[\s\S]*?-->", source):
        for position in range(match.start(), match.end()):
            if out[position] != "\n":
                out[position] = " "
    return "".join(out)


def _blank_style_blocks(source: str) -> str:
    """Blank out `<style ...> ... </style>`, preserving every offset.

    Style text is not template markup, so a token parked there must not count as
    wiring.
    """
    out = list(source)
    for match in re.finditer(r"<style\b[^>]*>[\s\S]*?</style\s*>", source):
        for position in range(match.start(), match.end()):
            if out[position] != "\n":
                out[position] = " "
    return "".join(out)


def _template_text(host: str) -> str:
    return _blank_style_blocks(_blank_html_comments(host))


def _script_text(host: str) -> str:
    """A `.vue` source with every byte outside a `<script>` block blanked.

    The JavaScript lexer is asked for script text, and template text is not script
    text.  An apostrophe in ordinary copy - `<span>don't</span>` - opened a string
    literal that ran on to the next quote anywhere in the file, so the boundary around
    the `<script setup>` body moved and the `hasCollaboration` computed below the copy
    was read as missing: a false reject on a shape nobody had to attack, because
    writing English is not an attack.  Offsets are preserved the same way the other
    blankings preserve them, and a source with no `<script` block is handed back
    untouched so a plain module is never silently emptied.

    The block is located on the shared tag scan rather than by a raw
    `<script\b[^>]*>` search, because that search read two ordinary shapes as the
    start of a script block: a bare `<script` inside a quoted attribute value
    (`data-note="<script"`) and a `<script` inside an HTML comment.  Either one moved
    the boundary and emptied the script region, and the file was rejected for a
    binding it had.  The scan skips comments and reads start tags to the first `>`
    outside quotes, so neither is a script block.  The closing delimiter stays
    case-insensitive: the SFC parser closes a block at `</SCRIPT>` as readily as at
    `</script>`, and a case-sensitive scan read the body as template text.
    """
    if "<script" not in host:
        return host
    out = ["\n" if character == "\n" else " " for character in host]
    found = False
    for kind, name, _tag_start, tag_end, _self_closing in _scan_tags(host):
        if kind != "open" or name.lower() != "script":
            continue
        closing = re.search(r"</script\s*>", host[tag_end:], re.I)
        body_end = tag_end + (closing.start() if closing is not None else len(host) - tag_end)
        for position in range(tag_end, body_end):
            out[position] = host[position]
        found = True
    if not found:
        return host
    return "".join(out)


def _start_tag_spans(source: str, name: str) -> list[tuple[int, str]]:
    """Every `<name ...>` start tag as `(offset, text)`, read to the first `>`."""
    spans = []
    for match in re.finditer(r"<" + name + r"\b", source):
        index = match.end()
        quote = ""
        while index < len(source):
            character = source[index]
            if quote:
                if character == quote:
                    quote = ""
            elif character in ("'", '"'):
                quote = character
            elif character == ">":
                spans.append((match.start(), source[match.start():index + 1]))
                break
            index += 1
    return spans


def _start_tags(source: str, name: str) -> list[str]:
    """Every `<name ...>` start tag, read to the first `>` outside quotes."""
    return [tag for _, tag in _start_tag_spans(source, name)]


def _element_spans_all(source: str) -> list[tuple[str, int, int, int]]:
    """`(name, offset, start_tag_end, element_end)` for every element, one scan.

    Nesting is counted on the token stream from `_scan_tags`, so a tag name that
    only appears inside a quoted attribute value or a comment cannot perturb it.
    """
    stack: list[tuple[str, int, int]] = []
    spans: list[tuple[str, int, int, int]] = []
    for kind, name, start, end, self_closing in _scan_tags(source):
        if kind == "open":
            if self_closing:
                spans.append((name, start, end, end))
            else:
                stack.append((name, start, end))
            continue
        for depth in range(len(stack) - 1, -1, -1):
            if stack[depth][0] == name:
                # Everything above the match was never closed, so it ends here too.
                # Dropping those entries silently let `<ObjectTaskPage><div>...</
                # ObjectTaskPage>` keep the slot 'inside' the flagged element with
                # the unclosed child invisible to the innermost-element lookup.
                for open_name, begin, tag_end in stack[depth:]:
                    spans.append((open_name, begin, tag_end, end))
                del stack[depth:]
                break
    for name, begin, tag_end in stack:
        spans.append((name, begin, tag_end, len(source)))
    return spans


def _element_spans(source: str, name: str) -> list[tuple[str, int, int]]:
    """`(start_tag, offset, end)` for every `<name>` element, depth counted.

    A region slot can keep every token and still be dead when it is moved out of
    the element whose slot it fills, so the slot has to be bound to the element
    that carries the flag rather than merely co-existing in the same file.
    """
    return [
        (source[start:tag_end], start, span_end)
        for element_name, start, tag_end, span_end in _element_spans_all(source)
        if element_name == name
    ]


def _innermost_element(source: str, offset: int) -> tuple[str, int, int] | None:
    """The innermost element strictly containing `offset`, as `(name, start, end)`.

    Strictly: the element that begins *at* `offset` is the slot itself, not its
    parent, and counting it would make every slot its own container.
    """
    candidates = [
        (name, start, end)
        for name, start, _tag_end, end in _element_spans_all(source)
        if start < offset < end
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda candidate: candidate[1])


_COLLABORATION_EXPECTED_FLAG = (
    "() => {\n"
    "  if (contractDeclaresSurfaces.value) {\n"
    "    return props.suppressCollaboration ? false : Boolean(collaborationSurface.value);\n"
    "  }\n"
    "  return resolveCollaborationVisibility({\n"
    "    capability: props.showCollaborationPanel,\n"
    "    suppressed: props.suppressCollaboration,\n"
    "    nodes: props.renderModel?.zones.subordinate,\n"
    "  });\n"
    "}"
)
# The reviewed flag, reflowed onto one line and with the capability spelled as a
# bracket property access.  Both are the same expression to the compiler and to the
# guard's normalizers, so they are accepted samples rather than rewrites.
_COLLABORATION_EXPECTED_FLAG_REFLOWED = re.sub(r"\s+", " ", _COLLABORATION_EXPECTED_FLAG)
_COLLABORATION_EXPECTED_FLAG_BRACKET = _COLLABORATION_EXPECTED_FLAG.replace(
    "props.showCollaborationPanel", "props['showCollaborationPanel']"
)


def _strip_wrapping_parens(text: str) -> str:
    """Drop parentheses that wrap the whole expression, keeping inner ones."""
    while len(text) > 1 and text.startswith("(") and text.endswith(")"):
        depth = 0
        wraps = True
        for index, character in enumerate(text):
            if character == "(":
                depth += 1
            elif character == ")":
                depth -= 1
                if depth == 0 and index != len(text) - 1:
                    wraps = False
                    break
        if not wraps:
            break
        text = text[1:-1]
    return text


def _normalize_flag_argument(argument: str) -> str:
    """Reduce `computed`'s argument to a canonical form for equality comparison.

    Only deterministic desugarings are undone - redundant parentheses, an optional
    return-type annotation and a block body whose sole statement is the `return`.
    The `return` is *required*: `() => { <delegation>; }` is an arrow whose value is
    `undefined`, so treating it as equal to `() => { return <delegation>; }` would
    accept a flag that is permanently falsy.  Anything else (a negation, a comma
    expression, a ternary, a trailing `||`/`&&`, an extra statement) survives, so
    the comparison below is an equality of the whole expression rather than a
    token count.
    """
    text = _strip_wrapping_parens(re.sub(r"\s+", "", argument))
    text = re.sub(r"^\(\):[^=]*?=>", "()=>", text)
    if text.startswith("()=>"):
        remainder = _strip_wrapping_parens(text[len("()=>"):])
        block = re.fullmatch(r"\{return(.*?);?\}", remainder)
        if block is not None and ";" not in block.group(1):
            remainder = block.group(1)
        text = "()=>" + remainder
    return text.replace(",}", "}")


def _string_literal_at(source: str, index: int) -> str | None:
    """The unquoted value of the string literal starting at or after `index`."""
    while index < len(source) and source[index] in " \t\r\n":
        index += 1
    if index >= len(source) or source[index] not in ("'", '"'):
        return None
    quote = source[index]
    end = index + 1
    while end < len(source):
        if source[end] == "\\":
            end += 2
            continue
        if source[end] == quote:
            return source[index + 1:end]
        end += 1
    return None


def _authority_named_imports(source: str, name: str) -> list[tuple[str, str, str]]:
    """`(local, imported, specifier)` for every named import binding of `name`.

    A bare "the host imports a symbol with this name" assertion is satisfied by
    `from './collaborationVisibilityShim'`, so the specifier has to be bound too -
    and so does the *local* name, because `import { X as _rcv } from '<vm>'` binds
    `_rcv`: the guard used to read the imported name and stay green while the call
    site raised `ReferenceError` at render time.  Imports are located on blanked
    source so a literal that merely spells the import cannot stand in for it; the
    specifier is read back out of the original text, which is a literal.
    """
    bindings = []
    for match in re.finditer(
        r"import\s*\{([^}]*)\}\s*from", _blank_comments_and_strings(_script_text(source))
    ):
        specifier = _string_literal_at(source, match.end())
        if specifier is None:
            continue
        for entry in match.group(1).split(","):
            parts = entry.split()
            if not parts or parts[0] != name:
                continue
            local = parts[2] if len(parts) >= 3 and parts[1] == "as" else parts[0]
            bindings.append((local, parts[0], specifier))
    return bindings


def _resolved_module_path(origin: str, specifier: str) -> str:
    """Resolve a relative import specifier against the importing file's path."""
    if not specifier.startswith("."):
        return specifier
    return posixpath.normpath(posixpath.join(posixpath.dirname(origin), specifier))


def collaboration_flag_failures(host: str, module: str) -> list[str]:
    """The flag must *be* the delegation, not merely mention the authority.

    The flag is the *wiring*, not the rule: the rule lives once in the runtime VM
    module and is proven there by an executable truth table.  A token-level check
    is not enough - `!resolve...(...)`, `(resolve...(...), false)`,
    `resolve...(...) || false` and `resolve...(...) ? false : false` all keep every
    token while destroying the rule, so the whole flag expression has to equal the
    delegation.
    """
    # `_blank_comments_and_strings` is offset preserving, so it cannot also rewrite
    # `props['showCollaborationPanel']` into `props.showCollaborationPanel` - the
    # bracket spelling is the same expression to the compiler and used to be accepted.
    # Comment blanking runs first (a bracket access inside a comment is not code), then
    # the length changing normalisation, and the string blanking last.
    body = _computed_argument(
        _blank_string_literals(
            _normalize_bracket_property_access(_blank_comments(_script_text(host)))
        ),
        "hasCollaboration",
    )
    if body is None:
        return ["the collaboration flag is no longer a computed"]
    failures = []
    observed = _normalize_flag_argument(body)
    expected = _normalize_flag_argument(_COLLABORATION_EXPECTED_FLAG)
    if observed != expected:
        failures.append(
            "the collaboration flag is no longer exactly the delegation to the single authority "
            f"(observed `{observed}`)"
        )
    source = _blank_comments_and_strings(_script_text(host))
    if re.search(
        r"(?:^|\n)\s*(?:export\s+)?(?:function|const|let|var|class)\s+"
        + re.escape(_COLLABORATION_AUTHORITY)
        + r"\b"
        + r"|(?:^|\n)\s*(?:export\s+)?(?:const|let|var)\s*\{[^}]*\b"
        + re.escape(_COLLABORATION_AUTHORITY)
        + r"\b[^}]*\}",
        source,
    ):
        failures.append(
            "the host declares its own collaboration visibility authority instead of importing the single one"
        )
    bindings = _authority_named_imports(host, _COLLABORATION_AUTHORITY)
    if not bindings:
        failures.append("the host no longer imports the collaboration visibility authority")
    else:
        for local, imported, specifier in bindings:
            if local != imported:
                failures.append(
                    "the host imports the collaboration visibility authority under another "
                    f"local name (`{local}`)"
                )
            if specifier != _COLLABORATION_VM_IMPORT_SPECIFIER:
                failures.append(
                    "the host no longer imports the collaboration visibility authority from "
                    f"`{_COLLABORATION_VM_IMPORT_SPECIFIER}`"
                )
    if f"export function {_COLLABORATION_AUTHORITY}" not in module:
        failures.append("the collaboration visibility authority is no longer an exported single authority")
    return failures


def _declared_kinds(source: str) -> tuple[list[str] | None, str | None]:
    """`(kinds, failure)` for the declared list, located on blanked source.

    The assignment is *located* on blanked source, so a string that merely spells
    `COLLABORATION_SURFACE_KINDS = [...]` cannot stand in for the declaration; the
    closing bracket is located there too, so a `]` inside a literal cannot truncate
    the list; and the literals are then read back out of the original text, which is
    why the located window is proved aligned first - exactly as in `_body_window`.
    A declaration that cannot be located is a failure, never a silent pass.
    """
    blanked = _blank_comments_and_strings(source)
    match = re.search(_COLLABORATION_KINDS_CONSTANT + r"[^=]*=\s*\[", blanked)
    if match is None:
        return None, "are no longer a literal list"
    if _blank_comments_and_strings(source[match.start():match.end()]) != match.group(0):
        return None, "have a misaligned read window"
    end = blanked.find("]", match.end())
    if end == -1:
        return None, "are no longer a literal list"
    return re.findall(r"['\"]([^'\"]*)['\"]", source[match.end():end]), None


def _expression_failures(body: str | None, canonical: str, subject: str) -> list[str]:
    """The subject must be exactly one `return` of the canonical expression."""
    if body is None:
        return [f"{subject} is gone"]
    expression, failure = _sole_return_expression(body)
    if failure is not None:
        return [f"{subject} {failure}"]
    if expression != canonical:
        return [
            f"{subject} is no longer the canonical expression "
            f"(observed `{expression}`, expected `{canonical}`)"
        ]
    return []


def collaboration_kind_failures(module: str) -> list[str]:
    """The declared collaboration kinds must stay declared *and* be consumed."""
    if _COLLABORATION_KINDS_CONSTANT not in _condense(_blank_comments_and_strings(module)):
        return ["the collaboration surface kinds are no longer declared"]
    failures = []
    declared, locator_failure = _declared_kinds(module)
    if locator_failure is not None:
        failures.append(f"the collaboration surface kinds {locator_failure}")
    else:
        missing = [kind for kind in _COLLABORATION_DECLARED_KINDS if kind not in declared]
        if missing:
            failures.append("the collaboration surface kinds no longer declare: " + ", ".join(missing))
    failures += _authority_expression_failures(
        module,
        _COLLABORATION_KIND_PREDICATE,
        _COLLABORATION_CANONICAL_KIND_PREDICATE,
        "the collaboration kind predicate",
    )
    return failures


def collaboration_node_authority_failures(module: str) -> list[str]:
    """The node authority must stay an existential read that asks the predicate."""
    return _authority_expression_failures(
        module,
        _COLLABORATION_NODE_AUTHORITY,
        _COLLABORATION_CANONICAL_NODE_AUTHORITY,
        "the node authority",
    )


def collaboration_visibility_rule_failures(module: str) -> list[str]:
    """The rule must OR the capability with a suppression-gated node authority."""
    return _authority_expression_failures(
        module,
        _COLLABORATION_AUTHORITY,
        _COLLABORATION_CANONICAL_VISIBILITY_RULE,
        "the collaboration visibility authority",
    )


# Nothing that can *continue* a statement, so a `}` in front of one does not end the
# statement it belongs to.  Reading the `>` of `export type X = Record<string, { ... }>;`
# as the head of a new statement used to report a statement the module never had, and
# the same table keeps `}` in `cond ? { ... } : { ... }` from splitting a statement at
# the `:` that follows it.
#
# The table is the ones that can continue an *expression*, and nothing else.  `!`, `~`,
# `@` and `#` cannot: `{ ... } !x` is not an expression, so Automatic Semicolon
# Insertion applies and the token begins a statement of its own.  Listing them as
# continuations is what let a whole statement hide behind a function body - the payload
# `function gate() { ... }` followed by `!gate()` reported no statement at all, and the
# call ran while the module loaded.  A tail character is a promise that the following
# text is still part of the statement, so only operators that can be infix stay on it.
#
# `+`, `-` and `/` are not infix-only: unary `+`/`-` and a leading `/re/` all *begin* a
# statement after a `}`, and the module executes them while it loads -
# `function gate() { ... }` followed by a line `-gate()` reported no statement, exactly
# as the `!gate()` spelling used to.  What they would have to continue here
# (`const a = { ... } - 1`) is a shape no module in this tree writes, so they leave the
# table and a token after a `}` decides on its own.
_JS_STATEMENT_TAIL_CHARS = frozenset(")]},;.>?:=*%&|^")
# Words that carry a statement on to the next line rather than beginning one of their
# own - and the statement heads that may carry them.  A word is a continuation only
# where the language allows it: `as`/`satisfies` belong to an expression, `is` to a
# signature, `extends`/`implements` to a class, interface or type header, and `from` to
# an import or an export *clause* (`_JS_MODULE_CLAUSE`).  Read everywhere, they glued
# the next statement on to the one above: `type gN3 = { a: number }` followed by a line
# `from: { (Array.prototype as any).includes = () => true }` reported one type alias,
# the shape rule matched its head, and the label's block ran while the module loaded.
# A word whose head is `export` is judged by the *second* token, because `export const
# x = { ... } satisfies T` carries it and `export type X = number` does not.
_JS_CONTINUATION_HEADS = {
    "as": frozenset({"const", "let", "var"}),
    "satisfies": frozenset({"const", "let", "var"}),
    "is": frozenset({"function", "const", "let", "var"}),
    "extends": frozenset(
        {"class", "interface", "type", "abstract", "declare", "default"}
    ),
    "implements": frozenset({"class", "abstract", "declare", "default"}),
}
_JS_MODULE_CLAUSE = re.compile(r"(?:import|export)\s*(?:type\s*)?(?:[*/]|\{)")
# A module clause may begin on the next line - `import\n  { read } from './peer'` and
# `export\n  { g }` are the same statements as their one-line spellings, and there is
# no boundary between a head and its clause for a parser to insert.  The walk ended
# the statement at the line break instead, because `{` is not a continuation character
# and `_statement_continues()` read the token alone: the import's specifier was then
# read out of a window that stopped at `import`, so a legal import was refused as a
# side-effect-only import, and a legal `export\n  { g }` was refused as a form the
# guard cannot read.  A clause token continues the statement only where the statement
# is still nothing but a head.
_JS_MODULE_CLAUSE_TOKENS = frozenset({"{", "*", "type"})


# A declaration whose body is the *end* of its statement: nothing that follows a
# function/class/interface/enum/namespace body can continue it, so the `}` ends the
# statement whatever the next token looks like.  The walk used to decide by the
# following token alone, and that is what let a call hide behind a declaration:
# `export function probe() { ... }` followed by a line starting `/^collect-/.test(` or
# `from(...)` read as one statement whose head was the declaration, so the call was
# never reported and ran while the module loaded.  `type` is deliberately absent: a
# type expression really does carry the `}` of a type literal on into `>`, `|` and `&`
# (`Record<string, { a: 1 }>`), and those three cannot begin a statement, so they stay
# continuations for every head.
_JS_CLOSED_DECLARATION_HEADS = frozenset(
    {"function", "class", "interface", "enum", "namespace", "declare", "abstract"}
)
_JS_DECLARATION_PREFIXES = frozenset({"export", "default", "async", "declare", "abstract"})
_JS_STRUCTURAL_CONTINUATIONS = frozenset({"else", "catch", "finally", "while"})
_JS_TYPE_EXPRESSION_CONTINUATIONS = frozenset(">|&")


def _closed_declaration_head(source: str, offset: int) -> str | None:
    """The declaration keyword at `offset` whose body ends the statement, if any.

    Only the tokens before the statement's first `=` are read, so
    `export const f = function () { ... }` stays a variable declaration - its `}`
    can still be followed by `as`/`satisfies` - while `export default class X { ... }`
    is a class declaration whose body is the end of the statement.
    """
    head = source[offset:offset + 96].split("=", 1)[0]
    words = _js_identifier_words(head)
    if not words:
        return None
    if words[0] in _JS_CLOSED_DECLARATION_HEADS:
        return words[0]
    if words[0] in _JS_DECLARATION_PREFIXES:
        for word in words[1:4]:
            if word in _JS_CLOSED_DECLARATION_HEADS:
                return word
    return None


def _statement_carries(source: str, offset: int | None, word: str) -> bool:
    """Whether the statement at `offset` may be carried on to the next line by `word`."""
    if offset is None:
        return False
    window = re.sub(r"\s+", " ", source[offset:offset + 64])
    if word == "from":
        return _JS_MODULE_CLAUSE.match(window) is not None
    heads = _JS_CONTINUATION_HEADS.get(word)
    if heads is None:
        return False
    words = _js_identifier_words(window)
    if not words:
        return False
    if word == "as" and _JS_MODULE_CLAUSE.match(window) is not None:
        # `import * as ns` / `export * as ns` carry the `as` inside the clause itself.
        return True
    candidates = [words[0]]
    if words[0] == "export" and len(words) > 1:
        candidates.append(words[1])
    return any(candidate in heads for candidate in candidates)


def _statement_awaits_module_clause(
    source: str, offset: int | None, index: int
) -> bool:
    """Whether the statement at `offset` is still only an `import`/`export` head.

    The head is read up to `index`, the position the walked token starts at, so a
    statement that has already named its clause (`import { x }`, `export * from
    './y'`) is not a head awaiting one: only `import`, `import type`, `export` and
    `export type` are.
    """
    if offset is None:
        return False
    head = re.sub(r"\s+", " ", source[offset:index])
    return re.match(r"(?:import|export)\s*(?:type\s*)?$", head) is not None


# The declarations whose *type-parameter list* may begin on the next line - `export
# function read` broken before `<T>(value: T)`, `export class Box` before `<T> { ... }`,
# `export interface I`, `export type A`, and the `function` a function expression ends
# with (`const f = function` before `<T>(x: T)`); all five are legal TypeScript and the
# real parser continues the declaration across the break, so the guard must too.
# The declarations whose *type-parameter list* may begin on the next line: a
# declaration head that has named its subject and has not reached `<` -
# `export function read` broken before `<T>(value: T)`, `export class Box` before
# `<T> { ... }`, `export interface I`, `export type A`; and the two keywords a
# function/class *expression* ends with (`export const f = function` before
# `<T>(x: T)`, `export const C = class`).  All of them are legal TypeScript and the
# real parser continues the declaration across the break, so the guard must too.
_JS_TYPE_PARAMETER_HEAD_KEYWORDS = frozenset(
    {"function", "class", "interface", "type", "enum", "namespace"}
)
_JS_HEAD_MODIFIERS = frozenset(
    {"export", "declare", "default", "abstract", "async", "const", "let", "var"}
)
_JS_HEAD_EXPRESSION_KEYWORDS = frozenset({"function", "class"})
_JS_HEAD_SINGLE_CHARACTER_TOKENS = frozenset("=;,.(){}[]<>|&!?:+-*/%^~")


def _js_head_tokens(text: str) -> list[str]:
    """The identifiers and single-character punctuation of a statement head.

    Everything else is stepped over, so a comment between two words cannot hide the
    shape this test reads.  Identifiers are read with the lexer's own continuation
    rule, which is what keeps a keyword the lexer is *extending* into a longer name
    (`extends\u0301`, `extends\u203f`) out of the keyword tests below.
    """
    tokens: list[str] = []
    index = 0
    while index < len(text):
        identifier = _js_identifier_at(text, index)
        if identifier is not None:
            tokens.append(identifier)
            index += len(identifier)
            continue
        character = text[index]
        if _js_identifier_start_non_ascii(character):
            end = index + 1
            while end < len(text) and _js_identifier_continue(text[end]):
                end += 1
            tokens.append(text[index:end])
            index = end
            continue
        if character in _JS_HEAD_SINGLE_CHARACTER_TOKENS:
            tokens.append(character)
        index += 1
    return tokens


def _js_head_token_is_name(token: str) -> bool:
    """Whether a head token is a name the declaration head can carry.

    Either half of the lexer's start rule may open the name: the ASCII half the walk
    reads, or the non-ASCII one it deliberately does not.
    """
    return bool(token) and (
        _js_identifier_start(token[0]) or _js_identifier_start_non_ascii(token[0])
    )


def _js_head_declared_tail(tokens: list[str]) -> list[str]:
    """The tail of a declaration head with the generator mark stepped over.

    `function* gen` names one thing: the `*` marks the declaration a generator, it is
    not a second name, and counting it as one read `export function* gen` broken before
    `<T>` as a head that had named a subject beyond the one name the declaration
    carries.  Real `tsc 5.9.3` and `esbuild 0.21.5` continue such a declaration across
    the break.  The mark can name nothing in any head this test reads: they are the
    declaration keywords after their modifiers, or `name = function`/`class`, and `*`
    spells no name and no keyword in either.
    """
    return [token for token in tokens if token != "*"]


def _statement_awaits_type_parameters(
    source: str, offset: int | None, index: int
) -> bool:
    """Whether the statement at `offset` is still only a head waiting for `<...>`.

    `<` is the one token that is *not* infix: a line that opens with it either continues
    a declaration that has not reached its type-parameter list yet, or begins a
    statement of its own - TypeScript's `<T>expr` assertion, which runs while the module
    loads.  The parser settles it by where the statement stands, so the whole head is
    read as a *shape*: the modifiers (`export`, `declare`, `abstract`, ...), then either
    a declaration keyword with at most the name it declares, or `name =` followed by the
    `function`/`class` an expression ends with.  `export function read` and
    `export class Box` are still waiting for `<T>`; `export type gB = number`,
    `export type A = Foo<Bar>` and `export type A = { type: string }` are not - those
    heads carry punctuation past the name, so the line below really is a statement
    (`[];` and `<C>[];` both reach the emitted output, checked with `esbuild 0.21.5` and
    `tsc 5.9.3`).  Reading the head's *last two words* instead let a name that collides
    with a keyword decide it - `export type CollaborationKindName = { type: string }`
    followed by `<unknown>...();` read as "still waiting for `<T>`" and the poisoned
    assertion ran while the module loaded, in both the authority body and the reviewed
    import closure.  Refusing a `<` this shape test cannot place is the same direction,
    and every declaration head it *can* place keeps compiling.

    Two spellings the shape test read as "no head at all" are heads.  The generator
    mark is stepped over rather than counted as a second name (`export function* gen`,
    `export async function* gen`, a local `function* gen`), and a name the ASCII walk
    cannot spell is read as the one name the head carries (`export function \u540d`).
    Both are legal cross-line continuations - `tsc 5.9.3` and `esbuild 0.21.5` compile
    the second line as the declaration's type-parameter list - and neither can carry a
    statement: a head that has reached neither `(` nor `{` compiles only if what follows
    it is a type-parameter list, which is a type and not code.
    """
    if offset is None:
        return False
    tokens = _js_head_tokens(_blank_comments_and_strings(source[offset:index]))
    position = 0
    modifiers: list[str] = []
    while position < len(tokens) and tokens[position] in _JS_HEAD_MODIFIERS:
        modifiers.append(tokens[position])
        position += 1
    rest = tokens[position:]
    if not rest:
        return False
    if rest[0] in _JS_TYPE_PARAMETER_HEAD_KEYWORDS:
        tail = _js_head_declared_tail(rest[1:])
        if not tail:
            # `export default function` / `export default class` may stay anonymous.
            return "default" in modifiers and rest[0] in _JS_HEAD_EXPRESSION_KEYWORDS
        return len(tail) == 1 and _js_head_token_is_name(tail[0])
    if len(rest) >= 3 and _js_head_token_is_name(rest[0]) and rest[1] == "=":
        tail = _js_head_declared_tail(rest[2:])
        if tail and tail[0] == "async":
            tail = tail[1:]
        return len(tail) == 1 and tail[0] in _JS_HEAD_EXPRESSION_KEYWORDS
    return False


def _statement_continues(source: str, index: int, offset: int | None) -> bool:
    """Whether the text at `index` continues the statement a top-level `}` closed.

    The token is read as the lexer reads it, blanks and combining marks included: a
    keyword the lexer is *extending* into a longer name is not the keyword, and the
    label below it is a statement of its own.
    """
    token, token_end = _js_next_token(source, index)
    if not token:
        return True
    if token == "<":
        # Odd `token_end` arithmetic, on purpose: the token starts where it ends minus
        # its own length, and the head test reads the statement *up to* it.
        return _statement_awaits_type_parameters(
            source, offset, token_end - len(token)
        )
    if token in _JS_STATEMENT_TAIL_CHARS:
        return True
    if token in _JS_STRUCTURAL_CONTINUATIONS:
        return True
    if token in _JS_MODULE_CLAUSE_TOKENS and _statement_awaits_module_clause(
        source, offset, index
    ):
        return True
    if _statement_labels(source, token_end):
        return False
    return _statement_carries(source, offset, token)


# The characters the walk steps over as blanks.  `str.isspace()` covers the Unicode
# space separators - `U+00A0` and its neighbours - but not the format characters a
# reader does not see either, and those are as invisible to the label test as a space
# is: the byte-order mark `U+FEFF` is whitespace to the TypeScript lexer, and the
# zero-width space with the two joiners are stepped over here so that a label cannot
# be padded with one.
_JS_INVISIBLE_CHARACTERS = frozenset("\u200b\u200c\u200d\ufeff\u2060")


def _js_is_blank(character: str) -> bool:
    """Whether the statement walk steps over this character as whitespace."""
    return character.isspace() or character in _JS_INVISIBLE_CHARACTERS


def _statement_labels(source: str, end: int) -> bool:
    """Whether the word that ends at `end` is a statement *label*, not a continuation.

    Every word in the continuation table is an identifier, so every one of them is a
    legal label as well - and a labelled statement runs while the module loads.
    `type gA3 = { a: number }` followed by a line
    `extends: { (Array.prototype as any).includes = () => true }` was therefore glued
    into one statement whose head was the alias, exactly as the `from:` spelling was:
    the head check alone cannot refuse it, because `extends` really does continue a
    `type` header (`type Result<T> = T` broken before its `extends` clause).  The
    colon tells the two apart.  No continuation is ever followed by one - `T extends
    U`, `x satisfies T` and `import { a } from './x'` all name something after the
    word - while a label always is, whitespace aside.

    *How much* whitespace was the whole question, and the test answered it with a fixed
    window: `source[end:end + 16]` looked sixteen characters ahead, so sixteen blanks of
    any kind pushed the `:` out of the window, the word read as a continuation, and the
    statement below it was glued on.  `export {}` followed by a line
    `as` + sixteen spaces + `: { (Array.prototype as any).includes = () => false }` +
    `break as;` reported one statement whose head was the export - which the ladder
    passed while the label's block ran as the module loaded, in the browser and not in
    the gate's own node domain.  The window is gone: the blanks are stepped over,
    however many there are and whatever kind of invisible character they are, and the
    next character decides.
    """
    index = end
    while index < len(source) and _js_is_blank(source[index]):
        index += 1
    if source[index:index + 1] == ":":
        return True
    # A character that can only *continue* an identifier, right where the word the walk
    # read ended, says the walk read a shorter word than the lexer does: `extends\u0301`
    # is one name, not the keyword, and the colon below it belongs to a label whose block
    # runs while the module loads.  Every word in the continuation table is a name the
    # lexer may extend, so the safe reading of an extension is the label.
    return index < len(source) and _js_word_may_extend(source[index])


def _can_end_statement(character: str) -> bool:
    """Whether a statement may end at this significant character.

    `>` is here because a type-argument list ends with it: `export type A =
    Record<string, number>` is a complete statement without a `;`, and read as an
    operator that could not end one, the walk absorbed the line below into the alias -
    this predicate is the only thing it consults before it looks at the next line - so
    the shape rule matched the alias' head and
    `(Array.prototype as any).includes = () => true` ran while the module loaded.  A
    `>` that really does continue a statement (`Foo<Bar>` broken before its `extends`
    clause, or before a `|`) is decided by `_statement_continues()` on the token that
    follows, not here.  The closing quotes are the same case for the callers that read
    raw text: the literal ended there, and a line cannot end on an *opening* quote.
    """
    return character.isalnum() or character in "_$)]}>\'\"`"


def _js_previous_significant(source: str, index: int) -> str:
    """The last character before `index` the statement walk does not step over.

    The character is what tells a declaration's *body* brace from a brace that
    belongs to a type in its header: `function f(): { a: 1 } {` opens the type
    literal after the `:`, which no declaration header ends on, and the body after
    the `}`, which a header does end on.  Without the distinction both braces read
    as the body, so the body was reported as a statement of its own.
    """
    cursor = index - 1
    while cursor >= 0 and _js_is_blank(source[cursor]):
        cursor -= 1
    return source[cursor] if cursor >= 0 else ""


def _module_statements(source: str) -> list[tuple[int, str]]:
    """`(offset, first token)` for every statement at the module's own level.

    A statement begins at the start of the file, after a top-level `;`, or after a
    top-level `}` that ends one.  Bracket depth comes from the blanked source, so a
    `;` inside a body - or inside a comment or a string, both already blanked - does
    not open a statement, and a `}` that merely closes an import's binding list, an
    `extends` object type, or a `do`/`try` body does not either.  A statement whose
    first token is not an identifier is reported with the character it starts with,
    so a bare expression such as `(Array.prototype as any).includes = ...` is not
    mistaken for a declaration.

    Three shapes used to leave whole statements invisible, and each of them runs code
    while the module loads:

    * A `(`/`[`/`{` while a statement was pending took the bracket branch *before*
      the pending branch, so the opener was pushed and never reported.  `{ poison() }`
      and `(() => { poison() })()` were therefore read as no statement at all, and the
      first token is now reported for them like any other.
    * TypeScript needs no `;`, and Automatic Semicolon Insertion makes the boundary
      invisible to a character walk: `export type T = typeof KINDS` followed by
      `if (typeof window !== 'undefined') { ... }` left the `if` inside a statement
      the walk thought it was still reading.  An identifier that begins a line whose
      previous significant character can *end* a statement therefore begins one too,
      and only the words that carry a declaration on to the next line are exempt.
    * The bracket stack recognised no difference between a function body and a
      type-literal brace, so what followed a top-level `}` decided by identifier
      shape alone.  It is the following character that decides now, and a tail
      character (`,`, `;`, `>`, `:`, ...) means the statement is still open.
    * That left the one pair of braces the following character cannot separate: a
      `}` followed by a `{`.  `function f(): { a: 1 } { ... }` closes the type
      literal and then opens the body, and the walk ended the declaration at the
      type literal, so the body brace was reported as a statement of its own - a
      legal function read as load-time code.  Which brace is the body is decided
      where it is opened now, from the character before it: a `:` opens a type
      literal and a `)`/`]`/`}`/identifier opens the body.
    """
    statements: list[tuple[int, str]] = []
    stack: list[str] = []
    pending = True
    line_break = False
    previous = ""
    closed_head: str | None = None
    # Whether the top-level group now open is the body that ends the statement it
    # belongs to.  One top-level group is open at a time, so one flag is enough: a
    # header brace (`function f(): { a: 1 }`) leaves it clear and the body brace
    # after it sets it, which is what keeps the walk from ending the declaration at
    # the type literal and reporting the real body as a statement of its own.
    body_group = False
    index = 0
    length = len(source)
    while index < length:
        character = source[index]
        if character in "([{":
            if not stack:
                if pending:
                    statements.append((index, character))
                    closed_head = _closed_declaration_head(source, index)
                    pending = False
                    body_group = character == "{"
                elif (
                    line_break
                    and _can_end_statement(previous)
                    and (
                        character in "(["
                        # A `{` on its own line is the body of the declaration the
                        # statement is still spelling - `export function f():
                        # Record<string, number>` broken before its brace - and for
                        # every other head it is a *block*, which runs while the
                        # module loads.  `closed_head` is what tells the two apart:
                        # only a declaration whose body ends its statement is still
                        # waiting for one, and
                        # `export type A = Record<string, number>` is not.
                        or (character == "{" and closed_head is None)
                    )
                    # A module statement's clause is not a statement of its own:
                    # `import\n  { read } from './peer'` spells its binding list on the
                    # next line, and the same test that carries it there for the
                    # line-break path decides it here.
                    and not _statement_continues(
                        source, index, statements[-1][0] if statements else None
                    )
                ):
                    statements.append((index, character))
                    closed_head = _closed_declaration_head(source, index)
                    pending = False
                    body_group = character == "{"
                else:
                    # The group belongs to the statement already open.  A `{` here is
                    # the declaration's body only when its header has ended: the `:`
                    # that opens `function f(): { a: 1 }` is followed by a type
                    # literal, and only the `}` that ends that literal is followed by
                    # the body.  Reading both as the body ended the declaration at the
                    # type literal and reported the body brace as its own statement.
                    body_group = character == "{" and _can_end_statement(
                        _js_previous_significant(source, index)
                    )
            stack.append(character)
            previous = character
            line_break = False
        elif character in ")]}":
            if stack:
                stack.pop()
            if not stack and character == "}":
                token, token_end = _js_next_token(source, index + 1)
                labelled = token != "" and _statement_labels(source, token_end)
                closes_body = body_group
                body_group = False
                if closed_head is not None:
                    # Only the body of a declaration ends its statement: a `}` that
                    # closed a type literal in the header leaves the declaration open,
                    # and the brace that follows is the body.  When it really is the
                    # body, the next token starts a new statement unless it belongs to
                    # the same one (`else`/`catch`/... ) or cannot begin one at all
                    # (`>`/`|`/`&` continue a type expression).
                    if closes_body and (
                        token not in _JS_STRUCTURAL_CONTINUATIONS
                        and token not in _JS_TYPE_EXPRESSION_CONTINUATIONS
                    ):
                        pending = True
                        closed_head = None
                elif labelled or not _statement_continues(
                    source, index + 1, statements[-1][0] if statements else None
                ):
                    pending = True
                    closed_head = None
            previous = character
            line_break = False
        elif not stack:
            if character == ";":
                pending = True
                closed_head = None
            elif _js_is_blank(character):
                # `U+2028`/`U+2029` terminate a line for Automatic Semicolon
                # Insertion exactly as `\n` does, and a gate hidden behind one was
                # read as a continuation of the statement above it.
                if character in "\n\u2028\u2029":
                    line_break = True
            elif pending:
                word = _js_identifier_at(source, index)
                token = word if word is not None else character
                statements.append((index, token))
                closed_head = _closed_declaration_head(source, index)
                pending = False
                previous = token[-1]
                line_break = False
            else:
                word = _js_identifier_at(source, index)
                if (
                    line_break
                    and word is not None
                    and _can_end_statement(previous)
                    and (
                        _statement_labels(source, index + len(word))
                        or not _statement_carries(
                            source,
                            statements[-1][0] if statements else None,
                            word,
                        )
                    )
                ):
                    statements.append((index, word))
                    closed_head = _closed_declaration_head(source, index)
                    pending = False
                elif (
                    # A statement does not have to begin with a name.  A line that
                    # opens a regular expression or a template literal is a statement
                    # of its own, and it was invisible here: the walk read the
                    # character, kept it as `previous`, and reported nothing - so
                    # `export type A = 'x'` followed by a line opening
                    # `/^collect-/.test(location.href) && (Array.prototype as
                    # any).includes = () => true` read as one alias whose head matched
                    # the shape rule, and the call ran while the module loaded.  What
                    # continues the statement is the same test the identifier branch
                    # uses: a character that can only be infix (`.`, `|`, `?`, `=`,
                    # ...) keeps it open, and anything else begins a new statement.
                    line_break
                    and word is None
                    and _can_end_statement(previous)
                    and not _statement_continues(
                        source, index, statements[-1][0] if statements else None
                    )
                ):
                    statements.append((index, character))
                    closed_head = _closed_declaration_head(source, index)
                    pending = False
                previous = character if word is None else word[-1]
                line_break = False
        index += 1
    return statements


def _statement_excerpt(source: str, offset: int, width: int = 44) -> str:
    """The statement's first `width` characters with whitespace removed.

    The excerpt is what a refusal quotes back, so it is read the way the rules read
    it: taken from the raw window, a statement padded with four hundred spaces quoted
    the padding and hid the code the refusal was about.
    """
    return _condense(_statement_text(source, offset, width))


# How much of one statement the guard reads before it gives up and refuses.  The bound
# is there so the read is finite, not to bound what a statement may hold: the window
# counts *collapsed* characters, so padding cannot fill it, and a statement longer than
# this is reported as unfinished rather than judged on the part that fit.  It has to be
# wide enough to reach the deciding token of the longest shape the ladders judge - a
# re-export's `from` clause sits after the whole named list, and sixty exported names
# already reach about eleven hundred collapsed characters - while still being a bound.
_COLLABORATION_STATEMENT_WINDOW = 2000


def _statement_window(
    source: str, offset: int, width: int = _COLLABORATION_STATEMENT_WINDOW
) -> tuple[str, bool]:
    """The statement at `offset`, and whether the window ran out before its end.

    The window counts *collapsed* characters, not raw ones.  Reading
    `source[offset:offset + width]` first let four hundred spaces stand where the
    statement should be, so `export` + 410 spaces read as `export ` and every rung of
    the export ladder below found nothing to match: the statement ran while its module
    loaded and the guard stayed green.  Whitespace is folded as it is read, so only
    text can fill the window.

    Where the statement *ends* is read the way `_module_statements()` reads it, not by
    looking for a `;`: this tree carries no semicolons at all, so a "read to the next
    `;`" window never found one and every signature longer than the window came back
    truncated.  A statement ends at a `;` outside every bracket, or at a line break
    whose last significant character can end a statement and whose next token cannot
    carry it on.  Bracket depth comes from the text as passed, so a terminator inside
    a body does not end the statement that opened it.

    Text can still fill the window: a long enough `export { ...names... } from './x'`
    pushes the `from` clause past `_COLLABORATION_STATEMENT_WINDOW`, the ladder cannot
    tell it from the local named export it falls back to, and `relative_edges()` never
    follows the edge - so a statement the window did not finish is reported as
    unfinished, and the callers refuse it rather than judge the half they can see.
    """
    characters: list[str] = []
    space = False
    depth = 0
    previous = ""
    index = offset
    length = len(source)
    while index < length:
        character = source[index]
        if character == ";" and not depth:
            return "".join(characters), False
        if (
            depth == 0
            and character in "\n\u2028\u2029"
            and _can_end_statement(previous)
            and not _statement_continues(source, index + 1, offset)
        ):
            return "".join(characters), False
        if len(characters) >= width:
            return "".join(characters), True
        if character in "([{":
            depth += 1
        elif character in ")]}":
            if depth:
                depth -= 1
        if _js_is_blank(character):
            space = bool(characters)
        else:
            if space:
                characters.append(" ")
                space = False
            characters.append(character)
            previous = character
        index += 1
    return "".join(characters), False


def _statement_text(
    source: str, offset: int, width: int = _COLLABORATION_STATEMENT_WINDOW
) -> str:
    """`_statement_window`'s text, for the callers that judge a statement they can read."""
    return _statement_window(source, offset, width)[0]


def _collaboration_import_failure(module: str, offset: int) -> str | None:
    """The refusal for the import at `offset`, or `None` when the guard has read it.

    The statement is read out of the **comment-blanked** text and the specifier is
    the one the `from` clause names - not, as before, the last string literal in the
    window.  `import { x } from './collaborationPoison' /* './valueUtils' */` passed
    the reviewed list on the strength of that comment; TypeScript drops the comment,
    so `./collaborationPoison` really did run its load-time code inside the gate's own
    import.  Anything that is not a plain `<specifier>;` is refused rather than
    guessed at.
    """
    statement = _statement_text(_blank_comments(module), offset)
    if re.match(r"import\s+type\b", statement):
        return None
    if not re.search(r"\bfrom\b", statement):
        return (
            "the collaboration authority imports a module for its side effects only "
            f"(`{statement[:120]}`), so another file's load-time code runs inside the "
            "gate's own import"
        )
    match = re.search(r"\bfrom\s*(['\"])([^'\"]*)\1", statement)
    if match is None:
        return (
            "the collaboration authority imports a module in a shape the guard cannot "
            f"read (`{statement[:120]}`)"
        )
    if statement[match.end():].strip():
        return (
            "the collaboration authority has text after its import specifier, so the "
            f"guard cannot tell which module is imported (`{statement[:120]}`)"
        )
    if match.group(2) not in _COLLABORATION_MODULE_IMPORT_SPECIFIERS:
        return (
            "the collaboration authority imports a module whose load-time code the "
            "guard has not reviewed "
            f"(`{statement[:120]}`)"
        )
    return None


def collaboration_module_scope_failures(module: str) -> list[str]:
    """The authority module must not observe the runtime, nor run load-time code.

    The token-level checks above only ever read the three authority bodies, and the
    executable proof only ever compares their results - so a module-level statement
    outside them is invisible to both layers.  Worse, the proof's browser-domain
    replay installs `window` *after* importing the module, so a gate evaluated
    during module load (a top-level `if (typeof window !== 'undefined') { ... }`, a
    per-load poisoning of `Array.prototype.includes`) ran in neither domain: the
    gate stayed green and the rule was dead in the browser.  Nothing in the module
    has any business reading the environment at all - the rule is a pure function of
    its argument - so the environment is banned by name anywhere in the module, and
    a statement at the module's own level must be a declaration.
    """
    unsegmentable = _js_unsegmentable_spans(module)
    if unsegmentable:
        start, _end, kind, terminated, _crossed = unsegmentable[0]
        if kind == "ambiguous":
            return [
                f"the collaboration authority cannot be segmented: the `/` at offset "
                f"{start} follows a `>` that may close a type-argument list or compare, "
                "and only one of those readings can be right, so every statement below "
                "it is unread rather than absent"
            ]
        return [
            "the collaboration authority cannot be segmented: "
            + (
                f"an unterminated {kind} starts at offset {start}"
                if not terminated
                else f"a {kind} literal starts at offset {start} and only closes below "
                "the line it opened on, so it is not a literal"
            )
            + ", so every statement below it is unread rather than absent"
        ]
    blanked = _blank_comments_and_strings(module)
    failures = _environment_reference_failures(blanked, "the collaboration authority")
    for offset, token in _module_statements(blanked):
        statement, truncated = _statement_window(blanked, offset)
        if token in _COLLABORATION_MODULE_DECLARATIONS:
            if token in ("const", "let", "var"):
                failures.append(
                    "the collaboration authority binds a module-level value that no "
                    f"layer reads at load time: `{_statement_excerpt(blanked, offset)}`"
                )
            elif (
                token in _COLLABORATION_DECLARATION_SHAPES
                and _COLLABORATION_DECLARATION_SHAPES[token].match(
                    _statement_text(module, offset)
                )
                is None
            ):
                # The whitelist names the *spelling* `type`/`interface`/`function`, so
                # `type(...)` was read as a type alias: the first token is the keyword
                # and nothing below it looked at the shape.  A call at the module's own
                # level runs while it loads, which is the one thing this whole function
                # exists to refuse.
                failures.append(
                    "the collaboration authority starts a statement with the "
                    f"{token} keyword but declares nothing, so it runs while it loads "
                    f"(`{_statement_excerpt(blanked, offset)}`)"
                )
            elif token == "import":
                import_failure = _collaboration_import_failure(module, offset)
                if import_failure is not None:
                    failures.append(import_failure)
            elif token == "export" and _COLLABORATION_MODULE_BINDING.match(statement):
                if not _COLLABORATION_MODULE_KINDS_DECLARATION.match(
                    _statement_text(module, offset)
                ):
                    failures.append(
                        "the collaboration authority evaluates an expression while it "
                        "loads: a module-level binding may only be the kind list of "
                        f"string literals (`{_statement_excerpt(blanked, offset)}`)"
                    )
            elif token == "export" and re.match(
                _COLLABORATION_EXPORT_LOAD_TIME_DECLARATION, statement
            ):
                failures.append(
                    "the collaboration authority exports a declaration whose body or "
                    "initializer is evaluated while the module loads "
                    f"(`{_statement_excerpt(blanked, offset)}`)"
                )
            elif token == "export" and (
                re.match(_COLLABORATION_EXPORT_DECLARATION, statement)
                or (
                    re.match(r"export\s*\{", statement)
                    and not re.search(r"\bfrom\b", statement)
                    # The rung below allows a local named export on the strength of
                    # the `from` it did *not* find, so it may only judge a statement
                    # it read to the end: `export { a000, b001, ... sixtyNames }
                    # from './x'` pushes the clause past the window, reads as the
                    # local export it is not, and the module on the far end runs its
                    # load-time code inside the gate.  A truncated statement falls
                    # through to the refusal beneath rather than be vouched for.
                    and not truncated
                )
            ):
                pass
            elif token == "export" and truncated and re.match(
                r"export\s*\{", statement
            ):
                failures.append(
                    "the collaboration authority exports a named list longer than "
                    "the guard can read, so a `from` clause may sit past the window "
                    "and evaluate another module at load time outside every authority "
                    f"(`{_statement_excerpt(blanked, offset)}`)"
                )
            elif token == "export":
                failures.append(
                    "the collaboration authority re-exports or default-exports "
                    f"(`{_statement_excerpt(blanked, offset)}`), which evaluates another "
                    "module at load time outside every authority"
                )
            continue
        failures.append(
            "the collaboration authority runs a statement outside its declared "
            f"authorities, which no layer reads at load time: `{_statement_excerpt(blanked, offset)}`"
        )
    return failures


def _environment_reference_failures(source: str, subject: str) -> list[str]:
    """The refusals for a module that probes the environment it happens to run in.

    The environment is the one thing that differs between the two domains the
    authority is checked in, so it is the ingredient every domain-asymmetric payload
    needs: the gate's node run and the executable proof's browser replay can only
    disagree if something asked which one it was in.  The list is deliberately wider
    than the spelling that was used, because enumerating one more global moves the
    hole to the next spelling rather than closing it - which is why the *authority*
    module is held to the stronger structural rule as well.
    """
    failures = []
    for global_name in _COLLABORATION_ENVIRONMENT_GLOBALS:
        if re.search(r"(?<![\w$.])" + re.escape(global_name) + r"(?![\w$])", source):
            failures.append(
                f"{subject} is no longer a pure function of its input: the module reads "
                f"the runtime environment (`{global_name}`), so its rule can differ "
                "between the gate and the browser"
            )
    if re.search(r"\bimport\s*\.\s*meta\b", source):
        failures.append(
            f"{subject} is no longer a pure function of its input: the module reads "
            "`import.meta`, so its rule can differ between the gate and the browser"
        )
    return failures


# A relative import is a promise that the guard read the module behind it, and the
# promise was never kept: `_COLLABORATION_MODULE_IMPORT_SPECIFIERS` named
# `./valueUtils` and `../../app/contracts/v2/store`, and the guard compared the
# specifier against that list without ever opening either file.  A load-time gate
# parked in either of them kept `contractRuntimeVm.ts` character for character the
# module the reviewers read, kept every authority body a pure function, and stayed
# green while the rule was dead in the browser - the imported file's top-level code
# runs inside the gate's own import, and the proof's browser replay installs `window`
# after that import has already happened.  The closure is therefore read, and every
# module in it is held to the environment ban.
_COLLABORATION_IMPORT_CLOSURE_SUFFIXES = (
    ".ts",
    ".tsx",
    ".js",
    "/index.ts",
    "/index.tsx",
)
_COLLABORATION_IMPORT_CLOSURE_DEPTH = 8
_COLLABORATION_IMPORT_CLOSURE_FILES = 40
# `export { x } from './y'` and `export * from './y'` evaluate `./y` at load time
# exactly as an `import` does, and the walk used to read `import` statements only, so
# a re-export was an edge the guard never followed.  The pattern is anchored on the
# export clause rather than on any `from` in the statement, so an initializer that
# merely calls something called `from` is not mistaken for an edge.
# The clause is spelled with `\s*`, not `\s+`: `export*from'./x'` and
# `export{a}from'./x'` are the same re-export written with no space after the
# keyword, so a pattern that demanded one let the whole family past - the ladder did
# not recognise the statement and the edge walk did not follow it, which is the one
# shape this rule exists to refuse.
_COLLABORATION_RE_EXPORT = re.compile(
    r"\s*export\s*(?:\*|\{[^}]*\})(?:\s*as\s+[\w$]+)?\s*from\b\s*(['\"])([^'\"]*)\1"
)
# The ladder can only tell a local named export from an edge by reading the clause
# after the list, so the list has to fit in the window: these two sit either side of
# `_COLLABORATION_STATEMENT_WINDOW`, and the pair is what pins both halves of the rule
# - a list the guard can read is followed to its target, a list it cannot is refused
# rather than allowed on the strength of the `from` it never saw.
_COLLABORATION_READABLE_EXPORT_NAMES = tuple(f"exportedName{i:03d}" for i in range(60))
_COLLABORATION_UNREADABLE_EXPORT_NAMES = tuple(f"exportedName{i:03d}" for i in range(400))
_COLLABORATION_READABLE_RE_EXPORT = (
    "export { "
    + ", ".join(_COLLABORATION_READABLE_EXPORT_NAMES)
    + " } from './collaborationProbe';\n"
)
_COLLABORATION_UNREADABLE_RE_EXPORT = (
    "export { "
    + ", ".join(_COLLABORATION_UNREADABLE_EXPORT_NAMES)
    + " } from './collaborationProbe';\n"
)
_COLLABORATION_READABLE_RE_EXPORT_TARGET = "".join(
    f"export function {name}(): number {{ return {index}; }}\n"
    for index, name in enumerate(_COLLABORATION_READABLE_EXPORT_NAMES)
)


def _resolve_local_module(origin: str, specifier: str) -> tuple[str, str] | None:
    """Read the file a relative `specifier` names from `origin`, or `None`.

    Only relative specifiers are resolved: a bare specifier is a package, and a
    package is not part of the reviewed closure.
    """
    if not specifier.startswith("."):
        return None
    base = posixpath.normpath(posixpath.join(posixpath.dirname(origin), specifier))
    for suffix in _COLLABORATION_IMPORT_CLOSURE_SUFFIXES:
        candidate = ROOT / (base + suffix)
        if candidate.is_file():
            return base + suffix, candidate.read_text(encoding="utf-8")
    return None


def collaboration_import_closure_failures(
    origin: str,
    source: str,
    resolver=_resolve_local_module,
    depth: int = _COLLABORATION_IMPORT_CLOSURE_DEPTH,
) -> list[str]:
    """Every local module the authority imports must stay environment-blind.

    The runtime closure is walked - `import type` is erased and therefore skipped -
    and each module in it must (a) resolve to a file the guard can read, (b) hold no
    unterminated opaque span, (c) name no runtime-environment global and no
    `import.meta`, and (d) hold nothing that is evaluated while it loads.  The
    authority module's *binding* exemption used to be copied here, on the reasoning
    that these modules legitimately carry module-level `const`s; they do not, and the
    exemption underneath was a statement whitelist, so the probe simply moved into an
    imported file: `if (typeof screen !== 'undefined') { ... }` at the top of
    `valueUtils.ts` was read by nothing, because the walk only looked at what each
    module *imported* and never at what it *ran*.  What is left at a closure member's
    own level is an import and a shape rule: a function or a type declaration is
    allowed, because it runs when it is called rather than when the module loads,
    and a statement that runs while it loads is not.

    Every edge is followed, not just the static `import ... from` ones: a re-export
    (`export { x } from './y'`) and a dynamic `import('./y')` reach a module exactly
    as an import does, and the poison that arrived through either was never opened.
    Both bounds are refusals rather than truncations - a closure the guard stopped
    walking is a closure it can no longer claim to have read.
    """
    failures: list[str] = []
    seen = {origin}

    def run_failures(
        path: str, blanked: str, commented: str, imported: bool
    ) -> list[str]:
        """The statement rules a closure member must satisfy.

        A closure member is a module the authority reaches at *load* time, so nothing
        in it may be evaluated while it loads.  The whitelist used to accept a
        module-level binding, and that is where the family stayed open: `export const
        dead = typeof Element !== 'undefined' ? (poison(), 1) : 0;` is a declaration
        whose *initializer* is load-time code, so the environment name it reaches for
        only has to be one the enumeration does not list.  The export ladder left the
        same hole behind `export default class RouteProbe { static x = ... }` - the
        declaration-body check ran after the allow-list, and `export default` was not
        on it - and behind `export = <expression>`.  Listing one more name, or one
        more export spelling, only moves the hole, so the rule is a *shape*: a
        function or a type declaration is allowed, because its body runs when it is
        called; everything else at the member's own level is refused.  The rule is
        written against the real closure - four modules of functions and types, no
        module-level binding, no class, no default export.

        The *origin* is exempt: it is the authority module itself, whose own level
        `collaboration_module_scope_failures` already judges - more tightly than this
        rule does (only the kind list may be bound, every statement must be a
        declaration, every import must be on the reviewed list) - so the walk adds the
        edges to it rather than a second, weaker opinion on its body.
        """
        out: list[str] = []
        if not imported:
            return out
        for offset, token in _module_statements(blanked):
            excerpt = _statement_excerpt(blanked, offset)
            _, truncated = _statement_window(blanked, offset)
            if token not in _COLLABORATION_MODULE_DECLARATIONS:
                out.append(
                    f"`{path}` runs a statement while it loads, and the collaboration "
                    f"authority links it: `{excerpt}`"
                )
                continue
            if token in _COLLABORATION_MODULE_BINDING_TOKENS:
                out.append(
                    f"`{path}` binds a module-level value whose initializer is "
                    "evaluated while it loads, and the collaboration authority links "
                    f"it: `{excerpt}`"
                )
                continue
            if token == "import":
                # The specifier is read out of the *comment*-blanked text: the
                # string-aware blanking this statement walk runs on has already
                # removed the literal, so every import would read as unopenable.
                statement = _statement_text(commented, offset)
                if not re.match(r"import\s+type\b", statement) and not re.search(
                    r"""\bfrom\s*(['"])\.[^'"]*\1""", statement
                ) and not re.match(r"""import\s*(['"])\.""", statement):
                    out.append(
                        f"`{path}` imports a module the guard cannot open, so whatever "
                        "it runs while loading sits outside every layer: "
                        f"`{excerpt}`"
                    )
                continue
            if token != "export":
                # The whitelist names a *spelling*, so the two contextual keywords on
                # it are read as declarations whatever follows them.  `type(...)` and
                # `interface(...)` are calls, and a call runs while the module loads.
                shape = _COLLABORATION_DECLARATION_SHAPES.get(token)
                if shape is not None and shape.match(
                    _statement_text(commented, offset)
                ) is None:
                    out.append(
                        f"`{path}` starts a statement with the {token} keyword but does "
                        "not declare anything, so it runs while it loads, and the "
                        f"collaboration authority links it: `{excerpt}`"
                    )
                continue
            statement = _statement_text(blanked, offset)
            if re.match(_COLLABORATION_EXPORT_BINDING, statement):
                out.append(
                    f"`{path}` binds a module-level value whose initializer is "
                    "evaluated while it loads, and the collaboration authority links "
                    f"it: `{excerpt}`"
                )
            elif re.match(_COLLABORATION_EXPORT_LOAD_TIME_DECLARATION, statement) or re.match(
                _COLLABORATION_EXPORT_DEFAULT_DECLARATION, statement
            ):
                out.append(
                    f"`{path}` exports a declaration whose body or initializer is "
                    "evaluated while it loads, and the collaboration authority links "
                    f"it: `{excerpt}`"
                )
            elif re.match(_COLLABORATION_EXPORT_DEFAULT, statement):
                out.append(
                    f"`{path}` default-exports, and a reviewed closure member carries "
                    "no default export, so the guard refuses the form rather than "
                    f"judge what it evaluates while it loads: `{excerpt}`"
                )
            elif re.match(_COLLABORATION_EXPORT_ASSIGNMENT, statement):
                out.append(
                    f"`{path}` exports through an assignment, which is evaluated while "
                    f"it loads, and the collaboration authority links it: `{excerpt}`"
                )
            elif (
                re_export := _COLLABORATION_RE_EXPORT.match(
                    _statement_text(commented, offset)
                )
            ) is not None:
                # A relative re-export is an edge the walk follows, so the module on
                # the other end is read and judged there; a package is not, and is
                # refused exactly as the import beside it is.
                if not re_export.group(2).startswith("."):
                    out.append(
                        f"`{path}` re-exports a module the guard cannot open, so "
                        "whatever it runs while loading sits outside every layer: "
                        f"`{excerpt}`"
                    )
            elif re.match(_COLLABORATION_EXPORT_DECLARATION, statement) or (
                re.match(r"export\s*\{", statement)
                and not re.search(r"\bfrom\b", statement)
                # The same rule as the authority's own level: this rung allows a
                # local named export on the strength of the `from` it did not find,
                # so it may only judge a statement it read to the end.  A truncated
                # named list falls through to the refusal beneath.
                and not truncated
            ):
                # The forms a member may carry: a declaration whose body waits to be
                # called, and a local named export.  Both are read by the whitelist
                # above the ladder, and everything else falls to the refusal below.
                pass
            elif truncated and re.match(r"export\s*\{", statement):
                out.append(
                    f"`{path}` exports a named list longer than the guard can read, "
                    "so a `from` clause may sit past the window and evaluate another "
                    "module while loading, and the collaboration authority links it: "
                    f"`{excerpt}`"
                )
            else:
                # The ladder used to end in silence, so anything it did not recognise
                # was accepted: `export*from'./x'` matched neither the patterns nor
                # the edge walk and became a load-time edge outside every layer.  The
                # default is a refusal now, so an unread spelling fails closed.
                out.append(
                    f"`{path}` exports a form the guard cannot read, so the gate "
                    "refuses it rather than judge what it evaluates while it loads, "
                    f"and the collaboration authority links it: `{excerpt}`"
                )
        return out

    def relative_edges(path: str, text: str) -> list[str]:
        edges: list[str] = []
        blanked = _blank_comments(text)
        for offset, token in _module_statements(_blank_comments_and_strings(text)):
            statement = _statement_text(blanked, offset)
            if token == "import":
                if re.match(r"import\s+type\b", statement):
                    continue
                match = re.search(r"\bfrom\s*(['\"])([^'\"]*)\1", statement)
                if match is None:
                    match = re.match(r"\s*import\s*(['\"])([^'\"]*)\1", statement)
            elif token == "export":
                match = _COLLABORATION_RE_EXPORT.match(statement)
            else:
                continue
            if match is not None and match.group(2).startswith("."):
                edges.append(match.group(2))
        for found in re.finditer(r"\bimport\s*\(\s*(['\"])([^'\"]*)\1\s*\)", blanked):
            if found.group(2).startswith("."):
                edges.append(found.group(2))
        return edges

    def read_module(path: str, text: str, imported: bool = True) -> bool:
        """The two rules every closure member gets: segmentable, runs nothing.

        `False` means the module could not be segmented, so it has no statement list
        to trust and the walk must not continue past it.

        The statement list comes off the **string-aware** blanking, not the
        comment-only one.  A module-level literal such as `const OPEN = '{'` left a
        `{` in the text that the character walk pushed and never popped, so every
        statement below it stopped being reported: the whole file went unread while
        the guard still called the closure reviewed.  There is no reason a string
        should be more opaque than a comment, and a template literal's `}` was
        already being read as a statement head, which rejected legal modules.
        """
        unsegmentable = _js_unsegmentable_spans(text)
        if unsegmentable:
            offset, _end, kind, terminated, _crossed = unsegmentable[0]
            if kind == "ambiguous":
                reason = (
                    f"the `/` at offset {offset} follows a `>` that may close a "
                    "type-argument list or compare, and the two readings place the "
                    "statements below it differently"
                )
            else:
                reason = (
                    f"an unterminated {kind} starts at offset {offset}"
                    if not terminated
                    else (
                        f"a {kind} literal starts at offset {offset} and only closes below "
                        "the line it opened on, so it is not a literal"
                    )
                )
            failures.append(
                f"`{path}` cannot be segmented: {reason}, so statements below it are "
                "unread rather than absent"
            )
            return False
        commented = _blank_comments(text)
        failures.extend(
            run_failures(path, _blank_comments_and_strings(text), commented, imported)
        )
        # A dynamic `import()` whose specifier is not a plain string literal is an
        # edge the walk cannot follow: `import('./' + 'deepModule')` reads as no edge
        # at all, so whatever that module runs while loading sits outside the closure
        # while the guard still calls the closure read.  The edge is refused rather
        # than guessed at, on the comment-blanked text so the literal is still there
        # to read.
        for found in re.finditer(r"\bimport\s*\(", commented):
            # The first argument has to be one plain string literal and the call has
            # to end there.  `import('./')` and `import('./' + name)` both *start*
            # with a quote, and only the first is an edge the walk can follow; a
            # literal with a second argument (`import('./x', { with: {} })`, the
            # `with`-attribute spelling) is neither - the closing parenthesis is not
            # where `relative_edges()` looks for it, so the target was read by
            # nothing while this scan called the specifier readable.
            if re.match(r"""\s*(['"])([^'"]*)\1\s*\)""", commented[found.end():]) is None:
                failures.append(
                    f"`{path}` reaches a module through a specifier the guard cannot "
                    "read, so whatever that module runs while loading sits outside "
                    "every layer"
                )
                break
        return True

    def walk(path: str, text: str, remaining: int, imported: bool = True) -> None:
        if len(seen) > _COLLABORATION_IMPORT_CLOSURE_FILES:
            failures.append(
                "the collaboration authority's runtime import closure is larger than "
                f"the guard's reviewed bound ({_COLLABORATION_IMPORT_CLOSURE_FILES} "
                "modules), so the guard can no longer claim to have read it"
            )
            return
        if not read_module(path, text, imported):
            return
        for specifier in relative_edges(path, text):
            resolved = resolver(path, specifier)
            if resolved is None:
                failures.append(
                    "the collaboration authority imports a local module the guard "
                    f"cannot read (`{specifier}` from `{path}`), so whatever it runs "
                    "while loading sits outside every layer"
                )
                continue
            target, target_text = resolved
            if target in seen:
                continue
            seen.add(target)
            failures.extend(
                # The environment ban is a ban on *names*, and a name spelled in a
                # comment or a string literal is not a read of it.  The authority
                # module's own rule already reads its blanked text; reading the raw
                # text here made one of them refuse a module the other accepted - the
                # word `document` in a doc comment was reported as a runtime
                # environment read, and the closure that contains `store.ts` failed
                # on a module that never touches the environment.
                _environment_reference_failures(
                    _blank_comments_and_strings(target_text),
                    f"the imported module `{target}`",
                )
            )
            if remaining > 1:
                walk(target, target_text, remaining - 1)
            else:
                # The module sits exactly at the depth bound.  Stopping the *walk* is
                # not the same as skipping the read.  The walk used to stop here and
                # report "too deep" only when the boundary module still had edges of
                # its own, so a chain that ended exactly at the bound was read by
                # nothing while the guard still claimed to have read it.  The
                # boundary module is read first, and the bound is reported on top.
                read_module(target, target_text)
                if relative_edges(target, target_text):
                    failures.append(
                        "the collaboration authority's runtime import closure is deeper "
                        f"than the {depth} modules the guard reviewed: `{target}` was "
                        "reached but not read"
                    )
    walk(origin, source, depth, imported=False)
    return failures


def collaboration_consumption_failures(host: str) -> list[str]:
    """The flag must stay wired into the region it governs, on the real elements.

    HTML comments and `<style>` bodies are blanked and the `<script setup>` body is
    dropped, so a decoy token parked in any of the three cannot stand in for the
    real binding.  The region slot must also still be a **direct child** of the
    element that carries the flag: a slot that keeps every token but sits inside a
    child component of that element (the real host renders `<CanonicalActionBar>`
    in the same region) fills nothing, so containment in the element interval is
    not the assertion - the innermost enclosing element must *be* the flagged one.

    Presence was still not enough, on three counts.  The flag could sit on an
    element that a literal `v-if="false"`/`v-show="false"` (or an ancestor thereof)
    removes from the tree; the slot could be declared a *second* time, and the
    compiler keeps the last declaration, so an empty later one silently replaces the
    wired one; and the slot could keep its gate while its only child was a
    literal-false panel.  Each kept every token in place and left the guard green
    while the panel never rendered, so the carrier element, the slot count and the
    panel inside the slot are asserted too.  Attributes are read as an attribute
    table (both quote styles, entities decoded) rather than by a double-quoted
    regular expression, matching the page-side checks, so a single-quoted
    `:has-collaboration='hasCollaboration'` is no longer a false reject.
    """
    # The script boundary comes off the shared tag scan: a bare `<script` inside a
    # quoted attribute value before the carrier (`data-note="<script"`) is not a
    # script block, and splitting on the raw substring cut the template short - and
    # the carrier with it - so a file that renders was rejected.
    template = _template_before_script(_template_text(host))
    failures = []
    elements = _element_spans_all(template)
    bindings = [
        value
        for _name, start, tag_end, _end in elements
        for value in _tag_dynamic_values(template[start:tag_end], "has-collaboration")
    ]
    if not bindings:
        failures.append("the host no longer passes the collaboration flag to the region")
    elif any(_condense(value or "") != "hasCollaboration" for value in bindings):
        failures.append("the host passes something other than the collaboration flag to the region")
    bound_regions = {
        (start, end)
        for tag, start, end in _element_spans(template, "ObjectTaskPage")
        if "hasCollaboration" in _tag_dynamic_values(tag, "has-collaboration")
    }
    if not bound_regions:
        failures.append("the collaboration flag is not bound on the object-task region element")
    for tag, start, end in _element_spans(template, "ObjectTaskPage"):
        failures += _dead_gate_failures(
            tag,
            "the object-task element that carries the collaboration flag",
            _COLLABORATION_HOST_TEMPLATE_GATES,
        )
        failures += _ancestor_dead_gate_failures(
            template,
            start,
            end,
            "the object-task element that carries the collaboration flag",
            _COLLABORATION_HOST_TEMPLATE_GATES,
            _COLLABORATION_HOST_ELSE_ELEMENTS,
        )
    slot_declarations = [
        (name, start, tag_end, end)
        for name, start, tag_end, end in elements
        for slot in _slot_names(template[start:tag_end])
        if slot == _COLLABORATION_REGION_SLOT.lstrip("#")
    ]
    for name, start, tag_end, end in elements:
        if _SLOT_NAME_DYNAMIC not in _slot_names(template[start:tag_end]):
            continue
        innermost = _innermost_element(template, start)
        if innermost is None or innermost[1:] not in bound_regions:
            continue
        failures.append(
            "the object-task element declares a slot whose name is computed at runtime, "
            "so the guard cannot prove which slot it declares - and the compiler keeps "
            f"the last declaration (`{_condense(template[start:tag_end])[:120]}`)"
        )
    occurrences = len(slot_declarations)
    if occurrences != 1:
        failures.append(
            "the collaboration region slot must be declared exactly once: "
            f"found {occurrences}, and the compiler keeps the last declaration, so a "
            "second, empty one silently replaces the wired slot"
        )
    collaboration_templates = [
        (start, tag_end, end, template[start:tag_end])
        for name, start, tag_end, end in slot_declarations
        if name == "template"
    ]
    if not collaboration_templates:
        failures.append("the collaboration region template is gone")
    for start, tag_end, end, tag in collaboration_templates:
        if "hasCollaboration" not in [
            _condense(value or "") for value in _tag_values(tag, "v-if")
        ]:
            failures.append("the collaboration region is no longer gated on the flag")
        innermost = _innermost_element(template, start)
        if innermost is None or innermost[0] != "ObjectTaskPage" or innermost[1:] not in bound_regions:
            failures.append(
                "the collaboration region slot is no longer a direct child of the object-task region element"
            )
        panels = [
            (panel_start, panel_tag_end, panel_end)
            for panel_name, panel_start, panel_tag_end, panel_end in elements
            if panel_name == "NativeCollaborationPanel"
            if panel_start >= tag_end and panel_end <= end
        ]
        if not panels:
            failures.append(
                "the collaboration region slot no longer renders the native collaboration panel"
            )
        for panel_start, panel_tag_end, panel_end in panels:
            panel_tag = template[panel_start:panel_tag_end]
            failures += _dead_gate_failures(
                panel_tag,
                "the native collaboration panel inside the region slot",
                _COLLABORATION_HOST_TEMPLATE_GATES,
            )
            failures += _ancestor_dead_gate_failures(
                template,
                panel_start,
                panel_end,
                "the native collaboration panel inside the region slot",
                _COLLABORATION_HOST_TEMPLATE_GATES,
                _COLLABORATION_HOST_ELSE_ELEMENTS,
            )
            panel_gates = [
                _condense(_blank_comments(value or ""))
                for value in _tag_values(panel_tag, "v-if")
            ]
            if panel_gates != [_COLLABORATION_PANEL_GATE]:
                failures.append(
                    "the native collaboration panel inside the region slot is no longer "
                    f"gated on `{_COLLABORATION_PANEL_GATE}`, so the wired slot renders "
                    "nothing"
                )
    return failures


_MAKE_DIRECTIVES = frozenset(
    {
        "ifeq",
        "ifneq",
        "else",
        "endif",
        "ifdef",
        "ifndef",
        "include",
        "-include",
        "sinclude",
        "export",
        "unexport",
        "override",
        "define",
        "endef",
        "vpath",
    }
)


def _rule_name_part(line: str) -> str | None:
    """The target-name portion of a make rule line, or `None` if it is not a rule."""
    index = 0
    while True:
        colon = line.find(":", index)
        if colon == -1:
            return None
        if line[colon + 1:colon + 2] == "=":
            index = colon + 1
            continue
        return line[:colon]


def _variable_named_rule_lines(source: str) -> list[str]:
    """Rule lines whose *target name* is composed with a make variable.

    `$(TARGET):` is invisible to a literal `^target\\s*:` count, so a second
    definition of the collaboration authority target could replace the executable
    proof with `@true` while the guard still reported exactly one definition.
    Assignments, conditionals, includes and recipes are excluded.
    """
    offenders = []
    for line in source.splitlines():
        if not line or line[0].isspace() or line.lstrip().startswith("#"):
            continue
        head = line.split(None, 1)[0]
        if head in _MAKE_DIRECTIVES or head.startswith("."):
            continue
        if re.match(r"^[A-Za-z_][\w.-]*\s*[:?+!]?=", line):
            continue
        name = _rule_name_part(line)
        if name is None:
            continue
        if "$(" in name or "${" in name:
            offenders.append(line.strip())
    return offenders


def _runs_node_on(line: str, outfile: str) -> bool:
    r"""Whether `line` executes exactly `node <outfile>` and nothing else.

    The executable name is anchored: `[^\s#]*node` also matched
    `@/tmp/attacker/fakenode <outfile>`, which runs anything the reviewer never saw.
    """
    text = line.strip()
    if text.startswith("@"):
        text = text[1:]
    parts = text.split()
    if len(parts) != 2:
        return False
    return posixpath.basename(parts[0]) == "node" and parts[1] == outfile


def collaboration_proof_failures(
    makefile: str, other_make_sources: tuple[str, ...] = ()
) -> list[str]:
    """The semantics must stay proven by the executable authority test.

    Text assertions can only bind wiring.  The rule itself (which kinds count, that
    the `||` really OR-s a live authority, that suppression still gates it) is
    proven by executing the real module, so the gate has to keep *running* that
    test: a rule that only requires the path to appear would accept a recipe that
    mentions the test and executes nothing.

    What is asserted is the recipe, not just the presence of a path: the target is
    defined exactly once, the bundler input is the literal path (a same-prefix
    sibling such as `..._test.ts.decoy.ts` was accepted by a substring test), the
    bundler is `esbuild` by basename, the outfile is written by that one line and
    executed by exactly one `node` line after it, and the outfile literal appears in
    no other recipe line - an injected `cp /tmp/evil.mjs <outfile>` or a second
    bundling step into the same outfile used to leave the guard green.

    Two further reach-arounds are excluded: a rule whose *target name* is composed
    with a make variable (`$(TARGET):` is invisible to a literal count, and a second
    definition wins), and any recipe line that expands a make variable at all - the
    reviewed recipe is two literal commands, so `cp /tmp/attacker.mjs $(OUT)` has no
    way to slip past the outfile-literal count.
    """
    failures = []
    make_sources = (makefile,) + tuple(other_make_sources)
    headers = [
        header
        for source in make_sources
        for header in re.findall(
            r"^" + re.escape(_COLLABORATION_AUTHORITY_TEST_TARGET) + r"\s*:",
            source,
            re.M,
        )
    ]
    if not headers:
        failures.append("the executable collaboration authority test target is gone")
    elif len(headers) > 1:
        failures.append(
            "the executable collaboration authority test target is defined more than once"
        )
    else:
        for source in make_sources:
            for line in _variable_named_rule_lines(source):
                failures.append(
                    "a make rule composes its target name with a variable, so the "
                    f"collaboration authority target can be redefined: `{line}`"
                )
        header = re.search(
            r"^" + re.escape(_COLLABORATION_AUTHORITY_TEST_TARGET) + r"\s*:(.*)$",
            makefile,
            re.M,
        )
        assert header is not None
        recipe = []
        for line in makefile[header.end():].splitlines():
            if line.startswith("\t"):
                recipe.append(line)
            elif line.strip() == "" or line.lstrip().startswith("#"):
                continue
            else:
                break
        bundling: list[tuple[str, str]] = []
        for line in recipe:
            if "$(" in line or "${" in line:
                failures.append(
                    "the executable collaboration authority recipe expands a make variable"
                )
                continue
            parts = line.strip().lstrip("@").split()
            if not parts or posixpath.basename(parts[0]) != "esbuild":
                continue
            if _COLLABORATION_AUTHORITY_TEST not in parts:
                continue
            if "--bundle" not in parts or "--platform=node" not in parts:
                continue
            outfile = None
            for part in parts:
                if part.startswith("--outfile=") and len(part) > len("--outfile="):
                    outfile = part[len("--outfile="):]
            if outfile is not None:
                bundling.append((line, outfile))
        if not bundling:
            failures.append("the collaboration authority test is no longer bundled for node execution")
        executed = False
        for line, outfile in bundling:
            mentions = [candidate for candidate in recipe if outfile in candidate]
            executors = [candidate for candidate in recipe if _runs_node_on(candidate, outfile)]
            if len(mentions) != 2:
                failures.append(
                    "the bundled collaboration authority outfile is written or read by another recipe line"
                )
                continue
            if len(executors) != 1:
                failures.append("the bundled collaboration authority test is no longer executed")
                continue
            if recipe.index(executors[0]) < recipe.index(line):
                failures.append("the bundled collaboration authority test is executed before it is bundled")
                continue
            executed = True
        if not executed:
            failures.append("the bundled collaboration authority test is no longer executed")
    if re.search(
        r"^verify\.frontend\.scene_component_bridge\.unit:[^\n]*"
        + re.escape(_COLLABORATION_AUTHORITY_TEST_TARGET),
        makefile,
        re.M,
    ) is None:
        failures.append(
            "the collaboration authority unit gate is no longer a prerequisite of the scene bridge unit gate"
        )
    return failures


_HTML_ENTITIES = {
    "&quot;": "\"",
    "&#34;": "\"",
    "&apos;": "'",
    "&#39;": "'",
    "&lt;": "<",
    "&gt;": ">",
    "&amp;": "&",
}


def _decode_entities(text: str) -> str:
    for entity, character in _HTML_ENTITIES.items():
        text = text.replace(entity, character)
    return text


def _tag_attributes(tag: str) -> list[tuple[str, str | None]]:
    """`(name, decoded value)` for every attribute of a start tag, either quote style.

    A regular expression that only accepts a double-quoted value cannot see a
    single-quoted one, so `:show-collaboration-panel='false'` beside a double-quoted
    decoy left the guard green while Vue compiled the literal.  The tag is therefore
    read as an attribute table, and entity-encoded spellings are decoded first
    because the compiler decodes them too.
    """
    inner = tag[1:].rstrip()
    if inner.endswith("/>"):
        inner = inner[:-2]
    elif inner.endswith(">"):
        inner = inner[:-1]
    name_match = re.match(r"\s*[A-Za-z][\w:.-]*", inner)
    index = name_match.end() if name_match is not None else 0
    attributes: list[tuple[str, str | None]] = []
    while index < len(inner):
        while index < len(inner) and inner[index].isspace():
            index += 1
        if index >= len(inner):
            break
        attribute = re.match(r"[^\s=/>]+", inner[index:])
        if attribute is None:
            index += 1
            continue
        name = attribute.group(0)
        index += len(name)
        while index < len(inner) and inner[index].isspace():
            index += 1
        value: str | None = None
        if index < len(inner) and inner[index] == "=":
            index += 1
            while index < len(inner) and inner[index].isspace():
                index += 1
            if index < len(inner) and inner[index] in ("'", '"'):
                quote = inner[index]
                end = inner.find(quote, index + 1)
                end = len(inner) if end == -1 else end
                value = inner[index + 1:end]
                index = end + 1
            else:
                end = index
                while end < len(inner) and not inner[end].isspace():
                    end += 1
                value = inner[index:end]
                index = end
        attributes.append((name, _decode_entities(value) if value is not None else None))
    return attributes


def _bound_dynamic_values(markup: str, attribute: str) -> list[str | None]:
    """Decoded values of every `:attr=`/`v-bind:attr=` binding in the markup."""
    values: list[str | None] = []
    for kind, _name, start, end, _self_closing in _scan_tags(markup):
        if kind != "open":
            continue
        for name, value in _tag_attributes(markup[start:end]):
            if name in (":" + attribute, "v-bind:" + attribute):
                values.append(value)
    return values


def _tag_dynamic_values(tag: str, attribute: str) -> list[str | None]:
    """Decoded `:attr=`/`v-bind:attr=` values on one start tag."""
    return [
        value
        for name, value in _tag_attributes(tag)
        if name in (":" + attribute, "v-bind:" + attribute)
    ]


# A slot name the template computes at runtime (`#[name]`, `v-slot:[name]`).  The
# guard cannot know which slot it declares, and the compiler keeps the last
# declaration, so it is refused instead of being counted as some other name.
_SLOT_NAME_DYNAMIC = "\0dynamic"


def _slot_names(tag: str) -> list[str]:
    """Every slot name a start tag declares; `#x` and `v-slot:x` are the same slot.

    Counting the literal `#collaboration` text is not the same as counting the slot
    the compiler fills.  `v-slot:collaboration` declares the same slot without
    spelling it that way, so a second, empty declaration still replaced the wired one
    while the guard reported exactly one - and a `{{ '#collaboration' }}` in template
    *text* is not a declaration at all, yet it was counted as one.  A computed name is
    reported as `_SLOT_NAME_DYNAMIC`: `#[collaborationRegionSlot]` declares whatever it
    evaluates to, and a second, empty one still displaces the wired slot.
    """
    names: list[str] = []
    for name, _value in _tag_attributes(tag):
        if name.startswith("#"):
            slot = name[1:]
        elif name.startswith("v-slot:"):
            slot = name[len("v-slot:"):]
        elif name == "v-slot":
            slot = ""
        else:
            continue
        if slot.startswith("[") and slot.endswith("]"):
            names.append(_SLOT_NAME_DYNAMIC)
        else:
            names.append(slot)
    return names


def _tag_values(tag: str, attribute: str) -> list[str | None]:
    """Decoded values of the plain `attr` on one start tag."""
    return [value for name, value in _tag_attributes(tag) if name == attribute]


_LITERAL_FALSY_GATES = frozenset(
    {
        "false",
        "0",
        "null",
        "undefined",
        "void0",
        "!true",
        "!1",
        "!!false",
        "!!0",
        "''",
        '""',
    }
)


def _literal_falsy_gate(value: str | None) -> bool:
    """Whether an attribute value is a literal that can never be truthy.

    Only *literals*.  The real elements carry real predicates - the region element
    is gated on `!preserveAuthoritativeBusinessSections` and the page's driver host
    on `!showCurrentFormFieldConfigScope` - so a check that rejected any `v-if`
    would reject the product.  What it must not accept is a gate that is written as
    a literal, because those are exactly the ones that read as wired while the
    subtree is gone: `v-if="false"` removes it, `v-show="false"` hides it.
    """
    if value is None:
        return False
    return _condense(_strip_wrapping_parens(value)).lower() in _LITERAL_FALSY_GATES


def _dead_gate_failures(
    tag: str,
    subject: str,
    allowed_gates: frozenset[str] = frozenset(),
    allow_bare_else: bool = False,
    allowed_v_for: frozenset[str] = frozenset(),
) -> list[str]:
    """Any gate on `tag` that is not one of the reviewed gates for this element.

    A blacklist of literal-falsy spellings was one enumeration short of the family it
    existed to close: `v-if="hasCollaboration && false"` is not a literal, it is a
    *dead* expression, and it removed the carrier, the slot and the panel alike while
    every token the guard reads stayed exactly where the guard reads it.  Literal
    falsiness is still reported as what it is, but the rule is now the other way
    round - each element on the reviewed path names the gates it may carry, and every
    other `v-if`/`v-else-if`/`v-show` is refused, so a new gate is a review event
    rather than a silent rewrite.  `v-else` is allowed only on the elements the
    reviewed markup already uses it on, because its condition is the negation of a
    sibling gate that is itself registered above.
    """
    failures = []
    for name, value in _tag_attributes(tag):
        if name in ("v-if", "v-else-if"):
            if value is not None and _condense(_strip_wrapping_parens(value)) in allowed_gates:
                continue
            if _literal_falsy_gate(value):
                failures.append(
                    f"{subject} is removed by a literal `{name}` that never evaluates true"
                )
            else:
                failures.append(
                    f"{subject} is gated on `{_condense(value or '')}`, which is not one of "
                    "the reviewed gates for this element, so the guard can no longer prove "
                    "the subtree renders"
                )
        elif name == "v-show":
            if value is not None and _condense(_strip_wrapping_parens(value)) in allowed_gates:
                continue
            failures.append(
                f"{subject} is hidden by a `v-show`, which the reviewed wiring does not "
                "use at all: the subtree renders nothing when the expression is false"
            )
        elif name == "v-else" and not allow_bare_else:
            failures.append(
                f"{subject} renders only inside an unreviewed `v-else` branch, so the "
                "guard cannot prove the branch is reachable"
            )
        elif name == "v-for":
            # `v-for="n in 0"` renders nothing, exactly like `v-if="false"`, and the
            # inventory named only the `v-if`/`v-else-if`/`v-show` spellings - so the
            # carrier, an ancestor and the panel could each be emptied with a
            # directive the check had no opinion about (the compiled template and the
            # SSR output both agreed the panel was absent, and the guard was green).
            # No reviewed element on either path iterates, so the honest inventory is
            # empty and anything else is a review event.
            if value is not None and _condense(_strip_wrapping_parens(value)) in allowed_v_for:
                continue
            failures.append(
                f"{subject} is removed by a `v-for` that the reviewed markup does not "
                "use at all: an iteration over nothing renders the subtree no more "
                "than a false `v-if` does"
            )
    return failures


def _ancestor_dead_gate_failures(
    markup: str,
    start: int,
    end: int,
    subject: str,
    allowed_gates: frozenset[str] = frozenset(),
    else_elements: frozenset[str] = frozenset(),
) -> list[str]:
    """The same gate check for every element that strictly contains `[start, end)`.

    Bounding the check to the element that *carries* the flag is one indirection
    short: a dead gate on any ancestor takes the whole subtree with it, and the
    flagged element keeps every token while nothing renders.
    """
    failures = []
    for name, ancestor_start, tag_end, ancestor_end in _element_spans_all(markup):
        if ancestor_start < start and ancestor_end > end:
            failures += _dead_gate_failures(
                markup[ancestor_start:tag_end],
                f"an ancestor element (`{name}`) of {subject}",
                allowed_gates,
                name in else_elements,
            )
    return failures


def collaboration_page_wiring_failures(page: str) -> list[str]:
    """The page must hand the two runtime facts to the driver host, and only those.

    A whole-file substring check is satisfied by the *other* consumer of the same
    capability (the native canvas keeps `:show-collaboration-panel` for the
    designer scope), and `:suppress-collaboration` had no gate at all, so a literal
    `false` there would have opened a dispatch context up with the guard green.
    The assertion is therefore made on the driver host's own start tag, and every
    dynamic spelling of either prop anywhere in the template must bind the same
    page-side authority.

    Binding the right authority is not the same as rendering: the real start tag
    already carries `v-if="!showCurrentFormFieldConfigScope"`, so the page can be
    shut off at exactly the same element the guard reads - and one level up, by a
    literal-false gate on any ancestor - while both props stay bound.  The host, its
    ancestors, and the props are therefore asserted separately.
    """
    template = _template_text(page)
    # As on the host side, the boundary is the script block the SFC parser sees, not
    # the first raw `<script` substring - which a quoted attribute value or an HTML
    # comment supplies long before the real one.  `template` keeps the script body,
    # which the two script-side assertions below read.
    markup = _template_before_script(template)
    failures = []
    host_tags = _start_tag_spans(markup, "ContractFormDriverHost")
    if not host_tags:
        return ["the contract form page no longer mounts the contract form driver host"]
    for element_name, start, tag_end, end in _element_spans_all(markup):
        if element_name != "ContractFormDriverHost":
            continue
        failures += _dead_gate_failures(
            markup[start:tag_end],
            "the contract form driver host",
            _COLLABORATION_PAGE_TEMPLATE_GATES,
        )
        failures += _ancestor_dead_gate_failures(
            markup,
            start,
            end,
            "the contract form driver host",
            _COLLABORATION_PAGE_TEMPLATE_GATES,
            _COLLABORATION_PAGE_ELSE_ELEMENTS,
        )
    for _start, tag in host_tags:
        attributes = _tag_attributes(tag)
        bound: dict[str, list[str | None]] = {}
        for name, value in attributes:
            bound.setdefault(name, []).append(value)
        if "v-bind" in bound:
            failures.append(
                "the driver host props are no longer bound individually: an object "
                "spread can rebind either collaboration prop"
            )
        for attribute, authority, message in (
            (
                _COLLABORATION_PANEL_ATTRIBUTE,
                _COLLABORATION_PANEL_AUTHORITY,
                "the driver host is no longer given the native collaboration panel capability",
            ),
            (
                _COLLABORATION_SUPPRESSION_ATTRIBUTE,
                _COLLABORATION_SUPPRESSION_AUTHORITY,
                "the driver host is no longer given the dispatch-context collaboration suppression",
            ),
        ):
            if bound.get(":" + attribute) != [authority]:
                failures.append(message)
    for attribute, authority, message in (
        (
            _COLLABORATION_PANEL_ATTRIBUTE,
            _COLLABORATION_PANEL_AUTHORITY,
            "the native collaboration capability is no longer the single page-side authority",
        ),
        (
            _COLLABORATION_SUPPRESSION_ATTRIBUTE,
            _COLLABORATION_SUPPRESSION_AUTHORITY,
            "the collaboration suppression is no longer the dispatch-context authority",
        ),
    ):
        for value in _bound_dynamic_values(markup, attribute):
            if value != authority:
                failures.append(message)
    if not re.search(
        r"const\s+dispatchContextCollaboration\s*=\s*computed\(\s*\(\s*\)\s*=>\s*"
        r"isDispatchContextGovernance\(",
        template,
    ):
        failures.append(
            "the page no longer derives the suppression from the declared dispatch-context governance"
        )
    if "collaborationSuppressed: dispatchContextCollaboration.value" not in template:
        failures.append(
            "the native collaboration panel authority no longer consumes the dispatch-context suppression"
        )
    return failures


def collaboration_authority_failures(
    host: str, module: str, makefile: str, other_make_sources: tuple[str, ...] = ()
) -> list[str]:
    return (
        collaboration_flag_failures(host, module)
        + collaboration_module_scope_failures(module)
        + collaboration_kind_failures(module)
        + collaboration_node_authority_failures(module)
        + collaboration_visibility_rule_failures(module)
        + collaboration_consumption_failures(host)
        + collaboration_proof_failures(makefile, other_make_sources)
    )


_COLLABORATION_MODULE_FLAG_CALL = (
    "resolveCollaborationVisibility({\n"
    "  capability: props.showCollaborationPanel,\n"
    "  suppressed: props.suppressCollaboration,\n"
    "  nodes: props.renderModel?.zones.subordinate,\n"
    "})"
)
_COLLABORATION_MODULE_KINDS = (
    "export const COLLABORATION_SURFACE_KINDS = ['chatter', 'activity'] as const;"
)
_COLLABORATION_MODULE_KIND_BODY = (
    "return (COLLABORATION_SURFACE_KINDS as readonly string[]).includes(\n"
    "    String(kind || '').trim().toLowerCase(),\n"
    "  );"
)
_COLLABORATION_MODULE_NODE_BODY = (
    "return Boolean(nodes?.some((node) => isCollaborationSurfaceKind(node.kind)));"
)
_COLLABORATION_MODULE_RULE_BODY = (
    "return Boolean(input.capability)\n"
    "    || (!input.suppressed && hasCollaborationNode(input.nodes));"
)
_DELEGATION_BLOCK = (
    "() => {\n"
    "  return resolveCollaborationVisibility({\n"
    "    capability: props.showCollaborationPanel,\n"
    "    suppressed: props.suppressCollaboration,\n"
    "    nodes: props.renderModel?.zones.subordinate,\n"
    "  });\n"
    "}"
)
_DELEGATION_BLOCK_WITHOUT_RETURN = _DELEGATION_BLOCK.replace("return ", "")
_COLLABORATION_SHIM_IMPORT = (
    "import {\n"
    "  resolveCollaborationVisibility,\n"
    "} from './collaborationVisibilityShim';\n"
)
# `input['capability']` is three characters shorter after
# `_normalize_bracket_property_access`, so an access anywhere earlier in the file
# used to move every later body window: the recorded fixture keeps it *before* the
# three authorities, where it is legal, ordinary TypeScript.
_COLLABORATION_MODULE_BRACKET_HELPER = (
    "export function readCapability(input: { capability?: unknown }): unknown {\n"
    "  return input['capability'];\n"
    "}\n"
)
# Evaluated while the module loads, which is the one moment neither layer watches:
# the guard reads the three bodies, and the proof's browser replay installs `window`
# only after importing the module.
_COLLABORATION_MODULE_LOAD_TIME_GATE = (
    "if (typeof window !== 'undefined') {\n"
    "  (COLLABORATION_SURFACE_KINDS as unknown as string[]).length = 0;\n"
    "}\n"
)
# A sample that is only used to assert the blanking preserves offsets: it mixes a
# line comment, a block comment, a template literal and bracket property accesses.
_COLLABORATION_OFFSET_SAMPLE = (
    "const a = x['member']; /* c */ const b = \"text\"; // d\n"
    "const c = y[\"other\"]; const d = z[ 'third' ]; const e = `t`;\n"
)


def _collaboration_module(
    kinds: str = _COLLABORATION_MODULE_KINDS,
    kind_body: str = _COLLABORATION_MODULE_KIND_BODY,
    node_body: str = _COLLABORATION_MODULE_NODE_BODY,
    rule_body: str = _COLLABORATION_MODULE_RULE_BODY,
    module_preamble: str = "",
    module_tail: str = "",
) -> str:
    """A minimal runtime VM module carrying the collaboration authority."""
    return (
        "/** Collaboration surface authority. */\n"
        f"{module_preamble}"
        f"{kinds}\n"
        "export function isCollaborationSurfaceKind(kind: unknown): boolean {\n"
        f"  {kind_body}\n"
        "}\n"
        "export function hasCollaborationNode(\n"
        "  nodes: readonly { kind?: unknown }[] | null | undefined,\n"
        "): boolean {\n"
        f"  {node_body}\n"
        "}\n"
        "export function resolveCollaborationVisibility(input: {\n"
        "  capability?: unknown;\n"
        "  suppressed?: boolean;\n"
        "  nodes: readonly { kind?: unknown }[] | null | undefined;\n"
        "}): boolean {\n"
        f"  {rule_body}\n"
        "}\n"
        f"{module_tail}"
    )


def _collaboration_host(
    flag_body: str | None = None,
    region_binding: str = ':has-collaboration="hasCollaboration"',
    region_gate: str = 'v-if="hasCollaboration"',
    region_slot: str = "#collaboration",
    panel_gate: str = 'v-if="collaborationPanelVisible"',
    region_prefix: str = "",
    region_tail: str = "",
    region_suffix: str = "",
    template_tail: str = "",
    script_tail: str = "",
    flag_argument: str | None = None,
    panel_wrapper_open: str = "",
    panel_wrapper_close: str = "",
    carrier_prefix: str = "",
    carrier_suffix: str = "",
    carrier_gate: str = "",
    import_line: str = (
        "import {\n"
        "  isCollaborationSurfaceKind,\n"
        "  resolveCollaborationVisibility,\n"
        "} from './contractRuntimeVm';\n"
    ),
) -> str:
    """A minimal host carrying the delegation and the region wiring.

    The region slot renders the native collaboration panel, because the slot is not
    what the region is for: a slot that keeps its gate while its only child is
    removed renders nothing, and the guard binds the panel's own gate as well.
    """
    # The reviewed flag is the contract-aware predicate, so an unadorned sample
    # carries it verbatim: only the samples that deliberately rewrite the flag
    # pass `flag_body`/`flag_argument`, and those spell the old delegation call.
    if flag_argument is not None:
        argument = flag_argument
    elif flag_body is not None:
        argument = f"() => (\n  {flag_body}\n)"
    else:
        argument = _COLLABORATION_EXPECTED_FLAG
    return (
        "<template>\n"
        f"{carrier_prefix}"
        f"  <ObjectTaskPage {region_binding}{carrier_gate}>\n"
        f"{region_prefix}"
        f"    <template {region_gate} {region_slot}>\n"
        f"      {panel_wrapper_open}<NativeCollaborationPanel {panel_gate} />{panel_wrapper_close}\n"
        f"    </template>\n"
        f"{region_tail}"
        f"{region_suffix}"
        "  </ObjectTaskPage>\n"
        f"{carrier_suffix}"
        f"  {template_tail}\n"
        "</template>\n"
        '<script setup lang="ts">\n'
        f"{import_line}"
        f"const hasCollaboration = computed({argument});\n"
        f"{script_tail}"
        "</script>\n"
        "<style scoped>\n"
        ".sc-form-driver-host { display: block; }\n"
        "</style>\n"
    )


def _collaboration_makefile(wired: bool = True) -> str:
    if not wired:
        return "verify.frontend.other.unit: guard.prod.forbid\n\t@echo other\n"
    return (
        f".PHONY: {_COLLABORATION_AUTHORITY_TEST_TARGET}\n"
        f"{_COLLABORATION_AUTHORITY_TEST_TARGET}: guard.prod.forbid\n"
        f"\t@frontend/apps/web/node_modules/.bin/esbuild {_COLLABORATION_AUTHORITY_TEST}"
        " --bundle --platform=node --format=esm --outfile=/tmp/collaboration.mjs >/dev/null\n"
        "\t@node /tmp/collaboration.mjs\n"
        "verify.frontend.scene_component_bridge.unit: guard.prod.forbid "
        f"{_COLLABORATION_AUTHORITY_TEST_TARGET}\n"
    )


# What a padded-label fixture needs to be a *payload* rather than a syntax error: the
# block is what the label names, the `typeof` guard is the one environment read the
# guard's own name list tolerates, and `break as` is what uses the label - so the
# shape compiles, and the linter's `no-unused-labels` is satisfied.
_COLLABORATION_LABEL_PAYLOAD_TAIL = (
    "{ if (typeof customElements !== 'undefined') { const e = Array.prototype as "
    "unknown as { includes: (v: unknown) => boolean }; e.includes = () => false; } "
    "break as; }\n"
)

_COLLABORATION_SELF_CHECK: tuple[tuple[str, str, str, str, bool], ...] = (
    # accepted: the delegation and the wiring the guard binds
    ("delegated flag and wired region", _collaboration_host(), _collaboration_module(), _collaboration_makefile(), True),
    (
        "reflowed delegation call",
        _collaboration_host(flag_argument=_COLLABORATION_EXPECTED_FLAG_REFLOWED),
        _collaboration_module(),
        _collaboration_makefile(),
        True,
    ),
    (
        "gate spelling with spaces around the equals sign",
        _collaboration_host(region_gate='v-if = "hasCollaboration"'),
        _collaboration_module(),
        _collaboration_makefile(),
        True,
    ),
    (
        "an additional collaboration kind declared",
        _collaboration_host(),
        _collaboration_module(kinds="export const COLLABORATION_SURFACE_KINDS = ['chatter', 'activity', 'note'] as const;"),
        _collaboration_makefile(),
        True,
    ),
    (
        "legacy delegation rewritten as a block whose sole statement is the return",
        _collaboration_host(flag_argument=_DELEGATION_BLOCK),
        _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    (
        "sibling markup after the region slot inside the flag element",
        _collaboration_host(region_tail='    <span class="decoy" />\n'),
        _collaboration_module(),
        _collaboration_makefile(),
        True,
    ),
    (
        "flag delegation spelling the capability as a bracket property access",
        _collaboration_host(flag_argument=_COLLABORATION_EXPECTED_FLAG_BRACKET),
        _collaboration_module(),
        _collaboration_makefile(),
        True,
    ),
    (
        "region slot declared with the `v-slot:` spelling",
        _collaboration_host(region_slot="v-slot:collaboration"),
        _collaboration_module(),
        _collaboration_makefile(),
        True,
    ),
    (
        "an interpolation that merely spells the region slot name",
        _collaboration_host(template_tail="{{ '#collaboration' }}"),
        _collaboration_module(),
        _collaboration_makefile(),
        True,
    ),
    (
        "an import of a reviewed module with a trailing comment naming another one",
        _collaboration_host(),
        _collaboration_module(
            module_preamble="import { normalizeRouteDefault } from './valueUtils';"
            " /* './collaborationPoison' */\n"
        ),
        _collaboration_makefile(),
        True,
    ),
    # rejected: token-preserving rewrites of the real wiring
    (
        "flag re-derived locally instead of delegated",
        _collaboration_host("Boolean(props.showCollaborationPanel) || hasCollaborationNode.value"),
        _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    (
        "delegation call left only in a line comment",
        _collaboration_host(
            "false // resolveCollaborationVisibility({ capability: props.showCollaborationPanel, "
            "suppressed: props.suppressCollaboration, nodes: props.renderModel?.zones.subordinate })"
        ),
        _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    (
        "delegation kept but a local || short-circuits it",
        _collaboration_host(
            "true || resolveCollaborationVisibility({ capability: props.showCollaborationPanel, "
            "suppressed: props.suppressCollaboration, nodes: props.renderModel?.zones.subordinate })"
        ),
        _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    (
        "capability dropped from the delegation",
        _collaboration_host(
            "resolveCollaborationVisibility({ suppressed: props.suppressCollaboration, "
            "nodes: props.renderModel?.zones.subordinate })"
        ),
        _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    (
        "subordinate zone dropped from the delegation",
        _collaboration_host(
            "resolveCollaborationVisibility({ capability: props.showCollaborationPanel, "
            "suppressed: props.suppressCollaboration })"
        ),
        _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    (
        "region binding set to a literal with a comment decoy",
        _collaboration_host(
            region_binding=':has-collaboration="false"',
            template_tail='<!-- <ObjectTaskPage :has-collaboration="hasCollaboration"> -->',
        ),
        _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    (
        "region gate set to a literal with a comment decoy",
        _collaboration_host(
            region_gate='v-if="false"',
            template_tail='<!-- <template v-if="hasCollaboration" #collaboration /> -->',
        ),
        _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    (
        "region binding parked in a style block",
        _collaboration_host(
            region_binding='data-region="collaboration"',
            template_tail='<style scoped>:has-collaboration="hasCollaboration" {}</style>',
        ),
        _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    (
        "region slot renamed with a comment decoy",
        _collaboration_host(
            region_slot="#collaborationSurface",
            region_tail="    <!-- <template v-if=\"hasCollaboration\" #collaboration /> -->\n",
        ),
        _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    (
        "binding moved off the object-task region element",
        _collaboration_host(
            region_binding='data-region="collaboration"',
            template_tail='<section :has-collaboration="hasCollaboration" />',
        ),
        _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    (
        "region slot moved out of the object-task region element",
        _collaboration_host(template_tail='<template v-if="hasCollaboration" #collaboration />'),
        _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    (
        "region binding kept only by a script string decoy",
        _collaboration_host(
            region_binding='data-region="collaboration"',
            script_tail='const decoy = \':has-collaboration="hasCollaboration"\';\n',
        ),
        _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    # rejected: the delegation is kept but its result no longer reaches the flag
    (
        "flag negated while still calling the authority",
        _collaboration_host(f"!{_COLLABORATION_MODULE_FLAG_CALL}"),
        _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    (
        "flag discards the authority result with a comma expression",
        _collaboration_host(f"({_COLLABORATION_MODULE_FLAG_CALL}, false)"),
        _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    (
        "flag short-circuits the authority with a trailing ||",
        _collaboration_host(f"{_COLLABORATION_MODULE_FLAG_CALL} || false"),
        _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    (
        "flag turns the authority into a constant with a ternary",
        _collaboration_host(f"{_COLLABORATION_MODULE_FLAG_CALL} ? false : false"),
        _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    (
        "authority shadowed by a host-local declaration",
        _collaboration_host(
            script_tail="const resolveCollaborationVisibility = () => false;\n",
        ),
        _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    (
        "authority no longer imported into the host",
        _collaboration_host(import_line=""),
        _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    # rejected: the authority redefined underneath the delegation
    (
        "node authority replaced by a constant",
        _collaboration_host(),
        _collaboration_module(node_body="return false;"),
        _collaboration_makefile(),
        False,
    ),
    (
        "node authority switched from existential to universal",
        _collaboration_host(),
        _collaboration_module(node_body="return Boolean(nodes?.every((node) => isCollaborationSurfaceKind(node.kind)));"),
        _collaboration_makefile(),
        False,
    ),
    (
        "node authority no longer asks the kind predicate",
        _collaboration_host(),
        _collaboration_module(node_body="return Boolean(nodes?.some((node) => Boolean(node.kind)));"),
        _collaboration_makefile(),
        False,
    ),
    (
        "declared kinds kept but no longer consumed",
        _collaboration_host(),
        _collaboration_module(kind_body="return false;"),
        _collaboration_makefile(),
        False,
    ),
    (
        "declared kinds emptied",
        _collaboration_host(),
        _collaboration_module(kinds="export const COLLABORATION_SURFACE_KINDS = [] as const;"),
        _collaboration_makefile(),
        False,
    ),
    (
        "a declared collaboration kind dropped",
        _collaboration_host(),
        _collaboration_module(kinds="export const COLLABORATION_SURFACE_KINDS = ['chatter'] as const;"),
        _collaboration_makefile(),
        False,
    ),
    (
        "visibility rule AND-s instead of OR-s",
        _collaboration_host(),
        _collaboration_module(
            rule_body="return Boolean(input.capability)\n"
            "    && (!input.suppressed && hasCollaborationNode(input.nodes));"
        ),
        _collaboration_makefile(),
        False,
    ),
    (
        "visibility rule drops the suppression gate",
        _collaboration_host(),
        _collaboration_module(
            rule_body="return Boolean(input.capability) || hasCollaborationNode(input.nodes);"
        ),
        _collaboration_makefile(),
        False,
    ),
    (
        "visibility rule no longer consults the node authority",
        _collaboration_host(),
        _collaboration_module(
            rule_body="return Boolean(input.capability)\n"
            "    || (!input.suppressed && Boolean(input.nodes));"
        ),
        _collaboration_makefile(),
        False,
    ),
    # rejected: the executable proof unwired from the gate
    (
        "executable authority test no longer run by the gate",
        _collaboration_host(),
        _collaboration_module(),
        _collaboration_makefile(wired=False),
        False,
    ),
    (
        "executable authority test dropped from the aggregate gate",
        _collaboration_host(),
        _collaboration_module(),
        _collaboration_makefile().replace(
            "verify.frontend.scene_component_bridge.unit: guard.prod.forbid "
            + _COLLABORATION_AUTHORITY_TEST_TARGET
            + "\n",
            "",
        ),
        False,
    ),
    (
        "executable authority test no longer bundled and executed",
        _collaboration_host(),
        _collaboration_module(),
        _collaboration_makefile().replace(
            f"\t@frontend/apps/web/node_modules/.bin/esbuild {_COLLABORATION_AUTHORITY_TEST}"
            " --bundle --platform=node --format=esm --outfile=/tmp/collaboration.mjs >/dev/null\n",
            "",
        ),
        False,
    ),
    (
        "executable authority test swapped for a placeholder echo",
        _collaboration_host(),
        _collaboration_module(),
        _collaboration_makefile().replace(
            f"\t@frontend/apps/web/node_modules/.bin/esbuild {_COLLABORATION_AUTHORITY_TEST}"
            " --bundle --platform=node --format=esm --outfile=/tmp/collaboration.mjs >/dev/null\n"
            "\t@node /tmp/collaboration.mjs\n",
            f"\t@echo '{_COLLABORATION_AUTHORITY_TEST} (skipped)'\n",
        ),
        False,
    ),
    (
        "bundled authority test no longer executed",
        _collaboration_host(),
        _collaboration_module(),
        _collaboration_makefile().replace("\t@node /tmp/collaboration.mjs\n", ""),
        False,
    ),
    # rejected: a flag that keeps the delegation but never returns its value
    (
        "flag block body that forgets the return",
        _collaboration_host(flag_argument=_DELEGATION_BLOCK_WITHOUT_RETURN),
        _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    (
        "flag block body with an extra leading statement",
        _collaboration_host(
            flag_argument=(
                "() => {\n  const ignored = true;\n  return "
                + _COLLABORATION_MODULE_FLAG_CALL.replace("\n", "\n  ")
                + ";\n}"
            )
        ),
        _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    # rejected: the delegation is imported from something other than the runtime VM
    (
        "authority imported from a shim module instead of the runtime VM",
        _collaboration_host(import_line=_COLLABORATION_SHIM_IMPORT),
        _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    # rejected: the executable proof is re-pointed, shadowed or wrapped
    (
        "proof target defined a second time with a no-op recipe",
        _collaboration_host(),
        _collaboration_module(),
        _collaboration_makefile()
        + f"\n{_COLLABORATION_AUTHORITY_TEST_TARGET}: guard.prod.forbid\n\t@true\n",
        False,
    ),
    (
        "proof replaced by a same-prefix sibling file",
        _collaboration_host(),
        _collaboration_module(),
        _collaboration_makefile().replace(
            f"esbuild {_COLLABORATION_AUTHORITY_TEST}",
            f"esbuild {_COLLABORATION_AUTHORITY_TEST}.decoy.ts",
        ),
        False,
    ),
    (
        "proof executed through a wrapper whose name merely ends in node",
        _collaboration_host(),
        _collaboration_module(),
        _collaboration_makefile().replace(
            "\t@node /tmp/collaboration.mjs",
            "\t@/tmp/attacker/fakenode /tmp/collaboration.mjs",
        ),
        False,
    ),
    (
        "outfile overwritten between bundling and execution",
        _collaboration_host(),
        _collaboration_module(),
        _collaboration_makefile().replace(
            "\t@node /tmp/collaboration.mjs",
            "\t@cp /tmp/attacker.mjs /tmp/collaboration.mjs\n\t@node /tmp/collaboration.mjs",
        ),
        False,
    ),
    (
        "a second bundling step overwrites the same outfile",
        _collaboration_host(),
        _collaboration_module(),
        _collaboration_makefile().replace(
            "\t@node /tmp/collaboration.mjs",
            f"\t@frontend/apps/web/node_modules/.bin/esbuild {_COLLABORATION_AUTHORITY_TEST}"
            " --bundle --platform=node --format=esm --outfile=/tmp/collaboration.mjs >/dev/null\n"
            "\t@node /tmp/collaboration.mjs",
        ),
        False,
    ),
    # rejected: a rule that is only reached under one runtime environment
    (
        "kind predicate gated on a runtime environment probe",
        _collaboration_host(),
        _collaboration_module(
            kind_body=(
                "if (typeof window !== 'undefined') return false;\n  "
                + _COLLABORATION_MODULE_KIND_BODY
            )
        ),
        _collaboration_makefile(),
        False,
    ),
    (
        "kind predicate parks the constant name in a dead trailing statement",
        _collaboration_host(),
        _collaboration_module(
            kind_body=(
                "return ['chatter', 'activity', 'ghost'].includes(\n"
                "    String(kind || '').trim().toLowerCase(),\n"
                "  ); void COLLABORATION_SURFACE_KINDS;"
            )
        ),
        _collaboration_makefile(),
        False,
    ),
    (
        "node authority gated on a runtime environment probe",
        _collaboration_host(),
        _collaboration_module(
            node_body=(
                "if (typeof window !== 'undefined') return false;\n  "
                + _COLLABORATION_MODULE_NODE_BODY
            )
        ),
        _collaboration_makefile(),
        False,
    ),
    (
        "visibility rule gated on a runtime environment probe",
        _collaboration_host(),
        _collaboration_module(
            rule_body=(
                "if (typeof window !== 'undefined') return false;\n  "
                + _COLLABORATION_MODULE_RULE_BODY
            )
        ),
        _collaboration_makefile(),
        False,
    ),
    (
        "visibility rule switches on the environment inside its return",
        _collaboration_host(),
        _collaboration_module(
            rule_body=(
                "return typeof window === 'undefined'\n"
                "    ? Boolean(input.capability)"
                " || (!input.suppressed && hasCollaborationNode(input.nodes))\n"
                "    : false;"
            )
        ),
        _collaboration_makefile(),
        False,
    ),
    # rejected: the region slot keeps every token but no longer fills the slot
    (
        "region slot nested under an unclosed child of the flag element",
        _collaboration_host(
            region_prefix="    <CanonicalActionBar>\n",
        ),
        _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    (
        "region slot nested in a child component of the flag element",
        _collaboration_host(
            region_prefix="    <CanonicalActionBar>\n",
            region_suffix="    </CanonicalActionBar>\n",
        ),
        _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    (
        "region slot moved out with a tag-name decoy inside an attribute string",
        _collaboration_host(
            region_tail="    <span :data-decoy=\"'<ObjectTaskPage>'\" />\n",
            template_tail='<template v-if="hasCollaboration" #collaboration />',
        ),
        _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    # rejected: gated on one runtime environment in spellings a probe blacklist
    # missed - each kept every token, killed the region in the browser and stayed
    # invisible to the node-run proof
    (
        "visibility rule gated on a bracket-property environment read",
        _collaboration_host(),
        _collaboration_module(
            rule_body=(
                "return globalThis['window'] !== undefined\n"
                "    ? false\n"
                "    : (Boolean(input.capability)"
                " || (!input.suppressed && hasCollaborationNode(input.nodes)));"
            )
        ),
        _collaboration_makefile(),
        False,
    ),
    (
        "visibility rule gated on a parenthesized typeof probe",
        _collaboration_host(),
        _collaboration_module(
            rule_body=(
                "return typeof(window) !== 'undefined'\n"
                "    ? false\n"
                "    : (Boolean(input.capability)"
                " || (!input.suppressed && hasCollaborationNode(input.nodes)));"
            )
        ),
        _collaboration_makefile(),
        False,
    ),
    (
        "visibility rule gated on a membership probe",
        _collaboration_host(),
        _collaboration_module(
            rule_body=(
                "return ('window' in globalThis)\n"
                "    ? false\n"
                "    : (Boolean(input.capability)"
                " || (!input.suppressed && hasCollaborationNode(input.nodes)));"
            )
        ),
        _collaboration_makefile(),
        False,
    ),
    (
        "visibility rule gated on the `self` binding",
        _collaboration_host(),
        _collaboration_module(
            rule_body=(
                "return typeof(self) !== 'undefined'\n"
                "    ? false\n"
                "    : (Boolean(input.capability)"
                " || (!input.suppressed && hasCollaborationNode(input.nodes)));"
            )
        ),
        _collaboration_makefile(),
        False,
    ),
    (
        "visibility rule whose single return is followed by an ASI-separated statement",
        _collaboration_host(),
        _collaboration_module(
            rule_body=(
                "return false\n    (Boolean(input.capability)"
                " || (!input.suppressed && hasCollaborationNode(input.nodes)));"
            )
        ),
        _collaboration_makefile(),
        False,
    ),
    (
        "compliant predicate body parked in a string literal",
        _collaboration_host(),
        _collaboration_module(
            kinds=(
                _COLLABORATION_MODULE_KINDS
                + "\n"
                + 'const _decoy = "function isCollaborationSurfaceKind(kind: unknown) {'
                " return (COLLABORATION_SURFACE_KINDS as readonly string[]).includes("
                "String(kind || '').trim().toLowerCase()); }\";"
            ),
            kind_body=(
                "return globalThis['window'] !== undefined\n"
                "    ? false\n"
                "    : (COLLABORATION_SURFACE_KINDS as readonly string[]).includes(\n"
                "    String(kind || '').trim().toLowerCase(),\n"
                "  );"
            ),
        ),
        _collaboration_makefile(),
        False,
    ),
    # rejected: the authority is imported, but not under the name that is called
    (
        "authority imported under another local name",
        _collaboration_host(
            import_line=(
                "import {\n"
                "  isCollaborationSurfaceKind,\n"
                "  resolveCollaborationVisibility as _rcv,\n"
                "} from './contractRuntimeVm';\n"
            )
        ),
        _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    (
        "authority destructured out of a namespace import",
        _collaboration_host(
            import_line=(
                "import { isCollaborationSurfaceKind } from './contractRuntimeVm';\n"
                "import * as _vm from './collaborationVisibilityShim';\n"
                "const { resolveCollaborationVisibility } = _vm;\n"
            )
        ),
        _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    # rejected: a decoy close inside an interpolation used to close the element
    (
        "region slot closed by a decoy inside an interpolation",
        _collaboration_host(
            region_prefix=(
                "    <CanonicalActionBar>\n"
                "      {{ '' /* '</CanonicalActionBar>' */ }}\n"
            ),
            region_tail="    </CanonicalActionBar>\n",
        ),
        _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    # rejected: reach-arounds at the make layer
    (
        "executable target redefined through a make variable",
        _collaboration_host(),
        _collaboration_module(),
        _collaboration_makefile()
        + "\nB6T = "
        + _COLLABORATION_AUTHORITY_TEST_TARGET
        + "\n$(B6T):\n\t@true\n",
        False,
    ),
    (
        "executable recipe overwrites the outfile through a make variable",
        _collaboration_host(),
        _collaboration_module(),
        _collaboration_makefile().replace(
            "\t@node /tmp/collaboration.mjs",
            "\t@cp /tmp/attacker.mjs $(B6_OUT)\n\t@node /tmp/collaboration.mjs",
        ),
        False,
    ),
    # accepted: shapes a purely textual scanner used to reject
    (
        "an interpolation before the region slot",
        _collaboration_host(region_prefix="    {{ count < 3 ? 'many' : 'few' }}\n"),
        _collaboration_module(),
        _collaboration_makefile(),
        True,
    ),
    (
        "an HTML void element before the region slot",
        _collaboration_host(region_prefix='    <br>\n    <img src="/x.png">\n'),
        _collaboration_module(),
        _collaboration_makefile(),
        True,
    ),
    (
        "the region flag bound with a single-quoted attribute",
        _collaboration_host(region_binding=":has-collaboration='hasCollaboration'"),
        _collaboration_module(),
        _collaboration_makefile(),
        True,
    ),
    (
        "a bracket property access earlier in the module",
        _collaboration_host(),
        _COLLABORATION_MODULE_BRACKET_HELPER + _collaboration_module(),
        _collaboration_makefile(),
        True,
    ),
    # rejected: the region's carrier, its slot count, and the panel inside the slot
    (
        "region carrier removed by a literal v-if",
        _collaboration_host(region_binding=':has-collaboration="hasCollaboration" v-if="false"'),
        _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    (
        "region carrier hidden by a literal v-show",
        _collaboration_host(region_binding=':has-collaboration="hasCollaboration" v-show="false"'),
        _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    (
        "an ancestor of the region carrier removed by a literal v-if",
        _collaboration_host(
            carrier_prefix='  <div v-if="false">\n', carrier_suffix="  </div>\n"
        ),
        _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    (
        "an unclosed child wrapper inside the region carrier",
        _collaboration_host(region_prefix='  <div v-if="false">\n')
        .replace("  </ObjectTaskPage>\n", "  </ObjectTaskPage>\n  </div>\n", 1),
        _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    (
        "the region slot declared a second time, empty",
        _collaboration_host(region_tail='    <template v-if="hasCollaboration" #collaboration />\n'),
        _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    (
        "the collaboration panel removed by a literal v-if",
        _collaboration_host(panel_gate='v-if="false"'),
        _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    (
        "the collaboration panel hidden by a literal v-show",
        _collaboration_host(panel_gate='v-show="false"'),
        _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    # rejected: the module itself, outside the three authorities
    (
        "module gated on the runtime environment while it loads",
        _collaboration_host(),
        _COLLABORATION_MODULE_LOAD_TIME_GATE + _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    (
        "module runs a statement outside its declared authorities",
        _collaboration_host(),
        "Object.defineProperty(Array.prototype, 'includes', { value: () => false });\n"
        + _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    (
        "module imports another file for its side effects only",
        _collaboration_host(),
        "import './collaborationPoison';\n" + _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    (
        "module re-exports another file",
        _collaboration_host(),
        "export { installCollaborationPoison } from './collaborationPoison';\n"
        + _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    (
        "authority body gated on the runtime environment",
        _collaboration_host(),
        _collaboration_module(
            rule_body=(
                "return typeof document === 'undefined'\n"
                "    ? Boolean(input.capability) || (!input.suppressed && hasCollaborationNode(input.nodes))\n"
                "    : false;"
            )
        ),
        _collaboration_makefile(),
        False,
    ),
    (
        "module binds a value with a load-time expression",
        _collaboration_host(),
        "export const degraded = ['chatter'].concat(['activity']);\n"
        + _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    (
        "module binds an environment-gated value at load time",
        _collaboration_host(),
        "export const degraded = typeof screen !== 'undefined';\n" + _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    (
        "module-level binding is not exported",
        _collaboration_host(),
        "const degraded = () => false;\n" + _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    (
        "the kind list is built by an expression instead of string literals",
        _collaboration_host(),
        _collaboration_module(
            kinds=(
                "export const COLLABORATION_SURFACE_KINDS = "
                "[typeof screen !== 'undefined' ? 'chatter' : 'note', 'activity'] as const;"
            )
        ),
        _collaboration_makefile(),
        False,
    ),
    (
        "module declares a resource binding that runs at load time",
        _collaboration_host(),
        "using degraded = openCollaborationPoison();\n" + _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    (
        "module declares an enum whose member runs at load time",
        _collaboration_host(),
        "enum Degraded { A = Number('1') }\n" + _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    (
        "module exports a class whose static initializer runs while it loads",
        _collaboration_host(),
        _collaboration_module(
            module_tail=(
                "\nexport class Degraded { static x = typeof screen !== 'undefined' "
                "? (COLLABORATION_SURFACE_KINDS as unknown as string[]).splice(0) : 0; }\n"
            )
        ),
        _collaboration_makefile(),
        False,
    ),
    (
        "module exports an enum whose member runs while it loads",
        _collaboration_host(),
        _collaboration_module(
            module_tail=(
                "\nexport enum Degraded { A = (typeof screen !== 'undefined' "
                "? (COLLABORATION_SURFACE_KINDS as unknown as string[]).splice(0).length : 0) }\n"
            )
        ),
        _collaboration_makefile(),
        False,
    ),
    (
        "module imports a binding from an unreviewed module",
        _collaboration_host(),
        "import { installCollaborationPoison } from './collaborationPoison';\n"
        + _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    (
        "a line-comment marker inside a string literal shields a same-line gate",
        _collaboration_host(),
        _collaboration_module(
            module_tail=(
                '\nexport type CollaborationPoison = "a//b"; '
                "if (typeof window !== 'undefined') "
                "{ (COLLABORATION_SURFACE_KINDS as unknown as string[]).length = 0 }\n"
            )
        ),
        _collaboration_makefile(),
        False,
    ),
    (
        "an unterminated block comment inside a string literal shields the rest",
        _collaboration_host(),
        _collaboration_module(
            module_tail=(
                "\nexport type CollaborationPoison = 'x/*y';\n"
                "if (typeof screen !== 'undefined') "
                "{ (COLLABORATION_SURFACE_KINDS as unknown as string[]).length = 0 }\n"
            )
        ),
        _collaboration_makefile(),
        False,
    ),
    (
        "a bare abstract class with a load-time static initializer",
        _collaboration_host(),
        "abstract class Degraded { static x = typeof screen !== 'undefined' "
        "? (COLLABORATION_SURFACE_KINDS as unknown as string[]).splice(0) : 0; }\n"
        + _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    (
        "the region slot declared a second time as a `v-slot:`",
        _collaboration_host(
            region_suffix='    <template v-if="hasCollaboration" v-slot:collaboration />\n'
        ),
        _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    (
        "the panel moved under a literal-false ancestor inside the slot",
        _collaboration_host(
            panel_wrapper_open='<div v-if="false">',
            panel_wrapper_close="</div>",
        ),
        _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    (
        "a regular expression literal's quote hides the gate after it",
        _collaboration_host(),
        _collaboration_module(
            module_tail=(
                "\nfunction poison(): RegExp { return /[']/g }\n"
                "if (typeof screen !== 'undefined') "
                "{ (COLLABORATION_SURFACE_KINDS as unknown as string[]).length = 0 }\n"
            )
        ),
        _collaboration_makefile(),
        False,
    ),
    (
        "an unterminated block comment hides the gate after it",
        _collaboration_host(),
        _collaboration_module(
            module_tail=(
                "\n/* unterminated\n"
                "if (typeof screen !== 'undefined') "
                "{ (COLLABORATION_SURFACE_KINDS as unknown as string[]).length = 0 }\n"
            )
        ),
        _collaboration_makefile(),
        False,
    ),
    (
        "a runtime import whose trailing comment names a reviewed module",
        _collaboration_host(),
        _collaboration_module(
            module_preamble=(
                "import { installCollaborationPoison } from './collaborationPoison'"
                " /* './valueUtils' */;\n"
            )
        ),
        _collaboration_makefile(),
        False,
    ),
    (
        "a runtime import with text after its specifier",
        _collaboration_host(),
        _collaboration_module(
            module_preamble=(
                "import { normalizeRouteDefault } from './valueUtils' './collaborationPoison';\n"
            )
        ),
        _collaboration_makefile(),
        False,
    ),
    (
        "a region slot whose name the template computes at runtime",
        _collaboration_host(
            region_suffix='    <template v-if="hasCollaboration" #[collaborationRegionSlot] />\n'
        ),
        _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    (
        "a region slot declared a second time with a computed `v-slot:` name",
        _collaboration_host(
            region_suffix='    <template v-if="hasCollaboration" v-slot:[collaborationRegionSlot] />\n'
        ),
        _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    (
        "the panel gated on the negation of the region flag",
        _collaboration_host(panel_gate='v-if="!hasCollaboration"'),
        _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    (
        "the panel gated on a literal that is not the panel authority",
        _collaboration_host(panel_gate='v-if="NaN"'),
        _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    (
        "a top-level block that runs while the module loads",
        _collaboration_host(),
        _collaboration_module(module_tail="\n{\n  poisonSurfaceKinds();\n}\n"),
        _collaboration_makefile(),
        False,
    ),
    (
        "a top-level call expression that runs while the module loads",
        _collaboration_host(),
        _collaboration_module(
            module_tail=(
                "\n(() => {\n"
                "  (COLLABORATION_SURFACE_KINDS as unknown as string[]).length = 0;\n"
                "})();\n"
            )
        ),
        _collaboration_makefile(),
        False,
    ),
    (
        "a top-level statement whose predecessor needs no semicolon",
        _collaboration_host(),
        _collaboration_module(
            module_tail=(
                "\nexport type CollaborationPoison = typeof COLLABORATION_SURFACE_KINDS\n"
                "if (typeof window !== 'undefined') "
                "{ (COLLABORATION_SURFACE_KINDS as unknown as string[]).length = 0 }\n"
            )
        ),
        _collaboration_makefile(),
        False,
    ),
    (
        "a top-level parenthesised assignment",
        _collaboration_host(),
        _collaboration_module(
            module_tail=(
                "\n(Array.prototype as unknown as { includes: unknown }).includes = "
                "() => true;\n"
            )
        ),
        _collaboration_makefile(),
        False,
    ),
    (
        "the carrier gated on the reviewed expression",
        _collaboration_host(carrier_gate=" v-if=\"!preserveAuthoritativeBusinessSections\""),
        _collaboration_module(),
        _collaboration_makefile(),
        True,
    ),
    (
        "the carrier gated on a dead expression that is not a literal",
        _collaboration_host(
            carrier_gate=' v-if="!preserveAuthoritativeBusinessSections && false"'
        ),
        _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    (
        "the carrier hidden rather than removed",
        _collaboration_host(carrier_gate=' v-show="hasCollaboration && false"'),
        _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    (
        "an ancestor of the carrier gated on a dead expression",
        _collaboration_host(
            carrier_prefix='<div v-if="hasCollaboration && false">\n',
            carrier_suffix="</div>\n",
        ),
        _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    (
        "an ancestor of the carrier gated on the reviewed flag",
        _collaboration_host(
            carrier_prefix='<div v-if="hasCollaboration">\n',
            carrier_suffix="</div>\n",
        ),
        _collaboration_module(),
        _collaboration_makefile(),
        True,
    ),
    (
        "an ancestor of the carrier that hides it in an unreviewed v-else",
        _collaboration_host(
            carrier_prefix="<div v-else>\n",
            carrier_suffix="</div>\n",
        ),
        _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    (
        "an apostrophe in the template copy",
        _collaboration_host(region_prefix="    <span>don't</span>\n"),
        _collaboration_module(),
        _collaboration_makefile(),
        True,
    ),
    (
        "a script block closed in a different case",
        _collaboration_host().replace("</script>", "</SCRIPT>"),
        _collaboration_module(),
        _collaboration_makefile(),
        True,
    ),
    (
        "the carrier iterated over nothing",
        _collaboration_host(carrier_gate=' v-for="n in 0" :key="n"'),
        _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    (
        "an ancestor of the carrier iterated over nothing",
        _collaboration_host(
            carrier_prefix='<div v-for="n in []" :key="n">\n',
            carrier_suffix="</div>\n",
        ),
        _collaboration_module(),
        _collaboration_makefile(),
        False,
    ),
    (
        "a call parked behind a declaration at the module's top level",
        _collaboration_host(),
        _collaboration_module(
            module_tail="function gate(): boolean { return true }\n!gate()\n"
        ),
        _collaboration_makefile(),
        False,
    ),
    (
        "a template literal statement at the module's top level",
        _collaboration_host(),
        _collaboration_module(module_tail="`${String(1)}`;\n"),
        _collaboration_makefile(),
        False,
    ),
    (
        "a statement after a U+2028 line terminator",
        _collaboration_host(),
        _collaboration_module(
            module_tail="export type CollabKind = typeof COLLABORATION_SURFACE_KINDS\u2028"
            "if (typeof screen !== 'undefined') { (COLLABORATION_SURFACE_KINDS as unknown as string[]).splice(0); }\n"
        ),
        _collaboration_makefile(),
        False,
    ),
    # The next two shapes are what the script boundary has to survive.  A bare
    # `<script` in a quoted attribute value is not a script block, and reading it as
    # one cut the template short - carrier and region with it - so a file that renders
    # was rejected for wiring it still has.
    (
        "a quoted attribute value before the carrier that merely spells a script block",
        _collaboration_host(carrier_prefix='  <div data-note="<script"></div>\n'),
        _collaboration_module(),
        _collaboration_makefile(),
        True,
    ),
    (
        "an HTML comment before the carrier that merely spells a script block",
        _collaboration_host(carrier_prefix="  <!-- <script> -->\n"),
        _collaboration_module(),
        _collaboration_makefile(),
        True,
    ),
    # A declaration's `}` ends its statement, so what follows it is a statement of its
    # own.  These four spellings ran while the module loaded and were read as a
    # continuation of the declaration above them, because the tail table still held
    # `+`, `-` and `/` as "still the same statement".
    (
        "a call parked behind a declaration with a unary plus",
        _collaboration_host(),
        _collaboration_module(module_tail="export function probe(): void {}\n+gate();\n"),
        _collaboration_makefile(),
        False,
    ),
    (
        "a call parked behind a declaration with a unary minus",
        _collaboration_host(),
        _collaboration_module(module_tail="export function probe(): void {}\n-gate();\n"),
        _collaboration_makefile(),
        False,
    ),
    (
        "a regular expression test parked behind a declaration",
        _collaboration_host(),
        _collaboration_module(
            module_tail="export function probe(): void {}\n/^collect-/.test('');\n"
        ),
        _collaboration_makefile(),
        False,
    ),
    (
        "a call parked behind a declaration with a word that may not start a statement",
        _collaboration_host(),
        _collaboration_module(module_tail="export function probe(): void {}\nfrom('x');\n"),
        _collaboration_makefile(),
        False,
    ),
    (
        "a call parked behind a declaration with the `satisfies` spelling",
        _collaboration_host(),
        _collaboration_module(
            module_tail="export function probe(): void {}\nsatisfies('x');\n"
        ),
        _collaboration_makefile(),
        False,
    ),
    (
        "a call parked behind a declaration with the `as` spelling",
        _collaboration_host(),
        _collaboration_module(module_tail="export function probe(): void {}\nas('x');\n"),
        _collaboration_makefile(),
        False,
    ),
    # ... while the three characters that genuinely cannot begin a statement - the
    # ones a type expression carries its `}` on into - still continue it.
    (
        "a type literal whose `}` is continued into a closing angle bracket",
        _collaboration_host(),
        _collaboration_module(
            module_tail="export type Shape = Record<string, { a: string }>;\n"
        ),
        _collaboration_makefile(),
        True,
    ),
    (
        "an authority whose contextual keyword starts a call",
        _collaboration_host(),
        _collaboration_module(
            module_tail="type(typeof customElements !== 'undefined' && "
            "(Array.prototype.includes = () => false));\n"
        ),
        _collaboration_makefile(),
        False,
    ),
    (
        "an authority that declares a type and a function",
        _collaboration_host(),
        _collaboration_module(
            module_tail="type Label = string;\n"
            "function read<T>(value: T): T { return value; }\n"
        ),
        _collaboration_makefile(),
        True,
    ),
    (
        "an authority whose generic declaration nests an angle bracket",
        _collaboration_host(),
        _collaboration_module(
            module_tail="type Box<N> = { value: N };\n"
            "type Wrapped<T extends Box<number>> = T;\n"
            "function read<T extends Box<number>>(value: T): T { return value; }\n"
            "export type { Wrapped };\n"
        ),
        _collaboration_makefile(),
        True,
    ),
    (
        "an authority that re-exports a module without the space",
        _collaboration_host(),
        _collaboration_module(module_tail="export*from'./collaborationProbe';\n"),
        _collaboration_makefile(),
        False,
    ),
    # The `}` of a `type` alias is not a closed declaration head - a type expression
    # really does carry it on into `>`, `|` and `&` - so which words may follow it is
    # decided by the *statement's own head*.  Read as continuations everywhere, `from`,
    # `as`, `satisfies`, `is`, `extends` and `implements` glued the next statement on to
    # the alias: `type gN3 = { a: number }` followed by a line
    # `from: { (Array.prototype as any).includes = () => true }` read as ONE statement,
    # the shape rule matched its head, and the label's block ran while the module
    # loaded - skipped in the gate's node run, live in the browser.  The first two
    # fixtures pin the glue, and the two after them pin that the head table did not
    # simply ban the words: a `type` header broken before its `extends` clause is one
    # statement, while `extends:` after the same alias is a *label* and not a clause.
    (
        "an authority whose type alias is followed by a `from` label",
        _collaboration_host(),
        _collaboration_module(
            module_tail="type gN3 = { a: number }\n"
            "from: { (Array.prototype as any).includes = () => true }\n"
        ),
        _collaboration_makefile(),
        False,
    ),
    (
        "an authority whose exported type alias is followed by a `from` label",
        _collaboration_host(),
        _collaboration_module(
            module_tail="export type gM4 = number\n"
            "from: { (Array.prototype as any).includes = () => true }\n"
        ),
        _collaboration_makefile(),
        False,
    ),
    (
        "an authority whose type alias is followed by a `from` call",
        _collaboration_host(),
        _collaboration_module(
            module_tail="type gN6 = { a: number }\nfrom('./collaborationProbe')\n"
        ),
        _collaboration_makefile(),
        False,
    ),
    (
        "an authority whose type alias is followed by an `extends` label",
        _collaboration_host(),
        _collaboration_module(
            module_tail="type gA3 = { a: number }\n"
            "extends: { (Array.prototype as any).includes = () => true }\n"
        ),
        _collaboration_makefile(),
        False,
    ),
    (
        "an authority whose exported type header is carried on to its `extends` clause",
        _collaboration_host(),
        _collaboration_module(module_tail="export type gR<T> = T\n  extends string ? 1 : 2\n"),
        _collaboration_makefile(),
        True,
    ),
    # The other half of the same rule: the export ladder allows a local named export
    # on the strength of the `from` it did *not* find, so it may only judge a list it
    # read to the end.  `export { a000, ... } from './x'` puts the clause past the
    # window, reads as a local export, and the far end runs its load-time code inside
    # the gate with the edge never followed.
    (
        "an authority whose exported name list is longer than the guard can read",
        _collaboration_host(),
        _collaboration_module(module_tail=_COLLABORATION_UNREADABLE_RE_EXPORT),
        _collaboration_makefile(),
        False,
    ),
    # The label test read a fixed sixteen-character window, so sixteen blanks of any
    # kind pushed the `:` out of it.  The word then read as a continuation, the
    # statement below was glued on to the export above, and the export ladder - which
    # only ever matched the head - passed it while the label's block ran as the module
    # loaded: skipped in the gate's node run, live in the browser, green in both.  Each
    # fixture below pads with a different character, and every one of them is the same
    # sixteen blanks to the walk: the tab, the no-break space and the byte-order mark
    # are whitespace to the lexer, the zero-width space is read by nothing at all, and
    # a comment is blanked before the walk is handed the text.  The fifteen-space
    # fixture is the control - refused before this rule and after it, by the other half
    # of the same ladder.
    (
        "an authority whose label is padded with sixteen spaces",
        _collaboration_host(),
        _collaboration_module(
            module_tail=(
                "export {}\nas" + " " * 16 + ": " + _COLLABORATION_LABEL_PAYLOAD_TAIL
            )
        ),
        _collaboration_makefile(),
        False,
    ),
    (
        "an authority whose label is padded with fifteen spaces",
        _collaboration_host(),
        _collaboration_module(
            module_tail=(
                "export {}\nas" + " " * 15 + ": " + _COLLABORATION_LABEL_PAYLOAD_TAIL
            )
        ),
        _collaboration_makefile(),
        False,
    ),
    (
        "an authority whose label is padded with sixteen tabs",
        _collaboration_host(),
        _collaboration_module(
            module_tail=(
                "export {}\nas" + "\t" * 16 + ": " + _COLLABORATION_LABEL_PAYLOAD_TAIL
            )
        ),
        _collaboration_makefile(),
        False,
    ),
    (
        "an authority whose label is padded with sixteen no-break spaces",
        _collaboration_host(),
        _collaboration_module(
            module_tail=(
                "export {}\nas" + "\u00a0" * 16 + ": " + _COLLABORATION_LABEL_PAYLOAD_TAIL
            )
        ),
        _collaboration_makefile(),
        False,
    ),
    (
        "an authority whose label is padded with sixteen zero-width spaces",
        _collaboration_host(),
        _collaboration_module(
            module_tail=(
                "export {}\nas" + "\u200b" * 16 + ": " + _COLLABORATION_LABEL_PAYLOAD_TAIL
            )
        ),
        _collaboration_makefile(),
        False,
    ),
    (
        "an authority whose label is padded with a two-hundred character comment",
        _collaboration_host(),
        _collaboration_module(
            module_tail=(
                "export {}\nas/*" + "x" * 200 + "*/: " + _COLLABORATION_LABEL_PAYLOAD_TAIL
            )
        ),
        _collaboration_makefile(),
        False,
    ),
    # The other half of the same defeat, and the reason the label test is not the whole
    # rule: the walk decided that a line could not end a statement from the *last
    # character it could still see*, and blanking a literal took that character away.
    # `export type gS7 = 'x'` left the `=` in charge of the newline, `_can_end_statement()`
    # said no, and the line below was absorbed into the alias - the shape rule matched
    # the alias' head and the assignment ran while the module loaded.  A type-argument
    # list ends the same way and used to be read the same way, because `>` could not end
    # a statement either; the `;` fixture is the control that was always refused.
    (
        "an authority whose literal type alias is followed by a bare expression",
        _collaboration_host(),
        _collaboration_module(
            module_tail=(
                "export type gS7 = 'x'\n"
                "(Array.prototype as any).includes = () => true\n"
            )
        ),
        _collaboration_makefile(),
        False,
    ),
    (
        "an authority whose type-argument alias is followed by a bare expression",
        _collaboration_host(),
        _collaboration_module(
            module_tail=(
                "export type gS8 = Record<string, number>\n"
                "(Array.prototype as any).includes = () => true\n"
            )
        ),
        _collaboration_makefile(),
        False,
    ),
    # A block is a statement too, and `{` at the head of a line was never reported:
    # the walk pushed the bracket, and everything inside it - including the whole
    # block - stopped being a statement the guard could see.  A `{` that is a
    # declaration body still continues the declaration, which the `closed_head` test
    # decides, but `export type gS8b = Record<string, number>` is a complete statement
    # and the block below it runs while the module loads.
    (
        "an authority whose type-argument alias is followed by a block statement",
        _collaboration_host(),
        _collaboration_module(
            module_tail=(
                "export type gS8b = Record<string, number>\n"
                "{ (Array.prototype as any).includes = () => true }\n"
            )
        ),
        _collaboration_makefile(),
        False,
    ),
    # A statement does not have to begin with a name, and the absorbed line does not
    # have to begin with a bracket: a regular expression, a template literal and a
    # number are statements too, and each of them used to be read as part of the
    # statement above it and then reported by nothing at all.
    (
        "an authority whose literal type alias is followed by a regular expression guard",
        _collaboration_host(),
        _collaboration_module(
            module_tail=(
                "export type gS7b = 'x'\n/^collect-/.test(String(1)) && 1\n"
            )
        ),
        _collaboration_makefile(),
        False,
    ),
    (
        "an authority whose semicolon type alias is followed by a bare expression",
        _collaboration_host(),
        _collaboration_module(
            module_tail=(
                "export type gS4 = 'x';\n"
                "(Array.prototype as any).includes = () => true\n"
            )
        ),
        _collaboration_makefile(),
        False,
    ),
    # Registered over-strictness, pinned so that it cannot change silently.  A `>` and
    # a closing quote now end a statement - that is what closed the absorption channel
    # above - and the cost is the mirror image: a type that legitimately continues on
    # the next line is cut in two, and the second half then reads as a top-level
    # statement that is not a declaration.  An array type, an indexed access and a
    # labelled statement after a type alias are all legal TypeScript that this round
    # started refusing.  The direction is fail-closed and it reaches no reviewed module
    # (the real-tree probe is green), so it is registered rather than re-opened: making
    # `[` continue a statement is the very channel this round closed.
    (
        "an authority whose array type alias continues on the next line (registered over-strictness)",
        _collaboration_host(),
        _collaboration_module(
            module_tail=(
                "export type gS9 = Record<string, number>\n"
                "  [];\n"
            )
        ),
        _collaboration_makefile(),
        False,
    ),
    (
        "an authority whose indexed access alias continues on the next line (registered over-strictness)",
        _collaboration_host(),
        _collaboration_module(
            module_tail=(
                "export type gS10 = Record<'a', number>\n"
                "  ['a'];\n"
            )
        ),
        _collaboration_makefile(),
        False,
    ),
    (
        "an authority whose type alias is followed by a labelled statement (registered over-strictness)",
        _collaboration_host(),
        _collaboration_module(
            module_tail=(
                "export type gS11 = Record<string, number>\n"
                "  postfix: 1;\n"
            )
        ),
        _collaboration_makefile(),
        False,
    ),
    # `export function* gen` broken before its type-parameter list is a declaration head
    # like any other: the `*` marks the declaration a generator, it does not name a
    # second subject, and the token after `function` is the one name the head carries.
    # The round-19 shape test counted the mark as that second name and read the second
    # line as a statement that begins with `<` - a refusal, not a reading - while real
    # `tsc 5.9.3` and `esbuild 0.21.5` both compile the second line as the declaration's
    # type-parameter list.  The round-20 shape test steps the mark over.
    (
        "an authority whose generator head continues before its type parameters",
        _collaboration_host(),
        _collaboration_module(
            module_tail=(
                "export function* gen\n"
                "<T>(): Iterable<T> {}\n"
            )
        ),
        _collaboration_makefile(),
        True,
    ),
    (
        "an authority whose async generator head continues before its type parameters",
        _collaboration_host(),
        _collaboration_module(
            module_tail=(
                "export async function* stream\n"
                "<T>(values: readonly T[]): AsyncGenerator<T> {\n"
                "  for (const value of values) { yield value; }\n"
                "}\n"
            )
        ),
        _collaboration_makefile(),
        True,
    ),
    (
        "an authority whose local generator head continues before its type parameters",
        _collaboration_host(),
        _collaboration_module(
            module_tail=(
                "function* walk\n"
                "<T>(values: readonly T[]): Generator<T> {\n"
                "  for (const value of values) { yield value; }\n"
                "}\n"
            )
        ),
        _collaboration_makefile(),
        True,
    ),
    # The head test reads the name the declaration carries, and a name is not required to
    # be spelled in ASCII: `export function \u540d` broken before `<T>` is a head that has
    # named its subject, and the walk's own ASCII-only start rule (which keeps a statement
    # that opens with a non-ASCII name reportable *as* that name) is deliberately left
    # alone - only the head shape test reads the other half of the lexer's start rule.
    (
        "an authority whose declaration name is not spelled in ASCII",
        _collaboration_host(),
        _collaboration_module(
            module_tail=(
                "export function \u540d\n"
                "<T>(value: T): T { return value; }\n"
            )
        ),
        _collaboration_makefile(),
        True,
    ),
    # Registered over-strictness, pinned so that it cannot change silently.  A `/`
    # directly after a `>` cannot be placed by the walk: read as a comparison the `/`
    # opens a literal, read as the close of a type-argument list it divides, and the two
    # readings pair the quotes below it differently, so one of them hides a statement the
    # other reads.  The cost is the mirror image: `(a as any) > /x/.test(b)` is a legal
    # comparison - `tsc 5.9.3` and `esbuild 0.21.5` both take it - whose literal the walk
    # refuses to read.  Reading every `>`-preceded `/` as a literal instead is the
    # narrowing that was weighed and left: it is the reading the poison above needs
    # hidden, and nothing in the walk separates the two cases (`(n as any) > /[']/...`
    # and the legal `(a as any) > /[']/.test(b)` share their whole window).  So the
    # refusal stays, registered, rather than re-opened cheaply.  The crossed shape
    # `a < b > /x/.test('y')` is refused by the same rule and does not compile, so that
    # part of the rule costs nothing.
    (
        "an authority whose comparison takes a regular expression on its right (registered over-strictness)",
        _collaboration_host(),
        _collaboration_module(
            module_tail=(
                "export function cmp(a: unknown, b: string): boolean {\n"
                "  return (a as any) > /x/.test(b);\n"
                "}\n"
            )
        ),
        _collaboration_makefile(),
        False,
    ),

    # The blanks the walk steps over are the lexer's (`_js_is_blank()`), not this
    # interpreter's: `str.isspace()` is false for `U+FEFF` while the TypeScript lexer
    # reads it as whitespace, so padding the `>` with one left the `/` without its
    # ambiguous span and the poison below passed the whole guard - the same bytes with
    # no padding were refused.  A one-character bypass, closed by the blank reading and
    # pinned here so it cannot come back silently.
    (
        "an authority whose comparison is padded before its regular expression with the byte-order mark",
        _collaboration_host(),
        _collaboration_module(
            module_tail=(
                "export function padEq(n: number) { return (n as any) > \ufeff/[']/.test(String(n)); } ; "
                "(Array.prototype as any).includes = () => false; // '\n"
            )
        ),
        _collaboration_makefile(),
        False,
    ),

    # A continuation word the lexer is *extending* is not the keyword, and the colon
    # after it is a label's.  `extends\u0301:` is one name - the combining acute accent
    # is an identifier-continue character to the TypeScript lexer and only ASCII to the
    # word reader - so the walk read the keyword `extends`, which really does continue a
    # `type` header, and glued the label's block into the alias above it: the block ran
    # while the module loaded in the browser while the guard reported one alias.  The
    # same holds for every combining mark and for the `Other_ID_Continue` punctuation
    # marks, which is what the wider `_js_identifier_continue()` is for.
    (
        "an authority whose alias is followed by a combining-mark label",
        _collaboration_host(),
        _collaboration_module(
            module_tail=(
                "export type gL1 = (x: number) => void\n"
                "extends\u0301: { (Array.prototype as any).includes = () => false; }\n"
            )
        ),
        _collaboration_makefile(),
        False,
    ),
    # A line that opens with `<` is not infix.  `export type gB = number` followed by
    # `<unknown>(() => { ... })();` is legal TypeScript - `number` takes no type
    # arguments, so the alias ends there and the angle-bracket assertion runs while the
    # module loads - and `esbuild 0.21.5` emits the call.  The tail table carried `<`
    # into the statement above it, so the assertion was never reported and the poisoned
    # `Array.prototype.includes` it installs loaded in the browser.  `<` is decided by
    # what the statement above it still is: a head with nothing but its type-parameter
    # list left to write, or anything else.
    (
        "an authority whose alias is followed by a legacy angle-bracket type assertion",
        _collaboration_host(),
        _collaboration_module(
            module_tail=(
                "export type gL2 = number\n"
                "<unknown>(() => { (Array.prototype as any).includes = () => false; })();\n"
            )
        ),
        _collaboration_makefile(),
        False,
    ),
    # The other side of the same question, verified against the real parser rather than
    # read off the guard: `export type A = B` followed by `<C>[];` is legal, and the
    # second line is a statement of its own - `[];` reaches the emitted output, so the
    # assertion is what the module runs.  A `<` after a head that already has its type
    # is therefore not a continuation, and neither is one after a completed type.
    (
        "an authority whose alias is followed by an asserted array literal",
        _collaboration_host(),
        _collaboration_module(
            module_tail=(
                "export type gL10 = B\n"
                "<C>[];\n"
            )
        ),
        _collaboration_makefile(),
        False,
    ),
    (
        "an authority whose completed alias is followed by a type-argument list",
        _collaboration_host(),
        _collaboration_module(
            module_tail=(
                "export type gL11 = Record\n"
                "  <string, number>;\n"
            )
        ),
        _collaboration_makefile(),
        False,
    ),
    # And the three legal continuations, which the same test has to keep: a declaration
    # head whose type-parameter list really is the next thing it writes.  `esbuild
    # 0.21.5` and `tsc 5.9.3` both compile all three across the line break.
    (
        "an authority whose function head continues before its type parameters",
        _collaboration_host(),
        _collaboration_module(
            module_tail=(
                "export function gL6\n"
                "<T>(value: T): T { return value; }\n"
            )
        ),
        _collaboration_makefile(),
        True,
    ),
    (
        "an authority whose interface head continues before its type parameters",
        _collaboration_host(),
        _collaboration_module(
            module_tail=(
                "export interface gL8\n"
                "<T> { value: T; }\n"
            )
        ),
        _collaboration_makefile(),
        True,
    ),
    (
        "an authority whose type alias head continues before its type parameters",
        _collaboration_host(),
        _collaboration_module(
            module_tail=(
                "export type gL9\n"
                "<T> = T;\n"
            )
        ),
        _collaboration_makefile(),
        True,
    ),
    # The other half of the same coin: the regular expressions those payloads hide
    # behind are read as operands, so a module that legitimately holds one - an arrow
    # body, the head of a `for`, and the division after a call - is still read as the
    # declaration it is.  `Math.round(value) / 2` is the spelling the reviewed
    # `valueUtils.ts` uses, and a `)` that treated every parenthesis as a statement head
    # would have read that slash as a literal.
    (
        "an authority whose arrow body holds a character-class regular expression",
        _collaboration_host(),
        _collaboration_module(
            module_tail=(
                "export function gL3(value: string): boolean {\n"
                "  const matches = (text: string): boolean => /[']/.test(text);\n"
                "  return matches(value);\n"
                "}\n"
            )
        ),
        _collaboration_makefile(),
        True,
    ),
    (
        "an authority whose loop head holds a character-class regular expression",
        _collaboration_host(),
        _collaboration_module(
            module_tail=(
                "export function gL4(list: string[]): number {\n"
                "  let total = 0;\n"
                "  for (const item of list) /[']/.test(item) && (total += 1);\n"
                "  return total;\n"
                "}\n"
            )
        ),
        _collaboration_makefile(),
        True,
    ),
    (
        "an authority whose division follows a call",
        _collaboration_host(),
        _collaboration_module(
            module_tail=(
                "export function gL5(value: number): number {\n"
                "  return Math.round(value) / 2;\n"
                "}\n"
            )
        ),
        _collaboration_makefile(),
        True,
    ),
    # The head test reads the *shape* of the statement, not its last two words: a name
    # that happens to equal a declaration keyword (`export type type = ...`, or a
    # property named `type`/`namespace`/`enum` inside the alias's type literal) is not
    # the keyword, and the alias above such an assertion has already been given a type.
    # Reading the last two words let exactly that spelling read as "still waiting for
    # `<T>`", so `<unknown>...();` glued into the alias and ran while the module loaded.
    (
        "an authority whose alias name equals a declaration keyword is followed by an angle-bracket assertion",
        _collaboration_host(),
        _collaboration_module(
            module_tail=(
                "export type type = number\n"
                "<unknown>(() => { (Array.prototype as any).includes = () => false; })();\n"
            )
        ),
        _collaboration_makefile(),
        False,
    ),
    (
        "an authority whose alias body names a property like a declaration keyword",
        _collaboration_host(),
        _collaboration_module(
            module_tail=(
                "export type gL13 = { type: string }\n"
                "<unknown>Object.defineProperty(Array.prototype, 'includes', "
                "{ value: () => false });\n"
            )
        ),
        _collaboration_makefile(),
        False,
    ),
    # The lexer continues an identifier with the connector punctuation and with the
    # four symbols the derived `Other_ID_*` properties add, and the walk has to as well:
    # `extends\u203f:` read as the keyword `extends` followed by something else glued
    # the label's block into the alias above it, exactly as `extends\u0301` did.
    (
        "an authority whose alias is followed by a connector-punctuation label",
        _collaboration_host(),
        _collaboration_module(
            module_tail=(
                "export type gL14 = (x: number) => void\n"
                "extends\u203f: { (Array.prototype as any).includes = () => false; }\n"
            )
        ),
        _collaboration_makefile(),
        False,
    ),
    (
        "an authority whose alias is followed by a symbol-mark label",
        _collaboration_host(),
        _collaboration_module(
            module_tail=(
                "export type gL15 = (x: number) => void\n"
                "extends\u30fb: { (Array.prototype as any).includes = () => false; }\n"
            )
        ),
        _collaboration_makefile(),
        False,
    ),
    # TypeScript puts no boundary between an `import`/`export` head and its clause, so
    # the clause may begin on the next line.  The walk ended the statement at the line
    # break instead - `{` is not a continuation character - and the import's specifier
    # was then read out of a window that stopped at `import`, so a legal import was
    # refused as a side-effect-only import and a legal `export\n  { read }` was refused
    # as a form the guard cannot read.
    (
        "an authority whose import clause begins on the next line",
        _collaboration_host(),
        _collaboration_module(
            module_preamble="import\n  { read } from './valueUtils';\n"
        ),
        _collaboration_makefile(),
        True,
    ),
    (
        "an authority whose export clause begins on the next line",
        _collaboration_host(),
        _collaboration_module(
            module_tail="import { read } from './valueUtils';\nexport\n  { read };\n"
        ),
        _collaboration_makefile(),
        True,
    ),
    # `export function pad(n: number) { return (n as any) > /[']/.test(String(n)); }
    # ; (Array.prototype as any).includes = () => false; // '` - **one line**, so the
    # quote in the character class opens a *string* that closes on the quote in the
    # trailing comment without ever crossing a raw newline (the `crossed` rule cannot
    # see it), the poisoned assignment sits inside that phantom span, and the walk read
    # the statement list as if it were not there.  Read as a comparison the `/` opens a
    # literal; read as a type-argument close it divides and the assignment is code.  The
    # guard refuses the shape rather than reading it one way.
    (
        "an authority whose comparison is followed by an unplaceable `/`",
        _collaboration_host(),
        _collaboration_module(
            module_tail=(
                "export function padEq(n: number) { return (n as any) > /[']/.test(String(n)); } ; "
                "(Array.prototype as any).includes = () => false; // '\n"
            )
        ),
        _collaboration_makefile(),
        False,
    ),
    (
        "an authority whose environment probe is followed by an unplaceable `/`",
        _collaboration_host(),
        _collaboration_module(
            module_tail=(
                "export function probeEq() { return (0 as any) > /[']/.test(String(screen)) "
                "&& typeof window !== 'undefined' && false; } ; "
                "(Array.prototype as any).includes = () => false; // '\n"
            )
        ),
        _collaboration_makefile(),
        False,
    ),
    # The same phantom string through `<`, which cannot end an expression: the `/`
    # after it opens a literal in every reading of the grammar, so no refusal is
    # needed and the poisoned statement after the class is read as the statement it is.
    (
        "an authority whose `<` is followed by a character-class literal",
        _collaboration_host(),
        _collaboration_module(
            module_tail=(
                "export function padLt(n: number) { return (n as any) < /[']/.test(String(n)); } ; "
                "(Array.prototype as any).includes = () => false; // '\n"
            )
        ),
        _collaboration_makefile(),
        False,
    ),
    # The control: a real division whose numerator ends in `)` and whose divisor is an
    # identifier.  Nothing here is ambiguous, and refusing it would make the guard
    # unusable on the one spelling it exists to allow.
    (
        "an authority whose division follows a rounded call",
        _collaboration_host(),
        _collaboration_module(
            module_tail=(
                "export function halfRounded(value: number, factor: number) {\n"
                "  return Math.round(value) / factor;\n"
                "}\n"
            )
        ),
        _collaboration_makefile(),
        True,
    ),
)


def _collaboration_page(
    host_attributes: str = (
        ':show-collaboration-panel="showNativeCollaborationPanel"\n'
        '      :suppress-collaboration="dispatchContextCollaboration"'
    ),
    extra_markup: str = "",
    outer_open: str = "",
    outer_close: str = "",
    derived_suppression: str = "computed(() => isDispatchContextGovernance(scope))",
    panel_consumption: str = "collaborationSuppressed: dispatchContextCollaboration.value",
) -> str:
    """A minimal contract form page carrying the driver host wiring."""
    return (
        "<template>\n"
        f"{outer_open}"
        "  <div>\n"
        "    <ContractFormDriverHost\n"
        "      actions-in-header\n"
        f"      {host_attributes}\n"
        '      @save="saveRecord()"\n'
        "    />\n"
        f"{extra_markup}"
        "  </div>\n"
        f"{outer_close}"
        "</template>\n"
        '<script setup lang="ts">\n'
        f"const dispatchContextCollaboration = {derived_suppression};\n"
        "const showNativeCollaborationPanel = computed(() => nativeCollaborationPanelAuthority({\n"
        f"  {panel_consumption},\n"
        "}));\n"
        "</script>\n"
        "<style scoped>\n"
        ".sc-form-page { display: block; }\n"
        "</style>\n"
    )


_COLLABORATION_PAGE_SELF_CHECK: tuple[tuple[str, str, bool], ...] = (
    ("canonical page wiring", _collaboration_page(), True),
    (
        "another element binds the same page-side authorities",
        _collaboration_page(
            extra_markup=(
                "  <ContractFormNativeCanvas\n"
                '    :show-collaboration-panel="showNativeCollaborationPanel"\n'
                '    :suppress-collaboration="dispatchContextCollaboration"\n'
                "  />\n"
            )
        ),
        True,
    ),
    # rejected: a single-quoted literal the compiler honours, hidden behind a
    # double-quoted decoy on the same start tag
    (
        "panel capability replaced by a single-quoted literal beside a decoy",
        _collaboration_page(
            host_attributes=(
                ":show-collaboration-panel='false'\n"
                '      :show-collaboration-panel="showNativeCollaborationPanel"\n'
                '      :suppress-collaboration="dispatchContextCollaboration"'
            )
        ),
        False,
    ),
    (
        "suppression replaced by a single-quoted literal beside a decoy",
        _collaboration_page(
            host_attributes=(
                ':show-collaboration-panel="showNativeCollaborationPanel"\n'
                ":suppress-collaboration='false'\n"
                '      :suppress-collaboration="dispatchContextCollaboration"'
            )
        ),
        False,
    ),
    (
        "driver host props replaced by an object spread",
        _collaboration_page(host_attributes='v-bind="collabAttrs"'),
        False,
    ),
    (
        "panel capability bound to a literal",
        _collaboration_page(
            host_attributes=(
                ':show-collaboration-panel="false"\n'
                '      :suppress-collaboration="dispatchContextCollaboration"'
            )
        ),
        False,
    ),
    (
        "another element reuses the prop for a different value",
        _collaboration_page(
            extra_markup=(
                "  <ContractFormNativeCanvas\n"
                '    :show-collaboration-panel="designerScopeFlag"\n'
                "  />\n"
            )
        ),
        False,
    ),
    (
        "suppression no longer derives from the dispatch-context governance",
        _collaboration_page(derived_suppression="ref(false)"),
        False,
    ),
    (
        "panel authority no longer consumes the derived suppression",
        _collaboration_page(panel_consumption="collaborationSuppressed: false"),
        False,
    ),
    (
        "page no longer mounts the driver host",
        _collaboration_page().replace("ContractFormDriverHost", "ContractFormLegacyCanvas"),
        False,
    ),
    # rejected: the two authorities stay bound while the host cannot render
    (
        "driver host removed by a literal v-if",
        _collaboration_page().replace(
            "    <ContractFormDriverHost\n",
            '    <ContractFormDriverHost v-if="false"\n',
            1,
        ),
        False,
    ),
    (
        "driver host hidden by a literal v-show",
        _collaboration_page().replace(
            "    <ContractFormDriverHost\n",
            '    <ContractFormDriverHost v-show="false"\n',
            1,
        ),
        False,
    ),
    (
        "an ancestor of the driver host removed by a literal v-if",
        _collaboration_page().replace("  <div>\n", '  <div v-if="false">\n', 1),
        False,
    ),
    (
        "the driver host iterated over nothing",
        _collaboration_page().replace(
            "    <ContractFormDriverHost\n",
            '    <ContractFormDriverHost v-for="n in 0" :key="n"\n',
            1,
        ),
        False,
    ),
    (
        "the driver host gated on a dead expression that is not a literal",
        _collaboration_page(
            host_attributes=(
                ':show-collaboration-panel="showNativeCollaborationPanel"\n'
                '      :suppress-collaboration="dispatchContextCollaboration"\n'
                '      v-if="!showCurrentFormFieldConfigScope && false"'
            )
        ),
        False,
    ),
    (
        "the driver host gated on the reviewed page scope",
        _collaboration_page(
            host_attributes=(
                ':show-collaboration-panel="showNativeCollaborationPanel"\n'
                '      :suppress-collaboration="dispatchContextCollaboration"\n'
                '      v-if="!showCurrentFormFieldConfigScope"'
            )
        ),
        True,
    ),
    (
        "the reviewed page section around the driver host",
        _collaboration_page(
            outer_open=(
                "  <section\n"
                "    v-if=\"pageSectionEnabled('details_fallback', true)"
                " && pageSectionTagIs('details_fallback', 'section')\"\n"
                "  >\n"
            ),
            outer_close="  </section>\n",
        ),
        True,
    ),
    (
        "the reviewed v-else branch around the driver host",
        _collaboration_page(outer_open="  <ScCard v-else>\n", outer_close="  </ScCard>\n"),
        True,
    ),
    (
        "the v-else branch turned into a dead v-else-if",
        _collaboration_page(
            outer_open='  <ScCard v-else-if="false">\n',
            outer_close="  </ScCard>\n",
        ),
        False,
    ),
    # The page check reads the markup before the *real* `<script` block, and the
    # driver host sits before it.  A bare `<script` inside a quoted attribute value
    # is not that block: splitting on the raw substring cut the page at the decoy and
    # reported a host that the page still mounts, which is a false reject on
    # ordinary markup.
    (
        "a quoted attribute value that merely spells a script block",
        _collaboration_page(outer_open='  <div data-note="<script"></div>\n'),
        True,
    ),
    (
        "an HTML comment that merely spells a script block",
        _collaboration_page(outer_open="  <!-- <script> -->\n"),
        True,
    ),
)


_COLLABORATION_IMPORT_CLOSURE_ORIGIN = _collaboration_module(
    module_preamble="import { normalizeRouteDefault } from './valueUtils';\n"
)
_COLLABORATION_IMPORT_CLOSURE_SELF_CHECK: tuple[
    tuple[str, dict[str, tuple[str, str]], str, bool], ...
] = (
    (
        "an environment-blind reviewed import target",
        {"./valueUtils": ("pages/valueUtils.ts", "export function read(v: unknown) { return v; }\n")},
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        True,
    ),
    (
        "a reviewed import target whose generator head continues before its type parameters",
        {
            "./valueUtils": (
                "pages/valueUtils.ts",
                "export function* walk\n"
                "<T>(values: readonly T[]): Generator<T> {\n"
                "  for (const value of values) { yield value; }\n"
                "}\n",
            )
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        True,
    ),
    (
        "a reviewed import target whose declaration name is not spelled in ASCII",
        {
            "./valueUtils": (
                "pages/valueUtils.ts",
                "export function \u540d\n<T>(value: T): T { return value; }\n",
            )
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        True,
    ),
    (
        "a reviewed import target whose comparison takes a regular expression on its right (registered over-strictness)",
        {
            "./valueUtils": (
                "pages/valueUtils.ts",
                "export function cmp(a: unknown, b: string): boolean {\n"
                "  return (a as any) > /x/.test(b);\n"
                "}\n",
            )
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        False,
    ),

    (
        "a reviewed import target whose comparison is padded before its regular expression with the byte-order mark",
        {
            "./valueUtils": (
                "pages/valueUtils.ts",
                "export function padEq(n: number) { return (n as any) > \ufeff/[']/.test(String(n)); } ; "
                "(Array.prototype as any).includes = () => false; // '\n",
            )
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        False,
    ),
    (
        "a reviewed import target that probes the environment",
        {
            "./valueUtils": (
                "pages/valueUtils.ts",
                "export function dead() { return typeof window !== 'undefined'; }\n",
            )
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        False,
    ),
    (
        "a module the reviewed import target pulls in that probes the environment",
        {
            "./valueUtils": (
                "pages/valueUtils.ts",
                "import { read } from './fieldUtils';\nexport function value() { return read(); }\n",
            ),
            "./fieldUtils": (
                "pages/fieldUtils.ts",
                "export function read() { return globalThis; }\n",
            ),
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        False,
    ),
    (
        "a reviewed import target the guard cannot read",
        {"./valueUtils": ("pages/valueUtils.ts", "")},
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN.replace(
            "from './valueUtils'", "from './missingModule'"
        ),
        False,
    ),
    (
        "a reviewed import target whose blanking hides the rest of the file",
        {
            "./valueUtils": (
                "pages/valueUtils.ts",
                "/* unterminated\nexport const read = () => 1;\n",
            )
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        False,
    ),
    (
        "a type-only import the compiler erases",
        {
            "./valueUtils": (
                "pages/valueUtils.ts",
                "import type { Shape } from './shapeTypes';\nexport type { Shape };\n",
            )
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        True,
    ),
    (
        "a reviewed import target whose type alias is followed by a `from` label",
        {
            "./valueUtils": (
                "pages/valueUtils.ts",
                "type gN3 = { a: number }\n"
                "from: { (Array.prototype as any).includes = () => true }\n",
            )
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        False,
    ),
    (
        "a reviewed import target whose interface header breaks before its `extends`",
        {
            "./valueUtils": (
                "pages/valueUtils.ts",
                "export interface gShape\n"
                "  extends Record<string, number> {}\n"
                "export function read(): number { return 1; }\n",
            )
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        True,
    ),
    (
        "a reviewed import target whose exported name list the guard can read",
        {
            "./valueUtils": (
                "pages/valueUtils.ts",
                _COLLABORATION_READABLE_RE_EXPORT,
            ),
            "./collaborationProbe": (
                "pages/collaborationProbe.ts",
                _COLLABORATION_READABLE_RE_EXPORT_TARGET,
            ),
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        True,
    ),
    (
        "a reviewed import target whose exported name list is longer than the read",
        {
            "./valueUtils": (
                "pages/valueUtils.ts",
                _COLLABORATION_UNREADABLE_RE_EXPORT,
            ),
            "./collaborationProbe": (
                "pages/collaborationProbe.ts",
                "export function probe(): number { return 1; }\n",
            ),
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        False,
    ),
    (
        "a reviewed import target that only declares at its own level",
        {
            "./valueUtils": (
                "pages/valueUtils.ts",
                "import { read } from './fieldUtils';\nexport function value() { return read(); }\n",
            ),
            "./fieldUtils": ("pages/fieldUtils.ts", "export function read() { return 1; }\n"),
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        True,
    ),
    (
        "a reviewed import target that runs a statement while it loads",
        {
            "./valueUtils": (
                "pages/valueUtils.ts",
                "if (typeof screen !== 'undefined') { (Array.prototype as any).includes = () => false; }\n"
                "export function read() { return 1; }\n",
            )
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        False,
    ),
    (
        "a re-export edge to a module that probes the environment",
        {
            "./valueUtils": (
                "pages/valueUtils.ts",
                "export { deep } from './deepModule';\nexport function read() { return 1; }\n",
            ),
            "./deepModule": (
                "pages/deepModule.ts",
                "export function deep() { return typeof window !== 'undefined'; }\n",
            ),
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        False,
    ),
    (
        "a dynamic import edge to a module that probes the environment",
        {
            "./valueUtils": (
                "pages/valueUtils.ts",
                "export function load() { return import('./deepModule'); }\n",
            ),
            "./deepModule": (
                "pages/deepModule.ts",
                "export function deep() { return typeof window !== 'undefined'; }\n",
            ),
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        False,
    ),
    (
        "a closure deeper than the reviewed bound",
        {
            "./valueUtils": ("pages/m0.ts", "export { v1 } from './m1';\n"),
            "./m1": ("pages/m1.ts", "export { v2 } from './m2';\n"),
            "./m2": ("pages/m2.ts", "export { v3 } from './m3';\n"),
            "./m3": ("pages/m3.ts", "export { v4 } from './m4';\n"),
            "./m4": ("pages/m4.ts", "export { v5 } from './m5';\n"),
            "./m5": ("pages/m5.ts", "export { v6 } from './m6';\n"),
            "./m6": ("pages/m6.ts", "export { v7 } from './m7';\n"),
            "./m7": ("pages/m7.ts", "export { v8 } from './m8';\n"),
            "./m8": ("pages/m8.ts", "export function v8() { return 1; }\n"),
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        False,
    ),
    # A module-level string literal used to blind the walk to everything below it: the
    # `{` in `'{'` was pushed by the character walk and never popped, so the statement
    # after the literal was never reported while the module still ran it on load.
    (
        "a reviewed import target whose string literal makes the next statement invisible",
        {
            "./valueUtils": (
                "pages/valueUtils.ts",
                "type OPEN_BRACE_HINT = '{';\n"
                "(Array.prototype as any).includes = () => false;\n",
            )
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        False,
    ),
    # ... while a template literal's `}` was read as a statement head, so a legal
    # module was refused.
    (
        "a reviewed import target whose template literal interpolates",
        {
            "./valueUtils": (
                "pages/valueUtils.ts",
                "type LABEL = `p-${1}`;\n",
            )
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        True,
    ),
    # The walk stops at the depth bound, but stopping the walk is not skipping the
    # read: the module sitting exactly on the bound was read by nothing, so a
    # statement at that depth ran while the guard called the closure reviewed.
    (
        "a module exactly at the reviewed depth bound that runs a statement",
        {
            "./valueUtils": ("pages/m0.ts", "export { v1 } from './m1';\n"),
            "./m1": ("pages/m1.ts", "export { v2 } from './m2';\n"),
            "./m2": ("pages/m2.ts", "export { v3 } from './m3';\n"),
            "./m3": ("pages/m3.ts", "export { v4 } from './m4';\n"),
            "./m4": ("pages/m4.ts", "export { v5 } from './m5';\n"),
            "./m5": ("pages/m5.ts", "export { v6 } from './m6';\n"),
            "./m6": ("pages/m6.ts", "export { v7 } from './m7';\n"),
            "./m7": (
                "pages/m7.ts",
                "(Array.prototype as any).includes = () => false;\nexport function v7() { return 1; }\n",
            ),
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        False,
    ),
    (
        "a module exactly at the reviewed depth bound that only declares",
        {
            "./valueUtils": ("pages/m0.ts", "export { v1 } from './m1';\n"),
            "./m1": ("pages/m1.ts", "export { v2 } from './m2';\n"),
            "./m2": ("pages/m2.ts", "export { v3 } from './m3';\n"),
            "./m3": ("pages/m3.ts", "export { v4 } from './m4';\n"),
            "./m4": ("pages/m4.ts", "export { v5 } from './m5';\n"),
            "./m5": ("pages/m5.ts", "export { v6 } from './m6';\n"),
            "./m6": ("pages/m6.ts", "export { v7 } from './m7';\n"),
            "./m7": ("pages/m7.ts", "export function v7() { return 1; }\n"),
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        True,
    ),
    # `export default <expression>` starts with `export`, so the declaration whitelist
    # waved it through while its initializer was evaluated as the module loaded.
    (
        "a reviewed import target that default-exports an expression",
        {"./valueUtils": ("pages/valueUtils.ts", "export default ('node');\n")},
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        False,
    ),
    # A class body is a declaration the walk never enters, and the form was on the
    # allow-list: `export default class RouteProbe { static x = ... }` ran its static
    # initializer while the module loaded.
    (
        "a reviewed import target that default-exports a class declaration",
        {
            "./valueUtils": (
                "pages/valueUtils.ts",
                "export default class Probe { read() { return 1; } }\n",
            )
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        False,
    ),
    (
        "a reviewed import target whose exported class carries a load-time initializer",
        {
            "./valueUtils": (
                "pages/valueUtils.ts",
                "export class Probe { static x = (Array.prototype as any); }\n",
            )
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        False,
    ),
    # `import('./' + 'deepModule')` starts with a quote, so the edge looked readable
    # and the walk followed nothing while the module behind it ran on load.
    (
        "a reviewed import target that reaches a module through an unreadable specifier",
        {
            "./valueUtils": (
                "pages/valueUtils.ts",
                "export function load() { return import('./' + 'deepModule'); }\n",
            ),
            "./deepModule": ("pages/deepModule.ts", "export function deep() { return 1; }\n"),
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        False,
    ),
    # The name is not one the enumeration lists, so only the shape rule catches it:
    # `Element` passed under `379163ec`, and the gate it fed answered differently in
    # the node domain than in the browser one.
    (
        "a reviewed import target whose module-level binding reads the environment",
        {
            "./valueUtils": (
                "pages/valueUtils.ts",
                "export const dead = typeof Element !== 'undefined' ? (poison(), 1) : 0;\n",
            )
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        False,
    ),
    # The probe that defeated `379163ec`: the class is created while the module loads
    # and its static initializer poisons `[].includes`, so the authority answered
    # `true` in every domain while both layers stayed green.
    (
        "a reviewed import target that default-exports a class with a static initializer",
        {
            "./valueUtils": (
                "pages/valueUtils.ts",
                "export default class RouteProbe { static x = "
                "(((Array.prototype as any).includes = () => true), 1); }\n",
            )
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        False,
    ),
    (
        "a reviewed import target that default-exports a class with a static block",
        {
            "./valueUtils": (
                "pages/valueUtils.ts",
                "export default class RouteProbe { static { "
                "(Array.prototype as any).includes = () => true; } }\n",
            )
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        False,
    ),
    # TypeScript's `export = <expression>` exports a value computed while the module
    # loads, and its `export` head kept it on the declaration side of the whitelist.
    (
        "a reviewed import target that exports through an assignment",
        {"./valueUtils": ("pages/valueUtils.ts", "export = read;\n")},
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        False,
    ),
    # A package import is an edge the walk cannot follow - only relative specifiers
    # resolve - so the module behind it ran inside the gate's own import while the
    # closure still called itself read.
    (
        "a reviewed import target that imports a package",
        {
            "./valueUtils": (
                "pages/valueUtils.ts",
                "import { helper } from '@sc/schema';\nexport function read() { return helper; }\n",
            )
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        False,
    ),
    # A literal with a second argument is not an edge `relative_edges()` recognises -
    # it looks for the closing parenthesis right after the literal - so the target was
    # neither followed nor refused and ran while the closure still called itself read.
    (
        "a reviewed import target whose dynamic import carries a second argument",
        {
            "./valueUtils": (
                "pages/valueUtils.ts",
                "export function load() { return import('./deepModule', { with: {} }); }\n",
            ),
            "./deepModule": (
                "pages/deepModule.ts",
                "export function deep() { return 1; }\n",
            ),
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        False,
    ),
    (
        "a reviewed import target that imports a package for its types only",
        {
            "./valueUtils": (
                "pages/valueUtils.ts",
                "import type { FieldDescriptor } from '@sc/schema';\n"
                "export function read(v: FieldDescriptor) { return v; }\n",
            )
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        True,
    ),
    (
        "a reviewed import target that re-exports a package",
        {"./valueUtils": ("pages/valueUtils.ts", "export * from 'somePackage';\n")},
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        False,
    ),
    (
        "a reviewed import target that re-exports a package by name",
        {
            "./valueUtils": (
                "pages/valueUtils.ts",
                "export { read } from '@sc/schema';\n",
            )
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        False,
    ),
    (
        "a reviewed import target that re-exports a package as a namespace",
        {
            "./valueUtils": (
                "pages/valueUtils.ts",
                "export * as ns from 'somePackage';\n",
            )
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        False,
    ),
    (
        "a reviewed import target whose contextual keyword starts a call",
        {
            "./valueUtils": (
                "pages/valueUtils.ts",
                "type(typeof customElements !== 'undefined' && "
                "(Array.prototype.includes = () => false));\n"
                "export function type(value: unknown) { return value; }\n",
            )
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        False,
    ),
    (
        "a reviewed import target that reaches its neighbour through a relative re-export",
        {
            "./valueUtils": ("pages/valueUtils.ts", "export * from './fieldUtils';\n"),
            "./fieldUtils": (
                "pages/fieldUtils.ts",
                "export function read() { return 1; }\n",
            ),
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        True,
    ),
    (
        "a reviewed import target whose declarations are the shape they claim",
        {
            "./valueUtils": (
                "pages/valueUtils.ts",
                "type Label = string;\n"
                "interface Shape { a: string }\n"
                "function read<T>(value: T): T { return value; }\n"
                "export type { Label };\n"
                "export function readShape(shape: Shape) { return shape.a; }\n",
            )
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        True,
    ),
    # The re-export clause is written with `\s*` in every spelling below.  The
    # ladder used to demand a space after `export` and to end in silence, so the
    # same re-export spelled `export*from'./x'` matched no rule, followed no edge
    # and ran another module's load-time code outside every layer.
    (
        "a reviewed import target that re-exports a package without the space",
        {"./valueUtils": ("pages/valueUtils.ts", "export*from'somePackage';\n")},
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        False,
    ),
    (
        "a reviewed import target that re-exports a package by name without the space",
        {"./valueUtils": ("pages/valueUtils.ts", "export{read}from'@sc/schema';\n")},
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        False,
    ),
    (
        "a reviewed import target that re-exports a package as a namespace without the space",
        {"./valueUtils": ("pages/valueUtils.ts", "export*as ns from'somePackage';\n")},
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        False,
    ),
    (
        "a reviewed import target that reaches its neighbour through a re-export without the space",
        {
            "./valueUtils": ("pages/valueUtils.ts", "export*from'./fieldUtils';\n"),
            "./fieldUtils": (
                "pages/fieldUtils.ts",
                "export function read() { return 1; }\n",
            ),
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        True,
    ),
    (
        "a reviewed import target that reaches its neighbour through an import without the space",
        {
            "./valueUtils": (
                "pages/valueUtils.ts",
                "import'./fieldUtils';\nexport function read() { return 1; }\n",
            ),
            "./fieldUtils": (
                "pages/fieldUtils.ts",
                "export function read() { return 1; }\n",
            ),
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        True,
    ),
    # The read window counts collapsed characters now: four hundred spaces used to
    # fill it, so the statement read as `export ` and every rung of the ladder found
    # nothing to match.
    (
        "a reviewed import target that pads its statement past the read window",
        {
            "./valueUtils": (
                "pages/valueUtils.ts",
                "export" + " " * 410 + "const dead = () => 1;\n",
            )
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        False,
    ),
    (
        "a reviewed import target that pads a declaration it may carry",
        {
            "./valueUtils": (
                "pages/valueUtils.ts",
                "export" + " " * 410 + "function read() { return 1; }\n",
            )
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        True,
    ),
    (
        "a reviewed import target that pads a package re-export past the read window",
        {
            "./valueUtils": (
                "pages/valueUtils.ts",
                "export" + " " * 410 + "* from 'somePackage';\n",
            )
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        False,
    ),
    # Only the ladder's default reads this one: the class body runs while the module
    # loads, but the decorator stands where the `class` rung looks for `class`.
    (
        "a reviewed import target that decorates an exported class body",
        {
            "./valueUtils": (
                "pages/valueUtils.ts",
                "export @sealed class Probe { static x = 1; }\n",
            )
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        False,
    ),
    (
        "a reviewed import target whose generics nest an angle bracket",
        {
            "./valueUtils": (
                "pages/valueUtils.ts",
                "type Box<N> = { value: N };\n"
                "type Wrapped<T extends Box<number>> = T;\n"
                "function read<T extends Box<number>>(value: T): T { return value; }\n"
                "export type { Wrapped };\n"
                "export function readWrapped(value: Wrapped<number>) { return value; }\n",
            )
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        True,
    ),
    # The same two defeats as the authority fixtures above, one layer out: the closure
    # member is a reviewed import target, and its `export type ... = 'x'` line used to
    # swallow the line below it - which is load-time code running inside the gate's own
    # import, in the browser and in the gate's node run alike.
    (
        "a reviewed import target whose literal type alias is followed by a bare expression",
        {
            "./valueUtils": (
                "pages/valueUtils.ts",
                "export type gC1 = 'x'\n"
                "(Array.prototype as any).includes = () => true\n",
            )
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        False,
    ),
    (
        "a reviewed import target whose type-argument alias is followed by a bare expression",
        {
            "./valueUtils": (
                "pages/valueUtils.ts",
                "export type gC2 = Record<string, number>\n"
                "(Array.prototype as any).includes = () => true\n",
            )
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        False,
    ),

    # The same `=>` and `)` the token walk cannot see on its own, one layer out: the
    # regular expression is an operand, the quote inside its character class is not a
    # string opener, and the gate below it stays in the text the walk reads.  Read as a
    # division, that quote opened a *string* which closed on the quote in
    # `typeof Element !== 'undefined'` - so the gate was erased from the member's text,
    # the walk found no statement there, and the poisoned `Array.prototype.includes` it
    # guards loaded in the browser while the closure stayed green.
    #
    # The second function is what makes these two fixtures say *that*: the quotes of the
    # erased span have to pair up, and with only one function the phantom string runs to
    # the end of the member and the walk refuses it as an unterminated literal instead -
    # the right verdict for the wrong reason, which would leave the channel itself
    # unpinned.  On `f944b313` the old guard accepted both shapes and the new one refuses
    # them for the statement the gate is.
    (
        "a reviewed import target whose arrow body holds a character-class regular expression",
        {
            "./valueUtils": (
                "pages/valueUtils.ts",
                "export function isQuotedValue(value: string): boolean {\n"
                "  const matches = (text: string): boolean => /[']/.test(text);\n"
                "  return matches(value);\n"
                "}\n"
                "\n"
                "if (typeof Element !== 'undefined') { "
                "(Array.prototype as any).includes = () => false; }\n"
                "\n"
                "export function isQuotedAgain(value: string): boolean {\n"
                "  const matches = (text: string): boolean => /[']/.test(text);\n"
                "  return matches(value);\n"
                "}\n",
            )
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        False,
    ),
    (
        "a reviewed import target whose loop head holds a character-class regular expression",
        {
            "./valueUtils": (
                "pages/valueUtils.ts",
                "export function totalOf(list: string[]): number {\n"
                "  let total = 0;\n"
                "  for (const item of list) /[']/.test(item) && (total += 1);\n"
                "  return total;\n"
                "}\n"
                "\n"
                "if (typeof Element !== 'undefined') { "
                "(Array.prototype as any).includes = () => false; }\n"
                "\n"
                "export function totalAgain(list: string[]): number {\n"
                "  let total = 0;\n"
                "  for (const item of list) /[']/.test(item) && (total += 1);\n"
                "  return total;\n"
                "}\n",
            )
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        False,
    ),
    (
        "a reviewed import target whose alias body names a property like a declaration keyword",
        {
            "./valueUtils": (
                "pages/valueUtils.ts",
                "export type CollaborationKindName = { type: string }\n"
                "<unknown>Object.defineProperty(Array.prototype, 'includes', "
                "{ value: () => false });\n",
            )
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        False,
    ),
    (
        "a reviewed import target whose only regular expression is an arrow body",
        {
            "./valueUtils": (
                "pages/valueUtils.ts",
                "export function isQuotedValue(value: string): boolean {\n"
                "  const matches = (text: string): boolean => /[']/.test(text);\n"
                "  return matches(value);\n"
                "}\n",
            )
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        True,
    ),
    # And the clause that may begin on the next line, which the closure walk has to
    # follow: the edge is only there while the import's own window reaches its `from`.
    (
        "a reviewed import target whose import clause begins on the next line",
        {
            "./valueUtils": (
                "pages/valueUtils.ts",
                "import\n  { fieldType } from './fieldUtils';\n"
                "export function read() { return 1; }\n",
            ),
            "./fieldUtils": (
                "pages/fieldUtils.ts",
                "export function fieldType() { return 'x'; }\n",
            ),
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        True,
    ),
    (
        "a reviewed import target whose type-only import clause begins on the next line",
        {
            "./valueUtils": (
                "pages/valueUtils.ts",
                "import type\n  { FieldKind } from './fieldUtils';\n"
                "export function read() { return 1; }\n",
            ),
            "./fieldUtils": (
                "pages/fieldUtils.ts",
                "export type FieldKind = string;\n",
            ),
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        True,
    ),
    # A declaration's body brace can sit right after a brace that ended a type in
    # its header (`): { a: boolean } {`), and the two are only told apart by what
    # precedes them.  Read as one shape, the walk ended the declaration at the type
    # literal and reported the legal body as a statement that runs on load - the
    # shape `store.ts` reached `resolveContractV2RecordActionStates` through.
    (
        "a reviewed import target whose declaration body follows an object type in its signature",
        {
            "./valueUtils": (
                "pages/valueUtils.ts",
                "export function read(policy: Record<string, unknown>): { blocked: boolean } {\n"
                "  const kind = (policy as Record<string, unknown>).kind;\n"
                "  return { blocked: kind === 'state_limited_business_document' };\n"
                "}\n",
            )
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        True,
    ),
    # The body brace that follows the type literal must still *end* the
    # declaration, or the block under it hides inside the function and runs while
    # the closure calls itself read.
    (
        "a reviewed import target whose statement follows a declaration body typed by an object literal",
        {
            "./valueUtils": (
                "pages/valueUtils.ts",
                "export function read(): { blocked: boolean } {\n"
                "  return { blocked: false };\n"
                "}\n"
                "{ (Array.prototype as any).includes = () => true }\n",
            )
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        False,
    ),
    # The environment ban is a ban on names the module reads.  A name spelled in a
    # comment or a string literal is not a read of it, and the authority module's
    # own rule already reads its blanked text.
    (
        "a reviewed import target that names the environment only in a comment",
        {
            "./valueUtils": (
                "pages/valueUtils.ts",
                "// the browser document is not read here\nexport function read(v: unknown) { return v; }\n",
            )
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        True,
    ),
    (
        "a reviewed import target that names the environment only in a string literal",
        {
            "./valueUtils": (
                "pages/valueUtils.ts",
                "export function label() { return 'document'; }\n",
            )
        },
        _COLLABORATION_IMPORT_CLOSURE_ORIGIN,
        True,
    ),
)


def _collaboration_import_closure_self_check_failures() -> list[str]:
    failures = []
    for name, files, source, expected in _COLLABORATION_IMPORT_CLOSURE_SELF_CHECK:
        observed = not collaboration_import_closure_failures(
            _COLLABORATION_VM_MODULE + ".ts",
            source,
            lambda _origin, specifier, files=files: files.get(specifier),
        )
        if observed is not expected:
            failures.append(name)
    return failures


def _collaboration_self_check_failures() -> list[str]:
    return [
        name
        for name, host, module, makefile, expected in _COLLABORATION_SELF_CHECK
        if (not collaboration_authority_failures(host, module, makefile)) is not expected
    ] + [
        name
        for name, page, expected in _COLLABORATION_PAGE_SELF_CHECK
        if (not collaboration_page_wiring_failures(page)) is not expected
    ] + _collaboration_import_closure_self_check_failures()

require(
    not _collaboration_self_check_failures(),
    "collaboration authority self-check misreads these shapes: "
    + ", ".join(_collaboration_self_check_failures()),
)

# Every located window - the three authority bodies and the declared kind list - is
# located on this blanking and then read back out of the original text, so the
# blanking has to preserve every offset.  It is asserted on the real inputs *and* on
# a sample that mixes comments, string literals and bracket property accesses, since
# those are exactly the three transforms that used to shorten the text.
require(
    all(
        len(_blank_comments_and_strings(text)) == len(text)
        for text in (
            form_host,
            contract_form_vm,
            contract_form_page,
            frontend_makefile,
            _COLLABORATION_OFFSET_SAMPLE,
        )
    ),
    "comment and string blanking must preserve every offset, or every located window "
    "is read back from the wrong place",
)

# The page-side props live on another file, so they are driven by their own
# self-check matrix (`_COLLABORATION_PAGE_SELF_CHECK`) rather than by the host one;
# the assertion is element level rather than a whole-file substring.
require(
    not collaboration_authority_failures(
        form_host, contract_form_vm, frontend_makefile, other_make_sources
    )
    and not collaboration_page_wiring_failures(contract_form_page),
    "collaboration region must follow the normalized runtime capability or subordinate node authority, "
    "and stay consumed by the host template: "
    + "; ".join(
        collaboration_authority_failures(
            form_host, contract_form_vm, frontend_makefile, other_make_sources
        )
        + collaboration_page_wiring_failures(contract_form_page)
    ),
)

# The proof is content bound: the layer that claims semantic correctness is only
# worth anything while it is the proof that was reviewed, so replacing it (even by
# one line that makes every assertion a no-op) has to fail here and force the
# digest in this guard to be updated in the same commit.
collaboration_authority_test = (ROOT / _COLLABORATION_AUTHORITY_TEST).read_text(encoding="utf-8")
require(
    hashlib.sha256(collaboration_authority_test.encode("utf-8")).hexdigest()
    == _COLLABORATION_AUTHORITY_TEST_SHA256,
    "the executable collaboration authority proof changed: re-run it, then update "
    "_COLLABORATION_AUTHORITY_TEST_SHA256 in this guard in the same commit",
)
require(
    "from 'node:assert/strict'" in collaboration_authority_test
    and _COLLABORATION_AUTHORITY_TEST_MODULE_IMPORT in collaboration_authority_test,
    "the executable collaboration authority proof no longer asserts against the real runtime module",
)

# The host and the proof must reach the rule at the *same* module, under the *same*
# local name: a specifier binding, not just a symbol name, so a shim module cannot
# serve both layers and `import { X as Y }` cannot bind a name nobody calls.
host_module_imports = _authority_named_imports(form_host, _COLLABORATION_AUTHORITY)
proof_module_imports = _authority_named_imports(
    collaboration_authority_test, _COLLABORATION_AUTHORITY
)
require(
    all(local == imported for local, imported, _specifier in host_module_imports)
    and all(local == imported for local, imported, _specifier in proof_module_imports)
    and any(
        _resolved_module_path(_COLLABORATION_HOST, specifier) == _COLLABORATION_VM_MODULE
        for _local, _imported, specifier in host_module_imports
    )
    and any(
        _resolved_module_path(_COLLABORATION_AUTHORITY_TEST, specifier)
        == _COLLABORATION_VM_MODULE
        for _local, _imported, specifier in proof_module_imports
    )
    and (ROOT / (_COLLABORATION_VM_MODULE + ".ts")).is_file(),
    "the collaboration authority must be imported by both the host and the executable proof "
    f"from the single runtime VM module `{_COLLABORATION_VM_MODULE}`",
)
# The reviewed import list is only a promise while the guard reads the modules behind
# the specifiers: it named `./valueUtils` and `../../app/contracts/v2/store`, and
# neither file's content was ever opened, so a load-time gate parked in either kept
# every layer green while the rule was dead in the browser.
require(
    not collaboration_import_closure_failures(
        _COLLABORATION_VM_MODULE + ".ts", contract_form_vm
    ),
    "the collaboration authority's reviewed imports must resolve and stay "
    "environment-blind: "
    + "; ".join(
        collaboration_import_closure_failures(
            _COLLABORATION_VM_MODULE + ".ts", contract_form_vm
        )
    ),
)
provider = (UI_SRC / "components/SceneUiProvider.vue").read_text(encoding="utf-8")
require(
    "{{ loadFailure.requestedKit }}" not in provider
    and "{{ loadFailure.fallbackKit }}" not in provider
    and "已切换到兼容模式" in provider,
    "component supplier names leak into the ordinary recovery notice",
)

host = (WEB_SRC / "views/ActionView.vue").read_text(encoding="utf-8")
runtime = (WEB_SRC / "app/action_runtime/useActionViewSceneComponentDriverRuntime.ts").read_text(encoding="utf-8")
require("useActionViewSceneComponentDriverRuntime" in host, "ActionView does not delegate component-driver orchestration")
require("session.featureFlags.scene_component_drivers_v1" in host, "backend policy flag is not consumed")
require("resolveSceneReadonlyCollectionBridge" in runtime, "normalized readonly bridge is not consumed")
require("currentDecision.targeted" in runtime and "contractError" in runtime, "targeted normalized failures do not fail closed")

system_init = (ROOT / "addons/smart_core/handlers/system_init.py").read_text(encoding="utf-8")
require("platform_feature_flags_for_user_readonly" in system_init, "startup flag source is not read-only entitlement")
require("resolve_system_feature_flags" in system_init, "startup flags are not normalized")

policy = (WEB_SRC / "app/renderers/sceneComponentDriverPolicy.ts").read_text(encoding="utf-8")
for reason in (
    "SCENE_DRIVER_POLICY_DISABLED",
    "SCENE_DRIVER_PAGE_NOT_READONLY",
    "SCENE_DRIVER_MUTATION_ACTION_PRESENT",
    "SCENE_DRIVER_SELECTION_PRESENT",
    "SCENE_DRIVER_SCOPE_EMPTY",
):
    require(reason in policy, f"fail-closed reason missing: {reason}")
require("SCENE_DRIVER_FORM_MODE_UNSUPPORTED" in policy, "readonly entitlement does not constrain form mode")
require("SCENE_DRIVER_FORM_MODES_MISSING" in policy, "editable form entitlement does not fail closed without explicit modes")
require(
    "systemDefaultKit: 'tdesign-modern'" in policy
    and "resolution: { kit: 'tdesign-modern', source: 'safe-default' }" in policy,
    "TDesign is not the formal safe product default",
)
require(
    "allowUserOverride: false" in policy,
    "component supplier remains a user-selectable product preference",
)

form_section = (WEB_SRC / "components/template/FormSection.vue").read_text(encoding="utf-8")
require("from '@sc/ui/form'" in form_section, "form fields must consume the narrow driver-neutral UI export")
require("emitFieldChange(field, $event)" in form_section, "driver field does not reuse the canonical field-change path")
require(
    ':model-value="contractFormDriverValue(field)"' in form_section,
    "driver field value bypasses the canonical empty-value normalizer",
)
require(
    form_section.index('v-else-if="usesSceneFieldControl(field) && !(preferReadonlyFacts && field.readonly)"')
    < form_section.index('v-else-if="field.readonly || isJsonField(field)"'),
    "readonly ContractForm fields bypass the selected component driver",
)
require(
    "preferReadonlyFacts?: boolean" in form_section
    and ":prefer-readonly-facts=\"preferReadonlyFacts\"" in canonical_node_renderer
    and object_task_page.count("prefer-readonly-facts") >= 6,
    "semantic readonly floorplan still renders disabled edit controls instead of business facts",
)
require(
    "preferReadonlyFacts?: boolean" in native_renderer
    and native_renderer.count(':prefer-readonly-facts="preferReadonlyFacts"') >= 5
    and native_surface.count(':prefer-readonly-facts="renderMode === \'readonly\'"') == 2,
    "native workspace readonly fields still render disabled edit controls instead of business facts",
)
require(
    form_section.index('v-else-if="usesProfessionalMany2many(field) && relationAdapter"')
    < form_section.index('v-else-if="field.readonly || isJsonField(field)"'),
    "readonly x2many fields leak raw ids instead of using the professional governed relation renderer",
)
scene_field_control = (UI_SRC / "components/primitives/SceneFieldControl.vue").read_text(encoding="utf-8")
require(
    scene_field_control.count("if (props.field.readonly) return;") >= 2,
    "readonly driver controls do not fail closed before emitting changes",
)
require(
    "normalizeSceneFieldControlValue(value, props.field.kind)" in scene_field_control,
    "driver change events bypass the shared empty-value normalizer",
)
probe_fixture = (ROOT / "addons/smart_construction_acceptance_fixture/tools/component_driver_probe.py").read_text(encoding="utf-8")
probe_tree = ast.parse(probe_fixture)
probe_function = next(
    (node for node in probe_tree.body if isinstance(node, ast.FunctionDef) and node.name == "apply_component_driver_probe"),
    None,
)
require(probe_function is not None, "browser probe fixture function missing")
probe_source = ast.get_source_segment(probe_fixture, probe_function) or ""
require("\"models\": [model]" in probe_source, "browser probe must consume the action-owned model")
require(
    '"allowed_kits": ["sc-native", "tdesign-modern"]' in probe_source,
    "browser probe must exercise all registered production form drivers",
)
require("component driver probe requires a non-payment action model" in probe_source, "browser probe lacks its non-payment boundary")
require("build_scope_key(" in probe_source, "browser probe does not identify its exact persisted driver preference")
require("preference_model.search([" in probe_source and "]).unlink()" in probe_source, "browser probe does not clean its persisted driver preference")
require("probe_record_name" in probe_source and "probe_model.search([" in probe_source, "browser probe does not own an exact disposable create target")
require('"create_probe_name": probe_record_name' in probe_source, "browser probe does not export its exact disposable create identity")
require('"view_id": form_view_id' in probe_source, "browser probe does not bind the action-owned native form view")
require("payment.request" not in probe_source, "browser probe drifted into the payment vertical")
acceptance_fixture = (ROOT / "scripts/test/frontend_productization_fixture.sh").read_text(encoding="utf-8")
require("SC_ACCEPTANCE_COMPONENT_DRIVER_PROBE_MODE" in acceptance_fixture, "browser probe is not routed through the governed fixture entry")
browser_probe = (ROOT / "scripts/verify/frontend_scene_component_driver_readonly_browser.mjs").read_text(encoding="utf-8")
for forbidden in ("api.data.create", "api.data.write", "api.data.unlink", "execute_button"):
    require(forbidden in browser_probe, f"readonly browser probe does not detect mutation: {forbidden}")
require(
    "await page.route('**/*'" in browser_probe
    and "route.abort('blockedbyclient')" in browser_probe
    and "evidence.mutations.length === 0" in browser_probe,
    "readonly parity probe does not fail closed before a business mutation reaches the backend",
)
require(
    "user.view.preference.set" not in browser_probe
    and "selectGovernedDriver" not in browser_probe
    and "exerciseEditableMode" not in browser_probe
    and "executeCreateProbe" not in browser_probe,
    "readonly parity probe still changes driver preference or enters edit/create",
)
require("{ width: 390, height: 844 }" in browser_probe, "browser probe does not cover the governed mobile viewport")
require("native_same_page_readonly_parity.v1" in browser_probe, "browser report is not explicitly readonly-only parity evidence")
for required in (
    "normalizedHierarchy", "canonicalHierarchy", "nativeStructureSignature",
    "normalizedStructureSignature", "fieldMetadata", "sourceView", "pageCapabilities",
    "native widget behavior is not resolved",
):
    require(required in browser_probe, f"readonly parity report omits native atom evidence: {required}")

form_page = (WEB_SRC / "pages/ContractFormPage.vue").read_text(encoding="utf-8")
driver_host_call = form_page[form_page.index("<ContractFormDriverHost"):form_page.index("<ContractFormNativeCanvas")]
for forbidden_prop in (
    "layout-nodes",
    "field-schemas-for-nodes",
    "native-action-state-resolver",
    "is-node-visible",
):
    require(forbidden_prop not in driver_host_call, f"product driver host still receives legacy authority: {forbidden_prop}")
require('@action-ref="runCanonicalFormAction"' in driver_host_call, "canonical action reference does not reach unified executor adapter")
require('ContractFormNativeCanvas v-else' in form_page and ':designer-mode="true"' in form_page, "legacy canvas is not isolated to form configuration mode")
require(':error="canonicalFormDriverError"' in driver_host_call, "canonical action adapter failures do not fail closed in the driver host")
require(
    "const canonicalProductRendererActive = computed(() => !showCurrentFormFieldConfigScope.value);" in form_page,
    "canonical product failure can reactivate the legacy product pipeline",
)
require(
    "validateCanonicalFormActionExecutors(" in form_page
    and "collectCanonicalFormActions(model)" in form_page
    and "validateCanonicalFormActionExecutors(collectCanonicalFormActions(model), contractActions.value)" in form_page,
    "canonical cutover does not validate every executable action reference",
)
require(
    form_page.index("const canSave = computed")
    < form_page.index("useContractFormComponentDriverRuntime({"),
    "immediate driver watchers must be installed after render-profile dependencies",
)
record_form_layout = (WEB_SRC / "pages/contractForm/useRecordFormLayout.ts").read_text(encoding="utf-8")
require(
    "normalizeWorkflowPhaseStatusbar" not in record_form_layout
    and "fallback:{visible:false,field:'',current:'',states:[],reachedValues:[],readonly:true}" in record_form_layout,
    "form statusbar can still be fabricated from workflow fallback",
)

collection_surface = (UI_SRC / "components/SceneCollectionSurface.vue").read_text(encoding="utf-8")
collection_wrapper = (WEB_SRC / "components/action/SceneReadonlyCollectionRenderer.vue").read_text(encoding="utf-8")
require("openRow" in collection_surface, "readonly collection does not expose row navigation")
require("'open-record'" in collection_wrapper, "driver row navigation is not returned to the unified host")

print(
    "[verify.frontend.scene_component_bridge.guard] PASS "
    f"checks={_CHECKS} collaboration_self_check="
    f"{len(_COLLABORATION_SELF_CHECK) + len(_COLLABORATION_PAGE_SELF_CHECK) + len(_COLLABORATION_IMPORT_CLOSURE_SELF_CHECK)}"
)
