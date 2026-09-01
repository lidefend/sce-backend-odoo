from __future__ import annotations

import unittest
from unittest.mock import patch

from addons.smart_construction_acceptance_fixture.tools.frontend_productization_fixture import (
    _upsert,
)


class _Field:
    def __init__(self, field_type: str) -> None:
        self.type = field_type


class _UnsafeXmlidRecord:
    _name = "sc.payment.execution"

    def __init__(self, record_id: int) -> None:
        self.id = record_id

    def __getitem__(self, field_name: str):
        raise AssertionError(f"raw xmlid record should not be read: {field_name}")


class _SafeRecord:
    _name = "sc.payment.execution"
    _fields = {"name": _Field("char"), "active": _Field("boolean")}

    def __init__(self, record_id: int, values: dict[str, object]) -> None:
        self.id = record_id
        self.values = dict(values)
        self.write_calls: list[dict[str, object]] = []

    def __getitem__(self, field_name: str):
        return self.values[field_name]

    def write(self, values: dict[str, object]) -> None:
        self.write_calls.append(dict(values))
        self.values.update(values)

    def exists(self):
        return self


class _FakeModel:
    def __init__(self, safe_record: _SafeRecord) -> None:
        self.safe_record = safe_record
        self.browse_ids: list[int] = []
        self.search_calls = 0

    def sudo(self):
        return self

    def with_context(self, **_kwargs):
        return self

    def browse(self, record_id: int):
        self.browse_ids.append(record_id)
        return self.safe_record

    def search(self, _domain):
        self.search_calls += 1
        return []

    def create(self, values):
        raise AssertionError(f"create should not be called: {values}")


class _FakeEnv:
    def __init__(self, model: _FakeModel, xmlid_record: _UnsafeXmlidRecord) -> None:
        self.model = model
        self.xmlid_record = xmlid_record

    def __getitem__(self, model_name: str):
        if model_name != "sc.payment.execution":
            raise AssertionError(f"unexpected model lookup: {model_name}")
        return self.model

    def ref(self, _xmlid: str, raise_if_not_found: bool = False):
        self.raise_if_not_found = raise_if_not_found
        return self.xmlid_record


class FrontendProductizationFixtureUpsertTest(unittest.TestCase):
    def test_existing_xmlid_record_is_rebound_to_sudo_model_before_field_read(self) -> None:
        safe_record = _SafeRecord(7, {"name": "FE-A-PE-001", "active": True})
        model = _FakeModel(safe_record)
        env = _FakeEnv(model, _UnsafeXmlidRecord(7))

        with patch(
            "addons.smart_construction_acceptance_fixture.tools.frontend_productization_fixture._bind_xmlid"
        ) as bind_xmlid:
            record = _upsert(
                env,
                "sc.payment.execution",
                "fe_execution_a",
                [("name", "=", "FE-A-PE-001")],
                {"name": "FE-A-PE-001", "active": True},
            )

        self.assertIs(record, safe_record)
        self.assertEqual(model.browse_ids, [7])
        self.assertEqual(model.search_calls, 0)
        self.assertEqual(safe_record.write_calls, [])
        bind_xmlid.assert_called_once()


if __name__ == "__main__":
    unittest.main()
