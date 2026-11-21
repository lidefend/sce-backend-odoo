"""Post-RT readback: temporary HTTP/browser support must leave no durable state."""
from odoo.tests.common import TransactionCase, tagged

from .test_native_advisory_draft import CONTENT, MODEL
from ..models.support.team_loan_deduction_workspace import _PROCESSING_ADVISORY_FEEDBACK, _PROCESSING_ADVISORY_REVIEW


@tagged("post_install", "-at_install", "feedback_evaluation_rt_restore")
class TestFeedbackEvaluationRtRestore(TransactionCase):
    def test_temporary_rt_state_is_absent(self):
        self.assertFalse(self.env["res.users"].search([
            ("login", "in", ["r6_3_rt_http_operator", "r6_3_rt_http_denied"]),
        ]))
        namespace = self.env["sc.platform.namespace"].sudo().resolve_alias("demo")
        self.assertEqual(namespace, self.env.ref("smart_core.namespace_demo"))
        self.assertEqual(namespace.database_name, "sc_demo")
        self.assertEqual(namespace.lifecycle_state, "active")
        self.assertFalse(self.env["sc.platform.namespace.alias"].sudo().search([
            ("alias", "=", "r6-3-rt"),
        ]))
        field = self.env[MODEL]._fields[CONTENT]
        self.assertEqual(field.sc_feedback_usage, _PROCESSING_ADVISORY_FEEDBACK)
        self.assertEqual(type(self.env[MODEL])._compute_processing_advisory._sc_feedback_evaluation_review,
                         _PROCESSING_ADVISORY_REVIEW)
        self.assertEqual(self.env[MODEL].search_count([]), 0)
