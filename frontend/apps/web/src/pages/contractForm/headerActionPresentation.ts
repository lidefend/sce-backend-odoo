import type { ContractAction } from './types';

export function presentContractHeaderActions(input: {
  direct: ContractAction[];
  overflow: ContractAction[];
  excludedKeys: Set<string>;
}) {
  const direct = input.direct.filter((action) => !input.excludedKeys.has(action.key));
  const visible = direct.filter((action) => !action.destructive).slice(0, 1);
  const overflow = [
    ...direct.filter((action) => !visible.some((visibleAction) => visibleAction.key === action.key)),
    ...input.overflow.filter((action) => !input.excludedKeys.has(action.key)),
  ].filter((action, index, rows) => rows.findIndex((row) => row.key === action.key) === index);
  return { direct: visible, overflow };
}
