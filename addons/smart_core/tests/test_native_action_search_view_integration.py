from __future__ import annotations

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_core.app_config_engine.services.dispatchers.action_dispatcher import ActionDispatcher
from odoo.addons.smart_core.app_config_engine.services.assemblers.page_assembler import PageAssembler


@tagged("post_install", "-at_install", "smart_core", "native_action_search_view")
class TestNativeActionSearchViewIntegration(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tree = cls.env["ir.ui.view"].create({
            "name": "P0-2 native action tree",
            "model": "res.partner",
            "type": "tree",
            "arch": '<tree><field name="name"/></tree>',
        })
        cls.search_a = cls.env["ir.ui.view"].create({
            "name": "P0-2 native action search A",
            "model": "res.partner",
            "type": "search",
            "arch": (
                '<search><field name="name"/>'
                '<filter name="filter_alpha" string="Alpha" '
                'domain="[(\'name\',\'ilike\',\'alpha\')]"/>'
                '<filter name="filter_system" string="System" '
                'groups="base.group_system" '
                'domain="[(\'name\',\'ilike\',\'system\')]"/></search>'
            ),
        })
        cls.search_b = cls.env["ir.ui.view"].create({
            "name": "P0-2 native action search B",
            "model": "res.partner",
            "type": "search",
            "arch": (
                '<search><field name="email"/>'
                '<filter name="filter_beta" string="Beta" '
                'domain="[(\'email\',\'ilike\',\'beta\')]"/></search>'
            ),
        })
        cls.env["ir.model.data"].create([
            {
                "module": "smart_core",
                "name": "p0_2_search_alpha",
                "model": "ir.ui.view",
                "res_id": cls.search_a.id,
            },
            {
                "module": "smart_core",
                "name": "p0_2_search_beta",
                "model": "ir.ui.view",
                "res_id": cls.search_b.id,
            },
        ])
        cls.action_a = cls._create_action("P0-2 Action A", cls.search_a)
        cls.action_b = cls._create_action("P0-2 Action B", cls.search_b)

    @classmethod
    def _create_action(cls, name, search_view):
        return cls.env["ir.actions.act_window"].create({
            "name": name,
            "res_model": "res.partner",
            "view_mode": "tree,form",
            "view_id": cls.tree.id,
            "search_view_id": search_view.id if search_view else False,
        })

    def _dispatch(self, action, env=None):
        source, _versions = ActionDispatcher(
            env or self.env,
            (env or self.env)["ir.model"].sudo().env,
        ).dispatch({
            "subject": "action",
            "action_id": action.id,
            "view_type": "tree",
        })
        return source

    def _dispatch_without_action(self):
        source, _versions = ActionDispatcher(
            self.env,
            self.env["ir.model"].sudo().env,
        ).dispatch({
            "subject": "model",
            "model": "res.partner",
            "view_type": "tree",
        })
        return source

    @staticmethod
    def _filter_keys(source):
        return {
            row.get("key")
            for row in (source.get("search") or {}).get("filters") or []
            if isinstance(row, dict) and row.get("key")
        }

    def test_action_bound_search_view_identity_and_filters(self):
        source = self._dispatch(self.action_a)
        identity = source["search"]["nativeIdentity"]

        self.assertEqual(identity["model"], "res.partner")
        self.assertEqual(identity["actionId"], self.action_a.id)
        self.assertEqual(identity["viewId"], self.search_a.id)
        self.assertEqual(identity["viewXmlId"], "smart_core.p0_2_search_alpha")
        self.assertEqual(identity["authority"], "action_search_view")
        self.assertIn("filter_alpha", self._filter_keys(source))
        self.assertNotIn("filter_beta", self._filter_keys(source))
        self.assertEqual(
            source["action_identity"]["search_view_xmlid"],
            "smart_core.p0_2_search_alpha",
        )

    def test_page_assembler_accepts_odoo_many2one_action_dict(self):
        page, _versions = PageAssembler(
            self.env,
            self.env["ir.model"].sudo().env,
        ).assemble_page_contract(
            {
                "model": "res.partner",
                "view_types": ["tree"],
                "action_id": self.action_a.id,
            },
            action=self.action_a.read()[0],
        )

        self.assertIsInstance(self.action_a.read()[0]["search_view_id"], tuple)
        self.assertEqual(
            page["search"]["nativeIdentity"]["viewId"],
            self.search_a.id,
        )

    def test_actions_on_same_model_keep_distinct_search_views(self):
        source_a = self._dispatch(self.action_a)
        source_b = self._dispatch(self.action_b)
        source_a_again = self._dispatch(self.action_a)

        self.assertEqual(
            source_a["search"]["nativeIdentity"]["viewId"],
            self.search_a.id,
        )
        self.assertEqual(
            source_b["search"]["nativeIdentity"]["viewId"],
            self.search_b.id,
        )
        self.assertEqual(
            source_a_again["search"]["nativeIdentity"]["viewId"],
            self.search_a.id,
        )
        self.assertIn("filter_alpha", self._filter_keys(source_a))
        self.assertIn("filter_beta", self._filter_keys(source_b))
        self.assertNotIn("filter_beta", self._filter_keys(source_a_again))

    def test_action_without_search_binding_marks_model_default_identity(self):
        source = self._dispatch_without_action()
        identity = source["search"]["nativeIdentity"]

        self.assertIsNone(identity["actionId"])
        self.assertGreater(identity["viewId"], 0)
        self.assertEqual(identity["authority"], "model_default_search_view")
        self.assertEqual(identity["sourceLocator"], "ir.ui.view:search")

    def test_invalid_action_search_view_does_not_fallback_to_model_default(self):
        other_search = self.env["ir.ui.view"].create({
            "name": "P0-2 invalid search model",
            "model": "res.users",
            "type": "search",
            "arch": '<search><field name="name"/></search>',
        })
        action = self._create_action("P0-2 invalid search action", other_search)

        with self.assertRaisesRegex(ValueError, "ACTION_SEARCH_VIEW"):
            self._dispatch(action)

    def test_action_search_projection_is_not_written_to_model_cache(self):
        before = self.env["app.search.config"].sudo().search_count([
            ("model", "=", "res.partner"),
        ])

        source = self._dispatch(self.action_a)

        after = self.env["app.search.config"].sudo().search_count([
            ("model", "=", "res.partner"),
        ])
        self.assertEqual(after, before)
        self.assertEqual(
            source["search"]["nativeIdentity"]["viewId"],
            self.search_a.id,
        )

    def test_action_search_filters_are_trimmed_by_the_runtime_user(self):
        self.assertIn("filter_system", self._filter_keys(self._dispatch(self.action_a)))
        restricted = self.env["res.users"].create({
            "name": "P0-2 restricted search user",
            "login": "p0-2-restricted-search@example.invalid",
            "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
        })

        source = self._dispatch(self.action_a, env=self.env(user=restricted))

        self.assertEqual(
            source["search"]["nativeIdentity"]["viewId"],
            self.search_a.id,
        )
        self.assertIn("filter_alpha", self._filter_keys(source))
        self.assertNotIn("filter_system", self._filter_keys(source))
