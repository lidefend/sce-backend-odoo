import { contractGapError } from './contract/contractGap';

const identity = (value: unknown): value is number => typeof value === 'number' && Number.isSafeInteger(value) && value > 0;

// Native Python evaluation values differ from display values and ORM commands.
export function nativeModifierRelationValue(value: unknown, type: string | undefined): unknown {
  if (type === 'many2one') {
    // An absent or empty relation is not a display value and carries no
    // identity; normalise it to the native false so an empty draft evaluates
    // exactly like Odoo's own empty many2one.
    if (value === false || value === undefined || value === '') return false;
    if (identity(value)) return value;
    if (Array.isArray(value) && value.length === 2 && identity(value[0]) && typeof value[1] === 'string') return value[0];
  } else if (type === 'one2many' || type === 'many2many') {
    if (value === undefined || value === '') return [];
    if (Array.isArray(value) && value.every(identity)) return value;
  } else return value;
  throw contractGapError({ kind: 'contract_defect', missing: 'native_modifier.relation_value',
    requiredDeclarationLayer: 'P0:smart_core:field_descriptor' }, '原生条件关系值缺少合法身份，不能使用显示值或关系命令代替');
}
