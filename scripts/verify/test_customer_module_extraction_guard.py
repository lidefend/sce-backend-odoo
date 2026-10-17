"""Product assertions survive P2 extraction; real injected assets must fail."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout
import io
from scripts.verify import form_view_scope_runtime_chain_guard as chain

from scripts.verify.customer_module_extraction_guard import verify_industry_user_data_boundary

ROOT = Path(__file__).resolve().parents[2]


class IndustryDataBoundaryTest(unittest.TestCase):
    def test_repository_baseline(self):
        self.assertEqual(verify_industry_user_data_boundary(ROOT), [])

    def test_reintroduced_payload_file_rejected_in_each_original_module(self):
        for module in ('smart_construction_core', 'smart_construction_scene', 'smart_construction_bootstrap'):
            with self.subTest(module=module), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path = root / 'addons' / module / 'data' / 'user_master_v1.xml'
                path.parent.mkdir(parents=True)
                self.assertEqual(verify_industry_user_data_boundary(root), [])
                path.write_text('<odoo/>')
                self.assertTrue(verify_industry_user_data_boundary(root))

    def test_renamed_payload_detected_by_legacy_identity(self):
        for suffix in ('.xml', '.csv', '.json', '.py', '.md'):
            with self.subTest(suffix=suffix), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path = root / 'addons/smart_construction_core' / ('renamed' + suffix)
                path.parent.mkdir(parents=True)
                path.write_text('ordinary product metadata')
                self.assertEqual(verify_industry_user_data_boundary(root), [])
                path.write_text('legacy_user_sc_synthetic_negative')
                self.assertTrue(verify_industry_user_data_boundary(root))

    def test_product_form_targets_keep_generic_checks_without_p2_prerequisites(self):
        text = (ROOT / 'make/runtime_ops.mk').read_text()
        targets = {}
        for line in text.splitlines():
            if line and not line[0].isspace() and ':' in line:
                key, value = line.split(':', 1)
                targets[key] = value.split()
        for target in ('verify.form_structure.contract', 'verify.form_structure.contract_runtime.audit'):
            dependencies = targets[target]
            self.assertIn('verify.form_view.scope.boundary_guard', dependencies)
            self.assertIn('verify.form_view.native_structure.boundary_guard', dependencies)
            self.assertIn('verify.form_view.scope.runtime_chain_guard', dependencies)
            self.assertFalse(any(item.startswith('verify.user_form.preference.') for item in dependencies))
        self.assertIn('verify.customer_module.extraction', targets['verify.form_structure.contract.guard'])
        self.assertNotIn('scripts/verify/user_form_preference_', text)
        self.assertNotIn('verify.user_form.preference.runtime_audit', targets)


class FormChainNegativeTest(unittest.TestCase):
    def test_actual_chain_then_injected_transport_and_projection_losses(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(chain.main(), 0)
        for path, token in (
            (chain.CONTRACT_V2_CLIENT, 'params.view_id = normalizedRecordId(options.viewId);'),
            (chain.CONTRACT_V2_CLIENT, 'params.menu_id = normalizedRecordId(options.menuId);'),
            (chain.CONTRACT_V2_CLIENT, 'params.action_id = actionId;'),
            (chain.CONTRACT_V2_CLIENT, 'const params = applyCommonOptions({'),
            (chain.APP_VIEW_CONFIG, "requested_view_raw = context.get('contract_view_id')"),
            (chain.APP_VIEW_CONFIG, "requested_view_raw = context.get('requested_view_id')"),
        ):
            with self.subTest(token=token):
                original = chain._read
                def changed(candidate):
                    text = original(candidate)
                    return text.replace(token, '') if candidate == path else text
                with patch.object(chain, '_read', side_effect=changed), redirect_stdout(io.StringIO()):
                    self.assertEqual(chain.main(), 1)


if __name__ == '__main__':
    unittest.main()
