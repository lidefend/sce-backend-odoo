export type NativeTextTone = 'neutral' | 'info' | 'success' | 'warning' | 'danger';

export type NativeTextPresentation = {
  kind: 'inline' | 'callout';
  tone: NativeTextTone;
  role?: 'alert';
};

type NativeTextPresentationNode = {
  class?: unknown;
  className?: unknown;
  attributes?: Record<string, unknown>;
};

function classTokens(node: NativeTextPresentationNode): Set<string> {
  const raw = [
    node.class,
    node.className,
    node.attributes?.class,
    node.attributes?.className,
  ].map((value) => String(value || '').trim()).filter(Boolean).join(' ');
  return new Set(raw.split(/\s+/).filter(Boolean));
}

function calloutTone(tokens: Set<string>): Exclude<NativeTextTone, 'neutral'> {
  if (tokens.has('alert-danger')) return 'danger';
  if (tokens.has('alert-warning')) return 'warning';
  if (tokens.has('alert-success')) return 'success';
  return 'info';
}

export function resolveNativeTextPresentation(node: NativeTextPresentationNode): NativeTextPresentation {
  const tokens = classTokens(node);
  const explicitAlert = tokens.has('alert') || String(node.attributes?.role || '').trim().toLowerCase() === 'alert';
  if (explicitAlert) {
    return { kind: 'callout', tone: calloutTone(tokens), role: 'alert' };
  }
  if (tokens.has('text-danger')) return { kind: 'inline', tone: 'danger' };
  if (tokens.has('text-warning')) return { kind: 'inline', tone: 'warning' };
  if (tokens.has('text-success')) return { kind: 'inline', tone: 'success' };
  return { kind: 'inline', tone: 'neutral' };
}
