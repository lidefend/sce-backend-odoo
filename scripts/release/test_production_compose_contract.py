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
ODOO_DIGEST = "sha256:" + "b" * 64
FRONTEND_DIGEST = "sha256:" + "d" * 64
ODOO_REF = "ghcr.io/lidefend/sce-product@" + ODOO_DIGEST
FRONTEND_REF = "ghcr.io/lidefend/sce-frontend@" + FRONTEND_DIGEST
SHA = "a" * 40


def manifest(**values):
    payload = {
        "repository": "lidefend/sce-backend-odoo",
        "branch": "main",
        "image": ODOO_REF,
        "image_digest": ODOO_DIGEST,
        "frontend_image": FRONTEND_REF,
        "frontend_image_digest": FRONTEND_DIGEST,
        "source_sha": SHA,
        "oci_revision": SHA,
        "container_source_revision": SHA,
    }
    payload.update(values)
    return payload


def validate(**values):
    args = {
        "project": "sc_production",
        "database": "sc_production",
        "odoo_image_ref": ODOO_REF,
        "frontend_image_ref": FRONTEND_REF,
        "expected_odoo_digest": ODOO_DIGEST,
        "expected_frontend_digest": FRONTEND_DIGEST,
        "manifest": manifest(),
    }
    args.update(values)
    return contract.validate(**args)


class ProductionComposeContractTests(unittest.TestCase):
    def test_digest_addressed_release_passes(self):
        result = validate()
        self.assertEqual(result["database"], "sc_production")
        self.assertEqual(result["odoo"]["image_reference"], ODOO_REF)
        self.assertEqual(result["odoo"]["image_digest"], ODOO_DIGEST)
        self.assertEqual(result["frontend"]["image_reference"], FRONTEND_REF)
        self.assertEqual(result["frontend"]["image_digest"], FRONTEND_DIGEST)

    def test_legacy_sc_prod_is_rejected(self):
        for field in ("project", "database"):
            with self.subTest(field=field), self.assertRaises(contract.ComposeContractError):
                validate(**{field: "sc_prod"})

    def test_tag_only_or_missing_digest_is_rejected(self):
        for reference in ("sce-product:1.0.0-rc.2", "sce-product:latest", ""):
            with self.subTest(service="odoo", reference=reference), self.assertRaises(
                contract.ComposeContractError
            ):
                validate(odoo_image_ref=reference)
            with self.subTest(service="frontend", reference=reference), self.assertRaises(
                contract.ComposeContractError
            ):
                validate(frontend_image_ref=reference)

    def test_missing_or_malformed_expected_digest_is_rejected(self):
        for digest in ("", "sha256:" + "A" * 64, "sha256:" + "b" * 63):
            with self.subTest(service="odoo", digest=digest), self.assertRaises(
                contract.ComposeContractError
            ):
                validate(expected_odoo_digest=digest)
            with self.subTest(service="frontend", digest=digest), self.assertRaises(
                contract.ComposeContractError
            ):
                validate(expected_frontend_digest=digest)

    def test_distinct_odoo_and_frontend_images_pass(self):
        result = validate()
        self.assertNotEqual(
            result["odoo"]["image_reference"], result["frontend"]["image_reference"]
        )
        self.assertNotEqual(
            result["odoo"]["image_digest"], result["frontend"]["image_digest"]
        )

    def test_same_image_reference_is_no_longer_required(self):
        # The old contract demanded one shared reference; a shared reference is
        # still admissible, but it must not be the only accepted shape.
        shared = validate(
            frontend_image_ref=ODOO_REF,
            expected_frontend_digest=ODOO_DIGEST,
            manifest=manifest(frontend_image=ODOO_REF, frontend_image_digest=ODOO_DIGEST),
        )
        self.assertEqual(shared["odoo"]["image_digest"], shared["frontend"]["image_digest"])

    def test_cross_wired_digests_are_rejected(self):
        with self.subTest(case="frontend-ref-carries-odoo-digest"), self.assertRaises(
            contract.ComposeContractError
        ):
            validate(frontend_image_ref="ghcr.io/lidefend/sce-frontend@" + ODOO_DIGEST)
        with self.subTest(case="odoo-ref-carries-frontend-digest"), self.assertRaises(
            contract.ComposeContractError
        ):
            validate(odoo_image_ref="ghcr.io/lidefend/sce-product@" + FRONTEND_DIGEST)
        with self.subTest(case="swapped-expected-digests"), self.assertRaises(
            contract.ComposeContractError
        ):
            validate(
                expected_odoo_digest=FRONTEND_DIGEST,
                expected_frontend_digest=ODOO_DIGEST,
            )

    def test_release_revision_mismatch_is_rejected(self):
        with self.assertRaises(contract.ComposeContractError):
            validate(manifest=manifest(container_source_revision="c" * 40))
        with self.assertRaises(contract.ComposeContractError):
            validate(manifest=manifest(oci_revision="c" * 40))
        with self.assertRaises(contract.ComposeContractError):
            validate(manifest=manifest(source_sha="c" * 40))

    def test_release_source_revision_is_required(self):
        payload = manifest()
        payload.pop("source_sha")
        with self.assertRaises(contract.ComposeContractError):
            validate(manifest=payload)

    def test_manifest_odoo_digest_mismatch_is_rejected(self):
        with self.assertRaises(contract.ComposeContractError):
            validate(manifest=manifest(image_digest="sha256:" + "e" * 64))

    def test_manifest_frontend_digest_mismatch_is_rejected(self):
        with self.assertRaises(contract.ComposeContractError):
            validate(manifest=manifest(frontend_image_digest="sha256:" + "e" * 64))

    def test_manifest_without_frontend_digest_is_rejected(self):
        payload = manifest()
        payload.pop("frontend_image_digest")
        with self.assertRaises(contract.ComposeContractError):
            validate(manifest=payload)

    def test_manifest_image_references_must_match_compose(self):
        with self.subTest(service="odoo"), self.assertRaises(contract.ComposeContractError):
            validate(manifest=manifest(image="ghcr.io/lidefend/sce-product@sha256:" + "f" * 64))
        with self.subTest(service="frontend"), self.assertRaises(contract.ComposeContractError):
            validate(manifest=manifest(frontend_image="ghcr.io/lidefend/sce-frontend@sha256:" + "f" * 64))

    def test_repository_and_branch_are_still_fixed(self):
        with self.subTest(case="repository"), self.assertRaises(contract.ComposeContractError):
            validate(manifest=manifest(repository="other/repository"))
        with self.subTest(case="branch"), self.assertRaises(contract.ComposeContractError):
            validate(manifest=manifest(branch="release"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
