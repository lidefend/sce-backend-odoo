#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "production_compose_contract", ROOT / "scripts/release/production_compose_contract.py"
)
assert SPEC and SPEC.loader
contract = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(contract)
DIGEST = "sha256:" + "b" * 64
REF = "sce-product@" + DIGEST
SHA = "a" * 40


def manifest(**values):
    payload = {
        "repository": "lidefend/sce-backend-odoo",
        "branch": "main",
        "image_digest": DIGEST,
        "oci_revision": SHA,
        "container_source_revision": SHA,
    }
    payload.update(values)
    return payload


def validate(**values):
    args = {
        "project": "sc_production",
        "database": "sc_production",
        "odoo_image_ref": REF,
        "nginx_image_ref": REF,
        "expected_digest": DIGEST,
        "manifest": manifest(),
    }
    args.update(values)
    return contract.validate(**args)


class ProductionComposeContractTests(unittest.TestCase):
    def test_digest_addressed_release_passes(self):
        self.assertEqual(validate()["database"], "sc_production")

    def test_legacy_sc_prod_is_rejected(self):
        for field in ("project", "database"):
            with self.subTest(field=field), self.assertRaises(contract.ComposeContractError):
                validate(**{field: "sc_prod"})

    def test_tag_only_or_missing_digest_is_rejected(self):
        for reference in ("sce-product:1.0.0-rc.2", "sce-product:latest", ""):
            with self.subTest(reference=reference), self.assertRaises(
                contract.ComposeContractError
            ):
                validate(odoo_image_ref=reference)

    def test_odoo_nginx_revision_mismatch_is_rejected(self):
        with self.assertRaises(contract.ComposeContractError):
            validate(nginx_image_ref="sce-nginx@" + DIGEST)
        with self.assertRaises(contract.ComposeContractError):
            validate(manifest=manifest(container_source_revision="c" * 40))

    def test_manifest_compose_digest_mismatch_is_rejected(self):
        with self.assertRaises(contract.ComposeContractError):
            validate(manifest=manifest(image_digest="sha256:" + "d" * 64))


if __name__ == "__main__":
    unittest.main(verbosity=2)
