#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FILES = {
    "dialog": ROOT / "frontend/apps/web/src/components/design-system/ScDialog.vue",
    "drawer": ROOT / "frontend/apps/web/src/components/design-system/ScDrawer.vue",
    "lifecycle": ROOT / "frontend/apps/web/src/composables/useModalLifecycle.ts",
    "action_view": ROOT / "frontend/apps/web/src/views/ActionView.vue",
    "attachment": ROOT / "frontend/apps/web/src/components/attachment/AttachmentViewer.vue",
    "messages": ROOT / "frontend/apps/web/src/components/GlobalMessagePanel.vue",
    "mobile_navigation": ROOT / "frontend/apps/web/src/components/product-shell/ProductMobileNavigationDrawer.vue",
}


def validate(sources: dict[str, str] | None = None) -> list[str]:
    values = sources or {key: path.read_text(encoding="utf-8") for key, path in FILES.items()}
    failures: list[str] = []
    drivers = {"dialog": "TDesignDialog", "drawer": "TDesignDrawer"}
    for key in ("dialog", "drawer"):
        source = values[key]
        markers = [f"<{drivers[key]}", ':close-on-esc-keydown="false"', ':close-on-overlay-click="dismissible && closeOnBackdrop"', ':prevent-scroll-through="false"', 'useModalLifecycle', 'aria-modal="true"', ":data-state=\"open ? 'open' : 'closed'\"", ':data-dismissible="dismissible"', "inheritAttrs: false", "@close=\"emit('close')\""]
        if key == "dialog":
            markers.append(':destroy-on-close="true"')
        for marker in markers:
            if marker not in source:
                failures.append(f"{key} lost canonical overlay lifecycle marker: {marker}")
    lifecycle = values["lifecycle"]
    for marker in ("bodyLockDepth", "restoreOpener", "focusInitial", "resolveModalKeyboardAction", "closeOnEscape"):
        if marker not in lifecycle:
            failures.append(f"modal lifecycle lost invariant: {marker}")
    consumers = {
        "action_view": ("<ScDialog", "business-category-picker-backdrop", 'role="dialog"'),
        "attachment": ("<ScDialog", "attachment-viewer-backdrop", "useModalLifecycle"),
        "messages": ("<ScDrawer", "global-message__backdrop", '<aside v-if="open"'),
    }
    for key, (required, forbidden_one, forbidden_two) in consumers.items():
        source = values[key]
        if required not in source:
            failures.append(f"{key} does not consume canonical overlay primitive: {required}")
        for marker in (forbidden_one, forbidden_two):
            if marker in source:
                failures.append(f"{key} retains parallel overlay authority: {marker}")
    messages = values["messages"]
    for marker in ("<ScButton", "<ScInput", "<ScTextarea"):
        if marker not in messages:
            failures.append(f"messages drawer bypasses governed collaboration control: {marker}")
    for marker in ("<textarea", "<input"):
        if marker in messages:
            failures.append(f"messages drawer retains raw generic control: {marker}")
    if "useModalLifecycle" not in values["mobile_navigation"]:
        failures.append("mobile navigation lost shared modal lifecycle regression coverage")
    return failures


if __name__ == "__main__":
    errors = validate()
    if errors:
        print("[frontend_overlay_lifecycle_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print("[frontend_overlay_lifecycle_guard] PASS canonical=3 consumers=3 formal_gaps=0")
