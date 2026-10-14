"""Read-only readiness of the generated SC data-scope company/purpose ceiling.

Executed only by local.dev.data_scope.ceiling.readiness in the registered demo DB.

Three facts are read back from the installed database, never inferred from source
text alone:

* the installed ceiling equals the committed generated source (identity, model,
  domain, perms, globality), so the source set is not a claim about runtime;
* the purpose partition is real: a customer principal and a non-customer
  principal resolve disjoint company realms through the single authority
  ``res.users._sc_data_company_ids()``;
* records whose ownership path is unset are not widenable: they stay invisible to
  an internal actor even though they exist, so a group union cannot expose them.

No business values, writes or fixtures are used.
"""
import json
import re
from lxml import etree
from odoo.exceptions import AccessError
from odoo.tools import file_open

assert env.cr.dbname == 'sc_dev_demo', 'requires the exact local.dev database'
env.cr.rollback()
original_commit = env.cr.commit


def reject_commit(*args, **kwargs):
    raise RuntimeError('data scope ceiling readiness forbids commit')


env.cr.commit = reject_commit

SOURCE_XML = 'smart_construction_core/security/sc_data_scope_ceiling_generated.xml'
MODULE = 'smart_construction_core'
IDENTIFIER = re.compile(r'^[a-z][a-z0-9_]*$')


def unset_owner_shape(domain: str) -> str:
    """``strict`` when the ceiling has no unset-owner branch, else ``shared``."""
    return "strict" if "'=', False" not in domain else "shared"

try:
    with file_open(SOURCE_XML, 'rb') as source:
        tree = etree.parse(source)
    declarations = []
    for node in tree.xpath("//record[@model='ir.rule']"):
        model_ref = node.xpath("field[@name='model_id']")[0].get('ref')
        domain = node.xpath("field[@name='domain_force']")[0].text.strip()
        declarations.append({
            'rule': node.get('id'),
            'rule_xmlid': MODULE + '.' + node.get('id'),
            'model_xmlid': model_ref if '.' in model_ref else MODULE + '.' + model_ref,
            'domain': domain,
        })

    # A. Installed ceiling equals committed source.
    mismatches = []
    resolved = []
    for decl in declarations:
        installed = env.ref(decl['rule_xmlid'], raise_if_not_found=False)
        target = env.ref(decl['model_xmlid'], raise_if_not_found=False)
        if not installed or not target:
            mismatches.append({'rule': decl['rule'], 'problems': ['missing_installed_rule_or_model']})
            continue
        problems = []
        if not installed.active:
            problems.append('inactive')
        if installed.groups:
            problems.append('group_bound')
        if installed.model_id.id != target.id:
            problems.append('wrong_model')
        if (installed.domain_force or '').strip() != decl['domain']:
            problems.append('domain_differs')
        if not all((installed.perm_read, installed.perm_write,
                    installed.perm_create, installed.perm_unlink)):
            problems.append('perm_gap')
        if problems:
            mismatches.append({'rule': decl['rule'], 'problems': problems})
        else:
            resolved.append({**decl, 'model': target.model,
                             'unset_owner': unset_owner_shape(decl['domain'])})

    # B. Purpose partition, read from persisted registrations and real principals.
    Registration = env['sc.tenant.company.registration'].sudo()
    registrations = Registration.search([('active', '=', True)])
    purpose_by_company = {r.company_id.id: r.data_purpose for r in registrations if r.company_id}
    purpose_counts = {}
    for purpose in purpose_by_company.values():
        purpose_counts[purpose] = purpose_counts.get(purpose, 0) + 1

    actor_scopes = []
    for user in env['res.users'].sudo().search(
            [('active', '=', True), ('share', '=', False)], order='id', limit=40):
        try:
            caller = env['res.users'].browse(user.id).with_user(user.id).with_context(
                allowed_company_ids=user.company_ids.ids)
            companies = list(caller._sc_data_company_ids())
        except Exception as error:  # a principal may legitimately hold no scope
            actor_scopes.append({'login': user.login, 'companies': None,
                                 'reason': type(error).__name__})
            continue
        purposes = sorted({purpose_by_company.get(company, 'unregistered') for company in companies})
        actor_scopes.append({'login': user.login, 'companies': companies, 'purposes': purposes})

    customer_scopes = [a for a in actor_scopes if a.get('purposes') and set(a['purposes']) == {'customer'}]
    non_customer_scopes = [a for a in actor_scopes
                           if a.get('purposes') and set(a['purposes']) <= {'demo', 'test'}]
    partition = {
        'customer_actors': len(customer_scopes),
        'non_customer_actors': len(non_customer_scopes),
        'disjoint': None,
    }
    if customer_scopes and non_customer_scopes:
        customer_companies = set(customer_scopes[0]['companies'])
        non_customer_companies = set(non_customer_scopes[0]['companies'])
        partition['disjoint'] = not (customer_companies & non_customer_companies)

    # C. Records with an unset ownership path exist and stay invisible to an actor.
    def internal_actors():
        return env['res.users'].sudo().search(
            [('active', '=', True), ('share', '=', False)], order='id')

    def visibility(model_name, domain, candidates):
        """First internal actor that may read the model; None when every ACL denies."""
        last_error = None
        for user in candidates:
            actor = env[model_name].with_user(user).with_context(allowed_company_ids=user.company_ids.ids)
            try:
                return actor.search_count(domain)
            except AccessError as error:
                last_error = type(error).__name__
        return last_error or 'no_internal_actor'

    candidates = internal_actors()
    unknown_owner = []
    for decl in resolved:
        anchor = decl['domain'].split("('", 1)[1].split("'", 1)[0]
        if '.' not in anchor:
            continue  # an own company_id column: NULL means shared configuration on purpose
        segments = anchor.split('.')
        company_field = segments[-1]
        hops = segments[:-1]
        model = env[decl['model']]
        # Resolve the anchor hop by hop: a detail model reaches the company
        # through a chain (settlement_id.project_id.company_id), so the check is
        # that every hop is a relation, not that the whole path is one field.
        joins, source_table, source_model = [], decl['model'].replace('.', '_'), model
        bad_hop = None
        for index, hop in enumerate(hops):
            relation = source_model._fields.get(hop)
            if relation is None or relation.type != 'many2one':
                bad_hop = hop
                break
            target = relation.comodel_name
            table = target.replace('.', '_')
            assert IDENTIFIER.match(table) and IDENTIFIER.match(hop), hop
            alias = 'r%d' % index
            joins.append('LEFT JOIN %s %s ON %s.id = %s.%s'
                         % (table, alias, alias, 't' if index == 0 else 'r%d' % (index - 1), hop))
            source_model, source_table = env[target], table
        if bad_hop is not None or company_field not in source_model._fields:
            unknown_owner.append({'rule': decl['rule'], 'model': decl['model'],
                                  'reason': 'anchor_is_not_a_relation',
                                  'anchor_hops': len(hops)})
            continue
        table = decl['model'].replace('.', '_')
        alias_last = 'r%d' % (len(hops) - 1)
        assert IDENTIFIER.match(table) and IDENTIFIER.match(company_field)
        unset_sql = ('SELECT COUNT(*) FROM %s t %s WHERE %s.%s IS NULL'
                     % (table, ' '.join(joins), alias_last, company_field))
        env.cr.execute('SELECT COUNT(*) FROM %s' % (table,))
        total = env.cr.fetchone()[0]
        env.cr.execute(unset_sql)
        unset = env.cr.fetchone()[0]
        visible = None
        if unset:
            # The unset-ownership records themselves, addressed by primary key, so
            # the count isolates the ceiling and not the actor's other filters.
            env.cr.execute(unset_sql.replace('SELECT COUNT(*)', 'SELECT t.id', 1))
            identifiers = [row[0] for row in env.cr.fetchall()]
            visible = visibility(decl['model'], [('id', 'in', identifiers)], candidates)
        # Does the unset-owner branch itself even match the unset rows? A dotted
        # left-hand side with ``= False`` compiles to SQL NULL = FALSE, which is
        # NULL rather than true, so the declared branch is not inert by accident.
        pass_through = env[decl['model']].sudo().search_count([(anchor, '=', False)]) if unset else None
        unknown_owner.append({'rule': decl['rule'], 'model': decl['model'],
                              'unset_owner': decl['unset_owner'],
                              'records': total,
                              'unset_ownership_records': unset,
                              'unset_owner_branch_matches': pass_through,
                              'internal_actor_visible_records': visible})

    registrations_all = env['sc.tenant.company.registration'].sudo().search([])
    purpose_of_company = {r.company_id.id: (r.data_purpose, r.active) for r in registrations_all}

    def _purpose_for(company_id):
        entry = purpose_of_company.get(company_id)
        return None if entry is None else {'purpose': entry[0], 'active': entry[1]}

    # D. Scope impact of the purpose term on real product models.
    def company_distribution(model_name):
        """Rows per owning company for a probe model, from one bounded group-by.

        The purpose term hides a whole company realm, so the blocker is only
        explainable together with where the rows actually live: a demo realm
        whose rows sit in an unregistered company is an environment-provisioning
        fact, not a rule defect.
        """
        if model_name not in env:
            return None
        table = model_name.replace('.', '_')
        assert IDENTIFIER.match(table), 'unexpected identifier in metadata: ' + table
        column = 'company_id' if 'company_id' in env[model_name]._fields else None
        if column is None:
            return None
        env.cr.execute(
            'SELECT %s, COUNT(*) FROM %s GROUP BY %s ORDER BY %s'
            % (column, table, column, column))
        return {('none' if company is None else str(company)): count
                for company, count in env.cr.fetchall()}

    scope_probe = []
    for model_name in ('payment.request', 'sc.general.contract', 'project.project',
                       'sc.business.category', 'ui.form.field.policy', 'res.users'):
        if model_name not in env:
            continue
        scope_probe.append({
            'model': model_name,
            'sudo_records': env[model_name].sudo().search_count([]),
            'company_distribution': company_distribution(model_name),
            'internal_actor_visible': visibility(model_name, [], candidates),
        })

    # D2. The platform bootstrap company must not own business rows: a record
    # under the technical carrier has no registered owner, so nothing can decide
    # whether it belongs to a customer, demo or test realm.
    bootstrap_probe = []
    for model_name in ('payment.request', 'sc.general.contract', 'project.project',
                       'sc.business.category'):
        if model_name not in env or 'company_id' not in env[model_name]._fields:
            continue
        for company in env['res.company'].sudo().search(
                [('is_platform_bootstrap_company', '=', True)]):
            rows = env[model_name].sudo().search_count([('company_id', '=', company.id)])
            if rows:
                bootstrap_probe.append({'model': model_name, 'company_id': company.id,
                                        'company_name': company.name, 'records': rows})

    # E. Platform contract carriers stay readable for an internal actor.
    carriers = {}
    for model_name in ('ui.menu.config.policy', 'ui.form.field.policy'):
        if model_name not in env:
            carriers[model_name] = None
            continue
        total = env[model_name].sudo().search_count([])
        carriers[model_name] = {'records': total,
                               'internal_actor_visible': visibility(model_name, [], candidates)}

    blockers = []
    if mismatches:
        blockers.append('installed_ceiling_differs_from_source')
    if partition['disjoint'] is False:
        blockers.append('customer_and_non_customer_scopes_overlap')
    if not customer_scopes or not non_customer_scopes:
        blockers.append('purpose_partition_not_observable_with_real_actors')
    for row in unknown_owner:
        unset = row.get('unset_ownership_records')
        visible = row.get('internal_actor_visible_records')
        if not unset or not isinstance(visible, int):
            continue  # nothing to observe, or no internal actor holds read ACL
        if row['unset_owner'] == 'strict' and visible:
            blockers.append('declared_unknown_ownership_is_visible:' + row['rule'])
        if row['unset_owner'] == 'shared' and not visible:
            blockers.append('shared_reference_was_hidden:' + row['rule'])
    for row in bootstrap_probe:
        blockers.append('bootstrap_company_carries_business_data:%s:%s'
                        % (row['company_id'], row['model']))
    carrier_rows = [c for c in carriers.values() if isinstance(c, dict)]
    if any(value is None for value in carriers.values()):
        blockers.append('contract_carrier_model_absent')
    elif carrier_rows and all(c['records'] and c['internal_actor_visible'] == 0
                              for c in carrier_rows):
        blockers.append('contract_carrier_not_readable_for_internal_actor')

    print('DATA_SCOPE_CEILING_READINESS=' + json.dumps({
        'status': 'blocked' if blockers else 'installed_ceiling_observed',
        'database': env.cr.dbname,
        'source_rule_count': len(declarations),
        'installed_match_count': len(resolved),
        'strict_rule_count': sum(1 for d in declarations if unset_owner_shape(d['domain']) == 'strict'),
        'strict_models': sorted(d['model_xmlid'] for d in declarations
                               if unset_owner_shape(d['domain']) == 'strict'),
        'mismatches': mismatches,
        'registered_companies_by_purpose': purpose_counts,
        'actor_scopes': actor_scopes,
        'purpose_partition': partition,
        'unset_ownership': unknown_owner,
        'hidden_unset_ownership': sorted(r['model'] for r in unknown_owner
                                         if r.get('unset_ownership_records')
                                         and r.get('internal_actor_visible_records') == 0),
        'scope_probe': scope_probe,
        'registration_rows_total': env['sc.tenant.company.registration'].sudo().search_count([]),
        'companies': [
            {'id': c.id, 'name': c.name,
             'bootstrap': bool(c.is_platform_bootstrap_company),
             'data_purpose_effective': _purpose_for(c.id)}
            for c in env['res.company'].sudo().search([], order='id')
        ],
        'bootstrap_company_business_data': bootstrap_probe,
        'contract_carriers': carriers,
        'blockers': blockers,
        'candidate_evidence': False,
        'writes': False,
        'limitations': 'No business-value or ACL-actor acceptance, no group-union bypass simulation, no SQL view equivalence proof',
    }, ensure_ascii=False, sort_keys=True))
finally:
    env.cr.rollback()
    env.cr.commit = original_commit
