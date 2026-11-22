# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import sys
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
CONTEXT_PATH = ROOT / "core" / "system_init_request_context.py"


def _load_context():
    spec = importlib.util.spec_from_file_location(
        "system_init_request_context_under_test", CONTEXT_PATH
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _env(user_id=7, company_id=3, database="sc_test"):
    return SimpleNamespace(
        cr=SimpleNamespace(dbname=database),
        user=SimpleNamespace(id=user_id),
        company=SimpleNamespace(id=company_id),
    )


class SystemInitRequestContextTest(unittest.TestCase):
    def test_loader_runs_once_and_consumers_share_the_same_value(self):
        module = _load_context()
        calls = []
        context = module.SystemInitRequestContext(_env())
        value = {"rows": [{"code": "projects.list"}]}

        def load():
            calls.append("load")
            return value

        first, first_loaded = context.resolve("scene_declarations", load)
        second, second_loaded = context.resolve("scene_declarations", load)

        self.assertIs(first, value)
        self.assertIs(second, value)
        self.assertTrue(first_loaded)
        self.assertFalse(second_loaded)
        self.assertEqual(calls, ["load"])
        self.assertEqual(context.loaded_keys(), ("scene_declarations",))

    def test_keys_and_contexts_are_isolated(self):
        module = _load_context()
        first_context = module.SystemInitRequestContext(_env(user_id=7))
        second_context = module.SystemInitRequestContext(_env(user_id=8))
        first_calls = []
        second_calls = []

        first, _loaded = first_context.resolve(
            "scene_declarations", lambda: first_calls.append(1) or ["first"]
        )
        second, _loaded = second_context.resolve(
            "scene_declarations", lambda: second_calls.append(1) or ["second"]
        )
        other, _loaded = first_context.resolve("other_fact", lambda: {"value": 1})

        self.assertEqual(first, ["first"])
        self.assertEqual(second, ["second"])
        self.assertEqual(other, {"value": 1})
        self.assertEqual(first_calls, [1])
        self.assertEqual(second_calls, [1])
        self.assertEqual(first_context.loaded_keys(), ("scene_declarations", "other_fact"))
        self.assertEqual(second_context.loaded_keys(), ("scene_declarations",))

    def test_loader_failure_is_not_cached(self):
        module = _load_context()
        context = module.SystemInitRequestContext(_env())
        calls = []

        def fail():
            calls.append("fail")
            raise RuntimeError("load failed")

        with self.assertRaisesRegex(RuntimeError, "load failed"):
            context.resolve("scene_declarations", fail)
        self.assertIsNone(context.fact("scene_declarations"))

        value, loaded = context.resolve("scene_declarations", lambda: {"ok": True})
        self.assertTrue(loaded)
        self.assertEqual(value, {"ok": True})
        self.assertEqual(calls, ["fail"])

    def test_concurrent_contexts_never_share_a_fact(self):
        module = _load_context()
        barrier = threading.Barrier(8)

        def run(user_id):
            context = module.SystemInitRequestContext(_env(user_id=user_id))
            calls = []

            def load():
                calls.append(user_id)
                barrier.wait(timeout=5)
                return {"owner": user_id}

            first, _ = context.resolve("scene_declarations", load)
            second, _ = context.resolve("scene_declarations", load)
            return first, second, calls

        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(run, range(1, 9)))

        for user_id, (first, second, calls) in enumerate(results, start=1):
            self.assertIs(first, second)
            self.assertEqual(first, {"owner": user_id})
            self.assertEqual(calls, [user_id])

    def test_empty_key_is_rejected(self):
        module = _load_context()
        context = module.SystemInitRequestContext(_env())
        with self.assertRaisesRegex(ValueError, "fact key"):
            context.resolve(" ", lambda: {})

    def test_request_identity_records_role_scope_and_product(self):
        module = _load_context()
        context = module.SystemInitRequestContext(
            _env(user_id=9, company_id=4, database="tenant_db"),
            request_identity={
                "product_key": "construction.standard",
                "base_product_key": "construction",
                "edition_key": "standard",
            },
        )
        self.assertEqual(
            context.identity,
            {
                "database": "tenant_db",
                "user_id": 9,
                "company_id": 4,
                "product_key": "construction.standard",
                "base_product_key": "construction",
                "edition_key": "standard",
            },
        )


if __name__ == "__main__":
    unittest.main()
