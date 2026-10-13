# -*- coding: utf-8 -*-
"""Restore product menu policies from the locked formal business baseline.

This script intentionally excludes legacy/user-acceptance menus from the
product release policy. Those menus are migration/acceptance surfaces, not the
daily product navigation contract.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from odoo import SUPERUSER_ID, api
from odoo.addons.smart_construction_core.services.locked_menu_policy_contract import (
    REQUIRED_PRODUCT_KEYS,
    load_locked_menu_policy_contract,
)
from odoo.modules.registry import Registry


BASELINE_FILE = "formal_business_product_menu_policy_v1.json"
PRODUCT_KEYS = REQUIRED_PRODUCT_KEYS
OUTPUT_JSON_NAME = "formal_product_menu_policy_restore_v1.json"
PRESERVED_INACTIVE_MENU_XMLIDS: list[str] = []

def _text(value) -> str:
    return str(value or "").strip()




def _artifact_root() -> Path:
    raw = os.getenv("MIGRATION_ARTIFACT_ROOT")
    candidates = [Path(raw)] if raw else []
    candidates.extend([Path("/mnt/artifacts/backend"), Path("/mnt/artifacts/migration"), Path("/tmp")])
    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            probe = candidate / ".write_probe"
            probe.write_text("ok\n", encoding="utf-8")
            probe.unlink()
            return candidate
        except Exception:
            continue
    return Path("/tmp")


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")






















def _policy_release_pages(groups: list[dict]) -> list[dict]:
    pages = []
    for group in groups:
        if not isinstance(group, dict):
            continue
        for menu in group.get("menus") if isinstance(group.get("menus"), list) else []:
            if not isinstance(menu, dict):
                continue
            pages.append(
                {
                    "page_key": _text(menu.get("page_key") or menu.get("menu_xmlid")),
                    "menu_key": _text(menu.get("menu_key") or menu.get("menu_xmlid")),
                    "menu_xmlid": _text(menu.get("menu_xmlid")),
                    "label": _text(menu.get("label") or menu.get("name")),
                    "route": _text(menu.get("route")),
                    "menu_id": int(menu.get("menu_id") or 0),
                    "action_id": int(menu.get("action_id") or 0),
                    "res_model": _text(menu.get("res_model") or menu.get("model")),
                    "enabled": True,
                    "release_state": "released",
                    "access_level": "public",
                    "visible_menu_path": _text(menu.get("visible_menu_path")),
                }
            )
    return pages


def _write_snapshot(read_env, product_key: str, pages: list[dict], *, platform_db: str) -> dict:
    Snapshot = read_env["sc.edition.release.snapshot"].sudo()
    snapshot = Snapshot.search(
        [
            ("product_key", "=", product_key),
            ("state", "=", "released"),
            ("is_active", "=", True),
            ("active", "=", True),
        ],
        order="released_at desc, activated_at desc, id desc",
        limit=1,
    )
    if not snapshot:
        return {"status": "SKIP", "reason": "active_release_snapshot_not_found", "platform_db": platform_db}
    meta = dict(snapshot.meta_json if isinstance(snapshot.meta_json, dict) else {})
    draft = dict(meta.get("release_draft") if isinstance(meta.get("release_draft"), dict) else {})
    draft["pages"] = pages
    draft["page_count"] = len(pages)
    draft["total_page_count"] = len(pages)
    draft["fingerprint"] = hashlib.sha256(
        json.dumps(pages, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    meta["release_draft"] = draft
    snapshot.write({"meta_json": meta})
    return {
        "status": "PASS",
        "platform_db": platform_db,
        "snapshot_id": int(snapshot.id),
        "release_draft_page_count": len(pages),
    }


def _sync_platform_release_gate(product_key: str, pages: list[dict]) -> dict:
    platform_db = _text(env["ir.config_parameter"].sudo().get_param("smart_core.platform_release_db", ""))  # noqa: F821
    if not platform_db:
        return {"status": "FAIL", "reason": "platform_release_db_required", "platform_db": ""}
    current_db = _text(env.cr.dbname)  # noqa: F821
    if platform_db == current_db:
        return _write_snapshot(env, product_key, pages, platform_db=platform_db)  # noqa: F821
    try:
        registry = Registry(platform_db)
        with registry.cursor() as cr:
            read_env = api.Environment(cr, SUPERUSER_ID, dict(env.context or {}))  # noqa: F821
            result = _write_snapshot(read_env, product_key, pages, platform_db=platform_db)
            cr.commit()
            return result
    except Exception as exc:
        return {"status": "FAIL", "reason": "platform_release_db_unavailable", "platform_db": platform_db, "error": str(exc)}




def main() -> None:
    # The same P1 synchronizer owns upgrades and recovery. Never synthesize
    # menus or write company/role low-code preferences in an ops repair.
    load_locked_menu_policy_contract()
    Policy = env["sc.product.policy"].sudo()  # noqa: F821
    policy_results = {}
    snapshot_results = {}
    group_counts = {}
    menu_config_result = {"status": "UNCHANGED", "reason": "explicit_lowcode_overrides_preserved"}
    for product_key in PRODUCT_KEYS:
        sync = Policy.synchronize_locked_formal_menu_policy(product_key)
        policy = sync["policy"]
        product = {"menu_groups": policy.menu_groups}
        pages = _policy_release_pages(product["menu_groups"])
        snapshot_results[product_key] = _sync_platform_release_gate(product_key, pages)
        group_counts[product_key] = {
            _text(group.get("group_label")): len(group.get("menus") or [])
            for group in product["menu_groups"]
        }
        policy_results[product_key] = {
            "status": "PASS",
            "policy_id": int(policy.id),
            "group_count": len(product["menu_groups"]),
            "menu_count": len(pages),
            "capability_count": len(policy.capabilities),
        }
    ok = all(row.get("status") == "PASS" for row in policy_results.values()) and all(
        row.get("status") == "PASS" for row in snapshot_results.values()
    )
    result = {
        "status": "PASS" if ok else "FAIL",
        "db": env.cr.dbname,  # noqa: F821
        "baseline": BASELINE_FILE,
        "policy_results": policy_results,
        "snapshot_results": snapshot_results,
        "group_counts": group_counts,
        "menu_config_result": menu_config_result,
        "preserved_inactive_menu_xmlids": sorted(set(PRESERVED_INACTIVE_MENU_XMLIDS)),
    }
    _write_json(_artifact_root() / OUTPUT_JSON_NAME, result)
    if not ok:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        raise SystemExit(1)
    env.cr.commit()  # noqa: F821
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


main()
