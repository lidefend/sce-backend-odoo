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

LIFECYCLE_PATH = MODULE_PATH.parents[1] / "core" / "contract_lifecycle.py"


def _load_lifecycle_module():
    """Load the real lifecycle module so the seal under test is the shipped one."""
    spec = importlib.util.spec_from_file_location("contract_lifecycle_under_test", LIFECYCLE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _payload_digest(value):
    """A byte-level digest of a payload graph, order- and alias-insensitive."""
    return TARGET.hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


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
        # Realistic store shape. ``source_contract`` is the assembly-time shallow
        # copy of ``ui_data``, so the live graphs still share every subtree the
        # normalizers did not replace; ``contract_v2`` is the assembled product and
        # sealing mutates it on every delivery. The snapshot therefore has two
        # ownership groups, not four independent components:
        #   * source group  = ``ui_data`` + ``_assembled_v2.source_contract``
        #                     (one shared copy memo keeps the live sharing single)
        #   * assembled group = ``_assembled_v2.contract`` (its own memo, so a seal
        #                     can never move the source payload it digests)
        shared_columns = ["name"]
        ui_data = {"ui_contract": {"columns": shared_columns}, "model": "x.document"}
        source_contract = {"columns": shared_columns, "model": "x.document"}
        contract_v2 = {"columns": shared_columns, "model": "x.document", "meta": {}}
        ui_meta = {"intent": "ui.contract"}
        namespace = {
            "CONTRACT_PROJECTION_HOT_CACHE": self.cache,
            "cache_key": "page", "source_token": "source",
            "runtime_source_type": "native", "ui_data": ui_data,
            "ui_meta": ui_meta, "ASSEMBLED_CONTRACT_CACHE_VERSION": "test",
            "client_type": "web", "delivery_profile": "full",
            "limit_params": {"limit": 20}, "contract_v2": contract_v2,
            "source_contract": source_contract, "deepcopy": copy.deepcopy,
            "source_snapshot_memo": {}, "assembled_digest_slot": {},
            "ASSEMBLED_SEMANTIC_DIGESTS_KEY": "assembled_semantic_digests",
        }
        with patch.object(TARGET.copy, "deepcopy", wraps=copy.deepcopy) as copied:
            eval(compile(ast.Expression(calls[0]), str(source_path), "eval"), namespace)
            # The producer owns copying; the cache must not recopy the snapshot.
            self.assertEqual(copied.call_count, 0)

        # value pollution: the stored snapshot owns its values, the live inputs do not
        expected = self.cache.get("page", "source")
        shared_columns.append("late-mutation")
        ui_meta["extra"] = "late-metadata"
        self.assertEqual(self.cache.get("page", "source"), expected)

        snapshot = self.cache._entries["page"][2]
        # the source group keeps the live sharing inside the entry
        self.assertIs(
            snapshot["ui_data"]["ui_contract"]["columns"],
            snapshot["_assembled_v2"]["source_contract"]["columns"],
        )
        # the assembled group is disjoint from the source group, so a seal cannot
        # move the source payload whose digest it is compared against
        self.assertIsNot(
            snapshot["_assembled_v2"]["contract"]["columns"],
            snapshot["ui_data"]["ui_contract"]["columns"],
        )
        self.assertIsNot(
            snapshot["_assembled_v2"]["contract"]["columns"],
            snapshot["_assembled_v2"]["source_contract"]["columns"],
        )

        # every component of the read graph is still disjoint from the entry
        first = self.cache.get("page", "source")
        self.assertIsNot(first, snapshot)
        self.assertIsNot(first["ui_data"], snapshot["ui_data"])
        self.assertIsNot(first["ui_meta"], snapshot["ui_meta"])
        self.assertIsNot(first["_assembled_v2"]["contract"], snapshot["_assembled_v2"]["contract"])
        self.assertIsNot(
            first["_assembled_v2"]["source_contract"],
            snapshot["_assembled_v2"]["source_contract"],
        )
        self.assertEqual(first["ui_meta"], {"intent": "ui.contract"})

        # in-place handler style mutations stay inside the read graph, and inside
        # the source group where the live graphs were already shared
        first["ui_data"]["ui_contract"]["columns"].append("request-mutation")
        self.assertEqual(
            first["_assembled_v2"]["source_contract"]["columns"], ["name", "request-mutation"]
        )
        self.assertEqual(first["_assembled_v2"]["contract"]["columns"], ["name"])
        first["_assembled_v2"]["contract"]["meta"]["etag"] = "sealed"
        first["ui_meta"]["request_id"] = "request-only"

        # cross-request pollution: the entry and the next read are untouched
        self.assertEqual(self.cache.get("page", "source"), expected)
        self.assertNotIn("etag", snapshot["_assembled_v2"]["contract"]["meta"])
        self.assertNotIn("request_id", snapshot["ui_meta"])

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
    must follow code identity by itself.

    The code identity is a content digest; the file-system stat row
    (``size``/``mtime_ns``/``ctime_ns``) is not part of it. Both directions are
    pinned here: a content rewrite that keeps ``mtime_ns`` and ``size`` equal
    must move the identity, and metadata-only drift (``utime``) must not."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self._saved = dict(TARGET._CODE_FINGERPRINT_CACHE)
        self.addCleanup(self._restore_fingerprint_cache)

    def _restore_fingerprint_cache(self):
        TARGET._CODE_FINGERPRINT_CACHE.clear()
        TARGET._CODE_FINGERPRINT_CACHE.update(self._saved)

    def _fingerprint(self):
        TARGET._CODE_FINGERPRINT_CACHE["value"] = None
        with patch.dict(os.environ, {"SC_SOURCE_ADDONS_ROOT": str(self.root)}, clear=False):
            return TARGET.contract_code_fingerprint()

    def _fingerprint_without_reset(self):
        with patch.dict(os.environ, {"SC_SOURCE_ADDONS_ROOT": str(self.root)}, clear=False):
            return TARGET.contract_code_fingerprint()

    @staticmethod
    def _recomputations():
        return int(TARGET._CODE_FINGERPRINT_CACHE["content_recomputations"])

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

    def test_metadata_only_drift_does_not_move_the_identity(self):
        target = self.root / "contract_under_test.py"
        target.write_text("VALUE = 'aaaa'\n", encoding="utf-8")
        first = self._fingerprint()
        after_first = self._recomputations()

        # Touch metadata only: a fresh content read must still produce the same
        # identity, so a timestamp row can never act as the code identity.
        time.sleep(0.05)
        os.utime(target, None)
        second = self._fingerprint()

        self.assertEqual(
            first,
            second,
            "metadata-only drift must not move the content identity",
        )
        self.assertEqual(
            self._recomputations(),
            after_first + 1,
            "the second identity must come from a fresh content read, not from a cached one",
        )

    def test_process_cached_digest_is_not_recomputed_per_call(self):
        (self.root / "contract_under_test.py").write_text("VALUE = 'aaaa'\n", encoding="utf-8")
        first = self._fingerprint()
        after_first = self._recomputations()

        second = self._fingerprint_without_reset()

        self.assertEqual(first, second)
        self.assertEqual(
            self._recomputations(),
            after_first,
            "the hot path must not re-read every source file per call",
        )

    def test_old_source_entry_is_refused_once_the_code_identity_moves(self):
        cache = LoadContractResponseCache()
        target = self.root / "contract_under_test.py"
        target.write_text("VALUE = 'aaaa'\n", encoding="utf-8")
        old_token = self._fingerprint()
        cache.put_generated("page", old_token, lambda: {"ui_data": {"model": "x.record"}})
        self.assertIsNotNone(cache.get("page", old_token))
        self.assertIsNotNone(cache.get("page", self._fingerprint()))

        before = target.stat()
        time.sleep(0.05)
        target.write_text("VALUE = 'bbbb'\n", encoding="utf-8")
        os.utime(target, ns=(before.st_atime_ns, before.st_mtime_ns))
        new_token = self._fingerprint()

        self.assertNotEqual(old_token, new_token)
        self.assertIsNone(
            cache.get("page", new_token),
            "the old source entry must be refused once the code identity moves",
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


class TestAssembledSharedRead(unittest.TestCase):
    """``get_assembled`` is the one accessor that hands out cache-owned graphs.

    ``ui_data`` / ``_assembled_v2.source_contract`` come back ON LOAN so the
    assembled hot hit stops re-copying the source graph it only reads, while
    ``contract`` / ``ui_meta`` / the semantic digests come back owned because the
    seal rewrites them. These tests bind both halves of that split, the gate
    that decides it, and the burst stability the loan depends on.
    """

    DIGESTS_KEY = "assembled_semantic_digests"
    GATE = {
        "cache_version": "ui-contract-v2-test",
        "client_type": "web_pc",
        "delivery_profile": "full",
        "limit_params": {"limit": 20},
    }

    def setUp(self):
        self.cache = TARGET.LoadContractResponseCache(max_entries=4, ttl_seconds=30.0)

    @staticmethod
    def _entry_payload():
        shared_columns = ["name"]
        return {
            "source_type": "runtime_intent",
            "ui_data": {"ui_contract": {"columns": shared_columns}, "model": "x.document"},
            "ui_meta": {"intent": "ui.contract", "source": "native"},
            "_assembled_v2": {
                "cache_version": "ui-contract-v2-test",
                "client_type": "web_pc",
                "delivery_profile": "full",
                "limit_params": {"limit": 20},
                "contract": {"columns": list(shared_columns), "model": "x.document", "meta": {}},
                "source_contract": {"columns": shared_columns, "model": "x.document"},
                "assembled_semantic_digests": {"contractSha256": "a" * 64, "sourceSha256": "b" * 64},
            },
        }

    def _store(self):
        self.cache.put("page", "source", self._entry_payload())
        return self.cache._entries["page"][2]

    def _hit(self, *, cache_key="page", source_token="source", **overrides):
        gate = dict(self.GATE)
        gate.update(overrides.pop("gate", {}))
        return self.cache.get_assembled(
            cache_key, source_token, digests_key=self.DIGESTS_KEY, **gate, **overrides
        )

    def test_shared_read_loans_the_source_and_owns_the_rest(self):
        entry = self._store()

        result = self._hit()

        self.assertIsNotNone(result)
        self.assertEqual(set(result), {"source_type", "ui_data", "ui_meta", "_assembled_v2"})
        # On loan: the exact objects the entry holds, so nothing was copied.
        self.assertIs(result["ui_data"], entry["ui_data"])
        assembled = result["_assembled_v2"]
        self.assertIs(assembled["source_contract"], entry["_assembled_v2"]["source_contract"])
        self.assertIs(
            result["ui_data"]["ui_contract"]["columns"],
            assembled["source_contract"]["columns"],
        )
        # Owned: the seal rewrites the contract and the request stamps its own meta.
        self.assertIsNot(assembled["contract"], entry["_assembled_v2"]["contract"])
        self.assertEqual(assembled["contract"], entry["_assembled_v2"]["contract"])
        self.assertIsNot(result["ui_meta"], entry["ui_meta"])
        self.assertEqual(result["ui_meta"], entry["ui_meta"])

    def test_shared_read_copies_the_bound_digests_instead_of_lending_them(self):
        entry = self._store()

        result = self._hit()
        result["_assembled_v2"][self.DIGESTS_KEY]["contractSha256"] = "c" * 64

        self.assertEqual(
            entry["_assembled_v2"][self.DIGESTS_KEY]["contractSha256"], "a" * 64
        )

    def test_shared_read_passes_through_the_other_gate_fields(self):
        self._store()

        result = self._hit()

        self.assertEqual(result["source_type"], "runtime_intent")
        self.assertEqual(result["_assembled_v2"]["cache_version"], self.GATE["cache_version"])
        self.assertEqual(result["_assembled_v2"]["client_type"], self.GATE["client_type"])
        self.assertEqual(result["_assembled_v2"]["delivery_profile"], self.GATE["delivery_profile"])
        self.assertEqual(result["_assembled_v2"]["limit_params"], self.GATE["limit_params"])

    def test_shared_read_refuses_any_gate_mismatch(self):
        cases = {
            "cache_version": {"gate": {"cache_version": "other-version"}},
            "client_type": {"gate": {"client_type": "web_mobile"}},
            "delivery_profile": {"gate": {"delivery_profile": "compact"}},
            "limit_params": {"gate": {"limit_params": {"limit": 5}}},
            "missing_limit_params": {"gate": {"limit_params": None}},
        }
        for name, kwargs in cases.items():
            with self.subTest(case=name):
                self._store()
                self.assertIsNone(self._hit(**kwargs))

    def test_shared_read_refuses_a_non_assembled_entry(self):
        for payload in (
            {"ui_data": {}, "ui_meta": {}},
            {"ui_data": {}, "ui_meta": {}, "_assembled_v2": "not-a-dict"},
            {
                "ui_data": {},
                "ui_meta": {},
                "_assembled_v2": {
                    "cache_version": self.GATE["cache_version"],
                    "client_type": self.GATE["client_type"],
                    "delivery_profile": self.GATE["delivery_profile"],
                    "limit_params": self.GATE["limit_params"],
                    "contract": "not-a-dict",
                    "source_contract": {"columns": []},
                },
            },
            {
                "ui_data": {},
                "ui_meta": {},
                "_assembled_v2": {
                    "cache_version": self.GATE["cache_version"],
                    "client_type": self.GATE["client_type"],
                    "delivery_profile": self.GATE["delivery_profile"],
                    "limit_params": self.GATE["limit_params"],
                    "contract": {"columns": []},
                    "source_contract": ["not-a-dict"],
                },
            },
        ):
            with self.subTest(payload=payload):
                self.cache.clear()
                self.cache.put("page", "source", payload)
                self.assertIsNone(self._hit())

    def test_shared_read_refuses_a_missing_entry_or_a_moved_source_token(self):
        self.assertIsNone(self._hit())
        self._store()
        self.assertIsNone(self._hit(cache_key="other-page"))
        self.assertIsNone(self._hit(source_token="source-v2"))
        # a moved token drops the entry, exactly like ``get``
        self.assertIsNone(self.cache.get("page", "source-v2"))

    def test_shared_read_refuses_an_expired_entry(self):
        now = [0.0]
        cache = TARGET.LoadContractResponseCache(
            max_entries=4, ttl_seconds=5, clock=lambda: now[0]
        )
        cache.put("page", "source", self._entry_payload())
        now[0] = 5.01

        self.assertIsNone(
            cache.get_assembled("page", "source", digests_key=self.DIGESTS_KEY, **self.GATE)
        )
        self.assertNotIn("page", cache._entries)

    def test_shared_read_keeps_the_entry_reachable_for_a_matching_request(self):
        self._store()

        self.assertIsNotNone(self._hit())
        self.assertIsNotNone(self._hit())
        self.assertEqual(list(self.cache._entries), ["page"])

    def test_gate_helper_is_the_single_gate_tuple(self):
        self.assertTrue(
            TARGET.assembled_snapshot_gate_matches(
                self._entry_payload(),
                cache_version=self.GATE["cache_version"],
                client_type=self.GATE["client_type"],
                delivery_profile=self.GATE["delivery_profile"],
                limit_params=self.GATE["limit_params"],
            )
        )
        for name, kwargs in (
            ("cache_version", {"cache_version": "other"}),
            ("client_type", {"client_type": "other"}),
            ("delivery_profile", {"delivery_profile": "other"}),
            ("limit_params", {"limit_params": {"limit": 1}}),
        ):
            with self.subTest(gate=name):
                gate = dict(
                    cache_version=self.GATE["cache_version"],
                    client_type=self.GATE["client_type"],
                    delivery_profile=self.GATE["delivery_profile"],
                    limit_params=self.GATE["limit_params"],
                )
                gate.update(kwargs)
                self.assertFalse(TARGET.assembled_snapshot_gate_matches(self._entry_payload(), **gate))
        for payload in (None, "text", [], {"ui_data": {}}):
            with self.subTest(payload=payload):
                self.assertFalse(
                    TARGET.assembled_snapshot_gate_matches(
                        payload,
                        cache_version=self.GATE["cache_version"],
                        client_type=self.GATE["client_type"],
                        delivery_profile=self.GATE["delivery_profile"],
                        limit_params=self.GATE["limit_params"],
                    )
                )

    def test_a_burst_of_real_seals_never_moves_the_entry(self):
        """The load-bearing proof: the real seal writes only its own copy.

        A burst of hot reads is delivered through the real lifecycle seal (not a
        test-side imitation), which stamps per-request meta into the contract and
        digests the loaned source payload. The entry must be byte-identical
        afterwards, or the loan would hand one request's mutations to the next.
        """
        lifecycle = _load_lifecycle_module()
        entry = self._store()
        # Bind the entry to the digests the real seal produces for exactly this
        # stored graph, the same way the handler writes them back on a miss.
        witness = lifecycle.seal_unified_page_contract(
            copy.deepcopy(entry["_assembled_v2"]["contract"]),
            source_payload=entry["_assembled_v2"]["source_contract"],
            source_type=entry["source_type"],
            request_id="witness",
            trace_id="witness",
            client_type=self.GATE["client_type"],
        )
        witness_lifecycle = witness["meta"]["lifecycle"]
        expected_contract_digest = witness_lifecycle["integrity"]["contractSha256"]
        expected_source_digest = witness_lifecycle["generation"]["sourceSha256"]
        entry["_assembled_v2"][self.DIGESTS_KEY] = {
            "contractSha256": expected_contract_digest,
            "sourceSha256": expected_source_digest,
        }
        before = _payload_digest(entry)

        seen_digests = set()
        for index in range(8):
            result = self._hit()
            self.assertIsNotNone(result)
            contract = result["_assembled_v2"]["contract"]
            source_contract = result["_assembled_v2"]["source_contract"]
            sealed = lifecycle.seal_unified_page_contract(
                contract,
                source_payload=source_contract,
                source_type=result["source_type"],
                request_id=f"request-{index}",
                trace_id=f"trace-{index}",
                client_type=self.GATE["client_type"],
                source_authority={"role": "finance"},
                reuse_digests=result["_assembled_v2"][self.DIGESTS_KEY],
            )
            integrity_ok, reason = lifecycle.verify_unified_page_contract_integrity(sealed)
            self.assertTrue(integrity_ok, reason)
            seen_digests.add(sealed["meta"]["lifecycle"]["integrity"]["contractSha256"])
            # the seal stamped its own copy, never the loaned graph
            self.assertNotIn("meta", result["_assembled_v2"]["source_contract"])

        self.assertEqual(_payload_digest(entry), before)
        self.assertNotIn("etag", entry["_assembled_v2"]["contract"]["meta"])
        self.assertNotIn("lifecycle", entry["_assembled_v2"]["contract"]["meta"])
        # one contract identity for every request: the reuse is a memo, not a
        # per-request value
        # reusing the bound digests reproduces the digest the seal recomputes: the
        # memo is a memo, never an authority
        self.assertEqual(seen_digests, {expected_contract_digest})

    def test_cross_request_pollution_of_the_loaned_graph_is_the_consumers_duty(self):
        """Documents where the boundary is enforced.

        ``get_assembled`` deliberately does NOT defend the loaned sections: it
        cannot, without giving back the copy it exists to avoid. The consumer is
        what keeps them read-only, so a write here is visible in the entry - this
        test pins that fact so the consumer-side guards (the handler AST guard
        below) stay the thing that is actually verified, instead of an assumed
        accessor-side protection.
        """
        entry = self._store()

        result = self._hit()
        result["ui_data"]["ui_contract"]["columns"].append("consumer-wrote-through-the-loan")

        self.assertEqual(
            entry["ui_data"]["ui_contract"]["columns"],
            ["name", "consumer-wrote-through-the-loan"],
        )


    def test_the_branch_rewrite_kept_the_gate_semantics(self):
        """The branch used to re-implement the gate inline; the helper must agree.

        Checked over a shape matrix, so the refactor that removed the duplicate
        gate is proven equivalent instead of assumed equivalent.
        """

        def removed_inline_gate(assembled_cached, *, is_create_request=False):
            return bool(
                isinstance(assembled_cached, dict)
                and not is_create_request
                and assembled_cached.get("cache_version") == self_gate["cache_version"]
                and assembled_cached.get("client_type") == self_gate["client_type"]
                and assembled_cached.get("delivery_profile") == self_gate["delivery_profile"]
                and assembled_cached.get("limit_params") == self_gate["limit_params"]
                and isinstance(assembled_cached.get("contract"), dict)
                and isinstance(assembled_cached.get("source_contract"), dict)
            )

        self_gate = dict(self.GATE)
        base = dict(
            cache_version=self_gate["cache_version"],
            client_type=self_gate["client_type"],
            delivery_profile=self_gate["delivery_profile"],
            limit_params=dict(self_gate["limit_params"]),
            contract={"columns": []},
            source_contract={"columns": []},
        )
        shapes = [
            ("match", dict(base)),
            ("version", {**base, "cache_version": "other"}),
            ("client", {**base, "client_type": "other"}),
            ("profile", {**base, "delivery_profile": "other"}),
            ("limits", {**base, "limit_params": {"limit": 1}}),
            ("no_limits", {k: v for k, v in base.items() if k != "limit_params"}),
            ("contract", {**base, "contract": "text"}),
            ("source", {**base, "source_contract": []}),
        ]
        for name, assembled in shapes:
            for entry in (
                {"_assembled_v2": assembled},
                {"_assembled_v2": assembled, "ui_data": {}},
                None,
                "text",
            ):
                with self.subTest(shape=name, entry=type(entry).__name__):
                    cached = entry
                    self.assertEqual(
                        TARGET.assembled_snapshot_gate_matches(
                            cached,
                            cache_version=self_gate["cache_version"],
                            client_type=self_gate["client_type"],
                            delivery_profile=self_gate["delivery_profile"],
                            limit_params=self_gate["limit_params"],
                        ),
                        removed_inline_gate(
                            cached.get("_assembled_v2") if isinstance(cached, dict) else None
                        ),
                    )

class TestSharedReadConsumerGuards(unittest.TestCase):
    """Static guards on the only consumer of the loaned graph (``_handle_contract``)."""

    SOURCE_PATH = MODULE_PATH.parents[1] / "handlers" / "ui_contract_v2.py"
    LOANED = ("ui_data", "source_contract")
    MUTATORS = frozenset({
        "update", "pop", "popitem", "setdefault", "clear", "append", "extend",
        "insert", "remove", "sort", "reverse",
    })

    @classmethod
    def setUpClass(cls):
        cls.tree = ast.parse(cls.SOURCE_PATH.read_text())

    @classmethod
    def _handler(cls):
        for node in ast.walk(cls.tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_handle_contract":
                return node
        raise AssertionError("_handle_contract not found")

    def _assembled_branch(self):
        for node in ast.walk(self._handler()):
            if not isinstance(node, ast.If):
                continue
            for inner in ast.walk(ast.Module(body=node.body, type_ignores=[])):
                if (
                    isinstance(inner, ast.Call)
                    and isinstance(inner.func, ast.Name)
                    and inner.func.id == "_reusable_assembled_digests"
                ):
                    return node
        raise AssertionError("the assembled hot branch was not found")

    def test_the_hot_read_routes_through_the_shared_accessor(self):
        handler = self._handler()
        shared_calls = [
            node for node in ast.walk(handler)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "get_assembled"
        ]
        self.assertEqual(len(shared_calls), 1)
        # ...and it is reached only for a request that cannot mutate the graph
        candidates = [
            node for node in ast.walk(handler)
            if isinstance(node, ast.If) and "get_assembled" in ast.unparse(node)
        ]
        self.assertTrue(candidates)
        # the innermost guard is the one that owns the call
        innermost = max(candidates, key=lambda node: node.lineno)
        guard = ast.unparse(innermost.test)
        self.assertIn("not runtime_record_id", guard)
        self.assertIn("not is_create_request", guard)
        # ...with the fully isolated read kept as the fallback
        fallback = [
            node for node in ast.walk(handler)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
        ]
        self.assertTrue(fallback, "the isolated get() fallback was removed")

    def test_the_assembled_branch_and_the_accessor_share_one_gate(self):
        branch = self._assembled_branch()
        self.assertIn("assembled_snapshot_gate_matches", ast.unparse(branch.test))
        # the gate tuple must not be re-implemented inline anywhere in the handler
        text = ast.unparse(self._handler())
        for stale in (
            "cache_version) ==",
            'assembled_cached.get("cache_version")',
            'assembled_cached.get("client_type")',
            'assembled_cached.get("delivery_profile")',
            'assembled_cached.get("limit_params")',
        ):
            with self.subTest(stale=stale):
                self.assertNotIn(stale, text)

    def test_the_assembled_branch_only_reads_the_loaned_sections(self):
        branch = self._assembled_branch()
        written = []
        for node in ast.walk(ast.Module(body=branch.body, type_ignores=[])):
            if isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Store):
                if isinstance(node.value, ast.Name) and node.value.id in self.LOANED:
                    written.append(ast.unparse(node))
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in self.MUTATORS
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id in self.LOANED
            ):
                written.append(ast.unparse(node))
            if isinstance(node, ast.Delete):
                for target in node.targets:
                    root = target
                    while isinstance(root, (ast.Subscript, ast.Attribute)):
                        root = root.value
                    if isinstance(root, ast.Name) and root.id in self.LOANED:
                        written.append(ast.unparse(target))
        self.assertEqual(
            written,
            [],
            "an assembled hit holds ui_data/source_contract on loan from the cache "
            "entry; writing there would hand this request's mutations to the next",
        )
        self.assertIsInstance(
            branch.body[-1],
            ast.Return,
            "the assembled branch must return instead of falling through to the "
            "assembly path, which writes into the graph it is handed",
        )


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


class TestAssembledCacheIdentityInvalidation(unittest.TestCase):
    """A record-free assembled hit must not survive a role or policy change.

    The assembled hit branch returns after re-sealing: it does not re-run
    entitlement, field/business policy, action, modifier or trim projection.
    That is only safe because the cache key contains the principal's group set
    and the source token contains the ACL/rule/user rows and the *definition* of
    every business policy. These negative cases pin both halves; without them a
    re-seal would be mistaken for a fresh authorization decision.
    """

    @staticmethod
    def _key_env(group_ids, *, company_id=1):
        return SimpleNamespace(
            cr=SimpleNamespace(dbname="sc_dev_demo"),
            user=SimpleNamespace(id=7, groups_id=SimpleNamespace(ids=list(group_ids))),
            company=SimpleNamespace(id=company_id),
            context={"lang": "zh_CN", "allowed_company_ids": [company_id]},
        )

    @staticmethod
    def _projection_key(env, params=None, context=None):
        return TARGET.build_projection_cache_key(
            env,
            namespace="ui.contract.v2.source.single-assembly.v1",
            params=params or {"model": "project.project"},
            model_name="project.project",
            view_types="form",
            context=context or {"lang": "zh_CN", "allowed_company_ids": [env.company.id]},
        )

    def test_role_revocation_changes_the_cache_key(self):
        before = self._projection_key(self._key_env([11, 12, 13]))
        revoked = self._projection_key(self._key_env([11, 12]))

        self.assertTrue(before)
        self.assertTrue(revoked)
        self.assertNotEqual(
            before,
            revoked,
            "removing one group from the principal must make the assembled entry unreachable",
        )

    def test_company_scope_changes_the_cache_key(self):
        first = self._projection_key(self._key_env([11], company_id=1))
        second = self._projection_key(self._key_env([11], company_id=2))

        self.assertNotEqual(first, second)

    def test_transport_only_params_do_not_churn_the_key(self):
        env = self._key_env([11])
        first = self._projection_key(env, {"model": "project.project", "request_id": "a"})
        second = self._projection_key(env, {"model": "project.project", "request_id": "b"})

        self.assertEqual(first, second)

    class _TokenModel:
        _fields = {"write_date": object()}

        def __init__(self, row, id_rows=None):
            self.row = row
            self.id_rows = id_rows

        def sudo(self):
            return self

        def with_context(self, **_kwargs):
            return self

        def search(self, _domain, **kwargs):
            if kwargs.get("order") == "id":
                return list(self.id_rows or [])
            return self.row

    class _TokenEnv:
        def __init__(self, rows):
            self.rows = rows
            self.user = SimpleNamespace(id=7, groups_id=SimpleNamespace(ids=[11]))
            self.company = SimpleNamespace(id=1)
            self.cr = SimpleNamespace(dbname="sc_dev_demo")

        def __contains__(self, _model_code):
            return True

        def __getitem__(self, model_code):
            value = self.rows[model_code]
            if model_code == "ui.business.config.contract":
                return TestAssembledCacheIdentityInvalidation._TokenModel(None, id_rows=value)
            return TestAssembledCacheIdentityInvalidation._TokenModel(value)

    @staticmethod
    def _default_token_rows():
        rows = {
            model_code: SimpleNamespace(
                id=1,
                write_date="2026-10-17 00:00:00",
                latest_version="",
            )
            for model_code in (
                "ir.ui.view",
                "ir.model.fields",
                "ir.actions.act_window",
                "ir.ui.menu",
                "ir.model.access",
                "ir.rule",
                "res.users",
                "ir.module.module",
                "app.model.config",
                "app.view.config",
                "app.search.config",
                "app.permission.config",
                "app.action.config",
                "ui.form.field.policy",
                "ui.menu.config.policy",
                "sc.approval.policy",
                "sc.scene",
            )
        }
        rows["ui.business.config.contract"] = [
            SimpleNamespace(
                id=1,
                definition_sha256="definition-a",
                version_no=1,
                status="published",
                active=True,
            )
        ]
        return rows

    def _source_token(self, rows):
        with patch.object(TARGET, "contract_code_fingerprint", return_value="c" * 64):
            with patch.dict(
                os.environ,
                {"SC_SOURCE_REVISION": "a" * 40, "SC_SOURCE_FINGERPRINT": "b" * 64},
                clear=False,
            ):
                return TARGET.build_projection_source_token(
                    self._TokenEnv(rows), model_name="project.project", action_id=506
                )

    def test_role_revocation_reaches_the_source_token(self):
        before = self._default_token_rows()
        after = self._default_token_rows()
        after["res.users"] = SimpleNamespace(
            id=1, write_date="2026-10-17 00:00:01", latest_version=""
        )

        self.assertNotEqual(
            self._source_token(before),
            self._source_token(after),
            "a group membership write moves res.users.write_date and must invalidate the token",
        )

    def test_acl_change_reaches_the_source_token(self):
        before = self._default_token_rows()
        after = self._default_token_rows()
        after["ir.model.access"] = SimpleNamespace(
            id=1, write_date="2026-10-17 00:00:01", latest_version=""
        )

        self.assertNotEqual(self._source_token(before), self._source_token(after))

    def test_business_policy_definition_change_reaches_the_source_token(self):
        before = self._default_token_rows()
        after = self._default_token_rows()
        after["ui.business.config.contract"] = [
            SimpleNamespace(
                id=1,
                definition_sha256="definition-b",
                version_no=1,
                status="published",
                active=True,
            )
        ]

        self.assertNotEqual(self._source_token(before), self._source_token(after))

    def test_unchanged_authorities_produce_a_stable_source_token(self):
        self.assertEqual(
            self._source_token(self._default_token_rows()),
            self._source_token(self._default_token_rows()),
        )

    def test_assembled_entry_is_unreachable_after_role_revocation(self):
        cache = LoadContractResponseCache(max_entries=2, ttl_seconds=30, clock=lambda: 0.0)
        env_before = self._key_env([11, 12, 13])
        key_before = self._projection_key(env_before)
        token_before = self._source_token(self._default_token_rows())
        cache.put_generated(
            key_before,
            token_before,
            lambda: self._stored_snapshot({"page": "before"}),
        )

        self.assertIsNotNone(cache.get_assembled(
            key_before,
            token_before,
            cache_version="test",
            client_type="web",
            delivery_profile="full",
            limit_params={},
            digests_key="assembled_semantic_digests",
        ))

        key_after = self._projection_key(self._key_env([11, 12]))
        self.assertIsNone(cache.get(key_after, token_before))
        self.assertIsNone(cache.get_assembled(
            key_after,
            token_before,
            cache_version="test",
            client_type="web",
            delivery_profile="full",
            limit_params={},
            digests_key="assembled_semantic_digests",
        ))

    def test_assembled_entry_is_unreachable_after_policy_change(self):
        cache = LoadContractResponseCache(max_entries=2, ttl_seconds=30, clock=lambda: 0.0)
        env = self._key_env([11, 12])
        key = self._projection_key(env)
        token_before = self._source_token(self._default_token_rows())
        cache.put_generated(
            key,
            token_before,
            lambda: self._stored_snapshot({"page": "before"}),
        )

        self.assertIsNotNone(cache.get_assembled(
            key,
            token_before,
            cache_version="test",
            client_type="web",
            delivery_profile="full",
            limit_params={},
            digests_key="assembled_semantic_digests",
        ))

        changed_rows = self._default_token_rows()
        changed_rows["ui.business.config.contract"] = [
            SimpleNamespace(
                id=1,
                definition_sha256="definition-b",
                version_no=1,
                status="published",
                active=True,
            )
        ]
        token_after = self._source_token(changed_rows)

        self.assertIsNone(cache.get(key, token_after))
        self.assertIsNone(cache.get_assembled(
            key,
            token_after,
            cache_version="test",
            client_type="web",
            delivery_profile="full",
            limit_params={},
            digests_key="assembled_semantic_digests",
        ))

    @staticmethod
    def _stored_snapshot(contract):
        return {
            "_assembled_v2": {
                "cache_version": "test",
                "client_type": "web",
                "delivery_profile": "full",
                "limit_params": {},
                "contract": contract,
                "source_contract": {},
                "assembled_semantic_digests": {},
            }
        }


if __name__ == "__main__":
    unittest.main()
