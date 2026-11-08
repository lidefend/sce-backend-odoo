import { inject, type InjectionKey } from 'vue';
import type { SceneCompositionContext } from '../types';

export const scenePrimitiveContextKey = Symbol(
  'ScenePrimitiveContext',
) as InjectionKey<SceneCompositionContext>;

export class ScenePrimitiveProviderError extends Error {
  readonly code = 'SCENE_PRIMITIVE_PROVIDER_MISUSE';

  constructor() {
    super('useScenePrimitiveContext() must be called inside ScenePrimitiveProvider');
    this.name = 'ScenePrimitiveProviderError';
  }
}

export function useScenePrimitiveContext(): SceneCompositionContext {
  const context = inject(scenePrimitiveContextKey, null);
  if (!context) {
    throw new ScenePrimitiveProviderError();
  }
  return context;
}
