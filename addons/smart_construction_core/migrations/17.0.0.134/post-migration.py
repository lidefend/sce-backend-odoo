"""Scope the generated WBS planning tree contract to its owning entry.

The historical contract was model-wide, although ``construction.work.breakdown``
has both the editable WBS planner and the read-oriented execution-structure
browser.  Bind the noupdate record to the planner action/view so each native
surface remains authoritative for its own column structure.
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
           AND action_data.name = 'action_work_breakdown'
           AND action_data.model = 'ir.actions.act_window'
          JOIN ir_model_data AS view_data
            ON view_data.module = 'smart_construction_core'
           AND view_data.name = 'view_work_breakdown_tree'
           AND view_data.model = 'ir.ui.view'
         WHERE contract_data.module = 'smart_construction_core'
           AND contract_data.name =
               'business_config_contract_construction_work_breakdown_tree_structure_generated'
           AND contract_data.model = 'ui.business.config.contract'
           AND contract.id = contract_data.res_id
           AND (contract.action_id IS DISTINCT FROM action_data.res_id
             OR contract.view_id IS DISTINCT FROM view_data.res_id)
        """
    )
