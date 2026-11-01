# -*- coding: utf-8 -*-
from __future__ import annotations

import unittest

from odoo.addons.smart_core.core import native_view_parsed_cache as cache


class _FakeEnv:
    def __init__(self, uid, context=None):
        self.uid = uid
        self.cr = object()
        self.context = dict(context or {})


class TestNativeViewParsedCache(unittest.TestCase):
    def tearDown(self):
        cache.clear_all()

    def test_store_and_fetch_roundtrip(self):
        env = _FakeEnv(1, {"lang": "zh_CN", "contract_action_id": 590})
        view_data = {"arch": "<form/>", "_arch_root": object(), "fields": {}}
        cache.store_parsed_view(env, "project.project", "form", 1776, view_data)
        self.assertIs(
            cache.fetch_parsed_view(env, "project.project", "form", 1776)["_arch_root"],
            view_data["_arch_root"],
        )

    def test_different_user_does_not_share(self):
        env1 = _FakeEnv(1, {"lang": "zh_CN"})
        env2 = _FakeEnv(2, {"lang": "zh_CN"})
        cache.store_parsed_view(env1, "project.project", "form", 1776, {"arch": "a"})
        self.assertIsNone(cache.fetch_parsed_view(env2, "project.project", "form", 1776))

    def test_different_context_does_not_reuse(self):
        env1 = _FakeEnv(1, {"lang": "zh_CN", "contract_action_id": 590})
        env2 = _FakeEnv(1, {"lang": "en_US", "contract_action_id": 590})
        cache.store_parsed_view(env1, "project.project", "form", 1776, {"arch": "a"})
        self.assertIsNone(cache.fetch_parsed_view(env2, "project.project", "form", 1776))

    def test_clear_request_drops_only_one_cursor(self):
        env1 = _FakeEnv(1)
        env2 = _FakeEnv(1)
        cache.store_parsed_view(env1, "project.project", "form", 1776, {"arch": "a"})
        cache.store_parsed_view(env2, "project.project", "form", 1776, {"arch": "b"})
        cache.clear_request(env1)
        self.assertIsNone(cache.fetch_parsed_view(env1, "project.project", "form", 1776))
        self.assertIsNotNone(cache.fetch_parsed_view(env2, "project.project", "form", 1776))


if __name__ == "__main__":
    unittest.main()

