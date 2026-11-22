import { productIdentityText } from './pageIdentity';

export interface BusinessActivityTitleInput {
  authorityName?: unknown;
  businessLabel?: unknown;
  sceneLabel?: unknown;
  actionTitle?: unknown;
  modelLabel?: unknown;
  menuTitle?: unknown;
  fallback?: unknown;
}

export interface ActivityPageTitlePublicationInput {
  routeName?: unknown;
  recordId?: unknown;
}

export interface SceneActivityTitleInput {
  sceneKey?: unknown;
  runtimeLabel?: unknown;
  registeredLabel?: unknown;
  queryLabel?: unknown;
}

function titleText(value: unknown): string {
  return String(value || '').replace(/\s+/g, ' ').trim();
}

/**
 * Activity tabs identify a stable business activity. Page modes such as create
 * and edit belong to the page itself and must not be prefixed into this title.
 */
export function resolveBusinessActivityTitle(input: BusinessActivityTitleInput): string {
  const candidates = [
    input.authorityName,
    input.businessLabel,
    input.sceneLabel,
    input.actionTitle,
    input.modelLabel,
    input.menuTitle,
    input.fallback,
  ];
  return candidates.map(productIdentityText).find(Boolean) || '';
}

export function shouldDeferActivityPageTitle(
  input: ActivityPageTitlePublicationInput,
): boolean {
  const routeName = titleText(input.routeName);
  return (routeName === 'record' || routeName === 'model-form')
    && titleText(input.recordId) === 'new';
}

/**
 * Resolve a scene tab/page title from declared scene labels. Runtime scene
 * projection wins over the static registry and the route-carried label; the
 * technical scene key is never rendered as a business title.
 */
export function resolveSceneActivityTitle(input: SceneActivityTitleInput): string {
  const sceneKey = titleText(input.sceneKey);
  const runtimeLabel = productIdentityText(input.runtimeLabel);
  const registeredLabel = productIdentityText(input.registeredLabel);
  const queryLabel = productIdentityText(input.queryLabel);
  return runtimeLabel || registeredLabel || (queryLabel !== sceneKey ? queryLabel : '') || '业务场景';
}

/**
 * SceneView owns one semantic heading. A visible handling-surface heading is
 * already the page h1, so the generic shell heading is omitted in that case.
 */
export function shouldRenderScenePageHeading(input: {
  hasSceneIdentity?: unknown;
  hasExplicitHeading?: unknown;
  hasEmbeddedContentHeading?: unknown;
}): boolean {
  return Boolean(titleText(input.hasSceneIdentity))
    && !input.hasExplicitHeading
    && !input.hasEmbeddedContentHeading;
}

export function shouldRenderSceneContractFallbackHeading(status: unknown): boolean {
  return status === 'loading' || status === 'error';
}
