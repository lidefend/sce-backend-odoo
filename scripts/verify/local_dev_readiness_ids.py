"""Read-only selection and business readback for governed native readiness pages."""
import hashlib
import json
from odoo.addons.smart_construction_core.services.baseline_readiness import build_readiness

assert env.cr.dbname == 'sc_dev_demo'
admin = env.ref('smart_construction_demo.sc_demo_user_test_admin')
reader = env.ref('smart_construction_demo.user_demo_project_read')
assert admin.active and reader.active
cases = []
missing = []

def add_case(key, actor, model, status, action_name, menu_name, domain=None):
    actor_model = env[model].with_user(actor).with_company(actor.company_id).with_context(allowed_company_ids=actor.company_ids.ids)
    record = None
    if status == 'no_data':
        expected = actor_model.default_get(['submission_readiness_display'])['submission_readiness_display']
    else:
        for candidate in actor_model.search(domain or [], order='id', limit=100):
            projection = build_readiness(actor_model.env, model, candidate.id)
            if projection['status'] == status:
                record = candidate
                expected = candidate.submission_readiness_display
                break
        if not record:
            missing.append(key)
            return
    action = env.ref('smart_construction_core.' + action_name)
    menu = env.ref('smart_construction_core.' + menu_name)
    assert action.res_model == model and menu.action == action
    cases.append({'key': key, 'actor': {'id': actor.id, 'login': actor.login}, 'model': model,
                  'status': status, 'record_id': record.id if record else None,
                  'action_id': action.id, 'menu_id': menu.id, 'expected': expected})

project_domain = [('lifecycle_state', '=', 'draft'), ('sc_approval_state', '=', 'draft')]
add_case('project-ready', admin, 'project.project', 'ready', 'action_sc_project_list', 'menu_sc_project_project', project_domain)
add_case('project-forbidden', reader, 'project.project', 'forbidden', 'action_sc_project_list', 'menu_sc_project_project', project_domain)
add_case('payment-blocked', admin, 'payment.request', 'blocked', 'action_payment_request_user_payment_apply', 'menu_sc_user_payment_apply', [('state', 'in', ['draft', 'rejected'])])
add_case('project-new', admin, 'project.project', 'no_data', 'action_project_initiation', 'menu_sc_project_initiation')
add_case('payment-new', admin, 'payment.request', 'no_data', 'action_payment_request_user_payment_apply', 'menu_sc_user_payment_apply')
# System readback is separate from principal-scoped selection. No elevation in product checks.
facts = {}
for model in ('project.project', 'payment.request', 'tier.review', 'sc.audit.log', 'project.funding.baseline'):
    facts[model] = env[model].sudo().with_context(active_test=False).search_read([], ['id', 'write_date'], order='id')
payload = {'database': env.cr.dbname, 'cases': cases, 'missing': missing,
           'business_fingerprint': hashlib.sha256(json.dumps(facts, sort_keys=True, default=str).encode()).hexdigest()}
print('LOCAL_DEV_READINESS_JSON=' + json.dumps(payload, ensure_ascii=True))
