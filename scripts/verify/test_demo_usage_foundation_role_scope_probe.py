import unittest
from pathlib import Path
from unittest.mock import patch

import scripts.verify.demo_usage_foundation_role_scope_probe as mod
from scripts.verify.demo_usage_foundation_role_scope_probe import (
    ManifestError,
    load_manifest,
    probe,
    validate_manifest,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = (
    REPO_ROOT / "scripts/verify/demo_usage_foundation_role_scope_manifest.json"
)


def _small_manifest() -> dict:
    return {
        "schema_version": 1,
        "id": "test.role.scope",
        "owner_layer": "P4",
        "authority": "test",
        "runtime": {
            "base_url_env": "E2E_BASE_URL",
            "base_url_default": "http://127.0.0.1:18081",
            "entry_namespace": "demo",
            "database_env": "E2E_DB",
            "database_default": "sc_dev_demo",
        },
        "company_scope": {
            "expected_company_id": 1,
            "expected_allowed_company_ids": [1],
        },
        "accounts": [
            {
                "key": "pm",
                "login": "demo_role_pm",
                "expectation": "role_code",
                "expected_role_code": "pm",
                "label": "项目经理",
            },
            {
                "key": "ct",
                "login": "ct1",
                "expectation": "valid_surface",
                "label": "合同",
                "expected_allowed_company_ids": [1, 2],
            },
        ],
        "negatives": [
            {
                "key": "wrong",
                "login": "wutao",
                "password": "badpass",
                "expectation": "login_denied",
            }
        ],
    }


def _fake_login(base_url, namespace, login, password):
    if password == "badpass":
        return 401, {"ok": False}, ""
    return 200, {"ok": True, "data": {"session": {"token": f"tok-{login}"}}}, f"tok-{login}"


def _fake_post(url, payload, token=None):
    intent = payload.get("intent")
    if intent == "system.init":
        allowed_company_ids = [1, 2] if token == "tok-ct1" else [1]
        return 200, {
            "ok": True,
            "data": {
                "role_surface": {"role_code": "pm"},
                "user": {
                    "company_id": 1,
                    "allowed_company_ids": allowed_company_ids,
                },
                "default_route": {"route": "/", "scene_key": "workspace.home"},
            },
        }
    if intent == "my.work.summary":
        return 200, {"ok": True, "data": {"summary": [{"key": "todo", "count": 0}]}}
    return 404, {"ok": False}


class DemoUsageFoundationRoleScopeProbeTest(unittest.TestCase):
    def test_real_manifest_loads_and_validates(self):
        manifest = load_manifest(MANIFEST_PATH)
        self.assertEqual(manifest["id"], "demo.usage.foundation.role_scope")
        validate_manifest(manifest)

    def test_real_manifest_covers_required_roles(self):
        manifest = load_manifest(MANIFEST_PATH)
        by_key = {a["key"] for a in manifest["accounts"]}
        for expected in (
            "business_full_wutao",
            "project_manager",
            "finance_manager",
            "owner",
            "executive",
            "cost_user",
            "project_member_read",
            "contract_admin",
            "purchase_user",
            "material_manager",
        ):
            self.assertIn(expected, by_key)

    def test_real_manifest_has_negative(self):
        manifest = load_manifest(MANIFEST_PATH)
        self.assertTrue(manifest["negatives"])
        self.assertEqual(manifest["negatives"][0]["expectation"], "login_denied")

    def test_missing_account_login_rejected(self):
        manifest = _small_manifest()
        del manifest["accounts"][0]["login"]
        with self.assertRaises(ManifestError):
            validate_manifest(manifest)

    def test_illegal_expectation_rejected(self):
        manifest = _small_manifest()
        manifest["accounts"][0]["expectation"] = "whatever"
        with self.assertRaises(ManifestError):
            validate_manifest(manifest)

    def test_illegal_owner_layer_rejected(self):
        manifest = _small_manifest()
        manifest["owner_layer"] = "P9"
        with self.assertRaises(ManifestError):
            validate_manifest(manifest)

    def test_illegal_first_screen_expectation_rejected(self):
        manifest = _small_manifest()
        manifest["accounts"][0]["first_screen_expectation"] = "sometimes"
        with self.assertRaises(ManifestError):
            validate_manifest(manifest)

    def test_duplicate_account_key_rejected(self):
        manifest = _small_manifest()
        manifest["accounts"].append(dict(manifest["accounts"][0]))
        with self.assertRaises(ManifestError):
            validate_manifest(manifest)

    def test_duplicate_login_rejected(self):
        manifest = _small_manifest()
        duplicate = dict(manifest["accounts"][0])
        duplicate["key"] = "pm_copy"
        manifest["accounts"].append(duplicate)
        with self.assertRaises(ManifestError):
            validate_manifest(manifest)

    def test_probe_classifies_ok(self):
        with patch.object(mod, "_login", side_effect=_fake_login), patch.object(
            mod, "_post", side_effect=_fake_post
        ):
            report = probe(_small_manifest(), "http://x", "demo", "123456")
        self.assertTrue(report["summary"]["overall_pass"])
        self.assertEqual(report["summary"]["account_failed"], 0)
        self.assertEqual(report["summary"]["negative_failed"], 0)

    def test_probe_fails_on_role_mismatch(self):
        def fake_post_role_wrong(url, payload, token=None):
            if payload.get("intent") == "system.init":
                data = _fake_post(url, payload, token)[1]["data"]
                data["role_surface"] = {"role_code": "executive"}
                return 200, {"ok": True, "data": data}
            return _fake_post(url, payload, token)

        with patch.object(mod, "_login", side_effect=_fake_login), patch.object(
            mod, "_post", side_effect=fake_post_role_wrong
        ):
            report = probe(_small_manifest(), "http://x", "demo", "123456")
        self.assertFalse(report["summary"]["overall_pass"])
        pm = next(a for a in report["accounts"] if a["key"] == "pm")
        self.assertFalse(pm["role_ok"])

    def test_probe_fails_on_wrong_company(self):
        def fake_post_company_wrong(url, payload, token=None):
            if payload.get("intent") == "system.init":
                data = _fake_post(url, payload, token)[1]["data"]
                data["user"]["company_id"] = 2
                return 200, {"ok": True, "data": data}
            return _fake_post(url, payload, token)

        with patch.object(mod, "_login", side_effect=_fake_login), patch.object(
            mod, "_post", side_effect=fake_post_company_wrong
        ):
            report = probe(_small_manifest(), "http://x", "demo", "123456")
        self.assertFalse(report["summary"]["overall_pass"])
        self.assertTrue(any(not a["company_ok"] for a in report["accounts"]))

    def test_probe_accepts_allowed_company_order_from_login_contract(self):
        def fake_post_reversed_companies(url, payload, token=None):
            if payload.get("intent") == "system.init":
                data = _fake_post(url, payload, token)[1]["data"]
                data["user"]["allowed_company_ids"] = [2, 1]
                return 200, {"ok": True, "data": data}
            return _fake_post(url, payload, token)

        with patch.object(mod, "_login", side_effect=_fake_login), patch.object(
            mod, "_post", side_effect=fake_post_reversed_companies
        ):
            report = probe(_small_manifest(), "http://x", "demo", "123456")

        ct = next(a for a in report["accounts"] if a["key"] == "ct")
        self.assertTrue(ct["company_ok"])
        self.assertEqual(ct["actual_allowed_company_ids"], [2, 1])

    def test_probe_fails_on_empty_first_screen_when_required(self):
        manifest = _small_manifest()
        manifest["accounts"][0]["first_screen_expectation"] = "non_empty"
        with patch.object(mod, "_login", side_effect=_fake_login), patch.object(
            mod, "_post", side_effect=_fake_post
        ):
            report = probe(manifest, "http://x", "demo", "123456")
        pm = next(a for a in report["accounts"] if a["key"] == "pm")
        self.assertFalse(pm["first_screen_ok"])
        self.assertFalse(report["summary"]["overall_pass"])

    def test_negative_requires_login_denied(self):
        def fake_login_always_ok(base_url, namespace, login, password):
            return 200, {"ok": True, "data": {"session": {"token": "tok"}}}, "tok"

        with patch.object(mod, "_login", side_effect=fake_login_always_ok), patch.object(
            mod, "_post", side_effect=_fake_post
        ):
            report = probe(_small_manifest(), "http://x", "demo", "123456")
        self.assertFalse(report["summary"]["overall_pass"])
        self.assertTrue(any(not n["pass"] for n in report["negatives"]))


if __name__ == "__main__":
    unittest.main()
