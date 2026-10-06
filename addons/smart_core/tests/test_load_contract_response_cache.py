# -*- coding: utf-8 -*-
import importlib.util
import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


MODULE_PATH = Path(__file__).resolve().parents[1] / "utils" / "load_contract_response_cache.py"
SPEC = importlib.util.spec_from_file_location("load_contract_response_cache_under_test", MODULE_PATH)
TARGET = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TARGET)
LoadContractResponseCache = TARGET.LoadContractResponseCache


class TestLoadContractResponseCache(unittest.TestCase):
    def test_create_defaults_are_not_a_reusable_projection_source(self):
        for key, value in (("render_profile", "create"), ("renderProfile", "create"),
                           ("record_id", "new"), ("recordId", "new"), ("res_id", "new"), ("resId", "new")):
            with self.subTest(key=key):
                self.assertIsNone(TARGET.projection_base_params({"model": "x.document", key: value}))

    def test_saved_records_and_lists_keep_record_independent_projection_cache(self):
        for request in ({"model": "x.document", "view_type": "tree"},
                        {"model": "x.document", "render_profile": "edit", "record_id": 42}):
            base = TARGET.projection_base_params(request)
            self.assertEqual(base["model"], "x.document")
            self.assertNotIn("record_id", base)
        self.assertIsNone(TARGET.projection_base_params({"model": "x.document", "default_project_id": 10}))

    def setUp(self):
        self.now = 100.0
        self.cache = LoadContractResponseCache(
            max_entries=2,
            ttl_seconds=5,
            clock=lambda: self.now,
        )

    def test_hit_returns_isolated_copy(self):
        response = {"status": "success", "data": {"views": ["form"]}}
        self.cache.put("user-page", "source-v1", response)

        first = self.cache.get("user-page", "source-v1")
        first["data"]["views"].append("tree")

        self.assertEqual(
            self.cache.get("user-page", "source-v1")["data"]["views"],
            ["form"],
        )

    def test_source_change_invalidates_entry(self):
        self.cache.put("user-page", "source-v1", {"status": "success"})

        self.assertIsNone(self.cache.get("user-page", "source-v2"))
        self.assertIsNone(self.cache.get("user-page", "source-v1"))

    def test_ttl_expiry_invalidates_entry(self):
        self.cache.put("user-page", "source-v1", {"status": "success"})
        self.now += 5.01

        self.assertIsNone(self.cache.get("user-page", "source-v1"))

    def test_capacity_evicts_least_recently_used_entry(self):
        self.cache.put("page-a", "source", {"page": "a"})
        self.cache.put("page-b", "source", {"page": "b"})
        self.assertEqual(self.cache.get("page-a", "source")["page"], "a")

        self.cache.put("page-c", "source", {"page": "c"})

        self.assertIsNone(self.cache.get("page-b", "source"))
        self.assertEqual(self.cache.get("page-a", "source")["page"], "a")
        self.assertEqual(self.cache.get("page-c", "source")["page"], "c")

    def test_projection_source_token_changes_with_runtime_source_fingerprint(self):
        class FakeModel:
            _fields = {"write_date": object()}

            def sudo(self):
                return self

            def with_context(self, **_kwargs):
                return self

            def search(self, _domain, **_kwargs):
                if _kwargs.get("order") == "id":
                    return [SimpleNamespace(id=1, definition_sha256="definition-A", version_no=1, status="published", active=True)]
                return SimpleNamespace(id=1, write_date="2026-08-21 00:00:00", latest_version="")

        class FakeEnv:
            def __init__(self):
                self.user = SimpleNamespace(id=7)
                self.company = SimpleNamespace(id=1)
                self._model = FakeModel()

            def __contains__(self, _model_code):
                return True

            def __getitem__(self, _model_code):
                return self._model

        env = FakeEnv()
        base = {"SC_SOURCE_REVISION": "a" * 40, "SC_SOURCE_FINGERPRINT": "b" * 64}
        with patch.dict(os.environ, base, clear=False):
            first = TARGET.build_projection_source_token(env, model_name="x.record")
        with patch.dict(os.environ, {**base, "SC_SOURCE_FINGERPRINT": "c" * 64}, clear=False):
            second = TARGET.build_projection_source_token(env, model_name="x.record")

        self.assertTrue(first)
        self.assertTrue(second)
        self.assertNotEqual(first, second)


class TestFieldPolicyProjectionSourceToken(unittest.TestCase):
    """A field-policy change must invalidate the projection source token.

    ``ui.form.field.policy`` rows are projection inputs. ``write_date`` is
    second-resolution and can stay identical for an A -> B -> A change inside a
    single transaction (for example a governed repair that retires a stale
    overlay), so the token must be derived from the policy definition set, not
    from the latest row's timestamp.
    """

    @staticmethod
    def _policy_row(**overrides):
        row = SimpleNamespace(
            id=85,
            write_date="2026-10-06 07:47:00",
            active=True,
            visible=False,
            field_name="project_code",
            action_id=SimpleNamespace(id=506),
            view_id=SimpleNamespace(id=0),
            sequence=1,
            label="项目编号",
            role_group_ids=SimpleNamespace(ids=[]),
        )
        for key, value in overrides.items():
            setattr(row, key, value)
        return row

    @classmethod
    def _build_env(cls, rows):
        class _GenericModel:
            _fields = {"write_date": object()}

            def sudo(self):
                return self

            def with_context(self, **_kwargs):
                return self

            def search(self, _domain, **_kwargs):
                if _kwargs.get("order") == "id":
                    return [SimpleNamespace(
                        id=1, definition_sha256="d", version_no=1,
                        status="published", active=True,
                    )]
                return SimpleNamespace(id=1, write_date="2026-08-21 00:00:00", latest_version="")

        class _PolicyModel:
            _fields = {"write_date": object(), "field_name": object(), "visible": object(), "active": object()}

            def __init__(self, policy_rows):
                self.policy_rows = policy_rows

            def sudo(self):
                return self

            def with_context(self, **_kwargs):
                return self

            def search(self, _domain, **_kwargs):
                return list(self.policy_rows)

        class _Env:
            def __init__(self, policy_rows):
                self.user = SimpleNamespace(id=7)
                self.company = SimpleNamespace(id=1)
                self.models = {
                    "ui.business.config.contract": _GenericModel(),
                    "ui.form.field.policy": _PolicyModel(policy_rows),
                }

            def __contains__(self, _model_code):
                return True

            def __getitem__(self, model_code):
                return self.models.setdefault(model_code, _GenericModel())

        return _Env(rows)

    def _token(self, rows):
        with patch.dict(os.environ, {"SC_SOURCE_REVISION": "a" * 40, "SC_SOURCE_FINGERPRINT": "b" * 64}, clear=False):
            return TARGET.build_projection_source_token(
                self._build_env(rows), model_name="project.project", action_id=506
            )

    def test_same_second_active_flip_reaches_the_token(self):
        row = self._policy_row()
        before = self._token([row])
        retired = self._policy_row(active=False)
        after = self._token([retired])

        self.assertTrue(before)
        self.assertTrue(after)
        self.assertNotEqual(
            before,
            after,
            "retiring a field-policy overlay in the same second must invalidate the projection token",
        )

    def test_visibility_and_identity_changes_reach_the_token(self):
        baseline = self._token([self._policy_row()])
        visible = self._token([self._policy_row(visible=True)])
        renamed = self._token([self._policy_row(field_name="business_nature")])
        removed = self._token([])

        self.assertNotEqual(baseline, visible)
        self.assertNotEqual(baseline, renamed)
        self.assertNotEqual(baseline, removed)


if __name__ == "__main__":
    unittest.main()
