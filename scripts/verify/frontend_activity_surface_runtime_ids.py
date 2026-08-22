# -*- coding: utf-8 -*-
"""Resolve the governed native Activity surface identity for browser acceptance."""

import json


menu = env.ref("account.menu_action_move_journal_line_form", raise_if_not_found=False)
action = env.ref("account.action_move_journal_line", raise_if_not_found=False)
move = env.ref(
    "smart_construction_acceptance_fixture.fe_activity_journal_entry",
    raise_if_not_found=False,
)
if not menu or not menu.exists() or not action or not action.exists() or not move or not move.exists():
    raise RuntimeError("formal Activity surface identity is unavailable")
if move._name != "account.move" or move.state != "draft" or not move.company_id:
    raise RuntimeError("Activity acceptance record identity mismatch")

payload = {
    "menu_id": int(menu.id),
    "action_id": int(action.id),
    "model": str(action.res_model or ""),
    "record_id": int(move.id),
    "company_id": int(move.company_id.id),
}
if payload["model"] != "account.move":
    raise RuntimeError("formal Activity surface model identity mismatch")

print("FRONTEND_ACTIVITY_SURFACE_TARGET_JSON=%s" % json.dumps(payload, sort_keys=True, separators=(",", ":")))
