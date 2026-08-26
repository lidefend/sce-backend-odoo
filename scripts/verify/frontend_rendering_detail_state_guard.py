#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INVENTORY_PATH = ROOT / "scripts/audit/generate_frontend_rendering_detail_inventory.py"
SPEC = importlib.util.spec_from_file_location("rendering_detail_inventory", INVENTORY_PATH)
assert SPEC and SPEC.loader
INVENTORY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INVENTORY)

LEGACY_PRIVATE_STATE_DOM = {
    "frontend/apps/web/src/layouts/AppShell.vue": ('<p v-if="recordContextSearching"', '<p v-else-if="recordContextError"'),
    "frontend/apps/web/src/components/GlobalMessagePanel.vue": ('class="global-message__empty sc-empty"', 'class="global-message__error sc-alert'),
    "frontend/apps/web/src/components/action/UnsupportedActionSurface.vue": ('<section class="unsupported-action-surface" role="alert">',),
    "frontend/apps/web/src/components/page/BlockRenderer.vue": ('<article v-else class="block-fallback">',),
    "frontend/apps/web/src/pages/contractForm/ContractFormDriverHost.vue": ('<section\n    v-if="error || !renderModel"', '<p v-else class="canonical-form-activity-empty">'),
    "frontend/apps/web/src/components/template/X2ManyRelationRenderer.vue": ('<p v-else class="relation-readonly-empty"', '<p v-if="adapter.showOne2manyErrors'),
    "frontend/apps/web/src/pages/contractForm/NativeCollaborationPanel.vue": ('<p v-if="unavailableMessage"', '<p v-if="chatterError"'),
    "frontend/apps/web/src/pages/contractForm/ProfessionalCollaborationTimeline.vue": (),
}


def validate(read_text=lambda source: (ROOT / source).read_text(encoding="utf-8")) -> list[str]:
    failures: list[str] = []
    for source, (_, requirements) in INVENTORY.OWNED_BINDINGS.items():
        text = read_text(source)
        binding_failures = INVENTORY.component_binding_failures(text, requirements)
        for failure in binding_failures:
            failures.append(f"state surface remains ungoverned: {source}: {failure}")
        for legacy in LEGACY_PRIVATE_STATE_DOM.get(source, ()):
            if legacy in text:
                failures.append(f"state surface retains private DOM: {source}: {legacy}")
    return failures


def main() -> int:
    failures = validate()
    if failures:
        print("[frontend_rendering_detail_state_guard] FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(f"[frontend_rendering_detail_state_guard] PASS surfaces={len(INVENTORY.OWNED_BINDINGS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
