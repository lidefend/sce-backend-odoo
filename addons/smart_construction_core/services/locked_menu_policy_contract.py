# -*- coding: utf-8 -*-
"""Versioned construction menu policy contract shared by release paths.

The repository JSON file is the source contract.  Production images carry the
same bytes at a fixed path plus a versioned SHA-256 lock.  Runtime code never
generates or downloads this contract.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable


BASELINE_FILE = "formal_business_product_menu_policy_v1.json"
BASELINE_CHECKSUM_FILE = f"{BASELINE_FILE}.sha256"
BASELINE_SCHEMA = "formal_business_product_menu_policy.v1"
IMAGE_CONTRACT_ROOT = Path("/opt/sce-product/contracts")
REQUIRED_PRODUCT_KEYS = ("construction.standard", "construction.preview")
CONFIG_CENTER_GROUP_LABEL = "配置中心"
LEGACY_CONFIG_GROUP_LABELS = {"基础设置", "系统设置", "业务配置"}

# These locked entries are intentionally delivered as action-only navigation
# surfaces. Their policy identity remains the versioned menu XMLID, while the
# runtime target is resolved through a stable action XMLID. Historical numeric
# IDs embedded in evidence baselines are never used as identity.
FORMAL_ACTION_ONLY_MENU_TARGETS = {
    "smart_construction_core.menu_sc_material_rental_in_acceptance": "smart_construction_core.action_sc_material_rental_in_acceptance",
    "smart_construction_core.menu_sc_material_rental_return_acceptance": "smart_construction_core.action_sc_material_rental_return_acceptance",
    "smart_construction_core.menu_sc_legacy_fuel_card_fact_acceptance": "smart_construction_core.action_sc_fuel_card_registration_formal",
    "smart_construction_core.menu_sc_legacy_fuel_card_recharge_fact_acceptance": "smart_construction_core.action_sc_fuel_card_recharge_formal",
    "smart_construction_core.menu_sc_company_user_roster_formal": "smart_construction_core.action_sc_company_user_roster_formal",
    "smart_construction_core.menu_sc_salary_registration_legacy_55_formal": "smart_construction_core.action_sc_salary_registration",
    "smart_construction_core.menu_sc_company_document_archive": "smart_construction_core.action_sc_company_document_archive",
    "smart_construction_core.menu_sc_tax_certificate_registration_user": "smart_construction_core.action_sc_tax_certificate_registration_user",
}

# Versioned definitions for action-only targets that are not installed by the
# module data set. They are created only inside the formal initialization
# transaction and receive the stable XMLID above before a policy can use them.
FORMAL_INITIALIZATION_ACTION_SPECS = {
    "smart_construction_core.action_sc_fuel_card_registration_formal": {
        "name": "油卡登记",
        "res_model": "sc.fund.account.operation",
        "domain": "[('legacy_source_model', '=', 'online_old_legacy_direct:direct_acceptance'), ('legacy_source_table', '=', 'direct_acceptance:油卡登记')]",
        "context": "{'create': False}",
    },
    "smart_construction_core.action_sc_fuel_card_recharge_formal": {
        "name": "充值登记",
        "res_model": "sc.fund.account.operation",
        "domain": "[('legacy_source_model', '=', 'online_old_legacy_direct:direct_acceptance'), ('legacy_source_table', '=', 'direct_acceptance:充值登记')]",
        "context": "{'create': False}",
    },
    "smart_construction_core.action_sc_company_user_roster_formal": {
        "name": "公司人员名册",
        "res_model": "res.users",
        "domain": "[('share', '=', False)]",
        "context": "{'create': False}",
    },
    "smart_construction_core.action_sc_company_document_archive": {
        "name": "公司资料存档",
        "res_model": "sc.document.admin.document",
        "domain": "[('fact_type', '=', 'company_document_archive')]",
        "context": "{'default_fact_type': 'company_document_archive'}",
    },
    "smart_construction_core.action_sc_tax_certificate_registration_user": {
        "name": "外经证登记",
        "res_model": "sc.legacy.payment.residual.fact",
        "domain": "[]",
        "context": "{'create': False}",
    },
}


class LockedMenuPolicyContractError(RuntimeError):
    """Fail-closed contract error with an operator-safe reason code."""

    def __init__(self, code: str, detail: str = ""):
        self.code = str(code or "LOCKED_MENU_BASELINE_INVALID")
        self.detail = str(detail or "").strip()
        super().__init__(f"{self.code}: {self.detail}" if self.detail else self.code)


def _text(value) -> str:
    return str(value or "").strip()


def canonical_group_label(value) -> str:
    label = _text(value)
    return CONFIG_CENTER_GROUP_LABEL if label in LEGACY_CONFIG_GROUP_LABELS else label


def stable_menu_identity(group_label: str, menu: dict) -> tuple[str, str, str]:
    row = menu if isinstance(menu, dict) else {}
    return (
        canonical_group_label(group_label),
        _text(row.get("label") or row.get("name") or row.get("page_label")),
        _text(row.get("menu_xmlid") or row.get("page_key") or row.get("menu_key")),
    )


def _source_contract_root() -> Path:
    # services -> smart_construction_core -> addons -> repository root
    return Path(__file__).resolve().parents[3] / "scripts" / "verify" / "baselines"


def default_contract_paths() -> tuple[Path, Path]:
    image_baseline = IMAGE_CONTRACT_ROOT / BASELINE_FILE
    image_checksum = IMAGE_CONTRACT_ROOT / BASELINE_CHECKSUM_FILE
    if image_baseline.is_file() or image_checksum.is_file():
        return image_baseline, image_checksum
    source_root = _source_contract_root()
    return source_root / BASELINE_FILE, source_root / BASELINE_CHECKSUM_FILE


def _expected_sha256(path: Path) -> str:
    try:
        tokens = path.read_text(encoding="utf-8").strip().split()
    except FileNotFoundError as exc:
        raise LockedMenuPolicyContractError("LOCKED_MENU_BASELINE_MISSING", str(path)) from exc
    except OSError as exc:
        raise LockedMenuPolicyContractError("LOCKED_MENU_BASELINE_INVALID", str(exc)) from exc
    expected = _text(tokens[0] if tokens else "").lower()
    if len(expected) != 64 or any(char not in "0123456789abcdef" for char in expected):
        raise LockedMenuPolicyContractError("LOCKED_MENU_BASELINE_INVALID", "invalid sha256 lock")
    return expected


def _validate_product(product: dict, product_key: str) -> None:
    groups = product.get("menu_groups")
    if not isinstance(groups, list) or not groups:
        raise LockedMenuPolicyContractError(
            "LOCKED_MENU_BASELINE_INVALID", f"{product_key} menu_groups must be a non-empty list"
        )
    rows = []
    for group in groups:
        if not isinstance(group, dict):
            raise LockedMenuPolicyContractError("LOCKED_MENU_BASELINE_INVALID", f"{product_key} group is not an object")
        group_label = group.get("group_label") or group.get("label")
        menus = group.get("menus")
        if not isinstance(menus, list):
            raise LockedMenuPolicyContractError(
                "LOCKED_MENU_BASELINE_INVALID", f"{product_key} group menus must be a list"
            )
        for menu in menus:
            if not isinstance(menu, dict):
                raise LockedMenuPolicyContractError(
                    "LOCKED_MENU_BASELINE_INVALID", f"{product_key} menu is not an object"
                )
            identity = stable_menu_identity(group_label, menu)
            if not all(identity):
                raise LockedMenuPolicyContractError(
                    "LOCKED_MENU_BASELINE_NORMALIZATION_MISMATCH", f"{product_key} incomplete identity {identity!r}"
                )
            if menu.get("enabled") is not True or _text(menu.get("release_state")) != "released":
                raise LockedMenuPolicyContractError(
                    "LOCKED_MENU_BASELINE_INVALID", f"{product_key} non-released locked menu {identity!r}"
                )
            rows.append(identity)
    if len(rows) != len(set(rows)):
        raise LockedMenuPolicyContractError(
            "LOCKED_MENU_BASELINE_NORMALIZATION_MISMATCH", f"{product_key} duplicate stable menu identity"
        )


def load_locked_menu_policy_contract(
    baseline_path: str | Path | None = None,
    checksum_path: str | Path | None = None,
) -> dict:
    default_baseline, default_checksum = default_contract_paths()
    baseline = Path(baseline_path) if baseline_path is not None else default_baseline
    checksum = Path(checksum_path) if checksum_path is not None else default_checksum
    try:
        raw = baseline.read_bytes()
    except FileNotFoundError as exc:
        raise LockedMenuPolicyContractError("LOCKED_MENU_BASELINE_MISSING", str(baseline)) from exc
    except OSError as exc:
        raise LockedMenuPolicyContractError("LOCKED_MENU_BASELINE_INVALID", str(exc)) from exc
    expected_sha256 = _expected_sha256(checksum)
    actual_sha256 = hashlib.sha256(raw).hexdigest()
    if actual_sha256 != expected_sha256:
        raise LockedMenuPolicyContractError(
            "LOCKED_MENU_BASELINE_INVALID",
            f"sha256 mismatch expected={expected_sha256} actual={actual_sha256}",
        )
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LockedMenuPolicyContractError("LOCKED_MENU_BASELINE_INVALID", f"invalid json: {exc}") from exc
    if not isinstance(payload, dict) or _text(payload.get("schema")) != BASELINE_SCHEMA:
        raise LockedMenuPolicyContractError("LOCKED_MENU_BASELINE_INVALID", "schema mismatch")
    products = payload.get("products")
    if not isinstance(products, list):
        raise LockedMenuPolicyContractError("LOCKED_MENU_BASELINE_INVALID", "products must be a list")
    by_key = {}
    for product in products:
        if not isinstance(product, dict):
            raise LockedMenuPolicyContractError("LOCKED_MENU_BASELINE_INVALID", "product is not an object")
        product_key = _text(product.get("product_key"))
        if not product_key or product_key in by_key:
            raise LockedMenuPolicyContractError("LOCKED_MENU_BASELINE_PRODUCT_MISMATCH", product_key or "missing key")
        by_key[product_key] = product
    missing = sorted(set(REQUIRED_PRODUCT_KEYS) - set(by_key))
    if missing:
        raise LockedMenuPolicyContractError("LOCKED_MENU_BASELINE_PRODUCT_MISMATCH", f"missing={missing}")
    for product_key in REQUIRED_PRODUCT_KEYS:
        _validate_product(by_key[product_key], product_key)
    return {
        "path": str(baseline),
        "sha256": actual_sha256,
        "payload": payload,
        "products": by_key,
    }


def baseline_rows(contract: dict, product_key: str) -> list[tuple[str, str, str]]:
    products = contract.get("products") if isinstance(contract, dict) else {}
    product = products.get(product_key) if isinstance(products, dict) else None
    if not isinstance(product, dict):
        raise LockedMenuPolicyContractError("LOCKED_MENU_BASELINE_PRODUCT_MISMATCH", product_key)
    return [
        stable_menu_identity(group.get("group_label") or group.get("label"), menu)
        for group in product.get("menu_groups") or []
        for menu in group.get("menus") or []
        if isinstance(group, dict) and isinstance(menu, dict)
    ]


def policy_rows(menu_groups: Iterable[dict]) -> list[tuple[str, str, str]]:
    rows = []
    for group in menu_groups if isinstance(menu_groups, (list, tuple)) else []:
        if not isinstance(group, dict):
            continue
        group_label = group.get("group_label") or group.get("label") or group.get("group_key")
        for menu in group.get("menus") or []:
            if not isinstance(menu, dict):
                continue
            if menu.get("enabled") is True and _text(menu.get("release_state")) == "released":
                rows.append(stable_menu_identity(group_label, menu))
    return rows


def assert_policy_matches_locked_contract(contract: dict, product_key: str, menu_groups) -> dict:
    expected = baseline_rows(contract, product_key)
    actual = policy_rows(menu_groups)
    if actual != expected:
        raise LockedMenuPolicyContractError(
            "LOCKED_MENU_POLICY_SYNCHRONIZATION_MISMATCH",
            f"{product_key} expected={len(expected)} actual={len(actual)}",
        )
    digest = hashlib.sha256(
        json.dumps(actual, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {"product_key": product_key, "menu_count": len(actual), "normalized_sha256": digest}


def assert_snapshot_matches_locked_contract(contract: dict, product_key: str, pages) -> dict:
    expected = baseline_rows(contract, product_key)
    actual = []
    for page in pages if isinstance(pages, list) else []:
        if not isinstance(page, dict):
            continue
        if page.get("enabled") is not True or _text(page.get("release_state")) != "released":
            raise LockedMenuPolicyContractError(
                "LOCKED_MENU_SNAPSHOT_MISMATCH", f"{product_key} contains non-released snapshot page"
            )
        actual.append(
            (
                _text(page.get("label") or page.get("name") or page.get("page_label")),
                _text(page.get("menu_xmlid") or page.get("page_key") or page.get("menu_key")),
            )
        )
    expected_projection = [(label, menu_xmlid) for _group, label, menu_xmlid in expected]
    if actual != expected_projection:
        raise LockedMenuPolicyContractError(
            "LOCKED_MENU_SNAPSHOT_MISMATCH",
            f"{product_key} expected={len(expected_projection)} actual={len(actual)}",
        )
    digest = hashlib.sha256(
        json.dumps(actual, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {"product_key": product_key, "menu_count": len(actual), "normalized_sha256": digest}
