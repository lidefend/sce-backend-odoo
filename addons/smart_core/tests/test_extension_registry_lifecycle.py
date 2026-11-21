from __future__ import annotations

import os
import unittest
import uuid

import psycopg2
from psycopg2 import sql

from odoo import SUPERUSER_ID, api
from odoo.modules.registry import Registry
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_core.core.extension_loader import (
    ExtensionConfigurationError,
    extension_runtime_context,
)


CONFIG_KEY = "sc.core.extension_modules"


@tagged("post_install", "-at_install", "sc_gate", "extension_lifecycle")
class TestExtensionRegistryLifecycle(TransactionCase):
    @classmethod
    def setUpClass(cls):
        if os.environ.get("SC_EXTENSION_LIFECYCLE_MATRIX") != "1":
            raise unittest.SkipTest("extension lifecycle matrix is opt-in")
        super().setUpClass()
        cls.template_database = str(
            os.environ.get("SC_EXTENSION_TEMPLATE_DB") or ""
        ).strip()
        if not cls.template_database.startswith("sc_test_template__"):
            raise ValueError("registered local.test template identity is required")
        params = {
            "dbname": "postgres",
            "host": os.environ.get("DB_HOST") or "db",
            "port": os.environ.get("DB_PORT") or "5432",
            "user": os.environ.get("DB_USER") or "",
            "password": os.environ.get("DB_PASSWORD") or "",
        }
        if not params["user"] or not params["password"]:
            raise ValueError("registered test database credentials are unavailable")
        cls.admin = psycopg2.connect(**params)
        cls.admin.autocommit = True
        cls.admin_cursor = cls.admin.cursor()
        suffix = uuid.uuid4().hex[:10]
        cls.database_a = "sc_test_arch_a_%s" % suffix
        cls.database_b = "sc_test_arch_b_%s" % suffix
        cls.addClassCleanup(cls._drop_databases)
        for database in (cls.database_a, cls.database_b):
            cls.admin_cursor.execute(
                sql.SQL("CREATE DATABASE {} TEMPLATE {}").format(
                    sql.Identifier(database),
                    sql.Identifier(cls.template_database),
                )
            )

    @classmethod
    def _drop_databases(cls):
        for database in (cls.database_b, cls.database_a):
            cls.admin_cursor.execute(
                "SELECT pg_terminate_backend(pid) "
                "FROM pg_stat_activity WHERE datname = %s",
                [database],
            )
            cls.admin_cursor.execute(
                sql.SQL("DROP DATABASE IF EXISTS {}").format(
                    sql.Identifier(database)
                )
            )
            cls.admin_cursor.execute(
                "SELECT COUNT(*) FROM pg_database WHERE datname = %s",
                [database],
            )
            if cls.admin_cursor.fetchone()[0] != 0:
                raise AssertionError("temporary registry database was not removed")
        cls.admin_cursor.close()
        cls.admin.close()

    def _set_config(self, database, value):
        registry = Registry(database)
        with registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            env["ir.config_parameter"].sudo().set_param(CONFIG_KEY, value)
            cr.commit()

    def _context(self, database, configured):
        self._set_config(database, configured)
        registry = Registry(database)
        with registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            context = extension_runtime_context(env)
            return context.modules, dict(context.handlers)

    def _apply_module_lifecycle(self, database, module_name, action):
        registry = Registry(database)
        cr = registry.cursor()
        try:
            env = api.Environment(cr, SUPERUSER_ID, {})
            module = env["ir.module.module"].sudo().search(
                [("name", "=", module_name)],
                limit=1,
            )
            self.assertTrue(module, module_name)
            button = getattr(module, "button_%s" % action)
            button()
            cr.commit()
        finally:
            try:
                cr.close()
            except (psycopg2.InterfaceError, psycopg2.ProgrammingError):
                pass
        Registry.new(database, update_module=True)

    def _module_state(self, database, module_name):
        registry = Registry(database)
        with registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            module = env["ir.module.module"].sudo().search(
                [("name", "=", module_name)],
                limit=1,
            )
            return module.state

    def test_registry_isolation_and_native_module_lifecycle(self):
        construction_modules, construction_handlers = self._context(
            self.database_a,
            "smart_construction_core",
        )
        empty_modules, empty_handlers = self._context(self.database_b, "")

        self.assertEqual(construction_modules, ("smart_construction_core",))
        self.assertIn("project.dashboard", construction_handlers)
        self.assertEqual(empty_modules, ())
        self.assertNotIn("project.dashboard", empty_handlers)

        with self.assertRaises(ExtensionConfigurationError):
            self._context(self.database_b, "smart_owner_core")

        self._apply_module_lifecycle(
            self.database_b,
            "smart_owner_core",
            "install",
        )
        self.assertEqual(
            self._module_state(self.database_b, "smart_owner_core"),
            "installed",
        )
        owner_modules, owner_handlers = self._context(
            self.database_b,
            "smart_owner_core",
        )
        self.assertEqual(owner_modules, ("smart_owner_core",))
        self.assertIn("owner.projects.list", owner_handlers)
        self.assertNotIn("project.dashboard", owner_handlers)

        # Returning to DB-A proves the first Registry still owns its independent
        # construction extension state after DB-B has loaded another module set.
        repeated_modules, repeated_handlers = self._context(
            self.database_a,
            "smart_construction_core",
        )
        self.assertEqual(repeated_modules, construction_modules)
        self.assertIn("project.dashboard", repeated_handlers)
        self.assertNotIn("owner.projects.list", repeated_handlers)

        # A same-Registry enablement change rebuilds its extension context.
        empty_again_modules, empty_again_handlers = self._context(
            self.database_a,
            "",
        )
        self.assertEqual(empty_again_modules, ())
        self.assertNotIn("project.dashboard", empty_again_handlers)

        self._apply_module_lifecycle(
            self.database_b,
            "smart_owner_core",
            "upgrade",
        )
        self.assertEqual(
            self._module_state(self.database_b, "smart_owner_core"),
            "installed",
        )
        upgraded_modules, upgraded_handlers = self._context(
            self.database_b,
            "smart_owner_core",
        )
        self.assertEqual(upgraded_modules, ("smart_owner_core",))
        self.assertIn("owner.projects.list", upgraded_handlers)

        self._apply_module_lifecycle(
            self.database_b,
            "smart_owner_core",
            "uninstall",
        )
        self.assertEqual(
            self._module_state(self.database_b, "smart_owner_core"),
            "uninstalled",
        )
        with self.assertRaises(ExtensionConfigurationError):
            self._context(self.database_b, "smart_owner_core")
