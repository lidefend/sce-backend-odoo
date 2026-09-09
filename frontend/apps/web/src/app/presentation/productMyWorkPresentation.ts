import type { ProductMyWorkFact } from '../../api/myWork';
import { formatMonetaryDisplayValue } from '../../components/template/formSection.mapper';

export type ProductMyWorkFactPresentation = {
  key: string;
  fact: ProductMyWorkFact;
  display: string;
};

function normalizedDigits(value: unknown) {
  const digits = Number(value);
  return Number.isFinite(digits) ? Math.min(20, Math.max(0, Math.trunc(digits))) : 2;
}

export function formatProductMyWorkFact(fact: ProductMyWorkFact): string {
  if (fact.display_role === 'money') {
    const money = fact.money;
    if (money?.value == null || !Number.isFinite(Number(money.value))) return '未填写';
    const digits = normalizedDigits(money.digits);
    return formatMonetaryDisplayValue(Number(money.value), [20, digits], money.currency || money.currency_symbol || '');
  }
  if (fact.display_role === 'datetime') {
    return fact.value ? String(fact.value).replace('T', ' ').slice(0, 16) : '未知';
  }
  return fact.value || '未填写';
}

export function partitionProductMyWorkFacts(
  facts: ProductMyWorkFact[],
  visibleLimit = 3,
): { primary: ProductMyWorkFactPresentation[]; supplementary: ProductMyWorkFactPresentation[] } {
  const rows = facts.map((fact, index) => ({
    key: `${String(fact.key || 'fact')}:${index}`,
    fact,
    display: formatProductMyWorkFact(fact),
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
