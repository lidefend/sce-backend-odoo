const ALLOWED_TAGS = new Set([
  'a', 'b', 'blockquote', 'br', 'code', 'em', 'i', 'li', 'ol', 'p', 'pre', 'strong', 'u', 'ul',
]);

const DROP_WITH_CONTENT_TAGS = new Set(['iframe', 'object', 'script', 'style', 'svg']);

function safeLinkTarget(raw: string): string {
  const value = String(raw || '').trim();
  if (!value) return '';
  if (value.startsWith('/') || value.startsWith('#')) return value;
  try {
    const parsed = new URL(value, window.location.origin);
    return ['http:', 'https:', 'mailto:'].includes(parsed.protocol) ? value : '';
  } catch {
    return '';
  }
}

/**
 * Render an Odoo Html field without allowing executable markup into the app shell.
 * Formatting is intentionally limited to the small content vocabulary used by
 * business descriptions; unknown containers are unwrapped and unsafe content is dropped.
 */
export function sanitizeReadonlyHtml(raw: unknown): string {
  if (typeof document === 'undefined') return '';
  const template = document.createElement('template');
  const source = String(raw ?? '');
  template.innerHTML = source;
  const decoded = template.content.textContent || '';
  if (!template.content.querySelector('*') && decoded !== source && /<\s*\/?\s*[a-z][^>]*>/i.test(decoded)) {
    template.innerHTML = decoded;
  }

  template.content.querySelectorAll('*').forEach((element) => {
    const tag = element.tagName.toLowerCase();
    if (DROP_WITH_CONTENT_TAGS.has(tag)) {
      element.remove();
      return;
    }
    if (!ALLOWED_TAGS.has(tag)) {
      element.replaceWith(...Array.from(element.childNodes));
      return;
    }

    const originalHref = tag === 'a' ? element.getAttribute('href') || '' : '';
    Array.from(element.attributes).forEach((attribute) => element.removeAttribute(attribute.name));
    if (tag === 'a') {
      const href = safeLinkTarget(originalHref);
      if (href) {
        element.setAttribute('href', href);
        element.setAttribute('rel', 'noopener noreferrer');
      }
    }
  });
  return template.innerHTML;
}
