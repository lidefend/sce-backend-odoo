#!/usr/bin/env python3
"""Guard modifier runtime wiring remains contract-driven and active in form engine."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / 'frontend/apps/web/src/app/modifierEngine.ts'
NATIVE_LAYOUT = ROOT / 'frontend/apps/web/src/pages/contractForm/nativeLayoutUtils.ts'
FORM_LAYOUT = ROOT / 'frontend/apps/web/src/pages/contractForm/useRecordFormLayout.ts'
FORM_PATHS = [
    ROOT / 'frontend/apps/web/src/pages/ContractFormPage.vue',
    ROOT / 'frontend/apps/web/src/pages/contractForm/useRecordFormLayout.ts',
    ROOT / 'frontend/apps/web/src/pages/contractForm/useRecordFormFieldSchemas.ts',
    ROOT / 'frontend/apps/web/src/pages/contractForm/nativeLayoutUtils.ts',
]


def _read(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(str(path))
    return path.read_text(encoding='utf-8')


def main() -> int:
    errors: list[str] = []
    try:
        engine = _read(ENGINE)
        form = '\n'.join(_read(path) for path in FORM_PATHS)
    except FileNotFoundError as exc:
        print('[FAIL] modifiers_runtime_guard')
        print(f'- {exc}')
        return 1

    engine_markers = [
        'export function buildRuntimeFieldStates(',
        "if (head === '|')",
        "if (head === '&')",
        "if (head === '!')",
        'invisible: evalModifierBucket(',
        'readonly: evalModifierBucket(',
        'required: evalModifierBucket(',
        # The declared value domain has exactly one rule, owned by the engine.
        'export function resolveDeclaredModifierFieldValue(',
        "live[name] !== undefined",
        'valueField ? resolveFieldValue(valueField) : row.value',
    ]
    for marker in engine_markers:
        if marker not in engine:
            errors.append(f'engine missing marker: {marker}')

    form_markers = [
        "import { buildRuntimeFieldStates } from '../../app/modifierEngine';",
        'const runtimeFieldStates = computed(() => {',
        'const runtimeState = (name: string)',
        'if (runtimeState(name).invisible) return false;',
        'state.readonly',
        'state.required',
    ]
    for marker in form_markers:
        if marker not in form:
            errors.append(f'form missing marker: {marker}')

    # A second implementation of the value-domain rule would let two consumers
    # disagree about the same declaration, which is the exact drift this guard
    # exists to prevent: the native layout path must consume the engine rule.
    try:
        native_layout = _read(NATIVE_LAYOUT)
        form_layout = _read(FORM_LAYOUT)
    except FileNotFoundError as exc:
        print('[FAIL] modifiers_runtime_guard')
        print(f'- {exc}')
        return 1
    if 'export function resolveNativeModifierFieldValue(' in native_layout:
        errors.append(
            'nativeLayoutUtils defines its own modifier value-resolution rule '
            'instead of consuming resolveDeclaredModifierFieldValue',
        )
    if 'resolveDeclaredModifierFieldValue' not in native_layout:
        errors.append('nativeLayoutUtils must re-export resolveDeclaredModifierFieldValue')
    if 'resolveDeclaredModifierFieldValue(modifierMainData(),context.formData,field)' not in form_layout:
        errors.append(
            'useRecordFormLayout must resolve declared modifiers through '
            'resolveDeclaredModifierFieldValue',
        )

    if errors:
        print('[FAIL] modifiers_runtime_guard')
        for line in errors:
            print(f'- {line}')
        return 1

    print('[OK] modifiers_runtime_guard')
    print(f'- engine: {ENGINE}')
    print(f'- form modules: {len(FORM_PATHS)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
