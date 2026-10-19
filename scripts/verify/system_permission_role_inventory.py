"""Offline declaration inventory, never a runtime authorization verdict.

Read manifest XML in order. Only supported literal group operations are interpreted;
external references and unsupported expressions are reported, never assumed safe.
"""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
MODULE = 'smart_construction_core'


def reference(value, module):
    return value if '.' in value else module + '.' + value


def expression(source, module):
    def read(node):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, (ast.List, ast.Tuple)):
            return [read(item) for item in node.elts]
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == 'ref' and len(node.args) == 1 and not node.keywords):
            value = read(node.args[0])
            if isinstance(value, str):
                return reference(value, module)
        raise ValueError('unsupported XML expression')
    return read(ast.parse(source, mode='eval').body)


def apply_commands(existing, commands):
    result = set(existing)
    for command in commands:
        if not isinstance(command, list) or not command:
            raise ValueError('invalid group relation command')
        op = command[0]
        if op == 6 and len(command) == 3 and isinstance(command[2], list):
            if not all(isinstance(x, str) for x in command[2]):
                raise ValueError('group references must be XMLIDs')
            result = set(command[2])
        elif op in (3, 4) and len(command) in (2, 3) and isinstance(command[1], str):
            if op == 4:
                result.add(command[1])
            else:
                result.discard(command[1])
        elif op == 5 and len(command) in (1, 3):
            result.clear()
        else:
            raise ValueError('unsupported group relation command')
    return result


def closure(groups, start):
    seen, unknown = set(), set()
    pending = [start]
    while pending:
        key = pending.pop()
        if key in seen:
            continue
        seen.add(key)
        row = groups.get(key)
        if row is None:
            unknown.add(key)
        else:
            pending.extend(row['implied'])
    return seen, unknown


def load_groups(root):
    base = root / 'addons' / MODULE
    manifest = base / '__manifest__.py'
    inputs = [manifest]
    groups, issues = {}, []
    for name in ast.literal_eval(manifest.read_text())['data']:
        if not name.endswith('.xml'):
            continue
        source = base / name
        inputs.append(source)
        for record in ET.parse(source).findall('.//record'):
            if record.get('model') != 'res.groups':
                continue
            key = reference(record.attrib['id'], MODULE)
            row = groups.setdefault(key, {'label': '', 'implied': set(), 'assignable': False, 'sources': []})
            row['sources'].append(str(source.relative_to(root)))
            for field in record.findall('field'):
                field_name = field.get('name')
                try:
                    if field_name == 'name':
                        row['label'] = field.text or ''
                    elif field_name == 'implied_ids':
                        row['implied'] = apply_commands(row['implied'], expression(field.attrib['eval'], MODULE))
                    elif field_name == 'sc_assignable_user_permission':
                        value = expression(field.attrib['eval'], MODULE) if 'eval' in field.attrib else (field.text or '').strip()
                        if value not in (True, False, 0, 1, '0', '1', 'True', 'False'):
                            raise ValueError('unsupported assignable flag')
                        row['assignable'] = value in (True, 1, '1', 'True')
                except (ValueError, KeyError, SyntaxError) as error:
                    issues.append({'group': key, 'file': str(source.relative_to(root)), 'field': field_name, 'reason': str(error)})
    return groups, issues, inputs


def catalog_hits(catalog, group_set):
    return {
        'explicit': sorted(row['role_code'] for row in catalog['default_roles'] if group_set.intersection(row.get('group_xmlids', []))),
        'capability_fallback_candidates': sorted(row['role_code'] for row in catalog['default_roles'] if group_set.intersection(row.get('capability_group_xmlids', []))),
    }


# These are search candidates, not a proof of model type or reachable writes.
RELATION_FIELDS = frozenset({'groups_id', 'implied_ids', 'users',
                             'sc_user_role_group_ids', 'sc_user_permission_group_ids'})


def python_write_candidates(source):
    tree = ast.parse(source)
    rows = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for key in node.keys:
                if isinstance(key, ast.Constant) and key.value in RELATION_FIELDS:
                    rows.add((key.lineno, key.value, 'dictionary_candidate'))
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                field = None
                if isinstance(target, ast.Attribute):
                    field = target.attr
                elif isinstance(target, ast.Subscript) and isinstance(target.slice, ast.Constant):
                    field = target.slice.value
                if field in RELATION_FIELDS:
                    rows.add((target.lineno, field, 'assignment_candidate'))
    return [{'line': line, 'field': field, 'kind': kind} for line, field, kind in sorted(rows)]


def write_inventory(root):
    rows, issues, inputs = [], [], {}
    for folder in ('addons', 'scripts'):
        for path in sorted((root / folder).rglob('*')):
            if path.suffix not in ('.py', '.xml') or not path.is_file():
                continue
            relative = path.relative_to(root).as_posix()
            # Explicit exclusion; test/probe writers remain a separate follow-up.
            if 'tests' in path.parts or path.name.startswith('test_'):
                continue
            source = path.read_text(encoding='utf-8')
            inputs[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
            try:
                if path.suffix == '.py':
                    candidates = python_write_candidates(source)
                else:
                    if not source.strip():
                        continue  # Empty files contain no declarations; keep their input hash.
                    candidates = []
                    for record in ET.fromstring(source).iter('record'):
                        model = record.get('model')
                        allowed = {'groups_id'} if model == 'res.users' else {'users', 'implied_ids'} if model == 'res.groups' else set()
                        for field in record.findall('field'):
                            if field.get('name') in allowed:
                                candidates.append({'record': record.get('id'), 'model': model,
                                                   'field': field.get('name'), 'kind': 'xml_declaration'})
                rows.extend({'file': relative, **row} for row in candidates)
            except (SyntaxError, ET.ParseError) as error:
                issues.append({'file': relative, 'reason': str(error)})
    return {'status': 'incomplete' if issues else 'candidate_inventory_complete',
            'authorization_verdict': 'not_evaluated', 'candidates': rows,
            'parse_issues': issues, 'inputs': inputs,
            'limitations': ['Static candidates require model/reachability review; dictionaries may be reads.',
                           'Dynamic keys, aliases, SQL, native Odoo and private customer modules are not resolved.',
                           'XML scan includes uninstalled declarations; test_* and tests/ are excluded.',
                           'No runtime write is performed; candidate coverage is not complete writer coverage.']}


def inventory(root):
    groups, issues, inputs = load_groups(root)
    policy = root / 'addons' / MODULE / 'data/formal_business_product_menu_policy_v1.json'
    catalog = json.loads(policy.read_text())['role_catalog']
    inputs.append(policy)
    rows = []
    for key, group in sorted(groups.items()):
        if not group['assignable'] and not key.startswith(MODULE + '.group_sc_role_'):
            continue
        effective, unknown = closure(groups, key)
        hits = catalog_hits(catalog, effective)
        rows.append({'group_xmlid': key, 'label': group['label'], 'assignable': group['assignable'],
                     'declared_closure': sorted(effective), 'unresolved_external_groups': sorted(unknown),
                     'catalog_candidates': hits, 'sources': sorted(set(group['sources'])),
                     'runtime_identity': 'not_run', 'runtime_authorization': 'not_run'})
    uncovered = [r['group_xmlid'] for r in rows if r['assignable'] and not any(r['catalog_candidates'].values())]
    return {'schema': 'system_permission_role_inventory.v1', 'mode': 'offline_declaration_only',
            'status': 'incomplete' if issues else 'inventory_complete',
            'authorization_verdict': 'not_evaluated',
            'limitations': ['P1 manifest only; dependency groups unresolved', 'XML initialization is not installed database state',
                            'Catalog hits are candidates, not resolver output; provider overlays and precedence are not executed',
                            'No ACL/record-rule evaluation or direct-user assignment inventory'],
            'inputs': {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(inputs))},
            'summary': {'declared_groups': len(groups), 'assignable_groups': sum(g['assignable'] for g in groups.values()),
                        'catalog_roles': len(catalog['default_roles']), 'rows': len(rows), 'unmapped_assignable_count': len(uncovered)},
            'unmapped_assignable_groups': uncovered, 'parse_issues': issues, 'roles': rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--write-candidates', action='store_true')
    args = parser.parse_args()
    output = Path(args.output).resolve()
    if not any(output.is_relative_to(ROOT / folder) for folder in ('.runtime', 'artifacts')):
        parser.error('output must be under ignored runtime evidence storage')
    report = write_inventory(ROOT) if args.write_candidates else inventory(ROOT)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'status': report['status'], **report.get('summary', {'candidates': len(report.get('candidates', []))}), 'report': str(output)}, ensure_ascii=False))
    return int(bool(report['parse_issues']))


if __name__ == '__main__':
    raise SystemExit(main())
