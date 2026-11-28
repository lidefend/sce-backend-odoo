import type { ProductMyWorkFact } from '../../api/myWork';
import {
  formatMonetaryDisplayValue,
  normalizeDeclaredDigits,
} from './businessValuePresentation';
import { contractGapError } from '../contract/contractGap';
import { FIELD_VALUE_EMPTY_TEXT, formatTemporalFieldValue } from '../../utils/fieldSemantics';

export type ProductMyWorkFactPresentation = {
  key: string;
  fact: ProductMyWorkFact;
  display: string;
};

function normalizedDigits(value: unknown) {
  const digits = normalizeDeclaredDigits([20, Number(value)]);
  if (!digits) {
    throw contractGapError({
      kind: 'contract_defect',
      missing: 'product_my_work.fact.money.digits',
      requiredDeclarationLayer: 'P0:smart_core:money_fact_digits_projection',
    }, '我的工作金额事实缺少契约声明精度 digits');
  }
  return digits;
}

export function formatProductMyWorkFact(fact: ProductMyWorkFact, timeZone = ''): string {
  if (fact.display_role === 'money') {
    const money = fact.money;
    if (money?.value == null || !Number.isFinite(Number(money.value))) return FIELD_VALUE_EMPTY_TEXT;
    const digits = normalizedDigits(money.digits);
    return formatMonetaryDisplayValue(
      Number(money.value),
      digits,
      money.currency || money.currency_symbol || '',
      'zh-CN',
      FIELD_VALUE_EMPTY_TEXT,
    );
  }
  if (fact.display_role === 'datetime') {
    return formatTemporalFieldValue(fact.value, 'datetime', 'compact', timeZone) || FIELD_VALUE_EMPTY_TEXT;
  }
  return String(fact.value ?? '').trim() || FIELD_VALUE_EMPTY_TEXT;
}

export function productMyWorkIdentityDisplay(
  label: string,
  amount?: ProductMyWorkFact,
  timeZone = '',
): string {
  const identity = String(label || '').trim();
  if (!identity || amount?.display_role !== 'money') return identity;
  const amountDisplay = formatProductMyWorkFact(amount, timeZone).trim();
  if (!amountDisplay || amountDisplay === FIELD_VALUE_EMPTY_TEXT) return identity;
  const segments = identity.split(/\s+\/\s+/);
  if (!segments.includes(amountDisplay)) return identity;
  return segments.filter((segment) => segment !== amountDisplay).join(' / ').trim() || identity;
}

export function productMyWorkTaskFacts(
  facts: ProductMyWorkFact[],
  hasAmountChip: boolean,
): ProductMyWorkFact[] {
  return hasAmountChip
    ? facts.filter((fact) => fact.display_role !== 'money')
    : facts;
}

export function partitionProductMyWorkFacts(
  facts: ProductMyWorkFact[],
  visibleLimit = 3,
  timeZone = '',
): { primary: ProductMyWorkFactPresentation[]; supplementary: ProductMyWorkFactPresentation[] } {
  const rows = facts.map((fact, index) => ({
    key: `${String(fact.key || 'fact')}:${index}`,
    fact,
    display: formatProductMyWorkFact(fact, timeZone),
    index,
  }));
  const businessRows = rows.filter((row) => row.fact.field_group !== 'audit');
  const amount = businessRows.find((row) => row.fact.display_role === 'money');
  const ordered = [amount, ...businessRows.filter((row) => row !== amount)].filter(
    (row): row is typeof rows[number] => Boolean(row),
  );
  const primaryIndexes = new Set(ordered.slice(0, Math.max(1, visibleLimit)).map((row) => row.index));
  return {
    primary: rows.filter((row) => primaryIndexes.has(row.index)),
    supplementary: rows.filter((row) => !primaryIndexes.has(row.index)),
  };
}
