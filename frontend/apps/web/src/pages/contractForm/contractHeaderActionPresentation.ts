import type { ContractAction } from './types';

function isConfigurationAction(action: ContractAction) {
  return String(action.intent || '').trim().toLowerCase() === 'ui.local_mode';
}

export function resolvePrimaryBusinessActionState(params: {
  busy: boolean;
  canSave: boolean;
  configurationMode: boolean;
  hasChanges: boolean;
  hasRecord: boolean;
  intakeMode: boolean;
  primaryCreateAction: ContractAction | null;
  primarySubmitAction: ContractAction | null;
  quickSubmitDisabled: boolean;
}) {
  const show = !params.configurationMode
    && !params.intakeMode
    && (params.canSave || Boolean(params.hasRecord && params.primarySubmitAction));
  if (params.busy) return { show, disabled: true };
  if (params.primarySubmitAction) {
    return {
      show,
      disabled: !params.primarySubmitAction.enabled || (params.hasRecord && params.hasChanges),
    };
  }
  if (!params.canSave) return { show, disabled: true };
  if (params.primaryCreateAction) return { show, disabled: false };
  return { show, disabled: params.quickSubmitDisabled };
}

export function groupContractHeaderActions(params: {
  actions: ContractAction[];
  intakeMode: boolean;
  nativeTree: boolean;
  configurationMode: boolean;
  isSubmitAction: (action: ContractAction) => boolean;
}) {
  const visible = params.intakeMode
    ? []
    : params.actions
      .filter((action) => !params.nativeTree
        || action.sourceWidgetId === 'page.header'
        || (action.sourceWidgetId === 'page.root' && action.level === 'header'))
      .filter((action) => Boolean(action.mutation) || !params.isSubmitAction(action) || !action.enabled);
  const configuration = visible
    .filter((action) => isConfigurationAction(action))
    .map((action) => action.presentationTier === 'primary' || action.semantic === 'primary_action'
      ? { ...action, presentationTier: 'overflow', semantic: action.semantic === 'primary_action' ? 'secondary_action' : action.semantic }
      : action);
  const businessCandidates = params.configurationMode ? [] : visible.filter((action) => !isConfigurationAction(action));
  let primaryClaimed = false;
  const business = businessCandidates.map((action) => {
    if (action.presentationTier !== 'primary' && action.semantic !== 'primary_action') return action;
    if (!primaryClaimed) {
      primaryClaimed = true;
      return { ...action, presentationTier: 'primary', semantic: 'primary_action' };
    }
    return { ...action, presentationTier: 'overflow', semantic: action.semantic === 'primary_action' ? 'secondary_action' : action.semantic };
  });
  const primary = business.find((action) => action.presentationTier === 'primary');
  const direct = [...(primary ? [primary] : []), ...business.filter((action) => action.presentationTier === 'secondary' && action.key !== primary?.key).slice(0, 2)];
  const directKeys = new Set(direct.map((action) => action.key));
  return {
    direct,
    overflow: business.filter((action) => !directKeys.has(action.key)),
    configuration,
  };
}
