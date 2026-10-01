/**
 * What page responsibility a surface renders, derived only from the effective
 * contract's declared page info.
 *
 * The contract declares what a page *is*: `pageInfo.viewType` with its
 * `pageInfo.layoutType` companion, enumerated in
 * `docs/architecture/unified_page_contract_v2/unified_page_contract_v2.schema.json`.
 * Which standard composition owns a surface follows from that declaration.  It
 * is never re-decided from a business model name, a field label, a button
 * caption, a route name, an action id, a menu id or a renderer preference, so a
 * renamed label, a new model or a new menu cannot change which composition
 * renders a page.
 *
 * Observe what the live contract actually declares for the surfaces this project
 * adopts, rather than an assumed vocabulary:
 *   - collection/tree pages: `viewType: 'list'`,  `layoutType: 'table'`
 *   - record forms:          `viewType: 'form'`,  `layoutType: 'form'`
 *   - analysis/kanban pages: `viewType: 'pivot' | 'kanban' | …`
 * `'tree'` is accepted alongside `'list'` because the backend's own request
 * normalization (`smart_core/handlers/ui_contract_v2_adapters.py`) uses `tree`
 * as the canonical token for a collection page.
 *
 * The declared view and the declared layout are two contract facts about the
 * same page.  When they disagree, this is a rule conflict between contract
 * declarations, not a choice for a page to settle, so the surface resolves to
 * `specialized` and reports the conflict instead of picking one of them.
 *
 * A page the contract does not classify as one of the adopted responsibilities
 * resolves to `specialized`.  That is the fail-closed answer: the caller keeps
 * the composition it had instead of guessing a standard one, and the surface
 * publishes that it was not adopted, so a contract-projection gap shows up as a
 * visible non-adoption rather than as a page that quietly looks standard.
 *
 * This is presentation scope only.  It decides which renderer frames an
 * already-authorized page; it never decides which records are readable, which
 * fields exist, which values may be written, or who may act.
 */

export type StandardPageType = 'query-list' | 'record-form' | 'record-detail' | 'specialized';

export type StandardPageTypeReason =
  | 'contract-collection-view'
  | 'contract-record-view'
  | 'contract-readonly-record-view'
  | 'contract-view-conflict'
  | 'contract-view-not-classified';

export type StandardPageTypeDecision = {
  pageType: StandardPageType;
  reason: StandardPageTypeReason;
};

/**
 * `pageInfo.viewType` values that declare a collection page.  Every entry is a
 * token the contract schema enumerates and the backend can declare for this
 * surface; the list is deliberately closed so an unknown token is never
 * upgraded into a standard collection by resemblance.
 */
export const STANDARD_COLLECTION_VIEW_TYPES: readonly string[] = Object.freeze(['list', 'tree']);

/** `pageInfo.layoutType` values that agree with a declared collection view. */
export const STANDARD_COLLECTION_LAYOUT_TYPES: readonly string[] = Object.freeze(['table', 'tree']);

/** The `pageInfo.viewType` token that declares a record page. */
export const STANDARD_RECORD_VIEW_TYPE = 'form';

/** The `pageInfo.layoutType` value that agrees with a declared record view. */
export const STANDARD_RECORD_LAYOUT_TYPE = 'form';

function normalizedToken(value: unknown): string {
  return String(value ?? '').trim().toLowerCase();
}

/** The page-info shape this policy reads from the normalized contract store. */
export type ContractPageInfoLike = {
  viewType?: unknown;
  layoutType?: unknown;
};

/**
 * The contract's declared page info, read from the normalized contract store.
 * A store that is not loaded has declared nothing, which is a real answer and
 * not a missing one: the caller gets `specialized`.
 */
export function readContractPageInfo(
  store: { snapshot?: { pageInfo?: unknown } } | null | undefined,
): ContractPageInfoLike {
  const raw = store?.snapshot?.pageInfo;
  return raw && typeof raw === 'object' ? (raw as ContractPageInfoLike) : {};
}

/**
 * Classify a page from its declared contract page info.
 *
 * `renderProfile` is the page's *effective* render profile (the contract's
 * `effectiveRenderProfile` merged with what the route requested), so an
 * authorization-driven downgrade to readonly makes the surface a record detail
 * even though the route asked for an editable form.
 */
export function resolveStandardPageType(input: {
  viewType?: unknown;
  layoutType?: unknown;
  renderProfile?: unknown;
}): StandardPageTypeDecision {
  const viewType = normalizedToken(input?.viewType);
  const layoutType = normalizedToken(input?.layoutType);

  if (STANDARD_COLLECTION_VIEW_TYPES.includes(viewType)) {
    if (layoutType && !STANDARD_COLLECTION_LAYOUT_TYPES.includes(layoutType)) {
      return { pageType: 'specialized', reason: 'contract-view-conflict' };
    }
    return { pageType: 'query-list', reason: 'contract-collection-view' };
  }

  if (viewType === STANDARD_RECORD_VIEW_TYPE) {
    if (layoutType && layoutType !== STANDARD_RECORD_LAYOUT_TYPE) {
      return { pageType: 'specialized', reason: 'contract-view-conflict' };
    }
    return normalizedToken(input?.renderProfile) === 'readonly'
      ? { pageType: 'record-detail', reason: 'contract-readonly-record-view' }
      : { pageType: 'record-form', reason: 'contract-record-view' };
  }

  return { pageType: 'specialized', reason: 'contract-view-not-classified' };
}

/**
 * The one place a page resolves its own responsibility: from its normalized
 * contract store and its effective render profile.
 */
export function resolveStandardPageTypeFromStore(
  store: { snapshot?: { pageInfo?: unknown } } | null | undefined,
  options: { renderProfile?: unknown } = {},
): StandardPageTypeDecision {
  const pageInfo = readContractPageInfo(store);
  return resolveStandardPageType({
    viewType: pageInfo.viewType,
    layoutType: pageInfo.layoutType,
    renderProfile: options.renderProfile,
  });
}
