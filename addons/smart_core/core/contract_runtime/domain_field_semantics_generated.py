# -*- coding: utf-8 -*-
"""GENERATED CONTRACT-RUNTIME CARRIER - do not edit by hand.

Derived from: contracts/generated/product_view_structure_contract.json, the
governed parse of the Odoo model metadata and the resolved view arch, restricted
to the entities ``contracts/domain/*.yaml`` declares.
Regenerate with:

    python3 scripts/contract/generate_semantic_registry.py

The runtime image does not ship ``contracts/``, so each governed entity's field
semantics are projected here as ``model -> field -> semantic``.  Every semantic
is *read from the field facts* by the same registry rules the page assembler
uses; no meaning is authored by hand, which keeps the backend input to the model,
the view and the permission data.

Drift between this carrier and the field facts is a lint failure
(``make verify.semantic.registry.lint``).
"""

from __future__ import annotations

GENERATED_FROM = ('contracts/generated/product_view_structure_contract.json',)

# model -> field -> semantic
DOMAIN_FIELD_SEMANTICS = {
    'payment.request': {
        'accepted_amount_uppercase': 'text',
        'actual_paid_amount_display': 'money',
        'actual_payee_unit': 'text',
        'actual_payee_unit_display': 'text',
        'amount': 'money',
        'amount_uppercase': 'text',
        'amount_uppercase_display': 'text',
        'attachment_ids': 'relation_collection',
        'business_category_id': 'relation',
        'can_review': 'boolean',
        'company_contractor_arrival_over_processed_amount': 'number',
        'company_contractor_arrival_unprocessed_amount': 'number',
        'company_contractor_responsibility_notice': 'text',
        'company_contractor_responsibility_state': 'choice',
        'company_contractor_responsibility_summary_id': 'relation',
        'company_contractor_self_funding_balance': 'number',
        'company_id': 'relation',
        'contract_change_amount': 'money',
        'contract_currency_id': 'relation',
        'contract_final_amount': 'money',
        'contract_id': 'relation',
        'contract_invoice_amount': 'money',
        'contract_paid_amount': 'money',
        'contract_payment_terms': 'long_text',
        'contract_settlement_amount': 'money',
        'contract_unpaid_amount': 'money',
        'cost_category_name': 'text',
        'cost_type_display': 'text',
        'currency_id': 'relation',
        'current_pay_amount': 'text',
        'current_receipt_amount': 'text',
        'date_request': 'date',
        'has_active_payment_execution': 'boolean',
        'invoice_amount': 'text',
        'invoice_no': 'text',
        'invoice_party_name': 'text',
        'invoiced_before_amount': 'text',
        'is_fully_paid': 'boolean',
        'is_overpay_risk': 'boolean',
        'ledger_line_ids': 'detail_collection',
        'legal_next_action_display': 'text',
        'line_settlement_summary': 'text',
        'material_settlement_id': 'relation',
        'name': 'text',
        'note': 'long_text',
        'note_display': 'text',
        'operation_strategy': 'choice',
        'outflow_line_ids': 'detail_collection',
        'paid_amount_total': 'money',
        'paid_at': 'text',
        'paid_before_amount': 'text',
        'partner_account_name': 'text',
        'partner_bank_account': 'text',
        'partner_bank_name': 'text',
        'partner_id': 'relation',
        'partner_transaction_eligibility': 'choice',
        'partner_transaction_eligibility_reason': 'text',
        'payee_account_completeness': 'choice',
        'payee_account_name_display': 'text',
        'payee_account_no_display': 'text',
        'payee_account_source_display': 'text',
        'payee_bank_name_display': 'text',
        'payee_unit_display': 'text',
        'payer_unit': 'text',
        'payer_unit_display': 'text',
        'payment_account_name': 'text',
        'payment_account_no': 'text',
        'payment_account_no_display': 'text',
        'payment_bank_name': 'text',
        'payment_basis_type': 'choice',
        'payment_blocking_reason_display': 'text',
        'payment_execution_ids': 'detail_collection',
        'payment_execution_status_display': 'text',
        'payment_flow_label': 'text',
        'project_id': 'relation',
        'project_name_display': 'text',
        'receipt_invoice_line_ids': 'detail_collection',
        'receipt_type': 'text',
        'ref': 'text',
        'reject_reason': 'long_text',
        'remaining_amount': 'text',
        'request_amount_display': 'money',
        'sequence': 'text',
        'settlement_amount_insufficient': 'boolean',
        'settlement_amount_payable': 'money',
        'settlement_amount_total': 'money',
        'settlement_approved_amount': 'money',
        'settlement_compliance_message': 'long_text',
        'settlement_deduction_amount': 'money',
        'settlement_id': 'relation',
        'settlement_match_blocked': 'boolean',
        'settlement_match_warn': 'boolean',
        'settlement_paid_amount': 'money',
        'settlement_period_end': 'date',
        'settlement_period_start': 'date',
        'settlement_remaining_amount': 'money',
        'settlement_submitted_amount': 'money',
        'source_created_at': 'datetime',
        'source_created_by': 'text',
        'source_document_no': 'text',
        'source_line_type': 'text',
        'state': 'status',
        'type': 'choice',
        'unpaid_amount': 'money',
        'validation_status': 'choice',
    },
}
