/**
 * Form-body action placeholders (workflow transitions, body actions) are
 * bypass carriers.  They are legitimate only while they do not duplicate a
 * proven carrier, and they must never be closed while they are the only entry
 * of an action.
 *
 * Record-list query filters are a list-surface concept and are not gated here at
 * all: the record form does not consume the record-list search contract, so there
 * is no placeholder left to close (see the boundary rule in
 * `docs/ops/iterations/form_structure_consumption_stabilization_20260917.md`:
 * "查询筛选只存在于列表页").
 *
 * - Workflow transitions and body actions are action entries.  Structure
 *   authority alone cannot prove that those actions already have a carrier,
 *   so they close only when the carrier is provable: either the native tree
 *   renders the actions, or every one of them is already present in the
 *   rendered header action row (direct, overflow, configuration or the
 *   primary footer action).
 */

export type FormActionPlaceholderGateInput = {
  useNativeFormTree: boolean;
  nativeStructureAuthority: string;
  /**
   * The form body is composed by the official form composition (the pilot
   * surfaces listed in `standardFormComposition.ts`).
   */
  officialFormComposition?: boolean;
  headerActionKeys: readonly unknown[];
  workflowTransitionActionKeys: readonly unknown[];
  bodyActionKeys: readonly unknown[];
};

export type FormActionPlaceholderGateResult = {
  suppressWorkflowTransitions: boolean;
  suppressBodyActions: boolean;
  uncarriedActionKeys: string[];
};

/**
 * The kinds of form body this gate can be asked about.  `Record<Union, …>` fails
 * to compile unless every kind is classified, so a new body kind cannot silently
 * inherit the previous kind's answer.
 *
 * `ownsStructure`: only a body whose structure this project owns (the native form
 * tree, or a contract-declared native structure authority) may close an action
 * entry, and then only for an entry whose carrier is provable.  Composition
 * authority alone is not structure ownership, so it never closes an action entry.
 */
export type FormActionPlaceholderBodyKind =
  | 'native_form_tree'
  | 'native_authority'
  | 'official_composition'
  | 'unowned_body';

const FORM_BODY_KIND_RULES: Record<FormActionPlaceholderBodyKind, {
  ownsStructure: boolean;
}> = {
  native_form_tree: { ownsStructure: true },
  native_authority: { ownsStructure: true },
  official_composition: { ownsStructure: false },
  unowned_body: { ownsStructure: false },
};

export const FORM_ACTION_PLACEHOLDER_BODY_KINDS = (
  Object.keys(FORM_BODY_KIND_RULES) as FormActionPlaceholderBodyKind[]
);

export function classifyFormActionPlaceholderBody(input: {
  useNativeFormTree: boolean;
  nativeStructureAuthority: string;
  officialFormComposition?: boolean;
}): FormActionPlaceholderBodyKind {
  if (input.useNativeFormTree) return 'native_form_tree';
  if (String(input.nativeStructureAuthority || '').trim() === 'native_authority') return 'native_authority';
  if (input.officialFormComposition) return 'official_composition';
  return 'unowned_body';
}

/** Only a structurally owned body may close an action entry. */
export function formBodyOwnsStructure(kind: FormActionPlaceholderBodyKind): boolean {
  return FORM_BODY_KIND_RULES[kind].ownsStructure;
}

function normalizedKeys(keys: readonly unknown[]): string[] {
  return keys.map((key) => String(key ?? '').trim()).filter(Boolean);
}

export function resolveFormActionPlaceholderGate(
  input: FormActionPlaceholderGateInput,
): FormActionPlaceholderGateResult {
  const bodyKind = classifyFormActionPlaceholderBody(input);
  const kindRules = FORM_BODY_KIND_RULES[bodyKind];
  const structureOwned = kindRules.ownsStructure;
  if (input.useNativeFormTree) {
    // The native tree renders header, statusbar and body buttons itself, so
    // the placeholders duplicate a proven carrier.
    return {
      suppressWorkflowTransitions: true,
      suppressBodyActions: true,
      uncarriedActionKeys: [],
    };
  }
  const carriedKeys = new Set(normalizedKeys(input.headerActionKeys));
  const uncarried: string[] = [];
  let workflowCarried = true;
  let bodyCarried = true;
  normalizedKeys(input.workflowTransitionActionKeys).forEach((key) => {
    if (carriedKeys.has(key)) return;
    workflowCarried = false;
    uncarried.push(key);
  });
  normalizedKeys(input.bodyActionKeys).forEach((key) => {
    if (carriedKeys.has(key)) return;
    bodyCarried = false;
    uncarried.push(key);
  });
  return {
    suppressWorkflowTransitions: structureOwned && workflowCarried,
    suppressBodyActions: structureOwned && bodyCarried,
    uncarriedActionKeys: uncarried,
  };
}
