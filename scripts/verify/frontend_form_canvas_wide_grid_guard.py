#!/usr/bin/env python3
"""Guard the full-width business form canvas and contract-driven responsive grid."""

from pathlib import Path

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
mapper = read("components/template/fieldSpan.mapper.ts")
schema_builder = read("pages/contractForm/useRecordFormFieldSchemas.ts")
object_task = read("pages/contractForm/ObjectTaskPage.vue")
section_navigation = read("pages/contractForm/FormSectionNavigation.vue")
native_driver = read("pages/contractForm/ContractFormDriverHost.vue")
native_surface = read("pages/contractForm/CanonicalNativeFormSurface.vue")
native_navigation_model = read("pages/contractForm/nativeSectionNavigation.ts")
canonical_renderer = read("pages/contractForm/CanonicalFormNodeRenderer.vue")
professional_base_field = read("components/professional-fields/ProfessionalBaseFieldControl.vue")
relations = read("components/template/X2ManyRelationRenderer.vue")

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
    ".field--compact {\n  grid-column: span 8;",
    ".field--normal,\n.field--half {\n  grid-column: span 12;",
    ".field--wide {\n  grid-column: span 16;",
    ".field--full {\n  grid-column: span 24;",
    ".template-form-section-grid--columns-1 > .field {\n  grid-column: 1 / -1;",
    ".field--wide,\n  .field--full {\n    grid-column: 1 / -1;",
    ".field-control-main {\n  flex: 1 1 auto;\n  display: grid;\n  width: 100%;\n  max-width: 100%;\n  min-width: 0;",
    ".readonly-value {\n  box-sizing: border-box;\n  display: grid;\n  align-items: center;\n  width: 100%;\n  max-width: 100%;\n  min-width: 0;",
    "white-space: pre-wrap;\n  overflow-wrap: anywhere;\n  word-break: break-word;",
):
    if required not in section:
        fail(f"responsive field grid contract missing: {required}")
for forbidden in ("fieldName", "description", "remark", "address", "location"):
    if forbidden in mapper:
        fail(f"field span guesses from business name/label: {forbidden}")
if "resolveFieldSpanClass({fieldType:" not in schema_builder:
    fail("schema builder does not use type-only safe span fallback")
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
    '@click="scrollTrack(-1)"',
    '@click="scrollTrack(1)"',
    '<ScIcon name="arrow-left"',
    '<ScIcon name="arrow-right"',
    'flex: 1 1 auto;',
    ':deep(.form-section-navigation__scroll-control)',
):
    if required not in section_navigation:
        fail(f"shared semantic navigation missing: {required}")
for forbidden in ('form-section-navigation__cue', '滑动 ›', 'linear-gradient('):
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
    "props.auditEvents.length ? {",
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
    "workspaceSurfaceNavigationItems",
    "auditAvailable: props.showCollaborationPanel === true && auditEvents.value.length > 0",
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
if "const sectionTitle = computed(() => '');" not in canonical_renderer or "const groupHeadingVisible = computed(() => false);" not in canonical_renderer:
    fail("intentionally hidden backend group titles were restored")
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
