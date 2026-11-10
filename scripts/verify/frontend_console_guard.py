#!/usr/bin/env python3
"""Keep browser console access behind the shared logger."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ALLOWED = "frontend/apps/web/src/utils/logger.ts"
CONSOLE_RE = re.compile(r"\bconsole\.\w+\s*\(")


def inspect(root: Path = ROOT) -> dict:
    web_src = root / "frontend/apps/web/src"
    errors: list[str] = []
    sites: dict[str, int] = {}
    for path in sorted(web_src.rglob("*")):
        if path.suffix not in {".ts", ".vue", ".js", ".html"} or not path.is_file():
            continue
        count = len(CONSOLE_RE.findall(path.read_text(encoding="utf-8", errors="ignore")))
        if count:
            sites[path.relative_to(root).as_posix()] = count

    for relative, count in sorted(sites.items()):
        if relative != ALLOWED:
            errors.append(f"console call outside shared logger: {relative} count={count}")
    if sites.get(ALLOWED, 0) > 5:
        errors.append(f"shared logger owns too many console calls: {sites[ALLOWED]}")

    logger = root / ALLOWED
    text = logger.read_text(encoding="utf-8") if logger.is_file() else ""
    for marker in ("VITE_DEBUG_LOGS", "sink.debug", "sink.info", "sink.warn", "sink.error"):
        if marker not in text:
            errors.append(f"shared logger missing policy marker: {marker}")

    return {"errors": errors, "sites": sites, "total": sum(sites.values())}


def main() -> int:
    result = inspect()
    if result["errors"]:
        print("[frontend_console_guard] FAIL")
        for error in result["errors"]:
            print(f"- {error}")
        return 1
    print("[frontend_console_guard] PASS")
    print(f"console_sites={len(result['sites'])} console_calls={result['total']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
