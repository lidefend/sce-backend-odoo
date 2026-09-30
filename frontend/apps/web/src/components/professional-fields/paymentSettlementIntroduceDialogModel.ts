import type { FormSectionFieldSchema } from '../template/formSection.types';

/**
 * The introduce-dialog contract for the settlement detail collection.
 *
 * Every term, every payload key and every action identity the dialog uses is
 * declared by the effective contract (``componentConfig`` produced by the
 * construction product layer). Nothing here is inferred from a model name, a
 * column header or a record value: when a required semantic is absent the
 * resolution reports a gap and the caller must fail closed instead of
 * substituting a guess.
 */
export type SettlementIntroducePayloadFields = Readonly<{
  record: string;
  source: string;
  sourceLines: string;
  applyMode: string;
  ratio: string;
  totalAmount: string;
  searchKeyword: string;
}>;

export type SettlementIntroduceColumnLabels = Readonly<{
  name: string;
  contract: string;
  settlementAmount: string;
  applied: string;
  remaining: string;
  state: string;
}>;

export type SettlementIntroduceActions = Readonly<{
  search: string;
  preview: string;
  introduce: string;
}>;

export type SettlementIntroduceContract = Readonly<{
  purpose: string;
  buttonLabel: string;
  title: string;
  description: string;
  searchPlaceholder: string;
  searchActionLabel: string;
  searchLoadingLabel: string;
  searchEmptyLabel: string;
  resultContractLabel: string;
  resultAmountLabel: string;
  resultLineCountLabel: string;
  resultLineCountSuffix: string;
  switchSourceLabel: string;
  selectAllLabel: string;
  summarySelectedPrefix: string;
  summaryLineCountSuffix: string;
  summarySettlementAmountLabel: string;
  summaryApplicableAmountLabel: string;
  columnLabels: SettlementIntroduceColumnLabels;
  stateAppliedLabel: string;
  stateApplicableLabel: string;
  allAppliedLabel: string;
  historyTitle: string;
  historyCountSuffix: string;
  historyExpandLabel: string;
  historyCollapseLabel: string;
  ratioModeLabel: string;
  amountModeLabel: string;
  ratioPlaceholder: string;
  totalPlaceholder: string;
  ratioHint: string;
  amountHint: string;
  applyTotalLabel: string;
  cancelLabel: string;
  confirmLabel: string;
  recordRequiredMessage: string;
  payloadFields: SettlementIntroducePayloadFields;
  actions: SettlementIntroduceActions;
}>;

export type SettlementIntroduceContractResolution =
  | { readonly ready: true; readonly contract: SettlementIntroduceContract }
  | { readonly ready: false; readonly missing: readonly string[] };

const DIALOG_CONFIG_KEY = 'introduceDialog';

/** Contract paths every dialog term is read from, expressed as flat paths. */
const REQUIRED_TERM_PATHS: readonly string[] = Object.freeze([
  `${DIALOG_CONFIG_KEY}.purpose`,
  `${DIALOG_CONFIG_KEY}.title`,
  `${DIALOG_CONFIG_KEY}.description`,
  `${DIALOG_CONFIG_KEY}.searchPlaceholder`,
  `${DIALOG_CONFIG_KEY}.searchActionLabel`,
  `${DIALOG_CONFIG_KEY}.searchLoadingLabel`,
  `${DIALOG_CONFIG_KEY}.searchEmptyLabel`,
  `${DIALOG_CONFIG_KEY}.resultContractLabel`,
  `${DIALOG_CONFIG_KEY}.resultAmountLabel`,
  `${DIALOG_CONFIG_KEY}.resultLineCountLabel`,
  `${DIALOG_CONFIG_KEY}.resultLineCountSuffix`,
  `${DIALOG_CONFIG_KEY}.switchSourceLabel`,
  `${DIALOG_CONFIG_KEY}.selectAllLabel`,
  `${DIALOG_CONFIG_KEY}.summarySelectedPrefix`,
  `${DIALOG_CONFIG_KEY}.summaryLineCountSuffix`,
  `${DIALOG_CONFIG_KEY}.summarySettlementAmountLabel`,
  `${DIALOG_CONFIG_KEY}.summaryApplicableAmountLabel`,
  `${DIALOG_CONFIG_KEY}.columnLabels.name`,
  `${DIALOG_CONFIG_KEY}.columnLabels.contract`,
  `${DIALOG_CONFIG_KEY}.columnLabels.settlementAmount`,
  `${DIALOG_CONFIG_KEY}.columnLabels.applied`,
  `${DIALOG_CONFIG_KEY}.columnLabels.remaining`,
  `${DIALOG_CONFIG_KEY}.columnLabels.state`,
  `${DIALOG_CONFIG_KEY}.stateAppliedLabel`,
  `${DIALOG_CONFIG_KEY}.stateApplicableLabel`,
  `${DIALOG_CONFIG_KEY}.allAppliedLabel`,
  `${DIALOG_CONFIG_KEY}.historyTitle`,
  `${DIALOG_CONFIG_KEY}.historyCountSuffix`,
  `${DIALOG_CONFIG_KEY}.historyExpandLabel`,
  `${DIALOG_CONFIG_KEY}.historyCollapseLabel`,
  `${DIALOG_CONFIG_KEY}.ratioModeLabel`,
  `${DIALOG_CONFIG_KEY}.amountModeLabel`,
  `${DIALOG_CONFIG_KEY}.ratioPlaceholder`,
  `${DIALOG_CONFIG_KEY}.totalPlaceholder`,
  `${DIALOG_CONFIG_KEY}.ratioHint`,
  `${DIALOG_CONFIG_KEY}.amountHint`,
  `${DIALOG_CONFIG_KEY}.applyTotalLabel`,
  `${DIALOG_CONFIG_KEY}.cancelLabel`,
  `${DIALOG_CONFIG_KEY}.confirmLabel`,
  `${DIALOG_CONFIG_KEY}.recordRequiredMessage`,
]);

/** Contract paths every request the dialog issues is keyed by. */
const REQUIRED_PAYLOAD_PATHS: readonly string[] = Object.freeze([
  `${DIALOG_CONFIG_KEY}.payloadFields.record`,
  `${DIALOG_CONFIG_KEY}.payloadFields.source`,
  `${DIALOG_CONFIG_KEY}.payloadFields.sourceLines`,
  `${DIALOG_CONFIG_KEY}.payloadFields.applyMode`,
  `${DIALOG_CONFIG_KEY}.payloadFields.ratio`,
  `${DIALOG_CONFIG_KEY}.payloadFields.totalAmount`,
  `${DIALOG_CONFIG_KEY}.payloadFields.searchKeyword`,
]);

/** Action identities remain the contract's decision, never a frontend guess. */
const REQUIRED_ACTION_PATHS: readonly string[] = Object.freeze([
  'actionRefs.search',
  'actionRefs.preview',
  'actionRefs.introduce',
]);

/** The collection entry label is declared next to the component, not here. */
const REQUIRED_ENTRY_PATHS: readonly string[] = Object.freeze(['introduceLabel']);

export const SETTLEMENT_INTRODUCE_REQUIRED_PATHS: readonly string[] = Object.freeze([
  ...REQUIRED_ENTRY_PATHS,
  ...REQUIRED_TERM_PATHS,
  ...REQUIRED_PAYLOAD_PATHS,
  ...REQUIRED_ACTION_PATHS,
]);

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function readPath(source: Record<string, unknown>, path: string): string {
  let cursor: unknown = source;
  for (const segment of path.split('.')) {
    cursor = asRecord(cursor)[segment];
  }
  return typeof cursor === 'string' || typeof cursor === 'number' ? String(cursor).trim() : '';
}

/**
 * Resolve the dialog contract from the effective field schema.
 *
 * A missing or blank value is reported as a gap so the caller can surface it,
 * keep the record intact and refuse the affected action. The resolver never
 * substitutes a default: an absent business term must not look like a working
 * dialog.
 */
export function resolveSettlementIntroduceContract(
  field: Pick<FormSectionFieldSchema, 'componentConfig'>,
): SettlementIntroduceContractResolution {
  const config = asRecord(field.componentConfig);
  const missing = SETTLEMENT_INTRODUCE_REQUIRED_PATHS.filter(
    (path) => !readPath(config, path),
  );
  if (missing.length) return Object.freeze({ ready: false as const, missing: Object.freeze(missing) });
  const dialog = asRecord(config[DIALOG_CONFIG_KEY]);
  const payloadFields = asRecord(dialog.payloadFields);
  const columnLabels = asRecord(dialog.columnLabels);
  const actions = asRecord(config.actionRefs);
  return Object.freeze({
    ready: true as const,
    contract: Object.freeze({
      purpose: readPath(config, `${DIALOG_CONFIG_KEY}.purpose`),
      buttonLabel: readPath(config, 'introduceLabel'),
      title: readPath(config, `${DIALOG_CONFIG_KEY}.title`),
      description: readPath(config, `${DIALOG_CONFIG_KEY}.description`),
      searchPlaceholder: readPath(config, `${DIALOG_CONFIG_KEY}.searchPlaceholder`),
      searchActionLabel: readPath(config, `${DIALOG_CONFIG_KEY}.searchActionLabel`),
      searchLoadingLabel: readPath(config, `${DIALOG_CONFIG_KEY}.searchLoadingLabel`),
      searchEmptyLabel: readPath(config, `${DIALOG_CONFIG_KEY}.searchEmptyLabel`),
      resultContractLabel: readPath(config, `${DIALOG_CONFIG_KEY}.resultContractLabel`),
      resultAmountLabel: readPath(config, `${DIALOG_CONFIG_KEY}.resultAmountLabel`),
      resultLineCountLabel: readPath(config, `${DIALOG_CONFIG_KEY}.resultLineCountLabel`),
      resultLineCountSuffix: readPath(config, `${DIALOG_CONFIG_KEY}.resultLineCountSuffix`),
      switchSourceLabel: readPath(config, `${DIALOG_CONFIG_KEY}.switchSourceLabel`),
      selectAllLabel: readPath(config, `${DIALOG_CONFIG_KEY}.selectAllLabel`),
      summarySelectedPrefix: readPath(config, `${DIALOG_CONFIG_KEY}.summarySelectedPrefix`),
      summaryLineCountSuffix: readPath(config, `${DIALOG_CONFIG_KEY}.summaryLineCountSuffix`),
      summarySettlementAmountLabel: readPath(config, `${DIALOG_CONFIG_KEY}.summarySettlementAmountLabel`),
      summaryApplicableAmountLabel: readPath(config, `${DIALOG_CONFIG_KEY}.summaryApplicableAmountLabel`),
      columnLabels: Object.freeze({
        name: readPath(columnLabels, 'name'),
        contract: readPath(columnLabels, 'contract'),
        settlementAmount: readPath(columnLabels, 'settlementAmount'),
        applied: readPath(columnLabels, 'applied'),
        remaining: readPath(columnLabels, 'remaining'),
        state: readPath(columnLabels, 'state'),
      }),
      stateAppliedLabel: readPath(config, `${DIALOG_CONFIG_KEY}.stateAppliedLabel`),
      stateApplicableLabel: readPath(config, `${DIALOG_CONFIG_KEY}.stateApplicableLabel`),
      allAppliedLabel: readPath(config, `${DIALOG_CONFIG_KEY}.allAppliedLabel`),
      historyTitle: readPath(config, `${DIALOG_CONFIG_KEY}.historyTitle`),
      historyCountSuffix: readPath(config, `${DIALOG_CONFIG_KEY}.historyCountSuffix`),
      historyExpandLabel: readPath(config, `${DIALOG_CONFIG_KEY}.historyExpandLabel`),
      historyCollapseLabel: readPath(config, `${DIALOG_CONFIG_KEY}.historyCollapseLabel`),
      ratioModeLabel: readPath(config, `${DIALOG_CONFIG_KEY}.ratioModeLabel`),
      amountModeLabel: readPath(config, `${DIALOG_CONFIG_KEY}.amountModeLabel`),
      ratioPlaceholder: readPath(config, `${DIALOG_CONFIG_KEY}.ratioPlaceholder`),
      totalPlaceholder: readPath(config, `${DIALOG_CONFIG_KEY}.totalPlaceholder`),
      ratioHint: readPath(config, `${DIALOG_CONFIG_KEY}.ratioHint`),
      amountHint: readPath(config, `${DIALOG_CONFIG_KEY}.amountHint`),
      applyTotalLabel: readPath(config, `${DIALOG_CONFIG_KEY}.applyTotalLabel`),
      cancelLabel: readPath(config, `${DIALOG_CONFIG_KEY}.cancelLabel`),
      confirmLabel: readPath(config, `${DIALOG_CONFIG_KEY}.confirmLabel`),
      recordRequiredMessage: readPath(config, `${DIALOG_CONFIG_KEY}.recordRequiredMessage`),
      payloadFields: Object.freeze({
        record: readPath(payloadFields, 'record'),
        source: readPath(payloadFields, 'source'),
        sourceLines: readPath(payloadFields, 'sourceLines'),
        applyMode: readPath(payloadFields, 'applyMode'),
        ratio: readPath(payloadFields, 'ratio'),
        totalAmount: readPath(payloadFields, 'totalAmount'),
        searchKeyword: readPath(payloadFields, 'searchKeyword'),
      }),
      actions: Object.freeze({
        search: readPath(actions, 'search'),
        preview: readPath(actions, 'preview'),
        introduce: readPath(actions, 'introduce'),
      }),
    }),
  });
}

export const COMPONENT_CONTRACT_SEMANTIC_MISSING = 'COMPONENT_CONTRACT_SEMANTIC_MISSING';

/** Diagnostic shown when the contract gap blocks the collection action. */
export function settlementIntroduceContractGapLabel(missing: readonly string[]): string {
  return `契约缺少必要语义，无法引入明细：${missing.join(', ')}`;
}

/** Fail-closed accessor for callers that cannot continue without the contract. */
export function requireSettlementIntroduceContract(
  field: Pick<FormSectionFieldSchema, 'componentConfig'>,
): SettlementIntroduceContract {
  const resolved = resolveSettlementIntroduceContract(field);
  if ('missing' in resolved) {
    throw new Error(`${COMPONENT_CONTRACT_SEMANTIC_MISSING}:${resolved.missing.join(',')}`);
  }
  return resolved.contract;
}
