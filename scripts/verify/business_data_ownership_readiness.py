"""Read-only business-data ownership readiness for the governed local.dev lane.

Calls the industry probe service and platform ownership decision, rolls back,
and fails the command when ownership is unresolved. Historical development
migrations are retired; this explicit check does not imply an upgrade hook.
"""
import json
import os

from odoo.addons.smart_construction_core.services import business_data_ownership
from odoo.addons.smart_core.security import data_space_provisioning as provisioning

expected = str(os.environ.get('SC_EXPECTED_DB') or '').strip()
if expected and env.cr.dbname != expected:
    raise SystemExit('BUSINESS_DATA_OWNERSHIP_READINESS=database_mismatch:%s' % env.cr.dbname)

report = business_data_ownership.ownership_readiness(env)
report['database'] = env.cr.dbname
report['onboarded_registration_purposes'] = sorted(
    set(provisioning.onboarded_registrations(env).mapped('data_purpose'))
)
report['bootstrap_company_ids'] = provisioning.bootstrap_company_ids(env)
report['companies'] = [
    {'id': company.id, 'name': company.name,
     'bootstrap': bool(company.is_platform_bootstrap_company)}
    for company in env['res.company'].sudo().search([], order='id')
]
try:
    report['ownership_gate'] = {
        'passed': True,
        'business_data_company_ids': (
            business_data_ownership.assert_existing_business_data_ownership(env)
        ),
    }
except ValueError as error:
    report['ownership_gate'] = {'passed': False, 'error': str(error)}
report['passed'] = bool(report['passed'] and report['ownership_gate']['passed'])
print('BUSINESS_DATA_OWNERSHIP_READINESS=' + json.dumps(report, ensure_ascii=False, sort_keys=True))
env.cr.rollback()
if not report['passed']:
    raise SystemExit(1)
