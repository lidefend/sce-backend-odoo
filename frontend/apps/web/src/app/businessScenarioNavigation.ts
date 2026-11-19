import type { BusinessScenarioMaintenance } from './releaseOperatorActionContract';

export type BusinessScenarioMaintenanceTarget = {
  path: string;
  query: Record<string, string>;
};

export function buildBusinessScenarioMaintenanceTarget(
  entry: Pick<BusinessScenarioMaintenance, 'enabled' | 'action' | 'menu'>,
  returnPath: string,
): BusinessScenarioMaintenanceTarget | null {
  if (!entry.enabled || entry.action.id <= 0) return null;
  const actionId = String(entry.action.id);
  return {
    path: `/a/${actionId}`,
    query: {
      action_id: actionId,
      ...(entry.menu.id > 0 ? { menu_id: String(entry.menu.id) } : {}),
      return_url: returnPath,
      return_label: '返回发布控制台',
    },
  };
}
