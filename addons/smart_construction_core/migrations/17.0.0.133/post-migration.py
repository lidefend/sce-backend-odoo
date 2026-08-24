"""Bind project initiation form contracts to their action/view scope.

The two project form-structure seeds are ``noupdate`` records.  Existing
databases therefore need an idempotent scope repair so the initiation surface
cannot govern the complete project workspace action.
"""


def migrate(cr, installed_version):
    del installed_version
    cr.execute(
        """
        UPDATE ui_business_config_contract AS contract
           SET action_id = action_data.res_id,
               view_id = view_data.res_id
          FROM ir_model_data AS contract_data
          JOIN ir_model_data AS action_data
            ON action_data.module = 'smart_construction_core'
           AND action_data.name = 'action_project_initiation'
           AND action_data.model = 'ir.actions.act_window'
          JOIN ir_model_data AS view_data
            ON view_data.module = 'smart_construction_core'
           AND view_data.name = 'view_project_create_form'
           AND view_data.model = 'ir.ui.view'
         WHERE contract_data.module = 'smart_construction_core'
           AND contract_data.name IN (
               'business_config_contract_project_project_form_structure_generated',
               'business_config_contract_project_project_form_structure_v1'
           )
           AND contract_data.model = 'ui.business.config.contract'
           AND contract.id = contract_data.res_id
           AND (contract.action_id IS DISTINCT FROM action_data.res_id
             OR contract.view_id IS DISTINCT FROM view_data.res_id)
        """
    )
