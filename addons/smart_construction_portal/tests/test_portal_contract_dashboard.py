# -*- coding: utf-8 -*-
"""
smart_construction_portal minimal tests (PRODUCTIZATION-P0-SPRINT-001, R1).

Pins the portal lifecycle dashboard contract: schema version, layout columns,
matrix-derived state/capability projections, and the sensitive-profile
redaction rule (customer-facing payloads must NOT leak login/db unless
explicitly enabled AND internal-group member).

PENDING-ENV: to be executed in an Odoo test run (make mod.tests or CI).
"""

from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_construction_portal.services.portal_contract_service import (
    PortalContractService,
)


class _DummyCompany:
    id = 1


class _DummyUser:
    tz = "Asia/Shanghai"

    def has_group(self, group_xmlid):
        return False


class _DummyICP:
    def __init__(self, params):
        self._params = params

    def sudo(self):
        return self

    def get_param(self, name, default=None):
        return self._params.get(name, default)


class _DummyEnv:
    def __init__(self, params, user=None):
        self._params = params
        self.user = user or _DummyUser()
        self.company = _DummyCompany()
        self.lang = "zh_CN"
        self.context = {"tz": "Asia/Shanghai"}

    def __getitem__(self, key):
        if key == "ir.config_parameter":
            return _DummyICP(self._params)
        raise KeyError(key)


@tagged("post_install", "-at_install", "smart_construction_portal", "contract_dashboard")
class TestPortalLifecycleDashboardContract(TransactionCase):
    def _build(self, params=None):
        service = PortalContractService(_DummyEnv(params or {}))
        matrix = {
            "draft": {"cap.sc.boq": {}, "cap.sc.plan": {}},
            "execution": {"cap.sc.boq": {}, "cap.sc.pay": {}},
        }
        with patch(
            "odoo.addons.smart_construction_core.services."
            "lifecycle_capability_service.LifecycleCapabilityService._load_matrix",
            return_value=(matrix, {"version": "v1"}),
        ):
            return service.build_lifecycle_dashboard(trace_id="trace-001")

    def test_dashboard_contract_shape(self):
        dashboard = self._build()
        self.assertEqual(dashboard["contract_version"], "v1")
        self.assertEqual(dashboard["schema_version"], "portal-lifecycle-v1")
        self.assertEqual(dashboard["subject"], "ui.contract")
        self.assertEqual(dashboard["route"], "/portal/lifecycle")
        self.assertEqual(dashboard["trace_id"], "trace-001")
        self.assertEqual(
            [column["key"] for column in dashboard["layout"]["columns"]],
            ["lifecycle", "detail", "capabilities"],
        )

    def test_matrix_projection_into_states_and_capabilities(self):
        dashboard = self._build()
        self.assertEqual(sorted(dashboard["lifecycle_states"]), ["draft", "execution"])
        self.assertEqual(
            sorted(dashboard["capability_codes"]),
            ["cap.sc.boq", "cap.sc.pay", "cap.sc.plan"],
        )
        self.assertEqual(dashboard["matrix_meta"], {"version": "v1"})

    def test_sensitive_profile_redacted_by_default(self):
        dashboard = self._build()
        # login/db/user_id/role must NOT leak into customer-facing profile
        for forbidden in ("login", "db", "user_id", "role"):
            self.assertNotIn(forbidden, dashboard["profile"], msg=f"{forbidden} leaked into portal profile")
        self.assertEqual(dashboard["profile"]["name"], "portal.lifecycle_dashboard")

    def test_sensitive_profile_stays_redacted_when_flag_enabled_without_group(self):
        # flag on but user lacks internal group -> still redacted
        dashboard = self._build(params={"sc.portal.debug_profile": "1"})
        self.assertNotIn("login", dashboard["profile"])
