import { contractGapError } from './contract/contractGap';
import { isPythonModifierValue } from './nativeModifierComparison';

function gap(): never {
  throw contractGapError({ kind: 'contract_defect', missing: 'native_modifier.context_operand',
    requiredDeclarationLayer: 'P0:smart_core:sourceContext.context' }, '原生条件缺少合法上下文或操作数声明');
}

function record(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
    && Object.getPrototypeOf(value) === Object.prototype;
}

export function bindNativeContext(values: Record<string, unknown>, source: unknown): Record<string, unknown> {
  const bound = { ...values };
  delete bound['$native.context'];
  if (record(source) && Object.prototype.hasOwnProperty.call(source, 'context') && record(source.context)) {
    bound['$native.context'] = { ...source.context };
  }
  return bound;
}

export function resolveNativeOperand(node: unknown, resolve: (field: string) => unknown): unknown {
  if (!record(node)) return gap();
  let value: unknown;
  if (node.kind === 'literal' && Object.prototype.hasOwnProperty.call(node, 'value')) value = node.value;
  else if (node.kind === 'field_value' && typeof node.field === 'string') value = resolve(node.field);
  else if (node.kind === 'context_get') {
    const context = resolve('$native.context');
    if (!record(context) || typeof node.key !== 'string' || !isPythonModifierValue(node.key)
      || !Object.prototype.hasOwnProperty.call(node, 'default') || !isPythonModifierValue(node.default)) return gap();
    value = Object.prototype.hasOwnProperty.call(context, node.key) ? context[node.key] : node.default;
  } else return gap();
  if (!isPythonModifierValue(value)) return gap();
  return value;
}
