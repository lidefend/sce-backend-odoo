import { contractGapError } from './contract/contractGap';

function identity(value: unknown): value is number {
  return typeof value === 'number' && Number.isSafeInteger(value) && value > 0;
}

// Native Python evaluation values differ from display values and ORM commands.
export function nativeModifierRelationValue(value: unknown, type: string | undefined): unknown {
  if (type === 'many2one') {
    // Explicit empty values have no identity. Missing dependencies remain unknown.
    if (value === false || value === '') return false;
    if (identity(value)) return value;
    if (Array.isArray(value) && value.length === 2 && identity(value[0]) && typeof value[1] === 'string') return value[0];
  } else if (type === 'one2many' || type === 'many2many') {
    if (value === '') return [];
    if (Array.isArray(value) && value.every(identity)) return value;
  } else return value;
  throw contractGapError({ kind: 'contract_defect', missing: 'native_modifier.relation_value',
    requiredDeclarationLayer: 'P0:smart_core:field_descriptor' }, '原生条件关系值缺少合法身份，不能使用显示值或关系命令代替');
}
