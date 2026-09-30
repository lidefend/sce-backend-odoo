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

/** Scene entry intents declared by the scene contract itself. */
export const SCENE_CONTRACT_ENTRY_INTENTS: Record<string, string> = {
  'workspace.home': 'workspace.home.enter',
  'dashboard.company': 'dashboard.company.enter',
  'project.management': 'project.dashboard.enter',
};

export function ownsSceneRoute(routeName: unknown): boolean {
  return String(routeName ?? '').trim() === SCENE_ROUTE_NAME;
}

export function resolveSceneContractEntryIntent(options: {
  routeName: unknown;
  sceneKey: string;
  queryEntryIntent: unknown;
  querySceneIntent: unknown;
}): string {
  if (!ownsSceneRoute(options.routeName)) return '';
  const queryIntent = String(options.queryEntryIntent || options.querySceneIntent || '').trim();
  if (queryIntent) return queryIntent;
  return SCENE_CONTRACT_ENTRY_INTENTS[String(options.sceneKey || '').trim()] || '';
}
