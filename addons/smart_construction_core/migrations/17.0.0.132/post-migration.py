"""Archive the superseded generated payment-execution form contract.

The generated structure seed is ``noupdate`` and remains active in upgraded
databases.  The productized model-level contract now owns the same form
surface, so keeping both active causes stale fields to be projected into the
normalized contract.  Archive only that exact generated XMLID.
"""


def migrate(cr, installed_version):
    del installed_version
    cr.execute(
        """
        UPDATE ui_business_config_contract AS contract
           SET active = FALSE
          FROM ir_model_data AS data
         WHERE data.module = 'smart_construction_core'
           AND data.name = 'business_config_contract_sc_payment_execution_form_structure_generated'
           AND data.model = 'ui.business.config.contract'
           AND contract.id = data.res_id
           AND contract.active = TRUE
        """
    )
