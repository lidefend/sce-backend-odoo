# -*- coding: utf-8 -*-
import ast
import copy
import importlib.util
import json
import os
import tempfile
import time
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

    def test_put_isolates_caller_owned_input(self):
        source = {"data": {"columns": ["name"]}}
        self.cache.put("page", "source", source)
        source["data"]["columns"].append("secret")
        self.assertEqual(self.cache.get("page", "source")["data"]["columns"], ["name"])

    def test_handler_generated_snapshot_keeps_component_and_request_isolation(self):
        # Execute the real handler call, not a test-side imitation of its payload.
        source_path = MODULE_PATH.parents[1] / "handlers" / "ui_contract_v2.py"
        tree = ast.parse(source_path.read_text())
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
                 and isinstance(node.func, ast.Attribute)
                 and node.func.attr == "put_generated"]
        self.assertEqual(len(calls), 1)
        shared = {"columns": ["name"]}
        metadata = {"policy": shared, "trace_id": "request-only", "request_id": "request-only"}
        namespace = {
            "CONTRACT_PROJECTION_HOT_CACHE": self.cache,
            "cache_key": "page", "source_token": "source",
            "runtime_source_type": "native", "ui_data": shared,
            "ui_meta": metadata, "ASSEMBLED_CONTRACT_CACHE_VERSION": "test",
            "client_type": "web", "delivery_profile": "full",
            "limit_params": {"limit": 20}, "contract_v2": shared,
            "source_contract": shared, "deepcopy": copy.deepcopy,
        }
        with patch.object(TARGET.copy, "deepcopy", wraps=copy.deepcopy) as copied:
            eval(compile(ast.Expression(calls[0]), str(source_path), "eval"), namespace)
            # The producer owns copying; the cache must not recopy the snapshot.
            self.assertEqual(copied.call_count, 0)
        expected = self.cache.get("page", "source")
        shared["columns"].append("late-mutation")
        metadata["extra"] = "late-metadata"
        self.assertEqual(self.cache.get("page", "source"), expected)
        first = self.cache.get("page", "source")
        self.assertNotIn("trace_id", first["ui_meta"])
        self.assertNotIn("request_id", first["ui_meta"])
        first["ui_data"]["columns"].append("request-mutation")
        self.assertEqual(first["_assembled_v2"]["contract"]["columns"], ["name"])
        self.assertEqual(first["_assembled_v2"]["source_contract"]["columns"], ["name"])
        self.assertEqual(first["ui_meta"]["policy"]["columns"], ["name"])
        self.assertEqual(self.cache.get("page", "source"), expected)

    def test_generated_snapshot_failure_does_not_replace_valid_entry(self):
        self.cache.put("page", "source", {"value": "original"})
        def fail():
            raise ValueError("assembly failed")
        with self.assertRaises(ValueError):
            self.cache.put_generated("page", "source", fail)
        self.assertEqual(self.cache.get("page", "source"), {"value": "original"})
        self.cache.put_generated("page", "source", lambda: None)
        self.assertEqual(self.cache.get("page", "source"), {"value": "original"})

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


class TestContractCodeFingerprintIdentity(unittest.TestCase):
    """The persisted runtime source asset has no expiry, so the source token
    must follow code identity by itself: a content rewrite that keeps
    ``mtime_ns`` and ``size`` equal (the pre-fix identity row) must still change
    ``contract_code_fingerprint`` or the old source contract stays served."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self._saved = TARGET._CODE_FINGERPRINT_CACHE["value"]
        self.addCleanup(self._restore_fingerprint_cache)

    def _restore_fingerprint_cache(self):
        TARGET._CODE_FINGERPRINT_CACHE["value"] = self._saved

    def _fingerprint(self):
        TARGET._CODE_FINGERPRINT_CACHE["value"] = None
        with patch.dict(os.environ, {"SC_SOURCE_ADDONS_ROOT": str(self.root)}, clear=False):
            return TARGET.contract_code_fingerprint()

    def test_same_size_same_mtime_content_change_changes_the_fingerprint(self):
        target = self.root / "contract_under_test.py"
        target.write_text("VALUE = 'aaaa'\n", encoding="utf-8")
        before = target.stat()
        first = self._fingerprint()

        # Advance past the coarse ctime tick, then rewrite the same byte length
        # and restore mtime so only the content (and ctime) differ.
        time.sleep(0.05)
        target.write_text("VALUE = 'bbbb'\n", encoding="utf-8")
        os.utime(target, ns=(before.st_atime_ns, before.st_mtime_ns))
        after = target.stat()

        self.assertEqual(after.st_size, before.st_size)
        self.assertEqual(after.st_mtime_ns, before.st_mtime_ns)
        self.assertNotEqual(after.st_ctime_ns, before.st_ctime_ns)

        second = self._fingerprint()
        self.assertNotEqual(
            first,
            second,
            "a same-size content rewrite with a restored mtime must change the code fingerprint",
        )


class TestIsolatedCloneStaysDeepcopyEquivalent(unittest.TestCase):
    """``get()`` hands out a graph disjoint from the entry. The clone used for
    that must stay exactly equivalent to ``copy.deepcopy`` for the JSON-shaped
    payload this cache stores, and must delegate everything else unchanged."""

    @staticmethod
    def _json_payload():
        shared = ["name", "state", "amount"]
        return {
            "source_type": "runtime_intent",
            "ui_data": {
                "fields": {
                    "project_id": {
                        "relation_entry": {
                            "search_dialog": {
                                "columns": ["name", "partner_id"],
                                "limit": 120,
                                "order": "id desc",
                            }
                        }
                    }
                },
                "rows": [{"id": index, "vals": [index, index + 1]} for index in range(25)],
                "unicode": "合同/项目",
                "flags": [True, False, None],
            },
            "ui_meta": {"intent": "ui.contract", "policy": {"locked": shared}},
            "shared_a": shared,
            "shared_b": shared,
        }

    def test_clone_equals_deepcopy_and_serialises_identically(self):
        payload = self._json_payload()
        cloned = TARGET.isolated_clone(payload)
        copied = copy.deepcopy(payload)

        self.assertEqual(cloned, copied)
        self.assertEqual(
            json.dumps(cloned, ensure_ascii=False, sort_keys=True),
            json.dumps(copied, ensure_ascii=False, sort_keys=True),
        )
        self.assertIsNot(cloned, payload)

    def test_clone_preserves_shared_aliasing_like_deepcopy(self):
        payload = self._json_payload()
        cloned = TARGET.isolated_clone(payload)
        copied = copy.deepcopy(payload)

        self.assertIs(cloned["shared_a"], cloned["shared_b"])
        self.assertIs(copied["shared_a"], copied["shared_b"])
        self.assertIsNot(cloned["shared_a"], payload["shared_a"])

    def test_clone_keeps_nested_writes_off_the_source_graph(self):
        payload = self._json_payload()
        cloned = TARGET.isolated_clone(payload)

        cloned["ui_data"]["rows"][0]["vals"].append("late")
        cloned["ui_data"]["fields"]["project_id"]["relation_entry"]["search_dialog"]["columns"].append("late")
        cloned["ui_meta"]["policy"]["locked"].append("late")

        self.assertEqual(payload["ui_data"]["rows"][0]["vals"], [0, 1])
        self.assertEqual(
            payload["ui_data"]["fields"]["project_id"]["relation_entry"]["search_dialog"]["columns"],
            ["name", "partner_id"],
        )
        self.assertEqual(payload["ui_meta"]["policy"]["locked"], ["name", "state", "amount"])

    def test_clone_delegates_non_json_types_to_deepcopy(self):
        from collections import OrderedDict

        for value in ({1, 2}, (1, [2]), b"bytes", OrderedDict(a=1), 3 + 4j, "text", 7, 1.5, True, None):
            with self.subTest(value=type(value).__name__):
                cloned = TARGET.isolated_clone(value)
                copied = copy.deepcopy(value)
                self.assertEqual(cloned, copied)
                self.assertIs(type(cloned), type(copied))

        atomic_tuple = ("a", 1)
        self.assertIs(TARGET.isolated_clone(atomic_tuple), atomic_tuple)
        self.assertIs(copy.deepcopy(atomic_tuple), atomic_tuple)

    def test_clone_handles_a_self_referential_graph(self):
        payload = {"name": "root"}
        payload["self"] = payload
        cloned = TARGET.isolated_clone(payload)

        self.assertIs(cloned["self"], cloned)
        self.assertIsNot(cloned, payload)

    def test_hot_read_never_falls_back_to_deepcopy_for_json_payloads(self):
        payload = self._json_payload()
        self.cache = TARGET.LoadContractResponseCache(max_entries=4, ttl_seconds=30.0)
        self.cache.put("page", "source", payload)

        with patch.object(TARGET.copy, "deepcopy", wraps=copy.deepcopy) as copied:
            first = self.cache.get("page", "source")
            self.assertEqual(copied.call_count, 0)

        entry = self.cache._entries["page"][2]
        self.assertIsNot(first, entry)
        self.assertIsNot(first["ui_data"], entry["ui_data"])
        self.assertIsNot(first["shared_a"], entry["shared_a"])

        first["ui_data"]["rows"][0]["vals"].append("request-only")
        self.assertEqual(self.cache.get("page", "source")["ui_data"]["rows"][0]["vals"], [0, 1])


class TestHandlerHandOffOwnsTheGetCopy(unittest.TestCase):
    """``ui_contract_v2`` mutates the cached source it gets in place (R3 removed
    a second copy there). That is only safe while the accessor already returns a
    fully disjoint graph; these bind that premise and stop the redundant copy
    from silently coming back."""

    def setUp(self):
        self.cache = TARGET.LoadContractResponseCache(max_entries=4, ttl_seconds=30.0)

    @staticmethod
    def _payload():
        return {
            "source_type": "runtime_intent",
            "ui_data": {
                "fields": {
                    "project_id": {
                        "relation_entry": {"search_dialog": {"columns": ["name"]}}
                    }
                }
            },
            "ui_meta": {"intent": "ui.contract"},
            "_assembled_v2": {
                "cache_version": "v",
                "contract": {"columns": ["a"]},
                "source_contract": {"columns": ["a"]},
            },
        }

    def test_handler_does_not_recopy_the_exclusively_owned_cached_source(self):
        source_path = MODULE_PATH.parents[1] / "handlers" / "ui_contract_v2.py"
        tree = ast.parse(source_path.read_text())
        offenders = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            func = node.func
            if isinstance(func, ast.Name) and func.id == "deepcopy":
                argument = ast.unparse(node.args[0])
                if argument.startswith(("cached_source", "assembled_cached")):
                    offenders.append(argument)
        self.assertEqual(
            offenders,
            [],
            "the handler must not copy again after get()/get_runtime_source_asset() "
            "already returned an exclusively owned graph",
        )

    def test_in_place_hand_off_of_the_get_copy_never_reaches_the_entry(self):
        self.cache.put("page", "source", self._payload())
        stored = self.cache.get("page", "source")

        cached_source = self.cache.get("page", "source")
        entry = self.cache._entries["page"][2]
        self.assertIsNot(cached_source, entry)
        self.assertIsNot(cached_source["ui_data"], entry["ui_data"])
        self.assertIsNot(
            cached_source["_assembled_v2"]["contract"],
            entry["_assembled_v2"]["contract"],
        )

        # handler-style hand-off: assign the get() graph, then mutate in place
        ui_data = cached_source["ui_data"]
        ui_meta = cached_source["ui_meta"]
        ui_data["fields"]["project_id"]["relation_entry"]["search_dialog"]["columns"].append(
            "late-request-value"
        )
        ui_meta["trace_id"] = "request-only"
        contract_v2 = cached_source["_assembled_v2"]["contract"]
        contract_v2["columns"].append("sealed")
        source_contract = cached_source["_assembled_v2"]["source_contract"]
        source_contract["columns"].append("sealed")

        after = self.cache.get("page", "source")
        self.assertEqual(
            after["ui_data"]["fields"]["project_id"]["relation_entry"]["search_dialog"]["columns"],
            ["name"],
        )
        self.assertEqual(after["_assembled_v2"]["contract"]["columns"], ["a"])
        self.assertEqual(after["_assembled_v2"]["source_contract"]["columns"], ["a"])
        self.assertNotIn("trace_id", after["ui_meta"])
        self.assertEqual(after, stored)


if __name__ == "__main__":
    unittest.main()
