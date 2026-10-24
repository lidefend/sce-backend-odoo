"""Controlled model-field advisory bindings; no XML protocol or business rules."""
import ast
import re
from copy import deepcopy

from .form_configuration_compiler import FormConfigurationError

DRAFT_FEEDBACK_CAPABILITY = "form.feedback.draft.v1"
DRAFT_FEEDBACK_VISIBILITY_OWNER = "feedback_evaluation"


def fail(code, path):
    raise FormConfigurationError(code, path)


def declaration(field, path):
    value = getattr(field, 'sc_feedback_usage', None)
    if value is None:
        return None
    if (type(value) is not dict or set(value) != {'purpose', 'occurrences'}
            or value['purpose'] != 'advisory' or getattr(field, 'sc_ui_usage', None) != 'interaction'
            or field.type not in {'char', 'text'}):
        fail('FEEDBACK_CONFIG_INVALID', path)
    rows = value['occurrences']
    if type(rows) is not list or not rows:
        fail('FEEDBACK_CONFIG_INVALID', path)
    seen = set()
    for row in rows:
        if type(row) is not dict or set(row) != {'view_xmlid', 'native_locator', 'occurrence_index'}:
            fail('FEEDBACK_CONFIG_INVALID', path)
        view, locator, index = row['view_xmlid'], row['native_locator'], row['occurrence_index']
        if (type(view) is not str or not re.fullmatch(r'[A-Za-z_][\w]*\.[A-Za-z_][\w]*', view)
                or type(locator) is not str or not re.fullmatch(r'(?:/[A-Za-z_][\w]*\[[1-9][0-9]*\])+', locator)
                or type(index) is not int or index <= 0):
            fail('FEEDBACK_CONFIG_INVALID', path)
        identity = (view, locator, index)
        if identity in seen:
            fail('FEEDBACK_CONFIG_INVALID', path)
        seen.add(identity)
    return rows


def bindings(env, model, field, view_id, path):
    rows = declaration(field, path)
    if rows is None:
        return None
    if type(view_id) is not int or view_id <= 0:
        fail('FEEDBACK_SOURCE_INVALID', path)
    matched = []
    for row in rows:
        view = env.ref(row['view_xmlid'], raise_if_not_found=False)
        if (not view or getattr(view, '_name', None) != 'ir.ui.view'
                or view.model != model or view.type != 'form'):
            fail('FEEDBACK_SOURCE_INVALID', path)
        if view.id == view_id:
            matched.append(row)
    return matched


def identity(node):
    return (node.get('nativeLocator', node.get('native_locator')),
            node.get('occurrenceIndex', node.get('occurrence_index')))


def walk(nodes, parent=None):
    for node in nodes:
        yield node, parent
        for key in ('children', 'pages', 'tabs', 'nodes', 'items'):
            if isinstance(node.get(key), list):
                yield from walk(node[key], node)


def condition(host, field_name, path):
    """Verify raw/native/AST agreement before deriving a private evaluation view.

    First supported form is Odoo's `not <Name>`. Original modifiers are untouched.
    No expression execution, unknown-key filtering, or permissive AST fallback.
    """
    attributes, modifiers = host.get('attributes'), host.get('modifiers')
    if type(attributes) is not dict or type(modifiers) is not dict:
        fail('FEEDBACK_CONDITION_INVALID', path)
    raw = attributes.get('invisible')
    value = modifiers.get('invisible')
    if type(raw) is not str or type(value) is not dict:
        fail('FEEDBACK_CONDITION_INVALID', path)
    try:
        parsed = ast.parse(raw.strip(), mode='eval').body
    except (SyntaxError, ValueError):
        fail('FEEDBACK_CONDITION_INVALID', path)
    if not (isinstance(parsed, ast.UnaryOp) and isinstance(parsed.op, ast.Not)
            and isinstance(parsed.operand, ast.Name) and parsed.operand.id == field_name):
        fail('FEEDBACK_CONDITION_INVALID', path)
    expected = {'kind': 'not', 'expr': {'kind': 'field_truthy', 'field': field_name}}
    if value != {**expected, 'raw': raw.strip()}:
        fail('FEEDBACK_CONDITION_INVALID', path)
    return expected


def host_shape(host, source, path):
    if (host is None or host.get('type') not in {'div', 'container'}
            or host.get('children') != [source] or host.get('text')
            or not identity(host)[0] or type(identity(host)[1]) is not int):
        fail('FEEDBACK_SOURCE_INVALID', path)


def has_draft_evaluation(model, field):
    method = getattr(model, field.compute, None) if isinstance(field.compute, str) else None
    return getattr(getattr(method, '__func__', method), '_sc_feedback_evaluation_review', None) is not None


def project(source_contract, env):
    """Project only controlled native field bindings, before scoped body admission."""
    if env is None or source_contract.get('view_type') not in (None, 'form'):
        return source_contract
    model = source_contract.get('model')
    if not model:
        return source_contract
    model_obj = env[model]
    declared = [(name, field) for name, field in getattr(model_obj, '_fields', {}).items()
                if getattr(field, 'sc_feedback_usage', None) is not None]
    if not declared:
        return source_contract
    source = deepcopy(source_contract)
    marker = source.get('nativeFormProjection')
    ui = source.get('ui') or source
    layout = marker.get('layout', []) if marker else ((ui.get('views') or {}).get('form') or {}).get('layout', [])
    rows = list(walk(layout))
    view_id = source.get('view_id') or (source.get('projection_identity') or {}).get('source_view_id')
    from .unified_page_contract_v2_assembler import _fingerprint
    for name, field in declared:
        path = 'native.field.' + name
        for binding in bindings(env, model, field, view_id, path):
            matches = [(n, p) for n, p in rows if identity(n) == (binding['native_locator'], binding['occurrence_index'])]
            if len(matches) != 1:
                fail('FEEDBACK_SOURCE_INVALID', path)
            node, host = matches[0]
            if node.get('type') != 'field' or node.get('name') != name:
                fail('FEEDBACK_SOURCE_INVALID', path)
            host_shape(host, node, path)
            condition(host, name, path)
            if host.get('componentKey') or host.get('componentConfig'):
                fail('FEEDBACK_OWNERSHIP_CONFLICT', path)
            # Derive provenance from this resolved native view, not page configuration.
            authority = {'kind': 'native_view', 'model': model, 'view_id': view_id}
            for item in (host, node):
                prior = item.get('source_authority') or item.get('sourceAuthority') or {}
                if any(k in prior and prior[k] != v for k, v in authority.items() if k != 'kind'):
                    fail('FEEDBACK_SOURCE_INVALID', path)
                item['source_authority'] = {**prior, **authority}
            locator, occurrence = identity(node)
            ref = f'field.{name}.occ.' + _fingerprint({'locator': locator, 'occurrence': occurrence})
            host['componentKey'] = 'sc.feedback.message'
            config = {'purpose': 'advisory', 'contentRef': {'containerId': ref}}
            if has_draft_evaluation(model_obj, field):
                config['evaluation'] = {
                    'capability': DRAFT_FEEDBACK_CAPABILITY,
                    'visibilityOwner': DRAFT_FEEDBACK_VISIBILITY_OWNER,
                }
            host['componentConfig'] = config
    return source


def validate_binding(env, model, field, host, source, originals, path):
    """Repeat model authorization against immutable native identity at final checks."""
    authority = source.get('sourceAuthority') or {}
    if authority.get('kind') != 'native_view' or authority.get('model') != model:
        fail('FEEDBACK_SOURCE_INVALID', path)
    rows = bindings(env, model, field, authority.get('view_id'), path)
    if not rows or not any(identity(source) == (r['native_locator'], r['occurrence_index']) for r in rows):
        fail('FEEDBACK_SOURCE_INVALID', path)
    if host.get('componentConfig', {}).get('purpose') != 'advisory':
        fail('FEEDBACK_CONFIG_INVALID', path)
    host_shape(host, source, path)
    original_hosts = [n for n, _ in originals if identity(n) == identity(host)]
    if len(original_hosts) != 1 or host.get('modifiers') != original_hosts[0].get('modifiers') or host.get('attributes') != original_hosts[0].get('attributes'):
        fail('FEEDBACK_CONDITION_INVALID', path)
    return condition(host, source['name'], path)
