import type { ContractAction } from './types';

function isConfigurationAction(action: ContractAction) {
  const label = String(action.label || '').trim();
  const key = String(action.key || '').trim().toLowerCase();
  const source = String(action.sourceWidgetId || '').trim().toLowerCase();
  return label.includes('设置') || key.includes('setting') || key.includes('config') || source.includes('setting') || source.includes('config');
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
      .filter((action) => Boolean(action.mutation) || !params.isSubmitAction(action));
  const configuration = visible
    .filter((action) => isConfigurationAction(action) && action.enabled)
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
