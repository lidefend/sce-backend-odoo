import type { SceneUiDriverRuntime, SceneUiKitId } from './types';

export type SceneUiDriverLoader = (id: SceneUiKitId) => Promise<SceneUiDriverRuntime>;

const nativeRuntime: SceneUiDriverRuntime = {
  id: 'sc-native',
  componentModel: 'native',
  components: {},
};

const loaders: Record<SceneUiKitId, () => Promise<SceneUiDriverRuntime>> = {
  'sc-native': async () => nativeRuntime,
  'tdesign-modern': async () => (await import('./tdesign/register')).tdesignRuntime,
};

const cache = new Map<SceneUiKitId, Promise<SceneUiDriverRuntime>>([
  ['sc-native', Promise.resolve(nativeRuntime)],
]);

export const loadSceneUiDriver: SceneUiDriverLoader = (id) => {
  const cached = cache.get(id);
  if (cached) return cached;
  const pending = loaders[id]();
  cache.set(id, pending);
  return pending;
};
