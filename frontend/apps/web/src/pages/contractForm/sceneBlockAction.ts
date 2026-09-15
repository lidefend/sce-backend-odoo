import type { Router } from 'vue-router';

/** Forward a scene target without changing statusbar, route, and scene precedence. */
export function dispatchSceneBlockAction(
  payload: { action?: { target?: Record<string, unknown> } },
  { router, setStatusbarValue }: { router: Pick<Router, 'push'>; setStatusbarValue: (value: string) => void },
) {
  const target =
    payload?.action?.target && typeof payload.action.target === 'object'
      ? payload.action.target
      : {};
  const targetKind = String(target.kind || '').trim();
  if (targetKind === 'statusbar_value') {
    const value = String(target.value || '').trim();
    if (value) {
      setStatusbarValue(value);
      return;
    }
  }
  const route = String(target.route || '').trim();
  if (route) {
    void router.push(route);
    return;
  }
  const sceneKey = String(target.scene_key || '').trim();
  if (sceneKey) {
    void router.push({ name: 'scene', params: { sceneKey } });
  }
}
