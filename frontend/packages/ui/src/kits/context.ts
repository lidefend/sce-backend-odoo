import type { ComputedRef, InjectionKey, ShallowRef } from 'vue';
import { inject } from 'vue';
import type { SceneUiDensity, SceneUiDriverRuntime, SceneUiKitId } from './types';

export interface SceneUiKitContext {
  kit: ComputedRef<SceneUiKitId>;
  requestedKit: ComputedRef<SceneUiKitId>;
  density: ComputedRef<SceneUiDensity>;
  runtime: ShallowRef<SceneUiDriverRuntime | null>;
  ready: ComputedRef<boolean>;
}

export const sceneUiKitKey: InjectionKey<SceneUiKitContext> = Symbol('scene-ui-kit');

export function useSceneUiKit(): SceneUiKitContext {
  const context = inject(sceneUiKitKey);
  if (!context) {
    throw new Error('Scene UI components must be rendered inside SceneUiProvider');
  }
  return context;
}

export function useOptionalSceneUiKit(): SceneUiKitContext | null {
  return inject(sceneUiKitKey, null);
}
