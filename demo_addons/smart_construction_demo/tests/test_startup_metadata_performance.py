"""Demo finance startup equivalence belongs to the demo-owned actor fixture."""
import re
from unittest.mock import patch
from odoo.tests.common import TransactionCase, tagged
from odoo.addons.smart_core.handlers import system_init
from odoo.addons.smart_core.delivery.menu_service import MenuService


UPDATED_AT_CLOCK_PATTERN = re.compile(r"^[0-2][0-9]:[0-5][0-9]$")


def _without_updated_at(value):
    """Drop every ``updated_at`` value and collect it for a shape assertion.

    ``workspace_home.hero.updated_at`` is built from ``fields.Datetime.now()``
    formatted as ``HH:MM``, so two calls that straddle a minute boundary differ
    by construction.  The stamp is asserted by shape instead of by equality;
    the rest of the payload keeps strict structural equality.
    """
    stamps = []
    if isinstance(value, dict):
        scrubbed = {}
        for key, item in value.items():
            if key == "updated_at":
                stamps.append(item)
                continue
            child, child_stamps = _without_updated_at(item)
            scrubbed[key] = child
            stamps.extend(child_stamps)
        return scrubbed, stamps
    if isinstance(value, list):
        scrubbed = []
        for item in value:
            child, child_stamps = _without_updated_at(item)
            scrubbed.append(child)
            stamps.extend(child_stamps)
        return scrubbed, stamps
    return value, stamps


@tagged('post_install', '-at_install', 'sc_gate')
class TestStartupMetadataPerformance(TransactionCase):
    def _assert_payload_matches(self, previous_data, current_data):
        previous_scrubbed, previous_stamps = _without_updated_at(previous_data)
        current_scrubbed, current_stamps = _without_updated_at(current_data)
        self.assertEqual(current_scrubbed, previous_scrubbed)
        self.assertTrue(previous_stamps, "payload lost its updated_at stamps")
        self.assertEqual(len(previous_stamps), len(current_stamps))
        for stamp in previous_stamps + current_stamps:
            self.assertRegex(stamp, UPDATED_AT_CLOCK_PATTERN)

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
        self._assert_payload_matches(previous.data, current.data)
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
        self._assert_payload_matches(previous.data, current.data)
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
        self._assert_payload_matches(previous.data, current.data)
        self.assertLess(self.env.cr.sql_log_count - before, previous_queries)
