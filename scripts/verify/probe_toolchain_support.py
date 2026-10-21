"""Lifecycle check for governed Python probe entrypoints, before runtime I/O."""
from __future__ import annotations

import json
from pathlib import Path


def assert_probe_supported(filename: str) -> None:
    root = Path(__file__).resolve().parents[2]
    relative = str(Path(filename).resolve().relative_to(root))
    registry = json.loads((root / 'config/frontend/probe_toolchain_registry.json').read_text())
    if registry['tools'].get(relative, {}).get('status') != 'supported':
        raise RuntimeError(f'PROBE_TOOL_UNSUPPORTED: {relative}; entry namespace adaptation is required; no runtime coverage was produced')
