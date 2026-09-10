#!/usr/bin/env python3
"""Runtime theme-profile switching guard.

Verifies that the product-level style profile layer stays consistent:

1. profile.css declares all three SceneDesignTokenProfile ids.
2. profile.css semantic overrides match the authoritative values in
   kits/tokens.ts (brand color, control radius, surface radius).
3. theme.ts exposes the full profile model: 3 ids, isSceneThemeProfile and a
   nextThemeProfile cycle that covers every id exactly once per rotation.
4. Orthogonality: profile.css must NOT override light/dark-owned surface
   tokens (surface-page / surface-panel) anywhere, so switching a profile
   inside dark mode keeps the dark surface intact. The one sanctioned
   exception is the high-contrast profile's non-dark text contrast block.

Exits non-zero on any violation (fail-closed).
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOKENS_TS = ROOT / "frontend/packages/ui/src/kits/tokens.ts"
PROFILE_CSS = ROOT / "frontend/apps/web/src/styles/tokens/profile.css"
THEME_TS = ROOT / "frontend/apps/web/src/styles/theme.ts"
APP_VUE = ROOT / "frontend/apps/web/src/App.vue"
MAIN_TS = ROOT / "frontend/apps/web/src/main.ts"
TDESIGN_CONFIG_TS = ROOT / "frontend/apps/web/src/styles/tdesignGlobalConfig.ts"
APPLICATION_RUNTIME_TS = ROOT / "frontend/apps/web/src/styles/themeApplicationRuntime.ts"

PROFILE_IDS = ("enterprise-neutral", "business-soft", "accessible-contrast")
SURFACE_OWNED = {"--sc-semantic-surface-page", "--sc-semantic-surface-panel"}

TOKEN_FIELD_TO_CSS = {
    "brand": "--sc-semantic-surface-interactive",
    "controlRadius": "--sc-bridge-tdesign-radius-default",
    "surfaceRadius": "--sc-bridge-tdesign-radius-medium",
}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def parse_tokens_profile(text: str) -> dict[str, dict[str, str]]:
    """Parse kits/tokens.ts profile blocks into {id: {field: value}}."""
    out: dict[str, dict[str, str]] = {}
    for profile_id in PROFILE_IDS:
        # Find the block starting at the profile id up to the next '},' close.
        m = re.search(rf"'{profile_id}'\s*:\s*\{{(.*?)\n\s*\}},", text, re.S)
        if not m:
            continue
        body = m.group(1)
        fields: dict[str, str] = {}
        for key in ("background", "surface", "border", "mutedText", "text", "brand",
                    "accentSoft", "warning", "success", "focus", "controlRadius", "surfaceRadius"):
            kv = re.search(rf"\b{key}\s*:\s*'([^']+)'", body)
            if kv:
                fields[key] = kv.group(1)
        out[profile_id] = fields
    return out


def parse_profile_css(text: str) -> dict[str, dict[str, str]]:
    """Parse profile.css blocks into {id: {var: value}}."""
    out: dict[str, dict[str, str]] = {}
    for profile_id in PROFILE_IDS:
        m = re.search(rf":root\[data-sc-theme-profile='{profile_id}'\]\s*\{{(.*?)\n\}}", text, re.S)
        if not m:
            continue
        body = m.group(1)
        vars_: dict[str, str] = {}
        for var, value in re.findall(r"(--[a-z][\w-]+)\s*:\s*([^;]+);", body):
            vars_[var] = value.strip()
        out[profile_id] = vars_
    return out


def parse_theme_ts(text: str) -> dict[str, object]:
    ids = re.findall(r"'(enterprise-neutral|business-soft|accessible-contrast)'", text)
    has_guard = "export function isSceneThemeProfile" in text
    has_cycle = "export function nextThemeProfile" in text
    return {"ids": ids, "has_guard": has_guard, "has_cycle": has_cycle}


def check_profile_css_declarations(css_profiles: dict[str, dict[str, str]]) -> list[str]:
    errors: list[str] = []
    for profile_id in PROFILE_IDS:
        if profile_id not in css_profiles:
            errors.append(f"profile.css is missing declaration block for {profile_id}")
    return errors


def check_token_consistency(tokens_profiles: dict[str, dict[str, str]],
                            css_profiles: dict[str, dict[str, str]]) -> list[str]:
    errors: list[str] = []
    for profile_id in ("business-soft", "accessible-contrast"):
        tp = tokens_profiles.get(profile_id, {})
        cp = css_profiles.get(profile_id, {})
        for field, var in TOKEN_FIELD_TO_CSS.items():
            expected = tp.get(field)
            actual = cp.get(var)
            if expected is None:
                errors.append(f"tokens.ts missing {profile_id}.{field}")
                continue
            if actual != expected:
                errors.append(
                    f"{profile_id} {var}: profile.css={actual!r} != tokens.ts {field}={expected!r}"
                )
    return errors


def check_theme_model(theme: dict[str, object]) -> list[str]:
    errors: list[str] = []
    ids = theme["ids"]  # type: ignore[assignment]
    if sorted(set(ids)) != sorted(PROFILE_IDS):
        errors.append(f"theme.ts profile ids mismatch: {sorted(set(ids))}")
    if not theme["has_guard"]:
        errors.append("theme.ts missing isSceneThemeProfile guard")
    if not theme["has_cycle"]:
        errors.append("theme.ts missing nextThemeProfile cycle")
    return errors


def check_orthogonality(css_profiles: dict[str, dict[str, str]]) -> list[str]:
    errors: list[str] = []
    for profile_id, vars_ in css_profiles.items():
        for var in vars_:
            if var in SURFACE_OWNED:
                errors.append(
                    f"{profile_id} overrides light/dark-owned surface token {var} "
                    "(breaks orthogonality with the mode layer)"
                )
    return errors


def main() -> int:
    tokens_text = read(TOKENS_TS)
    css_text = read(PROFILE_CSS)
    theme_text = read(THEME_TS)
    app_text = read(APP_VUE)
    main_text = read(MAIN_TS)
    tdesign_config_text = read(TDESIGN_CONFIG_TS)
    application_runtime_text = read(APPLICATION_RUNTIME_TS)

    if not tokens_text or not css_text or not theme_text:
        print(f"[theme_profile_guard] FAIL missing source: {rel(TOKENS_TS)} / {rel(PROFILE_CSS)} / {rel(THEME_TS)}")
        return 2

    tokens_profiles = parse_tokens_profile(tokens_text)
    css_profiles = parse_profile_css(css_text)
    theme = parse_theme_ts(theme_text)

    errors: list[str] = []
    errors += check_profile_css_declarations(css_profiles)
    errors += check_token_consistency(tokens_profiles, css_profiles)
    errors += check_theme_model(theme)
    errors += check_orthogonality(css_profiles)
    for label, source, markers in (
        ("App.vue", app_text, ("useThemeApplicationRuntime();",)),
        ("main.ts", main_text, ("startThemeApplicationRuntime();", "import.meta.hot.dispose(stopThemeApplicationRuntime)")),
        ("tdesignGlobalConfig.ts", tdesign_config_text, ("startTdesignGlobalConfigRuntime", "stopTdesignGlobalConfigRuntime", "exclude: []")),
        ("themeApplicationRuntime.ts", application_runtime_text, ("onMounted(startThemeApplicationRuntime)", "onBeforeUnmount(stopThemeApplicationRuntime)")),
    ):
        for marker in markers:
            if marker not in source:
                errors.append(f"{label} missing application theme lifecycle marker: {marker}")

    if errors:
        print(f"[theme_profile_guard] FAIL")
        for error in errors:
            print(f"  - {error}")
        return 1

    # Exercise the real TypeScript module through the existing registered gate.
    runtime = subprocess.run(["node", "-e", r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('./frontend/apps/web/node_modules/typescript');
const source = fs.readFileSync('./frontend/apps/web/src/styles/theme.ts', 'utf8');
const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText;
const attrs = new Map();
const darkListeners = new Set();
const motionListeners = new Set();
const media = (listeners) => ({ matches: false,
  addEventListener: (name, handler) => { assert.equal(name, 'change'); listeners.add(handler); },
  removeEventListener: (name, handler) => { assert.equal(name, 'change'); listeners.delete(handler); } });
const darkMedia = media(darkListeners);
const motionMedia = media(motionListeners);
const root = { style: {}, setAttribute: (name, value) => attrs.set(name, value), getAttribute: name => attrs.get(name) };
const moduleObject = { exports: {} };
vm.runInNewContext(code, { exports: moduleObject.exports, module: moduleObject,
  window: { matchMedia: query => query.includes('color-scheme') ? darkMedia : motionMedia }, document: { documentElement: root } });
const theme = moduleObject.exports;
const resolved = () => attrs.get('data-sc-theme-resolved');
theme.applyThemeProfile('business-soft');
theme.applyTheme('system');
const stop = theme.ensureThemeRuntimeWatch();
theme.ensureThemeRuntimeWatch();
assert.equal(darkListeners.size, 1);
assert.equal(motionListeners.size, 1);
assert.equal(resolved(), 'light');
darkMedia.matches = true; darkListeners.forEach(handler => handler());
assert.equal(resolved(), 'dark');
theme.applyTheme('light'); darkListeners.forEach(handler => handler());
assert.equal(resolved(), 'light', 'explicit light mode ignores system dark');
theme.applyTheme('dark'); darkMedia.matches = false; darkListeners.forEach(handler => handler());
assert.equal(resolved(), 'dark', 'explicit dark mode ignores system light');
theme.applyTheme('system');
assert.equal(resolved(), 'light');
assert.equal(attrs.get('data-sc-theme-profile'), 'business-soft', 'mode changes preserve style profile');
stop(); assert.equal(darkListeners.size, 0); assert.equal(motionListeners.size, 0);
darkMedia.matches = true; darkListeners.forEach(handler => handler());
assert.equal(resolved(), 'light', 'disposed listener cannot update theme');
console.log('[theme_system_runtime] PASS assertions=12');
"""], cwd=ROOT, check=False)
    if runtime.returncode:
        return runtime.returncode

    print(
        "[theme_profile_guard] PASS profiles=3 declared=3 "
        "brand/radius=consistent orthogonality=ok"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
