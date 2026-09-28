# -*- coding: utf-8 -*-
"""WEB-FIX-02 regression: mutation error classification + failure atomicity.

These are real-database tests. The rollback assertions read the table rows with
raw SQL *after* the handler returned and *before* the test teardown, so a
rollback that only happens because the test transaction ends cannot pass them.
"""

from unittest.mock import patch

from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase, tagged

from ..core.http_result_policy import result_http_status
from ..handlers.api_data import ApiDataHandler

MUTATION_TEST_TAG = "api_data_mutation_failure_atomicity"


@tagged("post_install", "-at_install", "smart_core", MUTATION_TEST_TAG)
class TestApiDataMutationFailureAtomicityOrm(TransactionCase):
    """Create/update must classify business failures and stay atomic."""

    def setUp(self):
        super().setUp()
        self.partner_model = self.env["res.partner"]
        self.partner_class = type(self.partner_model)
        self.handler = ApiDataHandler(env=self.env)

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _new_partner(self, name):
        return self.partner_model.create({"name": name})

    def _raw_partner_name(self, partner_id):
        """Read the persisted column, bypassing the ORM cache."""
        self.env.invalidate_all()
        self.env.cr.execute("SELECT name FROM res_partner WHERE id = %s", (partner_id,))
        row = self.env.cr.fetchone()
        return row[0] if row else None

    def _raw_partner_count(self, name):
        self.env.cr.execute("SELECT count(*) FROM res_partner WHERE name = %s", (name,))
        return self.env.cr.fetchone()[0]

    def _raw_category_count(self, name):
        # ``res.partner.category.name`` is a translated jsonb column, so match
        # the value under whichever language key the create wrote.
        self.env.cr.execute(
            "SELECT count(*) FROM res_partner_category c "
            "WHERE EXISTS (SELECT 1 FROM jsonb_each_text(c.name) kv WHERE kv.value = %s)",
            (name,),
        )
        return self.env.cr.fetchone()[0]

    def _write(self, partner_id, values):
        return self.handler._op_write(
            "res.partner", {"ids": [partner_id], "vals": values}, {}, False
        )

    def _create(self, values):
        return self.handler._op_create("res.partner", {"vals": values}, {}, False)

    # ------------------------------------------------------------------
    # classification
    # ------------------------------------------------------------------

    def test_write_business_validation_returns_identifiable_business_failure(self):
        partner = self._new_partner("WF02 validation original")

        def rejecting_write(records, vals):
            raise ValidationError("金额必须大于零")

        with patch.object(self.partner_class, "write", rejecting_write):
            result = self._write(partner.id, {"name": "WF02 validation blocked"})

        self.assertFalse(result["ok"])
        error = result["error"]
        self.assertEqual(error["reason_code"], "USER_ERROR")
        self.assertEqual(error["error_category"], "validation")
        self.assertEqual(error["suggested_action"], "fix_input")
        self.assertFalse(error["retryable"])
        self.assertEqual(error["message"], "金额必须大于零")
        # the HTTP status must stay in agreement with the envelope, not report 500
        self.assertEqual(result_http_status(result), 422)

    def test_create_business_validation_returns_identifiable_business_failure(self):
        def rejecting_create(records, vals):
            raise ValidationError("合同名称重复")

        with patch.object(self.partner_class, "create", rejecting_create):
            result = self._create({"name": "WF02 create blocked"})

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["reason_code"], "USER_ERROR")
        self.assertEqual(result["error"]["error_category"], "validation")
        self.assertEqual(result["error"]["message"], "合同名称重复")
        self.assertEqual(result_http_status(result), 422)

    def test_write_permission_denial_is_not_swallowed_by_business_classification(self):
        partner = self._new_partner("WF02 permission original")

        def denying_write(records, vals):
            raise AccessError("You are not allowed to modify 'Contact'.")

        with patch.object(self.partner_class, "write", denying_write):
            result = self._write(partner.id, {"name": "WF02 permission blocked"})

        self.assertFalse(result["ok"])
        error = result["error"]
        self.assertEqual(error["reason_code"], "PERMISSION_DENIED")
        self.assertEqual(error["error_category"], "permission")
        self.assertNotEqual(error["reason_code"], "USER_ERROR")
        self.assertEqual(result_http_status(result), 403)

    def test_create_permission_denial_is_not_swallowed_by_business_classification(self):
        def denying_create(records, vals):
            raise AccessError("You are not allowed to create 'Contact'.")

        with patch.object(self.partner_class, "create", denying_create):
            result = self._create({"name": "WF02 create denied"})

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["reason_code"], "PERMISSION_DENIED")
        self.assertEqual(result_http_status(result), 403)

    def test_write_unexpected_error_keeps_internal_diagnostics_out_of_the_envelope(self):
        partner = self._new_partner("WF02 unexpected original")
        leaked = (
            'psycopg2.errors.IntegrityError: DETAIL: relation "secret_table" does not exist '
            'at /home/odoo/workspace/sce-backend-odoo/x.py", line 12'
        )

        def exploding_write(records, vals):
            raise RuntimeError(leaked)

        with patch.object(self.partner_class, "write", exploding_write):
            result = self._write(partner.id, {"name": "WF02 unexpected blocked"})

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["reason_code"], "INTERNAL_ERROR")
        self.assertEqual(result_http_status(result), 500)
        message = result["error"]["message"]
        for fragment in ("psycopg2", "DETAIL", "secret_table", "/home/odoo", "Traceback"):
            self.assertNotIn(fragment, message)

    def test_create_unexpected_error_keeps_internal_diagnostics_out_of_the_envelope(self):
        def exploding_create(records, vals):
            raise RuntimeError('Traceback ... relation "secret_table" does not exist')

        with patch.object(self.partner_class, "create", exploding_create):
            result = self._create({"name": "WF02 create unexpected"})

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["reason_code"], "INTERNAL_ERROR")
        self.assertEqual(result_http_status(result), 500)
        self.assertNotIn("secret_table", result["error"]["message"])

    # ------------------------------------------------------------------
    # success paths
    # ------------------------------------------------------------------

    def test_write_success_commits_and_reads_back(self):
        partner = self._new_partner("WF02 success original")

        data, meta = self._write(partner.id, {"name": "WF02 success updated"})

        self.assertEqual(data["ids"], [partner.id])
        self.assertEqual(meta["op"], "write")
        self.assertEqual(self._raw_partner_name(partner.id), "WF02 success updated")

    def test_create_success_commits_and_reads_back(self):
        data, meta = self._create({"name": "WF02 created ok"})

        self.assertEqual(meta["op"], "create")
        self.assertEqual(self._raw_partner_count("WF02 created ok"), 1)

    # ------------------------------------------------------------------
    # failure atomicity
    # ------------------------------------------------------------------

    def test_failed_write_rolls_back_primary_and_related_rows(self):
        partner = self._new_partner("WF02 atomic original")
        related_name = "WF02 atomic related"
        original_write = self.partner_class.write

        def partial_then_reject(records, vals):
            # a real primary-row write ...
            original_write(records, vals)
            # ... plus a related row in the same logical operation
            self.env["res.partner.category"].create({"name": related_name})
            raise ValidationError("业务规则拒绝：不允许该修改")

        with patch.object(self.partner_class, "write", partial_then_reject):
            result = self._write(partner.id, {"name": "WF02 atomic blocked"})

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["reason_code"], "USER_ERROR")
        # asserted after the handler returned, before teardown: nothing may remain
        self.assertEqual(self._raw_partner_name(partner.id), "WF02 atomic original")
        self.assertEqual(self._raw_category_count(related_name), 0)

    def test_failed_create_rolls_back_primary_and_related_rows(self):
        primary_name = "WF02 create atomic blocked"
        related_name = "WF02 create atomic related"
        original_create = self.partner_class.create

        def partial_then_reject(records, vals):
            original_create(records, vals)
            self.env["res.partner.category"].create({"name": related_name})
            raise ValidationError("业务规则拒绝：不允许该创建")

        with patch.object(self.partner_class, "create", partial_then_reject):
            result = self._create({"name": primary_name})

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["reason_code"], "USER_ERROR")
        self.assertEqual(self._raw_partner_count(primary_name), 0)
        self.assertEqual(self._raw_category_count(related_name), 0)

    def test_failed_write_can_be_corrected_and_retried_to_success(self):
        partner = self._new_partner("WF02 retry original")
        original_write = self.partner_class.write
        state = {"reject": True}

        def reject_once(records, vals):
            if state["reject"]:
                raise ValidationError("金额必须大于零")
            return original_write(records, vals)

        with patch.object(self.partner_class, "write", reject_once):
            rejected = self._write(partner.id, {"name": "WF02 retry corrected"})
            self.assertFalse(rejected["ok"])
            self.assertEqual(self._raw_partner_name(partner.id), "WF02 retry original")

            state["reject"] = False
            accepted = self._write(partner.id, {"name": "WF02 retry corrected"})

        self.assertEqual(accepted[0]["ids"], [partner.id])
        self.assertEqual(self._raw_partner_name(partner.id), "WF02 retry corrected")

    def test_failed_create_can_be_corrected_and_retried_to_success(self):
        state = {"reject": True}
        original_create = self.partner_class.create

        def reject_once(records, vals):
            if state["reject"]:
                raise ValidationError("名称不合法")
            return original_create(records, vals)

        with patch.object(self.partner_class, "create", reject_once):
            rejected = self._create({"name": "WF02 create retry"})
            self.assertFalse(rejected["ok"])
            self.assertEqual(self._raw_partner_count("WF02 create retry"), 0)

            state["reject"] = False
            accepted = self._create({"name": "WF02 create retry"})

        self.assertEqual(accepted[1]["op"], "create")
        self.assertEqual(self._raw_partner_count("WF02 create retry"), 1)
