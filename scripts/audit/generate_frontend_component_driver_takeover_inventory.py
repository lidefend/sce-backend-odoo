#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "frontend/apps/web/src"
DESIGN = WEB / "components/design-system"
UI = ROOT / "frontend/packages/ui"
PACKAGE = UI / "node_modules/tdesign-vue-next/package.json"
OFFICIAL_ROOT = UI / "node_modules/tdesign-vue-next/esm"
OUTPUT = ROOT / "docs/frontend_productization/rendering-detail/component-driver-takeover-inventory-v1.json"
OWNERSHIP = json.loads((ROOT / "docs/frontend_productization/rendering-detail/rendering-surface-ownership-v1.json").read_text(encoding="utf-8"))
P3_OWNER = OWNERSHIP["owners"]["p3-low-code-administration"]
P3_FILES = set(P3_OWNER.get("sources", []))
P3_PREFIXES = tuple(P3_OWNER.get("prefixes", []))

INTERNAL_DIRS = {"_chunks", "common", "common-components", "config-provider", "locale", "style"}
REQUIRED_DRIVERS = {
    "alert", "auto-complete", "badge", "button", "card", "checkbox", "collapse", "date-picker",
    "descriptions", "dialog", "drawer", "dropdown", "empty", "form", "input", "input-number",
    "input-adornment", "layout", "list", "loading", "menu", "pagination", "progress", "radio", "select", "skeleton",
    "space", "steps", "table", "tabs", "tag", "textarea", "timeline",
    "tooltip", "upload",
}
NOT_REQUIRED_DECISIONS = {
    "popconfirm": "Destructive business actions use the governed confirmation-dialog authority; a local popconfirm must not bypass it.",
    "switch": "Contract V2 exposes persisted boolean form values, represented by checkbox; it has no immediate-setting toggle semantic.",
    "time-picker": "Contract V2 exposes date and datetime fields, represented by DatePicker; it has no standalone time-only field type.",
}
RAW_BEHAVIOR = re.compile(r"<(button|input|select|textarea|table|dialog|details)\b", re.I)
RAW_BEHAVIOR_APIS = {
    "window.confirm": re.compile(r"(?:\bwindow\s*\.\s*confirm|(?<![.\w])confirm)\s*\("),
    "window.alert": re.compile(r"(?:\bwindow\s*\.\s*alert|(?<![.\w])alert)\s*\("),
    "window.prompt": re.compile(r"(?:\bwindow\s*\.\s*prompt|(?<![.\w])prompt)\s*\("),
}
TDESIGN_TAG = re.compile(r"<TDesign([A-Za-z0-9]+)\b")
DIRECT_IMPORT = re.compile(r"from\s+['\"]tdesign-vue-next(?:/[^'\"]*)?['\"]")
SC_TAG = re.compile(r"<((?:Sc|Product)[A-Z][A-Za-z0-9]+)\b")
DRIVER_FAMILY = {
    "CollapsePanel": "Collapse",
    "DescriptionsItem": "Descriptions",
    "FormItem": "Form",
    "ListItem": "List",
    "MenuItem": "Menu",
    "StepItem": "Steps",
    "Submenu": "Menu",
    "TimelineItem": "Timeline",
}


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def digest(paths: list[Path], extra: str = "") -> str:
    output = hashlib.sha256()
    if extra:
        output.update(extra.encode())
        output.update(b"\0")
    for path in sorted(set(paths)):
        output.update(relative(path).encode())
        output.update(b"\0")
        output.update(path.read_bytes())
        output.update(b"\0")
    return output.hexdigest()


def official_components() -> list[str]:
    return sorted(path.name for path in OFFICIAL_ROOT.iterdir() if path.is_dir() and path.name not in INTERNAL_DIRS)


def sources() -> list[Path]:
    return sorted(path for path in WEB.rglob("*") if path.suffix in {".vue", ".ts", ".js"} and path.is_file())


def is_p3(source: str) -> bool:
    return source in P3_FILES or source.startswith(P3_PREFIXES)


def build_inventory() -> dict[str, object]:
    package = json.loads(PACKAGE.read_text(encoding="utf-8"))
    source_files = sources()
    bridge_files = [UI / "src/primitives.ts", DESIGN / "tdesignPrimitiveBridge.ts"]
    all_inputs = [Path(__file__), ROOT / "docs/frontend_productization/rendering-detail/rendering-surface-ownership-v1.json", *bridge_files, *source_files]
    ui_bridge = bridge_files[0].read_text(encoding="utf-8")
    web_bridge = bridge_files[1].read_text(encoding="utf-8")
    adapter_rows: dict[str, list[dict[str, object]]] = {}
    consumer_counts: dict[str, int] = {}
    direct_imports: list[str] = []
    raw_surfaces: list[dict[str, object]] = []

    for path in source_files:
        text = path.read_text(encoding="utf-8", errors="replace")
        source = relative(path)
        if DIRECT_IMPORT.search(text):
            direct_imports.append(source)
        if path.suffix == ".vue":
            for driver in sorted(set(TDESIGN_TAG.findall(text))):
                driver = DRIVER_FAMILY.get(driver, driver)
                semantic_adapters = set(SC_TAG.findall(text))
                if "/components/design-system/Sc" in source:
                    semantic_adapters.add(path.stem)
                if source == "frontend/apps/web/src/components/MenuTree.vue":
                    semantic_adapters.add("MenuTree")
                adapter_rows.setdefault(driver, []).append({"source": source, "semanticAdapters": sorted(semantic_adapters)})
            if not is_p3(source) and "/components/design-system/" not in source and source not in {
                "frontend/apps/web/src/components/MenuTree.vue",
                "frontend/apps/web/src/components/product-shell/CanonicalNavigationMenuNode.vue",
            }:
                tags = sorted(set(match.group(1).lower() for match in RAW_BEHAVIOR.finditer(text)))
                api_text = re.sub(r"\b(?:async\s+)?function\s+(?:confirm|alert|prompt)\s*\(", "", text)
                tags.extend(name for name, pattern in RAW_BEHAVIOR_APIS.items() if pattern.search(api_text))
                tags = sorted(set(tags))
                if tags:
                    raw_surfaces.append({"source": source, "rawBehaviorTags": tags, "assessment": "unassessed"})
        for adapter in set(SC_TAG.findall(text)):
            if f"/{adapter}.vue" not in source:
                consumer_counts[adapter] = consumer_counts.get(adapter, 0) + len(re.findall(fr"<{re.escape(adapter)}\b", text))
        if "<MenuTree" in text and source != "frontend/apps/web/src/components/MenuTree.vue":
            consumer_counts["MenuTree"] = consumer_counts.get("MenuTree", 0) + text.count("<MenuTree")

    rows: list[dict[str, object]] = []
    for component in official_components():
        pascal = "".join(part.capitalize() for part in component.split("-"))
        exports = sorted(set(re.findall(fr"\bTDesign{pascal}[A-Za-z0-9]*\b", ui_bridge)))
        web_exports = [name for name in exports if name in web_bridge]
        adapters = adapter_rows.get(pascal, [])
        adapter_names = sorted({name for row in adapters for name in row["semanticAdapters"]})
        required = component in REQUIRED_DRIVERS
        consumer_count = sum(consumer_counts.get(name, 0) for name in adapter_names)
        if not required:
            status = "not_required"
        elif exports and web_exports and adapters:
            status = "adapter_present" if consumer_count else "adapter_unconsumed"
        elif exports and web_exports:
            status = "bridge_only"
        else:
            status = "missing"
        rows.append({
            "officialComponent": component,
            "requiredForCurrentProduct": required,
            "bridgeExports": web_exports,
            "adapterSources": adapters,
            "adapterKeys": adapter_names,
            "productionConsumerCount": consumer_count,
            "status": status,
            "requirementDecision": "required_current_semantic" if required else NOT_REQUIRED_DECISIONS.get(component, "not required by current formal product semantics"),
        })

    counts = {status: sum(1 for row in rows if row["status"] == status) for status in ("adapter_present", "adapter_unconsumed", "bridge_only", "missing", "not_required")}
    return {
        "schemaVersion": "frontend-component-driver-takeover/v1",
        "authority": {"library": "tdesign-vue-next", "lockedVersion": package["version"], "publicEntrypoint": "tdesign-vue-next/es/<component>"},
        "scope": "repository P0/P1 frontend production sources",
        "inputDigest": digest(all_inputs, extra=f"tdesign-vue-next@{package['version']}"),
        "summary": {**counts, "officialComponents": len(rows), "requiredDrivers": len(REQUIRED_DRIVERS), "directLibraryImportBypasses": len(direct_imports), "unassessedRawBehaviorSurfaces": len(raw_surfaces)},
        "components": rows,
        "directLibraryImportBypasses": direct_imports,
        "rawBehaviorSurfaces": raw_surfaces,
        "completionRule": "missing=0, bridge_only=0, adapter_unconsumed=0, directLibraryImportBypasses=0, unassessedRawBehaviorSurfaces=0",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = json.dumps(build_inventory(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != payload:
            print(f"[component_driver_takeover_inventory] FAIL stale={relative(OUTPUT)}")
            if OUTPUT.is_file():
                try:
                    import json as _json
                    cur = _json.loads(OUTPUT.read_text(encoding="utf-8"))
                    newp = _json.loads(payload)
                    for key in ("inputDigest", "components", "directLibraryImportBypasses", "rawBehaviorSurfaces", "summary"):
                        if cur.get(key) != newp.get(key):
                            cl = len(str(cur.get(key))) if cur.get(key) is not None else 0
                            nl = len(str(newp.get(key))) if newp.get(key) is not None else 0
                            print(f"  DIFF field={key} committed_len={cl} generated_len={nl}")
                            if key == "components" and isinstance(cur.get(key), list) and isinstance(newp.get(key), list):
                                cset = {c.get("officialComponent") for c in cur["components"]}
                                nset = {c.get("officialComponent") for c in newp["components"]}
                                print(f"    only_committed={sorted(cset-nset)[:8]}")
                                print(f"    only_generated={sorted(nset-cset)[:8]}")
                            if key == "inputDigest":
                                from collections import Counter
                                import hashlib as _hl
                                sf = [relative(p) for p in sources()]
                                print(f"    source_files count={len(sf)}")
                                top = Counter(p.split("/")[2] if len(p.split("/")) > 2 else p for p in sf)
                                print(f"    top_dist={dict(top)}")
                                try:
                                    import subprocess
                                    tracked = set(subprocess.run(["git", "ls-files"], capture_output=True, text=True, cwd=ROOT).stdout.split())
                                    untracked = [p for p in sf if p not in tracked]
                                    print(f"    untracked_count={len(untracked)}")
                                    if untracked:
                                        print(f"    untracked={untracked[:15]}")
                                except Exception as e2:
                                    print(f"    (git ls-files failed: {e2})")
                                def _fsha(pp):
                                    return _hl.sha256(pp.read_bytes()).hexdigest()[:16]
                                for pp in [Path(__file__).resolve(), ROOT / "docs/frontend_productization/rendering-detail/rendering-surface-ownership-v1.json", UI / "src/primitives.ts", DESIGN / "tdesignPrimitiveBridge.ts"]:
                                    try:
                                        print(f"    sha {relative(pp)}={_fsha(pp)}")
                                    except Exception as e3:
                                        print(f"    sha {pp} ERR {e3}")
                                try:
                                    print(f"    src_digest={digest(sources())[:16]}")
                                    print(f"    gen_sha={_hl.sha256(Path(__file__).resolve().read_bytes()).hexdigest()[:16]}")
                                except Exception as e4:
                                    print(f"    (src_digest failed: {e4})")
                except Exception as exc:
                    print(f"  (diff inspect failed: {exc})")
            return 1
        report = json.loads(payload)
        print(f"[component_driver_takeover_inventory] PASS required={report['summary']['requiredDrivers']} missing={report['summary']['missing']} bridge_only={report['summary']['bridge_only']} raw={report['summary']['unassessedRawBehaviorSurfaces']}")
        return 0
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(payload, encoding="utf-8")
    print(f"[component_driver_takeover_inventory] wrote {relative(OUTPUT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
