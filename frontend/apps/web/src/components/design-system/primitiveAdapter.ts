export const SC_PRIMITIVE_KEYS = [
  'ScButton',
  'ScCheckbox',
  'ScRadioGroup',
  'ScRadio',
  'ScInput',
  'ScInlineState',
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
export type ScButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';

export interface TDesignButtonPresentation {
  theme: 'default' | 'primary' | 'danger' | 'warning' | 'success';
  variant: 'base' | 'outline' | 'text';
}

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

export function tdesignButtonPresentation(
  variant: ScButtonVariant,
  status: ScPrimitiveStatus = 'default',
): TDesignButtonPresentation {
  if (status === 'success') return { theme: 'success', variant: variant === 'ghost' ? 'text' : 'base' };
  if (status === 'warning') return { theme: 'warning', variant: variant === 'ghost' ? 'text' : 'base' };
  if (status === 'error') return { theme: 'danger', variant: variant === 'ghost' ? 'text' : 'base' };
  if (variant === 'primary') return { theme: 'primary', variant: 'base' };
  if (variant === 'danger') return { theme: 'danger', variant: 'base' };
  if (variant === 'ghost') return { theme: 'default', variant: 'text' };
  return { theme: 'default', variant: 'outline' };
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
