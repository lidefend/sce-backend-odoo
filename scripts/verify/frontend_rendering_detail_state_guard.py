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


# Global rendering-detail accessibility contracts: cross-surface guarantees
# that are not bound to a single owned surface but must never regress.
GLOBAL_ACCESSIBILITY_CONTRACTS = (
    (
        "frontend/apps/web/src/styles/product-patterns.css",
        "Global reduced-motion fallback",
        "@media (prefers-reduced-motion: reduce)",
    ),
    (
        "frontend/apps/web/src/styles/product-patterns.css",
        "global focus-visible rule",
        ":is(a, button, input, select, textarea, [tabindex]):focus-visible",
    ),
)


# Global shell density contracts: authoritative shell metrics must be consumed
# by their owning surfaces (never a mis-scoped sibling token such as the
# collection toolbar height standing in for the top bar height).
GLOBAL_SHELL_DENSITY_CONTRACTS = (
    (
        "frontend/apps/web/src/layouts/AppShell.css",
        "topbar height",
        "min-height: var(--sc-shell-topbar-height)",
    ),
    (
        "frontend/apps/web/src/components/design-system/ScAside.vue",
        "sidebar width",
        "var(--sc-shell-sidebar-width)",
    ),
)


# Component authority density tokens must be defined ONLY in the tokens layer.
# Pages express density variants through product-level tokens
# (--sc-product-table-*) so shared components keep the authoritative density.
COMPONENT_AUTHORITY_DENSITY_TOKENS = ("--sc-table-row-height:", "--sc-table-header-height:")
TOKENS_LAYER_PREFIX = "frontend/apps/web/src/styles/tokens/"


def authority_density_token_violations(sources: list[tuple[str, str]] | None = None) -> list[str]:
    if sources is None:
        sources = []
        for css in sorted((ROOT / "frontend/apps/web/src").rglob("*.css")):
            rel = css.relative_to(ROOT).as_posix()
            if rel.startswith(TOKENS_LAYER_PREFIX):
                continue
            sources.append((rel, css.read_text(encoding="utf-8")))
    violations: list[str] = []
    for rel, text in sources:
        for token in COMPONENT_AUTHORITY_DENSITY_TOKENS:
            if token in text:
                violations.append(f"component authority density token overridden outside tokens layer: {rel}: {token}")
    return violations


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
    for source, label, marker in GLOBAL_ACCESSIBILITY_CONTRACTS + GLOBAL_SHELL_DENSITY_CONTRACTS:
        try:
            text = read_text(source)
        except (KeyError, FileNotFoundError):
            # Injected read_text mocks cover OWNED_BINDINGS only; fall back to
            # the real file so global contracts are always checked.
            text = (ROOT / source).read_text(encoding="utf-8")
        if marker not in text:
            failures.append(f"global rendering-detail contract missing: {source}: {label}")
    failures.extend(authority_density_token_violations())
    return failures


def main() -> int:
    failures = validate()
    if failures:
        print("[frontend_rendering_detail_state_guard] FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(
        f"[frontend_rendering_detail_state_guard] PASS surfaces={len(INVENTORY.OWNED_BINDINGS)} "
        f"accessibility_contracts={len(GLOBAL_ACCESSIBILITY_CONTRACTS)} "
        f"shell_density_contracts={len(GLOBAL_SHELL_DENSITY_CONTRACTS)} "
        f"authority_density_tokens={len(COMPONENT_AUTHORITY_DENSITY_TOKENS)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
