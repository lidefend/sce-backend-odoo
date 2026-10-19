"""Read-only absence proof for the exact AUTH-01 TransactionCase fixture."""
import json

assert env.cr.dbname == 'sc_dev_demo', 'registered local.dev database required'
env.cr.rollback()
env.cr.execute('SET TRANSACTION READ ONLY')
try:
    suffixes = ('accounting_manager', 'accounting_read', 'accounting_user',
                'business_admin', 'general_user', 'partner_manager',
                'settlement_manager', 'material_manager')
    logins = ['auth01_separation_' + value for value in suffixes]
    logins += ['user_closure_config_admin', 'user_closure_member', 'user_closure_other', 'auth01_personnel_denied_create', 'auth01_rule_denied_create', 'auth01_rule_allowed_create', 'auth01_rule_http_denied', 'auth01_default_http', 'auth01_default_protected', 'auth01_default_created', 'auth01_default_assignment', 'auth01_context_0', 'auth01_context_1', 'auth01_role_maintainer', 'auth01_explicit_origin', 'auth01_approval_subject', 'auth01_approval_maintainer', 'auth01_approval_forbidden_new', 'auth01_reconcile_admin', 'auth01_reconcile_manager', 'auth01_reconcile_subject', 'auth01_http_subject', 'auth01_http_manager', 'auth01_http_authority_admin', 'smart_core_tester']
    logins += ['auth01_accounting_' + value for value in ('accounting_read', 'accounting_user', 'accounting_manager')]
    logins += ['auth01_business_' + value for value in ('general_user', 'business_admin', 'settlement_manager')]
    counts = {
        'users': env['res.users'].sudo().with_context(active_test=False).search_count([('login', 'in', logins)]),
        'companies': env['res.company'].sudo().with_context(active_test=False).search_count([('name', 'in', ['Synthetic TestUserModuleProductClosure', 'Synthetic AUTH01 personnel other company', 'Unauthorized synthetic rename', 'Synthetic forbidden company', 'Synthetic forbidden rename', 'Synthetic TestSystemPermissionSeparation', 'Synthetic TestApprovalScopeAuthority', 'Synthetic TestGroupAuthorityReconciliation', 'Synthetic TestSystemPermissionHttp', 'Synthetic TestSystemPermissionAccounting', 'Synthetic TestSystemPermissionBusiness'])]),
        'jobs': env['hr.job'].sudo().with_context(active_test=False).search_count([('name', 'in', ['Closure Job', 'Synthetic position A', 'Synthetic position B', 'Synthetic AUTH01 other hr.job', 'Synthetic AUTH01 hidden hr.job', 'Synthetic AUTH01 HTTP hidden job', 'Synthetic AUTH01 HTTP allowed job'])]),
        'action_targets': env['res.partner'].sudo().with_context(active_test=False).search_count([('name', 'in', ['Synthetic rule denied create', 'Synthetic rule allowed create', 'Synthetic rule HTTP denied', 'Synthetic revoked-role blacklist target', 'Synthetic HTTP revoked-role blacklist target', 'Synthetic AUTH01 settlement partner'])]),
    }
    counts['journals'] = env['account.journal'].sudo().with_context(active_test=False).search_count([('name', 'in', ['Synthetic AUTH01 journal', 'Forbidden AUTH01 journal', 'Synthetic AUTH01 manager journal', 'Synthetic AUTH01 manager changed', 'Forbidden journal configuration', 'Forbidden after revoke'])])
    counts['dictionaries'] = env['project.dictionary'].sudo().with_context(active_test=False).search_count([('code', 'in', ['AUTH01_READ', 'AUTH01_DENY', 'AUTH01_ADMIN'])])
    counts['projects'] = env['project.project'].sudo().with_context(active_test=False).search_count([('name', 'in', ['User Closure Project', 'Synthetic AUTH01 settlement project', 'Synthetic AUTH01 default project', 'Synthetic AUTH01 default HTTP project'])])
    counts['project_assignments'] = env['sc.project.member.assignment'].sudo().with_context(active_test=False).search_count(['|', ('user_id.login', 'in', ['auth01_default_assignment', 'auth01_default_http']), ('project_id.name', 'in', ['Synthetic AUTH01 default project', 'Synthetic AUTH01 default HTTP project'])])
    counts['authority_rules'] = env['ir.rule'].sudo().with_context(active_test=False).search_count([('name', 'in', ['Synthetic AUTH01 public profile user denial', 'Synthetic AUTH01 public profile job denial', 'Synthetic AUTH01 HTTP public profile denial', 'Synthetic AUTH01 personnel denial hr.department', 'Synthetic AUTH01 personnel denial hr.job', 'Synthetic AUTH01 personnel create denial', 'Synthetic AUTH01 HTTP personnel denial', 'Synthetic AUTH01 user write denial', 'Synthetic AUTH01 user create denial', 'Synthetic AUTH01 HTTP user denial'])])
    counts['departments'] = env['hr.department'].sudo().with_context(active_test=False).search_count([('name', 'in', ['Closure Department', 'Synthetic AUTH01 other hr.department', 'Synthetic AUTH01 hidden hr.department', 'Synthetic AUTH01 allowed department'])])
    counts['employees'] = env['hr.employee'].sudo().with_context(active_test=False).search_count([('user_id.login', 'in', logins)])
    counts['contracts'] = env['construction.contract'].sudo().search_count([('subject', 'in', ['Synthetic AUTH01 settlement contract', 'Forbidden contract write'])])
    counts['settlements'] = env['sc.settlement.order'].sudo().search_count([('name', '=', 'Synthetic AUTH01 settlement')])
    counts['settlement_lines'] = env['sc.settlement.order.line'].sudo().search_count([('name', '=', 'Synthetic AUTH01 settlement line')])
    counts['accounts'] = env['account.account'].sudo().with_context(active_test=False).search_count([('code', 'in', ['AUTH0101', 'AUTH0102'])])
    counts['moves'] = env['account.move'].sudo().search_count([('ref', '=', 'Synthetic AUTH01 journal entry')])
    counts['move_lines'] = env['account.move.line'].sudo().search_count([('name', 'in', ['Synthetic AUTH01 debit line', 'Synthetic AUTH01 credit line'])])
    counts['groups'] = env['res.groups'].sudo().search_count([('name', 'in', ['Synthetic AUTH01 definition root', 'Synthetic AUTH01 lifecycle root', 'Synthetic AUTH01 lifecycle second', 'Synthetic AUTH01 selection low', 'Synthetic AUTH01 selection high'])])
    counts['group_categories'] = env['ir.module.category'].sudo().search_count([('name', '=', 'Synthetic AUTH01 selection category')])
    counts['confirmations'] = env['sc.group.authority.confirmation'].sudo().search_count([('note', '=', 'Synthetic explicit source confirmation')])
    counts['reviews'] = env['sc.group.authority.reconcile'].sudo().search_count([('user_id.login', 'in', logins)])
    print('AUTH01_CLEANUP=' + json.dumps({'database': env.cr.dbname, 'counts': counts, 'passed': not any(counts.values())}))
    assert not any(counts.values()), 'AUTH-01 fixture remains after TransactionCase'
finally:
    env.cr.rollback()
