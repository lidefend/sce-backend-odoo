let activeContextEpoch = 0;
let activeContextController = new AbortController();

function rotateContext(): number {
  activeContextController.abort('context_changed');
  activeContextController = new AbortController();
  activeContextEpoch += 1;
  return activeContextEpoch;
}

export function beginContextTransition(): number {
  return rotateContext();
}

export function currentContextEpoch(): number {
  return activeContextEpoch;
}

export function isCurrentContextEpoch(epoch: number): boolean {
  return epoch === activeContextEpoch;
}

export function currentContextSignal(): AbortSignal {
  return activeContextController.signal;
}

export function invalidateContextRequests(): void {
  rotateContext();
}

export type ContextRequestIdentity = Record<string, string | number | boolean | null | undefined>;

export type ContextRequestTicket = Readonly<{
  family: string;
  sequence: number;
  epoch: number;
  identityKey: string;
  extraIdentity: ContextRequestIdentity;
}>;

type BooleanActivityRef = { value: boolean };

type ContextRequestOwnerAccessors = {
  currentEpoch: () => number;
  isCurrentEpoch: (epoch: number) => boolean;
};

const activityOwners = new WeakMap<object, object>();

export function beginBooleanActivity(target: BooleanActivityRef): () => void {
  const token = {};
  activityOwners.set(target, token);
  target.value = true;
  return () => {
    if (activityOwners.get(target) !== token) return;
    activityOwners.delete(target);
    target.value = false;
  };
}

function contextIdentityKey(epoch: number, identity: ContextRequestIdentity): string {
  const normalized = Object.entries(identity)
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([key, value]) => [key, value === null || value === undefined ? '' : String(value)]);
  return JSON.stringify([epoch, normalized]);
}

export function createContextRequestOwner(
  readIdentity: () => ContextRequestIdentity,
  accessors: ContextRequestOwnerAccessors = {
    currentEpoch: currentContextEpoch,
    isCurrentEpoch: isCurrentContextEpoch,
  },
) {
  const sequences = new Map<string, number>();
  let disposed = false;

  function nextSequence(family: string): number {
    const sequence = (sequences.get(family) || 0) + 1;
    sequences.set(family, sequence);
    return sequence;
  }

  function currentIdentityKey(extraIdentity: ContextRequestIdentity = {}): string {
    return contextIdentityKey(accessors.currentEpoch(), {
      ...readIdentity(),
      ...extraIdentity,
    });
  }

  return {
    begin(
      family: string,
      extraIdentity: ContextRequestIdentity = {},
    ): ContextRequestTicket {
      return {
        family,
        sequence: nextSequence(family),
        epoch: accessors.currentEpoch(),
        identityKey: currentIdentityKey(extraIdentity),
        extraIdentity: { ...extraIdentity },
      };
    },
    currentIdentityKey,
    isCurrent(ticket: ContextRequestTicket): boolean {
      return !disposed
        && accessors.isCurrentEpoch(ticket.epoch)
        && sequences.get(ticket.family) === ticket.sequence
        && ticket.identityKey === currentIdentityKey(ticket.extraIdentity);
    },
    isLatest(ticket: ContextRequestTicket): boolean {
      return sequences.get(ticket.family) === ticket.sequence;
    },
    invalidate(family?: string): void {
      if (family) nextSequence(family);
      else sequences.forEach((_sequence, key) => nextSequence(key));
    },
    dispose(): void {
      disposed = true;
      sequences.forEach((_sequence, key) => nextSequence(key));
    },
  };
}
