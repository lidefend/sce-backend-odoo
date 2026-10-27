#!/usr/bin/env python3
"""Select backend test modules from exact Git trees; never treat unknown as skip.

No result cache: excluded modules are outside impact, not claimed as executed.
The nightly runner still discovers and executes its entire module set.
"""
from __future__ import annotations

import argparse
import ast
import fnmatch
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]
ROOTS = ('addons', 'demo_addons')
STDLIB = frozenset(sys.stdlib_module_names)
GLOBAL = ('Dockerfile*', 'docker-compose*', 'requirements*', 'odoo.conf',
          'config/odoo*', 'scripts/test/**', 'scripts/ci/orm_result_guard.sh',
          '.github/workflows/backend_test_suite.yml',
          '.github/workflows/professional_quality_gate.yml', 'make/ci.mk',
          'make/dev_test.mk', 'Makefile')
NON_RUNTIME = ('docs/**', '.agent/**', 'frontend/**', 'make/frontend.mk', '*.md',
               'scripts/verify/**', 'scripts/ci/**', 'scripts/ops/**')

# Existing CI control-plane inputs are not Odoo runtime inputs. Changes still
# require their owning tool gate, and concrete test-file consumers take priority.
# Do not exempt scripts/**: runner and unknown paths retain conservative scope.
CONTROL_PLANE = {
    'scripts/ci/backend_impact_plan.py': 'verify.ci.workflow.contract',
    'scripts/ci/backend_suite_plan.py': 'verify.ci.workflow.contract',
    'scripts/ci/backend_test_receipt.py': 'verify.ci.workflow.contract',
    'scripts/ci/ci_risk_classifier.py': 'verify.ci.workflow.contract',
    'scripts/ci/select_authoritative_workflow_run.py': 'verify.ci.workflow.contract',
    'scripts/ops/daily_runtime_release_orchestration.py': 'verify.daily.runtime.release_orchestration.unit',
    'scripts/ops/daily_runtime_database_duty.py': 'verify.daily.runtime.database.duty',
    'scripts/ops/daily_runtime_source_revision_align.py': 'verify.daily.runtime.source_revision.align',
    'scripts/ops/daily_runtime_bundle_sync.py': 'verify.daily.runtime.main.bundle_sync',
    'scripts/ops/daily_candidate_bundle_sync.py': 'verify.daily.runtime.candidate.bundle_sync',
    'scripts/ops/daily_runtime_published_face_converge.py': 'verify.daily.runtime.published_face.converge',
    'scripts/ops/quick_input_scope.py': 'verify.quick.input_scope.unit',
    'scripts/audit/verification_lane_dispositions.json': 'verify.verification.lane_coverage',
    'scripts/audit/verification_lane_exemptions.json': 'verify.verification.lane_coverage',
}


def classify_import_top(top: str, local_modules: set[str]) -> str:
    """Classify a top-level import name; an unknown name is external, never internal."""
    if top == 'odoo':
        return 'odoo'
    if top in STDLIB:
        return 'stdlib'
    if top in local_modules:
        return 'local_module'
    return 'external'


def import_tops_from_line(line: str) -> tuple[list[str], bool]:
    """Extract top-level import names from one source line: (tops, ambiguous).

    Relative imports are internal. A line that looks like an import but cannot
    be fully parsed is flagged ambiguous so the caller can fail closed instead
    of silently missing an external dependency.
    """
    stripped = line.strip()
    if stripped.startswith('from .'):
        return [], False
    if stripped == 'import':
        return [], True
    if stripped.startswith('import '):
        rest = stripped[len('import '):].split('#', 1)[0].strip()
        if not rest:
            return [], True
        tops: list[str] = []
        ambiguous = False
        for part in rest.split(','):
            part = part.strip()
            if not part:
                ambiguous = True
                continue
            name = part.split(' as ', 1)[0].strip()
            if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.]*', name):
                ambiguous = True
                continue
            tops.append(name.split('.')[0])
        return tops, ambiguous
    if stripped == 'from':
        return [], True
    if stripped.startswith('from '):
        rest = stripped[len('from '):].split(' import', 1)[0].strip()
        if not rest or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.]*', rest):
            return [], True
        return [rest.split('.')[0]], False
    return [], False

def _is_cr_receiver(node) -> bool:
    if isinstance(node, ast.Name):
        return node.id in ('cr', '_cr')
    if isinstance(node, ast.Attribute):
        return node.attr in ('cr', '_cr')
    return False


def sql_execute_sites(source: str, path: str) -> tuple[list[str], list[str]]:
    """Literal SQL execute sites resolve; every other SQL form stays unresolved."""
    tree = ast.parse(source, filename=path)
    resolved: set[str] = set()
    unresolved: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        func = node.func
        if not isinstance(func, ast.Attribute) or func.attr != 'execute' or not _is_cr_receiver(func.value):
            continue
        argument = node.args[0]
        if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
            resolved.add(hashlib.sha256(argument.value.encode('utf-8')).hexdigest())
        else:
            unresolved.add(f'{path}:{node.lineno}')
    return sorted(resolved), sorted(unresolved)


def git(*args: str) -> str:
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True)


def test_file_reads(source: str, path: str) -> tuple[list[str], list[int]]:
    """Extract concrete Path reads without importing/executing test code.

    This is a bounded supplement to module dependencies, not a complete Python
    dependency resolver. Unresolved read sites remain visible to future receipt
    consumers; they must never be treated as proof of an empty input set.
    """
    tree = ast.parse(source, filename=path)
    anchor = PurePosixPath('/repository')
    found, unresolved = set(), set()
    lambda_nodes = {id(node) for item in ast.walk(tree) if isinstance(item, ast.Lambda)
                    for node in ast.walk(item)}

    def value(node, env):
        if isinstance(node, ast.Constant) and isinstance(node.value, (str, int)):
            return node.value
        if isinstance(node, ast.Name):
            return env.get(node.id)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            left, right = value(node.left, env), value(node.right, env)
            if isinstance(left, PurePosixPath) and isinstance(right, str):
                return left / right
        if isinstance(node, ast.Attribute) and node.attr == 'parent':
            parent = value(node.value, env)
            return parent.parent if isinstance(parent, PurePosixPath) else None
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute) and node.value.attr == 'parents':
            parent, index = value(node.value.value, env), value(node.slice, env)
            if isinstance(parent, PurePosixPath) and type(index) is int and 0 <= index < len(parent.parents):
                return parent.parents[index]
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and env.get(node.func.id) is PurePosixPath and len(node.args) == 1:
                arg = value(node.args[0], env)
                if isinstance(arg, (str, PurePosixPath)):
                    return PurePosixPath(arg)
            if isinstance(node.func, ast.Attribute) and node.func.attr == 'resolve' and not node.args:
                return value(node.func.value, env)
        return None

    def scope(body, inherited, class_body=False):
        nodes, children = [], []
        def visit(node):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                children.append(node)
                # Definition-time reads run in the outer scope, not the body.
                expressions = list(node.decorator_list)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    expressions += node.args.defaults + [x for x in node.args.kw_defaults if x]
                else:
                    expressions += node.bases + [x.value for x in node.keywords]
                for expression in expressions:
                    visit(expression)
                return
            nodes.append(node)
            for child in ast.iter_child_nodes(node):
                visit(child)
        for node in body:
            visit(node)
        env, assignments = dict(inherited), {}
        simple_targets = {id(target) for node in nodes if isinstance(node, ast.Assign)
                          for target in node.targets if isinstance(target, ast.Name)}
        for node in nodes:
            if isinstance(node, ast.ImportFrom) and node.module == 'pathlib':
                for alias in node.names:
                    if alias.name == 'Path':
                        env[alias.asname or alias.name] = PurePosixPath
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    if isinstance(node, ast.ImportFrom) and node.module == 'pathlib' and alias.name == 'Path':
                        continue
                    assignments.setdefault(alias.asname or alias.name.split('.')[0], []).extend([None, None])
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        assignments.setdefault(target.id, []).append(node.value)
            if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)) and id(node) not in simple_targets:
                assignments.setdefault(node.id, []).extend([None, None])
            if isinstance(node, ast.ExceptHandler) and node.name:
                assignments.setdefault(node.name, []).extend([None, None])
            # Unsupported binding forms must not retain an outer constant.
            targets = []
            if isinstance(node, (ast.AnnAssign, ast.AugAssign, ast.NamedExpr)):
                targets = [node.target]
            elif isinstance(node, (ast.For, ast.AsyncFor, ast.comprehension)):
                targets = [node.target]
            elif isinstance(node, ast.withitem) and node.optional_vars:
                targets = [node.optional_vars]
            for target in targets:
                for binding in ast.walk(target):
                    if isinstance(binding, ast.Name):
                        assignments.setdefault(binding.id, []).extend([None, None])
        for child in children:
            assignments.setdefault(child.name, []).extend([None, None])
        # Reassignments are ambiguous, not "last assignment wins".
        for name in assignments:
            env.pop(name, None)
        for _ in range(len(assignments)):
            for name, expressions in assignments.items():
                if len(expressions) == 1:
                    env[name] = value(expressions[0], env)
        for node in nodes:
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr not in {'read_text', 'read_bytes'}:
                continue
            if id(node) in lambda_nodes:
                unresolved.add(node.lineno)
                continue
            resolved = value(node.func.value, env)
            if isinstance(resolved, PurePosixPath) and resolved.is_relative_to(anchor) and '..' not in resolved.parts:
                found.add(str(resolved.relative_to(anchor)))
            else:
                unresolved.add(node.lineno)
        for child in children:
            # A method's bare names close over the class's outer scope, not
            # class attributes (Python's class namespace is not a closure).
            child_env = dict(inherited if class_body else env)
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                arguments = child.args.posonlyargs + child.args.args + child.args.kwonlyargs
                for argument in arguments + [a for a in (child.args.vararg, child.args.kwarg) if a]:
                    child_env.pop(argument.arg, None)
            scope(child.body, child_env, isinstance(child, ast.ClassDef))
    scope(tree.body, {'__file__': anchor / path})
    return sorted(found), sorted(unresolved)


def snapshot(revision: str) -> dict:
    files = git('ls-tree', '-r', '--name-only', revision).splitlines()
    modules = {}
    for path in files:
        parts = path.split('/')
        if len(parts) != 3 or parts[0] not in ROOTS or parts[2] != '__manifest__.py':
            continue
        name = parts[1]
        if not re.fullmatch(r'[a-zA-Z_][a-zA-Z0-9_]*', name) or name in modules:
            raise ValueError(f'invalid or ambiguous module: {name}')
        data = ast.literal_eval(git('show', f'{revision}:{path}'))
        deps = data.get('depends', [])
        if not isinstance(deps, list) or not all(isinstance(v, str) for v in deps):
            raise ValueError(f'invalid dependencies: {path}')
        prefix = '/'.join(parts[:2]) + '/'
        modules[name] = {'depends': set(deps), 'prefix': prefix,
                         'tests': any(f.startswith(prefix + 'tests/') and f.endswith('.py') for f in files),
                         'installable': data.get('installable', True)}
    # Cross-module Python imports also express consumers, including test helpers.
    imports = subprocess.run(
        ['git', 'grep', '-I', '-n', '-E', r'odoo\.addons\.[A-Za-z_]', revision,
         '--', 'addons/**/*.py', 'demo_addons/**/*.py'],
        cwd=ROOT, text=True, capture_output=True)
    if imports.returncode not in (0, 1):
        raise ValueError('cannot resolve cross-module imports')
    for line in imports.stdout.splitlines():
        _, path, _, source = line.split(':', 3)
        parts = path.split('/')
        if len(parts) >= 3 and parts[1] in modules:
            modules[parts[1]]['depends'].update(re.findall(r'odoo\.addons\.([A-Za-z_][A-Za-z_0-9]*)', source))
    for name, data in modules.items():
        reads, unresolved = set(), []
        for path in files:
            if not (path.startswith(data['prefix'] + 'tests/') and path.endswith('.py')):
                continue
            source = git('show', f'{revision}:{path}')
            if not any(token in source for token in ('read_text', 'read_bytes')):
                continue
            paths, lines = test_file_reads(source, path)
            reads.update(paths)
            unresolved.extend(f'{path}:{line}' for line in lines)
        data['file_inputs'] = sorted(reads)
        data['unresolved_file_reads'] = unresolved
    # External package imports: classify every top-level import in module files.
    imports = subprocess.run(
        ['git', 'grep', '-I', '-n', '-E',
         r'^[[:space:]]*(import[[:space:]]+[A-Za-z_]|from[[:space:]]+[A-Za-z_][A-Za-z0-9_.]*[[:space:]]+import)',
         revision, '--', 'addons/**/*.py', 'demo_addons/**/*.py'],
        cwd=ROOT, text=True, capture_output=True)
    if imports.returncode not in (0, 1):
        raise ValueError('cannot resolve Python import sites')
    local_tops = set(modules)
    for line in imports.stdout.splitlines():
        _rev, path, lineno, source_line = line.split(':', 3)
        parts = path.split('/')
        if len(parts) < 3 or parts[1] not in modules:
            continue
        tops, ambiguous = import_tops_from_line(source_line)
        if ambiguous:
            modules[parts[1]].setdefault('unresolved_imports', set()).add(f'{path}:{lineno}')
            continue
        for top in tops:
            if classify_import_top(top, local_tops) == 'external':
                modules[parts[1]].setdefault('external_imports', set()).add(top)
    # SQL execute sites: literal SQL resolves; dynamic SQL stays unresolved.
    sql_files = subprocess.run(
        ['git', 'grep', '-I', '-l', '-E', r'(cr|_cr)[[:space:]]*\.execute\(',
         revision, '--', 'addons/**/*.py', 'demo_addons/**/*.py'],
        cwd=ROOT, text=True, capture_output=True)
    if sql_files.returncode not in (0, 1):
        raise ValueError('cannot resolve SQL execute sites')
    for line in sql_files.stdout.splitlines():
        if ':' not in line:
            continue
        _rev, path = line.split(':', 1)
        parts = path.split('/')
        if len(parts) < 3 or parts[1] not in modules:
            continue
        resolved, unresolved = sql_execute_sites(git('show', line), path)
        modules[parts[1]].setdefault('sql_reads', set()).update(resolved)
        modules[parts[1]].setdefault('unresolved_sql', set()).update(unresolved)
    for data in modules.values():
        data['external_imports'] = sorted(data.get('external_imports', ()))
        data['sql_reads'] = sorted(data.get('sql_reads', ()))
        data['unresolved_sql'] = sorted(data.get('unresolved_sql', ()))
        data['unresolved_imports'] = sorted(data.get('unresolved_imports', ()))
    return modules


def select(paths: list[str], before: dict, after: dict, *, full: bool = False) -> dict:
    runnable = {k for k, v in after.items() if v['tests'] and v.get('installable', True)}
    graph = {}
    for tree in (before, after):
        for name, data in tree.items():
            graph.setdefault(name, set()).update(data['depends'])
    seeds, reasons, test_readers, tool_checks = set(), [], set(), set()
    file_consumers = {}
    for tree in (before, after):
        for name, data in tree.items():
            for path in data.get('file_inputs', []):
                file_consumers.setdefault(path, set()).add(name)
    for path in paths:
        parts = path.split('/')
        if path.startswith('/') or '..' in parts:
            raise ValueError('invalid changed path')
        # A test-only fixture changes the reading test, not its module's product
        # code. Keep product dependency propagation for actual module changes.
        test_readers.update(file_consumers.get(path, set()))
        if len(parts) >= 3 and parts[0] in ROOTS:
            if parts[1] in graph:
                seeds.add(parts[1])
            else:
                reasons.append('unknown_module:' + path)
        elif path in CONTROL_PLANE:
            tool_checks.add(CONTROL_PLANE[path])
        elif any(fnmatch.fnmatchcase(path, pattern) for pattern in GLOBAL):
            reasons.append('shared_runtime:' + path)
        elif not any(fnmatch.fnmatchcase(path, pattern) for pattern in NON_RUNTIME):
            reasons.append('unknown_impact:' + path)
    affected = set(seeds)
    while True:
        consumers = {name for name, deps in graph.items() if deps & affected}
        if consumers <= affected:
            break
        affected |= consumers
    if full:
        reasons.append('explicit_full')
    affected |= test_readers
    selected = runnable if reasons else runnable & affected
    # A module change without any executable owner/consumer must not turn green.
    for seed in sorted(seeds | test_readers):
        closure = {seed}
        while True:
            consumers = {name for name, deps in graph.items() if deps & closure}
            if consumers <= closure:
                break
            closure |= consumers
        if not closure & selected:
            raise ValueError(f'changed backend module has no runnable test coverage: {seed}')
    if not runnable:
        raise ValueError('no runnable backend tests')
    return {'mode': 'full' if reasons else 'incremental', 'reasons': sorted(reasons),
            'seeds': sorted(seeds), 'affected': sorted(affected),
            'modules': sorted(selected), 'excluded': sorted(runnable - selected),
            'file_input_hits': {path: sorted(file_consumers[path]) for path in sorted(paths) if path in file_consumers},
            'unresolved_test_file_reads': sorted({site for tree in (before, after)
                                                for data in tree.values()
                                                for site in data.get('unresolved_file_reads', [])}),
            'changed_paths': sorted(paths), 'tool_checks': sorted(tool_checks),
            'scope_status': 'required' if selected else 'NOT_APPLICABLE'}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', required=True)
    parser.add_argument('--head', required=True)
    parser.add_argument('--full', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--github-output', type=Path)
    args = parser.parse_args()
    base = git('rev-parse', '--verify', args.base + '^{commit}').strip()
    head = git('rev-parse', '--verify', args.head + '^{commit}').strip()
    # No rename collapsing: both old and new owners remain in the impact set.
    paths = git('diff', '--no-renames', '--name-only', base, head, '--').splitlines()
    before, after = snapshot(base), snapshot(head)
    plan = select(paths, before, after, full=args.full)
    plan.update(schema='backend-impact/v1', base=base, head=head)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(plan, indent=2) + '\n')
    print(json.dumps(plan, indent=2))
    if args.github_output:
        with args.github_output.open('a') as stream:
            stream.write('modules=' + ' '.join(plan['modules']) + '\n')
            stream.write('required=' + str(bool(plan['modules'])).lower() + '\n')
            stream.write('tool_checks=' + ' '.join(plan['tool_checks']) + '\n')
            stream.write('scope_status=' + plan['scope_status'] + '\n')


if __name__ == '__main__':
    main()
