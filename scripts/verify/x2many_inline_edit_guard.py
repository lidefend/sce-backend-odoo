#!/usr/bin/env python3
"""Guard one2many inline edit wiring remains active in ContractFormPage."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FORM_PATHS = [
    ROOT / 'frontend/apps/web/src/pages/ContractFormPage.vue',
    ROOT / 'frontend/apps/web/src/pages/contractForm/useContractFormPageState.ts',
    ROOT / 'frontend/apps/web/src/pages/contractForm/useOne2manyRuntime.ts',
    ROOT / 'frontend/apps/web/src/pages/contractForm/useRecordRelationshipFields.ts',
    ROOT / 'frontend/apps/web/src/pages/contractForm/useContractFormPageState.ts',
    ROOT / 'frontend/apps/web/src/pages/contractForm/one2manyUtils.ts',
    ROOT / 'frontend/apps/web/src/pages/contractForm/valueUtils.ts',
    ROOT / 'frontend/apps/web/src/pages/contractForm/onchangeNormalization.ts',
]
ENGINE = ROOT / 'frontend/apps/web/src/app/x2manyCommands.ts'
RELATION_RENDERER = ROOT / 'frontend/apps/web/src/components/template/X2ManyRelationRenderer.vue'
RELATION_ADAPTER = ROOT / 'frontend/apps/web/src/components/template/relationField.types.ts'


def _read(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(str(path))
    return path.read_text(encoding='utf-8')


def main() -> int:
    errors: list[str] = []
    try:
        form = '\n'.join(_read(path) for path in FORM_PATHS)
        engine = _read(ENGINE)
        relation_renderer = _read(RELATION_RENDERER)
        relation_adapter = _read(RELATION_ADAPTER)
    except FileNotFoundError as exc:
        print('[FAIL] x2many_inline_edit_guard')
        print(f'- {exc}')
        return 1

    engine_markers = [
        'export function buildOne2ManyInlineCommands(params: {',
        "mode: 'onchange' | 'write';",
        'commands.push([0, 0, values]);',
        'commands.push([1, id, values]);',
        'commands.push([2, id]);',
    ]
    for marker in engine_markers:
        if marker not in engine:
            errors.append(f'engine missing marker: {marker}')

    form_markers = [
        'showOne2manyErrors: ref(false),',
        'const one2manyValidation = computed(() => collectOne2manyDraftValidation());',
        'function one2manyColumns(name: string): One2ManyColumn[] {',
        'export function one2manyColumnInputType(column: One2ManyColumn)',
        'function addRow(name: string)',
        'function setRowField(fieldName: string, rowKey: string, column: One2ManyColumn, value: unknown)',
        'function removeRow(fieldName: string, rowKey: string)',
        'function restoreRow(fieldName: string, rowKey: string)',
        'function one2manyRowLabel(fieldName: string, row: One2ManyInlineRow) {',
        'export function one2manyRowStateLabel(row: One2ManyInlineRow)',
        'function one2manySummary(name: string) {',
        'export function isOne2manyEmptyValue(column: One2ManyColumn, value: unknown)',
        'function collectValidation()',
        'function one2manyRowErrors(fieldName: string, rowKey: string) {',
        'required: Boolean(descriptor?.required),',
        "params.mode || 'write'",
        "mode: 'onchange'",
    ]
    for marker in form_markers:
        if marker not in form:
            errors.append(f'form missing marker: {marker}')

    renderer_markers = [
        "v-else-if=\"field.type === 'one2many'\"",
        "adapter.one2manyCanCreate(field.name)",
        "adapter.addOne2manyRow(field.name)",
        "adapter.one2manyCreateLabel(field.name, field.label)",
        "adapter.one2manyColumns(field.name)",
        "adapter.setOne2manyRowField(field.name, row.key, column",
        "adapter.removeOne2manyRow(field.name, row.key)",
        "adapter.one2manyRowErrors(field.name, row.key)",
        "adapter.restoreOne2manyRow(field.name, row.key)",
    ]
    for marker in renderer_markers:
        if marker not in relation_renderer:
            errors.append(f'relation_renderer missing marker: {marker}')

    adapter_markers = [
        "one2manyCanCreate: (name: string) => boolean;",
        "one2manyCreateLabel: (name: string, fieldLabel?: string) => string;",
        "addOne2manyRow: (name: string) => void;",
        "setOne2manyRowField: (name: string, rowKey: string, column: RelationFieldColumn, value: unknown) => void;",
        "removeOne2manyRow: (name: string, rowKey: string) => void;",
        "restoreOne2manyRow: (name: string, rowKey: string) => void;",
    ]
    for marker in adapter_markers:
        if marker not in relation_adapter:
            errors.append(f'relation_adapter missing marker: {marker}')

    if errors:
        print('[FAIL] x2many_inline_edit_guard')
        for line in errors:
            print(f'- {line}')
        return 1

    print('[OK] x2many_inline_edit_guard')
    print(f'- form modules: {len(FORM_PATHS)}')
    print(f'- engine: {ENGINE}')
    print(f'- relation_renderer: {RELATION_RENDERER}')
    print(f'- relation_adapter: {RELATION_ADAPTER}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
