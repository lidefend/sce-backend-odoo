#!/usr/bin/env python3
"""Ensure one semantic component owns safe v-html rendering."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OWNER = "frontend/apps/web/src/components/content/ScRichText.vue"
CONSUMERS = {
    "frontend/apps/web/src/components/professional-fields/ProfessionalBaseFieldControl.vue": 1,
    "frontend/apps/web/src/components/page/blocks/BlockRichTextOverview.vue": 1,
    "frontend/apps/web/src/components/template/FormSection.vue": 2,
    "frontend/apps/web/src/pages/contractForm/ContractFormNativeCanvas.vue": 1,
}
V_HTML_RE = re.compile(r"\bv-html\s*=")


def inspect(root: Path = ROOT) -> dict:
    web_src = root / "frontend/apps/web/src"
    errors: list[str] = []
    directives: dict[str, int] = {}
    for path in sorted(web_src.rglob("*")):
        if path.suffix not in {".vue", ".html"} or not path.is_file():
            continue
        count = len(V_HTML_RE.findall(path.read_text(encoding="utf-8", errors="ignore")))
        if count:
            directives[path.relative_to(root).as_posix()] = count

    if directives.get(OWNER) != 1:
        errors.append(f"rich-text owner must contain exactly one v-html directive: {OWNER}")
    for relative in sorted(set(directives) - {OWNER}):
        errors.append(f"naked v-html outside ScRichText: {relative}")

    owner = root / OWNER
    owner_text = owner.read_text(encoding="utf-8") if owner.is_file() else ""
    for marker in (
        "sanitizeReadonlyHtml",
        "sanitizeRestrictedHtml",
        'data-semantic-component="ScRichText"',
        ':data-policy="policy"',
    ):
        if marker not in owner_text:
            errors.append(f"ScRichText missing required sanitizer contract: {marker}")

    for relative, expected in CONSUMERS.items():
        path = root / relative
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        actual = len(re.findall(r"<ScRichText\b", text))
        if actual != expected:
            errors.append(f"rich-text consumer count mismatch: {relative}: expected={expected} actual={actual}")

    return {"errors": errors, "directives": directives, "consumers": CONSUMERS}


def main() -> int:
    result = inspect()
    if result["errors"]:
        print("[frontend_rich_text_guard] FAIL")
        for error in result["errors"]:
            print(f"- {error}")
        return 1
    print("[frontend_rich_text_guard] PASS")
    print(f"owner_directives={result['directives'].get(OWNER, 0)} consumers={sum(result['consumers'].values())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
