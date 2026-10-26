import { contractGapError } from '../../app/contract/contractGap';

type Node = Record<string, unknown>;
function gap(): never {
  throw contractGapError({ kind: 'contract_defect', missing: 'relation.domain_expression',
    requiredDeclarationLayer: 'P0:smart_core:native_relation_domain' }, '关系筛选声明不可求值，无法加载可选内容');
}
function record(value: unknown): Node {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return gap();
  return value as Node;
}
function truth(value: unknown): boolean {
  return Array.isArray(value) ? value.length > 0 : Boolean(value);
}
export function relationDomainExpression(expression: unknown, raw: unknown) {
  const envelope = record(expression);
  if (envelope.version !== 1 || envelope.raw !== raw || envelope.kind !== undefined) return gap();
  const dependencies = new Set<string>();
  let count = 0;
  function validate(value: unknown, depth = 0): void {
    if (++count > 512 || depth > 32) return gap();
    const node = record(value);
    if (node.kind === 'literal') {
      if (Object.keys(node).some(key => !['kind', 'value'].includes(key))) return gap();
      const literal = node.value;
      if (literal === null || typeof literal === 'string' || typeof literal === 'boolean'
        || (typeof literal === 'number' && Number.isFinite(literal) && Math.abs(literal) <= Number.MAX_SAFE_INTEGER)) return;
      return gap();
    }
    if (node.kind === 'field') {
      if (Object.keys(node).some(key => !['kind', 'name'].includes(key)) || typeof node.name !== 'string'
        || !/^(?:parent\.)?[A-Za-z][A-Za-z0-9_]*$/.test(node.name)) return gap();
      dependencies.add(node.name); return;
    }
    if (!['sequence', 'tuple', 'concat', 'and', 'or'].includes(String(node.kind)) || !Array.isArray(node.items)
      || Object.keys(node).some(key => !['kind', 'items'].includes(key))
      || (node.kind === 'concat' && node.items.length !== 2)
      || (['and', 'or'].includes(String(node.kind)) && node.items.length < 2)) return gap();
    node.items.forEach(item => validate(item, depth + 1));
  }
  validate(envelope.tree);
  const names = [...dependencies].sort();
  if (JSON.stringify(envelope.dependencies) !== JSON.stringify(names)) return gap();
  return { tree: envelope.tree, dependencies: names };
}
export function evaluateRelationDomainExpression(expression: unknown, raw: unknown, resolve: (field: string) => unknown): unknown[] {
  const { tree } = relationDomainExpression(expression, raw);
  const tuples = new WeakSet<unknown[]>();
  let inputCount = 0;
  function checkInput(value: unknown, depth = 0): void {
    if (++inputCount > 512 || depth > 32) return gap();
    if (value === null || typeof value === 'string' || typeof value === 'boolean') return;
    if (typeof value === 'number' && Number.isFinite(value) && Math.abs(value) <= Number.MAX_SAFE_INTEGER) return;
    if (Array.isArray(value)) { value.forEach(item => checkInput(item, depth + 1)); return; }
    return gap();
  }
  function evaluate(value: unknown): unknown {
    const node = value as Node;
    if (node.kind === 'literal') return node.value;
    if (node.kind === 'field') {
      const value = resolve(node.name as string);
      checkInput(value);
      return value;
    }
    const items = node.items as unknown[];
    if (node.kind === 'sequence' || node.kind === 'tuple') {
      const result = items.map(evaluate);
      if (node.kind === 'tuple') tuples.add(result);
      return result;
    }
    if (node.kind === 'concat') {
      const left = evaluate(items[0]); const right = evaluate(items[1]);
      if (!Array.isArray(left) || !Array.isArray(right)) return gap();
      if (tuples.has(left) !== tuples.has(right)) return gap();
      const result = [...left, ...right];
      if (tuples.has(left)) tuples.add(result);
      return result;
    }
    let result: unknown;
    for (const item of items) {
      result = evaluate(item);
      if (node.kind === 'and' ? !truth(result) : truth(result)) break;
    }
    return result;
  }
  const domain = evaluate(tree);
  if (!Array.isArray(domain) || tuples.has(domain) || domain.length > 512) return gap();
  // Validate prefix arity while preserving implicit conjunction and token order.
  const tokens: unknown[] = domain;
  let index = 0;
  function term(depth = 0): void {
    if (depth > 32 || index >= tokens.length) return gap();
    const token = tokens[index++];
    if (token === '!' || token === '&' || token === '|') {
      term(depth + 1); if (token !== '!') term(depth + 1); return;
    }
    if (!Array.isArray(token) || token.length !== 3 || typeof token[0] !== 'string'
      || !token[0] || typeof token[1] !== 'string' || !token[1]) return gap();
  }
  while (index < domain.length) term();
  return domain;
}
