"""Read-only readiness of the exact payroll data-space slice, no business values.

Executed only by local.dev.payroll.data_scope.readiness in the registered demo DB.
"""
import json
from lxml import etree
from odoo.tools import file_open

assert env.cr.dbname == 'sc_dev_demo', 'requires the exact local.dev database'
env.cr.rollback()
original_commit = env.cr.commit


def reject_commit(*args, **kwargs):
    raise RuntimeError('payroll readiness forbids commit')


env.cr.commit = reject_commit
try:
    registrations = env['sc.tenant.company.registration'].sudo().search([
        ('active', '=', True), ('company_id.is_platform_bootstrap_company', '=', False),
    ])
    purposes = {row.company_id.id: row.data_purpose for row in registrations}
    blockers = []
    if not purposes:
        blockers.append('no_active_registered_data_spaces')
    counts = {}
    for table in ('sc_hr_payroll_document', 'sc_hr_salary_payment'):
        # Tables are fixed tool scope, never caller-provided identifiers.
        env.cr.execute(f'SELECT company_id, COUNT(*) FROM {table} GROUP BY company_id ORDER BY company_id')
        counts[table] = [
            {'company_id': company, 'records': count, 'registered_purpose': purposes.get(company)}
            for company, count in env.cr.fetchall()
        ]
        if any(not row['registered_purpose'] for row in counts[table]):
            blockers.append(table + ':unregistered_or_unknown_owner')
    env.cr.execute('''
        SELECT COUNT(*) FROM sc_hr_salary_payment payment
        JOIN sc_hr_payroll_document payroll ON payroll.id = payment.payroll_document_id
        WHERE payment.company_id IS DISTINCT FROM payroll.company_id
    ''')
    parent_mismatches = env.cr.fetchone()[0]
    if parent_mismatches:
        blockers.append('salary_payment:stored_parent_company_mismatch')
    env.cr.execute('''
        SELECT COUNT(*) FROM sc_hr_payroll_document payroll
        JOIN project_project project ON project.id = payroll.project_id
        WHERE payroll.company_id IS DISTINCT FROM project.company_id
    ''')
    project_mismatches = env.cr.fetchone()[0]
    if project_mismatches:
        blockers.append('payroll:project_company_mismatch')
    env.cr.execute('''
        SELECT attname FROM pg_attribute
        WHERE attrelid = to_regclass('sc_salary_summary') AND attnum > 0 AND NOT attisdropped
    ''')
    summary_columns = {row[0] for row in env.cr.fetchall()}
    missing_columns = sorted({'company_id', 'project_id', 'payer_unit_key'} - summary_columns)
    if missing_columns:
        blockers.append('salary_summary:pending_schema_upgrade')
    with file_open('smart_construction_core/security/sc_record_rules.xml', 'rb') as source:
        tree = etree.parse(source)
    rules = []
    for xmlid in ('rule_sc_hr_payroll_document_company', 'rule_sc_hr_salary_payment_company',
                  'rule_sc_salary_summary_company'):
        declaration = tree.xpath("//record[@id='%s']/field[@name='domain_force']" % xmlid)
        assert len(declaration) == 1, 'native rule declaration must be unique'
        installed = env.ref('smart_construction_core.' + xmlid, raise_if_not_found=False)
        matches = bool(installed and installed.active and not installed.groups
                       and installed.domain_force.strip() == declaration[0].text.strip()
                       and all((installed.perm_read, installed.perm_write,
                                installed.perm_create, installed.perm_unlink)))
        rules.append({'xmlid': xmlid, 'matches_source': matches})
        if not matches:
            blockers.append(xmlid + ':pending_rule_upgrade')
    print('PAYROLL_DATA_SCOPE_READINESS=' + json.dumps({
        'status': 'blocked' if blockers else 'scoped_preconditions_observed',
        'database': env.cr.dbname, 'registered_spaces': len(purposes),
        'model_counts': counts, 'payment_parent_mismatches': parent_mismatches,
        'payroll_project_mismatches': project_mismatches,
        'summary_missing_columns': missing_columns, 'rules': rules, 'blockers': blockers,
        'candidate_evidence': False, 'writes': False,
        'limitations': 'No actor acceptance, no data classification inference, no complete SQL view equivalence proof',
    }, ensure_ascii=False, sort_keys=True))
finally:
    env.cr.rollback()
    env.cr.commit = original_commit
