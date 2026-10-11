#!/usr/bin/env python3
"""Guard the full-width business form canvas and contract-driven responsive grid."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "frontend/apps/web/src"


def read(path: str) -> str:
    return (WEB / path).read_text(encoding="utf-8")


def fail(message: str) -> None:
    raise SystemExit(f"[frontend_form_canvas_wide_grid_guard] FAIL {message}")


tokens = read("styles/design-system.css")
patterns = read("styles/product-patterns.css")
form_css = read("pages/contractForm/ContractFormPage.css")
product_header = read("components/product-page-header/ProductPageHeader.vue")
section = read("components/template/FormSection.vue")
layout_span = read("components/template/layoutSpan.ts")
native_renderer = read("components/template/NativeFormTreeRenderer.vue")
schema_builder = read("pages/contractForm/useRecordFormFieldSchemas.ts")
object_task = read("pages/contractForm/ObjectTaskPage.vue")
section_navigation = read("pages/contractForm/FormSectionNavigation.vue")
native_driver = read("pages/contractForm/ContractFormDriverHost.vue")
native_surface = read("pages/contractForm/CanonicalNativeFormSurface.vue")
native_navigation_model = read("pages/contractForm/nativeSectionNavigation.ts")
canonical_renderer = read("pages/contractForm/CanonicalFormNodeRenderer.vue")
professional_base_field = read("components/professional-fields/ProfessionalBaseFieldControl.vue")
relations = read("components/template/X2ManyRelationRenderer.vue")
visual_smoke = (ROOT / "scripts/verify/local_dev_candidate_visual_smoke.mjs").read_text(encoding="utf-8")

combined = "\n".join((tokens, patterns, form_css))
for forbidden in ("--sc-content-focused-form-max", "--sc-form-field-content-max"):
    if forbidden in combined:
        fail(f"canvas-level focused limit remains: {forbidden}")
if "max-width: none" not in form_css or ".contract-form-canvas-shell" not in form_css:
    fail("form canvas does not explicitly own full available width")
for required in (
    "container-type: inline-size",
    "@container (max-width: 479px)",
    "@container (min-width: 480px) and (max-width: 959px)",
    "template-form-section-grid--columns-${columns}",
    ".field[data-field-span='8'] {\n  grid-column: span 8;",
    ".field[data-field-span='12'] {\n  grid-column: span 12;",
    ".field[data-field-span='16'] {\n  grid-column: span 16;",
    ".field[data-field-span='24'] {\n  grid-column: span 24;",
    ".template-form-section-grid--columns-1 > .field {\n  grid-column: 1 / -1;",
    ".template-form-section-grid > .field[data-field-band='full'] {\n    grid-column: 1 / -1;",
    ':data-field-span="fieldSpan(',
    ':data-field-band="fieldSpanBand(',
    ".field-control-main {\n  flex: 1 1 auto;\n  display: grid;\n  width: 100%;\n  max-width: 100%;\n  min-width: 0;",
    "white-space: pre-wrap;\n  overflow-wrap: anywhere;\n  word-break: break-word;",
):
    if required not in section:
        fail(f"responsive field grid contract missing: {required}")
readonly_block = re.search(r"(?m)^\.readonly-value\s*\{([^{}]*)\}", section)
if not readonly_block:
    fail("readonly value selector missing")
readonly_declarations = dict(re.findall(r"([\w-]+)\s*:\s*([^;]+);", readonly_block.group(1)))
for name, expected in {"box-sizing": "border-box", "display": "grid", "align-items": "center", "width": "100%", "max-width": "100%", "min-width": "0"}.items():
    if readonly_declarations.get(name, "").strip() != expected:
        fail(f"readonly value declaration missing or invalid: {name}")
# The single renderer-facing layout unit.  The projection folds the native arch
# `col` / `col-*` and the low-code `columns` / `field_size` into one `span` on a
# 24-unit grid, so the renderer consumes that number and must not keep a second
# width vocabulary of its own.
if (
    "export function layoutGridUnits(): number {\n  return 24;\n}" not in layout_span
    or "export function isDeclaredLayoutSpan(value: unknown): boolean" not in layout_span
    or "typeof value === 'number'" not in layout_span
    or "export function declaredLayoutSpan(value: unknown): number" not in layout_span
):
    fail("the layout span unit is not declared once, fail-closed, in one module")
for path, source in (("FormSection.vue", section), ("NativeFormTreeRenderer.vue", native_renderer)):
    if "from './layoutSpan'" not in source or "declaredLayoutSpan(" not in source:
        fail(f"{path} does not consume the declared layout span unit")
for forbidden in ("field--compact", "field--normal", "field--half", "field--wide", "field--full", "field--large"):
    if forbidden in section:
        fail(f"form section re-derives a field width from a low-code class name: {forbidden}")
resolve_span = re.search(r"resolveSpan\s*:\s*\(?[\w,\s]*\)?\s*=>\s*([^,\n]+)", schema_builder)
if resolve_span is None or not re.search(r"\.span\b", resolve_span.group(1)):
    fail("schema builder does not carry the declared span through to the field schema")
if re.search(r"(?:\?\?|\|\|)\s*\d", resolve_span.group(1)):
    fail("schema builder re-invents a fallback field span instead of failing closed on the declared unit")

# One declaration, one width: the facet table the renderer resolves a declared
# ``field_size`` with must mirror the projection's, or the same declaration is
# resolved by two authorities (an unknown facet used to fall back to the editor's
# ``normal`` width in the renderer while the projection treated it as undeclared).
projection = (ROOT / "addons/smart_core/handlers/ui_contract_v2_projection.py").read_text(encoding="utf-8")
projected_facets = dict(re.findall(r'"field--([a-z]+)":\s*(\d+)', projection))
facet_table = re.search(
    r"function declaredFieldSizeSpans\(\): Map<string, number> \{([\s\S]*?)\n\}",
    read("pages/contractForm/fieldUtils.ts"),
)
renderer_facets = dict(re.findall(r"\['([a-z]+)', (\d+)\]", facet_table.group(1))) if facet_table else {}
if not renderer_facets or projected_facets != renderer_facets:
    fail(
        "declared layout facets resolve by two authorities: "
        f"projection={projected_facets} renderer={renderer_facets}"
    )
# One declaration, one column authority.  The projection declares the
# container's field-grid column count exactly as it declares the zone, the
# presenter presents that declaration, and the canonical renderer neither
# raises it to a minimum of its own nor clamps it to its own enum.  Two
# defaults (a presenter ``|| 1`` beside a renderer ``?? 2``) let the same
# contract render a field-owning container as full-width on one surface and
# half-width on another.
assembler = (ROOT / "addons/smart_core/core/unified_page_contract_v2_assembler.py").read_text(encoding="utf-8")
presenter = read("app/presentation/contractFormPresenter.ts")
declarer_fn = re.search(r"def declare_container_columns\(node: dict\[str, Any\]\) -> bool:\n([\s\S]*?)\n\n\n", assembler)
declarer_body = declarer_fn.group(1) if declarer_fn else ""
if (
    "def declared_container_columns(" not in assembler
    or "columns = declared_container_columns(node)" not in declarer_body
    or 'node["columns"] = columns' not in declarer_body
):
    fail("the projection does not declare the container field-grid column count")
if "CONTAINER_GRID_COLUMNS_DEFAULT = 2" not in assembler:
    fail("the projection does not resolve an undeclared field grid against the official two-column default")
if (
    "from ..core.unified_page_contract_v2_assembler import declare_container_columns" not in projection
    or "declare_container_columns(node)" not in projection
):
    fail("the projection does not complete the field-grid declaration for a late-appended grid container")
if "declaredContainerColumns(container)" not in presenter:
    fail("the presenter does not present the declared container column count")
presented_columns_fn = re.search(r"function declaredContainerColumns\([\s\S]*?\n\}", presenter)
if presented_columns_fn is None:
    fail("the presenter does not present the declared container column count")
for forbidden in ("container.cols", "structure?.columns", "structure.columns", "|| 1", "?? 1"):
    if forbidden in presented_columns_fn.group(0):
        fail(f"the presenter re-derives a container column count instead of presenting the declaration: {forbidden}")
layout_columns_fn = re.search(r"const layoutColumns = computed\(\(\) => \{[\s\S]*?\n\}\);", canonical_renderer)
if layout_columns_fn is None or "Number(props.node.columns)" not in layout_columns_fn.group(0):
    fail("the canonical renderer does not present the declared container column count")
for forbidden in ("Math.max(", "Math.min(", "?? 2", "|| 2", "?? 3", "|| 3"):
    if forbidden in layout_columns_fn.group(0):
        fail(f"the canonical renderer raises or clamps a declared container column count: {forbidden}")
if "grid-template-columns: repeat(var(--canonical-layout-columns, 1), minmax(0, 1fr));" not in canonical_renderer:
    fail("the canonical container grid no longer consumes the declared column count")

for forbidden in ("model ===", "role ===", "overflow-x: hidden", "overflow-x: clip"):
    if forbidden in section or forbidden in form_css:
        fail(f"forbidden form-layout inference or overflow masking: {forbidden}")

for required in (
    'data-form-section-navigation',
    ":aria-current=\"activeKey === item.key ? 'location' : undefined\"",
    '章节入口可横向滚动',
    'target.scrollIntoView({ behavior: \'auto\', block: \'start\' })',
    'aria-label="向前浏览表单章节"',
    'aria-label="向后浏览表单章节"',
    'v-if="trackOverflows"',
    ':aria-disabled="!hasMoreBefore"',
    ':aria-disabled="!hasMoreAfter"',
    '@click="scrollTrack(-1)"',
    '@click="scrollTrack(1)"',
    "if (direction === -1 && !hasMoreBefore.value) return;",
    "if (direction === 1 && !hasMoreAfter.value) return;",
    '<ScIcon name="arrow-left"',
    '<ScIcon name="arrow-right"',
    'flex: 1 1 auto;',
    ':deep(.form-section-navigation__scroll-control)',
    'target.exerciseSectionBrowseFocus === true',
    'forwardAtEnd.focused',
    'backwardAtStart.focused',
    'mutationCountBefore === report.mutationCount',
):
    source = section_navigation if required not in (
        'target.exerciseSectionBrowseFocus === true',
        'forwardAtEnd.focused',
        'backwardAtStart.focused',
        'mutationCountBefore === report.mutationCount',
    ) else visual_smoke
    if required not in source:
        fail(f"shared semantic navigation missing: {required}")
for forbidden in (
    'form-section-navigation__cue',
    '滑动 ›',
    'linear-gradient(',
    'v-if="hasMoreBefore"',
    'v-if="hasMoreAfter"',
):
    if forbidden in section_navigation:
        fail(f"section navigation still overlays its terminal labels: {forbidden}")
if "--sc-form-section-nav-height: 0px" in form_css:
    fail("sticky section navigation height is omitted from anchor offset")
for required in (
    'data-section-title="基本信息"',
    'data-section-title="关系明细"',
    "relationshipCollectionNavigationItems(",
    'v-if="supplementaryInputNodes.length"',
    'data-form-section-target="surface:activity"',
    "contractSurfaceNavigationItems(props.sectionSurfaces || [])",
    "auditRegionVisible",
    '<section\n      v-if="presentableRelationNodes.length"',
):
    if required not in object_task:
        fail(f"semantic form structure missing: {required}")
if 'FormSectionNavigation' not in object_task or 'FormSectionNavigation' not in native_surface:
    fail("task and workspace forms do not share section navigation")
if "field.semanticRole).forEach((field) => roles.add" in native_driver:
    fail("workspace navigation still promotes field semantic roles to section identity")
if "inferredSectionRole" in native_navigation_model:
    fail("workspace navigation still infers section identity from descendant field roles")
for required in (
    "nativeBridge.value?.sectionLinks",
    "contractSurfaceNavigationItems(renderedSurfaces.value)",
    "const renderedSurfaces = computed(",
    ':section-surfaces="renderedSurfaces"',
):
    if required not in native_driver:
        fail(f"workspace section identity projection missing: {required}")
for required in (
    'data-form-section-target="surface:activity"',
    'data-section-source-identity="collaboration-panel"',
):
    if required not in native_surface:
        fail(f"workspace section identity projection missing: {required}")
for required in (
    'data-form-section-target="surface:audit"',
    'data-section-source-identity="professional-audit-timeline"',
):
    if required not in read("pages/contractForm/ProfessionalAuditTimeline.vue"):
        fail(f"audit section identity missing: {required}")
for required in (
    ":data-form-section-target=\"field.sectionNavigationTarget || undefined\"",
    ":data-section-source-identity=\"field.sectionSourceIdentity || undefined\"",
):
    if required not in section:
        fail(f"relation collection target projection missing: {required}")
for required in (
    ".sc-form-driver-host {",
    "width: 100%;",
    "max-width: 100%;",
    "min-width: 0;",
    "box-sizing: border-box;",
):
    if required not in native_driver:
        fail(f"native form host shrink chain missing: {required}")
for required in (
    ".sc-native-contract-page,",
    ".sc-native-contract-tree,",
    "width: 100%;",
    "max-width: 100%;",
    "min-width: 0;",
    "box-sizing: border-box;",
):
    if required not in native_surface:
        fail(f"native form shrink chain missing: {required}")
for required in (
    ".form-section-navigation",
    ".form-section-navigation__track",
    "overflow-x: auto;",
):
    if required not in section_navigation:
        fail(f"section navigation width ownership missing: {required}")
if "overflow: hidden;" in section_navigation or "overflow-x: hidden;" in section_navigation:
    fail("section navigation outer shell masks horizontal overflow")
if ':fill-orphan-rows="false"' not in read("components/template/NativeFormTreeRenderer.vue"):
    fail("native forms still stretch ordinary orphan fields across a full row")
if object_task.index('data-floorplan-region="relation"') > object_task.index('data-floorplan-region="post-relation-input"'):
    fail("relationship details are still placed after post-relation disclosures")
for required in (
    "const sectionTitle = computed(() => '');",
    "props.hideGovernedSectionHeading",
    "governedFormStructureSectionIdentity(props.node) || nativeBusinessSectionIdentity(props.node)",
    "const groupHeadingVisible = computed(() => Boolean(governedSection.value));",
):
    if required not in canonical_renderer:
        fail("group heading is not bound to declared section authority or feedback suppression")
for required in (
    ".canonical-form-node--readonly-fact :deep(.field-control-row),\n.canonical-form-node--readonly-fact :deep(.field-control-main) {\n  display: block;\n  width: 100%;\n  max-width: 100%;\n  min-width: 0;",
    "white-space: pre-wrap;\n  overflow-wrap: anywhere;\n  word-break: break-word;",
):
    if required not in canonical_renderer:
        fail(f"canonical readonly fact boundary missing: {required}")
for required in (
    ".professional-base-field-control__readonly {",
    "display: grid;",
    "max-width: 100%;",
    "white-space: pre-wrap;",
    "overflow-wrap: anywhere;",
    "word-break: break-word;",
):
    if required not in professional_base_field:
        fail(f"professional readonly value wrapping missing: {required}")
for required in ("readonlyO2mTableColumns", 'class="o2m-readonly-table"', 'class="o2m-readonly-list"'):
    if required not in relations:
        fail(f"responsive readonly detail structure missing: {required}")
if "background: var(--sc-app-panel);" not in product_header or "isolation: isolate;" not in product_header:
    fail("sticky form header is not an opaque isolated surface")
if ":deep(.template-page-header" in form_css:
    fail("form page bypasses shared header layout ownership")

print("[frontend_form_canvas_wide_grid_guard] PASS")
