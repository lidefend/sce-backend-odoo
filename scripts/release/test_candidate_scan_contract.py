#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "candidate_scan_contract", ROOT / "scripts/release/candidate_scan_contract.py"
)
assert SPEC and SPEC.loader
scan = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scan)

SHA = "a" * 40
DIGEST = "sha256:" + "b" * 64
FRONTEND_DIGEST = "sha256:" + "c" * 64
LOCAL_ID = "sha256:" + "d" * 64
FRONTEND_LOCAL_ID = "sha256:" + "e" * 64
ODOO_REPOSITORY = "ghcr.io/lidefend/sce-product"
FRONTEND_REPOSITORY = "ghcr.io/lidefend/sce-frontend"
PRODUCT_VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()


def published_manifest() -> dict:
    return {
        "schema_version": 3,
        "source_sha": SHA,
        "image": f"{ODOO_REPOSITORY}:{PRODUCT_VERSION}",
        "image_digest": DIGEST,
        "registry_repository": ODOO_REPOSITORY,
        "registry_refs": [f"{ODOO_REPOSITORY}@{DIGEST}"] * 2,
        "local_image_id": LOCAL_ID,
        "frontend_image": f"{FRONTEND_REPOSITORY}:{PRODUCT_VERSION}",
        "frontend_image_digest": FRONTEND_DIGEST,
        "frontend_registry_repository": FRONTEND_REPOSITORY,
        "frontend_registry_refs": [f"{FRONTEND_REPOSITORY}@{FRONTEND_DIGEST}"] * 2,
        "frontend_local_image_id": FRONTEND_LOCAL_ID,
        "publish_status": "published",
    }


def unpublished_manifest() -> dict:
    return {
        "schema_version": 3,
        "source_sha": SHA,
        "image": f"{ODOO_REPOSITORY}:{PRODUCT_VERSION}",
        "image_digest": None,
        "registry_repository": ODOO_REPOSITORY,
        "local_image_id": LOCAL_ID,
        "frontend_image": f"{FRONTEND_REPOSITORY}:{PRODUCT_VERSION}",
        "frontend_image_digest": None,
        "frontend_registry_repository": FRONTEND_REPOSITORY,
        "frontend_local_image_id": FRONTEND_LOCAL_ID,
        "publish_status": "not_published",
    }


def summary(report: dict, frontend_report: dict | None = None, **overrides):
    values = {
        "report": report,
        "frontend_report": (
            {"Results": []} if frontend_report is None else frontend_report
        ),
        "trivy_version": {"Version": "0.63.0"},
        "trivy_db_metadata": {"UpdatedAt": "2026-07-23T00:00:00Z"},
        "syft_version": {"version": "1.27.1"},
        "image_manifest": published_manifest(),
        "expected_source_sha": SHA,
        "expected_image_digest": DIGEST,
        "expected_frontend_image_digest": FRONTEND_DIGEST,
        "scanned_at": "2026-07-23T01:00:00Z",
    }
    values.update(overrides)
    return scan.build_summary(**values)


class CandidateScanContractTests(unittest.TestCase):
    def test_formal_scan_requests_all_observed_severities_and_secret_scanner(self):
        entrypoint = (ROOT / "scripts/release/immutable_candidate_scan.sh").read_text()
        self.assertIn("--severity UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL", entrypoint)
        self.assertIn("--scanners vuln,secret", entrypoint)

    def test_medium_low_are_captured_but_do_not_block(self):
        result = summary(
            {"Results": [{"Vulnerabilities": [{"Severity": "MEDIUM"}, {"Severity": "LOW"}]}]}
        )
        self.assertEqual(result["counts"]["MEDIUM"], 1)
        self.assertEqual(result["counts"]["LOW"], 1)
        self.assertEqual(result["policy"]["result"], "pass")
        self.assertEqual(result["schema_version"], "candidate_scan.v3")

    def test_missing_results_or_tool_metadata_fails_closed(self):
        with self.assertRaises(scan.ScanContractError):
            summary({})
        with self.assertRaises(scan.ScanContractError):
            summary({"Results": []}, trivy_db_metadata={})
        with self.assertRaises(scan.ScanContractError):
            summary({"Results": []}, frontend_report={})

    def test_formal_entrypoint_reads_trivy_db_metadata_from_cache(self):
        entrypoint = (ROOT / "scripts/release/immutable_candidate_scan.sh").read_text()
        self.assertIn("trivy-cache/trivy/db/metadata.json", entrypoint)
        self.assertIn("--trivy-db-metadata", entrypoint)

    def test_local_candidate_scan_precedes_registry_publication(self):
        build = (ROOT / "scripts/release/immutable_candidate_build.sh").read_text()
        legacy_publish = (
            ROOT / "scripts/release/immutable_candidate_publish.sh"
        ).read_text()
        publish = (ROOT / "scripts/release/release_publication.py").read_text()
        scan_entry = (ROOT / "scripts/release/immutable_candidate_scan.sh").read_text()
        makefile = (ROOT / "make/release.mk").read_text()
        self.assertIn('image_repository="ghcr.io/lidefend/sce-product"', build)
        self.assertIn('"image_digest": None', build)
        self.assertIn('"frontend_image_digest": None', build)
        self.assertIn('"schema_version": 3', build)
        self.assertIn("--expected-local-image-id", scan_entry)
        self.assertIn("--expected-frontend-local-image-id", scan_entry)
        self.assertIn("--expected-frontend-image-digest", scan_entry)
        self.assertIn("--frontend-trivy-report", scan_entry)
        self.assertIn('"$publish_status" == "published"', scan_entry)
        self.assertIn('["docker", "push", reference]', publish)
        self.assertIn('"buildx",', publish)
        self.assertIn('"imagetools",', publish)
        self.assertIn('"inspect",', publish)
        self.assertNotIn("docker push", legacy_publish)
        self.assertIn("legacy manifest-mutating publisher is disabled", legacy_publish)
        self.assertIn("release.candidate:", makefile)
        self.assertIn("release.publish:", makefile)
        self.assertIn("release.candidate.publish:", makefile)

    def test_unpublished_candidate_binds_scan_to_local_image_id(self):
        result = summary(
            {"Results": []},
            image_manifest=unpublished_manifest(),
            expected_image_digest=None,
            expected_frontend_image_digest=None,
            expected_local_image_id=LOCAL_ID,
            expected_frontend_local_image_id=FRONTEND_LOCAL_ID,
        )
        self.assertEqual(result["identity_kind"], "local_image_id")
        self.assertEqual(result["local_image_id"], LOCAL_ID)
        self.assertIsNone(result["image_digest"])
        self.assertEqual(result["publish_status"], "not_published")
        self.assertEqual(result["frontend"]["identity_kind"], "local_image_id")
        self.assertEqual(result["frontend"]["local_image_id"], FRONTEND_LOCAL_ID)
        self.assertIsNone(result["frontend"]["image_digest"])

    def test_unpublished_candidate_rejects_registry_digest_or_wrong_local_id(self):
        manifest = unpublished_manifest()
        local_ids = {
            "expected_local_image_id": LOCAL_ID,
            "expected_frontend_local_image_id": FRONTEND_LOCAL_ID,
        }
        with self.assertRaises(scan.ScanContractError):
            summary(
                {"Results": []},
                image_manifest=manifest,
                expected_image_digest=DIGEST,
                expected_frontend_image_digest=None,
                **local_ids,
            )
        with self.assertRaises(scan.ScanContractError):
            summary(
                {"Results": []},
                image_manifest=manifest,
                expected_image_digest=None,
                expected_frontend_image_digest=None,
                expected_local_image_id="sha256:" + "1" * 64,
                expected_frontend_local_image_id=FRONTEND_LOCAL_ID,
            )
        with self.assertRaises(scan.ScanContractError):
            summary(
                {"Results": []},
                image_manifest=manifest,
                expected_image_digest=None,
                expected_frontend_image_digest=None,
                expected_local_image_id=LOCAL_ID,
                expected_frontend_local_image_id="sha256:" + "1" * 64,
            )

    def test_critical_high_and_secret_each_block(self):
        rows = (
            {"Vulnerabilities": [{"Severity": "CRITICAL"}]},
            {"Vulnerabilities": [{"Severity": "HIGH"}]},
            {"Secrets": [{"RuleID": "secret"}]},
        )
        for image in ("odoo", "frontend"):
            for row in rows:
                with self.subTest(image=image, row=row):
                    if image == "odoo":
                        result = summary({"Results": [row]})
                    else:
                        result = summary({"Results": []}, frontend_report={"Results": [row]})
                    self.assertEqual(result["policy"]["result"], "fail")

    def test_frontend_findings_are_reported_separately_and_block_aggregate(self):
        result = summary(
            {"Results": [{"Vulnerabilities": [{"Severity": "MEDIUM"}]}]},
            frontend_report={"Results": [{"Vulnerabilities": [{"Severity": "HIGH"}]}]},
        )
        self.assertEqual(result["counts"]["MEDIUM"], 1)
        self.assertEqual(result["counts"]["HIGH"], 0)
        self.assertEqual(result["frontend"]["counts"]["HIGH"], 1)
        self.assertEqual(result["policy"]["result"], "fail")
        self.assertEqual(result["frontend"]["policy"]["result"], "fail")
        self.assertEqual(result["images"]["frontend"]["counts"]["HIGH"], 1)

    def test_scan_identity_mismatch_is_rejected(self):
        manifest = published_manifest()
        manifest["source_sha"] = "f" * 40
        with self.assertRaises(scan.ScanContractError):
            summary({"Results": []}, image_manifest=manifest)
        manifest = published_manifest()
        manifest["image_digest"] = "sha256:" + "f" * 64
        with self.assertRaises(scan.ScanContractError):
            summary({"Results": []}, image_manifest=manifest)
        manifest = published_manifest()
        manifest["frontend_image_digest"] = "sha256:" + "f" * 64
        with self.assertRaises(scan.ScanContractError):
            summary({"Results": []}, image_manifest=manifest)
        manifest = published_manifest()
        manifest["frontend_registry_refs"] = []
        with self.assertRaises(scan.ScanContractError):
            summary({"Results": []}, image_manifest=manifest)
        manifest = published_manifest()
        manifest["schema_version"] = 2
        with self.assertRaises(scan.ScanContractError):
            summary({"Results": []}, image_manifest=manifest)
        manifest = published_manifest()
        manifest["frontend_registry_repository"] = ODOO_REPOSITORY
        with self.assertRaises(scan.ScanContractError):
            summary({"Results": []}, image_manifest=manifest)


if __name__ == "__main__":
    unittest.main(verbosity=2)
