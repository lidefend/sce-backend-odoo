"""Compile native domain values to a bounded, data-only expression protocol.

Unlike modifiers, Python and/or return operands here (lists), not booleans.
No calls, arbitrary attributes, subscripts, or executable client code are admitted.
"""
import ast
import math


def compile_relation_domain(raw):
    if not isinstance(raw, str) or not raw.strip():
        return None
    dependencies = set()
    count = 0

    def visit(node, depth=0):
        nonlocal count
        count += 1
        if count > 512 or depth > 32:
            raise ValueError('expression_limit')
        def child(value):
            return visit(value, depth + 1)
        if isinstance(node, ast.Constant):
            value = node.value
            if value is None or isinstance(value, (str, bool)):
                return {'kind': 'literal', 'value': value}
            if isinstance(value, (int, float)) and math.isfinite(value) and abs(value) <= 9007199254740991:
                return {'kind': 'literal', 'value': value}
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)) and isinstance(node.operand, ast.Constant):
            value = node.operand.value
            if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and abs(value) <= 9007199254740991:
                return {'kind': 'literal', 'value': -value if isinstance(node.op, ast.USub) else value}
        if isinstance(node, ast.Name) and not node.id.startswith('_'):
            dependencies.add(node.id)
            return {'kind': 'field', 'name': node.id}
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == 'parent' and not node.attr.startswith('_'):
            name = 'parent.' + node.attr
            dependencies.add(name)
            return {'kind': 'field', 'name': name}
        if isinstance(node, (ast.List, ast.Tuple)):
            return {'kind': 'tuple' if isinstance(node, ast.Tuple) else 'sequence', 'items': [child(item) for item in node.elts]}
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            return {'kind': 'concat', 'items': [child(node.left), child(node.right)]}
        if isinstance(node, ast.BoolOp) and isinstance(node.op, (ast.And, ast.Or)):
            return {'kind': 'and' if isinstance(node.op, ast.And) else 'or', 'items': [child(item) for item in node.values]}
        raise ValueError('unsupported_expression')

    try:
        tree = visit(ast.parse(raw.strip(), mode='eval').body)
    except (SyntaxError, ValueError, RecursionError):
        return {'version': 1, 'raw': raw, 'kind': 'unsupported'}
    return {'version': 1, 'raw': raw, 'dependencies': sorted(dependencies), 'tree': tree}
