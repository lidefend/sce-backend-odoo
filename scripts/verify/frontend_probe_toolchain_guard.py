#!/usr/bin/env python3
"""Reject unregistered legacy authentication and unenforced probe lifecycles."""
from __future__ import annotations

import json
import re
import os
import sys
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
PATTERNS = {
    "database_token": r"sc_auth_token:\$\{(?:db|dbName|database|DB_NAME)\}",
    "database_header": r"['\"]X-Odoo-DB['\"]",
    "database_query": r"/api/v1/intent\?db=",
    "arbitrary_token": r"(?:find|filter)\(.*startsWith\(['\"]sc_auth_token",
}
CJS_BLOCK = "require('./lib/probe_toolchain_support.cjs').assertProbeSupported(__filename);"
ESM_BLOCK = "import './lib/probe_toolchain_blocked.mjs';"


def violations(source: str) -> list[str]:
    lines = [line for line in source.splitlines() if not line.lstrip().startswith(("//", "*"))]
    return [name for name, pattern in PATTERNS.items() if any(re.search(pattern, line) for line in lines)]


def executes_blocked_probe(line: str, blocked: set[str]) -> bool:
    # Match the interpreter's script operand, not arbitrary recipe asset lists.
    # Also covers interpreters inside a quoted container/SSH shell command.
    pattern = r"(?:^|[\s;|&\"'])@?(?:[\w/.-]*/)?(?:node|python[23]?|bash|sh)\s+(?:-[uB]\s+)*[\"']?([^\s\"';|&]+)"
    for match in re.finditer(pattern, line):
        operand = match.group(1)
        if not any(operand == name or operand.endswith('/' + name) for name in blocked):
            continue
        tail = re.split(r"[;|&\"']", line[match.end():], maxsplit=1)[0]
        if operand.endswith('/production_acceptance_harness.py') and tail.split() == ['--print-package-digest']:
            continue
        return True
    return False


def blocked_make_targets(root: Path, registry: dict) -> list[str]:
    from scripts.audit.verification_lane_coverage import parse_make, build_graph, closure
    targets, recipes, prereqs, _ = parse_make(root)
    edges, _, _ = build_graph(targets, recipes, prereqs)
    blocked = {name for name, entry in registry.items() if entry['status'] == 'blocked_legacy'}
    direct = {target for target, lines in recipes.items()
              if any(executes_blocked_probe(line, blocked) for line in lines)}
    return sorted(target for target in recipes if closure([target], edges) & direct)


def make_policy(root: Path, registry: dict) -> str:
    targets = ' '.join(blocked_make_targets(root, registry))
    return ('# Generated from probe_toolchain_registry.json and the existing Make graph.\n'
            '# Refuse before prerequisites, fixture setup, or container commands.\n'
            f'ifneq ($(strip $(filter {targets},$(MAKECMDGOALS))),)\n'
            '$(error PROBE_TOOL_UNSUPPORTED: requested target depends on a blocked legacy probe; see config/frontend/probe_toolchain_registry.json)\n'
            'endif\n')


def check(root: Path) -> list[str]:
    registry = json.loads((root / "config/frontend/probe_toolchain_registry.json").read_text())["tools"]
    errors = []
    if (root / 'Makefile').exists():
        policy = root / 'make/probe_toolchain.mk'
        if not policy.exists() or policy.read_text() != make_policy(root, registry):
            errors.append('Make probe lifecycle policy is missing or stale')
        if 'include make/probe_toolchain.mk' not in (root / 'Makefile').read_text().split('MIGRATION_ASSET_ROOT', 1)[0]:
            errors.append('Make probe lifecycle policy must run before environment setup')
    for name, entry in registry.items():
        path = root / name
        if not path.is_file():
            errors.append(f"{name}: registered tool missing")
            continue
        source = path.read_text()
        if entry["status"] == "blocked_legacy":
            if path.suffix == '.py':
                nodes = ast.parse(source).body
                effects = [node for node in nodes if not (
                    isinstance(node, ast.ImportFrom) and node.module == '__future__'
                    or isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str))]
                if not effects or not isinstance(effects[0], ast.If) or 'assert_probe_supported(__file__)' not in ast.get_source_segment(source, effects[0]):
                    errors.append(f'{name}: Python lifecycle gate must precede runtime imports')
                continue
            if path.suffix == '.sh':
                if "PROBE_TOOL_UNSUPPORTED" not in source.splitlines()[1] or source.splitlines()[2] != 'exit 2':
                    errors.append(f'{name}: shell lifecycle gate must precede runtime effects')
                continue
            statements = [line.strip() for line in source.splitlines()
                          if line.strip() and not line.startswith("#!") and line.strip() not in ("'use strict';", '\"use strict\";')]
            module = root / 'scripts/verify/lib' / ('probe_toolchain_blocked.mjs' if path.suffix == '.mjs' else 'probe_toolchain_support.cjs')
            relative = os.path.relpath(module, path.parent)
            if not relative.startswith('.'):
                relative = './' + relative
            expected = f"import '{relative}';" if path.suffix == '.mjs' else f"require('{relative}').assertProbeSupported(__filename);"
            if not statements or statements[0] != expected:
                errors.append(f"{name}: legacy blocker must precede every executable/import")
        elif entry["status"] != "supported":
            errors.append(f"{name}: unknown lifecycle")
    paths = list((root / "scripts").rglob("*")) + list((root / "frontend/apps/web/scripts").glob("*"))
    for path in paths:
        if not path.is_file() or path.suffix not in (".js", ".mjs", ".cjs", ".ts"):
            continue
        if {"node_modules", "retired"} & set(path.parts):
            continue
        name = str(path.relative_to(root))
        problems = violations(path.read_text())
        if problems and registry.get(name, {}).get("status") != "blocked_legacy":
            errors.append(f"{name}: unsupported authentication: {','.join(problems)}")
    return errors


def main() -> int:
    errors = check(ROOT)
    for error in errors:
        print(error)
    print(f"[frontend_probe_toolchain_guard] {'FAIL' if errors else 'PASS'}")
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
