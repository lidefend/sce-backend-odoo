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
section = read("components/template/FormSection.vue")
mapper = read("components/template/fieldSpan.mapper.ts")
schema_builder = read("pages/contractForm/useRecordFormFieldSchemas.ts")
object_task = read("pages/contractForm/ObjectTaskPage.vue")
section_navigation = read("pages/contractForm/FormSectionNavigation.vue")
native_driver = read("pages/contractForm/ContractFormDriverHost.vue")
canonical_renderer = read("pages/contractForm/CanonicalFormNodeRenderer.vue")
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
    ".field--wide,\n  .field--full {\n    grid-column: 1 / -1;",
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
):
    if required not in section_navigation:
        fail(f"shared semantic navigation missing: {required}")
for required in (
    'data-section-title="基本信息"',
    'data-section-title="关系明细"',
    "presentableRelationNodes.value.length ? { key: 'relation'",
    "props.supplementaryInputNodes.length ? { key: 'supplementary-input'",
    '<section\n      v-if="presentableRelationNodes.length"',
):
    if required not in object_task:
        fail(f"semantic form structure missing: {required}")
if 'FormSectionNavigation' not in object_task or 'FormSectionNavigation' not in native_driver:
    fail("task and workspace forms do not share section navigation")
if ':fill-orphan-rows="false"' not in read("components/template/NativeFormTreeRenderer.vue"):
    fail("native forms still stretch ordinary orphan fields across a full row")
if object_task.index('data-floorplan-region="relation"') > object_task.index('data-floorplan-region="supplementary-input"'):
    fail("relationship details are still placed after auxiliary disclosures")
if "const sectionTitle = computed(() => '');" not in canonical_renderer or "const groupHeadingVisible = computed(() => false);" not in canonical_renderer:
    fail("intentionally hidden backend group titles were restored")
for required in ("readonlyO2mTableColumns", 'class="o2m-readonly-table"', 'class="o2m-readonly-list"'):
    if required not in relations:
        fail(f"responsive readonly detail structure missing: {required}")
if "background: var(--sc-app-panel);" not in form_css or "isolation: isolate;" not in form_css:
    fail("sticky form header is not an opaque isolated surface")

print("[frontend_form_canvas_wide_grid_guard] PASS")
