"""Remove retired P2 projection views before validating canonical P1 forms.

The XML IDs below were created by the early user-confirmation experiment in
``smart_construction_core``.  Their source declarations have since been
removed, but Odoo keeps the database records forever unless an upgrade
migration removes them explicitly.  Once the corresponding customer fields
leave the P1 model, those stale inherited views prevent the canonical parent
forms from being upgraded.

Customer data is not touched here.  Current customer projections belong to a
P2 module and must use its own XML IDs.
"""


RETIRED_P2_FORM_VIEW_XMLIDS = (
    "view_project_project_user_confirmed_form_fields",
    "view_project_overview_user_confirmed_form_fields",
    "view_tender_bid_user_confirmed_form_fields",
    "view_construction_contract_expense_user_confirmed_form_fields",
    "view_sc_settlement_order_user_confirmed_form_fields",
    "view_sc_construction_diary_user_confirmed_form_fields",
    "view_project_material_plan_user_confirmed_form_fields",
    "view_sc_labor_usage_user_confirmed_form_fields",
    "view_sc_subcontract_request_user_confirmed_form_fields",
    "view_sc_equipment_usage_user_confirmed_form_fields",
    "view_sc_material_rfq_user_confirmed_form_fields",
    "view_sc_material_inbound_user_confirmed_form_fields",
    "view_sc_hr_payroll_document_user_confirmed_form_fields",
    "view_sc_tax_deduction_registration_user_confirmed_form_fields",
    "view_sc_fund_account_operation_user_confirmed_form_fields",
    "view_sc_financing_loan_user_confirmed_form_fields",
    "view_payment_request_user_confirmed_form_fields",
    "view_sc_payment_execution_user_confirmed_form_fields",
    "view_tender_guarantee_user_confirmed_form_fields",
    "view_sc_office_admin_document_user_confirmed_form_fields",
    "view_sc_document_admin_document_user_confirmed_form_fields",
)


def migrate(cr, installed_version):
    del installed_version
    cr.execute(
        """
        WITH RECURSIVE retired_view_ids AS (
            SELECT data.res_id AS id
              FROM ir_model_data data
             WHERE data.module = 'smart_construction_core'
               AND data.model = 'ir.ui.view'
               AND data.name = ANY(%s)
            UNION
            SELECT child.id
              FROM ir_ui_view child
              JOIN retired_view_ids parent ON child.inherit_id = parent.id
        ),
        deleted_view_xmlids AS (
            DELETE FROM ir_model_data
             WHERE model = 'ir.ui.view'
               AND res_id IN (SELECT id FROM retired_view_ids)
            RETURNING id
        )
        DELETE FROM ir_ui_view
         WHERE id IN (SELECT id FROM retired_view_ids)
        """,
        [list(RETIRED_P2_FORM_VIEW_XMLIDS)],
    )
