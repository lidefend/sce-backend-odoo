"""P4 daily diagnosis: rollback-only shell probes; bounded native HTTP profiler controls."""
REQUESTS = [{'intent': 'system.init', 'params': {'scene': 'web', 'with_preload': False, 'scene_ready_mode': 'registry', 'with': ['workspace_home'], 'company_id': 1, 'context': {'company_id': 1}}}, {'intent': 'ui.contract.v2', 'params': {'op': 'action_open', 'action_id': 588, 'record_id': 1, 'view_type': 'form', 'render_profile': 'edit', 'contract_surface': 'user', 'source_mode': 'governance_pipeline', 'context': {'company_id': 1}, 'scene_key': 'entry.smart_construction_core.menu_sc_project_project', 'menu_id': 382, 'delivery_profile': 'full', 'client_type': 'web_pc', 'accepted_contract_versions': ['2.0.x', '2.1.x', '2.2.x'], 'client_contract_capabilities': ['container_tree.v2', 'data_source.v2', 'action_rule.v2', 'relation_entry.v2', 'status_contract.v2', 'form_layout.children_owner.v1', 'form.feedback.message.v1', 'form.feedback.draft.v1', 'form.navigation.anchor.v1']}}]
EXPECTED_SOURCES = {'addons/smart_core/handlers/system_init.py': '5b15f6592b60bf3b39d20130b95f2a3ff2b60cb54e7f2c531902e4b86857de41', 'addons/smart_core/handlers/ui_contract_v2.py': 'e9f08bd529841199185d4415aedc879fa5fe9a81d6b84b57068878f5a7145627'}
import os
import gc
import re
import functools
import cProfile
import hashlib
import inspect
import json
import pstats
import time
from collections import defaultdict
from contextlib import nullcontext, contextmanager
import copy
import sys
from pathlib import Path


def summarize_collectors(profiler):
    result = {}
    for collector in profiler.collectors:
        entries = collector.entries
        if collector.name == 'sql':
            groups = {}
            for entry in entries:
                frames = entry['stack']
                project = [(f, line, name) for f, line, name, _ in frames if '/smart_' in f or '/smart_construction_' in f]
                nearest = project[-1] if project else ('unattributed', 0, '')
                # Never export parameter values; keep a structural query template and opaque repeat identity.
                query = re.sub(r"'(?:''|[^'])*'", '?', entry.get('query', ''))
                query = re.sub(r'\b\d+(?:\.\d+)?\b', '?', query)
                query = re.sub(r'\s+', ' ', query).strip()
                target = hashlib.sha256(entry.get('full_query', '').encode()).hexdigest()
                key = (nearest, query)
                row = groups.setdefault(key, {'project_site': nearest, 'template': query, 'count': 0,
                                               'sql_ms': 0.0, 'target_counts': {}, 'ancestor_context': project})
                row['count'] += 1
                row['sql_ms'] += entry.get('time', 0) * 1000
                row['target_counts'][target] = row['target_counts'].get(target, 0) + 1
            rows = sorted(groups.values(), key=lambda x: x['sql_ms'], reverse=True)
            for row in rows:
                row['unique_targets'] = len(row['target_counts'])
                row['repeated_target_calls'] = row['count'] - row['unique_targets']
            result['sql'] = {'count': len(entries), 'group_count_sum': sum(r['count'] for r in rows),
                             'total_ms': sum(e.get('time', 0) * 1000 for e in entries), 'groups': rows}
        else:
            result[collector.name] = [{'start': e['start'], 'stack': [(f, line, name) for f, line, name, _ in e['stack']]} for e in entries]
    return result


@contextmanager
def record_read_observation(actor):
    from odoo.models import BaseModel
    original = BaseModel.read
    events = []
    @functools.wraps(original)
    def measured(records, *args, **kwargs):
        if records._name != 'project.project' or 1 not in records.ids or records.env.uid != actor.uid:
            return original(records, *args, **kwargs)
        names = (args[0] if args else kwargs.get('fields')) or list(records._fields)
        event = {'fields': list(names), 'nonstored_compute': [
            {'name': name, 'compute': str(records._fields[name].compute)} for name in names
            if name in records._fields and records._fields[name].compute and not records._fields[name].store],
            'caller': (sys._getframe(1).f_code.co_filename, sys._getframe(1).f_lineno, sys._getframe(1).f_code.co_name)}
        started = time.perf_counter()
        try:
            return original(records, *args, **kwargs)
        except Exception as exc:
            event['exception_type'] = type(exc).__name__
            raise
        finally:
            event['elapsed_ms'] = (time.perf_counter() - started) * 1000
            events.append(event)
    BaseModel.read = measured
    try:
        yield events
    finally:
        BaseModel.read = original


@contextmanager
def bounded_copy_timing():
    """Time addon deepcopy call sites without wrapping recursive copy internals."""
    original = copy.deepcopy
    patches = []
    rows = {}
    def measured(value, *args, **kwargs):
        frame = sys._getframe(1)
        key = (frame.f_code.co_filename, frame.f_code.co_name, frame.f_lineno)
        started = time.perf_counter()
        try:
            return original(value, *args, **kwargs)
        finally:
            row = rows.setdefault(key, {'file': key[0], 'function': key[1], 'line': key[2], 'calls': 0, 'elapsed_ms': 0})
            row['calls'] += 1
            row['elapsed_ms'] += (time.perf_counter() - started) * 1000
    for name, module in list(sys.modules.items()):
        if name.startswith('odoo.addons.') and getattr(module, 'deepcopy', None) is original:
            patches.append(module)
            module.deepcopy = measured
    try:
        yield rows
    finally:
        for module in patches:
            module.deepcopy = original


OBSERVED_XMLID_IDS = {'res.groups': set(), 'ir.ui.menu': set()}


@contextmanager
def batch_xmlid_diagnostic(actor, mode):
    """Counterfactual over IDs observed on earlier control paths in this process."""
    from odoo.addons.smart_core.delivery.menu_service import MenuService
    from odoo.addons.smart_construction_core.services import scenario_surface_projection as surface
    old_group = MenuService.__dict__['_record_xmlid']
    old_menu = surface._menu_external_id
    maps = {}
    def resolve(record, kind, fallback):
        seen = OBSERVED_XMLID_IDS[kind]
        enabled = mode == 'batch_xmlid' or (kind == 'res.groups' and mode == 'batch_groups') or (kind == 'ir.ui.menu' and mode == 'batch_menus')
        if not enabled or record.id not in seen:
            seen.add(record.id)
            return fallback()
        if kind not in maps:
            try:
                maps[kind] = actor[kind].sudo().browse(sorted(seen)).get_external_id()
            except Exception:
                maps[kind] = None
        if maps[kind] is None or record.id not in maps[kind]:
            return fallback()
        value = maps[kind].get(record.id)
        return str(value or '').strip()
    def group_xmlid(record):
        if record._name != 'res.groups':
            return old_group.__func__(record)
        return resolve(record, 'res.groups', lambda: old_group.__func__(record))
    def menu_xmlid(env, menu):
        return resolve(menu, 'ir.ui.menu', lambda: old_menu(env, menu))
    MenuService._record_xmlid = staticmethod(group_xmlid)
    surface._menu_external_id = menu_xmlid
    try:
        yield
    finally:
        MenuService._record_xmlid = old_group
        surface._menu_external_id = old_menu


@contextmanager
def menu_children_diagnostic(actor, enabled):
    """Use the exact all_menus recordset already selected by the generating frame."""
    owner = type(actor['ir.ui.menu'])
    local = owner.__dict__.get('search')
    original = owner.search
    index = None
    stats = {'intercepted_calls': 0, 'source_menu_count': 0}
    @functools.wraps(original)
    def search(records, domain, *args, **kwargs):
        nonlocal index
        frame = sys._getframe(1)
        matches = (enabled and frame.f_code.co_name == 'collect' and frame.f_code.co_filename.endswith('/app_nav_config.py')
                   and isinstance(domain, list) and len(domain) == 2 and domain[0][:2] == ('parent_id', '=')
                   and domain[1] == ('active', '=', True) and kwargs.get('order') == 'sequence,id'
                   and not args and set(kwargs) == {'order'})
        if not matches:
            return original(records, domain, *args, **kwargs)
        if index is None:
            parent = frame
            while parent and parent.f_code.co_name != '_generate_from_menus':
                parent = parent.f_back
            if parent is None or 'all_menus' not in parent.f_locals:
                return original(records, domain, *args, **kwargs)
            menus = parent.f_locals['all_menus']
            index = {}
            for menu in menus:
                index.setdefault(menu.parent_id.id, []).append(menu.id)
            stats['source_menu_count'] = len(menus)
        stats['intercepted_calls'] += 1
        return records.browse(index.get(domain[0][2], []))
    owner.search = search
    try:
        yield stats
    finally:
        if local is None:
            delattr(owner, 'search')
        else:
            owner.search = local


@contextmanager
def gc_observation():
    events = []
    starts = {}
    def callback(phase, info):
        generation = info['generation']
        if phase == 'start':
            frame = sys._getframe(1)
            stack = []
            while frame:
                if '/smart_' in frame.f_code.co_filename:
                    stack.append((frame.f_code.co_filename, frame.f_lineno, frame.f_code.co_name))
                frame = frame.f_back
            starts[generation] = (time.perf_counter(), stack)
        elif generation in starts:
            started, stack = starts.pop(generation)
            events.append({'generation': generation, 'elapsed_ms': (time.perf_counter() - started) * 1000,
                           'collected': info.get('collected'), 'stack': stack})
    gc.callbacks.append(callback)
    try:
        yield events
    finally:
        gc.callbacks.remove(callback)


OBSERVED_ACTION_IDS = {}


@contextmanager
def action_prefetch_diagnostic(actor, enabled):
    """Prefetch only action IDs reached by earlier controls; preserve the original assembler."""
    owner = type(actor['app.menu.config'])
    local = owner.__dict__.get('_action_summary')
    original = owner._action_summary
    prepared = set()
    stats = {'calls': 0, 'prefetched_models': {}, 'prefetch_ms': 0.0}
    @functools.wraps(original)
    def summary(records, action):
        if not action:
            return original(records, action)
        key = (action._name, action.env.uid, action.env.su, repr(sorted(action.env.context.items())))
        known = OBSERVED_ACTION_IDS.setdefault(key, set())
        if not enabled or action.id not in known:
            known.add(action.id)
            return original(records, action)
        stats['calls'] += 1
        if key not in prepared:
            batch = action.browse(sorted(known))
            names = [n for n in ('name', 'res_model', 'view_mode', 'view_id', 'view_ids') if n in batch._fields]
            started = time.perf_counter()
            batch.fetch(names)
            if action._name == 'ir.actions.act_window':
                bindings = batch.mapped('view_ids')
                bindings.fetch(['view_id'])
                bindings.mapped('view_id').fetch(['type'])
            stats['prefetch_ms'] += (time.perf_counter() - started) * 1000
            stats['prefetched_models'][action._name] = len(batch)
            prepared.add(key)
        return original(records, action)
    owner._action_summary = summary
    try:
        yield stats
    finally:
        if local is None:
            delattr(owner, '_action_summary')
        else:
            owner._action_summary = local


@contextmanager
def contract_clone_diagnostic(enabled):
    from odoo.addons.smart_core.handlers import ui_contract_v2
    from odoo.addons.smart_core.core import unified_page_contract_v2_assembler
    from odoo.addons.smart_core.utils.load_contract_response_cache import isolated_clone
    patches = []
    stats = {'calls': 0, 'input_types': {}}
    def make_wrapper(original):
        def clone(value, *args, **kwargs):
            stats['calls'] += 1
            name = type(value).__name__
            stats['input_types'][name] = stats['input_types'].get(name, 0) + 1
            if enabled and not args and not kwargs:
                return isolated_clone(value)
            return original(value, *args, **kwargs)
        return clone
    for module in (ui_contract_v2, unified_page_contract_v2_assembler):
        original = module.deepcopy
        patches.append((module, original))
        module.deepcopy = make_wrapper(original)
    try:
        yield stats
    finally:
        for module, original in patches:
            module.deepcopy = original


@contextmanager
def cache_identity_observation(actor, enabled):
    from odoo.addons.smart_core.handlers import ui_contract_v2
    original = ui_contract_v2.build_projection_cache_key
    result = {}
    def key(env, **kwargs):
        actual = original(env, **kwargs)
        result.update({'actual_key': actual, 'context': dict(env.context), 'kwargs': kwargs})
        return actual
    if enabled:
        ui_contract_v2.build_projection_cache_key = key
    try:
        yield result
    finally:
        ui_contract_v2.build_projection_cache_key = original
        if enabled and result:
            matches = []
            for lang in (None, 'zh_CN', 'en_US'):
                for tz in (None, 'Asia/Shanghai'):
                    for companies in ([1], [1, 2]):
                        context = dict(result['context'])
                        for name, value in (('lang', lang), ('tz', tz)):
                            if value is None:
                                context.pop(name, None)
                            else:
                                context[name] = value
                        context['allowed_company_ids'] = companies
                        arguments = dict(result['kwargs'], context=context)
                        identity = original(actor, **arguments)
                        if identity.startswith('393a9b72ccd6'):
                            matches.append({'lang': lang, 'tz': tz, 'allowed_company_ids': companies, 'identity': identity})
            result['http_identity_matches'] = matches


def changed_paths(before, after, path=''):
    if type(before) is not type(after):
        return [path]
    if isinstance(before, dict):
        changes = []
        for key in sorted(set(before) | set(after)):
            child = path + '/' + str(key)
            changes.extend([child] if key not in before or key not in after else changed_paths(before[key], after[key], child))
        return changes
    if isinstance(before, list):
        if len(before) != len(after):
            return [path + '/length']
        return [p for i, (a, b) in enumerate(zip(before, after)) for p in changed_paths(a, b, path + '/' + str(i))]
    return [] if before == after else [path]


def http_profile_control(env, phase):
    """Only native diagnostic config/results; never alters business records."""
    from datetime import datetime, timedelta
    from types import SimpleNamespace
    from odoo import tools
    assert env.cr.dbname == 'sc_demo'
    assert tools.config['dbfilter'] == '^sc_demo$'
    print('DAILY_HTTP_STORAGE=' + json.dumps({'data_dir': str(tools.config['data_dir']), 'filestore': tools.config.filestore(env.cr.dbname)}), flush=True)
    assert str(tools.config['data_dir']) == '/opt/sce-runtime'
    assert tools.config.filestore(env.cr.dbname) == '/opt/sce-runtime/filestore/sc_demo'
    nonce = os.environ['DAILY_HTTP_PROFILE_NONCE']
    assert re.fullmatch(r'r6_[a-z0-9]{8,24}', nonce)
    key = 'base.profiling_enabled_until'
    if phase == 'http_status':
        env.cr.execute('SET TRANSACTION READ ONLY')
        row = env['ir.config_parameter'].sudo().search([('key', '=', key)])
        print('DAILY_HTTP_CONFIG_STATUS=' + json.dumps({'exists': bool(row), 'value': row.value if row else None, 'now_utc': str(datetime.utcnow())}), flush=True)
        env.cr.rollback()
        return
    if phase == 'http_export':
        env.cr.execute('SET TRANSACTION READ ONLY')
        profiles = env['ir.profile'].sudo().search([('name', 'like', 'sce_perf=' + nonce)], order='id', limit=101)
        assert len(profiles) < 101, "profile export truncated"
        from urllib.parse import urlsplit, parse_qs
        profiles = profiles.filtered(lambda p: parse_qs(urlsplit(p.name).query).get("sce_perf") == [nonce])
        assert len(set(profiles.mapped("session"))) <= 1, "mixed profiling sessions"
        rows = []
        for profile in profiles:
            collectors = [SimpleNamespace(name=name, entries=json.loads(profile[name] or '[]')) for name in ('sql', 'traces_async')]
            rows.append({'id': profile.id, 'session': profile.session, 'name': profile.name,
                         'duration_ms': profile.duration * 1000, 'sql_count': profile.sql_count,
                         'entry_count': profile.entry_count,
                         'collectors': summarize_collectors(SimpleNamespace(collectors=collectors))})
        print('DAILY_HTTP_PROFILES=' + json.dumps(rows, ensure_ascii=False), flush=True)
        env.cr.rollback()
        return
    assert phase == 'http_window'
    config = env['ir.config_parameter'].sudo()
    # Also serialize creation when the key does not exist. Held only until setup commit.
    env.cr.execute("SET LOCAL lock_timeout = '2s'")
    env.cr.execute('LOCK TABLE ir_config_parameter IN SHARE ROW EXCLUSIVE MODE')
    env.cr.execute('SELECT id, value FROM ir_config_parameter WHERE key=%s FOR UPDATE', [key])
    previous = env.cr.fetchone()
    old = previous[1] if previous else None
    # Do not interfere with a different active profiling window.
    assert not old or old < str(datetime.utcnow()), 'another profiling window active'
    expiry = (datetime.utcnow() + timedelta(seconds=240)).strftime('%Y-%m-%d %H:%M:%S')
    print('DAILY_HTTP_WINDOW_SNAPSHOT=' + json.dumps({'old': old, 'owned': expiry, 'nonce': nonce}), flush=True)
    try:
        config.set_param(key, expiry)
        env.cr.commit()
        print('DAILY_HTTP_WINDOW_READY=' + json.dumps({'owned': expiry, 'nonce': nonce}), flush=True)
        # Bounded window; restoration is in this same process, even on exceptions.
        for _ in range(18):
            time.sleep(10)
    finally:
        env.cr.rollback()
        env.invalidate_all()
        env.cr.execute('SELECT id, value FROM ir_config_parameter WHERE key=%s FOR UPDATE', [key])
        current = env.cr.fetchone()
        assert current and current[1] == expiry, 'config ownership changed; refusing overwrite'
        row = config.browse(current[0])
        if old is None:
            row.unlink()
        else:
            row.write({'value': old})
        env.cr.commit()
        env.invalidate_all()
        row = config.search([('key', '=', key)])
        assert (row.value if row else None) == old
        print('DAILY_HTTP_WINDOW_RESTORED=' + json.dumps({'restored': True, 'nonce': nonce}), flush=True)


def run(env):
    if os.environ.get('DAILY_PERFORMANCE_PHASE', '').startswith('http_'):
        return http_profile_control(env, os.environ['DAILY_PERFORMANCE_PHASE'])
    from odoo import api, release
    from odoo.tools.profiler import Profiler
    from odoo.addons.smart_core.handlers.system_init import SystemInitHandler
    from odoo.addons.smart_core.handlers.ui_contract_v2 import UiContractV2Handler
    from odoo.addons.smart_core.core.intent_execution_result import adapt_handler_result
    assert env.cr.dbname == 'sc_demo', 'registered demo database required'
    owners = {'system.init': SystemInitHandler, 'ui.contract.v2': UiContractV2Handler}
    sources = {}
    for intent, owner in owners.items():
        source = Path(inspect.getsourcefile(owner))
        relative = 'addons/smart_core/handlers/' + source.name
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        assert digest == EXPECTED_SOURCES[relative], 'deployed handler differs from observed baseline'
        sources[intent] = {'sha256': digest, 'path': str(source)}
    report = {'schema': 'daily-runtime-performance-diagnosis/v1', 'odoo_version': release.version,
              'sources': sources, 'user': 'demo_full', 'uid': 42, 'company_id': 1,
              'allowed_company_ids': [1, 2], 'database': 'sc_demo', 'samples': [],
              'limits': ['BaseIntentHandler.run in isolated shell process; no HTTP dispatcher/session', 'fresh cursor per sample; process caches warm across samples',
                         'profiler overhead excluded only in unprofiled samples', 'no network/queue/browser interactivity measurement']}
    phase = os.environ.get('DAILY_PERFORMANCE_PHASE', 'r3')
    report['phase'] = phase
    selected_requests = REQUESTS[1:] if phase in ('r4_gc', 'r5_clone', 'r5_identity') else REQUESTS if phase == 'r4_profile' else REQUESTS[:1]
    for request_index, request in enumerate(selected_requests):
        baseline_data = None
        modes = ('warmup', 'unprofiled', 'attribution', 'unprofiled') if phase == 'r4_profile' else ('warmup', 'control', 'batch_xmlid', 'control', 'batch_xmlid')
        if phase == 'r4_children':
            modes = ('warmup', 'unprofiled', 'children_index', 'unprofiled', 'children_index')
        if phase == 'r4_gc':
            modes = ('warmup', 'unprofiled', 'unprofiled', 'unprofiled')
        if phase == 'r5_actions':
            modes = ('warmup', 'unprofiled', 'action_prefetch', 'unprofiled', 'action_prefetch')
        if phase == 'r5_clone':
            modes = ('warmup', 'unprofiled', 'isolated_clone', 'unprofiled', 'isolated_clone')
        if phase == 'r5_identity':
            modes = ('unprofiled',)
        for sample_index, mode in enumerate(modes):
            # Fresh transaction matches the independent RPC cache boundary.
            with env.registry.cursor() as cr:
                cr.execute('SET TRANSACTION READ ONLY')
                cr.execute("SET LOCAL statement_timeout = '25000'")
                commit = cr.commit
                def refuse_commit(*args, **kwargs):
                    raise RuntimeError('diagnostic forbids commit')
                cr.commit = refuse_commit
                try:
                    actor = api.Environment(cr, 42, {'lang': 'zh_CN', 'tz': 'Asia/Shanghai',
                                                    'allowed_company_ids': [1, 2], 'company_id': 1})
                    assert actor.user.login == 'demo_full' and actor.user.active
                    assert actor.company.id == 1 and {1, 2}.issubset(set(actor.user.company_ids.ids))
                    assert actor['project.project'].browse(1).exists()
                    if mode == 'warmup' and request['intent'] == 'system.init':
                        menu = actor['app.menu.config'].sudo().with_context(active_test=False)
                        configs = menu.search([('target_model', '=', '__all__'), ('scene', '=', 'web'), ('company_id', '=', 1)])
                        print('DAILY_PERFORMANCE_CACHE=' + json.dumps({'actor_context': dict(actor.context), 'domain': menu._menu_config_domain(), 'configs': [{'id': c.id, 'lang': c.lang, 'active': c.is_active, 'version': c.version, 'metadata_changed': menu._menu_metadata_changed_since(c)} for c in configs]}, default=str), flush=True)
                    profiler = Profiler(collectors=['sql', 'traces_async'], db=None,
                                        params={'time_limit': 40, 'entry_count_limit': 40000}) if mode in ('sql_periodic', 'attribution') else None
                    cp = cProfile.Profile() if mode in ('cprofile', 'attribution') else None
                    before = cr.sql_log_count
                    started = time.perf_counter()
                    if cp:
                        cp.enable()
                    try:
                        with (profiler if profiler is not None else nullcontext()), (bounded_copy_timing() if mode == 'bounded_copy' else nullcontext()) as copy_rows, batch_xmlid_diagnostic(actor, 'batch_xmlid' if phase.startswith(('r4', 'r5')) and mode != 'warmup' else mode), (record_read_observation(actor) if mode == 'attribution' else nullcontext()) as read_events, menu_children_diagnostic(actor, mode == 'children_index' or (phase == 'r5_actions' and mode != 'warmup')) as child_stats, (gc_observation() if phase == 'r4_gc' else nullcontext()) as gc_events, action_prefetch_diagnostic(actor, mode == 'action_prefetch') as action_stats, (contract_clone_diagnostic(mode == 'isolated_clone') if phase == 'r5_clone' else nullcontext()) as clone_stats, cache_identity_observation(actor, phase == 'r5_identity') as identity_stats:
                            reply = adapt_handler_result(owners[request['intent']](env=actor).run(payload={'intent': request['intent'], 'params': request['params']}))
                    finally:
                        if cp:
                            cp.disable()
                    elapsed = (time.perf_counter() - started) * 1000
                    sample = {'intent': request['intent'], 'params': request['params'], 'mode': mode,
                              'sample_id': f'{request_index}:{sample_index}:{mode}', 'elapsed_ms': elapsed, 'sql_start': before, 'sql_end': cr.sql_log_count, 'sql_count': cr.sql_log_count - before, 'collection_mode': {'sql_periodic': profiler is not None, 'cprofile': cp is not None, 'record_read_observer': mode == 'attribution'},
                              'data_sha256': hashlib.sha256(json.dumps(reply.get('data'), ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest(), 'ok': reply.get('ok'), 'meta': {k: v for k, v in reply.get('meta', {}).items() if k in ('elapsed_ms', 'startup_profile', 'projection_cache')}}
                    if baseline_data is None and mode in ('control', 'unprofiled'):
                        baseline_data = json.loads(json.dumps(reply.get('data'), default=str))
                    sample['changed_data_paths'] = changed_paths(baseline_data, json.loads(json.dumps(reply.get('data'), default=str))) if baseline_data is not None else []
                    if not sample['ok']:
                        sample['error'] = reply.get('error')
                    if copy_rows is not None:
                        sample['copy_sites'] = sorted(copy_rows.values(), key=lambda r: r['elapsed_ms'], reverse=True)
                    sample['children_index'] = child_stats
                    sample['action_prefetch'] = action_stats
                    if identity_stats:
                        sample['cache_identity'] = identity_stats
                    if clone_stats is not None:
                        sample['contract_clone'] = clone_stats
                    if gc_events is not None:
                        sample['gc_events'] = gc_events
                    if read_events is not None:
                        sample['record_reads'] = read_events
                    if profiler:
                        sample['collectors'] = summarize_collectors(profiler)
                        sql = sample['collectors']['sql']
                        sample['sql_coverage'] = {'group_counts_match_collector': sql['count'] == sql['group_count_sum'], 'collector_minus_main_cursor': sql['count'] - sample['sql_count']}
                        sample['wall_time_minus_collected_sql_ms'] = elapsed - sql['total_ms']
                        sample['residual_label'] = 'not CPU: includes Python, collector overhead, waits and any uncovered work'
                    if cp:
                        rows = []
                        for (file, line, name), (primitive, calls, own, cumulative, callers) in pstats.Stats(cp).stats.items():
                            rows.append({'file': file, 'line': line, 'function': name, 'calls': calls,
                                         'self_ms': own * 1000, 'cumulative_ms': cumulative * 1000,
                                         'callers': [{'file': f, 'line': l, 'function': n, 'stats': s} for (f, l, n), s in callers.items()]})
                        sample['functions'] = sorted(rows, key=lambda r: r['cumulative_ms'], reverse=True)
                    report['samples'].append(sample)
                    print('DAILY_PERFORMANCE_SAMPLE=' + json.dumps(sample, ensure_ascii=False, default=str), flush=True)
                    assert sample['ok'], 'handler failed; no passing attribution'
                finally:
                    cr.rollback()
                    cr.commit = commit
    report['status'] = 'observed'
    print('DAILY_PERFORMANCE_REPORT=' + json.dumps(report, ensure_ascii=False, default=str), flush=True)
    return report


def local_main(argv=None):
    """Replay a diagnostic phase through its governed Make entry, never raw SSH."""
    import argparse
    import subprocess
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', required=True, choices=[
        'r3', 'r4_profile', 'r4_children', 'r4_gc', 'r5_actions', 'r5_clone',
        'r5_identity', 'http_window', 'http_export', 'http_status',
    ])
    parser.add_argument('--expected-sha', required=True,
                        choices=['5d631f6dd304a003f09c72e7de22fde45b8c3dbc'])
    parser.add_argument('--nonce', default='')
    args = parser.parse_args(argv)
    if args.phase.startswith('http_') and not re.fullmatch(r'r6_[a-z0-9]{8,24}', args.nonce):
        parser.error('HTTP phases require a bounded r6 nonce')
    if args.nonce and not re.fullmatch(r'r6_[a-z0-9]{8,24}', args.nonce):
        parser.error('invalid nonce')
    return subprocess.run([
        'make', 'audit.daily.demo.runtime_performance',
        'DAILY_RUNTIME_EXPECTED_SHA=' + args.expected_sha,
        'DAILY_PERFORMANCE_PHASE=' + args.phase,
        'DAILY_HTTP_PROFILE_NONCE=' + args.nonce,
    ], cwd=Path(__file__).resolve().parents[2], check=False).returncode


if 'env' in globals():
    run(env)
elif __name__ == '__main__':
    raise SystemExit(local_main())
