import type { BusinessScenarioMaintenance } from './releaseOperatorActionContract';

export type BusinessScenarioMaintenanceTarget = {
  path: string;
  query: Record<string, string>;
};

function returnPathForProduct(returnPath: string, productKey: string): string {
  const hashIndex = returnPath.indexOf('#');
  const hash = hashIndex >= 0 ? returnPath.slice(hashIndex) : '';
  const withoutHash = hashIndex >= 0 ? returnPath.slice(0, hashIndex) : returnPath;
  const queryIndex = withoutHash.indexOf('?');
  const path = queryIndex >= 0 ? withoutHash.slice(0, queryIndex) : withoutHash;
  const query = new URLSearchParams(queryIndex >= 0 ? withoutHash.slice(queryIndex + 1) : '');
  if (productKey) query.set('product_key', productKey);
  const search = query.toString();
  return `${path}${search ? `?${search}` : ''}${hash}`;
}

export function buildBusinessScenarioMaintenanceTarget(
  entry: Pick<
    BusinessScenarioMaintenance,
    'enabled' | 'action' | 'menu' | 'return_readback'
  >,
  returnPath: string,
): BusinessScenarioMaintenanceTarget | null {
  if (!entry.enabled || entry.action.id <= 0) return null;
  const actionId = String(entry.action.id);
  const returnProductKey = entry.return_readback.product_key;
  return {
    path: `/a/${actionId}`,
    query: {
      action_id: actionId,
      ...(entry.menu.id > 0 ? { menu_id: String(entry.menu.id) } : {}),
      return_url: returnPathForProduct(returnPath, returnProductKey),
      return_product_key: returnProductKey,
    },
  };
}
