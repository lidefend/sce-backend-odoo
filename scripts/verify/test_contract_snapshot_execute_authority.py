#!/usr/bin/env python3
from __future__ import annotations

import ast
import hashlib
import json
from collections.abc import Mapping
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "contract" / "snapshot_export.py"
TREE = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
FUNCTIONS = {
    "_authority_text",
    "validate_intent_authority_spec",
    "select_contract_execute_authority",
    "_check_record_read_access",
    "_record_state_fingerprint",
    "resolve_snapshot_execute_authority",
}
BODY = []
for node in TREE.body:
    if isinstance(node, ast.Assign) and any(
        isinstance(target, ast.Name)
        and target.id in {"_INTENT_AUTHORITY_KEYS", "_CONTRACT_V2_CAPABILITIES"}
        for target in node.targets
    ):
        BODY.append(node)
    elif isinstance(node, ast.ClassDef) and node.name == "SnapshotIntentAuthorityError":
        BODY.append(node)
    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in FUNCTIONS:
        BODY.append(node)
NAMESPACE = {"Mapping": Mapping, "hashlib": hashlib, "json": json}
exec(compile(ast.Module(body=BODY, type_ignores=[]), str(MODULE_PATH), "exec"), NAMESPACE)

SnapshotIntentAuthorityError = NAMESPACE["SnapshotIntentAuthorityError"]
resolve_snapshot_execute_authority = NAMESPACE["resolve_snapshot_execute_authority"]
select_contract_execute_authority = NAMESPACE["select_contract_execute_authority"]
validate_intent_authority_spec = NAMESPACE["validate_intent_authority_spec"]


class _Field:
    store = True
    type = "char"


class _Record:
    def __init__(self, model, record_id, *, values=None):
        self._name = model
        self.id = record_id
        self._fields = {"name": _Field()}
        self._values = values or {"id": record_id, "name": f"record-{record_id}"}
        self.parent_id = None
        self.action = None
        self.res_model = ""
        self.access_checks = []

    def __bool__(self):
        return True

    def exists(self):
        return self

    def check_access_rights(self, mode):
        self.access_checks.append(("rights", mode))

    def check_access_rule(self, mode):
        self.access_checks.append(("rule", mode))

    def read(self, _fields):
        return [dict(self._values)]


class _MenuModel:
    def __init__(self, visible_ids):
        self.visible_ids = visible_ids

    def _visible_menu_ids(self, debug=False):
        if debug:
            raise AssertionError("snapshot resolver must use non-debug reachability")
        return self.visible_ids


class _Env:
    def __init__(self, refs, visible_ids):
        self.refs = refs
        self.menu_model = _MenuModel(visible_ids)

    def ref(self, xmlid, raise_if_not_found=False):
        self.last_raise_if_not_found = raise_if_not_found
        return self.refs.get(xmlid)

    def __getitem__(self, model):
        if model != "ir.ui.menu":
            raise KeyError(model)
        return self.menu_model


def _spec(**updates):
    value = {
        "source": "ui.contract.v2",
        "record_xmlid": "demo.record",
        "action_xmlid": "core.action",
        "menu_xmlid": "core.menu",
        "view_type": "form",
        "button_type": "object",
        "method": "action_submit",
    }
    value.update(updates)
    return value


def _contract(*, rule_updates=None, status_updates=None, duplicate_rule=False, duplicate_status=False):
    rule = {
        "actionId": "submit",
        "actionKey": "action_submit",
        "backendIdentity": "native_button:object:action_submit:/form/button:1",
        "sourceWidgetId": "widget.submit",
        "allowed": True,
        "enabled": True,
        "disabled": False,
        "entitlementEvaluated": True,
        "button": {"type": "object", "name": "action_submit"},
    }
    rule.update(rule_updates or {})
    status = {
        "btnId": "btn.submit",
        "backendIdentity": rule.get("backendIdentity"),
        "visible": True,
        "disabled": False,
    }
    status.update(status_updates or {})
    rules = [rule, dict(rule)] if duplicate_rule else [rule]
    statuses = [status, dict(status)] if duplicate_status else [status]
    return {
        "actionContract": {"actionRuleList": rules},
        "statusContract": {"buttonStatus": statuses},
    }


def _runtime(contract=None):
    record = _Record("payment.request", 41)
    action = _Record("ir.actions.act_window", 52)
    action.res_model = "payment.request"
    parent = _Record("ir.ui.menu", 62)
    menu = _Record("ir.ui.menu", 63)
    menu.parent_id = parent
    menu.action = action
    env = _Env(
        {"demo.record": record, "core.action": action, "core.menu": menu},
        {62, 63},
    )
    calls = []

    def loader(*args, **kwargs):
        calls.append((args, kwargs))
        return contract or _contract()

    return env, record, action, menu, loader, calls


class SnapshotExecuteAuthorityTest(unittest.TestCase):
    def test_xmlids_resolve_to_contract_identity_and_dry_run_params(self):
        env, record, action, menu, loader, calls = _runtime()
        resolved = resolve_snapshot_execute_authority(env, object(), _spec(), contract_loader=loader)
        self.assertEqual(len(calls), 1)
        self.assertIs(calls[0][1]["record"], record)
        self.assertIs(calls[0][1]["action"], action)
        self.assertIs(calls[0][1]["menu"], menu)
        self.assertEqual(resolved["meta"], {"action_id": 52, "menu_id": 63})
        self.assertEqual(resolved["params"]["model"], "payment.request")
        self.assertEqual(resolved["params"]["res_id"], 41)
        self.assertIs(resolved["params"]["dry_run"], True)
        self.assertEqual(resolved["params"]["button"]["actionId"], "submit")
        self.assertEqual(
            resolved["params"]["button"]["backendIdentity"],
            "native_button:object:action_submit:/form/button:1",
        )
        self.assertEqual(resolved["params"]["button"]["sourceWidgetId"], "widget.submit")
        self.assertEqual(record.access_checks, [("rights", "read"), ("rule", "read")])
        self.assertEqual(action.access_checks, [("rights", "read"), ("rule", "read")])
        self.assertEqual(menu.access_checks, [("rights", "read"), ("rule", "read")])

    def test_record_model_and_action_menu_pair_fail_closed_before_contract_load(self):
        env, _record, action, menu, loader, calls = _runtime()
        action.res_model = "res.partner"
        with self.assertRaisesRegex(SnapshotIntentAuthorityError, "RECORD_MODEL_MISMATCH"):
            resolve_snapshot_execute_authority(env, object(), _spec(), contract_loader=loader)
        self.assertEqual(calls, [])

        env, _record, _action, menu, loader, calls = _runtime()
        menu.action = _Record("ir.actions.act_window", 99)
        with self.assertRaisesRegex(SnapshotIntentAuthorityError, "ACTION_MENU_MISMATCH"):
            resolve_snapshot_execute_authority(env, object(), _spec(), contract_loader=loader)
        self.assertEqual(calls, [])

    def test_full_parent_menu_chain_must_be_reachable(self):
        env, _record, _action, _menu, loader, calls = _runtime()
        env.menu_model.visible_ids = {63}
        with self.assertRaisesRegex(SnapshotIntentAuthorityError, "MENU_NOT_REACHABLE"):
            resolve_snapshot_execute_authority(env, object(), _spec(), contract_loader=loader)
        self.assertEqual(calls, [])

    def test_missing_duplicate_or_disabled_rule_and_status_fail_closed(self):
        failures = [
            (_contract(rule_updates={"sourceWidgetId": ""}), "IDENTITY_MISSING"),
            (_contract(duplicate_rule=True), "RULE_AMBIGUOUS"),
            (_contract(rule_updates={"allowed": False, "reasonCode": "DENIED"}), "DENIED"),
            (_contract(duplicate_status=True), "STATUS_AMBIGUOUS"),
            (_contract(status_updates={"disabled": True, "reasonCode": "BLOCKED"}), "BLOCKED"),
        ]
        missing_status = _contract()
        missing_status["statusContract"]["buttonStatus"] = []
        failures.append((missing_status, "STATUS_AMBIGUOUS"))
        for contract, reason in failures:
            with self.subTest(reason=reason):
                with self.assertRaisesRegex(SnapshotIntentAuthorityError, reason):
                    select_contract_execute_authority(
                        contract,
                        button_type="object",
                        method="action_submit",
                    )

    def test_selector_missing_or_multiple_matches_fail_closed(self):
        with self.assertRaisesRegex(SnapshotIntentAuthorityError, "RULE_AMBIGUOUS"):
            select_contract_execute_authority(
                _contract(rule_updates={"button": {"type": "object", "name": "other"}}),
                button_type="object",
                method="action_submit",
            )
        with self.assertRaisesRegex(SnapshotIntentAuthorityError, "RULE_AMBIGUOUS"):
            select_contract_execute_authority(
                _contract(duplicate_rule=True),
                button_type="object",
                method="action_submit",
            )

    def test_contract_load_failure_never_produces_execution_params(self):
        env, _record, _action, _menu, _loader, _calls = _runtime()
        executed = []

        def failing_loader(*_args, **_kwargs):
            raise SnapshotIntentAuthorityError("INTENT_AUTHORITY_CONTRACT_LOAD_FAILED")

        with self.assertRaisesRegex(SnapshotIntentAuthorityError, "CONTRACT_LOAD_FAILED"):
            resolved = resolve_snapshot_execute_authority(
                env,
                object(),
                _spec(),
                contract_loader=failing_loader,
            )
            executed.append(resolved)
        self.assertEqual(executed, [])

    def test_numeric_ids_and_incomplete_specs_are_rejected(self):
        for update in (
            {"record_xmlid": "41"},
            {"action_xmlid": "52"},
            {"menu_xmlid": "63"},
        ):
            with self.subTest(update=update):
                with self.assertRaisesRegex(SnapshotIntentAuthorityError, "XMLID_REQUIRED"):
                    validate_intent_authority_spec(_spec(**update))
        incomplete = _spec()
        incomplete.pop("method")
        with self.assertRaisesRegex(SnapshotIntentAuthorityError, "INVALID_SPEC"):
            validate_intent_authority_spec(incomplete)

    def test_governed_case_and_snapshot_contain_only_dynamic_authority(self):
        cases = json.loads((ROOT / "docs" / "contract" / "cases.yml").read_text(encoding="utf-8"))
        case = next(row for row in cases if row.get("case") == "execute_button_intent_dry_run_pm")
        self.assertNotIn("intent_params", case)
        self.assertEqual(case["user"], "sc_test_admin")
        for key in ("record_xmlid", "action_xmlid", "menu_xmlid"):
            self.assertIn(".", case["intent_authority"][key])
            self.assertFalse(case["intent_authority"][key].isdigit())

        snapshot = json.loads(
            (ROOT / "docs" / "contract" / "snapshots" / "execute_button_intent_dry_run_pm.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(snapshot["ui_contract_raw"]["result"]["reason_code"], "DRY_RUN")
        self.assertEqual(snapshot["ui_contract_raw"]["result"]["method"], "action_submit")
        self.assertIs(snapshot["intent_authority"]["recordStateUnchanged"], True)


if __name__ == "__main__":
    unittest.main()
