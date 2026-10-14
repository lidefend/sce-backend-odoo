import type { NativeActionNotification } from '@sc/schema';
import { TDesignNotificationPlugin } from './tdesignPrimitiveBridge';

const NATIVE_NOTIFICATION_TRANSIENT_DURATION_MS = 5000;

/** Registered P0 presentation mapping: sticky has no timer; transient lasts 5s. */
export async function showNativeActionNotification(notification: NativeActionNotification, onClosed?: () => void) {
  const instance = await TDesignNotificationPlugin(notification.type === 'danger' ? 'error' : notification.type, {
    title: notification.title,
    content: notification.message,
    duration: notification.sticky ? 0 : NATIVE_NOTIFICATION_TRANSIENT_DURATION_MS,
    closeBtn: true,
    onClose: onClosed,
    onDurationEnd: onClosed,
  });
  return () => { instance.close(); onClosed?.(); };
}
