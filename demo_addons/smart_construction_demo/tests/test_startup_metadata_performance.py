"""Demo finance startup equivalence belongs to the demo-owned actor fixture."""
from unittest.mock import patch
from odoo.tests.common import TransactionCase, tagged
from odoo.addons.smart_core.handlers import system_init
from odoo.addons.smart_core.delivery.menu_service import MenuService


@tagged('post_install', '-at_install', 'sc_gate')
class TestStartupMetadataPerformance(TransactionCase):
    def test_registry_startup_batch_preserves_full_response_and_reduces_sql(self):
        finance = self.env.ref('smart_construction_demo.user_demo_role_finance')
        actor = self.env(user=finance.id, context={'allowed_company_ids': [finance.company_id.id], 'lang': 'zh_CN'})
        self.assertFalse(actor.su)
        params = {'scene': 'web', 'scene_ready_mode': 'registry', 'with_preload': False, 'with': ['workspace_home']}
        warm = system_init.SystemInitHandler(env=actor).handle(payload={'params': params})
        self.assertTrue(warm.ok)
        with patch.object(MenuService, '_action_xmlids_from_facts', return_value={}):
            before = self.env.cr.sql_log_count
            previous = system_init.SystemInitHandler(env=actor).handle(payload={'params': params})
            previous_queries = self.env.cr.sql_log_count - before
        before = self.env.cr.sql_log_count
        current = system_init.SystemInitHandler(env=actor).handle(payload={'params': params})
        current_queries = self.env.cr.sql_log_count - before
        self.assertTrue(previous.ok)
        self.assertTrue(current.ok)
        self.assertEqual(current.data, previous.data)
        self.assertLess(current_queries, previous_queries)

    def test_registry_startup_path_batch_preserves_response_and_reduces_sql(self):
        finance = self.env.ref('smart_construction_demo.user_demo_role_finance')
        actor = self.env(user=finance.id, context={'allowed_company_ids': [finance.company_id.id], 'lang': 'zh_CN'})
        self.assertFalse(actor.su)
        params = {'scene': 'web', 'scene_ready_mode': 'registry', 'with_preload': False, 'with': ['workspace_home']}
        self.assertTrue(system_init.SystemInitHandler(env=actor).handle(payload={'params': params}).ok)
        with patch.object(MenuService, '_native_visible_menu_paths', return_value={}):
            before = self.env.cr.sql_log_count
            previous = system_init.SystemInitHandler(env=actor).handle(payload={'params': params})
            previous_queries = self.env.cr.sql_log_count - before
        before = self.env.cr.sql_log_count
        current = system_init.SystemInitHandler(env=actor).handle(payload={'params': params})
        self.assertTrue(previous.ok)
        self.assertTrue(current.ok)
        self.assertEqual(current.data, previous.data)
        self.assertLess(self.env.cr.sql_log_count - before, previous_queries)

    def test_registry_startup_scene_batch_preserves_response_and_reduces_sql(self):
        from odoo.addons.smart_core.governance import scene_normalizer
        finance = self.env.ref('smart_construction_demo.user_demo_role_finance')
        actor = self.env(user=finance.id, context={'allowed_company_ids': [finance.company_id.id], 'lang': 'zh_CN'})
        self.assertFalse(actor.su)
        params = {'scene': 'web', 'scene_ready_mode': 'registry', 'with_preload': False, 'with': ['workspace_home']}
        self.assertTrue(system_init.SystemInitHandler(env=actor).handle(payload={'params': params}).ok)
        with patch.object(scene_normalizer, '_resolve_xmlids_batch', return_value={}):
            before = self.env.cr.sql_log_count
            previous = system_init.SystemInitHandler(env=actor).handle(payload={'params': params})
            previous_queries = self.env.cr.sql_log_count - before
        before = self.env.cr.sql_log_count
        current = system_init.SystemInitHandler(env=actor).handle(payload={'params': params})
        self.assertTrue(previous.ok)
        self.assertTrue(current.ok)
        self.assertEqual(current.data, previous.data)
        self.assertLess(self.env.cr.sql_log_count - before, previous_queries)
