# -*- coding: utf-8 -*-
from __future__ import annotations

import unittest

from odoo.addons.smart_core.core.native_view_parsed_cache import RequestScopedCarrier


class _FakeCursor:
    _counter = 0

    def __init__(self):
        _FakeCursor._counter += 1
        self.id = _FakeCursor._counter
        self.closed = False

    def close(self):
        self.closed = True


class _FakeEnv:
    def __init__(self, uid, su=False, context=None, cursor=None):
        self.uid = uid
        self.su = su
        self.cr = cursor if cursor is not None else _FakeCursor()
        self.context = dict(context or {})


class TestRequestScopedCarrier(unittest.TestCase):
    def test_same_request_same_view_hits(self):
        env = _FakeEnv(1, context={"lang": "zh_CN", "contract_action_id": 590})
        carrier = RequestScopedCarrier(env)
        root = object()
        carrier.store(env, "project.project", "form", 1776, {"_arch_root": root})
        self.assertIs(carrier.fetch(env, "project.project", "form", 1776)["_arch_root"], root)

    def test_different_cursor_does_not_share(self):
        env1 = _FakeEnv(1, context={"lang": "zh_CN"})
        env2 = _FakeEnv(1, context={"lang": "zh_CN"})
        carrier = RequestScopedCarrier(env1)
        carrier.store(env1, "project.project", "form", 1776, {"_arch_root": object()})
        self.assertIsNone(carrier.fetch(env2, "project.project", "form", 1776))

    def test_closed_cursor_rejects_hit(self):
        env = _FakeEnv(1, context={"lang": "zh_CN"})
        carrier = RequestScopedCarrier(env)
        carrier.store(env, "project.project", "form", 1776, {"_arch_root": object()})
        env.cr.close()
        self.assertIsNone(carrier.fetch(env, "project.project", "form", 1776))

    def test_different_uid_isolated(self):
        carrier = RequestScopedCarrier(_FakeEnv(1, context={"lang": "zh_CN"}))
        carrier.store(_FakeEnv(1, context={"lang": "zh_CN"}), "project.project", "form", 1776, {"a": 1})
        other = _FakeEnv(2, context={"lang": "zh_CN"})
        self.assertIsNone(carrier.fetch(other, "project.project", "form", 1776))

    def test_different_su_isolated(self):
        base = _FakeEnv(1, su=False, context={"lang": "zh_CN"})
        su = _FakeEnv(1, su=True, context={"lang": "zh_CN"})
        carrier = RequestScopedCarrier(base)
        carrier.store(base, "project.project", "form", 1776, {"a": 1})
        self.assertIsNone(carrier.fetch(su, "project.project", "form", 1776))

    def test_different_lang_isolated(self):
        zh = _FakeEnv(1, context={"lang": "zh_CN"})
        en = _FakeEnv(1, context={"lang": "en_US"})
        carrier = RequestScopedCarrier(zh)
        carrier.store(zh, "project.project", "form", 1776, {"a": 1})
        self.assertIsNone(carrier.fetch(en, "project.project", "form", 1776))

    def test_different_view_isolated(self):
        env = _FakeEnv(1, context={"lang": "zh_CN"})
        carrier = RequestScopedCarrier(env)
        carrier.store(env, "project.project", "form", 1776, {"a": 1})
        self.assertIsNone(carrier.fetch(env, "project.project", "form", 944))

    def test_close_clears_entries_and_releases_cursor(self):
        env = _FakeEnv(1)
        carrier = RequestScopedCarrier(env)
        carrier.store(env, "project.project", "form", 1776, {"a": 1})
        carrier.close()
        self.assertIsNone(carrier.fetch(env, "project.project", "form", 1776))
        self.assertIsNone(carrier._cursor)

    def test_missing_cursor_fake_env_degrades(self):
        class NoCursorEnv:
            uid = 1
            su = False
            context = {}

        env = NoCursorEnv()
        carrier = RequestScopedCarrier(env)
        carrier.store(env, "project.project", "form", 1776, {"a": 1})
        self.assertIsNone(carrier.fetch(env, "project.project", "form", 1776))


if __name__ == "__main__":
    unittest.main()

