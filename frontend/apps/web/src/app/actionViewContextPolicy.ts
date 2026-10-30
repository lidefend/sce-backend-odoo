/**
 * Parse an Odoo/Python dict literal from the action route ``context_raw`` and
 * decide whether a collection operation (create/edit/delete) is explicitly
 * allowed.  The frontend consumes the declared capability without ever
 * granting one the backend would deny: a present-but-unparseable context
 * fails closed so an explicit ``create:false`` can never be rendered as a
 * writable entry.
 */

function pythonSingleQuotedStringToJson(text: string): string {
  return text.replace(/'([^'\\]*(?:\\.[^'\\]*)*)'/g, (_match, inner: string) => {
    const value = inner
      .replace(/\\'/g, "'")
      .replace(/\\"/g, '"')
      .replace(/\\n/g, '\n')
      .replace(/\\t/g, '\t')
      .replace(/\\\\/g, '\\');
    return JSON.stringify(value);
  });
}

/**
 * The route ``context_raw`` carries an Odoo/Python dict literal
 * (``{'create': False}``), not JSON.  ``parseContractContextRaw`` is JSON-only
 * and therefore cannot consume it; this is the single Python/JSON parser for
 * the action route context and returns ``null`` (never a silent ``{}``) when a
 * non-empty literal is malformed.
 */
export function parseOdooDictLiteral(raw: unknown): Record<string, unknown> | null {
  const text = String(raw || '').trim();
  if (!text) return {};
  try {
    let json = text
      .replace(/\bNone\b/g, 'null')
      .replace(/\bTrue\b/g, 'true')
      .replace(/\bFalse\b/g, 'false');
    json = pythonSingleQuotedStringToJson(json);
    const parsed = JSON.parse(json);
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
      return parsed as Record<string, unknown>;
    }
    return null;
  } catch {
    return null;
  }
}

export function contextOperationAllowed(contextRaw: unknown, operation: string): boolean {
  const text = String(contextRaw || '').trim();
  if (!text) return true;
  const context = parseOdooDictLiteral(text);
  if (context === null) return false;
  if (!(operation in context)) return true;
  const value = context[operation];
  return !(value === false || value === 0 || value === '0' || value === 'false' || value === 'False');
}
