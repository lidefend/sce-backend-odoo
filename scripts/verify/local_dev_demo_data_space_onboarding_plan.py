"""Read-only plan for onboarding the demo data space in the local.dev database.

Executed only by local.dev.demo.data_space.onboarding.plan in the registered demo DB.

Never writes. It answers the one open question for the pending governed P4
migration: which company should become the registered demo data space, and
exactly which rows must be re-owned so that
``business_data_never_in_platform_bootstrap_company`` holds afterwards.
"""
import json

assert env.cr.dbname == 'sc_dev_demo', 'requires the exact local.dev database'
env.cr.rollback()
original_commit = env.cr.commit


def reject_commit(*args, **kwargs):
    raise RuntimeError('demo data space onboarding plan forbids commit')


env.cr.commit = reject_commit

BUSINESS_PROBES = ('payment.request', 'sc.general.contract', 'project.project',
                   'sc.business.category')

try:
    companies = env['res.company'].sudo().search([], order='id')
    registrations = env['sc.tenant.company.registration'].sudo().search([])
    registered_ids = registrations.company_id.ids

    def rows_by_company(model_name):
        if model_name not in env or 'company_id' not in env[model_name]._fields:
            return None
        table = model_name.replace('.', '_')
        env.cr.execute('SELECT company_id, COUNT(*) FROM %s GROUP BY company_id' % table)
        return {('none' if company is None else int(company)): count
                for company, count in env.cr.fetchall()}

    per_company = {}
    for company in companies:
        per_company[company.id] = {
            'name': company.name,
            'bootstrap': bool(company.is_platform_bootstrap_company),
            'registered': company.id in registered_ids,
            'records': {},
        }

    bootstrap_owned = {}
    for model_name in BUSINESS_PROBES:
        distribution = rows_by_company(model_name)
        if distribution is None:
            continue
        for company_id, count in distribution.items():
            bucket = per_company.setdefault(
                company_id, {'name': None, 'bootstrap': None, 'registered': None, 'records': {}})
            bucket['records'][model_name] = count
            if bucket.get('bootstrap'):
                bootstrap_owned[model_name] = count

    candidates = [
        {'company_id': company_id, 'name': entry['name'], 'records': sum(entry['records'].values())}
        for company_id, entry in sorted(per_company.items())
        if not entry.get('bootstrap') and not entry.get('registered')
    ]
    candidates.sort(key=lambda item: (item['records'], item['company_id']))

    # Who can see the target company afterwards matters as much as the rows:
    # re-owning rows into a company that no actor has in allowed_company_ids
    # would hide them, which is worse than the current unregistered state.
    internal_users = env['res.users'].sudo().search(
        [('active', '=', True), ('share', '=', False)], order='id')
    company_coverage = {}
    for user in internal_users:
        for company_id in user.company_ids.ids:
            company_coverage[company_id] = company_coverage.get(company_id, 0) + 1

    plan = {
        'database': env.cr.dbname,
        'internal_user_count': len(internal_users),
        'users_allowing_company': company_coverage,
        'registration_rows_total': len(registrations),
        'bootstrap_company_ids': sorted(company_id for company_id, entry in per_company.items()
                                         if entry.get('bootstrap')),
        'companies': per_company,
        'reusable_unregistered_companies': candidates,
        'preferred_target_company_id': candidates[0]['company_id'] if candidates else None,
        'must_re_own_from_bootstrap': bootstrap_owned,
        'steps': [
            'onboard the target company through smart_core.security.data_space_provisioning'
            '.onboard_business_company(purpose="demo") so it becomes the registered demo space '
            '(the entry proves the declared strategy first and keeps the superuser maintenance rule)',
            're-own every row listed in must_re_own_from_bootstrap from the bootstrap company to '
            'the registered demo company inside one governed migration with a snapshot recovery point',
            're-run make local.dev.data_scope.ceiling.readiness until '
            'bootstrap_company_carries_business_data disappears from blockers',
            'bind smart_construction_demo seeding to assert_business_data_space_ready(purpose="demo") '
            'so a future install cannot seed before onboarding',
        ],
        'writes': False,
        'authorization_required': True,
    }
    print('DEMO_DATA_SPACE_ONBOARDING_PLAN=' + json.dumps(plan, ensure_ascii=False, sort_keys=True))
finally:
    env.cr.rollback()
    env.cr.commit = original_commit
