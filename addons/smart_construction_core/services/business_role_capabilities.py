"""Reviewed authorization bindings for existing business capability identities.

The registry remains the sole business directory. These platform-owned bindings
are never supplied by enterprise role editors or import files.
"""
from .business_capability_authorization import VERSION


PROJECT_READER = 'smart_construction_core.group_sc_cap_project_read'
AUTHORIZATIONS = {
    'project.list.open': {
        'version': VERSION, 'state': 'verified', 'composable': True,
        'operations': ['read'], 'native_groups': [PROJECT_READER, 'smart_construction_core.group_sc_cap_entry_scope_p11'],
        'dependencies': [], 'exclusions': [], 'sensitive': False,
        'scope_policy': 'company_and_record_rules',
        'native_group_edges': {
            PROJECT_READER: ['smart_construction_core.group_sc_bridge_project_base'],
            'smart_construction_core.group_sc_bridge_project_base': ['smart_construction_core.group_sc_cap_internal_identity', 'project.group_project_stages'],
            'project.group_project_stages': [],
            'smart_construction_core.group_sc_cap_internal_identity': ['base.group_user'],
            'smart_construction_core.group_sc_cap_entry_scope_p11': ['smart_construction_core.group_sc_entry_p11'],
            'smart_construction_core.group_sc_entry_p11': [],
        },
        # Incremental business ACLs beyond the native internal-user identity.
        'native_model_access': {
            'project.project': ['read'],
            'project.project.stage': ['read'],
            'project.dictionary': ['read'],
        },
        'verification_refs': ['smart_construction_core.tests.test_business_role:TestBusinessRole'],
    },
}
