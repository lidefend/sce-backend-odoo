import { isPlainRecord } from './readonlyBlockRequest';

export type SceneRuntimeFetchRequest = {
  intent: string;
  params: Record<string, unknown>;
  context?: Record<string, unknown>;
};

/** Deferred scene requests are declared by the backend, including nested parameters. */
export function resolveSceneRuntimeFetchRequest(hint: unknown): SceneRuntimeFetchRequest | null {
  if (!isPlainRecord(hint) || typeof hint.intent !== 'string' || !hint.intent.trim() || !isPlainRecord(hint.params)) return null;
  if (hint.context !== undefined && !isPlainRecord(hint.context)) return null;
  return {
    intent: hint.intent.trim(),
    params: { ...hint.params },
    ...(isPlainRecord(hint.context) ? { context: { ...hint.context } } : {}),
  };
}
