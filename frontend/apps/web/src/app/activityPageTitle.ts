export interface BusinessActivityTitleInput {
  authorityName?: unknown;
  businessLabel?: unknown;
  actionTitle?: unknown;
  modelLabel?: unknown;
  menuTitle?: unknown;
  fallback?: unknown;
}

export interface ActivityPageTitlePublicationInput {
  routeName?: unknown;
  recordId?: unknown;
}

function titleText(value: unknown): string {
  return String(value || '').replace(/\s+/g, ' ').trim();
}

/**
 * Activity tabs identify a stable business activity. Page modes such as create
 * and edit belong to the page itself and must not be prefixed into this title.
 */
export function resolveBusinessActivityTitle(input: BusinessActivityTitleInput): string {
  return titleText(
    input.authorityName
    || input.businessLabel
    || input.actionTitle
    || input.modelLabel
    || input.menuTitle
    || input.fallback,
  );
}

export function shouldDeferActivityPageTitle(
  input: ActivityPageTitlePublicationInput,
): boolean {
  const routeName = titleText(input.routeName);
  return (routeName === 'record' || routeName === 'model-form')
    && titleText(input.recordId) === 'new';
}
