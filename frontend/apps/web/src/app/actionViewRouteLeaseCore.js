export function shouldCaptureActionViewRouteLease(instanceActivityRouteKey, currentActivityRouteKey) {
  const instanceKey = String(instanceActivityRouteKey || '').trim();
  const currentKey = String(currentActivityRouteKey || '').trim();
  return Boolean(instanceKey && currentKey && instanceKey === currentKey);
}

export function isActionViewLoadLeaseCurrent(input = {}) {
  return (
    Number(input.loadGeneration || 0) > 0
    && Number(input.loadGeneration) === Number(input.latestLoadGeneration || 0)
    && input.isComponentActive === true
    && shouldCaptureActionViewRouteLease(input.instanceActivityRouteKey, input.currentActivityRouteKey)
  );
}
