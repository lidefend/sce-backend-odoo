#!/usr/bin/env python3
"""Fail closed when product UI bypasses the official icon adapter."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = ROOT / "frontend/apps/web/src"
SC_ICON = SOURCE_ROOT / "components/design-system/ScIcon.vue"
SC_ICON_MODEL = SOURCE_ROOT / "components/design-system/scIcon.ts"
UI_PACKAGE = ROOT / "frontend/packages/ui/package.json"
UI_ICONS = ROOT / "frontend/packages/ui/src/icons.ts"

FORBIDDEN_VISUAL_GLYPHS = ("📁", "📄", "📊", "📕", "📘", "📗", "📙", "🗜", "🖼", "🎵", "🎬", "📎", "💬", "📋", "🔗", "↩", "▾", "▸")
FORBIDDEN_CLASS_DRIVERS = (
    "['native-action-icon',",
    "['native-smart-action__icon',",
    "['native-action-overflow__icon',",
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def validate() -> list[str]:
    failures: list[str] = []
    component = read(SC_ICON)
    model = read(SC_ICON_MODEL)
    package = read(UI_PACKAGE)
    bridge = read(UI_ICONS)

    for marker in ('<component', 'data-icon-source="tdesign"', 'resolveScIconComponent'):
        if marker not in component:
            failures.append(f"ScIcon missing official adapter marker: {marker}")
    if "<svg" in component or "<path" in component or "pathData" in component:
        failures.append("ScIcon must not maintain handwritten SVG path data")
    if "satisfies Record<ScIconName, Component>" not in model:
        failures.append("ScIcon semantic map must be exhaustive at compile time")
    if '"./icons": "./src/icons.ts"' not in package or '"tdesign-icons-vue-next": "0.4.9"' not in package:
        failures.append("@sc/ui must expose and exact-pin the official icon bridge")
    if "from 'tdesign-icons-vue-next'" not in bridge or "from 'tdesign-icons-vue-next/" in bridge:
        failures.append("official icon bridge must consume the package public root API")

    for path in sorted(SOURCE_ROOT.rglob("*")):
        if path.suffix not in {".ts", ".vue"}:
            continue
        text = read(path)
        for glyph in FORBIDDEN_VISUAL_GLYPHS:
            if glyph in text:
                failures.append(f"manual visual glyph {glyph!r} remains in {path.relative_to(ROOT)}")
        for marker in FORBIDDEN_CLASS_DRIVERS:
            if marker in text:
                failures.append(f"class-driven icon bypass remains in {path.relative_to(ROOT)}: {marker}")
    return failures


if __name__ == "__main__":
    errors = validate()
    if errors:
        print("[frontend_official_icon_resource_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print("[frontend_official_icon_resource_guard] PASS source=tdesign-icons-vue-next manual_glyphs=0 handwritten_paths=0")
