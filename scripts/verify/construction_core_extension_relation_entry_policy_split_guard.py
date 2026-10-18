#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import line_budgets  # noqa: E402


ROOT = Path(__file__).resolve().parents[2]
CORE_EXTENSION = ROOT / "addons/smart_construction_core/core_extension.py"
RELATION_POLICY = ROOT / "addons/smart_construction_core/core_extension_relation_entry_policy.py"
CI = ROOT / "make/ci.mk"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.is_file() else ""


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    errors: list[str] = []
    core_text = _read(CORE_EXTENSION)
    policy_text = _read(RELATION_POLICY)
    ci_text = _read(CI)

    if not core_text:
        errors.append(f"missing core extension file: {CORE_EXTENSION.relative_to(ROOT)}")
    if not policy_text:
        errors.append(f"missing relation entry policy module: {RELATION_POLICY.relative_to(ROOT)}")

    if core_text:
        line_count = len(core_text.splitlines())
        line_budgets.advise_size("addons/smart_construction_core/core_extension.py", line_count, label="core_extension.py")
        for token in [
            "core_extension_relation_entry_policy as _relation_entry_policy",
            "return _relation_entry_policy.smart_core_relation_entry_policy(env, payload)",
        ]:
            if token not in core_text:
                errors.append(f"core_extension.py missing relation entry split token: {token}")

    if policy_text:
        line_count = len(policy_text.splitlines())
        line_budgets.advise_size(
            "addons/smart_construction_core/core_extension_relation_entry_policy.py",
            line_count,
            label="core_extension_relation_entry_policy.py",
        )
        for token in [
            "def smart_core_relation_entry_policy(",
            '"type_tax_use": "none"',
            '"amount_type": "percent"',
            "finance.self_funding.refund",
            "finance.deduction.bill",
            "contract.income.supplement",
            "contract.expense.supplement",
            '"search_more": "搜索承包人..."',
            '"search_more": "搜索责任方..."',
            '"search_more": "搜索原合同..."',
        ]:
            if token not in policy_text:
                errors.append(f"relation entry policy module missing token: {token}")
        for forbidden in (".write(", ".create(", ".unlink(", "commit(", "requests.", "registry["):
            if forbidden in policy_text:
                errors.append(f"relation entry policy module must not own write/registry side effects; forbidden token: {forbidden}")

    if "python3 scripts/verify/construction_core_extension_relation_entry_policy_split_guard.py" not in ci_text:
        errors.append("ci.local.quick must run construction_core_extension_relation_entry_policy_split_guard.py")

    if not errors:
        policy = _load(RELATION_POLICY, "construction_core_extension_relation_entry_policy_under_guard")
        unknown = policy.smart_core_relation_entry_policy(None, {"model": "res.partner", "relation": "res.users"})
        if unknown is not None:
            errors.append(f"unknown relation must return None, got: {unknown}")
        contract = policy.smart_core_relation_entry_policy(
            None,
            {
                "model": "construction.contract",
                "relation": "construction.contract",
                "field_name": "original_contract_id",
                "context": {"default_type": "in"},
            },
        )
        if not isinstance(contract, dict) or contract.get("domain") != [["type", "=", "in"]]:
            errors.append(f"contract supplement relation must stay direction-scoped: {contract}")
        supplement = policy.smart_core_relation_entry_policy(
            None,
            {
                "model": "construction.contract",
                "relation": "construction.contract",
                "field_name": "original_contract_id",
                "context": {"current_business_category_code": "contract.expense.supplement"},
            },
        )
        if not isinstance(supplement, dict) or supplement.get("domain") != [["type", "=", "in"]]:
            errors.append(f"expense supplement relation must stay direction-scoped: {supplement}")

    if errors:
        print("[construction_core_extension_relation_entry_policy_split_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("[construction_core_extension_relation_entry_policy_split_guard] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
