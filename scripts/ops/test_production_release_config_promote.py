#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("production_release_config_promote.py")
SPEC = importlib.util.spec_from_file_location("production_release_config_promote", SCRIPT)
assert SPEC and SPEC.loader
promote = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(promote)


class ProductionReleaseConfigPromoteTests(unittest.TestCase):
    def test_remote_contract_is_fixed_scope_atomic_and_rollback_capable(self):
        source = promote.REMOTE_PROMOTE
        self.assertIn('/opt/sce/config/sc_production/runtime.env', source)
        self.assertIn('/etc/scems/production-promotion.env', source)
        self.assertIn('sc_production-odoo-1', source)
        self.assertIn('sc_production-nginx-1', source)
        self.assertIn('shutil.copy2(runtime_backup, runtime_path)', source)
        self.assertIn('os.replace(runtime_temp, runtime_path)', source)
        self.assertIn('"ACCEPTANCE_PACKAGE_DIGEST": acceptance_digest', source)
        self.assertIn('observed_promotion.get("ACCEPTANCE_PACKAGE_DIGEST") != acceptance_digest', source)
        self.assertNotIn('systemctl', source)
        self.assertNotIn('docker compose', source)
        self.assertNotIn('DB_PASSWORD', source)

    def test_remote_contract_writes_and_reads_back_two_independent_image_identities(self):
        source = promote.REMOTE_PROMOTE
        for expected in (
            '"ODOO_IMAGE_REF": image_ref',
            '"EXPECTED_IMAGE_DIGEST": next_digest',
            '"FRONTEND_IMAGE_REF": frontend_ref',
            '"EXPECTED_FRONTEND_IMAGE_DIGEST": frontend_image_digest',
            '"FRONTEND_BUILD_SHA256": frontend_build_sha256',
            'observed_runtime.get("ODOO_IMAGE_REF") != image_ref',
            'observed_runtime.get("EXPECTED_IMAGE_DIGEST") != next_digest',
            'observed_runtime.get("FRONTEND_IMAGE_REF") != frontend_ref',
            'observed_runtime.get("EXPECTED_FRONTEND_IMAGE_DIGEST") != frontend_image_digest',
            'observed_runtime.get("FRONTEND_BUILD_SHA256") != frontend_build_sha256',
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, source)
        self.assertIn(
            'for key in ("FRONTEND_BUILD_SHA256", "EXPECTED_FRONTEND_IMAGE_DIGEST", '
            '"FRONTEND_IMAGE_REF", "NGINX_IMAGE_REF"):',
            source,
        )
        self.assertIn('runtime_rows.append(key + "=")', source)

    def test_remote_contract_derives_frontend_identity_from_its_own_registry_digest(self):
        source = promote.REMOTE_PROMOTE
        for expected in (
            'frontend_repository = str(image.get("frontend_registry_repository") or "").strip()',
            'frontend_ref = frontend_repository + "@" + frontend_image_digest',
            'frontend_tag != frontend_tags[0]',
            'image.get("frontend_registry_refs") != [frontend_ref, frontend_ref]',
            'image.get("registry_refs") != [image_ref, image_ref]',
            'release.get("frontend_image") != frontend_tag',
            'release.get("frontend_image_digest") != frontend_image_digest',
            'release.get("frontend_registry_refs") != [frontend_ref, frontend_ref]',
            'release.get("frontend_local_image_id") != frontend_image_id',
            'release.get("frontend_sha256") != frontend_build_sha256',
            'observed_next_frontend != frontend_image_id',
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, source)
        self.assertIn('ghcr.io/lidefend/sce-frontend', source)
        self.assertNotIn('release.get("image")', source)

    def test_remote_contract_refuses_a_shared_odoo_and_frontend_image(self):
        source = promote.REMOTE_PROMOTE
        self.assertIn('current_frontend_ref == current_image_ref', source)
        self.assertIn('frontend_ref == image_ref', source)

    def test_remote_contract_compiles_as_python(self):
        compile(promote.REMOTE_PROMOTE, "<remote-promote>", "exec")


if __name__ == "__main__":
    unittest.main()
