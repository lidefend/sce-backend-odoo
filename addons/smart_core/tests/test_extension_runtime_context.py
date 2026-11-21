from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_core.core.extension_loader import (
    ExtensionConfigurationError,
    clear_extension_runtime_context,
    extension_runtime_context,
    handlers_for_env,
)
from odoo.addons.smart_core.core.handler_registry import base_handlers


@tagged("post_install", "-at_install", "sc_gate", "extension_runtime_context")
class TestExtensionRuntimeContext(TransactionCase):
    def setUp(self):
        super().setUp()
        self.params = self.env["ir.config_parameter"].sudo()
        self.key = "sc.core.extension_modules"
        self.original = self.params.get_param(self.key, "")
        clear_extension_runtime_context(self.env)

    def tearDown(self):
        self.params.set_param(self.key, self.original)
        clear_extension_runtime_context(self.env)
        super().tearDown()

    def test_missing_configured_module_fails_with_diagnostic(self):
        self.params.set_param(self.key, "smart_core,arch_close_missing_extension")
        with self.assertRaises(ExtensionConfigurationError) as caught:
            extension_runtime_context(self.env)
        diagnostic = caught.exception.to_diagnostic()
        self.assertEqual(diagnostic["code"], "EXTENSION_CONFIGURATION_INVALID")
        self.assertIn("arch_close_missing_extension", diagnostic["missing"])

    def test_installed_module_without_enablement_is_not_in_context(self):
        self.params.set_param(self.key, "")
        context = extension_runtime_context(self.env)
        self.assertEqual(context.modules, ())
        self.assertGreater(len(context.handlers), 0)
        self.assertIn("login", context.handlers)
        self.assertIn("auth.login", context.handlers)
        self.assertIn("auth.logout", context.handlers)

    def test_request_context_cannot_expand_enablement(self):
        self.params.set_param(self.key, "")
        context = extension_runtime_context(
            self.env(context={"sc.core.extension_modules": "base"})
        )
        self.assertEqual(context.modules, ())

    def test_same_registry_rebuilds_when_configuration_changes(self):
        self.params.set_param(self.key, "")
        first = extension_runtime_context(self.env)
        self.params.set_param(self.key, "base")
        second = extension_runtime_context(self.env)
        self.assertIsNot(first, second)
        self.assertEqual(second.config_modules, ("base",))
        self.assertIs(second, extension_runtime_context(self.env))

    def test_module_order_does_not_change_handler_catalog(self):
        installed = ("base", "smart_core")
        self.params.set_param(self.key, ",".join(installed))
        forward = extension_runtime_context(self.env)
        self.params.set_param(self.key, ",".join(reversed(installed)))
        reverse = extension_runtime_context(self.env)
        self.assertEqual(forward.modules, reverse.modules)
        self.assertEqual(dict(forward.handlers), dict(reverse.handlers))

    def test_runtime_handler_mapping_cannot_mutate_registry_context(self):
        self.params.set_param(self.key, "")
        handlers = handlers_for_env(self.env)
        self.assertEqual(set(handlers), set(base_handlers()))
        with self.assertRaises(TypeError):
            handlers["arch_close_injected"] = object
