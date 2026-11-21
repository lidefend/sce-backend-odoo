from __future__ import annotations

import os
import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import patch

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
        cls.addClassCleanup(cls.admin.close)
        cls.addClassCleanup(cls.admin_cursor.close)

    def setUp(self):
        super().setUp()
        suffix = uuid.uuid4().hex[:10]
        self.database_a = "sc_test_arch_a_%s" % suffix
        self.database_b = "sc_test_arch_b_%s" % suffix
        self.addCleanup(self._drop_databases)
        for database in (self.database_a, self.database_b):
            self.admin_cursor.execute(
                sql.SQL("CREATE DATABASE {} TEMPLATE {}").format(
                    sql.Identifier(database), sql.Identifier(self.template_database),
                )
            )

    def _drop_databases(self):
        for database in (self.database_b, self.database_a):
            Registry.delete(database)
            self.admin_cursor.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s",
                [database],
            )
            self.admin_cursor.execute(
                sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(database))
            )
            self.admin_cursor.execute(
                "SELECT COUNT(*) FROM pg_database WHERE datname = %s", [database],
            )
            self.assertEqual(self.admin_cursor.fetchone()[0], 0)

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

    def _assert_login_works(self, database):
        from odoo import http
        from odoo.addons.smart_core.core.intent_router import resolve_handler
        from odoo.addons.smart_core.handlers import login as login_module
        from odoo.addons.smart_core.security import auth
        from .entry_namespace_test_support import configure_test_entry_namespace

        with Registry(database).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            headers = configure_test_entry_namespace(
                env, alias="lifecycle-entry", audience="tenant", duty_key="ci_suite",
            )
            secret = uuid.uuid4().hex
            user = env.ref("base.user_admin")
            user.with_context(no_reset_password=True).write({"password": secret})
            env["ir.config_parameter"].sudo().set_param("sc.jwt.secret", uuid.uuid4().hex)
            cr.commit()  # Native password authentication opens its own cursor.
            request = SimpleNamespace(
                env=env, session=SimpleNamespace(db=database),
                httprequest=SimpleNamespace(headers=headers, environ={}, remote_addr="127.0.0.1"),
            )
            handler = resolve_handler("login", env)
            self.assertIs(handler, login_module.LoginHandler)
            # Supply transport context only; authentication, namespace lookup,
            # handler resolution and token creation all use their real paths.
            with patch.object(http, "request", request), patch.object(auth, "request", request), \
                    patch.object(login_module, "request", request):
                result = handler(env, payload={"params": {"login": user.login, "password": secret}}).handle()
            self.assertIsInstance(result, tuple, result)
            data, metadata = result
            self.assertEqual(data["user"]["id"], user.id)
            self.assertTrue(data["session"]["token"])
            self.assertEqual(data["session"]["db"], database)
            self.assertEqual(metadata["source_kind"], login_module.LoginHandler.SOURCE_KIND)

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
        self._apply_module_lifecycle(self.database_a, "smart_construction_core", "install")
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
        self._set_config(self.database_b, "")
        with Registry(self.database_b).cursor() as cr:
            forged = api.Environment(cr, SUPERUSER_ID, {CONFIG_KEY: "smart_owner_core"})
            self.assertNotIn("owner.projects.list", extension_runtime_context(forged).handlers)
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

        self._apply_module_lifecycle(self.database_b, "smart_owner_bundle", "install")
        self._set_config(self.database_b, "smart_owner_core,smart_owner_bundle")
        self._apply_module_lifecycle(self.database_b, "smart_owner_bundle", "uninstall")
        self.assertEqual(self._configured_context(self.database_b)[0], ("smart_owner_core",))
        self.assertIn("owner.projects.list", self._configured_context(self.database_b)[1])
        self._apply_module_lifecycle(
            self.database_b,
            "smart_owner_core",
            "uninstall",
        )
        self.assertEqual(
            self._module_state(self.database_b, "smart_owner_core"),
            "uninstalled",
        )
        natural_modules, natural_handlers = self._configured_context(self.database_b)
        self.assertEqual(natural_modules, ())
        self.assertNotIn("owner.projects.list", natural_handlers)
        self._assert_login_works(self.database_b)
        # Deliberately corrupted configuration is distinct from native removal.
        with self.assertRaises(ExtensionConfigurationError):
            self._context(self.database_b, "smart_owner_core")

    def _configured_context(self, database):
        with Registry(database).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            context = extension_runtime_context(env)
            return context.modules, dict(context.handlers)

    def test_construction_install_upgrade_transition_is_loader_safe(self):
        # Clone a smart_core-only template: test actual defaults, not a repaired
        # config on an already-installed full product.
        modules, handlers = self._configured_context(self.database_a)
        self.assertNotIn("project.dashboard", handlers)
        for name in ("smart_construction_core", "smart_construction_scene",
                     "smart_construction_portal", "smart_construction_bundle"):
            self.assertEqual(self._module_state(self.database_a, name), "uninstalled")
        self._apply_module_lifecycle(self.database_a, "smart_construction_core", "install")
        modules, handlers = self._configured_context(self.database_a)
        self.assertEqual(modules, ("smart_construction_core",))
        self.assertIn("project.dashboard", handlers)
        self.assertEqual(self._module_state(self.database_a, "smart_construction_scene"), "uninstalled")
        self._apply_module_lifecycle(self.database_a, "smart_construction_core", "upgrade")
        self.assertIn("project.dashboard", self._configured_context(self.database_a)[1])

        self._apply_module_lifecycle(self.database_a, "smart_construction_bundle", "install")
        modules, handlers = self._configured_context(self.database_a)
        self.assertIn("smart_construction_scene", modules)
        self.assertIn("smart_construction_bundle", modules)
        self.assertIn("project.dashboard", handlers)
        for name in ("smart_construction_core", "smart_construction_scene"):
            before = Registry(self.database_a)
            self._apply_module_lifecycle(self.database_a, name, "upgrade")
            self.assertIsNot(before, Registry(self.database_a))
            self.assertEqual(self._configured_context(self.database_a), (modules, handlers))
        reversed_modules, reversed_handlers = self._context(self.database_a, ",".join(reversed(modules)))
        self.assertEqual((reversed_modules, reversed_handlers), (modules, handlers))

        # Native uninstall removes only the departing module's registration.
        self._apply_module_lifecycle(self.database_a, "smart_construction_bundle", "uninstall")
        self.assertEqual(self._module_state(self.database_a, "smart_construction_bundle"), "uninstalled")
        remaining_modules, remaining_handlers = self._configured_context(self.database_a)
        self.assertEqual(set(remaining_modules), set(modules) - {"smart_construction_bundle"})
        for name in remaining_modules:
            self.assertEqual(self._module_state(self.database_a, name), "installed")
        self.assertIn("project.dashboard", remaining_handlers)
        self._assert_login_works(self.database_a)
        with self.assertRaises(ExtensionConfigurationError):
            self._context(self.database_a, ",".join(modules))
