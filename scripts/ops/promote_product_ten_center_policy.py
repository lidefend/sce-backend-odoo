#!/usr/bin/env python3
"""Promote the locked construction policy to the approved ten-center runtime.

This is a source-contract migration, not a runtime fallback.  It preserves
every released menu identity, removes the two retired first-level centers,
and admits the installed Odoo accounting foundations through their stable
menu/action/model identities.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "scripts/verify/baselines/formal_business_product_menu_policy_v1.json"
CHECKSUM = BASELINE.with_suffix(BASELINE.suffix + ".sha256")

TARGET_CENTERS = (
    "工作台",
    "项目中心",
    "合同中心",
    "成本中心",
    "财务中心",
    "税务中心",
    "会计账务中心",
    "报表中心",
    "行政中心",
    "产品配置",
)

LEGACY_CENTER_TARGET = {
    "物资与分包": "项目中心",
    "施工管理": "项目中心",
    "组织行政": "行政中心",
    "配置中心": "产品配置",
    "基础设置": "产品配置",
    "系统设置": "产品配置",
    "业务配置": "产品配置",
}

ACCOUNTING_MENUS = (
    ("日记账分录", "account.menu_action_move_journal_line_form", "account.action_move_journal_line", "account.move", "凭证与分录"),
    ("日记账项目", "account.menu_action_account_moves_all", "account.action_account_moves_all", "account.move.line", "凭证与分录"),
    ("会计科目表", "account.menu_action_account_form", "account.action_account_form", "account.account", "会计科目"),
    ("日记账", "account.menu_action_account_journal_form", "account.action_account_journal_form", "account.journal", "账簿基础"),
    ("分析账户", "account.account_analytic_def_account", "analytic.action_account_analytic_account_form", "account.analytic.account", "分析核算"),
    ("分析分配模型", "account.menu_analytic__distribution_model", "analytic.action_analytic_distribution_model", "account.analytic.distribution.model", "分析核算"),
)


def _center_label(group: dict) -> str:
    return str(group.get("group_label") or group.get("label") or group.get("title") or "").strip()


def _target_label(group: dict) -> str:
    label = _center_label(group)
    return LEGACY_CENTER_TARGET.get(label, label)


def _rewrite_visible_path(value: object, target: str, label: str) -> str:
    parts = [part.strip() for part in str(value or "").split("/") if part.strip()]
    if not parts:
        return f"智慧施工管理平台 / {target} / {label}"
    if len(parts) == 1:
        return f"{parts[0]} / {target} / {label}"
    parts[1] = target
    return " / ".join(parts)


def _accounting_row(label: str, menu_xmlid: str, action_xmlid: str, model: str, domain_label: str) -> dict:
    capability_key = "construction.menu.%s" % menu_xmlid.replace(".", "_")
    return {
        "access_level": "public",
        "action_xmlid": action_xmlid,
        "business_entry_contract_version": "business_entry_disposition.v1",
        "capability_key": capability_key,
        "control_granularity": "user_visible_menu_page",
        "control_object": "Odoo 原生会计账务能力入口",
        "disposition_policy": "keep_list_form",
        "enabled": True,
        "entry_intent": "handling",
        "entry_intent_label": "办理",
        "entry_target_policy": "keep_list_form",
        "group_key": "construction.会计账务中心",
        "group_label": "会计账务中心",
        "integration_target": f"{model} {label}",
        "label": label,
        "locked_data_policy": "odoo_model_acl_and_record_rules",
        "menu_key": menu_xmlid,
        "menu_xmlid": menu_xmlid,
        "model": model,
        "name": label,
        "page_key": menu_xmlid,
        "page_label": label,
        "policy_note": "odoo_native_accounting_foundation_admitted_to_p1",
        "product_domain": "accounting",
        "product_domain_label": domain_label,
        "product_key": "会计账务中心",
        "productization_source": "odoo_native_accounting_foundation",
        "release_domain": "construction",
        "release_state": "released",
        "res_model": model,
        "source_kind": "odoo_native_accounting_foundation",
        "target_scene_key": "",
        "title": label,
        "view_modes": ["tree", "form"],
        "visible_menu_path": f"智慧施工管理平台 / 会计账务中心 / {domain_label} / {label}",
    }


def _capability_from_menu(row: dict) -> dict:
    keys = (
        "access_level", "allowed_business_category_codes", "capability_key",
        "control_object", "default_business_category_code", "delivery_level",
        "disposition_policy", "enabled", "entry_intent", "entry_intent_label",
        "entry_kind", "entry_target_policy", "group_key", "group_label",
        "integration_target", "label", "menu_xmlid", "product_domain",
        "product_domain_label", "product_key", "release_state", "res_model",
        "source_kind", "target_scene_key", "visible_menu_path",
    )
    capability = {key: row[key] for key in keys if key in row}
    capability.setdefault("entry_kind", "user_visible_menu_page")
    capability["target_page_key"] = str(row.get("page_key") or row.get("menu_xmlid") or "")
    return capability


def promote(payload: dict) -> dict:
    for product in payload.get("products") or []:
        rows_by_center = {center: [] for center in TARGET_CENTERS}
        seen_xmlids: set[str] = set()
        for group in product.get("menu_groups") or []:
            target = _target_label(group)
            if target not in rows_by_center:
                raise ValueError(f"unapproved first-level product center: {_center_label(group)!r}")
            for source_row in group.get("menus") or []:
                row = dict(source_row)
                menu_xmlid = str(row.get("menu_xmlid") or row.get("page_key") or "").strip()
                if not menu_xmlid or menu_xmlid in seen_xmlids:
                    raise ValueError(f"missing or duplicate menu identity: {menu_xmlid!r}")
                seen_xmlids.add(menu_xmlid)
                label = str(row.get("label") or row.get("name") or row.get("page_label") or "").strip()
                row["group_key"] = f"construction.{target}"
                row["group_label"] = target
                row["product_key"] = target
                row["visible_menu_path"] = _rewrite_visible_path(row.get("visible_menu_path"), target, label)
                rows_by_center[target].append(row)

        for definition in ACCOUNTING_MENUS:
            row = _accounting_row(*definition)
            if row["menu_xmlid"] not in seen_xmlids:
                rows_by_center["会计账务中心"].append(row)
                seen_xmlids.add(row["menu_xmlid"])

        product["menu_groups"] = [
            {
                "category": "user_visible_menu",
                "group_key": f"construction.{center}",
                "group_label": center,
                "label": center,
                "title": center,
                "menus": rows_by_center[center],
            }
            for center in TARGET_CENTERS
        ]
        product["capabilities"] = [
            _capability_from_menu(menu)
            for group in product["menu_groups"]
            for menu in group["menus"]
        ]

    counts = {len([menu for group in product.get("menu_groups") or [] for menu in group.get("menus") or []]) for product in payload.get("products") or []}
    if len(counts) != 1:
        raise ValueError(f"product menu counts diverged: {sorted(counts)}")
    menu_count = counts.pop()
    strategy = payload.setdefault("policy_strategy", {})
    strategy["effective_menu_count_per_product"] = menu_count
    strategy["effective_capability_count_per_product"] = menu_count
    updates = list(strategy.get("responsibility_boundary_updates") or [])
    for update in (
        "物资与分包：撤销一级中心，入口按项目执行、合同、成本和资金权威归属",
        "施工管理：撤销一级中心，现场履约能力归入项目中心",
        "组织行政：统一为行政中心",
        "配置中心：提升为产品配置",
        "会计账务：准入 Odoo 原生模型、视图、动作和权限能力",
    ):
        if update not in updates:
            updates.append(update)
    strategy["responsibility_boundary_updates"] = updates
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    current = BASELINE.read_text(encoding="utf-8")
    payload = promote(json.loads(current))
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    digest = hashlib.sha256(rendered.encode("utf-8")).hexdigest()
    if args.write:
        BASELINE.write_text(rendered, encoding="utf-8")
        CHECKSUM.write_text(f"{digest}  {BASELINE.name}\n", encoding="utf-8")
    elif current != rendered or CHECKSUM.read_text(encoding="utf-8") != f"{digest}  {BASELINE.name}\n":
        raise SystemExit("locked ten-center policy or checksum is not in canonical promoted form")
    print(json.dumps({"products": len(payload.get("products") or []), "menu_count": payload["policy_strategy"]["effective_menu_count_per_product"], "sha256": digest}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
