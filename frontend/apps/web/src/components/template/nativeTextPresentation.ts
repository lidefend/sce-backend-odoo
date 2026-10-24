import { contractGapError } from '../../app/contract/contractGap';
export type NativeTextTone = 'neutral' | 'info' | 'success' | 'warning' | 'danger';

export type NativeTextPresentation = {
  kind: 'inline' | 'callout';
  tone: NativeTextTone;
  role?: 'alert' | 'status';
};

type NativeTextPresentationNode = {
  class?: unknown;
  className?: unknown;
  containerId?: unknown;
  nativeLocator?: unknown;
  occurrenceIndex?: unknown;
  nodeComponent?: unknown;
  role?: unknown;
  styleToken?: unknown;
  text?: unknown;
  attributes?: Record<string, unknown>;
};

export const LEGACY_NATIVE_ALERT_TOKENS = [
  'alert',
  'alert-info',
  'alert-warning',
  'alert-danger',
  'alert-link',
] as const;

function declaredRole(node: NativeTextPresentationNode): string {
  return String(node.role || node.attributes?.role || '').trim().toLowerCase();
}

function nodeIdentity(node: NativeTextPresentationNode): string {
  const containerId = String(node.containerId || '').trim();
  if (containerId) return `container:${containerId}`;
  const locator = String(node.nativeLocator || '').trim();
  const occurrence = String(node.occurrenceIndex || '').trim();
  if (locator) return `native:${locator}${occurrence ? `#${occurrence}` : ''}`;
  return 'node:unidentified';
}

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

/**
 * A legacy alert class or role is not a feedback contract.  Vue form markup
 * must name the explicit node component (purpose, source, visibility owner and
 * condition) before it can render feedback or navigation.  This check is
 * intentionally independent of whether the node has text or is currently
 * visible: hidden and empty legacy hosts must also fail closed.
 */
export function assertNativePresentationConsumption(node: NativeTextPresentationNode): void {
  if (node.nodeComponent) return;
  const tokens = classTokens(node);
  const legacyToken = LEGACY_NATIVE_ALERT_TOKENS.find((token) => tokens.has(token));
  const role = declaredRole(node);
  if (!legacyToken && role !== 'alert') return;
  const identity = nodeIdentity(node);
  const declaration = legacyToken ? `token:${legacyToken}` : 'role:alert';
  throw contractGapError({
    kind: 'contract_defect',
    missing: `native_feedback_declaration.${identity}.${declaration}`,
    requiredDeclarationLayer: 'P0: explicit sc.feedback.message purpose/source/condition or sc.navigation.anchor target',
  }, `Legacy Vue alert declaration ${declaration} at ${identity} has no explicit feedback consumer`);
}

export function resolveNativeTextPresentation(node: NativeTextPresentationNode): NativeTextPresentation {
  assertNativePresentationConsumption(node);
  const tokens = classTokens(node);
  if (declaredRole(node) === 'status') return { kind: 'inline', tone: 'neutral', role: 'status' };
  if (tokens.has('text-danger')) return { kind: 'inline', tone: 'danger' };
  if (tokens.has('text-warning')) return { kind: 'inline', tone: 'warning' };
  if (tokens.has('text-success')) return { kind: 'inline', tone: 'success' };
  return { kind: 'inline', tone: 'neutral' };
}
