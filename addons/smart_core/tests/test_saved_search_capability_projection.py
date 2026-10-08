#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""收藏能力必须来自权威判定，不能是常量。

反例核心：同一个模型级 search_def 缓存，在不同用户/权限下必须投影出不同的
save_enabled。旧的 `save_enabled: True` 常量无法同时满足这些断言。
"""
from __future__ import annotations

import ast
import importlib.util
import logging
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SEARCH_PATH = ROOT / "addons/smart_core/app_config_engine/models/app_search_config.py"
AUTHORITY_PATH = ROOT / "addons/smart_core/handlers/ui_contract_v2_authority.py"


def _load_module_definitions(path: Path, stubs: dict) -> dict:
    """执行模块自身的顶层定义，只把外部 import 换成替身。

    一个只用到单个函数的用例，不应该手工拼装该函数的模块级依赖：seal 边界后来
    新增了发布版本引用与投递观测两个顶层 helper，而手工列举的命名空间不会同步，
    于是用例静默报 NameError。执行全部非 import 的顶层语句后，被测函数能拿到真实
    的传递依赖，只有外部 import 面需要替身。future import 属于 import 语句，这里
    显式补回，否则抽取出来的定义会提前求值注解。
    """
    tree = ast.parse(path.read_text(), filename=str(path))
    body = [
        node for node in tree.body
        if not isinstance(node, (ast.Import, ast.ImportFrom))
    ]
    future = ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)
    module = ast.fix_missing_locations(ast.Module(body=[future, *body], type_ignores=[]))
    namespace = {
        "__name__": "smart_core_test_ui_contract_v2_authority",
        "__file__": str(path),
        **stubs,
    }
    exec(compile(module, str(path), "exec"), namespace)
    return namespace


class _FieldFactory:
    def __getattr__(self, _name):
        def _field(*_args, **_kwargs):
            return None

        return _field


class _Api:
    @staticmethod
    def model(func):
        return func


class _Groups:
    ids = []


class _User:
    def __init__(self, internal=True):
        self.groups_id = _Groups()
        self._internal = internal

    def has_group(self, xmlid):
        return bool(self._internal) and xmlid == "base.group_user"


class _Model:
    def __init__(self, readable=True):
        self._readable = readable
        self.checked = []

    def check_access_rights(self, operation, raise_exception=False):
        self.checked.append(operation)
        if operation == "read":
            return bool(self._readable)
        return False


class _FilterRecordset:
    """ir.filters 记录集替身：只实现能力判定所需的最小面。"""

    def __init__(self, ids, *, writable=(), deletable=()):
        self.ids = list(ids)
        self._writable = set(writable)
        self._deletable = set(deletable)

    def _filter_access_rules(self, operation):
        if operation == "write":
            return _FilterRecordset(sorted(self._writable))
        if operation == "unlink":
            return _FilterRecordset(sorted(self._deletable))
        raise AssertionError(f"unexpected operation {operation}")


class _FilterModel:
    _fields: dict = {}

    def __init__(self, *, create_allowed=True, writable=(), deletable=(), browse_raises=False):
        self._create_allowed = create_allowed
        self._writable = set(writable)
        self._deletable = set(deletable)
        self._browse_raises = browse_raises
        self.browsed_ids = []

    def sudo(self):
        return self

    def check_access_rights(self, operation, raise_exception=False):
        return bool(self._create_allowed) if operation == "create" else operation in ("read", "unlink")

    def search(self, domain, limit=None):
        return []

    def browse(self, ids):
        if self._browse_raises:
            raise RuntimeError("ir.filters unavailable")
        self.browsed_ids.append(list(ids))
        return _FilterRecordset(ids, writable=self._writable, deletable=self._deletable)


class _Env(dict):
    def __init__(self, *, uid=7, internal=True, readable=True, filters=None, model="x.demo", with_filters=True):
        super().__init__()
        self.uid = uid
        self.user = _User(internal=internal)
        target = _Model(readable=readable)
        if model:
            self[model] = target
        self.target_model = target
        if with_filters and filters is not None:
            self["ir.filters"] = filters


def _install_odoo_stub():
    odoo = types.ModuleType("odoo")
    odoo.models = types.SimpleNamespace(Model=object, AbstractModel=object)
    odoo.fields = _FieldFactory()
    odoo.api = _Api()
    odoo._ = lambda text, *args, **kwargs: text % args if args else text

    tools = types.ModuleType("odoo.tools")
    safe_eval_mod = types.ModuleType("odoo.tools.safe_eval")
    safe_eval_mod.safe_eval = lambda value, *_args, **_kwargs: value
    tools.safe_eval = safe_eval_mod.safe_eval

    sys.modules["odoo"] = odoo
    sys.modules["odoo.tools"] = tools
    sys.modules["odoo.tools.safe_eval"] = safe_eval_mod


def _load_module():
    _install_odoo_stub()
    spec = importlib.util.spec_from_file_location("smart_core_test_saved_search_capability", SEARCH_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _record(module, env, *, rows=None):
    record = module.AppSearchConfig.__new__(module.AppSearchConfig)
    record.env = env
    record.model = "x.demo"
    record.version = 3
    record.search_def = {
        "filters": [],
        "group_by": [],
        "facets": {"enabled": True},
        "saved_filters": [],
        "custom": {
            "enabled": True,
            "favorites": {
                "label": "加入收藏",
                "intent": "search.favorite.set",
                "owner_scope": "current_user",
                "shared_enabled": False,
                "save_enabled": False,
            },
        },
        "defaults": {"limit": 20, "order": "id desc"},
    }
    record.ensure_one = lambda: None
    if rows is not None:
        record._collect_ir_filters = lambda model_name, action_id=None: [dict(row) for row in rows]
    return record


class SavedSearchSaveCapabilityTests(unittest.TestCase):
    def test_save_capability_follows_authority_instead_of_a_constant(self):
        module = _load_module()
        allowed_env = _Env(filters=_FilterModel(create_allowed=True))
        contract = _record(module, allowed_env).get_search_contract(
            filter_runtime=True, include_user_filters=True
        )
        favorites = contract["custom"]["favorites"]
        self.assertTrue(favorites["save_enabled"])
        self.assertEqual(favorites["disabled_reason"], "")
        self.assertEqual(favorites["owner_scope"], "current_user")
        self.assertFalse(favorites["shared_enabled"])

        denied_env = _Env(filters=_FilterModel(create_allowed=False))
        denied = _record(module, denied_env).get_search_contract(
            filter_runtime=True, include_user_filters=True
        )
        self.assertFalse(denied["custom"]["favorites"]["save_enabled"])
        self.assertEqual(
            denied["custom"]["favorites"]["disabled_reason"], "SAVED_SEARCH_CREATE_DENIED"
        )

    def test_non_internal_user_cannot_save_favorite(self):
        module = _load_module()
        env = _Env(internal=False, filters=_FilterModel(create_allowed=True))
        contract = _record(module, env).get_search_contract(
            filter_runtime=True, include_user_filters=True
        )
        favorites = contract["custom"]["favorites"]
        self.assertFalse(favorites["save_enabled"])
        self.assertEqual(favorites["disabled_reason"], "SAVED_SEARCH_REQUIRES_INTERNAL_USER")

    def test_model_read_denied_withholds_favorite_save(self):
        module = _load_module()
        env = _Env(readable=False, filters=_FilterModel(create_allowed=True))
        contract = _record(module, env).get_search_contract(
            filter_runtime=True, include_user_filters=True
        )
        favorites = contract["custom"]["favorites"]
        self.assertFalse(favorites["save_enabled"])
        self.assertEqual(favorites["disabled_reason"], "SAVED_SEARCH_MODEL_READ_DENIED")

    def test_missing_authority_fails_closed(self):
        module = _load_module()
        env = _Env(filters=None, with_filters=False)
        contract = _record(module, env).get_search_contract(
            filter_runtime=True, include_user_filters=True
        )
        favorites = contract["custom"]["favorites"]
        self.assertFalse(favorites["save_enabled"])
        self.assertEqual(favorites["disabled_reason"], "SAVED_SEARCH_AUTHORITY_UNAVAILABLE")

    def test_runtime_projection_overrides_static_conservative_default(self):
        module = _load_module()
        env = _Env(filters=_FilterModel(create_allowed=True))
        record = _record(module, env)
        stored = record.get_search_contract(filter_runtime=False, include_user_filters=False)
        self.assertFalse(stored["custom"]["favorites"]["save_enabled"])
        runtime = record.get_search_contract(filter_runtime=True, include_user_filters=True)
        self.assertTrue(runtime["custom"]["favorites"]["save_enabled"])
        self.assertEqual(stored["custom"]["favorites"]["label"], "加入收藏")


class SavedFilterMutationCapabilityTests(unittest.TestCase):
    rows = [
        {"id": 1, "name": "Mine", "owner": 7, "is_shared": False},
        {"id": 2, "name": "Other", "owner": 9, "is_shared": False},
        {"id": 3, "name": "Shared", "owner": None, "is_shared": True},
    ]

    def test_private_filter_of_another_user_is_not_projected(self):
        module = _load_module()
        filters = _FilterModel(create_allowed=True, writable=(1, 3), deletable=(1,))
        env = _Env(filters=filters)
        contract = _record(module, env, rows=self.rows).get_search_contract(
            filter_runtime=True, include_user_filters=True
        )
        self.assertEqual([1, 3], sorted(row["id"] for row in contract["saved_filters"]))

    def test_rows_expose_ownership_and_authoritative_mutation(self):
        module = _load_module()
        filters = _FilterModel(create_allowed=True, writable=(1, 3), deletable=(1,))
        env = _Env(filters=filters)
        contract = _record(module, env, rows=self.rows).get_search_contract(
            filter_runtime=True, include_user_filters=True
        )
        by_id = {row["id"]: row for row in contract["saved_filters"]}
        self.assertTrue(by_id[1]["owned_by_current_user"])
        self.assertTrue(by_id[1]["writable"])
        self.assertTrue(by_id[1]["deletable"])
        self.assertEqual(by_id[1]["delete_action"]["intent"], "search.favorite.delete")
        self.assertEqual(by_id[1]["delete_action"]["params"]["model"], "x.demo")
        self.assertTrue(by_id[1]["delete_action"]["enabled"])
        self.assertFalse(by_id[3]["delete_action"]["enabled"])
        self.assertFalse(by_id[3]["owned_by_current_user"])
        self.assertTrue(by_id[3]["writable"])
        self.assertFalse(by_id[3]["deletable"])
        self.assertEqual([1, 3], sorted(filters.browsed_ids[0]))

    def test_foreign_private_row_capability_is_denied(self):
        module = _load_module()
        filters = _FilterModel(create_allowed=True, writable=(1, 3), deletable=(1,))
        env = _Env(filters=filters)
        record = _record(module, env)
        rows = record._project_saved_filter_mutation_rows(
            [dict(row) for row in self.rows], env.uid
        )
        by_id = {row["id"]: row for row in rows}
        self.assertFalse(by_id[2]["owned_by_current_user"])
        self.assertFalse(by_id[2]["writable"])
        self.assertFalse(by_id[2]["deletable"])

    def test_unresolved_mutation_rules_fail_closed(self):
        module = _load_module()
        filters = _FilterModel(create_allowed=True, browse_raises=True)
        env = _Env(filters=filters)
        contract = _record(module, env, rows=self.rows).get_search_contract(
            filter_runtime=True, include_user_filters=True
        )
        self.assertTrue(contract["saved_filters"])
        for row in contract["saved_filters"]:
            self.assertFalse(row["writable"])
            self.assertFalse(row["deletable"])
        self.assertTrue(contract["saved_filters"][0]["owned_by_current_user"])


class CachedFavoriteRuntimeTests(unittest.TestCase):
    def test_deleted_rows_replace_cached_rows_with_empty_set(self):
        module = _load_module()
        record = _record(module, _Env(filters=_FilterModel(create_allowed=True)), rows=[])
        cached = {'saved_filters': [{'id': 7}], 'filters': [{'key': 'native'}]}
        record.refresh_saved_search_runtime(cached, 'x.demo', action_id=775)
        self.assertEqual(cached['saved_filters'], [])
        self.assertEqual(cached['filters'], [{'key': 'native'}])
        self.assertTrue(cached['custom']['favorites']['save_enabled'])

    def test_runtime_scope_and_permission_are_refreshed(self):
        module = _load_module()
        env = _Env(filters=_FilterModel(create_allowed=False))
        record = _record(module, env)
        calls = []
        def rows(model, action_id=None):
            calls.append((model, action_id))
            return [{'id': 1, 'owner': env.uid}, {'id': 2, 'owner': env.uid + 1}, {'id': 3, 'is_shared': True}]
        record._collect_ir_filters = rows
        cached = {'custom': {'favorites': {'save_enabled': True}}, 'saved_filters': []}
        record.refresh_saved_search_runtime(cached, 'x.demo', action_id=775)
        self.assertEqual(calls, [('x.demo', 775)])
        self.assertEqual([row['id'] for row in cached['saved_filters']], [1, 3])
        self.assertFalse(cached['custom']['favorites']['save_enabled'])

    def test_runtime_lookup_failure_does_not_deliver_cached_favorites(self):
        module = _load_module()
        record = _record(module, _Env(filters=_FilterModel(create_allowed=True)))
        def unavailable(*args, **kwargs):
            raise RuntimeError('authority unavailable')
        record._collect_ir_filters = unavailable
        with self.assertRaisesRegex(RuntimeError, 'authority unavailable'):
            record.refresh_saved_search_runtime({'saved_filters': [{'id': 7}]}, 'x.demo', action_id=775)

    def test_runtime_seal_refreshes_before_sealing(self):
        events = []

        class Search:
            def refresh_saved_search_runtime(self, contract, model, action_id=None):
                events.append(('refresh', model, action_id))
                contract['saved_filters'] = []

        def seal(contract, **kwargs):
            events.append(('seal', len(contract['searchContract']['saved_filters'])))
            return contract

        namespace = _load_module_definitions(AUTHORITY_PATH, {
            'logging': logging,
            'seal_unified_page_contract': seal,
            'verify_unified_page_contract_integrity': lambda _sealed: (True, ''),
            'build_observation': lambda **kwargs: kwargs,
            'emit_observation_line': lambda _observation, **_kwargs: True,
            'resolve_published_version_ref': lambda *_args, **_kwargs: '',
            '_slo_store': types.SimpleNamespace(persist_line=lambda *_args, **_kwargs: None),
        })
        owner = types.SimpleNamespace(
            env={'app.search.config': Search()},
            SOURCE_KIND='test',
            VERSION='1',
            source_authority_contract=lambda: {},
        )
        contract = {'searchContract': {'saved_filters': [{'id': 7}]}}
        namespace['seal_runtime_contract'](
            owner, contract, {'model': 'x.demo'}, 'ui.contract', 'r', 't', 'web_pc', action_id=775,
        )
        self.assertEqual(events, [('refresh', 'x.demo', 775), ('seal', 0)])


class SavedSearchDeleteCapabilityTests(unittest.TestCase):
    def test_shared_delete_is_denied_even_when_record_rule_allows(self):
        module = _load_module()
        env = _Env(filters=_FilterModel(deletable=(1, 2)))
        rows = _record(module, env)._project_saved_filter_mutation_rows(
            [{"id":1,"owner":7,"action_id":31},{"id":2,"owner":False,"is_shared":True}], 7, "x.demo")
        self.assertTrue(rows[0]["delete_action"]["enabled"])
        self.assertEqual(rows[0]["delete_action"]["params"], {"filter_id":1,"model":"x.demo","action_id":31})
        self.assertFalse(rows[1]["deletable"])
        self.assertFalse(rows[1]["delete_action"]["enabled"])

    def test_delete_requires_acl_internal_user_and_readable_model(self):
        module = _load_module()
        for denied in ("read", "unlink", "internal", "model"):
            with self.subTest(denied=denied):
                filters = _FilterModel(deletable=(1,))
                if denied in ("read", "unlink"):
                    filters.check_access_rights = lambda operation, raise_exception=False: operation != denied
                env = _Env(filters=filters, internal=denied != "internal", readable=denied != "model")
                rows = _record(module, env)._project_saved_filter_mutation_rows([{"id":1,"owner":7}],7,"x.demo")
                self.assertFalse(rows[0]["delete_action"]["enabled"])

    def test_delete_does_not_require_create_permission(self):
        module = _load_module()
        env = _Env(filters=_FilterModel(create_allowed=False, deletable=(1,)))
        rows = _record(module, env)._project_saved_filter_mutation_rows([{"id":1,"owner":7}],7,"x.demo")
        self.assertTrue(rows[0]["delete_action"]["enabled"])


if __name__ == "__main__":
    unittest.main()
