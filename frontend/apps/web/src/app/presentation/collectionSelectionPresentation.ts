export type CollectionSelectionState = 'unchecked' | 'checked' | 'mixed';

export function resolveCollectionSelectionPresentation(input: {
  checked: boolean;
  indeterminate?: boolean;
  disabled?: boolean;
}) {
  const state: CollectionSelectionState = input.indeterminate ? 'mixed' : input.checked ? 'checked' : 'unchecked';
  return { state, interactive: input.disabled !== true } as const;
}
