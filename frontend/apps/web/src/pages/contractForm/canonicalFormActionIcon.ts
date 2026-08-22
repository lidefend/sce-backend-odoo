const CANONICAL_ACTION_ICON_NAMES = {
  'fa-check': 'check',
} as const;

/**
 * Resolve only the native Font Awesome token dialect shipped by Odoo.
 * Unknown icon dialects fail closed and leave the accessible text label intact.
 */
export function canonicalFormActionIconClass(icon: string): '' | 'check' {
  const token = String(icon || '').trim().toLowerCase();
  return CANONICAL_ACTION_ICON_NAMES[token as keyof typeof CANONICAL_ACTION_ICON_NAMES] || '';
}
