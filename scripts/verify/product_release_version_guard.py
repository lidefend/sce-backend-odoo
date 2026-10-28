#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DERIVED_VERSION_OBSERVATIONS = {
    Path("docs/contract/snapshots/system_init_intent_admin.json"): (
        "ui_contract_raw",
        "product_version",
    ),
}

# Historical runtime observations are evidence, not release declarations.
# Only this registered report and a complete provenance-bearing line qualify;
# all other occurrences (including elsewhere in the same report) remain checked.
HISTORICAL_VERSION_REPORT = Path("docs/ops/iterations/fe_ux_walkthrough_01/journeys.md")
HISTORICAL_VERSION_LINE = re.compile(
    r"- 历史运行观测（非当前发布声明）：observed_at=2026-10-24; "
    r"source_sha=96c860d0fb041c556b687afaad6dc689528785e5; "
    r"page_version=`1\.0\.0-rc\.20`。"
)

# Reviewed historical responses are not current release configuration. Bind the
# complete projection (including timestamp, source revision and original hash),
# not a directory or arbitrary product_version field. Any edit needs review.
HISTORICAL_IDENTITY_OBSERVATIONS = {
    Path("docs/ops/iterations/fe-presentation-convergence-01/fepc-09/runtime-identity.json"):
        "2f84cbd776c4b83b9afe4a9d541fc5c377db36ee82d1aaf8ac92c3864aad8d4a",
}


def is_registered_historical_identity(relative: Path, content: str) -> bool:
    expected = HISTORICAL_IDENTITY_OBSERVATIONS.get(relative)
    return expected is not None and hashlib.sha256(content.encode("utf-8")).hexdigest() == expected


def validate_historical_identities(root: Path) -> list[str]:
    errors = []
    for relative in HISTORICAL_IDENTITY_OBSERVATIONS:
        try:
            content = (root / relative).read_bytes().decode("utf-8")
        except (OSError, UnicodeError):
            errors.append(f"historical runtime identity unreadable: {relative}")
            continue
        if not is_registered_historical_identity(relative, content):
            errors.append(f"historical runtime identity digest mismatch: {relative}")
    return errors


def has_release_version_duplicate(relative: Path, content: str, version: str) -> bool:
    if is_registered_historical_identity(relative, content):
        return False
    token = version_token_pattern(version)
    for line in content.splitlines():
        if relative == HISTORICAL_VERSION_REPORT and HISTORICAL_VERSION_LINE.fullmatch(line):
            continue
        if token.search(line):
            return True
    return False


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path.relative_to(ROOT)}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def tracked_files() -> list[Path]:
    output = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        text=True,
    )
    return [ROOT / item for item in output.splitlines() if item]


def version_token_pattern(version: str) -> re.Pattern[str]:
    return re.compile(
        rf"(?<![0-9A-Za-z.^~<>=]){re.escape(version)}(?![0-9A-Za-z.-])"
    )


def scalar_paths(value: object, expected: str, prefix: tuple[str, ...] = ()) -> list[tuple[str, ...]]:
    matches: list[tuple[str, ...]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            matches.extend(scalar_paths(item, expected, (*prefix, str(key))))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            matches.extend(scalar_paths(item, expected, (*prefix, str(index))))
    elif value == expected:
        matches.append(prefix)
    return matches


def validate_derived_version_observations(root: Path, version: str) -> list[str]:
    errors: list[str] = []
    token = version_token_pattern(version)
    for relative, expected_path in DERIVED_VERSION_OBSERVATIONS.items():
        path = root / relative
        try:
            content = path.read_bytes().decode("utf-8")
            payload = json.loads(content)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            errors.append(f"derived product-version observation unreadable: {relative}: {type(exc).__name__}")
            continue
        value: object = payload
        for key in expected_path:
            if not isinstance(value, dict) or key not in value:
                value = None
                break
            value = value[key]
        if value != version:
            errors.append(
                f"derived product-version observation does not match VERSION: {relative}:{'.'.join(expected_path)}"
            )
        matching_paths = scalar_paths(payload, version)
        if matching_paths != [expected_path] or len(token.findall(content)) != 1:
            errors.append(
                f"derived product-version observation is not unique: {relative}"
            )
    return errors


def main() -> int:
    errors: list[str] = []
    release = load("sce_product_release_guard", ROOT / "scripts" / "release" / "product_release.py")
    try:
        config = release.load_release_config()
    except ValueError as exc:
        print(f"[product.release.version] FAIL {exc}")
        return 1
    version = config["product_version"]
    version_token = version_token_pattern(version)
    derived_paths = {ROOT / path for path in DERIVED_VERSION_OBSERVATIONS}
    duplicates = []
    for path in tracked_files():
        if path == ROOT / "VERSION" or path in derived_paths or not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        if has_release_version_duplicate(path.relative_to(ROOT), content, version):
            duplicates.append(str(path.relative_to(ROOT)))
    if duplicates:
        errors.append(f"product version duplicated outside VERSION: {duplicates}")
    errors.extend(validate_derived_version_observations(ROOT, version))
    errors.extend(validate_historical_identities(ROOT))

    dockerfile = (ROOT / "Dockerfile.production-candidate").read_text(encoding="utf-8")
    for marker in (
        'ARG PRODUCT_VERSION',
        'org.opencontainers.image.title="sce-product"',
        'org.opencontainers.image.version="${PRODUCT_VERSION}"',
        'org.opencontainers.image.revision="${SOURCE_SHA}"',
        'org.opencontainers.image.created="${BUILD_TIME}"',
    ):
        if marker not in dockerfile:
            errors.append(f"Docker release label input missing: {marker}")
    build = (ROOT / "scripts" / "release" / "immutable_candidate_build.sh").read_text(encoding="utf-8")
    for marker in (
        "product_release.py --version",
        "${image_repository}:${product_version}",
        "${image_repository}:sha-${short_sha}",
        'PRODUCT_VERSION=$product_version',
    ):
        if marker not in build:
            errors.append(f"candidate build version binding missing: {marker}")

    runtime = load("sce_runtime_product_release_guard", ROOT / "addons" / "smart_core" / "utils" / "product_release.py")
    old_version = os.environ.get("SC_PRODUCT_VERSION")
    old_revision = os.environ.get("SC_SOURCE_REVISION")
    revision = "b" * 40
    try:
        os.environ["SC_PRODUCT_VERSION"] = version
        os.environ["SC_SOURCE_REVISION"] = revision
        identity = runtime.runtime_product_identity()
    finally:
        if old_version is None:
            os.environ.pop("SC_PRODUCT_VERSION", None)
        else:
            os.environ["SC_PRODUCT_VERSION"] = old_version
        if old_revision is None:
            os.environ.pop("SC_SOURCE_REVISION", None)
        else:
            os.environ["SC_SOURCE_REVISION"] = old_revision
    if identity != {"product_version": version, "source_revision": revision}:
        errors.append("runtime product identity does not match VERSION/revision")

    if errors:
        print("[product.release.version] FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print(
        f"[product.release.version] PASS version={version} duplicates=0 "
        f"derived_observations={len(DERIVED_VERSION_OBSERVATIONS)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
