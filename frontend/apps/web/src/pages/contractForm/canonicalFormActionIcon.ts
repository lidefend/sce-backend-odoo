const NATIVE_FONT_AWESOME_ICON = /^fa-[a-z0-9]+(?:-[a-z0-9]+)*$/;

/**
 * Resolve only the native Font Awesome token dialect shipped by Odoo.
 * Unknown icon dialects fail closed and leave the accessible text label intact.
 */
export function canonicalFormActionIconClass(icon: string): string {
  const token = String(icon || '').trim().toLowerCase();
  return NATIVE_FONT_AWESOME_ICON.test(token) ? `fa ${token}` : '';
}
