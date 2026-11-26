"""Explicit platform licensing for synthetic multi-company test principals."""


def license_multi_company(env, companies):
    plans = env['sc.subscription.plan'].sudo()
    for company in companies:
        plan = plans.create({
            'name': 'Synthetic multi-company license',
            'code': 'synthetic-multi-company-%s' % company.id,
            'multi_company_enabled': True,
        })
        env['sc.subscription'].sudo().create({
            'company_id': company.id, 'plan_id': plan.id, 'state': 'active',
        })
