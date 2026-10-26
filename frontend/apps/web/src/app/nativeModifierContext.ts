import { nativeModifierRelationValue } from './nativeModifierRelationValue';
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
  else if (node.kind === 'field_value' && typeof node.field === 'string' && node.field.trim()) value = resolve(node.field);
  else if (node.kind === 'context_get') {
    const context = resolve('$native.context');
    if (!record(context) || typeof node.key !== 'string' || !isPythonModifierValue(node.key)
      || !Object.prototype.hasOwnProperty.call(node, 'default') || !isPythonModifierValue(node.default)) return gap();
    value = Object.prototype.hasOwnProperty.call(context, node.key) ? context[node.key] : node.default;
  } else return gap();
  if (!isPythonModifierValue(value)) return gap();
  return value;
}

// The parent map is already bound by the contract store; row data cannot supply context.
export function bindNativeRowParentContext(parent: Record<string, unknown>, fieldContext: unknown): Record<string, unknown> {
  if (fieldContext === undefined || fieldContext === null) return parent;
  if (!record(fieldContext)) return gap();
  const context = parent['$native.context'];
  if (!record(context)) return gap();
  return { ...parent, '$native.context': { ...context, ...fieldContext } };
}

export function bindNativeFieldTypes(values: Record<string, unknown>, types: unknown): Record<string, unknown> {
  const bound = { ...values };
  delete bound['$native.fieldTypes'];
  if (record(types)) bound['$native.fieldTypes'] = { ...types };
  return bound;
}

export function resolveTypedNativeField(resolve: (field: string) => unknown, field: string): unknown {
  const value = resolve(field);
  if (field === '$native.context' || field === '$native.fieldTypes') return value;
  const types = resolve('$native.fieldTypes');
  const type = record(types) && Object.prototype.hasOwnProperty.call(types, field) ? types[field] : undefined;
  if (type !== undefined && typeof type !== 'string') return gap();
  return nativeModifierRelationValue(value, type as string | undefined);
}
