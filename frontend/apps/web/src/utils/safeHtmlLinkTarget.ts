const ALLOWED_PROTOCOLS = new Set(['http:', 'https:', 'mailto:']);

export function safeHtmlLinkTarget(raw: unknown): string {
  const value = String(raw || '').trim();
  if (!value) return '';
  if (value.startsWith('/') || value.startsWith('#')) return value;

  try {
    const absolute = new URL(value);
    return ALLOWED_PROTOCOLS.has(absolute.protocol) ? value : '';
  } catch {
    // Relative links still require an application origin for resolution.
  }

  if (typeof window === 'undefined') return '';
  try {
    const relative = new URL(value, window.location.href);
    return ALLOWED_PROTOCOLS.has(relative.protocol) ? value : '';
  } catch {
    return '';
  }
}
