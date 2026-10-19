# -*- coding: utf-8 -*-
"""Regression guards for the concurrent app.menu.config first-insert path.

Two concurrent ``system.init`` requests can both miss the menu cache and build
the same projection. Without an ordering point the loser's INSERT races the
unique dimension key and turns a cache miss into a 500.
"""

from __future__ import annotations

import importlib.util
import inspect
import sys
import types
import unittest
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "app_config_engine"
    / "models"
    / "app_nav_config.py"
)


def _install_module(name: str, **attrs):
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


def _load_module():
    for name in list(sys.modules):
        if name == "odoo" or name.startswith("odoo.") or name == "psycopg2":
            sys.modules.pop(name, None)

    fields_mod = types.SimpleNamespace(
        Char=lambda *args, **kwargs: None,
        Selection=lambda *args, **kwargs: None,
        Many2one=lambda *args, **kwargs: None,
        Integer=lambda *args, **kwargs: None,
        Datetime=lambda *args, **kwargs: None,
        Boolean=lambda *args, **kwargs: None,
        Json=lambda *args, **kwargs: None,
    )
    api_mod = types.SimpleNamespace(model=lambda fn: fn)
    _install_module(
        "odoo",
        models=types.SimpleNamespace(Model=object),
        fields=fields_mod,
        api=api_mod,
        _=lambda value: value,
    )
    _install_module("odoo.tools")
    _install_module("odoo.tools.safe_eval", safe_eval=lambda value: value)
    _install_module("psycopg2", IntegrityError=type("IntegrityError", (Exception,), {}))

    spec = importlib.util.spec_from_file_location("app_nav_config_under_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class _Env:
    def __init__(self, dbname="sc_demo", company_id=7, lang="zh_CN"):
        self.cr = types.SimpleNamespace(dbname=dbname)
        self.company = types.SimpleNamespace(id=company_id)
        self.lang = lang


class TestAppMenuConfigInsertLock(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = _load_module()
        cls.model_cls = cls.module.AppMenuConfig

    def _lock_key(self, *, model_name=None, scene="web", env=None):
        instance = self.model_cls.__new__(self.model_cls)
        instance.env = env or _Env()
        return instance._menu_config_lock_key(model_name=model_name, scene=scene)

    def test_lock_key_is_stable_per_cache_dimension(self):
        first = self._lock_key(model_name=None, scene="web")
        second = self._lock_key(model_name=None, scene="WEB")
        self.assertEqual(first, second)

    def test_lock_key_separates_every_unique_dimension(self):
        base = self._lock_key(model_name=None, scene="web")
        variants = (
            self._lock_key(model_name="project.task", scene="web"),
            self._lock_key(model_name=None, scene="mobile"),
            self._lock_key(model_name=None, scene="web", env=_Env(company_id=8)),
            self._lock_key(model_name=None, scene="web", env=_Env(lang="en_US")),
            self._lock_key(model_name=None, scene="web", env=_Env(dbname="sc_platform_control")),
        )
        self.assertEqual(len({base, *variants}), 1 + len(variants))

    def test_advisory_lock_precedes_insert_and_fallback_reads_committed_row(self):
        source = inspect.getsource(self.model_cls._generate_from_menus)
        lock_index = source.index("pg_advisory_xact_lock")
        create_index = source.index("create(vals)")
        self.assertLess(lock_index, create_index)

        fallback = source.split("except IntegrityError:", 1)[1]
        fetch_index = fallback.index("self.env.cr.fetchone()")
        self.assertIn("SELECT id FROM app_menu_config", fallback[:fetch_index])
        self.assertNotIn("search(", fallback[:fetch_index])


if __name__ == "__main__":
    unittest.main()
