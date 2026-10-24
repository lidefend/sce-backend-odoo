// P0 transport deadline, not a business SLA or a permission decision.
export const SCENE_HYDRATION_DEADLINE_MS = 30_000;

export async function awaitSceneHydration<T>(
  request: (signal: AbortSignal) => Promise<T>,
  parentSignal: AbortSignal,
  deadlineMs = SCENE_HYDRATION_DEADLINE_MS,
): Promise<T> {
  parentSignal.throwIfAborted();
  const controller = new AbortController();
  const signal = AbortSignal.any([parentSignal, controller.signal]);
  let timer: ReturnType<typeof setTimeout>;
  let onAbort: () => void;
  const interrupted = new Promise<never>((_resolve, reject) => {
    onAbort = () => reject(signal.reason);
    if (signal.aborted) onAbort();
    else signal.addEventListener('abort', onAbort, { once: true });
    timer = setTimeout(() => controller.abort(new DOMException('Scene request timed out', 'TimeoutError')), deadlineMs);
  });
  try {
    signal.throwIfAborted();
    return await Promise.race([request(signal), interrupted]);
  } finally {
    clearTimeout(timer!);
    signal.removeEventListener('abort', onAbort!);
  }
}
