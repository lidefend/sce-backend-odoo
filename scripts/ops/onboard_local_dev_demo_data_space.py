"""Onboard the local.dev demo database's main company as its demo data space.

Executed only by local.dev.data_space.onboard in the registered demo DB.

Owner ruling 2026-10-14 (DEMO_IS_FIRST_ONBOARDED_COMPANY): in the demo role the
environment main company IS the first onboarded business company, so onboarding
retires its bootstrap carrier marker instead of re-owning a single business row.
That is the whole difference from a data migration: no row changes company.

The entry is read-only by default. A real write requires the exact confirmation
``SC_CONFIRM_DATA_SPACE_ONBOARDING=onboard`` and commits only after the
post-conditions pass. The database name and the declared role are re-checked
here, so this script can never onboard a customer production database.
"""
import json
import os

from odoo.addons.smart_core.security import data_space_provisioning as provisioning

assert env.cr.dbname == 'sc_dev_demo', 'requires the exact local.dev database'
env.cr.rollback()

CONFIRMATION_TOKEN = 'onboard'
ENVIRONMENT_ROLE = 'platform_internal_demo'
DEMO_TENANT_KEY = 'sc-demo-main'


def readback():
    companies = env['res.company'].sudo().search([], order='id')
    registrations = env['sc.tenant.company.registration'].sudo().search([])
    return {
        'database': env.cr.dbname,
        'environment_role': provisioning.environment_role(env),
        'main_company_id': env.company.id,
        'registration_rows': len(registrations),
        'registered_company_ids': sorted(registrations.company_id.ids),
        'onboarded_demo_company_ids': provisioning.onboarded_registrations(
            env, purpose='demo').company_id.ids,
        'operators_pending_enrollment': (
            provisioning.data_space_operators_pending_enrollment(env, purpose='demo')
            if provisioning.onboarded_registrations(env, purpose='demo') else None
        ),
        'bootstrap_company_ids': provisioning.bootstrap_company_ids(env),
        'companies': [
            {'id': company.id, 'name': company.name,
             'bootstrap': bool(company.is_platform_bootstrap_company),
             'registered': company.id in registrations.company_id.ids}
            for company in companies
        ],
    }


before = readback()
confirmation = str(os.environ.get('SC_CONFIRM_DATA_SPACE_ONBOARDING') or '').strip()

if confirmation != CONFIRMATION_TOKEN:
    plan = dict(before, writes=False, confirmation_required=(
        'SC_CONFIRM_DATA_SPACE_ONBOARDING=%s' % CONFIRMATION_TOKEN))
    plan['steps'] = [
        'declare_environment_role(%s) on ir.config_parameter sc.environment.role' % ENVIRONMENT_ROLE,
        'onboard_environment_main_company(tenant_key="%s"): retire the bootstrap marker '
        'and write one sc.tenant.company.registration row' % DEMO_TENANT_KEY,
        'enroll_data_space_identities(purpose="demo"): grant the non-customer data realm to '
        'this space\'s operating identities, so onboarding produces a readable data space',
        'no business row changes company; re-run make local.dev.data_scope.ceiling.readiness',
    ]
    print('LOCAL_DEV_DATA_SPACE_ONBOARDING_PLAN=' + json.dumps(plan, ensure_ascii=False, sort_keys=True))
    env.cr.rollback()
else:
    provisioning.declare_environment_role(env, ENVIRONMENT_ROLE)
    registration = provisioning.onboard_environment_main_company(env, tenant_key=DEMO_TENANT_KEY)
    enrollment = provisioning.enroll_data_space_identities(env, purpose='demo')
    env.cr.commit()
    after = readback()
    after['writes'] = True
    after['registration_tenant_key'] = registration.tenant_key
    after['enrollment'] = enrollment
    after['post_conditions'] = {
        'main_company_is_not_a_carrier': bool(after['main_company_id'] not in after['bootstrap_company_ids']),
        'no_bootstrap_company_remains': not after['bootstrap_company_ids'],
        'one_registration_row': after['registration_rows'] == 1,
        'demo_registration_visible': bool(after['onboarded_demo_company_ids']),
        'operators_pending_enrollment_is_empty': after['operators_pending_enrollment'] == [],
    }
    after['passed'] = all(after['post_conditions'].values())
    print('LOCAL_DEV_DATA_SPACE_ONBOARDING=' + json.dumps(after, ensure_ascii=False, sort_keys=True))
