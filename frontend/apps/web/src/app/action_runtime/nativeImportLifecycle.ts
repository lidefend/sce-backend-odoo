import { currentContextEpoch, isCurrentContextEpoch } from '../contextEpoch';

export type NativeImportRequestTicket = Readonly<{
  generation: number;
  epoch: number;
  identity: string;
  signal: AbortSignal;
}>;

export type NativeImportInvalidationReason =
  | 'closed'
  | 'settled'
  | 'superseded'
  | 'context_changed'
  | 'unmounted';

type OwnerDependencies = {
  currentEpoch: () => number;
  isCurrentEpoch: (epoch: number) => boolean;
  createAbortController: () => AbortController;
};

const DEFAULT_DEPENDENCIES: OwnerDependencies = {
  currentEpoch: currentContextEpoch,
  isCurrentEpoch: isCurrentContextEpoch,
  createAbortController: () => new AbortController(),
};

/**
 * Owns the only live native-import request chain for one mounted wizard.
 * A response is allowed to mutate UI state only while its ticket remains current.
 */
export function createNativeImportRequestOwner(
  dependencies: OwnerDependencies = DEFAULT_DEPENDENCIES,
) {
  let generation = 0;
  let active: { ticket: NativeImportRequestTicket; controller: AbortController } | null = null;
  let disposed = false;

  function abortActive(reason: NativeImportInvalidationReason): void {
    if (!active) return;
    active.controller.abort(reason);
    active = null;
  }

  function begin(identity: string): NativeImportRequestTicket {
    if (disposed) throw new Error('native import lifecycle is disposed');
    abortActive('superseded');
    generation += 1;
    const controller = dependencies.createAbortController();
    const ticket: NativeImportRequestTicket = {
      generation,
      epoch: dependencies.currentEpoch(),
      identity: String(identity || ''),
      signal: controller.signal,
    };
    active = { ticket, controller };
    return ticket;
  }

  function isCurrent(ticket: NativeImportRequestTicket | null | undefined): boolean {
    return Boolean(
      !disposed
      && ticket
      && active?.ticket === ticket
      && active.ticket.generation === ticket.generation
      && active.ticket.identity === ticket.identity
      && dependencies.isCurrentEpoch(ticket.epoch),
    );
  }

  function invalidate(reason: NativeImportInvalidationReason): void {
    generation += 1;
    abortActive(reason);
  }

  function dispose(): void {
    if (disposed) return;
    disposed = true;
    invalidate('unmounted');
  }

  return {
    begin,
    isCurrent,
    invalidate,
    dispose,
    isDisposed: () => disposed,
  };
}
