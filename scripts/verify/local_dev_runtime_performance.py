"""Bounded backend observation, not browser/SLO or production acceptance.

Only the registered local demo finance principal, up to two already assigned
companies, one process-first observation plus five subsequent observations each.
Commit is forbidden; no user/company/schema/fixture changes are performed.
"""
import os
import copy
import cProfile
import pstats
import hashlib
import inspect
import json
import time
import sys
from pathlib import Path
from odoo import api
from odoo.addons.smart_core.handlers import system_init
from odoo.addons.smart_core.handlers.system_init import SystemInitHandler

assert env.cr.dbname == 'sc_dev_demo', 'registered local.dev database required'
env.cr.rollback()
original_commit = env.cr.commit

def refuse_commit(*args, **kwargs):
    raise RuntimeError('performance observation forbids commit')

# Historical oracle pinned to 56f50964; test-only, never an alternate product path.
def previous_strip(payload):
    if isinstance(payload, list):
        return [previous_strip(item) for item in payload]
    if not isinstance(payload, dict):
        return payload
    return {key: previous_strip(value) for key, value in payload.items()
            if key not in {'ui_base_contract', 'ui_base_contract_ref'}}

def menu_cache_state(actor):
    """Read authoritative cache conditions only; never call a generating API."""
    model = actor['app.menu.config']
    cfg = model.sudo().with_context(active_test=False).search(
        model._menu_config_domain(model_name=None, scene='web'), limit=1)
    reason = 'missing'
    if cfg:
        reason = ('inactive' if not cfg.is_active else
                  'metadata_changed' if model._menu_metadata_changed_since(cfg) else 'valid')
    return {'language': actor.lang, 'company_id': actor.company.id,
            'reason': reason, 'cache_id': cfg.id if cfg else None,
            'version': cfg.version if cfg else None,
            'last_generated': str(cfg.last_generated) if cfg and cfg.last_generated else None,
            'force_generation': bool(actor.context.get('force_menu_config_generate'))}


def _p4_caller_name():
    try:
        frame = sys._getframe(2)
        return '%s:%s' % (Path(frame.f_code.co_filename).name, frame.f_code.co_name)
    except Exception:
        return ''


def _collect_view_field_names(node, acc):
    if isinstance(node, dict):
        if str(node.get('type') or '').strip().lower() == 'field':
            name = str(node.get('name') or '').strip()
            if name:
                acc.add(name)
        for value in node.values():
            _collect_view_field_names(value, acc)
    elif isinstance(node, list):
        for value in node:
            _collect_view_field_names(value, acc)


class RelationAttribution:
    """Bounded diagnostic wrapper over existing relation-assembly methods.

    Records per key the generation count, SQL count, cumulative time and the
    immediate call source. It never reads or exports field data values and never
    mutates product code, schema, fixtures or ACLs; it only measures the current
    candidate through the existing local.demo principal.
    """

    _WRAPPED = (
        '_inject_relation_entry_contract',
        '_build_relation_entry_for_field',
        '_build_relation_search_dialog_contract',
    )

    def __init__(self, env, target):
        self.env = env
        self.target = target
        self.injects = []
        self.fields = []
        self.dialogs = []
        self.main_view_fields = set()
        self.hierarchy_fields = set()
        self.include_dialog_flags = set()
        self.installed = False
        self._originals = {}

    @classmethod
    def build(cls, env):
        try:
            from odoo.addons.smart_core.app_config_engine.services.assemblers.page_assembler import PageAssembler
        except Exception:
            return None
        if any(not callable(getattr(PageAssembler, name, None)) for name in cls._WRAPPED):
            return None
        return cls(env, PageAssembler)

    def install(self):
        target = self.target
        for name in self._WRAPPED:
            self._originals[name] = getattr(target, name)
        target._inject_relation_entry_contract = self._wrap_inject(self._originals['_inject_relation_entry_contract'])
        target._build_relation_entry_for_field = self._wrap_field(self._originals['_build_relation_entry_for_field'])
        target._build_relation_search_dialog_contract = self._wrap_dialog(self._originals['_build_relation_search_dialog_contract'])
        self.installed = True

    def uninstall(self):
        if not self.installed:
            return
        for name, original in self._originals.items():
            setattr(self.target, name, original)
        self.installed = False

    def _sql_before(self):
        value = getattr(self.env.cr, 'sql_log_count', None)
        return value if isinstance(value, int) else None

    def _sql_delta(self, before):
        after = getattr(self.env.cr, 'sql_log_count', None)
        if before is None or not isinstance(after, int):
            return None
        return after - before

    def _wrap_inject(self, original):
        def wrapper(self_assembler, data, model_name='', stage_timings=None, relation_cache_key=''):
            names = set()
            if isinstance(data, dict):
                _collect_view_field_names(data.get('views'), names)
                context = data.get('context') if isinstance(data.get('context'), dict) else {}
                levels = context.get('hierarchy_levels') if isinstance(context, dict) else None
                for level in (levels if isinstance(levels, list) else []):
                    if isinstance(level, dict):
                        field = str(level.get('field') or '').strip()
                        if field:
                            self.hierarchy_fields.add(field)
            self.main_view_fields |= names
            self.include_dialog_flags.add(bool(getattr(self_assembler, 'include_relation_search_dialogs', True)))
            before = self._sql_before()
            started = time.perf_counter()
            try:
                return original(self_assembler, data, model_name, stage_timings, relation_cache_key)
            finally:
                self.injects.append({
                    'caller': _p4_caller_name(),
                    'model': str(model_name or ''),
                    'declared_field_count': len(names),
                    'sql_count': self._sql_delta(before),
                    'elapsed_ms': round((time.perf_counter() - started) * 1000, 2),
                })
        return wrapper

    def _wrap_field(self, original):
        def wrapper(self_assembler, *args, **kwargs):
            field_name = str((args[0] if args else kwargs.get('field_name')) or '').strip()
            descriptor = args[1] if len(args) > 1 else kwargs.get('descriptor')
            relation = str(descriptor.get('relation') or '').strip() if isinstance(descriptor, dict) else ''
            model_name = str(kwargs.get('model_name') or (args[3] if len(args) > 3 else '') or '')
            include = kwargs.get('include_search_dialog', args[7] if len(args) > 7 else True)
            before = self._sql_before()
            started = time.perf_counter()
            result = original(self_assembler, *args, **kwargs)
            dialog = result.get('search_dialog') if isinstance(result, dict) else None
            self.fields.append({
                'field': field_name,
                'relation': relation,
                'model': model_name,
                'include_search_dialog': bool(include),
                'in_main_view': field_name in self.main_view_fields,
                'in_hierarchy_dialog': field_name in self.hierarchy_fields,
                'dialog_present': isinstance(dialog, dict),
                'dialog_source': dialog.get('source') if isinstance(dialog, dict) else None,
                'sql_count': self._sql_delta(before),
                'elapsed_ms': round((time.perf_counter() - started) * 1000, 2),
                'caller': _p4_caller_name(),
            })
            return result
        return wrapper

    def _wrap_dialog(self, original):
        def wrapper(self_assembler, relation, model_name=''):
            before = self._sql_before()
            started = time.perf_counter()
            result = original(self_assembler, relation, model_name)
            self.dialogs.append({
                'relation': str(relation or '').strip(),
                'model': str(model_name or '').strip(),
                'source': result.get('source') if isinstance(result, dict) else None,
                'column_count': len(result.get('columns') or []) if isinstance(result, dict) else None,
                'sql_count': self._sql_delta(before),
                'elapsed_ms': round((time.perf_counter() - started) * 1000, 2),
                'caller': _p4_caller_name(),
            })
            return result
        return wrapper

    def mark(self):
        return (len(self.injects), len(self.fields), len(self.dialogs))

    def since(self, mark):
        inject_mark, field_mark, dialog_mark = mark
        return {
            'inject_calls': self.injects[inject_mark:],
            'field_calls': self.fields[field_mark:],
            'dialog_calls': self.dialogs[dialog_mark:],
            'dialog_targets': sorted({row['relation'] for row in self.dialogs[dialog_mark:]}),
        }

    def summary(self):
        return {
            'inject_count': len(self.injects),
            'field_count': len(self.fields),
            'dialog_count': len(self.dialogs),
            'dialog_targets': sorted({row['relation'] for row in self.dialogs}),
            'dialog_sql_total': sum(row['sql_count'] or 0 for row in self.dialogs),
            'dialog_elapsed_ms_total': round(sum(row['elapsed_ms'] or 0 for row in self.dialogs), 2),
            'field_sql_total': sum(row['sql_count'] or 0 for row in self.fields),
            'field_elapsed_ms_total': round(sum(row['elapsed_ms'] or 0 for row in self.fields), 2),
            'include_relation_search_dialogs': sorted(self.include_dialog_flags),
            'main_view_field_count': len(self.main_view_fields),
            'hierarchy_field_count': len(self.hierarchy_fields),
        }


def install_relation_attribution(env):
    """Install the bounded attribution wrapper, or return None when unavailable."""
    attribution = RelationAttribution.build(env)
    if attribution is not None:
        attribution.install()
    return attribution

mode = os.environ.get('PRODUCT_PERFORMANCE_MODE', 'observe')

class RelationStageProbe:
    """Bounded sub-stage attribution for relation search-dialog assembly.

    Splits the native view read, the view/field parsing, the fallback resolution
    and the contract/ACL/governance build so a single relation's cost can be told
    apart from process-first initialisation. Diagnostic only: it wraps existing
    owners, never changes product behaviour, never writes data and never
    special-cases a model.
    """

    def __init__(self, env):
        self.env = env
        self._frames = []
        self._originals = []
        self._stages = ()
        self._dialog_owner = None
        self._dialog_attr = ""
        self.dialogs = []
        self.installed = False

    @classmethod
    def build(cls, env):
        try:
            from odoo.addons.smart_core.app_config_engine.models.app_view_config import AppViewConfig
            from odoo.addons.smart_core.app_config_engine.services.native_parse_service import NativeParseService
            from odoo.addons.smart_core.app_config_engine.services.parse_fallback_service import ParseFallbackService
            from odoo.addons.smart_core.app_config_engine.services.assemblers.page_assembler import PageAssembler
        except Exception:
            return None
        stages = (
            ('view_generate', AppViewConfig, '_generate_from_fields_view_get'),
            ('view_read', AppViewConfig, '_safe_get_view_data'),
            ('field_parse', NativeParseService, 'parse_with_primary_parser'),
            ('fallback_resolve', ParseFallbackService, 'resolve_parsed_contract'),
            ('contract_acl_governance', AppViewConfig, 'build_final_contract'),
        )
        if any(not callable(getattr(owner, attr, None)) for _name, owner, attr in stages):
            return None
        if not callable(getattr(PageAssembler, '_build_relation_search_dialog_contract', None)):
            return None
        probe = cls(env)
        probe._stages = stages
        probe._dialog_owner = PageAssembler
        probe._dialog_attr = '_build_relation_search_dialog_contract'
        return probe

    def install(self):
        for name, owner, attr in self._stages:
            original = getattr(owner, attr)
            self._originals.append((owner, attr, original))
            setattr(owner, attr, self._wrap(name, original))
        owner, attr = self._dialog_owner, self._dialog_attr
        original_dialog = getattr(owner, attr)
        self._originals.append((owner, attr, original_dialog))
        setattr(owner, attr, self._wrap_dialog(original_dialog))
        self.installed = True

    def uninstall(self):
        if not self.installed:
            return
        for owner, attr, original in self._originals:
            setattr(owner, attr, original)
        self._originals = []
        self.installed = False

    def _sql_before(self):
        value = getattr(self.env.cr, 'sql_log_count', None)
        return value if isinstance(value, int) else None

    def _sql_delta(self, before):
        after = getattr(self.env.cr, 'sql_log_count', None)
        if before is None or not isinstance(after, int):
            return None
        return after - before

    def _record(self, name, before, started):
        if not self._frames:
            return
        delta_sql = self._sql_delta(before) or 0
        elapsed = (time.perf_counter() - started) * 1000
        for frame in self._frames:
            entry = frame['stages'].setdefault(name, {'calls': 0, 'sql': 0, 'elapsed_ms': 0.0})
            entry['calls'] += 1
            entry['sql'] += delta_sql
            entry['elapsed_ms'] = round(entry['elapsed_ms'] + elapsed, 2)

    def _wrap(self, name, original):
        def wrapper(*args, **kwargs):
            before = self._sql_before()
            started = time.perf_counter()
            try:
                return original(*args, **kwargs)
            finally:
                self._record(name, before, started)
        return wrapper

    @staticmethod
    def _profile_top(profiler, limit=None):
        rows = []
        for (filename, line, function), (_, calls, own, cumulative, _) in pstats.Stats(profiler).stats.items():
            rows.append({'file': Path(filename).name, 'function': function, 'calls': calls,
                         'self_ms': round(own * 1000, 2), 'cumulative_ms': round(cumulative * 1000, 2)})
        rows.sort(key=lambda row: row['cumulative_ms'], reverse=True)
        return rows[:int(limit or os.environ.get('PRODUCT_PERFORMANCE_STAGE_PROBE_PROFILE_LIMIT') or 12)]

    def _wrap_dialog(self, original):
        def wrapper(assembler, relation, model_name=''):
            frame = {'scope': 'session_dialog', 'relation': str(relation or '').strip(),
                     'target_model': str(model_name or '').strip(), 'stages': {}}
            before = self._sql_before()
            self._frames.append(frame)
            started = time.perf_counter()
            try:
                result = original(assembler, relation, model_name)
            finally:
                self._frames.pop()
            frame['elapsed_ms'] = round((time.perf_counter() - started) * 1000, 2)
            frame['sql'] = self._sql_delta(before)
            frame['source'] = result.get('source') if isinstance(result, dict) else None
            frame['column_count'] = len(result.get('columns') or []) if isinstance(result, dict) else None
            self.dialogs.append(frame)
            return result
        return wrapper

    def begin_session(self):
        session = {'scope': 'session', 'stages': {}}
        self._frames.append(session)
        return session

    def end_session(self):
        return self._frames.pop()

    def probe(self, assembler, relation, model_name='', index=0, profiler=False):
        """Run one dialog build in isolation; the dialog wrapper records it."""
        prof = cProfile.Profile() if profiler else None
        if prof is not None:
            prof.enable()
        try:
            getattr(assembler, self._dialog_attr)(relation, model_name)
        finally:
            if prof is not None:
                prof.disable()
        frame = self.dialogs[-1]
        frame['scope'] = 'isolated'
        frame['index'] = index
        if prof is not None:
            frame['profile_top'] = self._profile_top(prof)
        return frame


def run_relation_stage_probe(env, actor, action, params, measured_handler, hashes):
    """Reproduce the real relation assembly, then split per stage and per relation.

    Order matters: the unmodified handler runs first under a session frame so the
    per-relation cold cost is captured in the real assembly context; the isolated
    ordered probes then run against the same process to separate a genuinely
    expensive relation from a one-time initialisation cost.
    """
    from odoo.addons.smart_core.app_config_engine.services.assemblers.page_assembler import PageAssembler
    from odoo.addons.smart_core.core.intent_execution_result import adapt_handler_result

    probe = RelationStageProbe.build(env)
    if probe is None:
        return {'status': 'unavailable', 'reason': 'stage probe owners not importable'}
    targets = [
        token.strip()
        for token in (os.environ.get('PRODUCT_PERFORMANCE_STAGE_PROBE_RELATIONS')
                      or 'res.partner,res.currency,res.partner,res.currency,res.users,res.users').split(',')
        if token.strip()
    ]
    skip_session = os.environ.get('PRODUCT_PERFORMANCE_STAGE_PROBE_SKIP_SESSION') == '1'
    profile_isolated = os.environ.get('PRODUCT_PERFORMANCE_STAGE_PROBE_PROFILE') == '1'
    owner_model = str(action.res_model or '').strip()
    report = {'status': 'observed', 'owner_model': owner_model,
              'probe_targets': targets, 'owner_hashes': hashes,
              'session_skipped': skip_session, 'isolated_profiled': profile_isolated,
              'session': None, 'dialogs': [], 'isolated': []}
    probe.install()
    try:
        if not skip_session:
            before = env.cr.sql_log_count
            started = time.perf_counter()
            session = probe.begin_session()
            try:
                result = adapt_handler_result(measured_handler(env=actor).handle({'params': params}))
            finally:
                probe.end_session()
            assert isinstance(result, dict) and result.get('ok') is True, 'stage probe contract failed'
            session['elapsed_ms'] = round((time.perf_counter() - started) * 1000, 2)
            session['sql'] = env.cr.sql_log_count - before
            session['response_sha256'] = hashlib.sha256(
                json.dumps(result, sort_keys=True, default=str).encode()).hexdigest()
            report['session'] = session
            report['dialogs'] = [row for row in probe.dialogs if row.get('scope') == 'session_dialog']
        assembler = PageAssembler(actor)
        isolated = []
        for index, relation in enumerate(targets):
            try:
                actor[relation]
                known = True
            except Exception:
                known = False
            if not known:
                isolated.append({'index': index, 'relation': relation, 'scope': 'isolated',
                                 'status': 'unknown_relation'})
                continue
            isolated.append(probe.probe(assembler, relation, owner_model,
                                        index=index, profiler=profile_isolated))
        report['isolated'] = isolated
    finally:
        probe.uninstall()
    return report


def _graph_stats(value):
    """Count container/leaf nodes and the shared-node factor of one object graph."""
    seen = {}
    stack = [value]
    containers = 0
    leaves = 0
    edges = 0
    while stack:
        node = stack.pop()
        if isinstance(node, (dict, list)):
            marker = id(node)
            if marker in seen:
                continue
            seen[marker] = True
            containers += 1
            children = list(node.values()) if isinstance(node, dict) else list(node)
            edges += len(children)
            stack.extend(children)
        else:
            leaves += 1
    return {'containers': containers, 'leaves': leaves, 'edges': edges,
            'nodes': containers + leaves,
            'shared_references': edges - containers}


def _best_ms(fn, repeats=7):
    best = None
    for _ in range(repeats):
        started = time.perf_counter()
        value = fn()
        elapsed = (time.perf_counter() - started) * 1000
        best = elapsed if best is None else min(best, elapsed)
        del value
    return round(best, 3)


def _shared_container_stats(*values):
    """Count containers reached by more than one of ``values`` when walked together.

    Two graphs that were deep-copied with separate memos share nothing, even when
    the live objects did alias. One shared memo (in the store and in the read
    clone) would keep every structurally shared subtree single, so this count is
    the ceiling of what a shared-memo copy can save.
    """
    visits = {}
    order = []
    for index, value in enumerate(values):
        stack = [value]
        while stack:
            node = stack.pop()
            if not isinstance(node, (dict, list)):
                continue
            marker = id(node)
            if marker not in visits:
                visits[marker] = set()
                order.append(marker)
            visits[marker].add(index)
            stack.extend(node.values() if isinstance(node, dict) else node)
    shared = sum(1 for marker in order if len(visits[marker]) > 1)
    return {'union_containers': len(order), 'shared_containers': shared}


def run_cache_clone_split(env, actor, action, params, measured_handler):
    """Read-only split of the warm assembled-cache read clone.

    The hot read path clones the whole cached entry, which holds both the source
    ``ui_data`` subtree and the ``_assembled_v2`` subtree that sealing mutates.
    This probe warms the process-local hot cache with one real ``action_open``
    request, then measures each subtree separately, so the share of the read
    clone that only feeds two fallback ``model``/``view_type`` lookups is told
    apart from the share that must stay isolated. It also records whether the two
    subtrees alias at all, which is what decides if one clone pass really covers
    them. Diagnostic only: the cache is read, never written; no product code and
    no database row is touched.
    """
    from odoo.addons.smart_core.core.intent_execution_result import adapt_handler_result
    from odoo.addons.smart_core.utils.load_contract_response_cache import (
        CONTRACT_PROJECTION_HOT_CACHE,
        isolated_clone,
    )

    warm = adapt_handler_result(measured_handler(env=actor).handle({'params': params}))
    assert isinstance(warm, dict) and warm.get('ok') is True, 'warm cache priming failed'
    entries = list(CONTRACT_PROJECTION_HOT_CACHE._entries.values())
    report = {'status': 'observed', 'entry_count': len(entries), 'entries': [],
              'warm_response_sha256': hashlib.sha256(
                  json.dumps(warm, sort_keys=True, default=str).encode()).hexdigest()}
    for created_at, token, response in entries:
        if not isinstance(response, dict):
            continue
        assembled = response.get('_assembled_v2')
        if not isinstance(assembled, dict):
            continue
        ui_data = response.get('ui_data')
        ui_meta = response.get('ui_meta')
        contract = assembled.get('contract')
        source_contract = assembled.get('source_contract')
        row = {
            'token_is_content_hash': isinstance(token, str) and len(token) == 64,
            'has_ui_data': isinstance(ui_data, dict),
            'has_assembled': True,
            'aliasing': {
                'contract_is_ui_data': contract is ui_data,
                'source_contract_is_ui_data': source_contract is ui_data,
                'source_contract_is_contract': source_contract is contract,
                'ui_meta_is_ui_data': ui_meta is ui_data,
            },
            'graph_full': _graph_stats(response),
            'graph_assembled': _graph_stats(assembled),
            'graph_contract': _graph_stats(contract or {}),
            'graph_source_contract': _graph_stats(source_contract or {}),
            'graph_ui_data': _graph_stats(ui_data or {}),
            'graph_ui_meta': _graph_stats(ui_meta or {}),
            'clone_full_ms': _best_ms(lambda: isolated_clone(response)),
            'clone_assembled_ms': _best_ms(lambda: isolated_clone(assembled)),
            'clone_contract_ms': _best_ms(lambda: isolated_clone(contract or {})),
            'clone_source_contract_ms': _best_ms(lambda: isolated_clone(source_contract or {})),
            'clone_ui_data_ms': _best_ms(lambda: isolated_clone(ui_data or {})),
            'clone_ui_meta_ms': _best_ms(lambda: isolated_clone(ui_meta or {})),
            'clone_ui_data_shared_with_source_contract_ms': _best_ms(
                lambda: isolated_clone({'ui_data': ui_data or {}, 'source_contract': source_contract or {}})),
            'shared_ui_data_vs_source_contract': _shared_container_stats(ui_data or {}, source_contract or {}),
            'shared_full_vs_assembled': _shared_container_stats(response, assembled),
            'json_bytes_full': len(json.dumps(response, sort_keys=True, default=str)),
            'json_bytes_assembled': len(json.dumps(assembled, sort_keys=True, default=str)),
            'json_bytes_ui_data': len(json.dumps(ui_data, sort_keys=True, default=str)),
            'json_bytes_ui_meta': len(json.dumps(ui_meta, sort_keys=True, default=str)),
        }
        report['entries'].append(row)
    return report

# Only pure per-request identity is excluded. Content-derived digests
# (contractSha256/sourceSha256) are deliberately kept so a real difference cannot
# be hidden by normalisation.
_VOLATILE_ENVELOPE_KEYS = frozenset({
    'requestId', 'traceId', 'traceSource', 'etag', 'snapshotId', 'elapsed_ms',
    'stages_ms', 'projection_cache', 'source_ref', 'source_token_ready',
    'isolation_id',
})


def _normalize_relation_search_dialog(dialog):
    """Contract metadata only; never a field value."""
    if not isinstance(dialog, dict):
        return None
    return {
        'source': str(dialog.get('source') or ''),
        'limit': dialog.get('limit'),
        'order': str(dialog.get('order') or ''),
        'read_fields': sorted(str(value) for value in (dialog.get('read_fields') or [])),
        'columns': sorted(
            str(column.get('name') or '')
            for column in (dialog.get('columns') or [])
            if isinstance(column, dict)
        ),
    }


def _normalize_relation_entry(entry):
    """Bounded relation-entry facts; the search popup payload is summarized, not copied."""
    if not isinstance(entry, dict):
        return None
    delete_policy = entry.get('delete_policy') if isinstance(entry.get('delete_policy'), dict) else {}
    inline_create = entry.get('inline_create') if isinstance(entry.get('inline_create'), dict) else {}
    dialog = entry.get('search_dialog')
    return {
        'can_read': entry.get('can_read'),
        'can_create': entry.get('can_create'),
        'can_open': entry.get('can_open'),
        'create_mode': str(entry.get('create_mode') or ''),
        'reason_code': str(entry.get('reason_code') or ''),
        'has_action': bool(entry.get('action_id')),
        'has_menu': bool(entry.get('menu_id')),
        'delete_allowed': delete_policy.get('allowed'),
        'delete_mode': str(delete_policy.get('delete_mode') or ''),
        'default_vals': sorted((entry.get('default_vals') or {}).keys()),
        'domain': entry.get('domain') or [],
        'display_field': str(entry.get('display_field') or ''),
        'order': str(entry.get('order') or ''),
        'switch_context_enabled': bool((entry.get('switch_context') or {}).get('enabled')),
        'inline_create_enabled': inline_create.get('enabled'),
        'default_from_fields': sorted((entry.get('default_from_fields') or {}).keys()),
        'page_size': entry.get('page_size'),
        'options_limit': entry.get('options_limit'),
        'options_search_limit': entry.get('options_search_limit'),
        'dialog_present': isinstance(dialog, dict),
        'dialog': _normalize_relation_search_dialog(dialog),
    }


def _normalize_demand_declaration(declaration):
    """Bounded projection of the P0 declaration: provenance, targets, stages."""
    if not isinstance(declaration, dict):
        return None
    sources = declaration.get('sources') if isinstance(declaration.get('sources'), dict) else {}
    targets = declaration.get('targets') if isinstance(declaration.get('targets'), dict) else {}
    return {
        'model': str(declaration.get('model') or ''),
        'sources': {
            str(key): sorted(str(value) for value in (rows or []))
            for key, rows in sources.items()
        },
        'dialog_required_fields': sorted(
            str(value) for value in (declaration.get('dialog_required_fields') or [])
        ),
        'targets': {
            str(key): sorted(str(value) for value in ((row or {}).get('stages') or []))
            for key, row in targets.items()
        },
        'capability_counts': {
            str(key): len([row for row in targets.values() if key in ((row or {}).get('stages') or [])])
            for key in ('permission', 'navigation', 'hierarchy_fact', 'search_dialog')
        },
    }


def _masked_envelope(payload, mask_dialogs=True):
    """Deep copy with volatile identity dropped and dialog payloads optionally masked."""
    if isinstance(payload, dict):
        out = {}
        for key, value in payload.items():
            if key in _VOLATILE_ENVELOPE_KEYS:
                continue
            if mask_dialogs and key == 'search_dialog':
                out[key] = '<masked>'
                continue
            out[key] = _masked_envelope(value, mask_dialogs=mask_dialogs)
        return out
    if isinstance(payload, list):
        return [_masked_envelope(item, mask_dialogs=mask_dialogs) for item in payload]
    return payload


def _path_digests(payload, max_depth=6, prefix='') -> dict:
    """Bounded path -> sha256 map so a difference can be located, not guessed."""
    out = {}
    if max_depth < 0 or len(out) > 400:
        return out
    children = None
    if isinstance(payload, dict):
        children = [(str(key), value) for key, value in sorted(payload.items())]
    elif isinstance(payload, list):
        children = [(str(index), value) for index, value in enumerate(payload)]
    for key, value in children or []:
        path = prefix + '/' + key
        if isinstance(value, (dict, list)):
            out[path] = hashlib.sha256(
                json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()
            out.update(_path_digests(value, max_depth=max_depth - 1, prefix=path))
        else:
            out[path] = hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()
    return out


class RelationDemandProbe:
    """Bounded capture of the P0 relation-demand declaration and its materialization.

    Read-only diagnostic: it wraps the existing declaration owner when present,
    the relation-entry injection and the search-dialog builder. It records what
    was declared and what was actually materialized, and never changes product
    behaviour, writes data or exports field values.
    """

    def __init__(self, env, owner):
        self.env = env
        self.owner = owner
        self.declarations = []
        self.injects = []
        self.dialogs = []
        self._originals = {}
        self.installed = False
        # Reconstructs the pre-declaration semantics inside this diagnostic only:
        # every readable relation field gets its search dialog again. The product
        # code is never modified, so the recorded difference is the real one.
        self.baseline = os.environ.get('PRODUCT_PERFORMANCE_DEMAND_BASELINE') == '1'

    @classmethod
    def build(cls, env):
        try:
            from odoo.addons.smart_core.app_config_engine.services.assemblers.page_assembler import PageAssembler
        except Exception:
            return None
        for attr in ('_inject_relation_entry_contract', '_build_relation_search_dialog_contract'):
            if not callable(getattr(PageAssembler, attr, None)):
                return None
        return cls(env, PageAssembler)

    def install(self):
        owner = self.owner
        plan = (
            ('_inject_relation_entry_contract', self._wrap_inject),
            ('_build_relation_search_dialog_contract', self._wrap_dialog),
        )
        if self.baseline:
            plan = plan + (('_build_relation_entry_for_field', self._wrap_field_baseline),)
        for attr, factory in plan:
            original = getattr(owner, attr, None)
            self._originals[attr] = original
            setattr(owner, attr, factory(original))
        declaration = getattr(owner, '_relation_demand_declaration', None)
        if callable(declaration):
            self._originals['_relation_demand_declaration'] = declaration
            setattr(owner, '_relation_demand_declaration', self._wrap_declaration(declaration))
        self.installed = True

    def uninstall(self):
        if not self.installed:
            return
        for attr, original in self._originals.items():
            setattr(self.owner, attr, original)
        self._originals = {}
        self.installed = False

    def _wrap_inject(self, original):
        def wrapper(assembler, data, model_name='', stage_timings=None, relation_cache_key=''):
            result = original(assembler, data, model_name, stage_timings, relation_cache_key)
            fields = data.get('fields') if isinstance(data, dict) and isinstance(data.get('fields'), dict) else {}
            view_fields = set()
            if isinstance(data, dict):
                _collect_view_field_names(data.get('views'), view_fields)
            surface = []
            for name, descriptor in sorted(fields.items()):
                if not isinstance(descriptor, dict):
                    continue
                field_type = str(descriptor.get('type') or '').strip().lower()
                relation = str(descriptor.get('relation') or '').strip()
                if field_type not in {'many2one', 'many2many', 'one2many'} or not relation:
                    continue
                surface.append({
                    'field': str(name),
                    'type': field_type,
                    'relation': relation,
                    'readonly': descriptor.get('readonly') is True,
                    'in_view': str(name) in view_fields,
                    'entry': _normalize_relation_entry(descriptor.get('relation_entry')),
                })
            self.injects.append({
                'model': str(model_name or ''),
                'declared_field_count': len(fields),
                'view_field_count': len(view_fields),
                'relation_field_count': len(surface),
                'relation_target_count': len({row['relation'] for row in surface}),
                'surface': surface,
            })
            return result
        return wrapper

    def _wrap_dialog(self, original):
        def wrapper(assembler, relation, model_name=''):
            before = getattr(self.env.cr, 'sql_log_count', None)
            started = time.perf_counter()
            try:
                result = original(assembler, relation, model_name)
            except Exception:
                self.dialogs.append({
                    'relation': str(relation or '').strip(),
                    'target_model': str(model_name or '').strip(),
                    'status': 'raised',
                })
                raise
            after = getattr(self.env.cr, 'sql_log_count', None)
            self.dialogs.append({
                'relation': str(relation or '').strip(),
                'target_model': str(model_name or '').strip(),
                'status': 'built',
                'source': result.get('source') if isinstance(result, dict) else None,
                'column_count': len(result.get('columns') or []) if isinstance(result, dict) else None,
                'sql_count': (after - before) if isinstance(before, int) and isinstance(after, int) else None,
                'elapsed_ms': round((time.perf_counter() - started) * 1000, 2),
                'caller': _p4_caller_name(),
            })
            return result
        return wrapper

    def _wrap_field_baseline(self, original):
        """Reconstruct the pre-declaration semantics exactly, in-process.

        The removed product code built one dialog per relation *target* through the
        projection cache key ("search_dialog", relation, model_name) and attached it
        to every relation field, without a can_read filter. Reuse the same cache and
        the same key so the reconstruction is the real pre-change pipeline rather
        than a per-field over-build.
        """
        def wrapper(assembler, field_name, descriptor, base_entry, **kwargs):
            entry = original(assembler, field_name, descriptor, base_entry, **kwargs)
            relation = str((descriptor or {}).get('relation') or '').strip()
            if not isinstance(entry, dict) or not relation:
                return entry
            model_name = str(kwargs.get('model_name') or '')
            cache = kwargs.get('relation_projection_cache')
            cache = cache if isinstance(cache, dict) else {}
            cache_key = ('search_dialog', relation, model_name)
            dialog = cache.get(cache_key)
            if not isinstance(dialog, dict):
                dialog = assembler._build_relation_search_dialog_contract(
                    relation, model_name=model_name)
                cache[cache_key] = copy.deepcopy(dialog)
            else:
                dialog = copy.deepcopy(dialog)
            entry['search_dialog'] = dialog
            return entry
        return wrapper

    def _wrap_declaration(self, original):
        def wrapper(assembler, *args, **kwargs):
            result = original(assembler, *args, **kwargs)
            self.declarations.append(_normalize_demand_declaration(result))
            return result
        return wrapper


def run_relation_demand_probe(env, actor, action, params, measured_handler, hashes):
    """Capture declaration -> materialization and the normalized contract digest."""
    from odoo.addons.smart_core.core.intent_execution_result import adapt_handler_result

    probe = RelationDemandProbe.build(env)
    if probe is None:
        return {'status': 'unavailable', 'reason': 'relation demand owners not importable'}
    owner_model = str(action.res_model or '').strip()
    before = env.cr.sql_log_count
    started = time.perf_counter()
    probe.install()
    try:
        result = adapt_handler_result(measured_handler(env=actor).handle({'params': params}))
    finally:
        probe.uninstall()
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    sql_count = env.cr.sql_log_count - before
    if not (isinstance(result, dict) and result.get('ok') is True):
        return {'status': 'failed', 'reason': 'contract request failed'}
    injections = [row for row in probe.injects if row['relation_field_count']]
    injection = injections[-1] if injections else None
    surface = injection['surface'] if injection else []
    built = [row for row in probe.dialogs if row.get('status') == 'built']
    masked = _masked_envelope(result, mask_dialogs=True)
    full = _masked_envelope(result, mask_dialogs=False)
    return {
        'status': 'observed',
        'owner_model': owner_model,
        'owner_hashes': hashes,
        'envelope_keys': sorted(result.keys()),
        'elapsed_ms': elapsed_ms,
        'sql_count': sql_count,
        'injection_count': len(probe.injects),
        'declared_field_count': injection['declared_field_count'] if injection else 0,
        'view_field_count': injection['view_field_count'] if injection else 0,
        'relation_field_count': injection['relation_field_count'] if injection else 0,
        'relation_fields_in_view': sorted(row['field'] for row in surface if row['in_view']),
        'relation_fields_not_in_view': sorted(row['field'] for row in surface if not row['in_view']),
        'relation_base_surface': [
            {'field': row['field'], 'relation': row['relation'], 'in_view': row['in_view'],
             **{key: value for key, value in (row['entry'] or {}).items()
                if key not in {'dialog', 'dialog_present'}}}
            for row in surface
        ],
        'dialog_present_fields': sorted(row['field'] for row in surface if (row['entry'] or {}).get('dialog_present')),
        'dialog_target_count': len({row['relation'] for row in surface if (row['entry'] or {}).get('dialog_present')}),
        'dialog_targets': sorted({row['relation'] for row in surface if (row['entry'] or {}).get('dialog_present')}),
        'dialog_build_count': len(built),
        'dialog_builds': built,
        'baseline_reconstruction': probe.baseline,
        'declarations': probe.declarations,
        'relation_surface': surface,
        'relation_base_sha256': hashlib.sha256(json.dumps(
            [{key: value for key, value in row.items() if key != 'entry'} for row in surface],
            sort_keys=True, default=str).encode()).hexdigest(),
        'relation_entry_sha256': hashlib.sha256(json.dumps(
            {row['field']: {key: value for key, value in (row['entry'] or {}).items()
                            if key not in {'dialog', 'dialog_present'}} for row in surface},
            sort_keys=True, default=str).encode()).hexdigest(),
        'search_dialog_sha256': hashlib.sha256(json.dumps(
            {row['field']: (row['entry'] or {}).get('dialog') for row in surface},
            sort_keys=True, default=str).encode()).hexdigest(),
        'envelope_full_sha256': hashlib.sha256(
            json.dumps(full, sort_keys=True, default=str).encode()).hexdigest(),
        'envelope_masked_sha256': hashlib.sha256(
            json.dumps(masked, sort_keys=True, default=str).encode()).hexdigest(),
        'envelope_path_digests': _path_digests(masked),
    }


assert mode in {'observe', 'cache_state', 'preference_profile', 'preference_compare', 'contract_profile', 'relation_attribution', 'relation_stage_probe', 'relation_demand_probe', 'cache_clone_split', 'profile', 'profile_first', 'shape', 'compare', 'sql', 'menu_compare', 'path_compare', 'scene_compare'}, 'unknown measurement mode'
request_case = os.environ.get('PRODUCT_PERFORMANCE_REQUEST_CASE', 'web_startup')
assert request_case in {'web_startup', 'full_default'}, 'unknown request case'
# Explicit counterpart of session.ts init request; full_default is diagnostic only.
request_params = ({'scene': 'web', 'with_preload': False, 'scene_ready_mode': 'registry',
                   'with': ['workspace_home']} if request_case == 'web_startup' else {})
env.cr.commit = refuse_commit
try:
    user = env.ref('smart_construction_demo.user_demo_role_finance')
    assert user.active and not user.share, 'declared demo finance identity unavailable'
    companies = [user.company_id.id] + [cid for cid in user.company_ids.ids if cid != user.company_id.id][:1]
    source = Path(inspect.getsourcefile(SystemInitHandler))
    expected_hash = os.environ.get('PRODUCT_PERFORMANCE_HANDLER_SHA256')
    assert expected_hash == hashlib.sha256(source.read_bytes()).hexdigest(), 'candidate handler identity mismatch'
    # Odoo builds model classes dynamically, so ``type(model)`` points at
    # odoo/api.py rather than the addon file. Resolve the defining module
    # through a method that lives in the model implementation.
    menu_config_owner = type(env['app.menu.config'])
    menu_config_method = getattr(menu_config_owner, '_menu_metadata_changed_since', None)
    assert menu_config_method is not None, 'menu config owner method unavailable'
    menu_config_source = Path(inspect.getsourcefile(menu_config_method))
    menu_config_hash = hashlib.sha256(menu_config_source.read_bytes()).hexdigest()
    assert menu_config_hash == os.environ.get('PRODUCT_PERFORMANCE_MENU_CONFIG_SHA256'), \
        'menu config owner identity mismatch'
    report = {'schema': 'runtime-performance-observation/v1', 'status': 'observed',
              'measurement_mode': mode, 'request_case': request_case, 'request_params': request_params, 'acceptance_pass': False, 'scope': 'local_demo_backend_only',
              'database': env.cr.dbname, 'principal_xmlid': 'smart_construction_demo.user_demo_role_finance',
              'handler_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'menu_config_sha256': menu_config_hash,
              'companies': [], 'limitations': ['no_http_browser_or_authentication_measurement',
              'no_true_cold_cache_claim', 'no_capacity_claim', 'not_delivery_baseline']}
    if mode in {'preference_profile', 'preference_compare', 'contract_profile', 'relation_attribution', 'relation_stage_probe', 'relation_demand_probe', 'cache_clone_split'}:
        report['request_case'] = 'list_preference'
        report['request_params'] = None  # Exact action/model recorded per company below.
    for company in companies:
        actor = api.Environment(env.cr, user.id, {'allowed_company_ids': [company], 'lang': 'zh_CN'})
        assert not actor.su, 'actor must not be elevated'
        if mode in {'preference_profile', 'preference_compare', 'contract_profile', 'relation_attribution', 'relation_stage_probe', 'relation_demand_probe', 'cache_clone_split'}:
            from odoo.addons.smart_core.handlers.user_view_preference import UserViewPreferenceGetHandler
            action_id = int(os.environ.get('PRODUCT_PERFORMANCE_PREFERENCE_ACTION_ID') or 0)
            assert action_id > 0, 'exact observed preference action required'
            action = actor['ir.actions.act_window'].browse(action_id).exists()
            assert action and action.res_model, 'observed action unavailable'
            preference_source = Path(inspect.getsourcefile(UserViewPreferenceGetHandler))
            source_hash = hashlib.sha256(preference_source.read_bytes()).hexdigest()
            assert source_hash == os.environ.get('PRODUCT_PERFORMANCE_PREFERENCE_SHA256'), 'preference handler identity mismatch'
            params = {'action_id': action_id, 'model': action.res_model, 'view_type': 'list', 'preference_key': 'list_columns'}
            measured_handler = UserViewPreferenceGetHandler
            if mode in {'contract_profile', 'relation_attribution', 'relation_stage_probe', 'relation_demand_probe', 'cache_clone_split'}:
                from odoo.addons.smart_core.handlers.ui_contract_v2 import UiContractV2Handler
                measured_handler = UiContractV2Handler
                digest = hashlib.sha256(Path(inspect.getsourcefile(measured_handler)).read_bytes()).hexdigest()
                assert digest == os.environ.get('PRODUCT_PERFORMANCE_V2_SHA256'), 'v2 handler identity mismatch'
                report['contract_handler_sha256'] = digest
                report['request_case'] = 'action_open_contract'
                params = {'action_id': action_id, 'op': 'action_open'}
            from odoo.addons.smart_core.handlers.ui_contract import UiContractHandler
            from odoo.addons.smart_core.core.intent_execution_result import adapt_handler_result
            from odoo.addons.smart_core.app_config_engine.services.assemblers.page_assembler import PageAssembler
            from odoo.addons.smart_core.app_config_engine.services.dispatchers.action_dispatcher import ActionDispatcher
            from unittest.mock import patch
            from contextlib import nullcontext
            hashes = {}
            for owner, key in ((UiContractHandler, 'UI'), (PageAssembler, 'ASSEMBLER'), (ActionDispatcher, 'DISPATCHER')):
                digest = hashlib.sha256(Path(inspect.getsourcefile(owner)).read_bytes()).hexdigest()
                assert digest == os.environ.get('PRODUCT_PERFORMANCE_' + key + '_SHA256'), 'projection owner mismatch: ' + key
                hashes[key] = digest
            if mode == 'relation_stage_probe':
                report['companies'].append({
                    'company_id': company,
                    'preference_handler_sha256': source_hash,
                    'stage_probe': run_relation_stage_probe(env, actor, action, params, measured_handler, hashes),
                })
                continue
            if mode == 'relation_demand_probe':
                report['companies'].append({
                    'company_id': company,
                    'preference_handler_sha256': source_hash,
                    'demand_probe': run_relation_demand_probe(env, actor, action, params, measured_handler, hashes),
                })
                continue
            if mode == 'cache_clone_split':
                report['companies'].append({
                    'company_id': company,
                    'preference_handler_sha256': source_hash,
                    'projection_owner_hashes': hashes,
                    'clone_split': run_cache_clone_split(env, actor, action, params, measured_handler),
                })
                continue
            def previous_profile(handler, payload):
                result = adapt_handler_result(handler.handle(payload))
                data = result.get('data') if isinstance(result, dict) else None
                profile = data.get('list_profile') if isinstance(data, dict) else None
                return profile if isinstance(profile, dict) else None
            samples = []
            variants = ['previous', 'candidate', 'candidate', 'previous', 'previous', 'candidate'] if mode == 'preference_compare' else ['candidate', 'candidate', 'candidate_unprofiled', 'registry_cold']
            if mode == 'contract_profile':
                pair_rounds = int(os.environ.get('PRODUCT_PERFORMANCE_PROFILE_PAIR') or 6)
                paired = [
                    'candidate_paired_profiled' if round_index % 2 == 0 else 'candidate_paired_unprofiled'
                    for round_index in range(pair_rounds)
                ]
                variants = ['candidate', 'candidate'] + paired + ['registry_cold']
            unprofiled_first = os.environ.get('PRODUCT_PERFORMANCE_PROFILE_FIRST_SAMPLE') == '0'
            attribution = install_relation_attribution(env) if mode == 'relation_attribution' else None
            try:
                for index, variant in enumerate(variants):
                    attribution_mark = attribution.mark() if attribution is not None else None
                    if variant == 'registry_cold':
                        env.registry.clear_cache()
                    profiler = None if (
                        variant.endswith('unprofiled') or (index == 0 and unprofiled_first)
                    ) else cProfile.Profile()
                    before = env.cr.sql_log_count
                    started = time.perf_counter()
                    if profiler is not None:
                        profiler.enable()
                    try:
                        with (patch.object(UiContractHandler, 'read_list_preference_profile', previous_profile)
                              if variant == 'previous' else nullcontext()):
                            result = adapt_handler_result(measured_handler(env=actor).handle({'params': params}))
                    finally:
                        if profiler is not None:
                            profiler.disable()
                    assert isinstance(result, dict) and result.get('ok') is True, 'preference read failed'
                    functions = []
                    if profiler is not None:
                        for (filename, line, function), (_, calls, own, cumulative, _) in pstats.Stats(profiler).stats.items():
                            functions.append({'file': Path(filename).name, 'line': line, 'function': function, 'calls': calls,
                                              'self_ms': round(own * 1000, 2), 'cumulative_ms': round(cumulative * 1000, 2)})
                    sample = {'index': index, 'variant': variant, 'response_sha256': hashlib.sha256(json.dumps(result, sort_keys=True, default=str).encode()).hexdigest(), 'profiled': profiler is not None, 'elapsed_ms': round((time.perf_counter() - started) * 1000, 2),
                              'sql_count': env.cr.sql_log_count - before,
                              'cumulative_top': sorted(functions, key=lambda row: row['cumulative_ms'], reverse=True)[:40],
                              'self_top': sorted(functions, key=lambda row: row['self_ms'], reverse=True)[:20]}
                    caller_names = [name for name in os.environ.get('PRODUCT_PERFORMANCE_PROFILE_CALLERS', '').split(',') if name]
                    if profiler is not None and caller_names:
                        wanted = set(caller_names)
                        aggregate = {}
                        for (filename, line, function), (_, calls, own, cumulative, callers_map) in pstats.Stats(profiler).stats.items():
                            if function not in wanted:
                                continue
                            row = aggregate.setdefault(function, {'calls': calls, 'cumulative_ms': round(cumulative * 1000, 2), 'callers': {}})
                            for (caller_file, caller_line, caller_function), (_, caller_nc, _, caller_ct) in (callers_map or {}).items():
                                key = '%s:%s:%s' % (Path(caller_file).name, caller_function, caller_line)
                                entry = row['callers'].setdefault(key, {'nc': 0, 'ct_ms': 0.0})
                                entry['nc'] += caller_nc
                                entry['ct_ms'] = round(entry['ct_ms'] + caller_ct * 1000, 2)
                        sample['callers'] = {name: {'calls': value['calls'], 'cumulative_ms': value['cumulative_ms'],
                                                    'top_callers': sorted(({'caller': key, 'nc': entry['nc'], 'ct_ms': entry['ct_ms']} for key, entry in value['callers'].items()),
                                                                          key=lambda item: item['ct_ms'], reverse=True)[:12]}
                                             for name, value in aggregate.items()}
                    if attribution_mark is not None:
                        sample['relation_attribution'] = attribution.since(attribution_mark)
                    samples.append(sample)
            finally:
                if attribution is not None:
                    attribution.uninstall()
            report['companies'].append({'company_id': company, 'preference_request': params,
                                        'preference_handler_sha256': source_hash, 'projection_owner_hashes': hashes, 'samples': samples,
                                        'relation_attribution': attribution.summary() if attribution is not None else None})
            continue
        if mode == 'cache_state':
            states = [menu_cache_state(api.Environment(env.cr, user.id, {'allowed_company_ids': [company], 'lang': lang}))
                      for lang in dict.fromkeys([user.lang or 'en_US', 'zh_CN'])]
            report['companies'].append({'company_id': company, 'menu_cache_states': states,
                'existing_dimensions': actor['app.menu.config'].sudo().with_context(active_test=False).search_read(
                    [('target_model', '=', '__all__'), ('scene', '=', 'web'), ('company_id', '=', company)],
                    ['lang', 'is_active', 'last_generated', 'version'], limit=20)})
            continue
        sizes = {model: actor[model].search_count([]) for model in ('project.project', 'construction.contract', 'payment.request')}
        observations = []
        first_profiler = cProfile.Profile() if mode == 'profile_first' else None
        for index in range(6 if mode == 'observe' else 1):
            before_queries = getattr(env.cr, 'sql_log_count', None)
            started = time.perf_counter()
            if first_profiler:
                first_profiler.enable()
            try:
                reply = SystemInitHandler(env=actor).handle(payload={'params': request_params})
            finally:
                if first_profiler:
                    first_profiler.disable()
            elapsed = round((time.perf_counter() - started) * 1000, 2)
            assert reply.ok, 'system.init failed'
            profile = reply.meta.get('startup_profile')
            assert profile and isinstance(profile.get('timings_ms'), dict), 'startup timing declaration missing'
            after_queries = getattr(env.cr, 'sql_log_count', None)
            observations.append({'index': index, 'state': 'process_first_for_company' if index == 0 else 'subsequent_same_process',
                'profiled': first_profiler is not None, 'elapsed_ms': elapsed, 'sql_count': after_queries - before_queries if isinstance(before_queries, int) and isinstance(after_queries, int) else None,
                'startup_profile': profile,
                'navigation_sha256': hashlib.sha256(json.dumps(reply.data.get('navigation'),sort_keys=True,default=str).encode()).hexdigest()})
        candidate_strip = system_init._strip_ui_base_contract_for_frontend
        root_shape = {}
        scene_shape = {}
        projection_shape = {}
        def count_shape(value):
            pending = [value]
            total = 0
            while pending:
                item = pending.pop()
                total += 1
                if isinstance(item, dict):
                    pending.extend(item.values())
                elif isinstance(item, list):
                    pending.extend(item)
            return total
        def inspect_strip(value):
            system_init._strip_ui_base_contract_for_frontend = candidate_strip
            if isinstance(value, dict):
                root_shape.update({key: count_shape(item) for key, item in value.items()})
                ready = value.get('scene_ready_contract') or {}
                for row in ready.get('scenes', []):
                    if not isinstance(row, dict):
                        continue
                    for key, item in row.items():
                        scene_shape[key] = scene_shape.get(key, 0) + count_shape(item)
            started = time.perf_counter()
            stripped = candidate_strip(value)
            projection_shape['strip_elapsed_ms'] = round((time.perf_counter() - started) * 1000, 2)
            projection_shape['input_nodes'] = count_shape(value)
            projection_shape['stripped_nodes'] = count_shape(stripped)
            return stripped
        if mode == 'shape':
            try:
                system_init._strip_ui_base_contract_for_frontend = inspect_strip
                inspected_reply = SystemInitHandler(env=actor).handle(payload={'params': request_params})
                assert inspected_reply.ok
                projection_shape['final_nodes'] = count_shape(inspected_reply.data)
                projection_shape['final_json_bytes'] = len(json.dumps(inspected_reply.data, ensure_ascii=False, default=str).encode())
                projection_shape['final_top_level_nodes'] = {key: count_shape(item) for key, item in inspected_reply.data.items()}
            finally:
                system_init._strip_ui_base_contract_for_frontend = candidate_strip
        sql_origins = {}
        if mode == 'sql':
            original_execute = env.cr.execute
            def trace_execute(*args, **kwargs):
                frame = sys._getframe(1)
                owners = []
                while frame is not None:
                    filename = frame.f_code.co_filename
                    if str(frame.f_globals.get('__name__', '')).startswith('odoo.addons.smart_'):
                        owners.append(Path(filename).name + ':' + frame.f_code.co_name + ':' + str(frame.f_lineno))
                        if len(owners) == 3:
                            break
                    frame = frame.f_back
                del frame
                key = ' <- '.join(owners) or 'odoo_framework'
                started = time.perf_counter()
                try:
                    return original_execute(*args, **kwargs)
                finally:
                    row = sql_origins.setdefault(key, {'count': 0, 'elapsed_ms': 0.0})
                    row['count'] += 1
                    row['elapsed_ms'] += (time.perf_counter() - started) * 1000
            try:
                env.cr.execute = trace_execute
                sql_reply = SystemInitHandler(env=actor).handle(payload={'params': request_params})
                assert sql_reply.ok
            finally:
                env.cr.execute = original_execute
        functions = []
        if mode in {'profile', 'profile_first'}:
            profiler = first_profiler or cProfile.Profile()
            if mode == 'profile':
                profiler.enable()
                try:
                    profiled_reply = SystemInitHandler(env=actor).handle(payload={'params': request_params})
                finally:
                    profiler.disable()
                assert profiled_reply.ok, 'profiled system.init failed'
            stats = pstats.Stats(profiler)
            for (filename, line, function), (primitive, calls, self_time, cumulative, callers) in stats.stats.items():
                functions.append({'file': Path(filename).name, 'line': line, 'function': function,
                                  'calls': calls, 'self_ms': round(self_time * 1000, 2),
                                  'cumulative_ms': round(cumulative * 1000, 2)})
            functions.sort(key=lambda row: row['cumulative_ms'], reverse=True)
        candidate_strip = system_init._strip_ui_base_contract_for_frontend
        paired = []
        menu_service_class = None
        original_menu_batch = None
        if mode in {'menu_compare', 'path_compare', 'scene_compare'}:
            if mode == 'scene_compare':
                from odoo.addons.smart_core.governance import scene_normalizer
                menu_service_class = scene_normalizer
                compared_method = '_resolve_xmlids_batch'
                expected_source_hash = os.environ.get('PRODUCT_PERFORMANCE_SCENE_SHA256')
                source_label = 'scene_normalizer_sha256'
            else:
                from odoo.addons.smart_core.delivery.menu_service import MenuService
                menu_service_class = MenuService
                compared_method = '_native_visible_menu_paths' if mode == 'path_compare' else '_action_xmlids_from_facts'
                expected_source_hash = os.environ.get('PRODUCT_PERFORMANCE_MENU_SHA256')
                source_label = 'menu_service_sha256'
            original_menu_batch = getattr(menu_service_class, compared_method)
            compared_source = Path(inspect.getsourcefile(menu_service_class))
            compared_hash = hashlib.sha256(compared_source.read_bytes()).hexdigest()
            assert compared_hash == expected_source_hash, 'compared owner identity mismatch'
            report[source_label] = compared_hash
        try:
            for pair in range(5 if mode in {'compare', 'menu_compare', 'path_compare', 'scene_compare'} else 0):
                results = {}
                # Alternate order to avoid always assigning later/warmed work
                # to the candidate. Both execute with one actor/env/data state.
                order = ('previous', 'candidate') if pair % 2 == 0 else ('candidate', 'previous')
                for variant in order:
                    if mode in {'menu_compare', 'path_compare', 'scene_compare'}:
                        setattr(menu_service_class, compared_method, (lambda self, rows: {}) if variant == 'previous' else original_menu_batch)
                    else:
                        system_init._strip_ui_base_contract_for_frontend = previous_strip if variant == 'previous' else candidate_strip
                    query_count_before = env.cr.sql_log_count
                    started = time.perf_counter()
                    result = SystemInitHandler(env=actor).handle(payload={'params': request_params})
                    duration = round((time.perf_counter() - started) * 1000, 2)
                    assert result.ok, 'paired system.init failed'
                    results[variant] = {'elapsed_ms': duration, 'sql_count': env.cr.sql_log_count - query_count_before,
                        'data_sha256': hashlib.sha256(json.dumps(result.data,sort_keys=True,default=str).encode()).hexdigest()}
                paired.append({'index': pair + 1, 'order': list(order), **results,
                               'data_equal': results['previous']['data_sha256'] == results['candidate']['data_sha256']})
        finally:
            system_init._strip_ui_base_contract_for_frontend = candidate_strip
            if menu_service_class is not None:
                setattr(menu_service_class, compared_method, original_menu_batch)
        report['companies'].append({'company_id': company, 'visible_record_counts': sizes, 'samples': observations, 'diagnostic_profile_top': functions[:35], 'diagnostic_self_top': sorted(functions, key=lambda row: row['self_ms'], reverse=True)[:35], 'paired_comparison': paired, 'strip_input_node_counts': root_shape, 'scene_field_node_counts': scene_shape, 'sql_origins': sql_origins, 'projection_shape': projection_shape})
    print('RUNTIME_PERFORMANCE_OBSERVATION=' + json.dumps(report, sort_keys=True, default=str), flush=True)
finally:
    env.cr.rollback()
    env.cr.commit = original_commit
