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
CONFIG_CENTER_GROUP_LABEL = "产品配置"
LEGACY_CONFIG_GROUP_LABELS = {"配置中心", "基础设置", "系统设置", "业务配置"}
PRODUCT_NAVIGATION_V2_GROUP_ALIASES = {
    "物资与分包": "项目中心",
    "施工管理": "项目中心",
    "组织行政": "行政中心",
    "基础资料": "行政中心",
    "人事行政": "行政中心",
    "资料证照": "行政中心",
}

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
}

# Business-decision targets remain fail-closed until their formal product
# ownership is approved. R11F2 resolved the only outstanding target by
# installing the independent tax-certificate model, action, and menu.
FORMAL_BUSINESS_DECISION_REQUIRED_TARGETS = {}

# A declared scene entry is a contracted navigation identity that carries no
# business action. Its identity is the native menu anchor plus the declared
# scene, and it is authorized by the same (menu_id, action_id=0) pair as every
# other entry. It has no res_model and no view structure to export, so the
# scene channel - never an action route - is what it navigates to.
SCENE_ENTRY_POLICIES = ("scene_entry",)
SCENE_ENTRY_TARGET_SCENE_KEY_FIELD = "target_scene_key"

# Declarative per-role landing surface carried by the versioned product contract.
# The platform identity resolver only projects this data; it is never derived
# from business facts and never hard-coded per role in runtime code.
ROLE_SURFACE_KEY = "role_surface"
ROLE_SURFACE_LANDING_FIELD = "landing_scene_candidates"
PLATFORM_SAFE_LANDING_SCENE = "workspace.home"

# Product default role set carried by the same versioned contract.  The
# catalog is a shipped default that a runtime may extend; it is never an
# authorization by itself.  Every non-synthetic role must bind at least one
# real group xmlid, because the delivered authority is always the
# intersection of the declaration with the principal's real group and
# record-rule visibility.
ROLE_CATALOG_KEY = "role_catalog"
ROLE_CATALOG_ROLES_FIELD = "default_roles"
ROLE_CATALOG_GROUP_FIELD = "group_xmlids"
# Optional capability groups for a role that also acts as a capability
# fallback.  When present they are the single declaration for the
# fallback binding, so the resolver never hard-codes a role order.
ROLE_CATALOG_CAPABILITY_GROUP_FIELD = "capability_group_xmlids"

# Versioned definitions for action-only targets that are not installed by the
# module data set. They are created only inside the formal initialization
# transaction and receive the stable XMLID above before a policy can use them.
FORMAL_INITIALIZATION_ACTION_SPECS = {
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
}


class LockedMenuPolicyContractError(RuntimeError):
    """Fail-closed contract error with an operator-safe reason code."""

    def __init__(self, code: str, detail: str = ""):
        self.code = str(code or "LOCKED_MENU_BASELINE_INVALID")
        self.detail = str(detail or "").strip()
        super().__init__(f"{self.code}: {self.detail}" if self.detail else self.code)


def _text(value) -> str:
    return str(value or "").strip()


def is_declared_scene_entry(row) -> bool:
    """True when a contract row declares a scene entry with no business action."""
    source = row if isinstance(row, dict) else {}
    declared = {_text(source.get("disposition_policy")), _text(source.get("entry_target_policy"))}
    return any(policy in declared for policy in SCENE_ENTRY_POLICIES)


def declared_scene_entry_key(row) -> str:
    """Declared scene key of a contract row that is a scene entry, else ''."""
    if not is_declared_scene_entry(row):
        return ""
    return _text((row if isinstance(row, dict) else {}).get(SCENE_ENTRY_TARGET_SCENE_KEY_FIELD))


def canonical_group_label(value) -> str:
    label = _text(value)
    return CONFIG_CENTER_GROUP_LABEL if label in LEGACY_CONFIG_GROUP_LABELS else label


def product_navigation_v2_group_label(value) -> str:
    label = canonical_group_label(value)
    return PRODUCT_NAVIGATION_V2_GROUP_ALIASES.get(label, label)


def stable_menu_identity(group_label: str, menu: dict) -> tuple[str, str, str]:
    row = menu if isinstance(menu, dict) else {}
    return (
        product_navigation_v2_group_label(group_label),
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


def _role_surface(product: dict) -> dict:
    surface = product.get(ROLE_SURFACE_KEY)
    return surface if isinstance(surface, dict) else {}


def _validate_role_surface(product: dict, product_key: str) -> None:
    """Validate the declarative role landing surface, when the product declares one."""
    if ROLE_SURFACE_KEY not in product:
        return
    surface = product.get(ROLE_SURFACE_KEY)
    if not isinstance(surface, dict):
        raise LockedMenuPolicyContractError(
            "LOCKED_MENU_ROLE_SURFACE_INVALID", f"{product_key} role_surface must be an object"
        )
    roles = surface.get("roles")
    if not isinstance(roles, dict) or not roles:
        raise LockedMenuPolicyContractError(
            "LOCKED_MENU_ROLE_SURFACE_INVALID", f"{product_key} role_surface.roles must be a non-empty object"
        )
    safe_scene = _text(surface.get("platform_safe_landing_scene")) or PLATFORM_SAFE_LANDING_SCENE
    if safe_scene != PLATFORM_SAFE_LANDING_SCENE:
        raise LockedMenuPolicyContractError(
            "LOCKED_MENU_ROLE_SURFACE_INVALID",
            f"{product_key} platform_safe_landing_scene must be {PLATFORM_SAFE_LANDING_SCENE}",
        )
    for role_code, role_meta in roles.items():
        role_key = _text(role_code)
        if not role_key:
            raise LockedMenuPolicyContractError(
                "LOCKED_MENU_ROLE_SURFACE_INVALID", f"{product_key} role_surface role code is empty"
            )
        if not isinstance(role_meta, dict):
            raise LockedMenuPolicyContractError(
                "LOCKED_MENU_ROLE_SURFACE_INVALID", f"{product_key} role_surface.{role_key} must be an object"
            )
        candidates = role_meta.get(ROLE_SURFACE_LANDING_FIELD)
        if not isinstance(candidates, list) or not candidates:
            raise LockedMenuPolicyContractError(
                "LOCKED_MENU_ROLE_SURFACE_INVALID",
                f"{product_key} role_surface.{role_key}.{ROLE_SURFACE_LANDING_FIELD} must be a non-empty list",
            )
        for candidate in candidates:
            if not _text(candidate):
                raise LockedMenuPolicyContractError(
                    "LOCKED_MENU_ROLE_SURFACE_INVALID",
                    f"{product_key} role_surface.{role_key} has an empty landing candidate",
                )
        # Fail closed: a declared role landing must always be able to reach the
        # platform-safe landing surface, so a released role can never be sent to
        # a scene the published route authority does not grant.
        if safe_scene not in {_text(item) for item in candidates}:
            raise LockedMenuPolicyContractError(
                "LOCKED_MENU_ROLE_SURFACE_INVALID",
                f"{product_key} role_surface.{role_key} must include {safe_scene}",
            )


def _validate_role_catalog(payload: dict, products: dict) -> None:
    """Validate the declared default role catalog and its landing alignment.

    Fail-closed rules: roles are unique and non-empty, precedence is an integer,
    every non-synthetic role binds at least one group xmlid (permission
    alignment), capability roles must be declared roles, and every catalog role
    must also carry a declared landing surface so a recognised role can never be
    left without a first hop.
    """
    if ROLE_CATALOG_KEY not in payload:
        return
    catalog = payload.get(ROLE_CATALOG_KEY)
    if not isinstance(catalog, dict):
        raise LockedMenuPolicyContractError(
            "LOCKED_MENU_ROLE_CATALOG_INVALID", f"{ROLE_CATALOG_KEY} must be an object"
        )
    rows = catalog.get(ROLE_CATALOG_ROLES_FIELD)
    if not isinstance(rows, list) or not rows:
        raise LockedMenuPolicyContractError(
            "LOCKED_MENU_ROLE_CATALOG_INVALID",
            f"{ROLE_CATALOG_KEY}.{ROLE_CATALOG_ROLES_FIELD} must be a non-empty list",
        )
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise LockedMenuPolicyContractError(
                "LOCKED_MENU_ROLE_CATALOG_INVALID", f"{ROLE_CATALOG_KEY} role must be an object"
            )
        role_code = _text(row.get("role_code"))
        if not role_code:
            raise LockedMenuPolicyContractError(
                "LOCKED_MENU_ROLE_CATALOG_INVALID", f"{ROLE_CATALOG_KEY} role_code is empty"
            )
        if role_code in seen:
            raise LockedMenuPolicyContractError(
                "LOCKED_MENU_ROLE_CATALOG_INVALID", f"{ROLE_CATALOG_KEY} duplicate role_code {role_code}"
            )
        seen.add(role_code)
        if not isinstance(row.get("precedence"), int):
            raise LockedMenuPolicyContractError(
                "LOCKED_MENU_ROLE_CATALOG_INVALID", f"{ROLE_CATALOG_KEY}.{role_code} precedence must be an integer"
            )
        groups = row.get(ROLE_CATALOG_GROUP_FIELD)
        if not isinstance(groups, list) or not groups:
            raise LockedMenuPolicyContractError(
                "LOCKED_MENU_ROLE_CATALOG_INVALID",
                f"{ROLE_CATALOG_KEY}.{role_code} must bind at least one group xmlid",
            )
        for group in groups:
            if not _text(group):
                raise LockedMenuPolicyContractError(
                    "LOCKED_MENU_ROLE_CATALOG_INVALID", f"{ROLE_CATALOG_KEY}.{role_code} has an empty group xmlid"
                )
        capability_groups = row.get(ROLE_CATALOG_CAPABILITY_GROUP_FIELD)
        if capability_groups is not None:
            if not isinstance(capability_groups, list) or not capability_groups:
                raise LockedMenuPolicyContractError(
                    "LOCKED_MENU_ROLE_CATALOG_INVALID",
                    f"{ROLE_CATALOG_KEY}.{role_code}.{ROLE_CATALOG_CAPABILITY_GROUP_FIELD} must be a non-empty list",
                )
            for group in capability_groups:
                if not _text(group):
                    raise LockedMenuPolicyContractError(
                        "LOCKED_MENU_ROLE_CATALOG_INVALID",
                        f"{ROLE_CATALOG_KEY}.{role_code} has an empty capability group xmlid",
                    )
    synthetic = catalog.get("synthetic_role_codes")
    if synthetic is not None and (
        not isinstance(synthetic, list) or any(not _text(item) for item in synthetic)
    ):
        raise LockedMenuPolicyContractError(
            "LOCKED_MENU_ROLE_CATALOG_INVALID", f"{ROLE_CATALOG_KEY}.synthetic_role_codes must be a list of strings"
        )
    for field in ("capability_role_codes", "capability_fallback_order"):
        values = catalog.get(field)
        if values is None:
            continue
        if not isinstance(values, list) or any(not _text(item) for item in values):
            raise LockedMenuPolicyContractError(
                "LOCKED_MENU_ROLE_CATALOG_INVALID", f"{ROLE_CATALOG_KEY}.{field} must be a list of strings"
            )
        unknown = sorted({_text(item) for item in values} - seen)
        if unknown:
            raise LockedMenuPolicyContractError(
                "LOCKED_MENU_ROLE_CATALOG_INVALID",
                f"{ROLE_CATALOG_KEY}.{field} names undeclared roles {unknown}",
            )
    declared_surface_roles: set[str] = set()
    for product_key in REQUIRED_PRODUCT_KEYS:
        roles = _role_surface(products.get(product_key) or {}).get("roles")
        if isinstance(roles, dict):
            declared_surface_roles.update(_text(code) for code in roles if _text(code))
    for product_key in REQUIRED_PRODUCT_KEYS:
        if not _role_surface(products.get(product_key) or {}):
            raise LockedMenuPolicyContractError(
                "LOCKED_MENU_ROLE_CATALOG_INVALID",
                f"{product_key} declares {ROLE_CATALOG_KEY} but no {ROLE_SURFACE_KEY} landing surface",
            )
    missing_landing = sorted((seen | {_text(item) for item in (synthetic or [])}) - declared_surface_roles)
    if missing_landing:
        raise LockedMenuPolicyContractError(
            "LOCKED_MENU_ROLE_CATALOG_INVALID",
            f"{ROLE_CATALOG_KEY} role(s) without a declared landing surface: {missing_landing}",
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
        _validate_role_surface(by_key[product_key], product_key)
    _validate_role_catalog(payload, by_key)
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


def product_role_surface(contract: dict, product_key: str) -> dict:
    """Declared role landing surface for one product, or an empty object."""
    products = contract.get("products") if isinstance(contract, dict) else {}
    product = products.get(product_key) if isinstance(products, dict) else None
    if not isinstance(product, dict):
        raise LockedMenuPolicyContractError("LOCKED_MENU_BASELINE_PRODUCT_MISMATCH", product_key)
    return _role_surface(product)


def role_landing_candidates(contract: dict, product_key: str) -> dict:
    """role_code -> declared landing scene candidate list for one product."""
    roles = product_role_surface(contract, product_key).get("roles")
    declared: dict = {}
    if not isinstance(roles, dict):
        return declared
    for role_code, role_meta in roles.items():
        role_key = _text(role_code)
        if not role_key or not isinstance(role_meta, dict):
            continue
        candidates = role_meta.get(ROLE_SURFACE_LANDING_FIELD)
        if isinstance(candidates, list):
            declared[role_key] = [str(item).strip() for item in candidates if _text(item)]
    return declared


def role_catalog(contract: dict) -> dict:
    """Declared default role catalog, or an empty object when absent."""
    payload = contract.get("payload") if isinstance(contract, dict) else {}
    catalog = payload.get(ROLE_CATALOG_KEY) if isinstance(payload, dict) else None
    return catalog if isinstance(catalog, dict) else {}


def role_catalog_bindings(contract: dict) -> dict:
    """``role_code -> group xmlids`` ordered by declared precedence."""
    rows = role_catalog(contract).get(ROLE_CATALOG_ROLES_FIELD)
    ordered = sorted(
        (row for row in rows if isinstance(row, dict)) if isinstance(rows, list) else [],
        key=lambda row: (row.get("precedence") or 0, _text(row.get("role_code"))),
    )
    bindings: dict = {}
    for row in ordered:
        role_code = _text(row.get("role_code"))
        if not role_code:
            continue
        bindings[role_code] = [_text(group) for group in row.get(ROLE_CATALOG_GROUP_FIELD) or [] if _text(group)]
    return bindings


def role_catalog_resolution(contract: dict) -> dict:
    """Ordered role codes plus the declared capability and synthetic roles."""
    catalog = role_catalog(contract)
    bindings = role_catalog_bindings(contract)
    rows = catalog.get(ROLE_CATALOG_ROLES_FIELD)
    metadata = {}
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        role_code = _text(row.get("role_code"))
        if not role_code:
            continue
        metadata[role_code] = {
            "label": _text(row.get("label")) or role_code,
            "identity_role": row.get("identity_role", True) is not False,
            "exclusive_surface": row.get("exclusive_surface") is True,
        }
    capability_roles = [_text(item) for item in catalog.get("capability_role_codes") or [] if _text(item)]
    return {
        "precedence": tuple(bindings.keys()),
        "bindings": bindings,
        "metadata": metadata,
        "capability_role_codes": tuple(capability_roles),
        "capability_fallback_order": tuple(
            _text(item) for item in catalog.get("capability_fallback_order") or [] if _text(item)
        ),
        "capability_groups": {
            _text(row.get("role_code")): [
                _text(group) for group in row.get(ROLE_CATALOG_CAPABILITY_GROUP_FIELD) or [] if _text(group)
            ]
            for row in rows if isinstance(row, dict)
            and _text(row.get("role_code")) in {_text(item) for item in catalog.get("capability_fallback_order") or []}
        },
        "synthetic_role_codes": tuple(
            _text(item) for item in catalog.get("synthetic_role_codes") or [] if _text(item)
        ),
        "catalog_version": _text(catalog.get("catalog_version")),
    }


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
    expected_set = set(expected)
    actual_set = set(actual)
    missing = expected_set - actual_set
    additions = actual_set - expected_set
    if missing or additions or len(actual) != len(actual_set):
        raise LockedMenuPolicyContractError(
            "LOCKED_MENU_POLICY_SYNCHRONIZATION_MISMATCH",
            f"{product_key} expected={len(expected)} actual={len(actual)} "
            f"missing={len(missing)} additions={len(additions)} duplicates={len(actual) - len(actual_set)}",
        )
    digest = hashlib.sha256(
        json.dumps(actual, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "product_key": product_key,
        "menu_count": len(actual),
        "locked_menu_count": len(expected),
        "exact_match": True,
        "normalized_sha256": digest,
    }


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
    expected_set = set(expected_projection)
    actual_set = set(actual)
    missing = expected_set - actual_set
    additions = actual_set - expected_set
    if missing or additions or len(actual) != len(actual_set):
        raise LockedMenuPolicyContractError(
            "LOCKED_MENU_SNAPSHOT_MISMATCH",
            f"{product_key} expected={len(expected_projection)} actual={len(actual)} "
            f"missing={len(missing)} additions={len(additions)} duplicates={len(actual) - len(actual_set)}",
        )
    digest = hashlib.sha256(
        json.dumps(actual, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "product_key": product_key,
        "menu_count": len(actual),
        "locked_menu_count": len(expected_projection),
        "exact_match": True,
        "normalized_sha256": digest,
    }


def normalized_page_release_state(page: dict) -> str:
    """Normalize a frozen release page the same way the runtime gate does.

    A disabled page is never effective. An enabled page without an explicit
    release state defaults to ``released`` so legacy snapshots stay comparable
    against the same caliber as current ones.
    """
    row = page if isinstance(page, dict) else {}
    if row.get("enabled") is not True:
        return "hidden"
    return _text(row.get("release_state")) or "released"


def _menu_release_projection(rows: Iterable[dict]) -> list[tuple[str, str]]:
    return [
        (
            _text(row.get("label") or row.get("name") or row.get("page_label")),
            _text(row.get("menu_xmlid") or row.get("page_key") or row.get("menu_key")),
        )
        for row in rows
        if isinstance(row, dict)
    ]


def policy_preview_rows(menu_groups) -> list[dict]:
    """Return the policy menus explicitly declared as ``preview``.

    A preview entry is a declared widening of a product face beyond the locked
    released baseline. It is allowed only when the owning policy states it, which
    keeps the widening controllable and knowable instead of an undeclared drift.
    """
    rows = []
    for group in menu_groups if isinstance(menu_groups, (list, tuple)) else []:
        if not isinstance(group, dict):
            continue
        group_label = group.get("group_label") or group.get("label") or group.get("group_key")
        for menu in group.get("menus") or []:
            if not isinstance(menu, dict):
                continue
            if menu.get("enabled") is not True or _text(menu.get("release_state")) != "preview":
                continue
            row = dict(menu)
            row["_group_label"] = _text(group_label)
            rows.append(row)
    return rows


def assert_snapshot_matches_policy_release_states(
    contract: dict,
    product_key: str,
    pages,
    menu_groups,
) -> dict:
    """Compare a frozen snapshot to the contract on one shared caliber.

    The locked baseline owns the released surface; the product policy may declare
    additional ``preview`` menus. The snapshot's released pages must equal the
    locked baseline exactly, its preview pages must equal the policy's declared
    preview set exactly, and no other effective state is tolerated. This keeps a
    larger preview face controllable (only what is declared) and knowable (the
    counts and digests are returned) without weakening the released assertion.
    """
    page_rows = [page for page in pages if isinstance(page, dict)] if isinstance(pages, list) else []
    released_pages = [page for page in page_rows if normalized_page_release_state(page) == "released"]
    preview_pages = [page for page in page_rows if normalized_page_release_state(page) == "preview"]
    others = [page for page in page_rows if normalized_page_release_state(page) not in {"released", "preview"}]
    if others:
        raise LockedMenuPolicyContractError(
            "LOCKED_MENU_SNAPSHOT_MISMATCH",
            f"{product_key} frozen snapshot contains {len(others)} non-effective page(s)",
        )
    released_match = assert_snapshot_matches_locked_contract(contract, product_key, released_pages)
    declared_preview = _menu_release_projection(policy_preview_rows(menu_groups))
    actual_preview = _menu_release_projection(preview_pages)
    expected_preview_set = set(declared_preview)
    actual_preview_set = set(actual_preview)
    missing = expected_preview_set - actual_preview_set
    additions = actual_preview_set - expected_preview_set
    if missing or additions or len(actual_preview) != len(actual_preview_set):
        raise LockedMenuPolicyContractError(
            "LOCKED_MENU_SNAPSHOT_PREVIEW_MISMATCH",
            f"{product_key} declared={len(declared_preview)} snapshot={len(actual_preview)} "
            f"missing={len(missing)} additions={len(additions)}",
        )
    return {
        "product_key": product_key,
        "released_count": len(released_pages),
        "preview_count": len(preview_pages),
        "effective_count": len(released_pages) + len(preview_pages),
        "locked_released_count": int(released_match.get("locked_menu_count") or 0),
        "declared_preview_count": len(declared_preview),
        "released_normalized_sha256": _text(released_match.get("normalized_sha256")),
        "exact_match": True,
    }


def resolve_declared_product_keys(
    raw=None,
    *,
    default: Iterable[str] = REQUIRED_PRODUCT_KEYS,
    allowed: Iterable[str] = REQUIRED_PRODUCT_KEYS,
) -> tuple[str, ...]:
    """Resolve an explicitly declared product scope, failing closed on unknown keys.

    An empty declaration falls back to the full published scope; naming a product
    outside ``allowed`` is an error rather than a silent narrowing of the check.
    """
    keys = tuple(item.strip() for item in str(raw or "").split(",") if item.strip())
    keys = keys or tuple(default)
    unknown = sorted(set(keys) - set(allowed))
    if unknown:
        raise LockedMenuPolicyContractError(
            "PRODUCT_MENU_CATALOG_PRODUCT_KEYS_INVALID",
            f"unknown product key(s): {unknown}",
        )
    return keys
