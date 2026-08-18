# -*- coding: utf-8 -*-
"""
smart_license_core minimal tests (PRODUCTIZATION-P0-SPRINT-001, R1).

License tier gate is the productization storefront: these tests pin the
tier ranking, prefix-based minimum tier resolution, capability filtering
and the fallback behavior when config parameters are unavailable.

PENDING-ENV: to be executed in an Odoo test run (make mod.tests or CI).
"""

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_license_core.core_extension import (
    TIER_RANK,
    _allow,
    _min_tier_for_key,
    get_intent_handler_contributions,
    smart_core_extend_system_init,
)


class _BrokenEnv:
    """Simulates an env whose ir.config_parameter access fails (defensive path)."""

    def __getitem__(self, key):
        raise RuntimeError(f"no model access in dummy env: {key}")


class _ParamEnv:
    """Minimal env stub serving ir.config_parameter values."""

    def __init__(self, params):
        self._params = params

    def __getitem__(self, key):
        if key != "ir.config_parameter":
            raise KeyError(key)

        class _ICP:
            def __init__(self, params):
                self._params = params

            def sudo(self):
                return self

            def get_param(self, name, default=None):
                return self._params.get(name, default)

        return _ICP(self._params)


@tagged("post_install", "-at_install", "smart_license_core", "tier_gate")
class TestLicenseTierGate(TransactionCase):
    def test_tier_rank_ordering(self):
        self.assertLess(TIER_RANK["community"], TIER_RANK["pro"])
        self.assertLess(TIER_RANK["pro"], TIER_RANK["enterprise"])

    def test_min_tier_for_key_prefix_rules(self):
        self.assertEqual(_min_tier_for_key("governance.audit"), "pro")
        self.assertEqual(_min_tier_for_key("analytics.report"), "pro")
        self.assertEqual(_min_tier_for_key("finance.pay"), "pro")
        self.assertEqual(_min_tier_for_key("owner.dashboard"), "enterprise")
        self.assertEqual(_min_tier_for_key("project.list"), "community")
        self.assertEqual(_min_tier_for_key(""), "community")
        self.assertEqual(_min_tier_for_key(None), "community")

    def test_allow_enforces_upgrade_path(self):
        # community license must NOT see pro/enterprise capabilities
        self.assertFalse(_allow("governance.audit", "community"))
        self.assertFalse(_allow("owner.dashboard", "community"))
        self.assertFalse(_allow("owner.dashboard", "pro"))
        # pro sees pro-tier but not enterprise-tier
        self.assertTrue(_allow("governance.audit", "pro"))
        self.assertFalse(_allow("owner.dashboard", "pro"))
        # enterprise sees everything; unknown level falls back to community
        self.assertTrue(_allow("owner.dashboard", "enterprise"))
        self.assertFalse(_allow("governance.audit", "unknown-level"))

    def test_extend_system_init_filters_capabilities_by_level(self):
        env = _ParamEnv({"sc.license.level": "pro"})
        data = {
            "capabilities": [
                {"key": "project.list"},
                {"key": "governance.audit"},
                {"key": "owner.dashboard"},
                "not-a-dict",
            ],
            "capability_groups": [
                {"capabilities": [{"key": "finance.pay"}, {"key": "owner.risk.list"}]},
            ],
        }
        smart_core_extend_system_init(data, env, None)
        self.assertEqual(
            sorted(cap["key"] for cap in data["capabilities"]),
            ["governance.audit", "project.list"],
        )
        bucket = data["capability_groups"][0]
        self.assertEqual([cap["key"] for cap in bucket["capabilities"]], ["finance.pay"])
        self.assertEqual(bucket["capability_count"], 1)
        license_fact = data["ext_facts"]["product"]["license"]
        self.assertEqual(license_fact["level"], "pro")
        self.assertEqual(license_fact["tiers"], ["community", "pro", "enterprise"])
        self.assertTrue(license_fact["customer_visible"])

    def test_extend_system_init_fallback_is_enterprise(self):
        # broken env must degrade to enterprise (fail-open per design) and not crash
        smart_core_extend_system_init({}, _BrokenEnv(), None)

    def test_intent_handler_contributions_empty_by_design(self):
        # license core gates capabilities, it does not contribute intent handlers
        self.assertEqual(get_intent_handler_contributions(), [])
