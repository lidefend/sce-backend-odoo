#!/usr/bin/env python3
"""Static authority checks for the Token v1 CSS boundary.

The guard is deliberately incremental: historical style debt remains visible in
the Phase 0 inventory, while newly introduced global variables and forbidden
consumer edges fail immediately.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "frontend/apps/web/src"
TOKEN_DIR = WEB / "styles/tokens"
AUTHORITY = ROOT / "frontend/packages/design-tokens/token-authority.json"
INVENTORY = ROOT / "docs/frontend_productization/design-token-inventory.json"
TDESIGN_BRIDGE = ROOT / "frontend/packages/ui/src/kits/tdesign/theme.css"
STYLE_SUFFIXES = {".css", ".scss", ".sass", ".vue"}
DECLARATION_RE = re.compile(r"(?m)^\s*(--[A-Za-z][\w-]*)\s*:")
REFERENCE_RE = re.compile(r"var\(\s*(--sc-[\w-]+)")
TDESIGN_RE = re.compile(r"--td-[\w-]+")
PRIMITIVE_RE = re.compile(r"var\(\s*--sc-base-[\w-]+")
BRAND_LITERAL_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b")
Z_INDEX_RE = re.compile(r"z-index\s*:\s*(?!var\(--sc-base-z-index-)([1-9]\d*)")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def style_files(root: Path = WEB) -> list[Path]:
    return sorted(path for path in root.rglob("*") if path.suffix in STYLE_SUFFIXES)


def load_authority() -> dict:
    return json.loads(read(AUTHORITY))


def classify_legacy_name(name: str, authority: dict | None = None) -> dict | None:
    authority = authority or load_authority()
    for rule in authority["legacyClassificationRules"]:
        if re.fullmatch(rule["match"], name):
            return rule
    return None


def phase0_inventory_names() -> list[str]:
    payload = json.loads(read(INVENTORY))
    return [str(row["name"]) for row in payload["cssVariableDefinitions"]]


def token_definitions() -> dict[str, Path]:
    definitions: dict[str, Path] = {}
    for path in sorted(TOKEN_DIR.glob("*.css")):
        for name in DECLARATION_RE.findall(read(path)):
            definitions[name] = path
    for path in sorted((ROOT / "frontend/packages/design-tokens/dist/web").glob("*.css")):
        for name in DECLARATION_RE.findall(read(path)):
            definitions[name] = path
    return definitions


def token_reference_errors() -> list[str]:
    definitions = token_definitions()
    declarations: dict[str, str] = {}
    for name, path in definitions.items():
        match = re.search(rf"(?m)^\s*{re.escape(name)}\s*:\s*([^;]+);", read(path))
        if match:
            declarations[name] = match.group(1)
    return reference_graph_errors(declarations)


def reference_graph_errors(declarations: dict[str, str]) -> list[str]:
    graph: dict[str, set[str]] = {name: set() for name in declarations}
    for name, value in declarations.items():
        refs = set(REFERENCE_RE.findall(value))
        missing = sorted(ref for ref in refs if ref not in declarations)
        if missing:
            return [f"{name} references undefined token(s): {', '.join(missing)}"]
        graph[name] = refs

    errors: list[str] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(name: str, stack: list[str]) -> None:
        if name in visiting:
            errors.append(f"token alias cycle: {' -> '.join(stack + [name])}")
            return
        if name in visited:
            return
        visiting.add(name)
        for ref in graph.get(name, set()):
            visit(ref, stack + [name])
        visiting.remove(name)
        visited.add(name)

    for name in graph:
        visit(name, [])
    return errors


def changed_style_lines() -> dict[Path, str]:
    """Return only added style lines, preserving the baseline as an allowlist."""
    command = ["git", "diff", "--unified=0", "HEAD", "--", "frontend/apps/web/src", "frontend/packages/ui/src/kits/tdesign"]
    result = subprocess.run(command, cwd=ROOT, check=True, text=True, capture_output=True)
    current: Path | None = None
    changed: dict[Path, list[str]] = {}
    for line in result.stdout.splitlines():
        if line.startswith("+++ b/"):
            candidate = ROOT / line[6:]
            current = candidate if candidate.suffix in STYLE_SUFFIXES else None
        elif current and line.startswith("+") and not line.startswith("+++"):
            changed.setdefault(current, []).append(line[1:])
    return {path: "\n".join(lines) for path, lines in changed.items()}


def incremental_boundary_errors() -> list[str]:
    errors: list[str] = []
    for path, added in changed_style_lines().items():
        errors.extend(boundary_errors_for(path, added))
    return errors


def boundary_errors_for(path: Path, added: str) -> list[str]:
    """Validate one added style fragment; exposed for positive and negative tests."""
    errors: list[str] = []
    in_token_dir = TOKEN_DIR in path.parents
    label = rel(path)
    if not in_token_dir and path != TDESIGN_BRIDGE and DECLARATION_RE.search(added):
        errors.append(f"new global CSS variable outside Token v1: {label}")
    if not in_token_dir and PRIMITIVE_RE.search(added):
        errors.append(f"business style directly consumes primitive token: {label}")
    if path != TDESIGN_BRIDGE and TDESIGN_RE.search(added):
        errors.append(f"TDesign theme variable outside bridge: {label}")
    if not in_token_dir and BRAND_LITERAL_RE.search(added):
        errors.append(f"new hardcoded color outside token source: {label}")
    if not in_token_dir and Z_INDEX_RE.search(added):
        errors.append(f"new unregistered z-index outside token source: {label}")
    return errors


def validate_authority() -> list[str]:
    errors: list[str] = []
    authority = load_authority()
    expected_layers = {"primitive", "semantic", "component", "pattern"}
    if set(authority.get("layers", {})) != expected_layers:
        errors.append("token authority must declare exactly primitive, semantic, component, pattern layers")
    required_record_fields = {"token", "layer", "valueOrReference", "status", "replacement", "owner", "allowedConsumerScope"}
    if set(authority.get("recordFields", [])) != required_record_fields:
        errors.append("token authority record schema is incomplete")
    for record in authority.get("canonicalSources", []):
        if set(record) != required_record_fields:
            errors.append(f"canonical token source has incomplete authority record: {record.get('token', '<unknown>')}")
        elif record["status"] != "canonical":
            errors.append(f"canonical token source has invalid status: {record['token']}")
    for name in phase0_inventory_names():
        if not classify_legacy_name(name, authority):
            errors.append(f"unclassified Phase 0 variable: {name}")
    return errors


def main() -> int:
    errors = validate_authority() + token_reference_errors() + incremental_boundary_errors()
    if errors:
        print("[design_token_system] FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("[design_token_system] PASS")
    print(f"phase0_variable_classification={len(phase0_inventory_names())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
