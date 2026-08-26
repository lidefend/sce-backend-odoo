export const SC_PRIMITIVE_KEYS = [
  'ScButton',
  'ScInput',
  'ScTextarea',
  'ScSelect',
  'ScDialog',
  'ScDrawer',
  'ScTabs',
  'ScTable',
  'ScBadge',
  'ScTooltip',
  'ScDropdown',
  'ScFormField',
  'ScLoading',
  'ScEmptyState',
  'ScErrorState',
] as const;

export type ScPrimitiveKey = (typeof SC_PRIMITIVE_KEYS)[number];
export type ScPrimitiveSize = 'small' | 'medium' | 'large';
export type ScPrimitiveStatus = 'default' | 'success' | 'warning' | 'error';

export interface ScPrimitiveStateProps {
  size?: ScPrimitiveSize;
  status?: ScPrimitiveStatus;
  disabled?: boolean;
  loading?: boolean;
}

export function semanticPrimitiveIdentity(component: ScPrimitiveKey): Record<string, string> {
  return {
    'data-semantic-component': component,
    'data-semantic-layer': 'primitive',
  };
}

export function normalizePrimitiveSize(size?: ScPrimitiveSize): ScPrimitiveSize {
  return size ?? 'medium';
}

export function normalizePrimitiveStatus(status?: ScPrimitiveStatus): ScPrimitiveStatus {
  return status ?? 'default';
}

export function resolvePrimitiveControlUpdate(input: {
  value: unknown;
  disabled?: boolean;
  readonly?: boolean;
  loading?: boolean;
}): string | null {
  if (input.disabled || input.readonly || input.loading) return null;
  return String(input.value ?? '');
}

export function tdesignTabsSize(size?: ScPrimitiveSize): 'medium' | 'large' {
  return normalizePrimitiveSize(size) === 'large' ? 'large' : 'medium';
}

export interface ScDropdownOptionInput {
  value: string | number;
  label: string;
  disabled?: boolean;
}

export function tdesignDropdownOptions(items: readonly ScDropdownOptionInput[]) {
  return items.map((item) => ({
    value: item.value,
    content: item.label,
    disabled: Boolean(item.disabled),
  }));
}
