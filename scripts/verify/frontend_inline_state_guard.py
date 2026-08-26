#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FILES = {
    "inline": ROOT / "frontend/apps/web/src/components/design-system/ScInlineState.vue",
    "empty": ROOT / "frontend/apps/web/src/components/design-system/ScEmptyState.vue",
    "error": ROOT / "frontend/apps/web/src/components/design-system/ScErrorState.vue",
}


def validate(sources: dict[str, str] | None = None) -> list[str]:
    values = sources or {key: path.read_text(encoding="utf-8") for key, path in FILES.items()}
    failures: list[str] = []
    inline = values["inline"]
    for marker in (
        'data-semantic-component="ScInlineState"',
        ':data-state="state"',
        ':data-density="density"',
        ":role=\"state === 'error' ? 'alert' : 'status'\"",
        ":aria-busy=\"state === 'loading' || undefined\"",
        "prefers-reduced-motion: reduce",
    ):
        if marker not in inline:
            failures.append(f"inline state missing {marker}")
    for forbidden in ("project.project", "payment.request", "action_id", "menu_id", "付款", "项目"):
        if forbidden in inline:
            failures.append(f"inline state contains forbidden business identity {forbidden}")

    for key in ("empty", "error"):
        source = values[key]
        for marker in (':data-density="density"', "headingLevel?: 2 | 3 | 4 | 5 | 6", "const titleTag = computed"):
            if marker not in source:
                failures.append(f"{key} state missing bounded hierarchy marker {marker}")
    if "<h2" in values["error"]:
        failures.append("error state retains a fixed heading level")
    return failures


def main() -> int:
    failures = validate()
    if failures:
        print("[frontend_inline_state_guard] FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("[frontend_inline_state_guard] PASS primitives=3")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
