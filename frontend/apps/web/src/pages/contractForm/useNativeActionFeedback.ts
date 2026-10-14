import { getCurrentScope, onScopeDispose, ref, watch } from 'vue';
import type { NativeActionNotification } from '@sc/schema';
import { currentContextEpoch, currentContextSignal } from '../../app/contextEpoch';
import { decodeNativeActionNotification } from '../../app/contract/nativeActionNotification';

export type ActionFeedbackOwner = { owns: () => boolean; publish: (result: unknown) => Promise<void>; publishNotification: (notification: NativeActionNotification) => Promise<void>; navigationTicket: () => (() => boolean) | null };

export function useNativeActionFeedback(params: {
  identity: () => string;
  active: () => boolean;
  show: (notification: NativeActionNotification) => Promise<() => void>;
}) {
  let epoch = 0;
  const sequence = ref(0);
  let disposed = false;
  let close: (() => void) | undefined;
  let detach: (() => void) | undefined;
  const invalidate = () => { epoch += 1; close?.(); close = undefined; detach?.(); detach = undefined; };
  watch(() => [params.identity(), params.active()], invalidate, { flush: 'sync' });
  if (getCurrentScope()) onScopeDispose(() => { disposed = true; invalidate(); });
  function begin(): ActionFeedbackOwner {
    close?.(); close = undefined; detach?.();
    const signal = currentContextSignal();
    signal.addEventListener('abort', invalidate, { once: true });
    detach = () => signal.removeEventListener('abort', invalidate);
    const operation = ++sequence.value;
    const ownerEpoch = epoch;
    const contextEpoch = currentContextEpoch();
    const owns = () => !disposed && params.active() && operation === sequence.value
      && ownerEpoch === epoch && contextEpoch === currentContextEpoch();
    async function publishNotification(notification: NativeActionNotification) {
      if (!owns()) return;
      const dismiss = await params.show(notification);
      if (!owns()) dismiss(); else close = dismiss;
    }
    return { owns, publishNotification, navigationTicket: () => owns() ? (() => operation === sequence.value && contextEpoch === currentContextEpoch()) : null, async publish(result) {
      if (!owns()) return;
      const notification = decodeNativeActionNotification(result);
      if (!notification) return;
      await publishNotification(notification);
    } };
  }
  return { begin };
}
