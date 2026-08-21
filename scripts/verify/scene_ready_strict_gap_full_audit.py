#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from pathlib import Path

from intent_smoke_utils import require_ok
from python_http_smoke_utils import (
    build_intent_url,
    extract_login_token,
    get_base_url,
    http_post_json,
)


ROOT = Path(__file__).resolve().parents[2]
REPORT_JSON = ROOT / "artifacts" / "backend" / "scene_ready_strict_gap_full_audit.json"
REPORT_MD = ROOT / "docs" / "ops" / "audits" / "scene_ready_strict_gap_full_audit.md"
DEFAULT_STATE_PATH = ROOT / "artifacts" / "backend" / "scene_contract_field_schema_state.json"


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _as_dict(value):
    return value if isinstance(value, dict) else {}


def _as_list(value):
    return value if isinstance(value, list) else []


def _text(value) -> str:
    return str(value or "").strip()


def _to_bool(value) -> bool:
    return _text(value).lower() in {"1", "true", "yes", "y", "on"}


def _load_contract_from_state(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(payload, dict):
        return {}
    if isinstance(payload.get("scene_ready_contract"), dict):
        return _as_dict(payload.get("scene_ready_contract"))
    return payload if isinstance(payload.get("scenes"), list) else {}


def _scene_key_matches(scene_key: str, candidate: str) -> bool:
    key = str(scene_key or "").strip().lower()
    cand = str(candidate or "").strip().lower()
    if not key or not cand:
        return False
    return key in {cand, cand.replace('.', '_'), cand.replace('_', '.')}


def _missing_contract_paths(row: dict) -> list[str]:
    missing: list[str] = []
    scene = _as_dict(row.get("scene"))
    page = _as_dict(row.get("page"))
    scene_blocks = row.get("scene_blocks")
    page_zones = page.get("zones")
    action_surface = _as_dict(row.get("action_surface"))
    meta = _as_dict(row.get("meta"))

    if not _text(scene.get("key")):
        missing.append("scene.key")
    if not _text(scene.get("title")):
        missing.append("scene.title")
    if not _text(page.get("scene_key")):
        missing.append("page.scene_key")
    if not (_text(page.get("route")) or _text(page.get("model"))):
        missing.append("page.route|model")
    if not isinstance(page_zones, list):
        missing.append("page.zones")
    if not isinstance(scene_blocks, list) or not scene_blocks:
        missing.append("scene_blocks")
    if not isinstance(action_surface.get("primary_actions"), list):
        missing.append("action_surface.primary_actions")
    if not isinstance(action_surface.get("groups"), list):
        missing.append("action_surface.groups")
    if not str(action_surface.get("selection_mode") or "").strip():
        missing.append("action_surface.selection_mode")
    if not isinstance(row.get("search_surface"), dict):
        missing.append("search_surface")
    if not isinstance(meta.get("compile_verdict"), dict):
        missing.append("meta.compile_verdict")
    if not isinstance(meta.get("ui_base_contract_source"), dict):
        missing.append("meta.ui_base_contract_source")
    return missing


def _fetch_scene_ready_contract() -> dict:
    base_url = get_base_url()
    db_name = os.getenv("E2E_DB") or os.getenv("DB_NAME") or ""
    intent_url = build_intent_url(base_url, db_name)
    login = os.getenv("E2E_LOGIN") or os.getenv("ROLE_PM_LOGIN") or "demo_role_pm"
    password = (
        os.getenv("E2E_PASSWORD")
        or os.getenv("ROLE_PM_PASSWORD")
        or os.getenv("SC_DEMO_USER_PASSWORD")
        or "demo"
    )
    status, login_resp = http_post_json(
        intent_url,
        {"intent": "login", "params": {"db": db_name, "login": login, "password": password}},
        headers={"X-Anonymous-Intent": "1", "X-Odoo-DB": db_name},
    )
    require_ok(status, login_resp, "login")
    token = extract_login_token(login_resp)
    if not token:
        raise RuntimeError("login response missing token")

    status, init_resp = http_post_json(
        intent_url,
        {
            "intent": "system.init",
            "params": {
                "contract_mode": "user",
                "with_preload": True,
                "scene_ready_mode": "full",
            },
        },
        headers={"Authorization": f"Bearer {token}", "X-Odoo-DB": db_name},
    )
    require_ok(status, init_resp, "system.init")
    data = _as_dict(init_resp.get("data"))
    return _as_dict(data.get("scene_ready_contract"))


def main() -> int:
    warnings: list[str] = []
    contract_source = "live"
    state_path = ROOT / _text(
        os.getenv("SC_SCENE_READY_STRICT_GAP_FULL_AUDIT_STATE_FILE")
        or DEFAULT_STATE_PATH.relative_to(ROOT).as_posix()
    )
    allow_fallback = _to_bool(os.getenv("SC_SCENE_READY_STRICT_GAP_ALLOW_STATE_FALLBACK_ON_LIVE_FAIL"))
    try:
        contract = _fetch_scene_ready_contract()
    except Exception as exc:
        contract = _load_contract_from_state(state_path) if allow_fallback else {}
        if contract:
            contract_source = "state_file"
            warnings.append(f"live fetch failed, fallback state file used: {exc}")
        else:
            print("[FAIL] scene_ready_strict_gap_full_audit")
            print(f" - fetch scene_ready_contract failed: {exc}")
            return 2

    scenes = _as_list(contract.get("scenes"))
    all_rows = []
    unresolved_all_rows = []
    strict_rows = []
    unresolved_strict_rows = []
    source_gap_rows = []

    for row in scenes:
        if not isinstance(row, dict):
            continue
        meta = _as_dict(row.get("meta"))
        scene = _as_dict(row.get("scene"))
        scene_key = str(scene.get("key") or row.get("scene_key") or "").strip()
        missing_paths = _missing_contract_paths(row)
        all_report = {
            "scene_key": scene_key,
            "missing": missing_paths,
        }
        all_rows.append(all_report)
        if missing_paths:
            unresolved_all_rows.append(all_report)

        compile_verdict = _as_dict(meta.get("compile_verdict"))
        strict_mode = bool(compile_verdict)
        if not strict_mode:
            continue

        missing = [
            str(item).strip()
            for key in ("grammar_issues", "semantic_issues")
            for item in _as_list(compile_verdict.get(key))
            if str(item).strip()
        ]
        source = _as_dict(meta.get("ui_base_contract_source"))
        source_kind = _text(source.get("kind"))
        source_missing = [] if source_kind and source_kind not in {"none", "runtime_fallback"} else ["ui_base_contract_source.kind"]
        defaults_applied: list[str] = []
        contract_ready = bool(compile_verdict.get("ok")) and bool(
            compile_verdict.get("base_contract_bound")
        )

        row_report = {
            "scene_key": scene_key,
            "contract_ready": contract_ready,
            "missing": missing,
            "source_missing": source_missing,
            "defaults_applied": defaults_applied,
        }
        strict_rows.append(row_report)
        if missing or not contract_ready:
            unresolved_strict_rows.append(row_report)
        if source_missing:
            source_gap_rows.append(row_report)

    required_pilot_keys = ["workspace.home"]
    strict_scene_keys = [str(row.get("scene_key") or "").strip() for row in strict_rows]
    missing_required_strict = [
        key
        for key in required_pilot_keys
        if not any(_scene_key_matches(item, key) for item in strict_scene_keys)
    ]

    errors: list[str] = []
    if len(scenes) == 0:
        errors.append("scene_ready_contract.scenes is empty")
    if unresolved_all_rows:
        errors.append(f"unresolved full-scene contract gaps: {len(unresolved_all_rows)}")
    if len(strict_rows) == 0:
        errors.append("strict_scene_count is 0")
    if missing_required_strict:
        errors.append(f"required strict scenes missing: {','.join(missing_required_strict)}")
    if unresolved_strict_rows:
        errors.append(f"unresolved strict scenes: {len(unresolved_strict_rows)}")

    result = {
        "ok": len(errors) == 0,
        "warnings": warnings,
        "scene_count": len(scenes),
        "full_unresolved_count": len(unresolved_all_rows),
        "strict_scene_count": len(strict_rows),
        "strict_unresolved_count": len(unresolved_strict_rows),
        "strict_source_gap_count": len(source_gap_rows),
        "missing_required_strict": missing_required_strict,
        "contract_source": contract_source,
        "state_file": state_path.relative_to(ROOT).as_posix(),
        "allow_fallback_on_live_fail": allow_fallback,
        "errors": errors,
        "all_rows": all_rows,
        "unresolved_all_rows": unresolved_all_rows,
        "strict_rows": strict_rows,
        "strict_unresolved_rows": unresolved_strict_rows,
        "strict_source_gap_rows": source_gap_rows,
    }
    _write(REPORT_JSON, json.dumps(result, ensure_ascii=False, indent=2) + "\n")

    lines = [
        "# Scene Ready Strict Gap Full Audit",
        "",
        f"- status: {'PASS' if result['ok'] else 'FAIL'}",
        f"- contract_source: {contract_source}",
        f"- scene_count: {result['scene_count']}",
        f"- full_unresolved_count: {result['full_unresolved_count']}",
        f"- strict_scene_count: {result['strict_scene_count']}",
        f"- strict_unresolved_count: {result['strict_unresolved_count']}",
        f"- strict_source_gap_count: {result['strict_source_gap_count']}",
    ]
    if warnings:
        lines.extend(["", "## Warnings"])
        lines.extend([f"- {item}" for item in warnings])
    if errors:
        lines.extend(["", "## Errors"])
        lines.extend([f"- {item}" for item in errors])
    if source_gap_rows:
        lines.extend(["", "## Source Gaps"])
        for row in source_gap_rows:
            lines.append(
                f"- `{row['scene_key']}` source_missing={','.join(row['source_missing']) or '-'} defaults_applied={','.join(row['defaults_applied']) or '-'}"
            )
    if unresolved_all_rows:
        lines.extend(["", "## Full Scene Unresolved"])
        for row in unresolved_all_rows:
            lines.append(
                f"- `{row['scene_key']}` missing={','.join(row['missing']) or '-'}"
            )
    if unresolved_strict_rows:
        lines.extend(["", "## Unresolved"])
        for row in unresolved_strict_rows:
            lines.append(
                f"- `{row['scene_key']}` missing={','.join(row['missing']) or '-'} contract_ready={row['contract_ready']}"
            )
    _write(REPORT_MD, "\n".join(lines) + "\n")

    if errors:
        print("[FAIL] scene_ready_strict_gap_full_audit")
        for item in errors:
            print(f" - {item}")
        print(f"report: {REPORT_JSON.relative_to(ROOT).as_posix()}")
        print(f"report_md: {REPORT_MD.relative_to(ROOT).as_posix()}")
        return 2

    print("[PASS] scene_ready_strict_gap_full_audit")
    print(
        "summary:",
        f"full_unresolved_count={len(unresolved_all_rows)}",
        f"strict_scene_count={len(strict_rows)}",
        f"source_gap_count={len(source_gap_rows)}",
        f"strict_unresolved_count={len(unresolved_strict_rows)}",
    )
    print(f"report: {REPORT_JSON.relative_to(ROOT).as_posix()}")
    print(f"report_md: {REPORT_MD.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
