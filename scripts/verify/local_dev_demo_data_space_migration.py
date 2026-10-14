"""Governed P4 migration: onboard this database's demo data space.

Owner-authorized 2026-10-14. Two phases in one artifact:

* without ``SC_CONFIRM_DATA_SPACE_MIGRATION=1`` it prints the exact write set and
  rolls back (read-only plan);
* with the confirmation it performs the same write set in one transaction,
  verifies the post-conditions, commits, then prints a write report.

The re-own target set is derived from the installed data-scope ceiling rules, so
the migration moves exactly the models whose isolation dimension is company
ownership instead of a hand-kept model list. Residual bootstrap rows outside
that set are reported, never silently ignored.
"""
import json
import os

assert env.cr.dbname == 'sc_dev_demo', 'requires the exact local.dev database'
CONFIRM = str(os.environ.get('SC_CONFIRM_DATA_SPACE_MIGRATION') or '') == '1'
TENANT_KEY = 'local-dev-demo'
PURPOSE = 'demo'
EXCLUDED_MODELS = {
    'res.company', 'res.users', 'res.partner',
    'sc.tenant.company.registration', 'sc.data.space.serialization',
}


def ceiling_models():
    """Installed generated ceilings name exactly the company-isolated models."""
    rules = env['ir.rule'].sudo().search([('name', 'like', 'SC Data Scope -')])  # noqa: F821
    return sorted({rule.model_id.model for rule in rules if rule.model_id})


def bootstrap_ids():
    return env['res.company'].sudo().search(  # noqa: F821
        [('is_platform_bootstrap_company', '=', True)]).ids


def rows_under(model_name, company_ids):
    model = env[model_name]  # noqa: F821
    records = model.sudo().with_context(active_test=False).search(
        [('company_id', 'in', company_ids)])
    return records


def target_company(bootstrap, registered_ids):
    candidates = env['res.company'].sudo().search(  # noqa: F821
        [('is_platform_bootstrap_company', '=', False)]).filtered(
        lambda company: company.id not in registered_ids and company.active)
    if len(candidates) != 1:
        raise RuntimeError('DATA_SPACE_TARGET_NOT_DETERMINISTIC:%s'
                           % ','.join(str(company.id) for company in candidates))
    return candidates[0]


bootstrap = bootstrap_ids()
registrations = env['sc.tenant.company.registration'].sudo().search([])  # noqa: F821
registered_ids = registrations.company_id.ids
target = target_company(bootstrap, registered_ids)

ceiling = [name for name in ceiling_models() if name not in EXCLUDED_MODELS]
owning_bootstrap, residual, empty = {}, [], []
for model_name in ceiling:
    if model_name not in env or 'company_id' not in env[model_name]._fields:  # noqa: F821
        empty.append(model_name)
        continue
    records = rows_under(model_name, bootstrap)
    if records:
        owning_bootstrap[model_name] = len(records)

# Residual scan: every stored company_id model outside the ceiling set. Each
# probe runs in its own savepoint because a failing probe must not abort the
# transaction that the migration still has to use.
company_field_models = sorted({
    field.model for field in env['ir.model.fields'].sudo().search(  # noqa: F821
        [('name', '=', 'company_id'), ('store', '=', True)])
    if field.model})
for model_name in company_field_models:
    if model_name in ceiling or model_name in EXCLUDED_MODELS or model_name not in env:  # noqa: F821
        continue
    model = env[model_name]  # noqa: F821
    if getattr(model, '_transient', False) or not getattr(model, '_table', None):
        continue
    try:
        with env.cr.savepoint():  # noqa: F821
            records = rows_under(model_name, bootstrap)
            if records:
                residual.append({'model': model_name, 'records': len(records)})
    except Exception:  # noqa: BLE001 - a probe is not a migration step
        continue

internal_users = env['res.users'].sudo().with_context(active_test=False).search(  # noqa: F821
    [('share', '=', False)])
root = env.ref('base.user_root', raise_if_not_found=False)  # noqa: F821
membership_updates = []
default_updates = []
for user in internal_users:
    if root and user.id == root.id:
        continue
    if target.id not in user.company_ids.ids:
        membership_updates.append(user.id)
    if user.company_id.id in bootstrap:
        default_updates.append(user.id)

plan = {
    'database': env.cr.dbname,
    'confirmed': CONFIRM,
    'bootstrap_company_ids': bootstrap,
    'registered_company_ids': registered_ids,
    'target_company': {'id': target.id, 'name': target.name},
    'tenant_key': TENANT_KEY,
    'data_purpose': PURPOSE,
    'models_to_re_own': owning_bootstrap,
    'records_to_re_own': sum(owning_bootstrap.values()),
    'models_without_company_column': empty,
    'residual_bootstrap_models': residual,
    'internal_users_total': len(internal_users),
    'users_gaining_membership': len(membership_updates),
    'users_default_company_reassigned': len(default_updates),
    'writes': 0,
}

if not CONFIRM:
    print('DEMO_DATA_SPACE_MIGRATION_PLAN=' + json.dumps(plan, ensure_ascii=False, sort_keys=True))
    raise SystemExit(0)

failures = []
moved = {}
try:
    if not registered_ids:
        adopt = __import__(
            'odoo.addons.smart_core.security.data_space_provisioning', fromlist=['adopt_business_company'])
        registration = adopt.adopt_business_company(
            env, tenant_key=TENANT_KEY, purpose=PURPOSE, company_id=target.id)
        plan['registration_id'] = registration.id
        plan['registration_tenant_key'] = registration.tenant_key
    elif target.id not in registered_ids:
        raise RuntimeError('DATA_SPACE_TARGET_MUST_BE_REGISTERED_BY_THE_GOVERNED_ENTRY')

    for user_id in membership_updates:
        env['res.users'].sudo().browse(user_id).write({'company_ids': [(4, target.id)]})  # noqa: F821
    for user_id in default_updates:
        env['res.users'].sudo().browse(user_id).write({'company_id': target.id})  # noqa: F821

    for model_name in sorted(owning_bootstrap):
        try:
            with env.cr.savepoint():  # noqa: F821
                records = rows_under(model_name, bootstrap)
                records.write({'company_id': target.id})
                moved[model_name] = len(records)
        except Exception as error:  # noqa: BLE001 - one report, then fail closed
            failures.append('%s:%s' % (model_name, type(error).__name__))

    if failures:
        raise RuntimeError('DATA_SPACE_MIGRATION_REOWN_FAILED:' + ','.join(failures))

    leftover = {model_name: len(rows_under(model_name, bootstrap))
                for model_name in sorted(owning_bootstrap)
                if rows_under(model_name, bootstrap)}
    registrations_after = env['sc.tenant.company.registration'].sudo().search(  # noqa: F821
        [('company_id', '=', target.id), ('data_purpose', '=', PURPOSE), ('active', '=', True)])
    if leftover:
        raise RuntimeError('DATA_SPACE_MIGRATION_LEFTOVER:' + json.dumps(leftover))
    if len(registrations_after) != 1:
        raise RuntimeError('DATA_SPACE_MIGRATION_REGISTRATION_NOT_OBSERVED')

    plan['moved'] = moved
    plan['registration_observed'] = True
    plan['leftover_bootstrap_rows'] = 0
    plan['remaining_bootstrap_defaults'] = env['res.users'].sudo().with_context(  # noqa: F821
        active_test=False).search_count([('company_id', 'in', bootstrap)])
    plan['writes'] = (len(moved) and sum(moved.values())) + len(membership_updates) + len(default_updates)
    env.cr.commit()  # noqa: F821
    plan['committed'] = True
except Exception as error:  # noqa: BLE001
    env.cr.rollback()  # noqa: F821
    plan['committed'] = False
    plan['error'] = '%s: %s' % (type(error).__name__, error)
    print('DEMO_DATA_SPACE_MIGRATION=' + json.dumps(plan, ensure_ascii=False, sort_keys=True))
    raise

print('DEMO_DATA_SPACE_MIGRATION=' + json.dumps(plan, ensure_ascii=False, sort_keys=True))
