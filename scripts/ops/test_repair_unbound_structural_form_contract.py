# -*- coding: utf-8 -*-
"""Behavioural test for the unbound structural form-config repair driver.

The driver is a stdin script executed inside ``odoo shell`` (``bash
scripts/ops/odoo_shell_exec.sh < scripts/ops/repair_unbound_structural_form_contract.py``),
so it cannot be imported: its body runs against the ambient ``env``.  The
behaviour that matters is therefore exercised by executing the *same source* in
a sandbox with a stub ``env``, which drives the real decision tree the database
run used instead of asserting on text.

What is locked here is the fail-closed ladder, because every rung guards a write
against a live demo database:

* an unresolved target, an unpublished config, a view-bound config, a config
  that declares no structural form, or a name that is not the unbound low-code
  form identity all stop *before* the write;
* a scope with no view-bound native semantic surface refuses to retire anything
  (``SC_REPAIR_CONTRACT_ID`` on the wrong scope must not delete a real config);
* without ``APPLY=1`` the run is a dry run that publishes the verdict and
  performs no write and no commit;
* with ``APPLY=1`` the only mutation is ``active=False`` on the exact target,
  followed by a commit and an authoritative readback.

The pure helpers (``_text``, ``_form_spec``, ``_declared_fields``) are checked
through the reports they produce, so a helper regression fails here rather than
in the database.
"""

import contextlib
import io
import json
import os
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("repair_unbound_structural_form_contract.py")
SOURCE = SCRIPT.read_text(encoding="utf-8")

NATIVE_MODE = "native_semantic_surface"
UNBOUND_NAME = "view_orchestration:sc.general.contract:form:action:669:view:0"


class _FakeField(object):
    def __init__(self, record_id):
        self.id = record_id


class _FakeCursor(object):
    def __init__(self, dbname="sc_demo"):
        self.dbname = dbname
        self.commits = 0

    def commit(self):
        self.commits += 1


class _FakeRecord(object):
    def __init__(self, **values):
        self.id = values.get("id", 0)
        self.name = values.get("name", "")
        self.model = values.get("model", "")
        self.view_type = values.get("view_type", "")
        self.action_id = _FakeField(values.get("action_id", 0))
        self.view_id = _FakeField(values.get("view_id", 0))
        self.status = values.get("status", "published")
        self.active = values.get("active", True)
        self.priority = values.get("priority", 0)
        self.contract_json = values.get("contract_json")
        self.write_date = values.get("write_date", "2026-10-13 00:00:00")
        self._present = values.get("present", True)
        self.writes = []

    def exists(self):
        return self._present

    def write(self, values):
        self.writes.append(dict(values))
        owner = getattr(self, "_owner", None)
        if owner is not None:
            owner.writes.append((self.id, dict(values)))
        if "active" in values:
            self.active = values["active"]


class _FakeModel(object):
    def __init__(self, records):
        self._records = records
        self.writes = []

    def sudo(self):
        return self

    def browse(self, record_id):
        record = self._records.get(record_id)
        if record is None:
            missing = _FakeRecord(id=record_id, present=False)
            missing._owner = self
            return missing
        return record

    def search(self, domain):
        model = action_id = None
        for field, _operator, value in domain:
            if field == "model":
                model = value
            elif field == "action_id":
                action_id = value
        return [
            record
            for record in self._records.values()
            if record.model == model
            and record.action_id.id == action_id
            and record.active
            and record.status == "published"
            and record.view_type == "form"
        ]


class _FakeEnv(object):
    def __init__(self, model, cursor):
        self._model = model
        self.cr = cursor

    def __getitem__(self, _key):
        return self._model


def _native_surface(record_id, model, action_id, **overrides):
    values = {
        "id": record_id,
        "name": "daily_contract_form_native_v1",
        "model": model,
        "view_type": "form",
        "action_id": action_id,
        "view_id": 1699,
        "contract_json": {
            "view_orchestration": {"views": {"form": {"composition_mode": NATIVE_MODE}}}
        },
    }
    values.update(overrides)
    return _FakeRecord(**values)


def _unbound_config(record_id, model, action_id, **overrides):
    values = {
        "id": record_id,
        "name": UNBOUND_NAME,
        "model": model,
        "view_type": "form",
        "action_id": action_id,
        "view_id": 0,
        "contract_json": {
            "view_orchestration": {
                "views": {"form": {"fields": [{"name": "subcontract_mode"}]}}
            }
        },
    }
    values.update(overrides)
    return _FakeRecord(**values)


def run_driver(records, target_id=None, apply_flag=False):
    """Execute the real driver source against a stub ``env`` and capture its verdict."""
    previous_target = os.environ.get("SC_REPAIR_CONTRACT_ID")
    previous_apply = os.environ.get("APPLY")
    if target_id is None:
        os.environ.pop("SC_REPAIR_CONTRACT_ID", None)
    else:
        os.environ["SC_REPAIR_CONTRACT_ID"] = str(target_id)
    if apply_flag:
        os.environ["APPLY"] = "1"
    else:
        os.environ.pop("APPLY", None)
    try:
        cursor = _FakeCursor()
        model = _FakeModel(records)
        for record in records.values():
            record._owner = model
        namespace = {"env": _FakeEnv(model, cursor), "__name__": "__main__"}
        stream = io.StringIO()
        code = None
        with contextlib.redirect_stdout(stream):
            try:
                exec(compile(SOURCE, str(SCRIPT), "exec"), namespace)
            except SystemExit as exc:  # noqa: PERF203 - the driver exits by code
                code = exc.code
        payload = json.loads(stream.getvalue()) if stream.getvalue().strip() else None
        return code, payload, model, cursor
    finally:
        if previous_target is None:
            os.environ.pop("SC_REPAIR_CONTRACT_ID", None)
        else:
            os.environ["SC_REPAIR_CONTRACT_ID"] = previous_target
        if previous_apply is None:
            os.environ.pop("APPLY", None)
        else:
            os.environ["APPLY"] = previous_apply


class _DriverBase(unittest.TestCase):
    def scope(self):
        """A model/action pair with one unbound config over one bound native surface."""
        return {
            1: _native_surface(1, "sc.general.contract", 669),
            2: _unbound_config(2, "sc.general.contract", 669),
        }


class RepairDriverGuardTest(_DriverBase):
    def test_a_missing_target_is_refused_before_any_write(self):
        code, payload, model, cursor = run_driver(self.scope(), target_id=None)
        self.assertEqual(code, 2)
        self.assertEqual(payload["error"], "target contract not found")
        self.assertEqual(model.writes, [])
        self.assertEqual(cursor.commits, 0)

    def test_an_unknown_record_is_refused_before_any_write(self):
        code, payload, model, cursor = run_driver(self.scope(), target_id=99)
        self.assertEqual(code, 2)
        self.assertEqual(payload["error"], "target contract not found")
        self.assertEqual(model.writes, [])

    def test_an_unpublished_config_is_refused(self):
        records = self.scope()
        records[2].status = "draft"
        code, payload, model, _cursor = run_driver(records, target_id=2, apply_flag=True)
        self.assertEqual(code, 3)
        self.assertEqual(payload["error"], "target contract is not an active published config")
        self.assertEqual(model.writes, [])

    def test_a_view_bound_config_is_refused(self):
        records = self.scope()
        records[2].view_id = _FakeField(1699)
        code, payload, model, _cursor = run_driver(records, target_id=2, apply_flag=True)
        self.assertEqual(code, 3)
        self.assertIn("view-bound", payload["error"])
        self.assertEqual(model.writes, [])

    def test_a_config_without_a_structural_declaration_is_refused(self):
        records = self.scope()
        records[2].contract_json = {"view_orchestration": {"views": {"form": {}}}}
        code, payload, model, _cursor = run_driver(records, target_id=2, apply_flag=True)
        self.assertEqual(code, 3)
        self.assertEqual(payload["error"], "target contract declares no structural form declaration")
        self.assertEqual(model.writes, [])

    def test_a_non_unbound_identity_is_refused(self):
        records = self.scope()
        records[2].name = "view_orchestration:sc.general.contract:form:action:669:view:1699"
        code, payload, model, _cursor = run_driver(records, target_id=2, apply_flag=True)
        self.assertEqual(code, 3)
        self.assertEqual(payload["error"], "target contract is not an unbound low-code form config")
        self.assertEqual(model.writes, [])

    def test_a_scope_without_a_bound_native_surface_refuses_to_retire(self):
        records = self.scope()
        del records[1]
        code, payload, model, _cursor = run_driver(records, target_id=2, apply_flag=True)
        self.assertEqual(code, 4)
        self.assertIn("no view-bound native semantic surface", payload["error"])
        self.assertEqual(model.writes, [])


class RepairDriverApplyTest(_DriverBase):
    def test_the_default_run_is_a_dry_run_with_no_write(self):
        code, payload, model, cursor = run_driver(self.scope(), target_id=2)
        self.assertEqual(code, 0)
        self.assertEqual(payload["action"], "dry_run")
        self.assertFalse(payload["apply"])
        self.assertEqual(payload["bound_native_surfaces"][0]["contract_id"], 1)
        self.assertEqual(payload["declared_structural_keys"], ["fields"])
        self.assertEqual(payload["declared_fields"], ["subcontract_mode"])
        self.assertEqual(model.writes, [])
        self.assertEqual(cursor.commits, 0)

    def test_apply_retires_exactly_the_target_and_reads_it_back(self):
        code, payload, model, cursor = run_driver(self.scope(), target_id=2, apply_flag=True)
        self.assertIsNone(code)
        self.assertEqual(payload["action"], "retired")
        self.assertEqual(len(model.writes), 1)
        record_id, values = model.writes[0]
        self.assertEqual(record_id, 2)
        self.assertEqual(values, {"active": False})
        self.assertEqual(cursor.commits, 1)
        self.assertFalse(payload["readback"]["active"])

    def test_the_retired_scope_keeps_the_native_surface_untouched(self):
        code, payload, model, _cursor = run_driver(self.scope(), target_id=2, apply_flag=True)
        self.assertIsNone(code)
        self.assertEqual(payload["action"], "retired")
        self.assertEqual([rid for rid, _values in model.writes], [2])

    def test_a_second_unbound_config_in_scope_is_not_touched(self):
        records = self.scope()
        records[3] = _unbound_config(3, "sc.general.contract", 669)
        code, _payload, model, _cursor = run_driver(records, target_id=2, apply_flag=True)
        self.assertIsNone(code)
        self.assertEqual([rid for rid, _values in model.writes], [2])


if __name__ == "__main__":
    unittest.main()
