/**
 * Scene route ownership and scene-contract entry intent.
 *
 * The scene runtime is cached by `<KeepAlive>`, so its watchers keep firing for
 * every global route change and can outlive the route it was mounted for.
 * Ownership is therefore resolved before any scene resolution or entry-intent
 * dispatch happens.
 *
 * A route query `entry_intent` is shared with the business entry contract
 * (`handling`, `query`, `analysis`, `config`, `master_data`, `source_fact`) and
 * also carries the declared scene intent for row actions that open a scene.
 * Which one it is depends on the route that owns it, never on the value shape.
 */
const SCENE_ROUTE_NAME = 'scene';

export function ownsSceneRoute(routeName: unknown): boolean {
  return String(routeName ?? '').trim() === SCENE_ROUTE_NAME;
}

export function resolveSceneContractEntryIntent(options: {
  routeName: unknown;
  declaredTarget?: { intent?: unknown; entry_intent?: unknown } | null;
  queryEntryIntent: unknown;
  querySceneIntent: unknown;
}): string {
  if (!ownsSceneRoute(options.routeName)) return '';
  const queryIntent = String(options.queryEntryIntent || options.querySceneIntent || '').trim();
  if (queryIntent) return queryIntent;
  return String(options.declaredTarget?.entry_intent || options.declaredTarget?.intent || '').trim();
}

/** Present only diagnostics explicitly carried by the selected scene runtime. */
export function resolveSceneRuntimeDiagnostic(
  runtime: Record<string, unknown>,
  pageText: (key: string, fallback: string) => string,
): string {
  const count = (value: unknown): number => {
    if (typeof value !== 'number' && typeof value !== 'string') return 0;
    const parsed = Number(value);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : 0;
  };
  const missingRequiredCount = count(runtime.missing_required_count);
  const activeTransitionCount = count(runtime.active_transition_count);
  const bridgeAligned = typeof runtime.bridge_aligned === 'boolean'
    ? runtime.bridge_aligned : runtime.semantic_bridge_aligned;
  const parts: string[] = [];
  if (missingRequiredCount > 0) parts.push(`${pageText('runtime_diag_missing_required_prefix', '待补充事项')}：${missingRequiredCount}`);
  if (activeTransitionCount > 0) parts.push(`${pageText('runtime_diag_transition_prefix', '可办理步骤')}：${activeTransitionCount}`);
  if (bridgeAligned === false) parts.push(pageText('runtime_diag_alignment_mismatch', '当前场景语义尚未完全对齐。'));
  return parts.join('；');
}
