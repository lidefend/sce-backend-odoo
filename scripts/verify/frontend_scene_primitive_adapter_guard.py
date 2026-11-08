#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADAPTER_DIR = Path("frontend/apps/web/src/components/design-system/scene-adapter")
PRODUCT_SOURCE = Path("frontend/apps/web/src")
REQUIRED_FILES = {
    "ScSceneButton.vue",
    "buttonContract.ts",
    "index.ts",
}
IMPORT = re.compile(r"(?:from\s+|import\s*\()['\"](?P<specifier>[^'\"]+)['\"]")
ALLOWED_IMPORTS = {
    'vue',
    '@sc/ui/primitive-port',
    '../ScButton.vue',
    '../ScInput.vue',
    '../ScTextarea.vue',
    '../ScTable.vue',
    '../ScIcon.vue',
    './ScSceneButton.vue',
    './ScSceneInput.vue',
    './ScSceneTextarea.vue',
    './ScSceneTable.vue',
    './ScSceneIcon.vue',
    './buttonContract',
    './textControlContracts',
    './collectionContracts',
}
FORBIDDEN_SOURCE = (
    re.compile(r"\bas\s+Primitive(?:Component|Binding)\b"),
    re.compile(r"tdesign(?:-vue-next|-icons-vue-next)"),
)
FORBIDDEN_BUNDLE_INPUTS = (
    "frontend/packages/ui/src/components/",
    "frontend/apps/web/src/pages/",
)
INTERNAL_PRODUCT_IMPORT = re.compile(
    r"(?:from\s+|import\s*\()['\"](?:[^'\"]*design-system/scene-adapter|@sc/ui/primitive-port/provider)['\"]"
)
BUTTON_CAPABILITIES = {
    "activate",
    "focus",
    "blur",
    "keyboard",
    "loading",
}


def source_files(adapter_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in adapter_dir.rglob("*")
        if path.is_file() and path.suffix in {".ts", ".vue"}
    )


def validate(root: Path = ROOT, metafile: Path | None = None) -> list[str]:
    errors: list[str] = []
    adapter_dir = root / ADAPTER_DIR
    if not adapter_dir.is_dir():
        return [f"missing scene-adapter directory: {ADAPTER_DIR.as_posix()}"]

    existing = {path.name for path in source_files(adapter_dir)}
    missing = sorted(REQUIRED_FILES - existing)
    if missing:
        errors.append(f"missing scene-adapter files: {', '.join(missing)}")

    for path in source_files(adapter_dir):
        relative = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        for match in IMPORT.finditer(text):
            specifier = match.group("specifier")
            if specifier not in ALLOWED_IMPORTS:
                errors.append(
                    f"scene-adapter import escapes the Sc/Port authority: {relative} -> {specifier}"
                )
        for pattern in FORBIDDEN_SOURCE:
            if pattern.search(text):
                errors.append(
                    f"scene-adapter contains a forbidden vendor path or compatibility cast: {relative}"
                )

    contract_path = adapter_dir / "buttonContract.ts"
    if contract_path.is_file():
        contract = contract_path.read_text(encoding="utf-8")
        if "primitive: 'Button'" not in contract:
            errors.append("buttonContract.ts must declare Button identity")
        if "portVersion: 1" not in contract:
            errors.append("buttonContract.ts must declare portVersion 1")
        for capability in sorted(BUTTON_CAPABILITIES):
            if f"'{capability}'" not in contract:
                errors.append(f"buttonContract.ts is missing capability {capability}")
        if "component: ScSceneButton" not in contract:
            errors.append("buttonContract.ts must bind the real ScSceneButton wrapper")

    wrapper_path = adapter_dir / "ScSceneButton.vue"
    if wrapper_path.is_file():
        wrapper = wrapper_path.read_text(encoding="utf-8")
        for marker, detail in (
            ("<ScButton", "must render the ScButton authority"),
            ("defineEmits<ButtonPortEmits>()", "must declare the Button Port emits"),
            ("defineSlots<ButtonPortSlots>()", "must declare the Button Port slots"),
            ("emit('activate'", "must emit the Button Port activate event"),
            ("nativeEvent: event", "must preserve the real native event"),
            ("props.disabled || props.loading", "must guard disabled/loading activation"),
            (":aria-label=\"accessibleLabel\"", "must project the accessible label"),
        ):
            if marker not in wrapper:
                errors.append(f"ScSceneButton.vue {detail}")

    index_path = adapter_dir / "index.ts"
    if index_path.is_file():
        index = index_path.read_text(encoding="utf-8")
        if "export { default as ScSceneButton } from './ScSceneButton.vue';" not in index:
            errors.append("scene-adapter index must export ScSceneButton")
        if "scSceneButtonBinding" not in index or "scSceneButtonContract" not in index:
            errors.append("scene-adapter index must export the real Button binding and contract")

    product_source = root / PRODUCT_SOURCE
    if product_source.is_dir():
        for path in sorted(product_source.rglob("*")):
            relative = path.relative_to(root)
            if (
                not path.is_file()
                or path.suffix not in {".ts", ".tsx", ".vue"}
                or ADAPTER_DIR in relative.parents
            ):
                continue
            if INTERNAL_PRODUCT_IMPORT.search(path.read_text(encoding="utf-8")):
                errors.append(
                    "product source now consumes the fixture-only primitive adapter/provider; "
                    "reclassify list-surface runtime evidence before enabling this path: "
                    f"{relative.as_posix()}"
                )

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
                for required in (
                    "frontend/apps/web/src/components/design-system/scene-adapter/ScSceneButton.vue",
                    "frontend/apps/web/src/components/design-system/ScButton.vue",
                ):
                    if not any(name.endswith(required) for name in input_names):
                        errors.append(f"adapter bundle does not include required input {required}")
                for input_name in input_names:
                    if any(fragment in input_name for fragment in FORBIDDEN_BUNDLE_INPUTS):
                        errors.append(f"adapter bundle loads forbidden input: {input_name}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metafile", type=Path)
    args = parser.parse_args()
    errors = validate(metafile=args.metafile)
    if errors:
        print("[frontend_scene_primitive_adapter_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("[frontend_scene_primitive_adapter_guard] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
