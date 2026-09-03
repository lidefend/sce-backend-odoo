#!/usr/bin/env python3
"""Mobile viewport contract guard (G4 incremental closure).

R-G4-01: the SPA declares `env(safe-area-inset-*)` paddings in shell and
form pages. Without `viewport-fit=cover` in the viewport meta those
environment variables are always 0 on notched devices, silently disabling
the safe-area handling. This guard fail-closes on:

1. index.html viewport meta missing `width=device-width`,
   `initial-scale=1` or `viewport-fit=cover`.
2. Any style using `env(safe-area-inset-` while viewport-fit=cover is
   absent (cross-file consistency).
3. `user-scalable=no` / `maximum-scale=1` regressions (accessibility
   floor: zoom must not be disabled).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INDEX_HTML = ROOT / "frontend/apps/web/index.html"
STYLE_SUFFIXES = {".css", ".scss", ".sass", ".vue"}
SAFE_AREA_RE = re.compile(r"env\(\s*safe-area-inset-")
VIEWPORT_RE = re.compile(
    r"<meta\s+name=\"viewport\"\s+content=\"([^\"]*)\"", re.IGNORECASE
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def style_files() -> list[Path]:
    web = ROOT / "frontend/apps/web/src"
    return sorted(p for p in web.rglob("*") if p.suffix in STYLE_SUFFIXES)


def parse_viewport_content(index_text: str) -> str:
    match = VIEWPORT_RE.search(index_text)
    return match.group(1) if match else ""


def validate(
    index_text: str | None = None,
    style_sources: dict[str, str] | None = None,
) -> list[str]:
    failures: list[str] = []

    text = index_text if index_text is not None else read(INDEX_HTML)
    if not text:
        failures.append(f"missing {rel(INDEX_HTML)}")
        return failures

    content = parse_viewport_content(text)
    if not content:
        failures.append("index.html must declare a viewport meta tag")
        content = ""

    for required in ("width=device-width", "initial-scale=1", "viewport-fit=cover"):
        if required not in content.replace(" ", ""):
            failures.append(
                f"viewport meta must include '{required}' (got: '{content}')"
            )

    for forbidden in ("user-scalable=no", "maximum-scale=1", "maximum-scale=1.0"):
        if forbidden in content.replace(" ", "").lower():
            failures.append(
                f"viewport meta must not disable zoom ('{forbidden}' violates the "
                "accessibility floor)"
            )

    # Cross-check: safe-area usage requires viewport-fit=cover.
    cover_present = "viewport-fit=cover" in content.replace(" ", "")
    sources = (
        style_sources
        if style_sources is not None
        else {rel(p): read(p) for p in style_files()}
    )
    safe_area_users = [name for name, src in sources.items() if SAFE_AREA_RE.search(src)]
    if safe_area_users and not cover_present:
        failures.append(
            "styles use env(safe-area-inset-*) but viewport meta lacks "
            "viewport-fit=cover, so safe-area handling is inert on notched "
            f"devices (users: {', '.join(safe_area_users[:5])})"
        )

    return failures


def main() -> int:
    failures = validate()
    if failures:
        for failure in failures:
            print(f"[mobile_viewport_guard] FAIL {failure}")
        return 1
    users = [rel(p) for p in style_files() if SAFE_AREA_RE.search(read(p))]
    print(
        "[mobile_viewport_guard] PASS viewport-fit=cover present; "
        f"safe-area users={len(users)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
