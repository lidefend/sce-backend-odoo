# -*- coding: utf-8 -*-
import threading
import uuid

from psycopg2.errors import SerializationFailure

from odoo import SUPERUSER_ID, api
from lxml import etree

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.modules.registry import Registry
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "p1_settlement_fact_immutability_v1")
class TestSettlementFactImmutabilityV1(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.project = cls.env["project.project"].create(
            {"name": "Settlement fact authority project", "company_id": cls.company.id}
        )
        cls.partner = cls.env["res.partner"].create(
            {"name": "Settlement fact authority partner"}
        )
        cls.contract = cls.env["construction.contract"].create(
            {
                "subject": "Settlement fact authority contract",
                "type": "in",
                "project_id": cls.project.id,
                "partner_id": cls.partner.id,
                "company_id": cls.company.id,
                "currency_id": cls.company.currency_id.id,
            }
        )
        cls.reader = cls._create_user(
            "settlement_fact_reader",
            "smart_construction_core.group_sc_cap_settlement_read",
        )
        cls.operator = cls._create_user(
            "settlement_fact_operator",
            "smart_construction_core.group_sc_cap_settlement_user",
        )
        cls.initiator = cls._create_user(
            "settlement_fact_initiator",
            "smart_construction_core.group_sc_cap_business_initiator",
        )
        cls.manager = cls._create_user(
            "settlement_fact_manager",
            "smart_construction_core.group_sc_cap_settlement_manager",
        )
        cls.project.message_subscribe(
            partner_ids=[
                cls.reader.partner_id.id,
                cls.operator.partner_id.id,
                cls.initiator.partner_id.id,
            ]
        )

    @classmethod
    def _create_user(cls, login, group_xmlid):
        return cls.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": login,
                "login": login,
                "email": "%s@example.invalid" % login,
                "company_id": cls.company.id,
                "company_ids": [(6, 0, [cls.company.id])],
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            cls.env.ref("base.group_user").id,
                            cls.env.ref(group_xmlid).id,
                        ],
                    )
                ],
            }
        )

    def _settlement(self, suffix="one"):
        settlement = self.env["sc.settlement.order"].create(
            {
                "name": "Settlement fact %s" % suffix,
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "settlement_unit_id": self.partner.id,
                "contract_id": self.contract.id,
                "company_id": self.company.id,
                "currency_id": self.company.currency_id.id,
                "settlement_type": "out",
            }
        )
        line = self.env["sc.settlement.order.line"].create(
            {
                "settlement_id": settlement.id,
                "contract_id": self.contract.id,
                "name": "Settlement line %s" % suffix,
                "qty": 2.0,
                "price_unit": 50.0,
            }
        )
        return settlement, line

    def _request(self, suffix, **extra):
        values = {
            "name": "Settlement payment %s" % suffix,
            "type": "pay",
            "project_id": self.project.id,
            "partner_id": self.partner.id,
            "contract_id": self.contract.id,
            "currency_id": self.company.currency_id.id,
            "amount": 10.0,
        }
        values.update(extra)
        return self.env["payment.request"].with_context(payment_soft_gate=True).create(
            values
        )

    def test_state_is_private_and_approved_fact_is_immutable(self):
        settlement, line = self._settlement()

        with self.assertRaises(AccessError):
            self.env["sc.settlement.order"].create(
                {
                    "name": "illegal approved create",
                    "project_id": self.project.id,
                    "partner_id": self.partner.id,
                    "company_id": self.company.id,
                    "currency_id": self.company.currency_id.id,
                    "state": "approve",
                }
            )
        with self.assertRaises(AccessError):
            settlement.write({"state": "approve"})

        with self.assertRaises(AccessError):
            settlement._write_lifecycle({"state": "approve"})

        settlement._write_lifecycle("approve")
        self.assertEqual(settlement.state, "approve")
        self.assertEqual(settlement.amount_total, 100.0)

        for record, values in (
            (settlement, {"partner_id": self.env.company.partner_id.id}),
            (settlement, {"settlement_amount": 1.0}),
            (line, {"qty": 3.0}),
            (line, {"price_unit": 75.0}),
        ):
            with self.assertRaises(AccessError):
                record.write(values)

        with self.assertRaises(AccessError):
            self.env["sc.settlement.order.line"].create(
                {
                    "settlement_id": settlement.id,
                    "contract_id": self.contract.id,
                    "name": "late line",
                    "qty": 1.0,
                    "price_unit": 1.0,
                }
            )
        with self.assertRaises(AccessError):
            line.unlink()
        with self.assertRaises(AccessError):
            settlement.unlink()

        settlement.write({"note": "audit annotation"})
        self.assertEqual(settlement.note, "audit annotation")
        with self.assertRaises(AccessError):
            settlement.with_context(
                **{
                    settlement._LIFECYCLE_CONTEXT_KEY:
                        settlement._LIFECYCLE_SERVICE_TOKEN
                }
            ).write({"settlement_amount": 999.0})
        with self.assertRaises(AccessError):
            settlement._write_lifecycle("draft")

    def test_server_actions_enforce_real_settlement_roles(self):
        denied, _line = self._settlement("role-denied")
        for user in (self.reader, self.operator, self.initiator):
            with self.assertRaises(AccessError):
                denied.with_user(user).action_cancel()
            denied.invalidate_recordset(["state"])
            self.assertEqual(denied.state, "draft")

        denied.with_user(self.manager).action_cancel()
        denied.invalidate_recordset(["state"])
        self.assertEqual(denied.state, "cancel")

        submit_denied, _line = self._settlement("submit-role-denied")
        with self.assertRaises(AccessError):
            submit_denied.with_user(self.reader).action_submit()
        self.assertEqual(submit_denied.state, "draft")

        for user, suffix in (
            (self.operator, "operator-submit"),
            (self.initiator, "initiator-submit"),
        ):
            allowed, _line = self._settlement(suffix)
            allowed.with_user(user).action_submit()
            allowed.invalidate_recordset(["state"])
            self.assertEqual(allowed.state, "submit")

    def test_payment_line_uses_one_canonical_settlement_relation(self):
        settlement, settlement_line = self._settlement("canonical")
        other, other_line = self._settlement("canonical-other")

        request = self._request("canonical-line")
        line = self.env["payment.request.line"].create(
            {
                "request_id": request.id,
                "legacy_line_id": "canonical-line",
                "legacy_parent_id": "canonical-parent",
                "settlement_line_id": settlement_line.id,
                "contract_id": self.contract.id,
                "amount": 10.0,
                "current_pay_amount": 10.0,
            }
        )
        self.assertEqual(line.settlement_id, settlement)

        matching = self.env["payment.request.line"].create(
            {
                "request_id": request.id,
                "legacy_line_id": "canonical-match",
                "legacy_parent_id": "canonical-parent",
                "settlement_id": other.id,
                "settlement_line_id": other_line.id,
                "contract_id": self.contract.id,
                "amount": 1.0,
            }
        )
        self.assertEqual(matching.settlement_id, other)

        with self.assertRaises(ValidationError):
            self.env["payment.request.line"].create(
                {
                    "request_id": request.id,
                    "legacy_line_id": "canonical-conflict",
                    "legacy_parent_id": "canonical-parent",
                    "settlement_id": settlement.id,
                    "settlement_line_id": other_line.id,
                    "contract_id": self.contract.id,
                    "amount": 1.0,
                }
            )
        with self.assertRaises(ValidationError):
            line.write({"settlement_id": other.id})

        line_only_request = self._request("line-only")
        self.env["payment.request.line"].create(
            {
                "request_id": line_only_request.id,
                "legacy_line_id": "canonical-line-only",
                "legacy_parent_id": "canonical-line-only-parent",
                "settlement_line_id": settlement_line.id,
                "contract_id": self.contract.id,
                "amount": 5.0,
                "current_pay_amount": 5.0,
            }
        )
        line_only_request.action_submit()
        with self.assertRaises(UserError):
            settlement.action_cancel()

    def test_cancel_uses_sudo_visibility_and_is_batch_atomic(self):
        blocked, _line = self._settlement("hidden-payment")
        untouched, _line = self._settlement("batch-untouched")
        blocked._write_lifecycle("approve")
        request = self._request("hidden-payment", settlement_id=blocked.id)
        request.action_submit()

        with self.assertRaises(AccessError):
            self.env["payment.request"].with_user(self.manager).search_count(
                [("id", "=", request.id)]
            )
        with self.assertRaises(UserError):
            (untouched | blocked).with_user(self.manager).action_cancel()
        (untouched | blocked).invalidate_recordset(["state"])
        self.assertEqual(untouched.state, "draft")
        self.assertEqual(blocked.state, "approve")

    def test_batch_cancel_payment_query_count_is_constant(self):
        settlements = self.env["sc.settlement.order"]
        for index in range(50):
            settlement, _line = self._settlement("query-%s" % index)
            settlements |= settlement

        def query_count(records):
            start = self.env.cr.sql_log_count
            records._check_payments_before_cancel()
            return self.env.cr.sql_log_count - start

        one_count = query_count(settlements[:1])
        ten_count = query_count(settlements[:10])
        fifty_count = query_count(settlements)
        self.assertLessEqual(ten_count, one_count + 2)
        self.assertLessEqual(fifty_count, one_count + 2)

    def test_batch_line_create_has_bounded_query_growth(self):
        def create_lines(count, suffix):
            settlement = self.env["sc.settlement.order"].create(
                {
                    "name": "Settlement batch query %s" % suffix,
                    "project_id": self.project.id,
                    "partner_id": self.partner.id,
                    "settlement_unit_id": self.partner.id,
                    "contract_id": self.contract.id,
                    "company_id": self.company.id,
                    "currency_id": self.company.currency_id.id,
                    "settlement_type": "out",
                }
            )
            start = self.env.cr.sql_log_count
            self.env["sc.settlement.order.line"].create(
                [
                    {
                        "settlement_id": settlement.id,
                        "contract_id": self.contract.id,
                        "name": "Batch line %s-%s" % (suffix, index),
                        "qty": 1.0,
                        "price_unit": 1.0,
                    }
                    for index in range(count)
                ]
            )
            return self.env.cr.sql_log_count - start

        one_count = create_lines(1, "one")
        ten_count = create_lines(10, "ten")
        fifty_count = create_lines(50, "fifty")
        # One physical row write per new line is irreducible.  The bounded
        # overhead allowance proves that contract/parent validation adds no
        # additional per-line lookup on top of those writes.
        self.assertLessEqual(ten_count, one_count + 9 + 8)
        self.assertLessEqual(fifty_count, one_count + 49 + 8)

    def test_native_terminal_form_exposes_readonly_fact_and_annotations(self):
        arch = self.env["sc.settlement.order"].get_view(view_type="form")["arch"]
        root = etree.fromstring(arch.encode("utf-8"))
        for field_name in (
            "project_id",
            "contract_id",
            "partner_id",
            "settlement_amount",
            "line_ids",
            "settlement_description",
            "invoice_ref",
            "purchase_order_ids",
        ):
            nodes = root.xpath(".//field[@name='%s']" % field_name)
            self.assertTrue(nodes, field_name)
            self.assertTrue(
                any("approve" in (node.get("readonly") or "") for node in nodes),
                "%s must be readonly for terminal settlement states" % field_name,
            )
        self.assertTrue(root.xpath(".//field[@name='note' and not(@readonly)]"))
        self.assertTrue(
            root.xpath(".//field[@name='attachment_ids' and not(@readonly)]")
        )

    def test_controlled_done_transition_preserves_fact(self):
        settlement, line = self._settlement("done")
        settlement._write_lifecycle("approve")

        settlement.action_done()

        self.assertEqual(settlement.state, "done")
        self.assertEqual(settlement.amount_total, 100.0)
        with self.assertRaises(AccessError):
            line.unlink()

    def test_cancel_check_handles_recordsets_and_keeps_facts(self):
        first, first_line = self._settlement("cancel-one")
        second, second_line = self._settlement("cancel-two")

        (first | second).action_cancel()

        self.assertEqual(set((first | second).mapped("state")), {"cancel"})
        for record in (first, second, first_line, second_line):
            with self.assertRaises(AccessError):
                record.unlink()

    def test_submitted_payment_blocks_cancel_and_canceled_fact_blocks_submit(self):
        submitted_settlement, _line = self._settlement("submitted-payment")
        submitted_settlement._write_lifecycle("approve")
        submitted_request = self.env["payment.request"].with_context(
            payment_soft_gate=True
        ).create(
            {
                "name": "Submitted settlement payment",
                "type": "pay",
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "contract_id": self.contract.id,
                "settlement_id": submitted_settlement.id,
                "currency_id": self.company.currency_id.id,
                "amount": 10.0,
            }
        )
        submitted_request.action_submit()
        with self.assertRaises(UserError):
            submitted_settlement.action_cancel()

        legacy_settlement, _line = self._settlement("legacy-payment-line")
        legacy_settlement._write_lifecycle("approve")
        legacy_request = self.env["payment.request"].with_context(
            payment_soft_gate=True
        ).create(
            {
                "name": "Legacy settlement-line payment",
                "type": "pay",
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "contract_id": self.contract.id,
                "currency_id": self.company.currency_id.id,
                "amount": 10.0,
                "outflow_line_ids": [
                    (
                        0,
                        0,
                        {
                            "legacy_line_id": "legacy-settlement-line",
                            "legacy_parent_id": "legacy-settlement-parent",
                            "settlement_id": legacy_settlement.id,
                            "contract_id": self.contract.id,
                            "amount": 10.0,
                            "current_pay_amount": 10.0,
                        },
                    )
                ],
            }
        )
        legacy_request.action_submit()
        with self.assertRaises(UserError):
            legacy_settlement.action_cancel()

        canceled_settlement, _line = self._settlement("canceled-payment")
        canceled_settlement.action_cancel()
        canceled_request = self.env["payment.request"].with_context(
            payment_soft_gate=True
        ).create(
            {
                "name": "Canceled settlement payment",
                "type": "pay",
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "contract_id": self.contract.id,
                "settlement_id": canceled_settlement.id,
                "currency_id": self.company.currency_id.id,
                "amount": 10.0,
            }
        )
        with self.assertRaises(UserError):
            canceled_request.action_submit()


@tagged("post_install", "-at_install", "p1_settlement_fact_immutability_v1")
class TestSettlementFactConcurrencyV1(TransactionCase):
    def _committed_fixture(self, suffix, with_request=False):
        registry = Registry(self.env.cr.dbname)
        with registry.cursor() as cursor:
            env = api.Environment(
                cursor,
                SUPERUSER_ID,
                {
                    "tracking_disable": True,
                    "mail_create_nosubscribe": True,
                    "payment_soft_gate": True,
                },
            )
            token = uuid.uuid4().hex[:8]
            partner = env["res.partner"].create(
                {"name": "Settlement concurrency partner %s %s" % (suffix, token)}
            )
            project = env["project.project"].create(
                {
                    "name": "Settlement concurrency project %s %s" % (suffix, token),
                    "company_id": env.company.id,
                }
            )
            contract = env["construction.contract"].create(
                {
                    "subject": "Settlement concurrency contract %s %s" % (suffix, token),
                    "type": "in",
                    "project_id": project.id,
                    "partner_id": partner.id,
                    "company_id": env.company.id,
                    "currency_id": env.company.currency_id.id,
                }
            )
            settlement = env["sc.settlement.order"].create(
                {
                    "name": "Settlement concurrency %s %s" % (suffix, token),
                    "project_id": project.id,
                    "partner_id": partner.id,
                    "settlement_unit_id": partner.id,
                    "contract_id": contract.id,
                    "company_id": env.company.id,
                    "currency_id": env.company.currency_id.id,
                    "settlement_type": "out",
                }
            )
            line = env["sc.settlement.order.line"].create(
                {
                    "settlement_id": settlement.id,
                    "contract_id": contract.id,
                    "name": "Settlement concurrency line",
                    "qty": 1.0,
                    "price_unit": 100.0,
                }
            )
            request = env["payment.request"]
            if with_request:
                request = env["payment.request"].create(
                    {
                        "name": "Settlement concurrency payment %s" % token,
                        "type": "pay",
                        "project_id": project.id,
                        "partner_id": partner.id,
                        "contract_id": contract.id,
                        "settlement_id": settlement.id,
                        "currency_id": env.company.currency_id.id,
                        "amount": 10.0,
                    }
                )
            ids = {
                "partner": partner.id,
                "project": project.id,
                "contract": contract.id,
                "settlement": settlement.id,
                "line": line.id,
                "request": request.id or False,
            }
            cursor.commit()
        self.addCleanup(self._cleanup_committed_fixture, ids)
        return registry, ids

    def _cleanup_committed_fixture(self, ids):
        registry = Registry(self.env.cr.dbname)
        with registry.cursor() as cursor:
            env = api.Environment(cursor, SUPERUSER_ID, {"tracking_disable": True})
            if ids["request"]:
                cursor.execute(
                    "UPDATE payment_request SET state = 'cancel' WHERE id = %s",
                    [ids["request"]],
                )
                env["payment.request"].browse(ids["request"]).invalidate_recordset()
                env["payment.request"].browse(ids["request"]).unlink()
                env.invalidate_all(flush=False)
            cursor.execute(
                "UPDATE sc_settlement_order SET state = 'draft' WHERE id = %s",
                [ids["settlement"]],
            )
            env["sc.settlement.order"].browse(ids["settlement"]).invalidate_recordset()
            env["sc.settlement.order.line"].browse(ids["line"]).unlink()
            env.flush_all()
            env["sc.settlement.order"].browse(ids["settlement"]).unlink()
            env["construction.contract"].browse(ids["contract"]).unlink()
            env["project.project"].browse(ids["project"]).unlink()
            env["res.partner"].browse(ids["partner"]).unlink()
            cursor.commit()

    def test_line_write_waits_for_parent_approval_and_is_rejected(self):
        registry, ids = self._committed_fixture("line-lock")
        started = threading.Event()
        finished = threading.Event()
        outcomes = []

        def mutate_line():
            with registry.cursor() as cursor:
                started.set()
                for attempt in range(2):
                    env = api.Environment(cursor, SUPERUSER_ID, {})
                    try:
                        env["sc.settlement.order.line"].browse(ids["line"]).write(
                            {"qty": 2.0}
                        )
                        cursor.commit()
                        outcomes.append("written")
                        break
                    except SerializationFailure:
                        cursor.rollback()
                        if attempt:
                            outcomes.append("serialization_failed")
                    except AccessError:
                        cursor.rollback()
                        outcomes.append("rejected")
                        break
                finished.set()

        first_cursor = registry.cursor()
        try:
            first_env = api.Environment(first_cursor, SUPERUSER_ID, {})
            settlement = first_env["sc.settlement.order"].browse(ids["settlement"])
            settlement._lock_lifecycle_rows()
            worker = threading.Thread(target=mutate_line)
            worker.start()
            self.assertTrue(started.wait(5))
            self.assertFalse(finished.wait(0.2))
            settlement._write_lifecycle("approve")
            first_cursor.commit()
            worker.join(15)
            self.assertFalse(worker.is_alive())
            self.assertIn(outcomes, (["rejected"], ["serialization_failed"]))
        finally:
            first_cursor.close()

        with registry.cursor() as cursor:
            env = api.Environment(cursor, SUPERUSER_ID, {})
            line = env["sc.settlement.order.line"].browse(ids["line"])
            self.assertEqual(line.qty, 1.0)
            self.assertEqual(line.settlement_id.state, "approve")

    def test_payment_submit_and_settlement_cancel_have_one_winner(self):
        registry, ids = self._committed_fixture("submit-cancel", with_request=True)
        barrier = threading.Barrier(2)
        outcome_lock = threading.Lock()
        outcomes = []

        def run_action(action):
            outcome = "unexpected"
            for attempt in range(2):
                with registry.cursor() as cursor:
                    env = api.Environment(
                        cursor, SUPERUSER_ID, {"payment_soft_gate": True}
                    )
                    try:
                        barrier.wait(timeout=15) if attempt == 0 else None
                        if action == "submit":
                            env["payment.request"].browse(ids["request"]).action_submit()
                        else:
                            env["sc.settlement.order"].browse(
                                ids["settlement"]
                            ).action_cancel()
                        cursor.commit()
                        outcome = "%s_ok" % action
                        break
                    except SerializationFailure:
                        cursor.rollback()
                        if attempt:
                            outcome = "%s_serialization_failed" % action
                    except (AccessError, UserError, ValidationError):
                        cursor.rollback()
                        outcome = "%s_rejected" % action
                        break
            with outcome_lock:
                outcomes.append(outcome)

        threads = [
            threading.Thread(target=run_action, args=("submit",)),
            threading.Thread(target=run_action, args=("cancel",)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(30)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(len([row for row in outcomes if row.endswith("_ok")]), 1, outcomes)
        self.assertEqual(len(outcomes), 2, outcomes)

        with registry.cursor() as cursor:
            env = api.Environment(cursor, SUPERUSER_ID, {})
            request = env["payment.request"].browse(ids["request"])
            settlement = env["sc.settlement.order"].browse(ids["settlement"])
            self.assertFalse(
                request.state in ("submit", "approve", "approved", "done")
                and settlement.state == "cancel"
            )
