#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PORT_DIR = Path("frontend/packages/ui/src/primitive-port")
PACKAGE_JSON = Path("frontend/packages/ui/package.json")
REQUIRED_FILES = {"types.ts", "events.ts", "slots.ts", "validation.ts", "index.ts"}
FORBIDDEN_IMPORT = re.compile(
    r"(?:from\s+|import\s*\()['\"](?:tdesign-[^'\"]+|@sc/ui(?:/|['\"])|\.\./components|\.\./icons|.*apps/web)",
)
FORBIDDEN_SOURCE = (
    re.compile(r"\bas\s+Primitive(?:Component|Binding)\b"),
    re.compile(r"\b(CNY|Intl\.NumberFormat|style:\s*['\"]currency['\"])\b"),
)
FORBIDDEN_BUNDLE_INPUTS = (
    "frontend/apps/web/",
    "frontend/packages/ui/src/components/",
    "frontend/packages/ui/src/kits/tdesign/",
    "tdesign-vue-next",
    "tdesign-icons-vue-next",
)


def source_files(port_dir: Path) -> list[Path]:
    return sorted(path for path in port_dir.rglob("*.ts") if path.is_file())


def validate(root: Path = ROOT, metafile: Path | None = None) -> list[str]:
    errors: list[str] = []
    port_dir = root / PORT_DIR
    package_path = root / PACKAGE_JSON

    if not port_dir.is_dir():
        return [f"missing primitive-port directory: {PORT_DIR.as_posix()}"]
    existing = {path.name for path in source_files(port_dir)}
    missing = sorted(REQUIRED_FILES - existing)
    if missing:
        errors.append(f"missing primitive-port files: {', '.join(missing)}")

    if not package_path.is_file():
        return errors + [f"missing package manifest: {PACKAGE_JSON.as_posix()}"]
    package = json.loads(package_path.read_text(encoding="utf-8"))
    if package.get("exports", {}).get("./primitive-port") != "./src/primitive-port/index.ts":
        errors.append("package exports must expose ./primitive-port -> ./src/primitive-port/index.ts")

    for path in source_files(port_dir):
        relative = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        if FORBIDDEN_IMPORT.search(text):
            errors.append(f"primitive-port import escapes the protocol boundary: {relative}")
        for pattern in FORBIDDEN_SOURCE:
            if pattern.search(text):
                errors.append(f"primitive-port contains forbidden compatibility or business semantic proof: {relative}")

    index_path = port_dir / "index.ts"
    if index_path.is_file():
        index = index_path.read_text(encoding="utf-8")
        for module in ("events", "slots", "types", "validation"):
            if f"export * from './{module}';" not in index:
                errors.append(f"primitive-port index does not export {module}.ts")

    if metafile is not None:
        if not metafile.is_file():
            errors.append(f"bundle metafile is missing: {metafile}")
        else:
            payload = json.loads(metafile.read_text(encoding="utf-8"))
            inputs = payload.get("inputs", {})
            if not isinstance(inputs, dict):
                errors.append("bundle metafile inputs must be an object")
            else:
                input_names = [str(path).replace("\\", "/") for path in inputs]
                if not any("/frontend/packages/ui/src/primitive-port/index.ts" in f"/{path}" for path in input_names):
                    errors.append("bundle metafile does not include the primitive-port entry")
                for input_name in input_names:
                    if any(fragment in input_name for fragment in FORBIDDEN_BUNDLE_INPUTS):
                        errors.append(f"primitive-port bundle loads forbidden input: {input_name}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metafile", type=Path)
    args = parser.parse_args()
    errors = validate(metafile=args.metafile)
    if errors:
        print("[frontend_primitive_port_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("[frontend_primitive_port_guard] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
