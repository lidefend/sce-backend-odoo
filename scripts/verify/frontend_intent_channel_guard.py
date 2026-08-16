#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[2]
WEB_SRC = ROOT / "frontend/apps/web/src"
INTENT_ENDPOINT = "/api/v1/intent"
# Credential bootstrap deliberately stays outside the authenticated intent
# transport. These exact routes need save_session=False plus no-store response
# handling and may carry one-time secrets before a principal exists. Keep the
# exception bound to one transport adapter; it is not a general /auth/* escape.
DIRECT_TRANSPORT_EXCEPTIONS = {
    "frontend/apps/web/src/services/accountActivation.ts": frozenset(
        {
            "/api/v1/auth/activation/start",
            "/api/v1/auth/activation/complete",
            "/api/v1/auth/password-recovery/status",
        }
    ),
}
API_PATH_RE = re.compile(r"['\"](/api/[a-zA-Z0-9_./-]+)['\"]")


def _iter_files(web_src: Path = WEB_SRC):
    if not web_src.is_dir():
        return
    for ext in ("*.ts", "*.tsx", "*.js", "*.jsx", "*.vue"):
        for path in web_src.rglob(ext):
            yield path


def is_allowed_api_path(rel: str, api_path: str) -> bool:
    if api_path == INTENT_ENDPOINT:
        return True
    return api_path in DIRECT_TRANSPORT_EXCEPTIONS.get(rel, frozenset())


def scan_api_paths(root: Path = ROOT) -> tuple[list[str], set[str], set[tuple[str, str]]]:
    web_src = root / "frontend/apps/web/src"
    violations: list[str] = []
    found_paths: set[str] = set()
    used_exceptions: set[tuple[str, str]] = set()

    for path in _iter_files(web_src):
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8", errors="ignore")
        for match in API_PATH_RE.finditer(text):
            api_path = str(match.group(1) or "").strip()
            if not api_path:
                continue
            found_paths.add(api_path)
            if not is_allowed_api_path(rel, api_path):
                violations.append(f"{rel}: forbidden api path in web app source: {api_path}")
                continue
            if api_path != INTENT_ENDPOINT:
                used_exceptions.add((rel, api_path))

    declared_exceptions = {
        (rel, api_path)
        for rel, api_paths in DIRECT_TRANSPORT_EXCEPTIONS.items()
        for api_path in api_paths
    }
    for rel, api_path in sorted(declared_exceptions - used_exceptions):
        violations.append(f"{rel}: stale direct transport exception: {api_path}")
    return violations, found_paths, used_exceptions


def main() -> int:
    violations, found_paths, used_exceptions = scan_api_paths()

    if violations:
        print("[frontend_intent_channel_guard] FAIL")
        for item in violations:
            print(item)
        return 1

    print("[frontend_intent_channel_guard] PASS")
    print(f"intent_endpoint={INTENT_ENDPOINT}")
    print(f"observed_paths={sorted(found_paths) if found_paths else []}")
    print(
        "direct_transport_exceptions="
        f"{[f'{rel}:{api_path}' for rel, api_path in sorted(used_exceptions)]}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
