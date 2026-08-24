#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def validate(read_text=lambda path: (ROOT / path).read_text(encoding="utf-8")) -> list[str]:
    failures: list[str] = []
    registry = read_text("frontend/apps/web/src/app/presentation/professionalComponentRegistry.ts")
    presenter = read_text("frontend/apps/web/src/app/presentation/contractFormPresenter.ts")
    renderer = read_text("frontend/apps/web/src/components/template/FormSection.vue")
    canonical_renderer = read_text("frontend/apps/web/src/pages/contractForm/canonicalFormRenderer.ts")
    required_registration_fields = (
        "componentKey", "semanticType", "supportedFieldTypes", "supportedPresentationModes",
        "supportedRenderProfiles", "requiredCapabilities", "renderer", "fallback", "readiness",
    )
    for marker in required_registration_fields:
        if marker not in registry:
            failures.append(f"registry missing required field {marker}")
    for marker in (
        "PROFESSIONAL_COMPONENT_UNREGISTERED", "PROFESSIONAL_COMPONENT_FIELD_TYPE_MISMATCH",
        "PROFESSIONAL_COMPONENT_PRESENTATION_MODE_MISMATCH", "PROFESSIONAL_COMPONENT_RENDER_PROFILE_MISMATCH",
        "PROFESSIONAL_COMPONENT_CAPABILITY_MISSING",
    ):
        if marker not in registry:
            failures.append(f"registry missing fail-closed invariant {marker}")
    if "resolveProfessionalComponent({" not in presenter:
        failures.append("Presenter does not resolve every canonical field through the registry")
    if "componentResolution," not in presenter:
        failures.append("Presenter does not retain the registry resolution")
    for marker in ("data-component-key", "data-component-readiness", "data-component-renderer", "data-component-fallback"):
        if marker not in renderer:
            failures.append(f"FormSection missing semantic marker {marker}")
    if "componentResolution" not in canonical_renderer:
        failures.append("canonical renderer does not forward registry resolution")
    forbidden = ("payment.request", "project.project", "action_id", "menu_id", "付款", "项目")
    for marker in forbidden:
        if marker in registry:
            failures.append(f"registry contains forbidden product special case {marker}")
    return failures


def main() -> int:
    failures = validate()
    if failures:
        print("[frontend_professional_component_registry_guard] FAIL")
        for failure in failures:
            print(f" - {failure}")
        return 1
    print("[frontend_professional_component_registry_guard] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
