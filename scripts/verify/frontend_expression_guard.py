#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Frontend expression single-source guard (G1-G3).

Conservative, locatable static checks.  It does NOT scan every string literal;
it only checks *definitions* of the authoritative formatters/constants and the
direct primitive bypasses, so a business label that happens to contain a dash
does not trip it.  Legal adapters are registered in
``docs/frontend_productization/frontend_expression_ledger_v1.json``.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FRONTEND_SRC = ROOT / "frontend" / "apps" / "web" / "src"
LEDGER_REL = "docs/frontend_productization/frontend_expression_ledger_v1.json"


def _rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _load_ledger() -> dict:
    path = ROOT / LEDGER_REL
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _sources():
    for path in FRONTEND_SRC.rglob("*"):
        if not path.is_file() or path.suffix not in {".ts", ".vue"}:
            continue
        if "node_modules" in path.parts:
            continue
        yield path


def validate(source: callable | None = None) -> list[str]:
    """Return a list of human-readable violations; empty means PASS."""
    failures: list[str] = []
    ledger = _load_ledger()

    money_authority = ledger.get("g1_money", {}).get("authority_files", [])
    money_adapters = set(ledger.get("g1_money", {}).get("adapter_files", []))
    money_redef = re.compile(
        r"export\s+(?:async\s+)?function\s+(formatMonetaryDisplayValue|formatMonetaryInputValue|resolveMonetaryScale|monetaryInputStep)\b"
    )
    local_fmt_money = re.compile(r"(?:export\s+)?function\s+fmtMoney\b")

    date_primitives = (
        set(ledger.get("g2_date", {}).get("primitive_files", []))
        | set(ledger.get("g2_date", {}).get("bridge_files", []))
    )
    date_tag = re.compile(r"<TDesignDatePicker\b")
    date_import = re.compile(r"\bTDesignDatePicker\b")

    empty_authority = ledger.get("g3_empty", {}).get("authority_files", [])
    empty_definition = re.compile(r"export\s+const\s+\w*EMPTY\w*\s*=\s*['\"]--['\"]")

    status_authority = ledger.get("g4_status", {}).get("authority_files", [])
    status_tone_def = re.compile(r"(?:export\s+)?(?:async\s+)?function\s+resolveStatusTone\b")

    action_authority = ledger.get("g9_action", {}).get("authority_files", [])
    execute_dispatch = re.compile(r"intentRequest\s*\(\s*\{[^}]*intent\s*:\s*['\"]execute['\"]", re.S)

    industry_allowed = set(ledger.get("g10_industry", {}).get("allowed_files", []))
    industry_token = re.compile(
        r"PaymentSettlementDetailCollectionControl|PaymentSettlementIntroduceDialog|sc\.payment\.settlement_detail_collection"
    )

    field_dispatcher = set(ledger.get("g_field_render_a", {}).get("dispatcher_files", []))
    field_dispatcher_internal = set(ledger.get("g_field_render_a", {}).get("internal_dirs", []))
    professional_control_import = re.compile(
        r"from\s+['\"][^'\"]*(?:ProfessionalBaseFieldControl|ProfessionalRelationFieldControl|ProfessionalBusinessValueControl|ProfessionalDetailCollectionControl)\.vue['\"]"
    )

    industry_register_module = set(ledger.get("g_field_render_c", {}).get("registration_files", []))
    industry_control_import = re.compile(r"from\s+['\"][^'\"]*PaymentSettlementDetailCollectionControl\.vue['\"]")

    for path in _sources():
        rel = _rel(path)
        text = path.read_text(encoding="utf-8", errors="replace")
        if source is not None:
            text = source(rel) or text

        for match in money_redef.finditer(text):
            if rel not in money_authority:
                failures.append(
                    f"{rel}:{text[: match.start()].count(chr(10)) + 1}: G1 money formatter '{match.group(1)}' is redefined outside utils/money.ts"
                )
        for match in local_fmt_money.finditer(text):
            if rel not in money_adapters:
                failures.append(
                    f"{rel}:{text[: match.start()].count(chr(10)) + 1}: G1 local fmtMoney is not a registered platform-formatter adapter"
                )

        if rel not in date_primitives:
            if date_tag.search(text) or date_import.search(text):
                failures.append(
                    f"{rel}: G2 TDesignDatePicker is used outside the registered date primitives (ScDatePicker/ScDateField)"
                )

        for match in empty_definition.finditer(text):
            if rel not in empty_authority:
                failures.append(
                    f"{rel}:{text[: match.start()].count(chr(10)) + 1}: G3 an EMPTY_TEXT constant is redefined outside utils/fieldSemantics.ts"
                )

        for match in status_tone_def.finditer(text):
            if rel not in status_authority:
                failures.append(
                    f"{rel}:{text[: match.start()].count(chr(10)) + 1}: G4 resolveStatusTone is redefined outside collectionStatusPresentation.ts"
                )

        for match in execute_dispatch.finditer(text):
            if rel not in action_authority:
                failures.append(
                    f"{rel}:{text[: match.start()].count(chr(10)) + 1}: G9 direct intent 'execute' dispatch outside the action runtime"
                )

        if rel not in industry_allowed and industry_token.search(text):
            failures.append(
                f"{rel}: G10 platform file references an industry renderer or component key"
            )

        for match in professional_control_import.finditer(text):
            if rel not in field_dispatcher and not any(rel.startswith(d) for d in field_dispatcher_internal):
                failures.append(
                    f"{rel}:{text[: match.start()].count(chr(10)) + 1}: G-field-render-a a Professional field control is imported outside FormSection.vue"
                )

        for match in industry_control_import.finditer(text):
            if rel not in industry_register_module:
                failures.append(
                    f"{rel}:{text[: match.start()].count(chr(10)) + 1}: G-field-render-c industry renderer is imported outside its registration module"
                )

    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    failures = validate()
    for failure in failures:
        print(f"[frontend-expression-guard] FAIL {failure}")
    if failures:
        return 1
    print("[frontend-expression-guard] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
