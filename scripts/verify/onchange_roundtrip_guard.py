#!/usr/bin/env python3
"""Guard onchange roundtrip is wired end-to-end (backend handler + frontend consumer)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / 'addons/smart_core/handlers/api_onchange.py'
FRONTEND_API = ROOT / 'frontend/apps/web/src/api/onchange.ts'
FORM_PATHS = [
    ROOT / 'frontend/apps/web/src/pages/ContractFormPage.vue',
    ROOT / 'frontend/apps/web/src/pages/contractForm/useRecordFormState.ts',
    ROOT / 'frontend/apps/web/src/pages/contractForm/onchangeNormalization.ts',
]


def _read(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(str(path))
    return path.read_text(encoding='utf-8')


def main() -> int:
    errors: list[str] = []
    try:
        backend = _read(BACKEND)
        api = _read(FRONTEND_API)
        form = '\n'.join(_read(path) for path in FORM_PATHS)
    except FileNotFoundError as exc:
        print('[FAIL] onchange_roundtrip_guard')
        print(f'- {exc}')
        return 1

    backend_markers = [
        'class ApiOnchangeHandler(BaseIntentHandler):',
        'INTENT_TYPE = "api.onchange"',
        'env_model.onchange(values, changed_fields, field_onchange)',
        '"patch": patch',
        '"modifiers_patch": modifiers_patch',
    ]
    for marker in backend_markers:
        if marker not in backend:
            errors.append(f'backend missing marker: {marker}')

    api_markers = [
        'export async function triggerOnchange(',
        "intent: 'api.onchange'",
        'changed_fields: params.changed_fields',
    ]
    for marker in api_markers:
        if marker not in api:
            errors.append(f'frontend api missing marker: {marker}')

    form_markers = [
        "import { triggerOnchange } from '../api/onchange';",
        'function markFieldChanged(name: string) {',
        'context.changedFieldSet.add(key)',
        'setTimeout(()=>void runOnchangeRoundtrip(),300)',
        'async function runOnchangeRoundtrip()',
        'const response=await triggerOnchange({',
        'const patch = response?.patch && typeof response.patch',
        # A response is written back only through its roundtrip identity: the
        # record it was computed for, its issue order, and the draft values it
        # was computed from. Without these the roundtrip can overwrite a newer
        # draft, or land on another record (frontend release finding F1-02).
        "import { buildOnchangeDraftSnapshot, createOnchangeRoundtripTicket, onchangeRecordKey, planOnchangeApplication } from './onchangeRoundtripIdentity';",
        'const ticket=createOnchangeRoundtripTicket({sequence:onchangeSequence+1',
        'onchangeSequence=ticket.sequence;',
        'const plan=planOnchangeApplication({ticket,latestSequence:onchangeSequence',
        'if(plan.dropped)return;',
        'Object.entries(plan.patch)',
    ]
    # The raw response patch must never be applied directly: `plan.patch` is the
    # superset-filtered set, so applying the response object would reintroduce
    # the overwrite this guard exists to prevent.
    forbidden_form_markers = ['Object.entries(patch)']
    for marker in form_markers:
        if marker not in form:
            errors.append(f'form missing marker: {marker}')
    for marker in forbidden_form_markers:
        if marker in form:
            errors.append(f'form applies an unverified response patch: {marker}')

    if errors:
        print('[FAIL] onchange_roundtrip_guard')
        for line in errors:
            print(f'- {line}')
        return 1

    print('[OK] onchange_roundtrip_guard')
    print(f'- backend: {BACKEND}')
    print(f'- frontend_api: {FRONTEND_API}')
    print(f'- form modules: {len(FORM_PATHS)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
