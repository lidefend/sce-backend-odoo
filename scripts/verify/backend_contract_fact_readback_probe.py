"""P4: one same-snapshot local.dev delivery, never a reusable CI result.

No product patches persist: the seal observer and request shims are scoped to
this disposable shell process and restored in finally. PostgreSQL READ ONLY
and a refused commit enforce the data boundary. No raw business values leave
this process; only input scope and digests are printed.
"""
from contextlib import contextmanager
from copy import deepcopy
import inspect
import hashlib
import os
import re
from pathlib import Path
import json

DATABASE = 'sc_dev_demo'
ROLE_XMLID = 'smart_construction_demo.user_demo_role_finance'
ACTION_XMLID = 'smart_construction_core.action_payment_request_pay'


def candidate_head_identity(environment=None):
    """Bind the readback report to an exact candidate head and tree.

    The runtime-sealed contract and facts only authorize reuse for the exact
    source they were read back from. When the probe is invoked without these
    two environment values it reports both as null and remains non-reusable.
    """
    environment = os.environ if environment is None else environment
    source_head = str(environment.get('CANDIDATE_GIT_HEAD') or '')
    source_tree = str(environment.get('CANDIDATE_GIT_TREE') or '')
    if source_head and not re.fullmatch('[0-9a-f]{40}', source_head):
        raise ValueError('candidate git head must be exact 40-hex when provided')
    if source_tree and not re.fullmatch('[0-9a-f]{40}', source_tree):
        raise ValueError('candidate git tree must be exact 40-hex when provided')
    return {'source_head': source_head or None, 'source_tree': source_tree or None}


def candidate_database(environment=None):
    """Resolve the registered database the probe must read back against.

    The local.dev default keeps the historical diagnostic entry working; a CI
    invocation passes CANDIDATE_DB_NAME so the same probe can bind the CI demo
    module fresh database instead of hard-coding sc_dev_demo.
    """
    environment = os.environ if environment is None else environment
    value = str(environment.get('CANDIDATE_DB_NAME') or DATABASE)
    if not value or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', value):
        raise ValueError('registered database name required')
    return value


def candidate_role_xmlid(environment=None):
    """Resolve the registered principal whose permission projection is read back."""
    environment = os.environ if environment is None else environment
    value = str(environment.get('CANDIDATE_ROLE_XMLID') or ROLE_XMLID)
    if not value or not re.fullmatch(r'[a-z_][a-z0-9_]*\.[a-z_][a-z0-9_]*', value):
        raise ValueError('registered role XMLID required')
    return value


def candidate_action_xmlid(environment=None):
    """Resolve the registered window action whose contract is read back."""
    environment = os.environ if environment is None else environment
    value = str(environment.get('CANDIDATE_ACTION_XMLID') or ACTION_XMLID)
    if not value or not re.fullmatch(r'[a-z_][a-z0-9_]*\.[a-z_][a-z0-9_]*', value):
        raise ValueError('registered action XMLID required')
    return value


@contextmanager
def observe_delivery(authority, observer):
    original = authority.seal_runtime_contract
    signature = inspect.signature(original)

    def wrapped(*args, **kwargs):
        bound = signature.bind(*args, **kwargs)
        bound.apply_defaults()
        # Capture AFTER the original seals: its source may be legitimately
        # completed during delivery. Do not mutate source or returned contract.
        result = original(*args, **kwargs)
        observer(bound.arguments, result)
        return result

    authority.seal_runtime_contract = wrapped
    try:
        yield
    finally:
        authority.seal_runtime_contract = original


def binding(lifecycle, source, contract):
    ok, reason = lifecycle.verify_unified_page_contract_integrity(contract)
    if not ok:
        raise ValueError('contract integrity: ' + str(reason))
    evidence = contract['meta']['lifecycle']
    source_hash = lifecycle.payload_sha256(lifecycle.strip_request_transport_identity(source))
    if not source or source_hash != evidence['generation']['sourceSha256']:
        raise ValueError('source fact binding mismatch')
    return {'source_sha256': source_hash, 'contract_sha256': evidence['integrity']['contractSha256'],
            'source_authority': deepcopy(evidence.get('authority')),
            'published_version_ref': evidence.get('definition', {}).get('publishedVersionRef')}


def authorized_dispatch(actor, user, shim, request, principal, context_class, permission, router):
    ctx = context_class(actor,user,request,request_obj=shim,principal=principal)
    if not permission.check_intent_permission(ctx):
        raise ValueError('intent permission denied')
    return router.route_intent_payload(request,ctx=ctx)


def assert_target(source, contract, model, record_id):
    page = contract.get('pageInfo') or {}
    main = (contract.get('dataContract') or {}).get('mainData') or {}
    identities = {'source_model':source.get('model'), 'contract_model':page.get('model'),
                  'contract_record_id':main.get('id'), 'expected_model':model, 'expected_record_id':record_id}
    if source.get('model') != model or page.get('model') != model or type(main.get('id')) is not int or main['id'] != record_id:
        raise ValueError('contract target mismatch: ' + json.dumps(identities,sort_keys=True))


# Comparison scope only, not product semantics. Relations and context-dependent
# transformations require their own declared projection proof before reuse.
DIRECT_SCALAR_TYPES = frozenset({'boolean','integer','float','monetary','char','text','selection','date','datetime'})
RELATION_TYPES = frozenset({'many2one','one2many','many2many'})


def value_parity(canonical_json, metadata, source_record, main_data, facts, relation_declarations=None):
    checked = []; uncovered = {}; mismatches = []
    if not all(isinstance(value,dict) for value in (metadata,source_record,main_data,facts)):
        raise ValueError('explicit source, projection and fact mappings required')
    declarations = relation_declarations or {}
    for name in sorted(set(main_data) | set(source_record)):
        if name == 'id':
            continue  # identity has its separate strict check, not a value test
        field = metadata.get(name)
        if field is None:
            uncovered[name] = 'not_a_native_field'
        elif (not field.get('store') or field.get('compute') or field.get('related')
              or field.get('translate') or field.get('company_dependent')):
            uncovered[name] = 'derived_or_context_dependent_field'
        elif field.get('type') in RELATION_TYPES:
            declared = declarations.get(name)
            if not (field.get('comodel_name') and isinstance(declared, dict)
                    and declared.get('model') == field.get('comodel_name')
                    and declared.get('can_read') is True):
                uncovered[name] = ('relation_target_not_declared' if not field.get('comodel_name')
                                   else 'relation_permission_projection_not_declared')
            elif name not in source_record or name not in main_data or name not in facts:
                uncovered[name] = 'missing_value_in_source_projection_or_readback'
            else:
                checked.append(name)
                values = [canonical_json(row[name]) for row in (source_record,main_data,facts)]
                if values[0] != values[1] or values[1] != values[2]:
                    mismatches.append(name)
        elif field.get('type') not in DIRECT_SCALAR_TYPES:
            uncovered[name] = 'relation_or_non_scalar_projection'
        elif name not in source_record or name not in main_data or name not in facts:
            uncovered[name] = 'missing_value_in_source_projection_or_readback'
        else:
            checked.append(name)
            # Use the existing delivery serializer. No string coercion, false/
            # null defaults, tolerance or fixture-specific exceptions.
            values = [canonical_json(row[name]) for row in (source_record,main_data,facts)]
            if values[0] != values[1] or values[1] != values[2]:
                mismatches.append(name)
    if not checked:
        raise ValueError('no comparable non-identity fact fields')
    return {'checked_fields':checked,'uncovered_fields':uncovered,'mismatch_fields':mismatches,
            'status':'failed' if mismatches else 'passed', 'full_projection_parity':not uncovered and not mismatches}


def declared_relation_projections(contract):
    """Extract declared relation projections from a ui.contract.v2 contract.

    Mirrors the browser relation probe: walk the contract for nodes carrying a
    relation_entry with a target model and a read permission. A relation field
    is comparable only when it is declared here; everything else stays uncovered.
    """
    out = {}

    def walk(node):
        if isinstance(node, list):
            for item in node:
                walk(item)
            return
        if not isinstance(node, dict):
            return
        field_info = node.get('fieldInfo') if isinstance(node.get('fieldInfo'), dict) else {}
        entry = field_info.get('relation_entry') or node.get('relation_entry') or node.get('relationEntry')
        name = str(node.get('name') or node.get('fieldName') or node.get('field_name') or '').strip()
        if isinstance(entry, dict) and name and name not in out:
            model = str(entry.get('model') or '').strip()
            can_read = entry.get('can_read')
            if isinstance(can_read, bool):
                out[name] = {'model': model, 'can_read': can_read}
        for value in node.values():
            walk(value)

    walk(contract)
    return out


def probe(env):
    from types import SimpleNamespace
    from odoo import api
    from odoo.tools.safe_eval import safe_eval
    from odoo.addons.smart_core.core import contract_lifecycle as lifecycle, intent_router
    from odoo.addons.smart_core.core.context import RequestContext
    from odoo.addons.smart_core.handlers import ui_contract_v2_authority as authority
    from odoo.addons.smart_core.security import intent_permission as ip

    identity = candidate_head_identity()
    database = candidate_database()
    role_xmlid = candidate_role_xmlid()
    action_xmlid = candidate_action_xmlid()
    if env.cr.dbname != database:
        raise ValueError('registered local.dev database required')
    env.cr.rollback()
    env.invalidate_all(flush=False)
    env.cr.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
    env.cr.execute("SELECT current_setting('transaction_read_only'), current_setting('transaction_isolation'), txid_current_snapshot()::text")
    readonly, isolation, snapshot = env.cr.fetchone()
    if readonly != 'on' or isolation != 'repeatable read':
        raise ValueError('consistent read-only snapshot required')
    original_commit = env.cr.commit
    original_ip, original_router = ip.request, intent_router.request

    def refuse_commit(*args, **kwargs):
        raise RuntimeError('fact readback forbids commit')

    env.cr.commit = refuse_commit
    try:
        user = env.ref(role_xmlid)
        if not user.active or user.share:
            raise ValueError('registered principal unavailable')
        company = user.company_id.id
        actor = api.Environment(env.cr, user.id, {'allowed_company_ids':[company], 'lang':'zh_CN'})
        if actor.su:
            raise ValueError('elevated actor forbidden')
        action = actor.ref(action_xmlid)
        if action._name != 'ir.actions.act_window' or not action.res_model:
            raise ValueError('registered window action required')
        model = action.res_model
        action_domain = safe_eval(action.domain or '[]', {'uid':actor.uid,'user':actor.user,'context':dict(actor.context)})
        if not isinstance(action_domain,list):
            raise ValueError('native action domain must be a list')
        record = actor[model].search(action_domain, order='id', limit=1)
        if not record:
            raise ValueError('no existing readable record; do not create a fixture')
        record.check_access_rights('read')
        record.check_access_rule('read')
        params = {'action_id':action.id, 'op':'action_open', 'record_id':record.id}
        shim = SimpleNamespace(env=actor,uid=user.id,session=SimpleNamespace(db=DATABASE,uid=user.id),
                               httprequest=SimpleNamespace(headers={},remote_addr='127.0.0.1'),
                               params={},jsonrequest=None)
        principal = {'auth_method':'password','principal_type':'human','user_id':user.id,'payload':{'db':DATABASE}}
        request = {'intent':'ui.contract.v2','params':params,'context':dict(actor.context),'meta':{}}
        ip.request = intent_router.request = shim
        captured = []

        def observe(arguments, result):
            owner = arguments['owner']
            if owner.env.cr is not actor.cr or owner.env.uid != actor.uid or owner.env.su:
                raise ValueError('delivery escaped actor or snapshot')
            source = arguments['source_payload']
            item = binding(lifecycle,source,result)
            assert_target(source,result,model,record.id)
            main = (result.get('dataContract') or {}).get('mainData') or {}
            names = sorted({'id','write_date'} & set(record._fields) |
                           {name for name in main if name in record._fields and record._fields[name].store})
            fact_record = owner.env[model].browse(record.id)
            facts = fact_record.read(names)
            metadata = {name:{'type':field.type,'store':bool(field.store),'compute':bool(field.compute),
                              'related':bool(field.related),'translate':bool(getattr(field,'translate',False)),
                              'company_dependent':bool(getattr(field,'company_dependent',False)),
                              'comodel_name':str(getattr(field,'comodel_name','') or '')}
                        for name,field in fact_record._fields.items() if name in main or name in (source.get('record') or {})}
            parity = value_parity(lifecycle.canonical_json,metadata,source.get('record'),main,facts[0],
                                  declared_relation_projections(result))
            if parity['mismatch_fields']:
                raise ValueError('source/projection/fact value mismatch fields: ' + ','.join(parity['mismatch_fields']))
            item.update(model=model, record_ids=record.ids, read_fields=names, value_parity=parity,
                        delivery_context_sha256=lifecycle.payload_sha256(dict(owner.env.context)),
                        comparison_metadata_sha256=lifecycle.payload_sha256(metadata),
                        business_facts_sha256=lifecycle.payload_sha256(facts),
                        source_payload_model=source.get('model'),
                        structure_sha256=lifecycle.payload_sha256({name:{'type':record._fields[name].type,
                            'relation':getattr(record._fields[name],'comodel_name',None),
                            'required':record._fields[name].required, 'readonly':record._fields[name].readonly}
                            for name in names}))
            # No raw values in the report. Keep an in-process equality witness.
            captured.append((item, facts, fact_record))

        with observe_delivery(authority,observe):
            result = authorized_dispatch(actor,user,shim,request,principal,RequestContext,ip,intent_router)
        envelope = result.to_legacy_dict() if hasattr(result,'to_legacy_dict') else result
        if not isinstance(envelope,dict) or envelope.get('ok') is not True or len(captured) != 1:
            raise ValueError('one successful observed delivery required')
        item, facts, fact_record = captured[0]
        final = envelope.get('data') or {}
        final_ok, _ = lifecycle.verify_unified_page_contract_integrity(final)
        if (not final_ok or final['meta']['lifecycle']['integrity']['contractSha256'] != item['contract_sha256']
                or fact_record.read(item['read_fields']) != facts):
            raise ValueError('final response or readback diverged')
        # Administrative reads inspect policy declarations only. Product dispatch
        # and business record reads above always use the unprivileged actor.
        domain = [('model_id.model','=',model)]
        access = env['ir.model.access'].search(domain).read(['group_id','perm_read','active'])
        rules = env['ir.rule'].search(domain).read(['groups','domain_force','perm_read','active'])
        return {'schema':'backend-contract-fact-readback/v1','database':database,
                **identity,
                'environment_purpose':'local collector diagnostic, not CI test receipt',
                'loaded_sources':{module.__name__:hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
                                  for module in (lifecycle,authority)},
                'actor':{'uid':actor.uid,'role_xmlid':role_xmlid,'company_id':company,
                         'groups_sha256':lifecycle.payload_sha256(sorted(actor.user.groups_id.ids)),
                         'context_sha256':lifecycle.payload_sha256(dict(actor.context))},
                'transaction':{'read_only':True,'isolation':isolation,'snapshot':snapshot},
                'request':{'intent':'ui.contract.v2',**params},'observation':item,
                'native_action':{'xmlid':action_xmlid,'id':action.id,'model':model,
                    'domain_sha256':lifecycle.payload_sha256(action_domain),
                    'context_sha256':lifecycle.payload_sha256(action.context)},
                'policy_declarations_sha256':lifecycle.payload_sha256({'access':access,'rules':rules}),
                'reuse_ready':False,'blockers':['not_ci_execution','query_dependency_closure_incomplete',
                    'related_model_permission_closure_incomplete','platform_execution_not_attested'] +
                    (['projection_value_coverage_incomplete'] if item['value_parity']['uncovered_fields'] else [])}
    finally:
        ip.request, intent_router.request = original_ip, original_router
        try:
            env.cr.rollback()
        finally:
            env.cr.commit = original_commit


if 'env' in globals():
    print('BACKEND_CONTRACT_FACT_READBACK=' + json.dumps(probe(globals()['env']),sort_keys=True))
