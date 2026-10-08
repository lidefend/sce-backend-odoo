#!/usr/bin/env python3
"""Fail-closed enforcement of the frontend contract-basis boundary.

Rule: everything the frontend consumes beyond rendering and interaction must come
from the contract. A frontend judgement without contract basis IS a contract
defect; it must be closed at the declaration layer, never backfilled by a
frontend default. This guard binds each registered declaration to its declaration
site, its consuming symbol and its stop behaviour, and refuses unregistered
mechanism constants that claim to carry product semantics.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / "docs/architecture/frontend_contract_basis_ledger.json"
MAKE_GLOBS = ("make/*.mk",)
STOP_BEHAVIOURS = ("stop",)


def load_ledger(path: Path = LEDGER) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema") != "frontend.contract-basis.ledger.v1":
        raise ValueError("unexpected ledger schema")
    return data


def registered_targets() -> set[str]:
    targets: set[str] = set()
    for pattern in MAKE_GLOBS:
        for path in ROOT.glob(pattern):
            targets.update(re.findall(r"^([A-Za-z0-9_.-]+)\s*:", path.read_text(encoding="utf-8", errors="ignore"), re.M))
    return targets


def read(relative: str) -> str:
    path = ROOT / relative
    if not path.is_file():
        raise ValueError(f"missing file: {relative}")
    return path.read_text(encoding="utf-8", errors="ignore")


# High-signal patterns for "the frontend decided something the contract did not".
# Vocabulary dispatch on declared values (componentKey/semanticType/field type) is
# the renderer's own job and is deliberately not scanned: switching on a declared
# kind is consumption, not invention.
SCAN_ROOTS = ("frontend/apps/web/src",)
SCAN_RULES = (
    ("frontend_selected_data_volume", re.compile(r"limit\s*:\s*\d+")),
    (
        "contract_parameter_fallback",
        re.compile(
            r"(page_size|pageSize|variance_tolerance|default_sample_limit|group_sample_limit|page_limit|failed_page_limit)"
            r"\s*(\|\||\?\?)\s*(\d|\[|')"
        ),
    ),
    ("request_default_page_size", re.compile(r"limit\s*(\|\||\?\?)\s*\d+")),
)


def scan_sites() -> dict[str, set[str]]:
    found: dict[str, set[str]] = {}
    for root in SCAN_ROOTS:
        for path in sorted((ROOT / root).rglob("*")):
            if not path.is_file() or path.suffix not in (".ts", ".vue"):
                continue
            if path.name.endswith((".test.ts", ".spec.ts", ".d.ts")):
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            relative = path.relative_to(ROOT).as_posix()
            for name, pattern in SCAN_RULES:
                if pattern.search(text):
                    found.setdefault(relative, set()).add(name)
    return found


def check(ledger: dict, targets: set[str] | None = None, scanned: dict[str, set[str]] | None = None) -> list[str]:
    targets = registered_targets() if targets is None else targets
    errors: list[str] = []
    bindings = ledger.get("declarationBindings")
    if not isinstance(bindings, list) or not bindings:
        return ["declarationBindings must be a non-empty list"]
    for binding in bindings:
        surface = binding.get("surface", "<unnamed>")
        try:
            declared_text = read(binding["declaredBy"])
            consumed_text = read(binding["consumedBy"])
            read(binding["behaviourTest"])
        except (KeyError, ValueError) as exc:
            errors.append(f"{surface}: {exc}")
            continue
        if binding.get("declaredSymbol") not in declared_text:
            errors.append(f"{surface}: declaration site no longer publishes {binding.get('declaredSymbol')}")
        if binding.get("consumedSymbol") not in consumed_text:
            errors.append(f"{surface}: consumption no longer goes through {binding.get('consumedSymbol')}")
        if binding.get("stopSymbol") not in consumed_text:
            errors.append(f"{surface}: missing fail-closed stop symbol {binding.get('stopSymbol')}")
        if binding.get("onMissing") not in STOP_BEHAVIOURS:
            errors.append(f"{surface}: onMissing must fail closed, got {binding.get('onMissing')!r}")
        if binding.get("regressionGuard") not in targets:
            errors.append(f"{surface}: regression guard {binding.get('regressionGuard')!r} is not a registered make target")
    for exemption in ledger.get("registeredMechanismExemptions", []):
        symbol = exemption.get("symbol", "<unnamed>")
        try:
            text = read(exemption["file"])
        except (KeyError, ValueError) as exc:
            errors.append(f"exemption {symbol}: {exc}")
            continue
        if symbol not in text:
            errors.append(f"exemption {symbol}: declared symbol is gone from {exemption.get('file')}")
        if exemption.get("carriesProductSemantics") is not False:
            errors.append(f"exemption {symbol}: a mechanism exemption must not carry product semantics")
        if not exemption.get("rationale"):
            errors.append(f"exemption {symbol}: a mechanism exemption requires a recorded rationale")
    inventory = ledger.get("frontendLogicInventory")
    if not isinstance(inventory, list) or not inventory:
        errors.append("frontendLogicInventory must be a non-empty list")
        inventory = []
    registered = {}
    for entry in inventory:
        relative = entry.get("file")
        if not relative or not isinstance(entry.get("classes"), list) or not entry.get("classes"):
            errors.append(f"frontend logic entry needs file + classes: {entry!r}")
            continue
        if not entry.get("reason"):
            errors.append(f"frontend logic entry needs a reason: {relative}")
        if entry.get("verdict") not in (
            "renderer_dispatch",
            "registered_mechanism",
            "contract_declared_consumption",
            "contract_defect_open",
        ):
            errors.append(f"frontend logic entry needs a known verdict: {relative}")
        registered[relative] = entry
        if entry.get("verdict") == "contract_defect_open" and not entry.get("defectId"):
            errors.append(f"an open contract defect must reference its ledger entry: {relative}")
    for relative, classes in (scan_sites() if scanned is None else scanned).items():
        entry = registered.get(relative)
        if entry is None:
            errors.append(f"unregistered frontend logic site ({sorted(classes)}): {relative}")
            continue
        missing = sorted(classes - set(entry["classes"]))
        if missing:
            errors.append(f"{relative}: unregistered frontend logic classes {missing}")
    open_ids = {defect.get("id") for defect in ledger.get("openContractDefects", [])}
    for entry in inventory:
        defect_id = entry.get("defectId")
        if defect_id and defect_id not in open_ids:
            errors.append(f"{entry.get('file')}: unknown open contract defect {defect_id}")
    for defect in ledger.get("openContractDefects", []):
        for field in ("id", "missing", "owner", "closureCondition"):
            if not defect.get(field):
                errors.append(f"open contract defect {defect.get('id', '<unnamed>')}: missing {field}")
    return errors


def enforcement_stop_reasons(ledger: dict) -> list[str]:
    """机制：出现前端判断即停机，回契约要结果。

    交付车道必须 fail-closed：只要还有未闭合的契约缺陷（openContractDefects 或
    verdict=contract_defect_open 的站点），就不得冻结/放行，必须由声明层补齐声明。
    """
    reasons: list[str] = []
    for defect in ledger.get("openContractDefects", []):
        reasons.append(f"{defect.get('id')}: 缺失 {defect.get('missing')} | 归属 {defect.get('owner')}")
    open_entries = [
        entry for entry in ledger.get("frontendLogicInventory", [])
        if entry.get("verdict") == "contract_defect_open"
    ]
    if open_entries:
        reasons.append(f"受影响前端站点 {len(open_entries)} 个")
    return reasons


def main() -> int:
    try:
        ledger = load_ledger()
    except (OSError, ValueError) as exc:
        print(f"[frontend_contract_basis_guard] FAIL {exc}")
        return 1
    if "--list-candidates" in sys.argv:
        for relative, classes in sorted(scan_sites().items()):
            print(f"{relative}\t{','.join(sorted(classes))}")
        return 0
    enforce = "--enforce" in sys.argv
    errors = check(ledger)
    if errors:
        print("[frontend_contract_basis_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    open_defects = ledger.get("openContractDefects", [])
    print(
        "[frontend_contract_basis_guard] PASS bindings="
        f"{len(ledger['declarationBindings'])} exemptions={len(ledger.get('registeredMechanismExemptions', []))} "
        f"logic_sites={len(ledger['frontendLogicInventory'])} open_defects={len(open_defects)}"
    )
    if enforce:
        stop_reasons = enforcement_stop_reasons(ledger)
        if stop_reasons:
            # 机制：出现前端判断即停机，回契约要结果。交付车道禁止带着未闭合契约缺陷冻结。
            print("[frontend_contract_basis_guard] STOP 存在未闭合的契约缺陷：交付（freeze）车道禁止放行")
            for reason in stop_reasons:
                print(f"- {reason}")
            print("- 收口条件见 ledger.openContractDefects[].closureCondition")
            print("- 下一步：由声明层补齐声明并由前端原样消费（缺失即 ContractGapError 停机），再重跑本守卫")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
