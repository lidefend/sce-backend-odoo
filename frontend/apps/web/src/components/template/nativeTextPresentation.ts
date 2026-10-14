import { contractGapError } from '../../app/contract/contractGap';
export type NativeTextTone = 'neutral' | 'info' | 'success' | 'warning' | 'danger';

export type NativeTextPresentation = {
  kind: 'inline' | 'callout';
  tone: NativeTextTone;
  role?: 'alert';
};

type NativeTextPresentationNode = {
  class?: unknown;
  className?: unknown;
  styleToken?: unknown;
  attributes?: Record<string, unknown>;
};

/**
 * Presentation tokens declared by the contract for this node.
 *
 * `styleToken` is the declared presentation facet published by the projection
 * (the bridge mirrors it on `attributes.contractStyleToken`).  The renderer maps
 * declared tokens to a presentation; it never invents one from native markup.
 */
function classTokens(node: NativeTextPresentationNode): Set<string> {
  const raw = [
    node.class,
    node.className,
    node.styleToken,
    node.attributes?.class,
    node.attributes?.className,
    node.attributes?.contractStyleToken,
  ].map((value) => String(value || '').trim()).filter(Boolean).join(' ');
  return new Set(raw.split(/\s+/).filter(Boolean));
}

export function resolveNativeTextPresentation(node: NativeTextPresentationNode): NativeTextPresentation {
  const tokens = classTokens(node);
  const explicitAlert = tokens.has('alert') || String(node.attributes?.role || '').trim().toLowerCase() === 'alert';
  if (explicitAlert) {
    throw contractGapError({ kind: 'contract_defect', missing: 'native feedback interaction declaration',
      requiredDeclarationLayer: 'P1: native field help or action/result feedback metadata' },
      'Native alert markup cannot declare permanent form guidance');
  }
  if (tokens.has('text-danger')) return { kind: 'inline', tone: 'danger' };
  if (tokens.has('text-warning')) return { kind: 'inline', tone: 'warning' };
  if (tokens.has('text-success')) return { kind: 'inline', tone: 'success' };
  return { kind: 'inline', tone: 'neutral' };
}
