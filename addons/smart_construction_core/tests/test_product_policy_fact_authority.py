"""Maintained native catalog facts; source files are initialization inputs only."""
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch

from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase, tagged
from odoo.addons.smart_core.delivery.edition_release_snapshot_service import EditionReleaseSnapshotService
from odoo.addons.smart_construction_core.models.support import product_policy_sync


@tagged('post_install', '-at_install', 'sc_gate', 'product_policy_fact_authority')
class TestProductPolicyFactAuthority(TransactionCase):
    def setUp(self):
        super().setUp()
        self.menu = self.env.ref('smart_construction_core.menu_sc_product_scenario_business_config')
        self.policy = self.env['sc.product.policy'].create({
            'product_key': 'construction.fact_test', 'base_product_key': 'construction',
            'edition_key': 'fact_test', 'label': 'Maintained catalog test', 'state': 'stable',
            'menu_groups': [{'group_key': 'configuration', 'group_label': 'Configuration', 'menus': []}],
        })
        self.env['ir.config_parameter'].sudo().set_param('smart_core.release_operator.catalog_source_db', self.env.cr.dbname)
        self.service = EditionReleaseSnapshotService(self.env)

    def _maintain(self):
        self.policy.set_native_menu_publication(self.menu.id, 'configuration', 'released')
        return self.service.build_policy_draft_contract(product_key=self.policy.product_key)

    def test_existing_archived_empty_policy_does_not_read_seed(self):
        self.policy.write({'active': False, 'menu_groups': []})
        with patch.object(product_policy_sync, 'load_locked_menu_policy_contract', side_effect=AssertionError('seed read')):
            result = self.env['sc.product.policy'].synchronize_locked_formal_menu_policy(self.policy.product_key)
        self.assertEqual(result['policy'], self.policy)
        self.assertFalse(result['changed'])
        self.assertFalse(self.policy.active)
        self.assertFalse(self.policy.menu_groups)

    def test_native_entry_can_be_maintained_without_file_membership(self):
        snapshots_before = self.env['sc.edition.release.snapshot'].search_count([])
        draft = self._maintain()
        self.assertEqual(draft['blocking_issue_count'], 0, draft['preflight_checks'])
        self.assertEqual(draft['pages'][0]['menu_xmlid'], self.menu.get_external_id()[self.menu.id])
        self.assertEqual(draft['pages'][0]['res_model'], 'sc.product.scenario')
        self.assertEqual(self.env['sc.edition.release.snapshot'].search_count([]), snapshots_before)
        self.policy.set_native_menu_publication(self.menu.id, 'configuration', 'preview')
        self.assertEqual(len(self.policy.menu_groups[0]['menus']), 1)

    def test_invalid_group_does_not_mutate_policy(self):
        before = deepcopy(self.policy.menu_groups)
        with self.assertRaises(ValidationError):
            self.policy.set_native_menu_publication(self.menu.id, 'unknown')
        self.assertEqual(self.policy.menu_groups, before)

    def test_business_role_does_not_acquire_product_publishing_rights(self):
        user = self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Business configuration only', 'login': 'fact_policy_role_test',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id,
                self.env.ref('smart_construction_core.group_sc_cap_business_config_admin').id])],
        })
        with self.assertRaises(AccessError):
            self.policy.with_user(user).set_native_menu_publication(self.menu.id, 'configuration', 'released')

    def test_runtime_consumes_published_catalog_until_next_publication(self):
        import hashlib
        import json
        from odoo.addons.smart_core.delivery.product_policy_service import ProductPolicyService
        self._maintain()
        self.env['ir.config_parameter'].sudo().set_param('smart_core.platform_release_db', self.env.cr.dbname)
        original = self.policy.to_runtime_dict()
        digest = hashlib.sha256(json.dumps(original, ensure_ascii=False, sort_keys=True, default=str,
                                          separators=(',', ':')).encode()).hexdigest()
        self.env['sc.edition.release.snapshot'].create({
            'product_key': self.policy.product_key, 'base_product_key': 'construction',
            'edition_key': 'fact_test', 'label': 'Published catalog', 'version': 'test',
            'state': 'released', 'is_active': True, 'source_policy_id': self.policy.id,
            'snapshot_json': {'policy_snapshot_schema': 'maintained_product_policy.v1',
                              'policy': original, 'policy_sha256': digest},
        })
        self.policy.set_native_menu_publication(self.menu.id, 'configuration', 'hidden')
        runtime = ProductPolicyService(self.env).get_policy(product_key=self.policy.product_key, enforce_release=True)
        self.assertEqual(runtime['menu_groups'], original['menu_groups'])
        draft = self.service.build_policy_draft_contract(product_key=self.policy.product_key)
        self.assertEqual(draft['page_count'], 0)

    def test_legacy_published_catalog_requires_explicit_refreeze_before_edit(self):
        self._maintain()
        self.env['sc.edition.release.snapshot'].create({
            'product_key': self.policy.product_key, 'base_product_key': 'construction',
            'edition_key': 'fact_test', 'label': 'Legacy catalog', 'version': 'test',
            'state': 'released', 'is_active': True, 'source_policy_id': self.policy.id,
            'snapshot_json': {'policy': {'product_key': self.policy.product_key}},
        })
        with self.assertRaisesRegex(ValidationError, 'Re-freeze'):
            self.policy.set_native_menu_publication(self.menu.id, 'configuration', 'hidden')

    def test_cross_database_legacy_publication_blocks_draft_edit(self):
        from contextlib import nullcontext
        from odoo.addons.smart_core.delivery import product_policy_service as module
        self._maintain()
        self.env['ir.config_parameter'].sudo().set_param('smart_core.platform_release_db', 'declared_test_release')
        record = SimpleNamespace(snapshot_json={'policy': {'product_key': self.policy.product_key}})
        model = SimpleNamespace(search=lambda *args, **kwargs: record)
        model.sudo = lambda: model
        remote = {'sc.edition.release.snapshot': model}
        with patch.object(module.ProductPolicyService, '_platform_policy_db', return_value='declared_test_release'), \
             patch.object(module, 'Registry', return_value=SimpleNamespace(cursor=lambda: nullcontext(object()))), \
             patch.object(module, 'api', SimpleNamespace(Environment=lambda *args: remote)):
            with self.assertRaisesRegex(ValidationError, 'LEGACY_PUBLISHED_POLICY_REQUIRES_REFREEZE'):
                self.policy.set_native_menu_publication(self.menu.id, 'configuration', 'hidden')
        self.assertEqual(self.policy.menu_groups[0]['menus'][0]['release_state'], 'released')

    def test_unknown_published_schema_never_falls_back_to_draft(self):
        from odoo.addons.smart_core.delivery.product_policy_service import ProductPolicyService
        self._maintain()
        self.env['ir.config_parameter'].sudo().set_param('smart_core.platform_release_db', self.env.cr.dbname)
        self.env['sc.edition.release.snapshot'].create({
            'product_key': self.policy.product_key, 'base_product_key': 'construction',
            'edition_key': 'fact_test', 'label': 'Unsupported catalog', 'version': 'test',
            'state': 'released', 'is_active': True, 'source_policy_id': self.policy.id,
            'snapshot_json': {'policy_snapshot_schema': 'future.or.corrupt'},
        })
        with self.assertRaisesRegex(ValueError, 'SCHEMA_UNSUPPORTED'):
            ProductPolicyService(self.env).get_policy(product_key=self.policy.product_key, enforce_release=True)

    def test_runtime_gate_rejects_corrupt_published_catalog_and_pages(self):
        import hashlib
        import json
        from odoo.addons.smart_core.handlers.system_init import _release_gate_page_contract_from_snapshot
        draft = self._maintain()
        original = self.policy.to_runtime_dict()
        frozen = {'policy_snapshot_schema': 'maintained_product_policy.v1', 'policy': original,
                  'policy_sha256': hashlib.sha256(json.dumps(original, ensure_ascii=False, sort_keys=True,
                                      default=str, separators=(',', ':')).encode()).hexdigest()}
        snapshot = {'product_key': self.policy.product_key, 'snapshot_json': frozen,
                    'meta_json': {'release_draft': deepcopy(draft)}}
        gate = _release_gate_page_contract_from_snapshot(snapshot)
        self.assertEqual(gate['menu_release_states'][self.menu.get_external_id()[self.menu.id]], 'released')
        snapshot['meta_json']['release_draft']['pages'][0]['res_model'] = 'res.partner'
        with self.assertRaisesRegex(ValueError, 'PAGES_FINGERPRINT_MISMATCH'):
            _release_gate_page_contract_from_snapshot(snapshot)
        frozen['policy']['label'] = 'tampered'
        with self.assertRaisesRegex(ValueError, 'POLICY_DIGEST_MISMATCH'):
            _release_gate_page_contract_from_snapshot(snapshot)

    def test_native_xmlid_and_action_model_mismatches_block_release(self):
        page = self._maintain()['pages'][0]
        for changed, expected in [
            ({'menu_xmlid': 'base.menu_administration'}, 'SOURCE_MENU_XMLID_MISMATCH'),
            ({'action_xmlid': 'base.action_res_users'}, 'SOURCE_ACTION_XMLID_MISMATCH'),
            ({'res_model': 'res.partner'}, 'SOURCE_ACTION_MODEL_MISMATCH'),
        ]:
            with self.subTest(expected=expected):
                issues = self.service._source_target_issues(self.env, [{**page, **changed}])
                self.assertIn(expected, {item['code'] for item in issues})

    def test_frozen_publication_is_independent_of_later_draft_edits(self):
        draft = self._maintain()
        snapshot = SimpleNamespace(meta_json={'release_draft': deepcopy(draft)},
            snapshot_json={'policy': self.policy.to_runtime_dict()},
            product_key=self.policy.product_key, source_policy_id=self.policy)
        self.policy.set_native_menu_publication(self.menu.id, 'configuration', 'hidden')
        self.assertTrue(self.service.assert_frozen_release_integrity(snapshot)['exact_match'])
        for schema in ('future', '', None):
            snapshot.snapshot_json['policy_snapshot_schema'] = schema
            with self.assertRaisesRegex(ValueError, 'SCHEMA_UNSUPPORTED'):
                self.service.assert_frozen_release_integrity(snapshot)
        snapshot.snapshot_json.pop('policy_snapshot_schema')
        snapshot.meta_json['release_draft']['pages'][0]['action_id'] += 1
        with self.assertRaisesRegex(ValueError, 'FINGERPRINT_MISMATCH'):
            self.service.assert_frozen_release_integrity(snapshot)
