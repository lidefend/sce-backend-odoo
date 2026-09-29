#!/usr/bin/env python3
"""Hardening guard: keep the browser test/probe layer off vendor-internal DOM.

The adopted official template is consumed through its documented public
surface (roles, semantic markers, business facts). Test and probe scripts
must verify user-visible behaviour the same way. Coupling them to TDesign
internal class names, transition state classes, or pixel geometry makes a
green suite meaningless once the official component changes its markup,
and it hides real regressions because the assertion follows the markup
instead of the business fact.

Enforced rules over the browser test/probe corpus:

* ``transition_state_class`` (zero tolerance)
  Vue/transition state classes such as ``--enter-active`` or ``v-enter``
  observed from a probe prove nothing about the settled page and are
  inherently timing dependent.
* ``dom_api_playwright_pseudo`` (zero tolerance)
  Playwright-only selector syntax (``:visible``, ``:has-text(``,
  ``:text=``) passed to ``querySelector``/``querySelectorAll`` is a latent
  runtime error, not a passing assertion.
* ``vendor_internal_selector`` (baseline, decrease-only)
  A literal selector that reaches a ``.t-*`` class below a non-``Sc`` root
  couples the probe to private TDesign internals.
* ``inline_geometry_assertion`` (baseline, decrease-only)
  ``getBoundingClientRect().width/height`` assertions encode transient
  layout numbers instead of a stable contract.

Baselines record existing debt so the guard blocks new coupling without
forcing an unrelated cleanup in the same change. Baselines may only shrink;
a recorded number is an upper bound, never a licence.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASELINE_PATH = ROOT / "scripts/verify/baselines/playwright_vendor_coupling.json"
METRIC = "playwright-vendor-coupling-v1"

SCOPE_ROOTS = ("frontend/apps/web/scripts", "scripts/verify")
SUFFIXES = {".py", ".sh", ".mjs", ".js", ".cjs", ".ts", ".tsx", ".vue"}

RULE_TRANSITION = "transition_state_class"
RULE_DOM_PSEUDO = "dom_api_playwright_pseudo"
RULE_VENDOR = "vendor_internal_selector"
RULE_GEOMETRY = "inline_geometry_assertion"

ZERO_TOLERANCE_RULES = (RULE_TRANSITION, RULE_DOM_PSEUDO)
BUDGET_RULES = (RULE_VENDOR, RULE_GEOMETRY)

# Mirrors the product-side official-design rule: a vendor class is tolerable
# only on a compound whose root is an Sc*/semantic-component anchor, never as
# a descendant coupling into TDesign internals.
VENDOR_CLASS_RE = re.compile(r"\.t-[a-z0-9_-]+")
SC_ROOT_RE = re.compile(r"(?:\.sc-[a-z0-9_-]+|\[data-semantic-component(?:=|\]))")

TRANSITION_STATE_RE = re.compile(
    r"(?:--(?:enter|leave)-(?:active|from|to)|v-(?:enter|leave)(?:-active|-from|-to)?)(?![A-Za-z0-9_-])"
)
GEOMETRY_RE = re.compile(r"getBoundingClientRect\s*\(\s*\)\s*\.\s*(?:width|height)")
DOM_PSEUDO_RE = re.compile(r"querySelector(?:All)?\s*\(\s*(?P<quote>['\"`])(?P<selector>[^'\"`]*)(?P=quote)")
PLAYWRIGHT_ONLY_TOKENS = (":visible", ":has-text(", ":text=")

LITERAL_RE = re.compile(r"'(?:[^'\\\n]|\\.)*'|\"(?:[^\"\\\n]|\\.)*\"|`(?:[^`\\]|\\.)*`")
EXAMPLE_LIMIT = 3


def _first_combinator(selector: str) -> int | None:
    match = re.search(r"\s[>+~]?\s*", selector)
    return None if match is None else match.start()


def selector_targets_vendor_internals(selector: str) -> bool:
    """True when a selector reaches a vendor class below a non-Sc root."""
    for part in selector.split(","):
        part = " ".join(part.split())
        if not VENDOR_CLASS_RE.search(part):
            continue
        start = _first_combinator(part)
        root = part if start is None else part[:start]
        tail = "" if start is None else part[start:]
        if not SC_ROOT_RE.search(root) or VENDOR_CLASS_RE.search(tail):
            return True
    return False


# The rule definition and its negative fixtures necessarily spell out the
# forbidden literals. Scanning them would only ever flag the guard itself, so
# they are excluded by exact path -- never by directory or wildcard.
SELF_EXCLUDED = (
    Path(__file__).resolve(),
    (Path(__file__).resolve().parent / "test_playwright_vendor_coupling_guard.py").resolve(),
)


def scope_files() -> list[Path]:
    files: list[Path] = []
    for rel_root in SCOPE_ROOTS:
        base = ROOT / rel_root
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.suffix not in SUFFIXES:
                continue
            if path.resolve() in SELF_EXCLUDED:
                continue
            files.append(path)
    return sorted(files, key=lambda item: item.relative_to(ROOT).as_posix())


def _literal_selector_hits(text: str) -> list[str]:
    hits = []
    for match in LITERAL_RE.finditer(text):
        literal = match.group(0)[1:-1]
        if ".t-" in literal and selector_targets_vendor_internals(literal):
            hits.append(literal.strip())
    return hits


def scan_file(path: Path, label: str | None = None) -> dict[str, list[str]]:
    rel = label or path.relative_to(ROOT).as_posix()
    text = path.read_text(encoding="utf-8", errors="ignore")
    findings: dict[str, list[str]] = {rule: [] for rule in (*ZERO_TOLERANCE_RULES, *BUDGET_RULES)}
    for number, line in enumerate(text.splitlines(), start=1):
        if TRANSITION_STATE_RE.search(line):
            findings[RULE_TRANSITION].append(f"{rel}:{number}")
        for match in DOM_PSEUDO_RE.finditer(line):
            selector = match.group("selector")
            if any(token in selector for token in PLAYWRIGHT_ONLY_TOKENS):
                findings[RULE_DOM_PSEUDO].append(f"{rel}:{number}")
        for _ in GEOMETRY_RE.finditer(line):
            findings[RULE_GEOMETRY].append(f"{rel}:{number}")
    findings[RULE_VENDOR] = [f"{rel}: {literal}" for literal in _literal_selector_hits(text)]
    return findings


def collect() -> tuple[dict[str, dict[str, int]], dict[str, list[str]]]:
    counts: dict[str, dict[str, int]] = {rule: {} for rule in (*ZERO_TOLERANCE_RULES, *BUDGET_RULES)}
    locations: dict[str, list[str]] = {rule: [] for rule in (*ZERO_TOLERANCE_RULES, *BUDGET_RULES)}
    for path in scope_files():
        findings = scan_file(path)
        rel = path.relative_to(ROOT).as_posix()
        for rule, hits in findings.items():
            if hits:
                counts[rule][rel] = len(hits)
                locations[rule].extend(hits[:EXAMPLE_LIMIT])
    return counts, locations


def load_baseline() -> dict[str, dict[str, int]]:
    if not BASELINE_PATH.exists():
        return {}
    payload = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    if payload.get("metric") != METRIC:
        raise ValueError("baseline must use the playwright-vendor-coupling metric")
    rules = payload.get("rules")
    if not isinstance(rules, dict):
        raise ValueError("baseline rules must be an object")
    baseline: dict[str, dict[str, int]] = {}
    for rule, entry in rules.items():
        files = entry.get("files") if isinstance(entry, dict) else None
        if not isinstance(files, dict):
            continue
        baseline[str(rule)] = {str(key): int(value) for key, value in files.items()}
    return baseline


def write_baseline(counts: dict[str, dict[str, int]]) -> None:
    rules = {}
    for rule in (*ZERO_TOLERANCE_RULES, *BUDGET_RULES):
        files = counts[rule]
        rules[rule] = {
            "mode": "zero" if rule in ZERO_TOLERANCE_RULES else "decrease-only",
            "files": files,
            "total": sum(files.values()),
        }
    payload = {
        "metric": METRIC,
        "scope": list(SCOPE_ROOTS),
        "rules": rules,
    }
    BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    BASELINE_PATH.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--update", action="store_true", help="rewrite the baseline from the current tree")
    args = parser.parse_args()

    counts, locations = collect()

    if args.update:
        write_baseline(counts)
        print("[OK] playwright vendor coupling baseline updated")
        print(f"- file: {BASELINE_PATH.relative_to(ROOT)}")
        for rule in (*ZERO_TOLERANCE_RULES, *BUDGET_RULES):
            print(f"- {rule}: files={len(counts[rule])} total={sum(counts[rule].values())}")
        return 0

    try:
        baseline = load_baseline()
    except ValueError as error:
        print("[FAIL] playwright vendor coupling guard")
        print(f"- invalid baseline: {error}")
        return 1
    if not baseline:
        print("[FAIL] playwright vendor coupling guard")
        print(f"- missing baseline: {BASELINE_PATH.relative_to(ROOT)}")
        print("- run: python3 scripts/verify/playwright_vendor_coupling_guard.py --update")
        return 1

    errors: list[str] = []
    for rule in ZERO_TOLERANCE_RULES:
        for path, count in sorted(counts[rule].items()):
            errors.append(f"{rule}: {path} ({count}); zero tolerance")
    for rule in BUDGET_RULES:
        recorded = baseline.get(rule, {})
        for path, count in sorted(counts[rule].items()):
            allowed = int(recorded.get(path, 0))
            if count > allowed:
                errors.append(f"{rule}: {path} {count} > baseline {allowed}")

    if errors:
        print("[FAIL] playwright vendor coupling guard")
        for error in errors:
            print(f"- {error}")
        for rule in (*ZERO_TOLERANCE_RULES, *BUDGET_RULES):
            shown = locations.get(rule) or []
            if shown and any(error.startswith(rule) for error in errors):
                print(f"  {rule} first locations: {', '.join(shown)}")
        print("- fix the probe to assert business facts or documented public surface")
        print("- only shrinking an existing entry is allowed; never raise the baseline to pass")
        return 1

    print("[OK] playwright vendor coupling guard")
    print(f"- scanned_files: {len(scope_files())}")
    for rule in (*ZERO_TOLERANCE_RULES, *BUDGET_RULES):
        mode = "zero" if rule in ZERO_TOLERANCE_RULES else "decrease-only"
        print(f"- {rule}: mode={mode} files={len(counts[rule])} total={sum(counts[rule].values())}")
        if rule in BUDGET_RULES:
            recorded_total = sum(int(value) for value in baseline.get(rule, {}).values())
            print(f"  recorded_total={recorded_total} headroom={max(recorded_total - sum(counts[rule].values()), 0)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
