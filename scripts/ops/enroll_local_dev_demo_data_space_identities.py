"""Reconcile the local.dev demo data space's operator identity realm.

Executed only by ``local.dev.data_space.enroll_identities`` in the registered
demo database. Read-only by default; a real write requires the exact
confirmation ``SC_CONFIRM_DATA_SPACE_IDENTITY_ENROLLMENT=enroll``.

Why a separate governed entry exists even though onboarding enrolls identities:
an Odoo module upgrade reloads the demo user data (``noupdate="0"``) while
``post_init_hook`` does not run again, so a registration can outlive its
operators' enrollment. This entry is the idempotent reconcile path for that
case; the demo seed guard re-enrolls before it asserts readiness, so a drifted
database fails closed instead of silently rendering an empty product.
"""
import json
import os

from odoo.addons.smart_core.security import data_space_provisioning as provisioning

assert env.cr.dbname == 'sc_dev_demo', 'requires the exact local.dev database'
env.cr.rollback()

CONFIRMATION_TOKEN = 'enroll'


def readback():
    registrations = provisioning.onboarded_registrations(env, purpose='demo')
    return {
        'database': env.cr.dbname,
        'environment_role': provisioning.environment_role(env),
        'registered_company_ids': sorted(registrations.company_id.ids),
        'operators_pending_enrollment': (
            provisioning.data_space_operators_pending_enrollment(env, purpose='demo')
            if registrations else None
        ),
    }


before = readback()
confirmation = str(os.environ.get('SC_CONFIRM_DATA_SPACE_IDENTITY_ENROLLMENT') or '').strip()

if confirmation != CONFIRMATION_TOKEN:
    plan = dict(before, writes=False, confirmation_required=(
        'SC_CONFIRM_DATA_SPACE_IDENTITY_ENROLLMENT=%s' % CONFIRMATION_TOKEN))
    plan['steps'] = [
        'enroll_data_space_identities(purpose="demo"): grant the non-customer data '
        'realm to this demo space\'s operating identities (idempotent)',
        'no business row and no company ownership changes',
    ]
    print('LOCAL_DEV_DATA_SPACE_IDENTITY_ENROLLMENT_PLAN='
          + json.dumps(plan, ensure_ascii=False, sort_keys=True))
    env.cr.rollback()
else:
    receipt = provisioning.enroll_data_space_identities(env, purpose='demo')
    pending = provisioning.data_space_operators_pending_enrollment(env, purpose='demo')
    env.cr.commit()
    after = readback()
    after['writes'] = True
    after['enrollment'] = receipt
    after['post_conditions'] = {
        'operators_pending_enrollment_is_empty': pending == [],
        'identity_group_is_declared': bool(receipt.get('group')),
    }
    after['passed'] = all(after['post_conditions'].values())
    print('LOCAL_DEV_DATA_SPACE_IDENTITY_ENROLLMENT='
          + json.dumps(after, ensure_ascii=False, sort_keys=True))
