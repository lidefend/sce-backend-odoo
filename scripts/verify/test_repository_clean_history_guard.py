#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import repository_clean_history_guard as guard


SCRIPT = Path(__file__).with_name("repository_clean_history_guard.py")


class RepositoryCleanHistoryGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.git("init", "-b", "main")
        self.git("remote", "add", "origin", "https://example.invalid/new-product.git")
        self.policy = self.root / "policy.json"
        self.policy.write_text(
            json.dumps(
                {
                    "schema_version": "sce.repository_clean_history_policy.v1",
                    "allowed_remotes": {"origin": "https://example.invalid/new-product.git"},
                    "forbidden_repository_tokens": ["old-private-repository"],
                    "repository_token_exempt_paths": ["docs/migration-history.md"],
                    "forbidden_commit_objects": [],
                    "forbidden_path_prefixes": ["filestore/", "attachments/", "artifacts/migration/"],
                    "forbidden_archive_suffixes": [".dump", ".tar", ".zip", ".zst"],
                    "maximum_blob_bytes": 1024 * 1024,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        self.write("README.md", "clean product\n")
        self.base = self.commit("initial clean root")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def git(
        self,
        *args: str,
        input_text: str | None = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=self.root,
            text=True,
            encoding="utf-8",
            errors="replace",
            input=input_text,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=check,
        )

    def write(self, relative: str, content: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def commit(self, message: str) -> str:
        self.git("add", "-A")
        self.git(
            "-c",
            "user.name=Guard Test",
            "-c",
            "user.email=guard@example.invalid",
            "commit",
            "-m",
            message,
        )
        return self.git("rev-parse", "HEAD").stdout.strip()

    def run_guard(self, *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(SCRIPT), "--root", str(self.root), "--policy", str(self.policy), *extra],
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_clean_reachable_history_passes(self) -> None:
        result = self.run_guard()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("reachable_scan=public_refs", result.stdout)

    def test_trusted_base_scans_only_candidate_delta(self) -> None:
        self.write("frontend/change.ts", "export const clean = true;\n")
        self.commit("add clean candidate delta")
        result = self.run_guard("--trusted-base", self.base)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("reachable_scan=trusted_base_incremental", result.stdout)

    def test_trusted_base_rejects_new_secret_material(self) -> None:
        self.write("frontend/unsafe.ts", "token = 'ghp_" + "A" * 36 + "'\n")
        self.commit("add unsafe candidate delta")
        result = self.run_guard("--trusted-base", self.base)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SECRET_MATERIAL", result.stderr)

    def test_trusted_base_rejects_invalid_or_unavailable_identity(self) -> None:
        for value in ("abc123", "f" * 40):
            with self.subTest(value=value):
                result = self.run_guard("--trusted-base", value)
                self.assertEqual(result.returncode, 2)
                self.assertIn("TRUSTED_BASE_INVALID", result.stderr)

        tree = self.git("rev-parse", "HEAD^{tree}").stdout.strip()
        unrelated = self.git(
            "-c",
            "user.name=Guard Test",
            "-c",
            "user.email=guard@example.invalid",
            "commit-tree",
            tree,
            "-m",
            "unrelated trusted base",
        ).stdout.strip()
        result = self.run_guard("--trusted-base", unrelated)
        self.assertEqual(result.returncode, 2)
        self.assertIn("trusted base must be an ancestor", result.stderr)

    def test_trusted_base_authority_change_falls_back_to_full_scan(self) -> None:
        payload = json.loads(self.policy.read_text(encoding="utf-8"))
        payload["forbidden_repository_tokens"].append("retired-product")
        self.policy.write_text(json.dumps(payload) + "\n", encoding="utf-8")
        self.commit("change history policy authority")
        result = self.run_guard("--trusted-base", self.base)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("reachable_scan=public_refs_authority_fallback", result.stdout)

    def test_trusted_base_checks_changed_path_when_blob_is_reused(self) -> None:
        self.git("mv", "README.md", ".env.prod")
        self.commit("reuse base blob under forbidden path")
        result = self.run_guard("--trusted-base", self.base)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("TRACKED_RUNTIME_ENV_FILE", result.stderr)

    def test_detached_head_without_public_refs_remains_authoritative(self) -> None:
        candidate = self.git("rev-parse", "HEAD").stdout.strip()
        self.git("checkout", "--detach", candidate)
        self.git("update-ref", "-d", "refs/heads/main")

        self.assertEqual(
            self.git(
                "for-each-ref",
                "--format=%(refname)",
                "refs/heads",
                "refs/remotes",
                "refs/tags",
            ).stdout.strip(),
            "",
        )
        result = self.run_guard()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("roots=1", result.stdout)

    def test_unrelated_local_stash_root_does_not_pollute_public_history(self) -> None:
        blob_id = self.git("hash-object", "-w", "--stdin", input_text="local recovery\n").stdout.strip()
        tree_id = self.git(
            "mktree",
            input_text=f"100644 blob {blob_id}\tlocal.txt\n",
        ).stdout.strip()
        stash_commit = self.git(
            "-c",
            "user.name=Guard Test",
            "-c",
            "user.email=guard@example.invalid",
            "commit-tree",
            tree_id,
            "-m",
            "unrelated local stash root",
        ).stdout.strip()
        self.git("update-ref", "refs/stash", stash_commit)

        result = self.run_guard()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("roots=1", result.stdout)

        hygiene = self.run_guard("--local-hygiene")
        self.assertNotEqual(hygiene.returncode, 0)
        self.assertIn("LOCAL_STASH_REF_PRESENT", hygiene.stderr)

    def test_policy_requires_expected_schema(self) -> None:
        self.policy.write_text('{"schema_version":"wrong"}\n', encoding="utf-8")
        with self.assertRaises(ValueError):
            guard.load_policy(self.policy)

    def test_reachable_customer_module_is_rejected(self) -> None:
        self.write("addons/sce_customer_acme/__manifest__.py", "{}\n")
        self.commit("add forbidden customer module")
        result = self.run_guard()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("CUSTOMER_MODULE_PATH", result.stderr)

    def test_current_tree_clean_but_history_dirty_is_rejected(self) -> None:
        self.write(".env.prod", "DB_PASSWORD=not-a-real-password\n")
        self.commit("add runtime environment")
        (self.root / ".env.prod").unlink()
        self.commit("clean current tree")
        result = self.run_guard()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("TRACKED_RUNTIME_ENV_FILE", result.stderr)

    def test_hex_digest_with_mobile_shaped_segment_is_not_personal_data(self) -> None:
        digest = "a1f4-" + "13800" + "138000" + "F0c9"
        self.write("docs/audit.json", json.dumps({"evidence_digest": digest}) + "\n")
        self.commit("record anonymized evidence digest")
        result = self.run_guard()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_standalone_mobile_number_is_rejected(self) -> None:
        mobile = "13800" + "138000"
        self.write("docs/contact.txt", f"contact={mobile}\n")
        self.commit("record personal contact")
        result = self.run_guard()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("PERSONAL_DATA", result.stderr)

    def register_false_positive(
        self,
        *,
        path: str,
        blob_id: str,
        rule_id: str = "PD002",
        classification: str = "MOBILE_PHONE_PATTERN",
    ) -> None:
        registry = "personal-data-false-positives.json"
        policy = json.loads(self.policy.read_text(encoding="utf-8"))
        policy["personal_data_false_positive_registry"] = registry
        self.policy.write_text(json.dumps(policy) + "\n", encoding="utf-8")
        (self.root / registry).write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "entries": [
                        {
                            "rule_id": rule_id,
                            "path": path,
                            "blob_id": blob_id,
                            "classification": classification,
                            "reason": "verified_synthetic_fixture",
                        }
                    ],
                }
            )
            + "\n",
            encoding="utf-8",
        )

    def register_oversized_blob_exception(
        self,
        *,
        path: str,
        blob_id: str,
        rule_id: str = "RH007",
        classification: str = "OVERSIZED_BLOB",
    ) -> None:
        registry = "oversized-blob-exceptions.json"
        policy = json.loads(self.policy.read_text(encoding="utf-8"))
        policy["oversized_blob_exception_registry"] = registry
        self.policy.write_text(json.dumps(policy) + "\n", encoding="utf-8")
        (self.root / registry).write_text(
            json.dumps(
                {
                    "schema_version": "sce.repository_oversized_blob_exceptions.v1",
                    "entries": [
                        {
                            "rule_id": rule_id,
                            "path": path,
                            "blob_id": blob_id,
                            "classification": classification,
                            "reason": "reviewed generated evidence",
                        }
                    ],
                }
            )
            + "\n",
            encoding="utf-8",
        )

    def test_exact_registered_oversized_blob_is_scanned_and_suppressed(self) -> None:
        path = "contracts/generated/report.json"
        self.write(path, "x" * (1024 * 1024 + 1))
        blob_id = self.git("hash-object", path).stdout.strip()
        self.register_oversized_blob_exception(path=path, blob_id=blob_id)
        self.commit("add governed oversized evidence")
        result = self.run_guard()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("oversized_exceptions=1", result.stdout)

    def test_oversized_exception_does_not_suppress_changed_blob(self) -> None:
        path = "contracts/generated/report.json"
        self.write(path, "x" * (1024 * 1024 + 1))
        blob_id = self.git("hash-object", path).stdout.strip()
        self.register_oversized_blob_exception(path=path, blob_id=blob_id)
        self.write(path, "y" * (1024 * 1024 + 1))
        self.commit("add changed oversized evidence")
        result = self.run_guard()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("OVERSIZED_BLOB", result.stderr)
        self.assertIn("STALE_OVERSIZED_BLOB_EXCEPTION", result.stderr)

    def test_oversized_exception_does_not_suppress_other_path(self) -> None:
        path = "contracts/generated/report.json"
        self.write(path, "x" * (1024 * 1024 + 1))
        blob_id = self.git("hash-object", path).stdout.strip()
        self.register_oversized_blob_exception(
            path="contracts/generated/other.json",
            blob_id=blob_id,
        )
        self.commit("add path-mismatched oversized evidence")
        result = self.run_guard()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("OVERSIZED_BLOB", result.stderr)
        self.assertIn("STALE_OVERSIZED_BLOB_EXCEPTION", result.stderr)

    def test_registered_oversized_blob_still_rejects_secret_material(self) -> None:
        path = "contracts/generated/report.json"
        secret_value = "ghp_" + "A" * 36
        self.write(path, secret_value + "\n" + "x" * (1024 * 1024 + 1))
        blob_id = self.git("hash-object", path).stdout.strip()
        self.register_oversized_blob_exception(path=path, blob_id=blob_id)
        self.commit("add unsafe oversized evidence")
        result = self.run_guard()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SECRET_MATERIAL", result.stderr)
        self.assertNotIn(secret_value, result.stdout + result.stderr)

    def test_oversized_exception_requires_full_blob_identity(self) -> None:
        self.register_oversized_blob_exception(
            path="contracts/generated/report.json",
            blob_id="abc123",
        )
        result = self.run_guard()
        self.assertEqual(result.returncode, 2)
        self.assertIn("classification=ValueError", result.stderr)

    def test_exact_registered_synthetic_mobile_history_is_suppressed(self) -> None:
        path = "addons/smart_construction_demo/demo.py"
        self.write(path, "phone = '138" + "00000001'\n")
        blob_id = self.git("hash-object", path).stdout.strip()
        self.register_false_positive(path=path, blob_id=blob_id)
        self.commit("add governed synthetic fixture")
        result = self.run_guard()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_exact_registered_synthetic_bank_account_history_is_suppressed(self) -> None:
        path = "addons/smart_construction_core/tests/test_payment.py"
        self.write(path, "bank_account = '622202" + "1234567890'\n")
        blob_id = self.git("hash-object", path).stdout.strip()
        self.register_false_positive(
            path=path,
            blob_id=blob_id,
            rule_id="PD003",
            classification="BANK_ACCOUNT_PATTERN",
        )
        self.commit("add governed synthetic bank fixture")
        result = self.run_guard()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_synthetic_bank_account_registration_does_not_suppress_changed_blob(self) -> None:
        path = "addons/smart_construction_core/tests/test_payment.py"
        self.write(path, "bank_account = '622202" + "1234567890'\n")
        self.register_false_positive(
            path=path,
            blob_id="a" * 40,
            rule_id="PD003",
            classification="BANK_ACCOUNT_PATTERN",
        )
        self.commit("add unmatched synthetic bank fixture")
        result = self.run_guard()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("BANK_ACCOUNT_PATTERN", result.stderr)

    def test_registered_mobile_does_not_suppress_other_personal_data(self) -> None:
        path = "addons/smart_construction_demo/demo.py"
        self.write(
            path,
            "phone = '138" + "00000001'\nid_number = '110105" + "19491231002X'\n",
        )
        blob_id = self.git("hash-object", path).stdout.strip()
        self.register_false_positive(path=path, blob_id=blob_id)
        self.commit("add mixed synthetic fixture")
        result = self.run_guard()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("GOVERNMENT_ID_PATTERN", result.stderr)

    def test_false_positive_with_wrong_blob_does_not_suppress(self) -> None:
        path = "addons/smart_construction_demo/demo.py"
        self.write(path, "phone = '138" + "00000001'\n")
        self.register_false_positive(path=path, blob_id="a" * 40)
        self.commit("add unmatched synthetic fixture")
        result = self.run_guard()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("MOBILE_PHONE_PATTERN", result.stderr)

    def test_false_positive_with_wrong_path_does_not_suppress(self) -> None:
        path = "addons/smart_construction_demo/demo.py"
        self.write(path, "phone = '138" + "00000001'\n")
        blob_id = self.git("hash-object", path).stdout.strip()
        self.register_false_positive(path="other.py", blob_id=blob_id)
        self.commit("add path-mismatched synthetic fixture")
        result = self.run_guard()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("MOBILE_PHONE_PATTERN", result.stderr)

    def test_current_old_repository_identity_is_rejected(self) -> None:
        self.write("scripts/checkout.sh", "git clone old-private-repository\n")
        self.commit("add stale executable repository identity")
        result = self.run_guard()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("OLD_REPOSITORY_REFERENCE", result.stderr)

    def test_historical_old_repository_identity_is_preserved(self) -> None:
        self.write("scripts/checkout.sh", "git clone old-private-repository\n")
        self.commit("record old repository identity")
        (self.root / "scripts/checkout.sh").unlink()
        self.commit("remove stale executable repository identity")
        result = self.run_guard()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_explicit_migration_history_path_is_exempt(self) -> None:
        self.write("docs/migration-history.md", "moved from old-private-repository\n")
        self.commit("document repository migration")
        result = self.run_guard()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_tag_pointing_to_sensitive_commit_is_rejected(self) -> None:
        self.write(".env.prod", "DB_PASSWORD=not-a-real-password\n")
        sensitive_commit = self.commit("sensitive tagged commit")
        (self.root / ".env.prod").unlink()
        self.commit("remove runtime environment")
        self.git("tag", "legacy-sensitive", sensitive_commit)
        result = self.run_guard("--local-hygiene")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("TAG_REF_PRESENT", result.stderr)
        self.assertIn("TRACKED_RUNTIME_ENV_FILE", result.stderr)

    def test_remote_tracking_ref_to_old_object_is_rejected(self) -> None:
        self.write(".env.prod", "DB_PASSWORD=not-a-real-password\n")
        sensitive_commit = self.commit("old remote commit")
        (self.root / ".env.prod").unlink()
        self.commit("remove old remote content")
        self.git("update-ref", "refs/remotes/origin/legacy", sensitive_commit)
        result = self.run_guard("--local-hygiene")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("STALE_REMOTE_TRACKING_REF", result.stderr)

    def test_reflog_only_sensitive_blob_is_rejected_without_value_disclosure(self) -> None:
        secret_value = "ghp_" + "A" * 36
        self.write("temporary-secret.txt", f"TOKEN={secret_value}\n")
        self.commit("temporary sensitive commit")
        self.git("reset", "--hard", "HEAD^")
        result = self.run_guard("--local-hygiene")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("REFLOG_ONLY_COMMIT", result.stderr)
        self.assertIn("SECRET_MATERIAL", result.stderr)
        self.assertNotIn(secret_value, result.stdout + result.stderr)
        self.assertIn("sensitive_values_recorded=false", result.stderr)

    def test_unreachable_env_prod_is_rejected(self) -> None:
        blob_id = self.git("hash-object", "-w", "--stdin", input_text="DB_PASSWORD=ephemeral\n").stdout.strip()
        tree_id = self.git(
            "mktree",
            input_text=f"100644 blob {blob_id}\t.env.prod\n",
        ).stdout.strip()
        self.git(
            "-c",
            "user.name=Guard Test",
            "-c",
            "user.email=guard@example.invalid",
            "commit-tree",
            tree_id,
            "-m",
            "unreachable environment",
        )
        result = self.run_guard("--local-hygiene")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("UNREACHABLE_OBJECT", result.stderr)
        self.assertIn("TRACKED_RUNTIME_ENV_FILE", result.stderr)


if __name__ == "__main__":
    unittest.main()
