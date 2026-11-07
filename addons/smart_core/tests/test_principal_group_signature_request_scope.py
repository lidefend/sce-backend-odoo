# -*- coding: utf-8 -*-
"""Host-runnable request-scope lock for principal group xmlid resolution.

``runtime_route_authority._request_cached_user_group_xmlids`` must resolve the
principal's effective group xmlids at most once per request (per cursor) and
must never let the snapshot cross a cursor, user, or group-id boundary. This
test loads ``runtime_route_authority.py`` with a stubbed identity resolver, so
it runs without a live Odoo runtime.
"""
from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace


REPO = Path(__file__).resolve().parents[3]
MODULE_PATH = (
    REPO
    / "addons"
    / "smart_core"
    / "delivery"
    / "runtime_route_authority.py"
)


_RESOLUTIONS = {"count": 0}


class _FakeIdentityResolver:
    def __init__(self, env):
        self.env = env

    def user_group_xmlids(self, user):
        _RESOLUTIONS["count"] += 1
        return {f"group_{group_id}" for group_id in (user.groups_id.ids or ())}


def _load_module():
    for name in ("smart_core", "smart_core.identity", "smart_core.delivery"):
        sys.modules.setdefault(name, types.ModuleType(name))
    identity = types.ModuleType("smart_core.identity.identity_resolver")
    identity.IdentityResolver = _FakeIdentityResolver
    sys.modules["smart_core.identity.identity_resolver"] = identity
    spec = importlib.util.spec_from_file_location(
        "smart_core.delivery.runtime_route_authority", MODULE_PATH
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["smart_core.delivery.runtime_route_authority"] = module
    spec.loader.exec_module(module)
    return module


MODULE = _load_module()


class _Cursor:
    pass


class _User:
    def __init__(self, uid, group_ids):
        self.id = uid
        self.groups_id = SimpleNamespace(ids=group_ids)


class _Env:
    def __init__(self, cursor, user):
        self.cr = cursor
        self.user = user


class TestPrincipalGroupSignatureRequestScope(unittest.TestCase):
    def test_same_request_resolves_once(self):
        cursor = _Cursor()
        env = _Env(cursor, _User(7, [1, 2, 3]))
        _RESOLUTIONS["count"] = 0
        first = MODULE._request_cached_user_group_xmlids(env)
        second = MODULE._request_cached_user_group_xmlids(env)
        third = MODULE._request_cached_user_group_xmlids(env)
        self.assertEqual(first, second)
        self.assertEqual(first, third)
        self.assertEqual(_RESOLUTIONS["count"], 1)

    def test_different_user_recomputes(self):
        cursor = _Cursor()
        _RESOLUTIONS["count"] = 0
        first = MODULE._request_cached_user_group_xmlids(_Env(cursor, _User(7, [1, 2])))
        second = MODULE._request_cached_user_group_xmlids(_Env(cursor, _User(8, [1, 2])))
        self.assertEqual(_RESOLUTIONS["count"], 2)
        self.assertEqual(first, second)

    def test_different_cursor_recomputes(self):
        _RESOLUTIONS["count"] = 0
        first = MODULE._request_cached_user_group_xmlids(_Env(_Cursor(), _User(7, [1, 2])))
        second = MODULE._request_cached_user_group_xmlids(_Env(_Cursor(), _User(7, [1, 2])))
        self.assertEqual(_RESOLUTIONS["count"], 2)
        self.assertEqual(first, second)

    def test_group_id_change_recomputes(self):
        cursor = _Cursor()
        _RESOLUTIONS["count"] = 0
        first = MODULE._request_cached_user_group_xmlids(_Env(cursor, _User(7, [1, 2])))
        second = MODULE._request_cached_user_group_xmlids(_Env(cursor, _User(7, [1, 2, 3])))
        self.assertEqual(_RESOLUTIONS["count"], 2)
        self.assertNotEqual(first, second)


if __name__ == "__main__":
    unittest.main()
