// 平台级金额表达权威：唯一的金额格式、精度、币种、负数、零值和空值规则。
// ScMoney 只负责展示，任何列表/详情/表单/行业组件都必须通过本模块获得金额文本，
// 不得再定义自己的金额格式化规则。

export function resolveMonetaryScale(digits?: [number, number], currencyLabel = ''): number | undefined {
  if (digits) return digits[1];
  const currencyCode = /^[A-Z]{3}$/.test(currencyLabel) ? currencyLabel : '';
  if (!currencyCode) return undefined;
  try {
    return new Intl.NumberFormat('zh-CN', { style: 'currency', currency: currencyCode })
      .resolvedOptions().maximumFractionDigits;
  } catch {
    return undefined;
  }
}

export function monetaryInputStep(digits?: [number, number], currencyLabel = ''): string {
  const scale = resolveMonetaryScale(digits, currencyLabel);
  if (!Number.isInteger(scale)) return 'any';
  return scale === 0 ? '1' : `0.${'0'.repeat(Math.max(0, scale - 1))}1`;
}

export function formatMonetaryInputValue(
  value: unknown,
  digits?: [number, number],
  currencyLabel = '',
): string | number {
  if (value === null || value === undefined || value === '') return '';
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return String(value);
  const scale = resolveMonetaryScale(digits, currencyLabel);
  return Number.isInteger(scale) ? numeric.toFixed(scale) : value as string | number;
}

export function formatMonetaryDisplayValue(
  value: unknown,
  digits?: [number, number],
  currencyLabel = '',
  locale = 'zh-CN',
  emptyText = '-',
): string {
  if (value === null || value === undefined || value === false || value === '') return emptyText;
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return emptyText;
  const scale = resolveMonetaryScale(digits, currencyLabel);
  const options: Intl.NumberFormatOptions = Number.isInteger(scale)
    ? { minimumFractionDigits: scale, maximumFractionDigits: scale }
    : {};
  const currencyCode = /^[A-Z]{3}$/.test(currencyLabel) ? currencyLabel : '';
  if (currencyCode) {
    return new Intl.NumberFormat(locale, { ...options, style: 'currency', currency: currencyCode }).format(numeric);
  }
  const formatted = new Intl.NumberFormat(locale, options).format(numeric);
  return currencyLabel ? `${formatted} ${currencyLabel}` : formatted;
}
