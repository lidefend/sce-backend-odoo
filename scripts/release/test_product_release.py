#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
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
version_guard = load(
    ROOT / "scripts/verify/product_release_version_guard.py", "product_release_version_guard"
)
SHA = "a" * 40
DIGEST = "sha256:" + "c" * 64
FRONTEND_DIGEST = "sha256:" + "7" * 64


def image_manifest() -> dict:
    return {
        "product_version": release.read_version(),
        "source_sha": SHA,
        "oci_revision": SHA,
        "container_source_revision": SHA,
        "source_tree_sha": "b" * 40,
        "image": f"ghcr.io/lidefend/sce-product:{release.read_version()}",
        "image_tags": [
            f"ghcr.io/lidefend/sce-product:{release.read_version()}",
            f"ghcr.io/lidefend/sce-product:sha-{SHA[:12]}",
        ],
        "registry_repository": "ghcr.io/lidefend/sce-product",
        "registry_refs": [
            f"ghcr.io/lidefend/sce-product@{DIGEST}",
            f"ghcr.io/lidefend/sce-product@{DIGEST}",
        ],
        "image_digest": DIGEST,
        "local_image_id": "sha256:" + "2" * 64,
        "archive_config_digest": "sha256:" + "3" * 64,
        "frontend_image": f"ghcr.io/lidefend/sce-frontend:{release.read_version()}",
        "frontend_image_tags": [
            f"ghcr.io/lidefend/sce-frontend:{release.read_version()}",
            f"ghcr.io/lidefend/sce-frontend:sha-{SHA[:12]}",
        ],
        "frontend_registry_repository": "ghcr.io/lidefend/sce-frontend",
        "frontend_registry_refs": [
            f"ghcr.io/lidefend/sce-frontend@{FRONTEND_DIGEST}",
            f"ghcr.io/lidefend/sce-frontend@{FRONTEND_DIGEST}",
        ],
        "frontend_image_digest": FRONTEND_DIGEST,
        "frontend_local_image_id": "sha256:" + "4" * 64,
        "frontend_archive_config_digest": "sha256:" + "5" * 64,
        "frontend_archive_sha256": hashlib.sha256(b"frontend-archive").hexdigest(),
        "base_image_digests": {
            "frontend_builder": "sha256:" + "d" * 64,
            "frontend_runtime": "sha256:" + "6" * 64,
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
        "schema_version": "candidate_scan.v3",
        "status": "completed",
        "source_sha": SHA,
        "image_digest": DIGEST,
        "counts": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 2, "LOW": 3, "SECRET": 0},
        "tools": {"trivy": "0.63.0", "syft": "1.27.1"},
        "vulnerability_db_updated_at": "2026-07-23T00:00:00Z",
        "scanned_at": "2026-07-23T01:00:00Z",
        "policy": {"result": "pass"},
        "frontend": {
            "image_digest": FRONTEND_DIGEST,
            "counts": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "SECRET": 0},
            "policy": {"result": "pass"},
        },
    }


class ProductReleaseTests(unittest.TestCase):
    def invoke(self, root: Path, image: dict | None = None) -> subprocess.CompletedProcess[str]:
        image = image or image_manifest()
        image_path = root / "image-manifest.json"
        sbom = root / "sbom.cyclonedx.json"
        frontend_sbom = root / "sbom-frontend.cyclonedx.json"
        scan = root / "security-summary.json"
        archive = root / "candidate-image.tar"
        frontend_archive = root / "candidate-frontend-image.tar"
        reload_digest = root / "reloaded-image-id.txt"
        frontend_reload_digest = root / "reloaded-frontend-image-id.txt"
        output = root / "product-release-manifest.json"
        image_path.write_text(json.dumps(image), encoding="utf-8")
        sbom.write_text('{"bomFormat":"CycloneDX"}\n', encoding="utf-8")
        frontend_sbom.write_text('{"bomFormat":"CycloneDX"}\n', encoding="utf-8")
        scan.write_text(json.dumps(scan_summary()), encoding="utf-8")
        archive.write_bytes(b"archive")
        frontend_archive.write_bytes(b"frontend-archive")
        reload_digest.write_text(DIGEST + "\n", encoding="utf-8")
        frontend_reload_digest.write_text(FRONTEND_DIGEST + "\n", encoding="utf-8")
        return subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/release/product_release_manifest.py"),
                "--image-manifest", str(image_path),
                "--sbom", str(sbom),
                "--frontend-sbom", str(frontend_sbom),
                "--scan-summary", str(scan),
                "--archive", str(archive),
                "--frontend-archive", str(frontend_archive),
                "--archive-reload-digest-file", str(reload_digest),
                "--frontend-archive-reload-digest-file", str(frontend_reload_digest),
                "--expected-source-sha", SHA,
                "--output", str(output),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )

    def test_manifest_v4_binds_both_registry_and_archive_identities(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = self.invoke(root)
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads((root / "product-release-manifest.json").read_text())
            schema = json.loads(
                (ROOT / "schemas/release/product_release_manifest.v4.schema.json").read_text()
            )
            Draft202012Validator.check_schema(schema)
            Draft202012Validator(schema).validate(payload)
            self.assertEqual(payload["repository"], "lidefend/sce-backend-odoo")
            self.assertEqual(payload["branch"], "main")
            self.assertEqual(payload["scan"]["counts"]["MEDIUM"], 2)
            self.assertEqual(payload["archive_reload_image_id"], DIGEST)
            self.assertEqual(payload["image_digest"], DIGEST)
            self.assertEqual(payload["frontend_image_digest"], FRONTEND_DIGEST)
            self.assertEqual(payload["frontend_registry_refs"], [
                f"ghcr.io/lidefend/sce-frontend@{FRONTEND_DIGEST}"
            ] * 2)
            self.assertEqual(payload["frontend_archive_reload_image_id"], FRONTEND_DIGEST)
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
            frontend_sbom_sha256="3" * 64,
            archive_sha256=image_manifest()["archive_sha256"],
            frontend_archive_sha256=image_manifest()["frontend_archive_sha256"],
            archive_reload_image_id=DIGEST,
            frontend_archive_reload_image_id=FRONTEND_DIGEST,
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
                    candidate,
                    expected_source_sha=SHA,
                    expected_image_digest=DIGEST,
                    expected_frontend_image_digest=FRONTEND_DIGEST,
                )

    def test_version_and_release_contract_have_one_source(self):
        payload = release.load_release_config()
        self.assertEqual(payload["product_version"], release.read_version())
        self.assertEqual(payload["version_source"], "VERSION")

    def test_explicit_target_version_uses_semver_not_string_order(self):
        contracts = ["tenant_payload_v1", "route_authority.v1"]
        for target in ("1.0.0-rc.6", "1.0.0-rc.10", "1.10.0", "2.0.0-rc.1"):
            with self.subTest(target=target):
                release.verify_customer_compatibility(
                    "1.0.0-rc.6",
                    "2.0.0",
                    contracts,
                    target_version=target,
                )
        for target in ("1.0.0-rc.5", "2.0.0", "2.0.1"):
            with self.subTest(target=target), self.assertRaisesRegex(
                ValueError, "PRODUCT_VERSION_INCOMPATIBLE"
            ):
                release.verify_customer_compatibility(
                    "1.0.0-rc.6",
                    "2.0.0",
                    contracts,
                    target_version=target,
                )

    def test_prerelease_identifier_precedence_is_semver_compliant(self):
        self.assertLess(
            release.compare_versions("1.0.0-rc.9", "1.0.0-rc.10"), 0
        )
        self.assertLess(
            release.compare_versions("1.0.0-rc.10", "1.0.0"), 0
        )
        self.assertGreater(
            release.compare_versions("1.10.0", "1.2.0"), 0
        )

    def test_historical_observation_is_not_a_release_declaration(self):
        report = (ROOT / version_guard.HISTORICAL_VERSION_REPORT).read_text()
        version = re.search(r"page_version=`([^`]+)`", report).group(1)
        line = ("- 历史运行观测（非当前发布声明）：observed_at=2026-10-24; "
                "source_sha=96c860d0fb041c556b687afaad6dc689528785e5; "
                f"page_version=`{version}`。")
        path = version_guard.HISTORICAL_VERSION_REPORT
        self.assertTrue(version_guard.has_release_version_duplicate(
            path, line.replace(version, "99.0.0"), "99.0.0"))
        self.assertFalse(version_guard.has_release_version_duplicate(path, line, version))
        # A current declaration in that report is still a conflict.
        self.assertTrue(version_guard.has_release_version_duplicate(
            path, line + f"\n当前发布版本：{version}", version))
        for invalid in (line.replace("2026-10-24", "2026-10-25"),
                        line.replace("96c860d0", "00000000"),
                        line + f" 当前版本 {version}",
                        f"历史版本 {version}"):
            with self.subTest(invalid=invalid):
                self.assertTrue(version_guard.has_release_version_duplicate(path, invalid, version))
        self.assertTrue(version_guard.has_release_version_duplicate(
            Path("docs/current-release.md"), line, version))

    def write_derived_version_snapshot(self, root: Path, payload: dict) -> None:
        relative = next(iter(version_guard.DERIVED_VERSION_OBSERVATIONS))
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def historical_identity(self):
        relative = next(iter(version_guard.HISTORICAL_IDENTITY_OBSERVATIONS))
        content = (ROOT / relative).read_bytes().decode("utf-8")
        return relative, content, json.loads(content)

    def test_registered_historical_identity_has_exact_provenance(self):
        relative, content, payload = self.historical_identity()
        self.assertEqual(payload["kind"], "historical_runtime_identity_projection")
        self.assertEqual(payload["http_status"], 200)
        self.assertRegex(payload["observed_at"], r"^\d{4}-\d{2}-\d{2}T")
        self.assertRegex(payload["response_projection"]["source_revision"], r"^[0-9a-f]{40}$")
        self.assertRegex(payload["provenance"]["original_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(payload["provenance"]["original_commit"], r"^[0-9a-f]{40}$")
        version = payload["response_projection"]["product_version"]
        self.assertEqual(version_guard.scalar_paths(payload, version),
                         [("response_projection", "product_version")])
        self.assertFalse(version_guard.has_release_version_duplicate(relative, content, version))
        self.assertEqual(version_guard.validate_historical_identities(ROOT), [])

    def test_historical_identity_does_not_exempt_another_path(self):
        _, content, payload = self.historical_identity()
        version = payload["response_projection"]["product_version"]
        for path in ("docs/current-release.json", "docs/ops/iterations/fe-presentation-convergence-01/fepc-09/other.json"):
            with self.subTest(path=path):
                self.assertTrue(version_guard.has_release_version_duplicate(Path(path), content, version))

    def test_historical_identity_rejects_mutations_and_added_declarations(self):
        relative, content, payload = self.historical_identity()
        version = payload["response_projection"]["product_version"]
        variants = [content + f"\nCurrent release: {version}\n", content.replace("\n", "\r\n")]
        for container, key in ((payload, "observed_at"),
                               (payload["response_projection"], "source_revision"),
                               (payload["provenance"], "original_sha256")):
            previous = container[key]
            container[key] = "tampered"
            variants.append(json.dumps(payload))
            container[key] = previous
        payload["current_release"] = version
        variants.append(json.dumps(payload))
        for mutated in variants:
            with self.subTest(mutated=mutated[-80:]):
                self.assertFalse(version_guard.is_registered_historical_identity(relative, mutated))
                self.assertTrue(version_guard.has_release_version_duplicate(relative, mutated, version))

    def test_historical_identity_missing_or_changed_version_fails_even_after_release_bump(self):
        relative, _, payload = self.historical_identity()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.assertTrue(version_guard.validate_historical_identities(root))
            target = root / relative
            target.parent.mkdir(parents=True)
            payload["response_projection"]["product_version"] = "99.0.0"
            target.write_text(json.dumps(payload), encoding="utf-8")
            self.assertTrue(version_guard.validate_historical_identities(root))

    def test_registered_identity_does_not_exempt_other_lines_in_reports(self):
        _, _, payload = self.historical_identity()
        version = payload["response_projection"]["product_version"]
        report = Path("docs/ops/iterations/fe-presentation-convergence-01/fepc-09/findings.md")
        self.assertTrue(version_guard.has_release_version_duplicate(report, f"release: {version}", version))

    def test_derived_version_observation_matches_exact_snapshot_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_derived_version_snapshot(
                root,
                {"ui_contract_raw": {"product_version": release.read_version()}},
            )
            self.assertEqual(
                version_guard.validate_derived_version_observations(
                    root, release.read_version()
                ),
                [],
            )

    def test_derived_version_observation_rejects_stale_value(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_derived_version_snapshot(
                root,
                {"ui_contract_raw": {"product_version": "0.0.0-stale"}},
            )
            errors = version_guard.validate_derived_version_observations(
                root, release.read_version()
            )
            self.assertTrue(any("does not match VERSION" in item for item in errors))

    def test_derived_version_observation_rejects_wrong_json_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_derived_version_snapshot(
                root,
                {"product_version": release.read_version()},
            )
            errors = version_guard.validate_derived_version_observations(
                root, release.read_version()
            )
            self.assertTrue(any("does not match VERSION" in item for item in errors))

    def test_derived_version_observation_rejects_duplicate_value(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            version = release.read_version()
            self.write_derived_version_snapshot(
                root,
                {
                    "ui_contract_raw": {"product_version": version},
                    "duplicate": version,
                },
            )
            errors = version_guard.validate_derived_version_observations(root, version)
            self.assertTrue(any("is not unique" in item for item in errors))


if __name__ == "__main__":
    unittest.main(verbosity=2)
