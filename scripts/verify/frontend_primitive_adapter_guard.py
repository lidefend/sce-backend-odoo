#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
DESIGN_SYSTEM = ROOT / "frontend/apps/web/src/components/design-system"
INDEX = DESIGN_SYSTEM / "index.ts"
BRIDGE = DESIGN_SYSTEM / "tdesignPrimitiveBridge.ts"

PRIMITIVES = (
    "ScButton", "ScInput", "ScSelect", "ScDialog", "ScDrawer", "ScTabs", "ScTable",
    "ScBadge", "ScTooltip", "ScDropdown", "ScFormField", "ScLoading", "ScEmptyState", "ScErrorState",
)
FORBIDDEN_PRIVATE_TDESIGN = re.compile(r"tdesign-vue-next/(?:lib|cjs|src)/")
FORBIDDEN_BUSINESS_IDENTITY = re.compile(
    r"\b(?:project\.project|payment\.request|construction\.contract|action_id|menu_id|role_code)\b",
    re.IGNORECASE,
)


def validate(root: Path = ROOT) -> list[str]:
    design = root / "frontend/apps/web/src/components/design-system"
    index = (design / "index.ts").read_text(encoding="utf-8") if (design / "index.ts").is_file() else ""
    bridge = (design / "tdesignPrimitiveBridge.ts").read_text(encoding="utf-8") if (design / "tdesignPrimitiveBridge.ts").is_file() else ""
    errors: list[str] = []

    for component in PRIMITIVES:
        source = design / f"{component}.vue"
        if not source.is_file():
            errors.append(f"missing primitive source: {source.relative_to(root)}")
            continue
        text = source.read_text(encoding="utf-8")
        if f"data-semantic-component=\"{component}\"" not in text and f"semanticPrimitiveIdentity('{component}')" not in text:
            errors.append(f"{component} missing exact semantic component identity")
        if "data-semantic-layer=\"primitive\"" not in text and "semanticPrimitiveIdentity(" not in text:
            errors.append(f"{component} missing primitive layer identity")
        if FORBIDDEN_PRIVATE_TDESIGN.search(text):
            errors.append(f"{component} imports a private TDesign path")
        if FORBIDDEN_BUSINESS_IDENTITY.search(text):
            errors.append(f"{component} contains business-specific identity")
        if f"export {{ default as {component} }}" not in index:
            errors.append(f"index.ts does not export {component}")

    for modal in ("ScDialog", "ScDrawer"):
        text = (design / f"{modal}.vue").read_text(encoding="utf-8") if (design / f"{modal}.vue").is_file() else ""
        if "useModalLifecycle" not in text or 'role="dialog"' not in text or 'aria-modal="true"' not in text:
            errors.append(f"{modal} must use the shared modal lifecycle and dialog semantics")

    input_text = (design / "ScInput.vue").read_text(encoding="utf-8") if (design / "ScInput.vue").is_file() else ""
    if "<input" not in input_text or ':aria-describedby="describedBy"' not in input_text or ':aria-invalid=' not in input_text:
        errors.append("ScInput must place accessible state on the native input control")

    if not bridge:
        errors.append("missing TDesign primitive bridge")
    else:
        if FORBIDDEN_PRIVATE_TDESIGN.search(bridge):
            errors.append("TDesign primitive bridge imports a private path")
        if "tdesign-vue-next/es/" not in bridge:
            errors.append("TDesign primitive bridge does not use public component entrypoints")
        for path in design.glob("*.vue"):
            text = path.read_text(encoding="utf-8")
            if "tdesign-vue-next" in text:
                errors.append(f"{path.name} bypasses the TDesign primitive bridge")

    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("[frontend_primitive_adapter_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"[frontend_primitive_adapter_guard] PASS components={len(PRIMITIVES)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
