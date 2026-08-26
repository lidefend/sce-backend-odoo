#!/usr/bin/env python3
"""Inventory the boundary between the installed TDesign system and SC styling."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "frontend/packages/ui/package.json"
THEME = ROOT / "frontend/packages/ui/src/kits/tdesign/theme.css"
WEB = ROOT / "frontend/apps/web/src"
UI = ROOT / "frontend/packages/ui/src"
OUTPUT = ROOT / "docs/frontend_productization/rendering-detail/official-design-alignment-inventory-v1.json"

TOKEN_RE = re.compile(r"--td-[a-z0-9-]+")
SELECTOR_RE = re.compile(r"(?P<selector>[^{}]+)\{(?P<body>[^{}]*)\}", re.S)
APPEARANCE_RE = re.compile(r"data-appearance=['\"](?P<name>[^'\"]+)['\"]")
VISUAL_LITERAL_RE = re.compile(r"(?<![\w-])(?:#[0-9a-fA-F]{3,8}\b|rgba?\([^)]*\)|-?\d+(?:\.\d+)?px\b)")
VENDOR_CLASS_RE = re.compile(r"\.t-[a-z0-9_-]+")
SC_ROOT_RE = re.compile(r"(?:\.sc-[a-z0-9_-]+|\[data-semantic-component(?:=|\]))")
STYLE_BLOCK_RE = re.compile(r"<style\b[^>]*>(?P<body>.*?)</style>", re.S | re.I)


def encode(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def locked_version() -> str:
    package = json.loads(PACKAGE.read_text(encoding="utf-8"))
    return str(package["dependencies"]["tdesign-vue-next"])


def installed_style(version: str) -> Path:
    roots = sorted((ROOT / "frontend/node_modules/.pnpm").glob(f"tdesign-vue-next@{version}_*/node_modules/tdesign-vue-next"))
    if len(roots) != 1:
        raise RuntimeError(f"expected one installed tdesign-vue-next@{version}, found {len(roots)}")
    style = roots[0] / "es/style/index.css"
    if not style.is_file():
        raise RuntimeError(f"installed official stylesheet missing: {style}")
    return style


def normalized_selector(value: str) -> str:
    return " ".join(value.split())


def selector_has_descendant_vendor_target(selector: str) -> bool:
    """Allow a TDesign class on the Sc root, reject internal descendant coupling."""
    for part in selector.split(","):
        part = normalized_selector(part)
        if not VENDOR_CLASS_RE.search(part):
            continue
        first_combinator = re.search(r"\s[>+~]?\s*", part)
        root = part if first_combinator is None else part[: first_combinator.start()]
        tail = "" if first_combinator is None else part[first_combinator.start() :]
        if not SC_ROOT_RE.search(root) or VENDOR_CLASS_RE.search(tail):
            return True
    return False


def appearance_consumers(name: str) -> list[str]:
    needle = re.compile(rf"['\"]{re.escape(name)}['\"]")
    consumers = []
    for path in sorted((*WEB.rglob("*.vue"), *WEB.rglob("*.ts"))):
        if needle.search(path.read_text(encoding="utf-8", errors="ignore")):
            consumers.append(path.relative_to(ROOT).as_posix())
    return consumers


def formal_style_sources() -> list[tuple[Path, str, int]]:
    """Return every formal P0/P1 style carrier with its source line offset."""
    sources: list[tuple[Path, str, int]] = []
    for root in (WEB, UI):
        for path in sorted(root.rglob("*.css")):
            sources.append((path, path.read_text(encoding="utf-8", errors="ignore"), 0))
        for path in sorted(root.rglob("*.vue")):
            text = path.read_text(encoding="utf-8", errors="ignore")
            for match in STYLE_BLOCK_RE.finditer(text):
                sources.append((path, match.group("body"), text.count("\n", 0, match.start("body"))))
    return sources


def build_inventory() -> dict[str, object]:
    version = locked_version()
    official_path = installed_style(version)
    official_text = official_path.read_text(encoding="utf-8")
    theme_text = THEME.read_text(encoding="utf-8")
    official_tokens = sorted(set(TOKEN_RE.findall(official_text)))
    project_tokens = sorted(set(TOKEN_RE.findall(theme_text)))
    unknown_tokens = sorted(set(project_tokens) - set(official_tokens))

    style_sources = formal_style_sources()
    internal_selector_gaps: list[dict[str, object]] = []
    visual_literal_gaps: list[dict[str, object]] = []
    appearances: dict[str, dict[str, object]] = {}
    for path, style_text, line_offset in style_sources:
        for match in SELECTOR_RE.finditer(style_text):
            selector = normalized_selector(match.group("selector"))
            if selector_has_descendant_vendor_target(selector):
                internal_selector_gaps.append({
                    "file": path.relative_to(ROOT).as_posix(),
                    "line": line_offset + style_text.count("\n", 0, match.start()) + 1,
                    "selector": selector,
                    "status": "legacy_override_gap",
                })

    for match in SELECTOR_RE.finditer(theme_text):
        selector = normalized_selector(match.group("selector"))
        body = match.group("body")
        line = theme_text.count("\n", 0, match.start()) + 1
        literal_source = re.sub(r"calc\([^)]*var\([^)]*\)[^)]*\)", "", body)
        literals = sorted(set(VISUAL_LITERAL_RE.findall(literal_source)))
        if literals:
            visual_literal_gaps.append({"line": line, "selector": selector, "literals": literals, "status": "legacy_override_gap"})
        for appearance in APPEARANCE_RE.findall(selector):
            row = appearances.setdefault(appearance, {"appearance": appearance, "selectors": [], "consumers": []})
            row["selectors"].append(selector)

    for name, row in appearances.items():
        row["selectors"] = sorted(set(row["selectors"]))
        row["consumers"] = appearance_consumers(name)
        row["status"] = "registered_product_variance" if row["consumers"] else "orphaned_product_variance"

    payload = {
        "schemaVersion": "frontend.official-design-alignment.inventory.v1",
        "scope": "formal P0/P1 frontend TDesign driver and product adapter styling",
        "authority": {
            "library": "tdesign-vue-next",
            "lockedVersion": version,
            "officialStylesheet": official_path.relative_to(ROOT).as_posix(),
            "projectThemeBridge": THEME.relative_to(ROOT).as_posix(),
            "officialCustomizationRule": "inherit official defaults; customize only through installed public CSS variables; internal vendor selectors require removal",
        },
        "themeTokens": {
            "officialPublicTokens": official_tokens,
            "projectPublicTokenOverrides": project_tokens,
            "unknownProjectTokenOverrides": unknown_tokens,
            "inheritedOfficialTokenCount": len(set(official_tokens) - set(project_tokens)),
        },
        "internalVendorSelectorGaps": internal_selector_gaps,
        "visualLiteralGaps": visual_literal_gaps,
        "productAppearanceVariants": sorted(appearances.values(), key=lambda row: str(row["appearance"])),
        "summary": {
            "officialPublicTokenCount": len(official_tokens),
            "projectPublicTokenOverrideCount": len(project_tokens),
            "unknownProjectTokenOverrideCount": len(unknown_tokens),
            "internalVendorSelectorGapCount": len(internal_selector_gaps),
            "visualLiteralGapCount": len(visual_literal_gaps),
            "productAppearanceVariantCount": len(appearances),
            "orphanedProductAppearanceVariantCount": sum(row["status"] == "orphaned_product_variance" for row in appearances.values()),
            "formalStyleSourceCount": len(style_sources),
        },
        "completionRule": "unknownProjectTokenOverrideCount=0; internalVendorSelectorGapCount=0; visualLiteralGapCount=0; orphanedProductAppearanceVariantCount=0",
        "excludedScopes": ["Contract V2", "permissions", "routes", "task/workspace authority", "P3 low-code designer styling"],
        "inputDigest": digest((official_text + "\n" + "\n".join(
            f"{path.relative_to(ROOT).as_posix()}\n{style_text}" for path, style_text, _ in style_sources
        )).encode()),
    }
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = encode(build_inventory())
    output = args.output.resolve()
    if args.check:
        if not output.is_file() or output.read_text(encoding="utf-8") != payload:
            print(f"[frontend_official_design_alignment_inventory] FAIL stale={output}")
            return 1
        report = json.loads(payload)
        print(f"[frontend_official_design_alignment_inventory] PASS summary={report['summary']}")
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(payload, encoding="utf-8")
    print(f"[frontend_official_design_alignment_inventory] wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
