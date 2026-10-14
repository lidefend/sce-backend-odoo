"""Read-only readback of the upgrade-time business-data ownership gate.

One question: would ``smart_construction_core``'s upgrade gate pass in this
database right now? Onboarding was previously only proven before new writes, so
a database whose business rows predate the data-space declaration could serve an
empty product with nothing failing loudly.

The report carries both halves of the same decision: the ownership readback, and
the result of calling the real gate function the pre-migration calls. This entry
is read-only and commits nothing.

Executed only by local.dev.business_data.ownership.readiness in the registered
demo DB.
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
    report['upgrade_gate'] = {
        'passed': True,
        'business_data_company_ids': (
            business_data_ownership.assert_existing_business_data_ownership(env)
        ),
    }
except ValueError as error:
    report['upgrade_gate'] = {'passed': False, 'error': str(error)}
report['passed'] = bool(report['passed'] and report['upgrade_gate']['passed'])
print('BUSINESS_DATA_OWNERSHIP_READINESS=' + json.dumps(report, ensure_ascii=False, sort_keys=True))
env.cr.rollback()
