/**
 * Form-body action placeholders (quick filters, workflow transitions, body
 * actions) are bypass carriers.  They are legitimate only while they do not
 * duplicate a proven carrier, and they must never be closed while they are
 * the only entry of an action.
 *
 * - Record-list query presets belong to the record list.  A form body whose
 *   structure is owned natively never hosts them, so they close on structure
 *   authority alone.
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
  headerActionKeys: readonly unknown[];
  workflowTransitionActionKeys: readonly unknown[];
  bodyActionKeys: readonly unknown[];
};

export type FormActionPlaceholderGateResult = {
  suppressSearchFilters: boolean;
  suppressWorkflowTransitions: boolean;
  suppressBodyActions: boolean;
  uncarriedActionKeys: string[];
};

function normalizedKeys(keys: readonly unknown[]): string[] {
  return keys.map((key) => String(key ?? '').trim()).filter(Boolean);
}

export function resolveFormActionPlaceholderGate(
  input: FormActionPlaceholderGateInput,
): FormActionPlaceholderGateResult {
  const nativeAuthority = String(input.nativeStructureAuthority || '').trim() === 'native_authority';
  const suppressSearchFilters = input.useNativeFormTree || nativeAuthority;
  if (input.useNativeFormTree) {
    // The native tree renders header, statusbar and body buttons itself, so
    // the placeholders duplicate a proven carrier.
    return {
      suppressSearchFilters,
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
    suppressSearchFilters,
    suppressWorkflowTransitions: suppressSearchFilters && workflowCarried,
    suppressBodyActions: suppressSearchFilters && bodyCarried,
    uncarriedActionKeys: uncarried,
  };
}
