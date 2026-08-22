export type ContractFormExitPresentation = {
  label: '返回列表' | '取消';
  semanticIdentity: 'return-list' | 'cancel-edit';
};

/**
 * Container navigation is local presentation state, not a backend business
 * action. A managed relation iframe cancels through its scoped message
 * channel; an independent form keeps the normal history return behavior.
 */
export function resolveContractFormExitPresentation(
  managedRelationDialog: boolean,
): ContractFormExitPresentation {
  return managedRelationDialog
    ? { label: '取消', semanticIdentity: 'cancel-edit' }
    : { label: '返回列表', semanticIdentity: 'return-list' };
}
