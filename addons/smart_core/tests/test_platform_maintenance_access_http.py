# -*- coding: utf-8 -*-
"""The maintenance-authorization flow is a product entry, not a shell substitute.

Owner ruling (2026-10-16): the authorization flow must be a product capability,
so the decision has to be reachable and auditable through an entry, not by
editing a row or by passing an approver name to a script. These cases drive the
HTTP entry and assert the guarantees the ruling names:

* the decider is the principal verified from the session, and a body that names
  an approver or a state is refused rather than silently ignored;
* a request authorizes nothing before an independent security administrator
  approves it;
* the ledger is not readable by an unrelated principal.

The state machine itself (target binding, validity window, append-only audit,
expiry sweep) is proven at the ORM layer
(``test_platform_database_governance_orm``); this file owns the transport.
"""

import json
import os
import uuid

from odoo import SUPERUSER_ID, api, fields
from odoo.modules.registry import Registry
from odoo.tests.common import HttpCase, tagged

SECRET = "platform-maintenance-access-test-signing-secret-2026-10-16-64bytes"
PASSWORD_PREFIX = "MaintenanceAccess"


@tagged("post_install", "-at_install", "platform_maintenance_access")
class TestPlatformMaintenanceAccessHttp(HttpCase):
    def setUp(self):
        super().setUp()
        suffix = uuid.uuid4().hex[:10]
        previous_secret = os.environ.get("SC_JWT_SECRET")
        os.environ["SC_JWT_SECRET"] = SECRET
        self.addCleanup(
            lambda: os.environ.pop("SC_JWT_SECRET", None)
            if previous_secret is None
            else os.environ.__setitem__("SC_JWT_SECRET", previous_secret)
        )
        registry = Registry(self.env.cr.dbname)
        with registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            env["ir.config_parameter"].sudo().set_param("sc.jwt.secret", SECRET)
            self.database_name = "sc_db_maintenance_access_http_%s" % suffix
            env["sc.platform.database.registration"]._register_database(
                db_name=self.database_name,
                environment_role="platform_internal_demo",
                data_purpose="demo",
            )
            company = env.ref("base.main_company")
            self.password = "%s-%s" % (PASSWORD_PREFIX, suffix)

            def account(prefix, groups):
                user = env["res.users"].sudo().create({
                    "name": "%s %s" % (prefix, suffix),
                    "login": "%s_%s" % (prefix, suffix),
                    "password": self.password,
                    "active": True,
                    "company_id": company.id,
                    "company_ids": [(6, 0, [company.id])],
                    "groups_id": [(6, 0, [env.ref(group).id for group in groups])],
                })
                return user.login

            # The requester may file a request but holds no decision authority.
            self.requester_login = account(
                "maint_requester", ["base.group_user", "smart_core.group_smart_core_admin"]
            )
            # The decider is the independent security administration identity.
            self.decider_login = account(
                "maint_decider",
                ["base.group_user", "smart_core.group_smart_core_security_admin"],
            )
            # One principal holding both roles: the independence rule, not the
            # entry's role gate, has to stop it approving its own request.
            self.both_login = account(
                "maint_both",
                [
                    "base.group_user",
                    "smart_core.group_smart_core_admin",
                    "smart_core.group_smart_core_security_admin",
                ],
            )
            self.outsider_login = account("maint_outsider", ["base.group_user"])
            cr.commit()
        self.ledger = self.env["sc.platform.maintenance.access"].sudo()

    # -- transport ---------------------------------------------------------
    def _json_response(self, response):
        body = response
        for _index in range(3):
            if isinstance(body, (bytes, str)):
                break
            if callable(getattr(body, "json", None)):
                parsed = body.json()
                if isinstance(parsed, dict):
                    return parsed
                body = parsed
            elif hasattr(body, "get_data"):
                body = body.get_data(as_text=True)
            elif hasattr(body, "content"):
                body = body.content
            elif hasattr(body, "text"):
                body = body.text
            elif hasattr(body, "data"):
                body = body.data
            elif hasattr(body, "read"):
                body = body.read()
            else:
                break
        if isinstance(body, bytes):
            body = body.decode("utf-8")
        if isinstance(body, dict):
            return body
        return json.loads(body or "{}")

    def _login(self, login):
        response = self.url_open(
            "/api/v1/intent?db=%s" % self.env.cr.dbname,
            data=json.dumps({
                "intent": "login",
                "params": {
                    "login": login,
                    "password": self.password,
                    "db": self.env.cr.dbname,
                    "contract_mode": "default",
                },
            }),
            headers={"Content-Type": "application/json", "X-Anonymous-Intent": "true"},
        )
        payload = self._json_response(response)
        session = (payload.get("data") or {}).get("session") or {}
        token = session.get("token")
        self.assertTrue(token, "login issued no token: %s" % payload)
        return token

    def _call(self, path, token=None, payload=None, *, method="POST", trace_id=None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = "Bearer %s" % token
        if trace_id:
            headers["X-Trace-Id"] = trace_id
        if method == "GET":
            return self._json_response(self.url_open(path, headers=headers))
        return self._json_response(
            self.url_open(path, data=json.dumps(payload or {}), headers=headers)
        )

    def _request(self, token, **overrides):
        body = {
            "db_name": self.database_name,
            "capability": "migrate",
            "reason": "HTTP entry acceptance for the maintenance authorization flow",
            "operator_identity_key": "smart_core.svc_tenant_payload_operator_http",
            "subject_checksum": "a" * 64,
            "authorized_operations": ["provision", "grant"],
        }
        body.update(overrides)
        return self._call("/api/ops/maintenance/access/request", token, body)

    def _access_id(self, response):
        self.assertTrue(response.get("ok"), response)
        return response["data"]["access"]["access_id"]

    def _approved_covering_access(self):
        """The projection a governed executor reads; None until approval."""
        return self.ledger._approved_access_projection(
            db_name=self.database_name, capability="migrate"
        )

    # -- cases -------------------------------------------------------------
    def test_the_flow_is_served_by_the_product_entry(self):
        requester = self._login(self.requester_login)
        decider = self._login(self.decider_login)

        opened = self._request(requester)
        self.assertTrue(opened.get("ok"), opened)
        access = opened["data"]["access"]
        self.assertEqual(access["state"], "requested")
        self.assertEqual(access["requested_by"], self.requester_login)
        self.assertEqual(access["approved_by"], "")
        self.assertEqual(access["authorized_operations"], ["provision", "grant"])
        self.assertEqual(opened["data"]["principal_login"], self.requester_login)
        # A request is not an authorization: nothing may consume it yet.
        self.assertIsNone(self._approved_covering_access())

        listed = self._call(
            "/api/ops/maintenance/access?db_name=%s" % self.database_name,
            requester,
            method="GET",
        )
        self.assertTrue(listed.get("ok"), listed)
        self.assertEqual(
            [row["access_id"] for row in listed["data"]["accesses"]], [access["access_id"]]
        )

        approved = self._call(
            "/api/ops/maintenance/access/approve", decider, {"access_id": access["access_id"]}
        )
        self.assertTrue(approved.get("ok"), approved)
        self.assertEqual(approved["data"]["access"]["state"], "approved")
        self.assertEqual(approved["data"]["access"]["approved_by"], self.decider_login)
        self.assertEqual(approved["data"]["principal_login"], self.decider_login)

        covering = self._approved_covering_access()
        self.assertTrue(covering, "the approved access must cover the capability")
        self.assertEqual(covering["access_id"], access["access_id"])
        self.assertEqual(covering["requested_by"], self.requester_login)
        self.assertEqual(covering["approved_by"], self.decider_login)
        self.assertFalse(covering["grants_business_data_scope"])

    def test_the_envelope_projects_the_request_trace_identity(self):
        requester = self._login(self.requester_login)
        trace_id = "http-entry-trace-%s" % uuid.uuid4().hex[:8]
        listed = self._call(
            "/api/ops/maintenance/access?db_name=%s" % self.database_name,
            requester,
            method="GET",
            trace_id=trace_id,
        )
        self.assertTrue(listed.get("ok"), listed)
        self.assertEqual(listed["trace_id"], trace_id)

        refused = self._call(
            "/api/ops/maintenance/access/approve", requester, {"access_id": 0}, trace_id=trace_id
        )
        self.assertFalse(refused.get("ok"), refused)
        self.assertEqual(refused["trace_id"], trace_id)
        self.assertEqual(refused["error"]["trace_id"], trace_id)

    def test_a_decider_cannot_supply_a_server_owned_decision_field(self):
        # The decider holds the role, so the refusal cannot come from the role
        # gate: it has to come from the body being refused.
        requester = self._login(self.requester_login)
        decider = self._login(self.decider_login)
        access_id = self._access_id(self._request(requester))
        for field in (
            "approved_by",
            "approved_by_id",
            "requested_by",
            "requested_by_id",
            "state",
            "valid_from",
            "valid_until",
        ):
            with self.subTest(field=field):
                refused = self._call(
                    "/api/ops/maintenance/access/approve",
                    decider,
                    {"access_id": access_id, field: self.requester_login},
                )
                self.assertFalse(refused.get("ok"), refused)
                self.assertEqual(refused["error"]["code"], "MAINTENANCE_ACCESS_SERVER_OWNED_FIELD")
                self.assertIn(field, refused["error"]["message"])
        # The refusals are refusals, not silent writes.
        self.assertEqual(self.ledger.browse(access_id).state, "requested")
        self.assertIsNone(self._approved_covering_access())

    def test_an_approver_without_the_role_is_refused(self):
        requester = self._login(self.requester_login)
        access_id = self._access_id(self._request(requester))
        refused = self._call(
            "/api/ops/maintenance/access/approve", requester, {"access_id": access_id}
        )
        self.assertFalse(refused.get("ok"), refused)
        self.assertEqual(refused["error"]["code"], "PERMISSION_DENIED")
        self.assertEqual(self.ledger.browse(access_id).state, "requested")

    def test_a_requester_may_not_approve_its_own_request(self):
        both = self._login(self.both_login)
        access_id = self._access_id(self._request(both))
        refused = self._call(
            "/api/ops/maintenance/access/approve", both, {"access_id": access_id}
        )
        self.assertFalse(refused.get("ok"), refused)
        self.assertIn("INDEPENDENT", refused["error"]["message"])
        self.assertEqual(self.ledger.browse(access_id).state, "requested")
        self.assertIsNone(self._approved_covering_access())

    def test_the_ledger_is_not_readable_by_an_ordinary_principal(self):
        requester = self._login(self.requester_login)
        self._request(requester)
        outsider = self._login(self.outsider_login)
        refused = self._call("/api/ops/maintenance/access", outsider, method="GET")
        self.assertFalse(refused.get("ok"), refused)
        self.assertEqual(refused["error"]["code"], "PERMISSION_DENIED")

    def test_an_unauthenticated_caller_is_refused(self):
        refused = self._call("/api/ops/maintenance/access", None, method="GET")
        self.assertFalse(refused.get("ok"), refused)
        self.assertEqual(refused["error"]["code"], "PERMISSION_DENIED")

    def test_a_migrate_request_must_name_the_operation_set(self):
        requester = self._login(self.requester_login)
        for operations, code in (
            (None, "DATABASE_GOVERNANCE_MAINTENANCE_OPERATIONS_REQUIRED"),
            ([], "DATABASE_GOVERNANCE_MAINTENANCE_OPERATIONS_REQUIRED"),
            (["import"], "DATABASE_GOVERNANCE_UNKNOWN_MAINTENANCE_OPERATION"),
        ):
            with self.subTest(operations=operations):
                refused = self._request(requester, authorized_operations=operations)
                self.assertFalse(refused.get("ok"), refused)
                self.assertEqual(refused["error"]["code"], code)

    def test_rejection_is_decided_by_the_independent_identity(self):
        requester = self._login(self.requester_login)
        decider = self._login(self.decider_login)
        access_id = self._access_id(self._request(requester))

        refused = self._call(
            "/api/ops/maintenance/access/reject",
            requester,
            {"access_id": access_id, "note": "requesting principal is not the decider"},
        )
        self.assertFalse(refused.get("ok"), refused)
        self.assertEqual(refused["error"]["code"], "PERMISSION_DENIED")
        self.assertEqual(self.ledger.browse(access_id).state, "requested")

        rejected = self._call(
            "/api/ops/maintenance/access/reject",
            decider,
            {"access_id": access_id, "note": "no maintenance window agreed"},
        )
        self.assertTrue(rejected.get("ok"), rejected)
        self.assertEqual(rejected["data"]["access"]["state"], "rejected")
        self.assertEqual(rejected["data"]["access"]["decision_note"], "no maintenance window agreed")
        self.assertIsNone(self._approved_covering_access())

    def test_an_approval_can_be_revoked_before_it_is_consumed(self):
        requester = self._login(self.requester_login)
        decider = self._login(self.decider_login)
        access_id = self._access_id(self._request(requester))
        self._call("/api/ops/maintenance/access/approve", decider, {"access_id": access_id})
        self.assertTrue(self._approved_covering_access())

        revoked = self._call(
            "/api/ops/maintenance/access/revoke",
            decider,
            {"access_id": access_id, "note": "window withdrawn"},
        )
        self.assertTrue(revoked.get("ok"), revoked)
        self.assertEqual(revoked["data"]["access"]["state"], "revoked")
        self.assertIsNone(self._approved_covering_access())

    def test_the_expiry_entry_is_reserved_for_the_security_admin(self):
        requester = self._login(self.requester_login)
        refused = self._call(
            "/api/ops/maintenance/access/expire", requester, {"db_name": self.database_name}
        )
        self.assertFalse(refused.get("ok"), refused)
        self.assertEqual(refused["error"]["code"], "PERMISSION_DENIED")

        decider = self._login(self.decider_login)
        swept = self._call(
            "/api/ops/maintenance/access/expire", decider, {"db_name": self.database_name}
        )
        self.assertTrue(swept.get("ok"), swept)
        self.assertEqual(swept["data"]["count"], 0)

        # An elapsed approval already authorizes nothing; the sweep only retires
        # the row so it stops *reading* as an approval, and it is idempotent.
        access_id = self._access_id(self._request(requester))
        self._call("/api/ops/maintenance/access/approve", decider, {"access_id": access_id})
        self.ledger.browse(access_id)._super_write({
            "valid_until": fields.Datetime.subtract(fields.Datetime.now(), hours=1)
        })
        self.assertIsNone(self._approved_covering_access())
        elapsed = self._call(
            "/api/ops/maintenance/access/expire", decider, {"db_name": self.database_name}
        )
        self.assertTrue(elapsed.get("ok"), elapsed)
        self.assertEqual(elapsed["data"]["count"], 1)
        self.assertEqual(self.ledger.browse(access_id).state, "expired")
        replay = self._call(
            "/api/ops/maintenance/access/expire", decider, {"db_name": self.database_name}
        )
        self.assertTrue(replay.get("ok"), replay)
        self.assertEqual(replay["data"]["count"], 0)

    def test_a_decided_request_is_not_decidable_again(self):
        requester = self._login(self.requester_login)
        decider = self._login(self.decider_login)
        access_id = self._access_id(self._request(requester))
        self._call("/api/ops/maintenance/access/approve", decider, {"access_id": access_id})

        replay = self._call("/api/ops/maintenance/access/approve", decider, {"access_id": access_id})
        self.assertFalse(replay.get("ok"), replay)
        self.assertIn("NOT_REQUESTED", replay["error"]["message"])
        self.assertEqual(self.ledger.browse(access_id).state, "approved")
