# -*- coding: utf-8 -*-
import threading
import uuid

from psycopg2.errors import SerializationFailure

from odoo import SUPERUSER_ID, api
from odoo.exceptions import UserError, ValidationError
from odoo.modules.registry import Registry
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "sc_gate", "cost_fact_concurrency_v2")
class TestCostFactConcurrencyV2(TransactionCase):
    """Exercise source-header serialization with independent DB transactions."""

    def _environment(self):
        registry = Registry(self.env.cr.dbname)
        cursor = registry.cursor()
        return cursor, api.Environment(cursor, SUPERUSER_ID, {})

    def _values(self, env, source_id, amount):
        project = env["project.project"].search(
            [("company_id", "!=", False)], order="id", limit=1
        )
        cost_code = env["project.cost.code"].search([], order="id", limit=1)
        self.assertTrue(project, "governed local.dev fixture must provide a company project")
        self.assertTrue(cost_code, "governed local.dev fixture must provide a cost code")
        return {
            "project_id": project.id,
            "cost_code_id": cost_code.id,
            "date": "2026-09-02",
            "source_amount": amount,
            "source_currency_id": project.company_id.currency_id.id,
            "source_model": "account.move.line",
            "source_id": source_id,
            "source_line_id": source_id,
            "note": "并发事实序列化测试",
        }

    def _run_transaction(self, operation, errors, started, finished):
        try:
            for attempt in range(2):
                cursor = None
                try:
                    cursor, env = self._environment()
                    started.set()
                    operation(env)
                    cursor.commit()
                    return
                except SerializationFailure:
                    if cursor:
                        cursor.rollback()
                    if attempt:
                        raise
                finally:
                    if cursor:
                        cursor.close()
        except Exception as exc:  # pragma: no cover - surfaced by the parent assertion
            errors.append(exc)
        finally:
            finished.set()

    def test_withdraw_and_replay_share_transaction_order(self):
        source_id = uuid.uuid4().int % 900_000_000 + 100_000_000
        setup_cursor, setup_env = self._environment()
        try:
            values = self._values(setup_env, source_id, 100.0)
            setup_env["project.cost.ledger"]._upsert_generated_cost_rows([values])
            setup_cursor.commit()
        finally:
            setup_cursor.close()

        errors = []
        started = threading.Event()
        finished = threading.Event()
        first_cursor, first_env = self._environment()
        try:
            ledger = first_env["project.cost.ledger"]
            ledger._lock_generated_source_headers([("account.move.line", source_id)])
            thread = threading.Thread(
                target=self._run_transaction,
                args=(
                    lambda env: env["project.cost.ledger"]._upsert_generated_cost_rows(
                        [{**self._values(env, source_id, 200.0), "recognition_state": "active"}]
                    ),
                    errors,
                    started,
                    finished,
                ),
            )
            thread.start()
            self.assertTrue(started.wait(5))
            self.assertFalse(finished.wait(0.2), "replay must wait for the withdrawal lock")
            ledger._withdraw_generated_cost_rows("account.move.line", [source_id])
            first_cursor.commit()
            thread.join(10)
            self.assertFalse(thread.is_alive())
            self.assertFalse(errors)
        finally:
            first_cursor.close()

        verify_cursor, verify_env = self._environment()
        try:
            row = verify_env["project.cost.ledger"].search([
                ("source_model", "=", "account.move.line"),
                ("source_id", "=", source_id),
            ])
            self.assertEqual(row.recognition_state, "active")
            self.assertEqual(row.source_amount, 200.0)
            row.with_context(
                sc_cost_generated_service=row._GENERATED_SERVICE_TOKEN
            ).unlink()
            verify_cursor.commit()
        finally:
            verify_cursor.close()

    def test_receipt_correction_and_supplier_return_use_latest_origin_fact(self):
        setup_cursor, setup_env = self._environment()
        try:
            project = setup_env["project.project"].search(
                [("company_id", "!=", False)], order="id", limit=1
            )
            cost_code = setup_env["project.cost.code"].search([], order="id", limit=1)
            picking_type = setup_env["stock.picking.type"].search(
                [("code", "=", "incoming"), ("company_id", "=", project.company_id.id)],
                limit=1,
            )
            supplier = setup_env["stock.location"].search([("usage", "=", "supplier")], limit=1)
            internal = picking_type.default_location_dest_id
            product = setup_env["product.product"].create({
                "name": "并发退货事实材料 " + uuid.uuid4().hex[:8],
                "type": "consu",
                "default_cost_code_id": cost_code.id,
            })
            receipt = setup_env["stock.picking"].create({
                "picking_type_id": picking_type.id,
                "location_id": supplier.id,
                "location_dest_id": internal.id,
            })
            receipt_move = setup_env["stock.move"].create({
                "name": product.name,
                "product_id": product.id,
                "product_uom_qty": 5,
                "quantity": 5,
                "product_uom": product.uom_id.id,
                "picking_id": receipt.id,
                "location_id": supplier.id,
                "location_dest_id": internal.id,
                "project_id": project.id,
                "cost_code_id": cost_code.id,
            })
            return_type = picking_type.return_picking_type_id
            return_picking = setup_env["stock.picking"].create({
                "picking_type_id": return_type.id,
                "location_id": internal.id,
                "location_dest_id": supplier.id,
            })
            return_move = setup_env["stock.move"].create({
                "name": product.name + " supplier return",
                "product_id": product.id,
                "product_uom_qty": 2,
                "quantity": 2,
                "product_uom": product.uom_id.id,
                "picking_id": return_picking.id,
                "location_id": internal.id,
                "location_dest_id": supplier.id,
                "origin_returned_move_id": receipt_move.id,
            })
            origin_values = {
                **self._values(setup_env, receipt_move.id, 100.0),
                "source_model": "stock.move",
                "source_line_id": receipt_move.id,
                "qty": 5,
                "uom_id": product.uom_id.id,
                "cost_code_id": cost_code.id,
                "project_id": project.id,
            }
            setup_env["project.cost.ledger"]._upsert_generated_cost_rows([origin_values])
            setup_cursor.commit()
            ids = (receipt.id, receipt_move.id, return_picking.id, return_move.id, product.id)
        finally:
            setup_cursor.close()

        errors = []
        started = threading.Event()
        finished = threading.Event()
        first_cursor, first_env = self._environment()
        try:
            ledger = first_env["project.cost.ledger"]
            ledger._lock_generated_source_headers([("stock.move", ids[1])])
            ledger._upsert_generated_cost_rows([
                {
                    **self._values(first_env, ids[1], 200.0),
                    "source_model": "stock.move",
                    "source_line_id": ids[1],
                    "qty": 5,
                    "uom_id": first_env["product.product"].browse(ids[4]).uom_id.id,
                }
            ])
            thread = threading.Thread(
                target=self._run_transaction,
                args=(
                    lambda env: env["stock.picking"].browse(ids[2])._create_cost_ledger_from_moves(),
                    errors,
                    started,
                    finished,
                ),
            )
            thread.start()
            self.assertTrue(started.wait(5))
            self.assertFalse(finished.wait(0.2), "supplier return must wait for origin correction")
            first_cursor.commit()
            thread.join(10)
            self.assertFalse(thread.is_alive())
            self.assertFalse(errors)
        finally:
            first_cursor.close()

        verify_cursor, verify_env = self._environment()
        try:
            facts = verify_env["project.cost.ledger"].search([
                ("source_model", "=", "stock.move"),
                ("source_id", "in", [ids[1], ids[3]]),
            ])
            return_fact = facts.filtered(lambda fact: fact.source_id == ids[3])
            self.assertEqual(return_fact.source_amount, -80.0)
            facts.with_context(sc_cost_generated_service=facts._GENERATED_SERVICE_TOKEN).unlink()
            verify_env["stock.move"].browse([ids[3], ids[1]]).unlink()
            verify_env["stock.picking"].browse([ids[2], ids[0]]).unlink()
            verify_env["product.product"].browse(ids[4]).unlink()
            verify_cursor.commit()
        finally:
            verify_cursor.close()

    def test_period_lock_waits_for_fact_boundary_and_rejects_late_write(self):
        setup_source_id = uuid.uuid4().int % 900_000_000 + 100_000_000
        blocked_source_id = uuid.uuid4().int % 900_000_000 + 100_000_000
        setup_cursor, setup_env = self._environment()
        try:
            project = setup_env["project.project"].create({
                "name": "并发期间锁项目 " + uuid.uuid4().hex[:8],
                "company_id": setup_env.company.id,
            })
            cost_code = setup_env["project.cost.code"].search([], order="id", limit=1)
            values = {
                "project_id": project.id,
                "cost_code_id": cost_code.id,
                "date": "2099-12-15",
                "source_amount": 10.0,
                "source_currency_id": project.company_id.currency_id.id,
                "source_model": "account.move.line",
                "source_id": setup_source_id,
                "source_line_id": setup_source_id,
                "note": "并发期间锁测试",
            }
            fact = setup_env["project.cost.ledger"]._upsert_generated_cost_rows([values])
            period_id = fact.period_id.id
            project_id = project.id
            setup_cursor.commit()
        finally:
            setup_cursor.close()

        errors = []
        blocked = []
        started = threading.Event()
        finished = threading.Event()
        first_cursor, first_env = self._environment()
        try:
            period = first_env["project.cost.period"].browse(period_id)
            period.action_lock_period(reason="并发期间锁测试")

            def attempt_late_fact(env):
                try:
                    env["project.cost.ledger"]._upsert_generated_cost_rows([{
                        **values,
                        "source_amount": 20.0,
                        "source_id": blocked_source_id,
                        "source_line_id": blocked_source_id,
                        "date": "2099-12-15",
                    }])
                except UserError:
                    blocked.append(True)

            thread = threading.Thread(
                target=self._run_transaction,
                args=(attempt_late_fact, errors, started, finished),
            )
            thread.start()
            self.assertTrue(started.wait(5))
            self.assertFalse(finished.wait(0.2), "fact write must wait for the period row")
            first_cursor.commit()
            thread.join(10)
            self.assertFalse(thread.is_alive())
            self.assertFalse(errors)
            self.assertEqual(blocked, [True])
        finally:
            first_cursor.close()

        cleanup_cursor, cleanup_env = self._environment()
        try:
            period = cleanup_env["project.cost.period"].browse(period_id)
            period.write({
                "locked": False,
                "locked_by": False,
                "locked_at": False,
                "lock_reason": False,
            })
            facts = cleanup_env["project.cost.ledger"].search([
                ("source_model", "=", "account.move.line"),
                ("source_id", "in", [setup_source_id, blocked_source_id]),
            ])
            self.assertEqual(facts.mapped("source_id"), [setup_source_id])
            facts.with_context(sc_cost_generated_service=facts._GENERATED_SERVICE_TOKEN).unlink()
            cleanup_env["sc.audit.log"].search([
                ("model", "=", "project.cost.period"), ("res_id", "=", period_id)
            ]).unlink()
            period.unlink()
            cleanup_env["project.project"].browse(project_id).unlink()
            cleanup_cursor.commit()
        finally:
            cleanup_cursor.close()

    def test_concurrent_project_returns_conserve_original_issue_quantity(self):
        setup_cursor, setup_env = self._environment()
        try:
            project = setup_env["project.project"].search(
                [("company_id", "!=", False)], order="id", limit=1
            )
            warehouse = setup_env["stock.warehouse"].search(
                [("company_id", "=", project.company_id.id)], limit=1
            )
            product = setup_env["product.product"].create({
                "name": "并发项目退库材料 " + uuid.uuid4().hex[:8],
                "type": "consu",
                "purchase_line_warn": "no-message",
            })

            def outbound(name, outbound_type, qty, origin_line_id=False):
                return setup_env["sc.material.outbound"].create({
                    "name": name,
                    "outbound_type": outbound_type,
                    "project_id": project.id,
                    "warehouse_id": warehouse.id,
                    "source_location_id": warehouse.lot_stock_id.id,
                    "currency_id": project.company_id.currency_id.id,
                    "line_ids": [(0, 0, {
                        "product_id": product.id,
                        "product_uom_id": product.uom_id.id,
                        "qty": qty,
                        "unit_price": 12,
                        "origin_issue_line_id": origin_line_id,
                    })],
                })

            issue = outbound("并发原领用", "issue", 5)
            issue.action_submit()
            issue.action_issue()
            first_return = outbound("并发退库一", "return", 3, issue.line_ids.id)
            second_return = outbound("并发退库二", "return", 3, issue.line_ids.id)
            first_return.action_submit()
            second_return.action_submit()
            ids = (issue.id, issue.line_ids.id, first_return.id, second_return.id, product.id)
            setup_cursor.commit()
        finally:
            setup_cursor.close()

        errors = []
        blocked = []
        started = threading.Event()
        finished = threading.Event()
        first_cursor, first_env = self._environment()
        try:
            first_env["sc.material.outbound"].browse(ids[2]).action_issue()

            def attempt_second_return(env):
                try:
                    env["sc.material.outbound"].browse(ids[3]).action_issue()
                except ValidationError:
                    blocked.append(True)

            thread = threading.Thread(
                target=self._run_transaction,
                args=(attempt_second_return, errors, started, finished),
            )
            thread.start()
            self.assertTrue(started.wait(5))
            self.assertFalse(finished.wait(0.2), "second return must wait for the origin issue row")
            first_cursor.commit()
            thread.join(10)
            self.assertFalse(thread.is_alive())
            self.assertFalse(errors)
            self.assertEqual(blocked, [True])
        finally:
            first_cursor.close()

        cleanup_cursor, cleanup_env = self._environment()
        try:
            origin = cleanup_env["sc.material.outbound.line"].browse(ids[1])
            self.assertEqual(origin.returned_qty, 3)
            returns = cleanup_env["sc.material.outbound"].browse([ids[2], ids[3]])
            self.assertEqual(returns.mapped("state"), ["issued", "submitted"])
            facts = cleanup_env["project.cost.ledger"].search([
                ("source_model", "=", "sc.material.outbound"),
                ("source_id", "in", [ids[0], ids[2], ids[3]]),
            ])
            self.assertEqual(set(facts.mapped("source_id")), {ids[0], ids[2]})
            facts.with_context(sc_cost_generated_service=facts._GENERATED_SERVICE_TOKEN).unlink()
            documents = cleanup_env["sc.material.outbound"].browse([ids[3], ids[2], ids[0]])
            documents._write_cost_source_state({"state": "cancel"})
            documents.unlink()
            cleanup_env["product.product"].browse(ids[4]).unlink()
            cleanup_cursor.commit()
        finally:
            cleanup_cursor.close()
