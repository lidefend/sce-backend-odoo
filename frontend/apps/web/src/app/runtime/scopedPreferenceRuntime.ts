/** Component-local transport coordination. Keys are supplied by the consumer;
 * this mechanism does not decide permissions or interpret preference values. */
export function createScopedPreferenceRuntime<Scope, Value>(options: {
  load: (scope: Scope) => Promise<Value>;
  waitForWrites?: () => Promise<unknown>;
  apply: (value: Value) => void;
  clear: () => void;
  onError: (error: unknown) => void;
}) {
  let identity = '';
  let scope: Scope;
  let generation = 0;
  let sequence = 0;
  let contractKey: string | null = null;
  let hasSeenContract = false;
  let snapshot: { value: Value } | null = null;

  function apply() {
    if (contractKey !== null && snapshot) {
      try { options.apply(snapshot.value); }
      catch (error) {
        snapshot = null;
        options.clear();
        options.onError(error);
      }
    }
  }
  async function load() {
    const requested = ++sequence;
    const target = scope;
    try {
      if (options.waitForWrites) await options.waitForWrites();
      if (requested !== sequence) return;
      const value = await options.load(target);
      if (requested !== sequence) return;
      snapshot = { value };
      apply();
    } catch (error) {
      if (requested !== sequence) return;
      snapshot = null;
      options.clear();
      options.onError(error);
    }
  }
  return {
    sync(nextIdentity: string, nextScope: Scope, nextContractKey: string | null) {
      if (nextIdentity !== identity) {
        identity = nextIdentity;
        scope = nextScope;
        generation += 1;
        sequence += 1;
        contractKey = nextContractKey;
        hasSeenContract = nextContractKey !== null;
        snapshot = null;
        options.clear();
        if (identity) void load();
        return;
      }
      if (nextContractKey === contractKey) return;
      const firstReady = !hasSeenContract && nextContractKey !== null;
      hasSeenContract ||= nextContractKey !== null;
      contractKey = nextContractKey;
      if (firstReady) {
        // Initial contract arrival must not repeat the already parallel GET.
        apply();
      } else {
        // Responses were sanitized by the server's policy. A changed policy
        // needs a fresh response, not reinterpretation of a filtered snapshot.
        snapshot = null;
        sequence += 1;
        options.clear();
        if (identity && contractKey !== null) void load();
      }
    },
    edit(value: Value) {
      sequence += 1; // A slow GET must not overwrite a newer local edit/reset.
      snapshot = { value };
    },
    capture() {
      const capturedGeneration = generation;
      const capturedIdentity = identity;
      return { scope, isCurrent: () => generation === capturedGeneration && identity === capturedIdentity };
    },
  };
}

/** Navigation may change while a write is queued; authentication may not. */
export function enqueuePreferenceWrite(
  previous: Promise<unknown>,
  write: () => Promise<unknown>,
  isAuthorityCurrent: () => boolean,
): Promise<void> {
  return previous.catch(() => {}).then(async () => {
    if (!isAuthorityCurrent()) throw new Error('preference write authority changed');
    await write();
  });
}
