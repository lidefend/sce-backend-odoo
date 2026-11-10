#!/usr/bin/env python3
"""Keep inline styles limited to explicitly owned rendering mechanics."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WEB_SRC = ROOT / "frontend/apps/web/src"
ALLOWLIST = ROOT / "docs/architecture/inline_style_allowlist.json"

STATIC_STYLE_RE = re.compile(r"(?<![-:\w])style\s*=")
DYNAMIC_STYLE_RE = re.compile(r"(?:(?<![-:\w]):|v-bind:)style\s*=")
STYLE_PROP_RE = re.compile(
    r"(?:(?<![-:\w]):|v-bind:)(?:layout|body|header|overlay|dialog)-style\s*="
)
SCRIPT_STYLE_RE = re.compile(
    r"\bstyle\s*:\s*(?:\{|[A-Za-z_$][\w$]*(?:\s*\([^)]*\))?)"
)
SCRIPT_RE = re.compile(r"<script\b[^>]*>(.*?)</script>", re.DOTALL)


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _template_text(text: str) -> str:
    start = text.find("<template")
    if start < 0:
        return ""
    end = text.find("<script")
    return text[start:end if end >= 0 else len(text)]


def _uses_inline_style(path: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="ignore")
    template_text = _template_text(text) if path.suffix == ".vue" else text
    if path.suffix in {".vue", ".html"} and any(
        pattern.search(template_text)
        for pattern in (DYNAMIC_STYLE_RE, STYLE_PROP_RE)
    ):
        return True
    script_text = "\n".join(
        match.group(1) for match in SCRIPT_RE.finditer(text)
    ) if path.suffix == ".vue" else text
    return bool(SCRIPT_STYLE_RE.search(script_text))


def inspect(root: Path = ROOT, allowlist_path: Path | None = None) -> dict:
    web_src = root / "frontend/apps/web/src"
    allowlist_path = allowlist_path or root / "docs/architecture/inline_style_allowlist.json"
    errors: list[str] = []
    try:
        payload = json.loads(allowlist_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return {"errors": [f"invalid allowlist: {exc}"], "files": [], "mechanisms": {}}

    if payload.get("schema_version") != 1:
        errors.append("allowlist schema_version must be 1")
    if payload.get("scope") != "frontend/apps/web/src":
        errors.append("allowlist scope must be frontend/apps/web/src")
    mechanisms = payload.get("mechanisms")
    registered = payload.get("files")
    if not isinstance(mechanisms, dict) or not mechanisms:
        errors.append("allowlist mechanisms must be a non-empty object")
        mechanisms = {}
    if not isinstance(registered, dict):
        errors.append("allowlist files must be an object")
        registered = {}

    for mechanism, record in mechanisms.items():
        if not isinstance(record, dict):
            errors.append(f"mechanism {mechanism} must be an object")
            continue
        if not str(record.get("owner", "")).strip():
            errors.append(f"mechanism {mechanism} is missing owner")
        if not str(record.get("reason", "")).strip():
            errors.append(f"mechanism {mechanism} is missing reason")

    discovered: set[str] = set()
    for path in sorted(web_src.rglob("*")):
        if path.suffix not in {".vue", ".ts", ".js", ".html"} or not path.is_file():
            continue
        relative = _relative(path, root)
        if path.suffix in {".vue", ".html"}:
            raw = path.read_text(encoding="utf-8", errors="ignore")
            template = _template_text(raw) if path.suffix == ".vue" else raw
            if STATIC_STYLE_RE.search(template):
                errors.append(f"literal static inline style is forbidden: {relative}")
        if _uses_inline_style(path):
            discovered.add(relative)

    for relative, assigned in sorted(registered.items()):
        if relative not in discovered:
            errors.append(f"stale inline-style allowlist entry: {relative}")
        if not isinstance(assigned, list) or not assigned:
            errors.append(f"inline-style allowlist entry has no mechanisms: {relative}")
            continue
        unknown = sorted(set(assigned) - set(mechanisms))
        if unknown:
            errors.append(
                f"inline-style allowlist entry uses unknown mechanisms: {relative}: {', '.join(unknown)}"
            )

    unregistered = sorted(discovered - set(registered))
    for relative in unregistered:
        errors.append(f"unregistered inline-style site: {relative}")

    return {
        "errors": errors,
        "files": sorted(discovered),
        "mechanisms": {relative: registered.get(relative, []) for relative in sorted(discovered)},
    }


def main() -> int:
    result = inspect()
    if result["errors"]:
        print("[frontend_inline_style_guard] FAIL")
        for error in result["errors"]:
            print(f"- {error}")
        return 1
    print("[frontend_inline_style_guard] PASS")
    print(f"registered_files={len(result['files'])} mechanisms={len({item for values in result['mechanisms'].values() for item in values})}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
