#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


release = load(ROOT / "scripts/release/product_release.py", "product_release")
manifest_contract = load(
    ROOT / "scripts/release/product_release_manifest.py", "product_release_manifest"
)
SHA = "a" * 40
DIGEST = "sha256:" + "c" * 64


def image_manifest() -> dict:
    return {
        "product_version": release.read_version(),
        "source_sha": SHA,
        "oci_revision": SHA,
        "container_source_revision": SHA,
        "source_tree_sha": "b" * 40,
        "image": f"sce-product:{release.read_version()}",
        "image_tags": [f"sce-product:{release.read_version()}", f"sce-product:sha-{SHA[:12]}"],
        "image_digest": DIGEST,
        "base_image_digests": {
            "frontend_builder": "sha256:" + "d" * 64,
            "odoo_runtime": "sha256:" + "e" * 64,
        },
        "baseline_checksum": "f" * 64,
        "frontend_build_sha256": "1" * 64,
        "module_version_matrix": {"smart_core": "17.0.1.0.0"},
        "build_time": "2026-01-01T00:00:00Z",
        "archive_sha256": hashlib.sha256(b"archive").hexdigest(),
    }


def scan_summary() -> dict:
    return {
        "schema_version": "candidate_scan.v2",
        "status": "completed",
        "source_sha": SHA,
        "image_digest": DIGEST,
        "counts": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 2, "LOW": 3, "SECRET": 0},
        "tools": {"trivy": "0.63.0", "syft": "1.27.1"},
        "vulnerability_db_updated_at": "2026-07-23T00:00:00Z",
        "scanned_at": "2026-07-23T01:00:00Z",
        "policy": {"result": "pass"},
    }


class ProductReleaseTests(unittest.TestCase):
    def invoke(self, root: Path, image: dict | None = None) -> subprocess.CompletedProcess[str]:
        image = image or image_manifest()
        image_path = root / "image-manifest.json"
        sbom = root / "sbom.cyclonedx.json"
        scan = root / "security-summary.json"
        archive = root / "candidate-image.tar"
        reload_digest = root / "reloaded-image-id.txt"
        output = root / "product-release-manifest.json"
        image_path.write_text(json.dumps(image), encoding="utf-8")
        sbom.write_text('{"bomFormat":"CycloneDX"}\n', encoding="utf-8")
        scan.write_text(json.dumps(scan_summary()), encoding="utf-8")
        archive.write_bytes(b"archive")
        reload_digest.write_text(DIGEST + "\n", encoding="utf-8")
        return subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/release/product_release_manifest.py"),
                "--image-manifest", str(image_path),
                "--sbom", str(sbom),
                "--scan-summary", str(scan),
                "--archive", str(archive),
                "--archive-reload-digest-file", str(reload_digest),
                "--expected-source-sha", SHA,
                "--output", str(output),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )

    def test_manifest_v2_binds_all_required_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = self.invoke(root)
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads((root / "product-release-manifest.json").read_text())
            schema = json.loads(
                (ROOT / "schemas/release/product_release_manifest.v2.schema.json").read_text()
            )
            Draft202012Validator.check_schema(schema)
            Draft202012Validator(schema).validate(payload)
            self.assertEqual(payload["repository"], "lidefend/sce-backend-odoo")
            self.assertEqual(payload["branch"], "main")
            self.assertEqual(payload["scan"]["counts"]["MEDIUM"], 2)
            self.assertEqual(payload["archive_reload_digest"], DIGEST)
            self.assertEqual(payload["deployment_status"], "not_deployed")
            manifest_sha = hashlib.sha256(
                (root / "product-release-manifest.json").read_bytes()
            ).hexdigest()
            self.assertTrue(
                (root / "product-release-manifest.sha256").read_text().startswith(manifest_sha)
            )

    def test_missing_required_field_fails_closed(self):
        candidate = image_manifest()
        del candidate["base_image_digests"]
        with tempfile.TemporaryDirectory() as temporary:
            result = self.invoke(Path(temporary), candidate)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("base_image_digests", result.stderr)

    def test_old_sha_or_digest_is_rejected(self):
        for field, value in (
            ("source_sha", "b" * 40),
            ("image_digest", "sha256:" + "9" * 64),
        ):
            candidate = image_manifest()
            candidate[field] = value
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temporary:
                result = self.invoke(Path(temporary), candidate)
                self.assertNotEqual(result.returncode, 0)

    def test_wrong_branch_and_repository_are_rejected(self):
        payload = manifest_contract.build_manifest(
            image=image_manifest(),
            scan=scan_summary(),
            sbom_sha256="2" * 64,
            archive_sha256=image_manifest()["archive_sha256"],
            archive_reload_digest=DIGEST,
            release=release.load_release_config(),
            expected_source_sha=SHA,
        )
        for field, value in (("branch", "release"), ("repository", "Leedefend/sce-backend-odoo")):
            candidate = dict(payload)
            candidate[field] = value
            with self.subTest(field=field), self.assertRaises(
                manifest_contract.ManifestContractError
            ):
                manifest_contract.validate_manifest(
                    candidate, expected_source_sha=SHA, expected_image_digest=DIGEST
                )

    def test_version_and_release_contract_have_one_source(self):
        payload = release.load_release_config()
        self.assertEqual(payload["product_version"], release.read_version())
        self.assertEqual(payload["version_source"], "VERSION")


if __name__ == "__main__":
    unittest.main(verbosity=2)
