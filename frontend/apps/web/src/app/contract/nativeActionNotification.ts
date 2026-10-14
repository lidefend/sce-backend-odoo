import type { NativeActionNotification } from '@sc/schema';
import { contractGapError } from './contractGap';

export function decodeNativeActionNotification(result: unknown): NativeActionNotification | null {
  if (!result || typeof result !== 'object' || Array.isArray(result)) return null;
  const raw = (result as Record<string, unknown>).raw_action;
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null;
  const action = raw as Record<string, unknown>;
  if (action.tag !== 'display_notification') return null;
  if (action.type !== 'ir.actions.client') {
    throw contractGapError({ kind: 'contract_defect', missing: 'result.raw_action.type',
      requiredDeclarationLayer: 'P0: native action result normalizer' }, 'Invalid native notification action');
  }
  return decodeNativeNotificationParameters(action.params);
}

export function decodeNativeNotificationParameters(value: unknown): NativeActionNotification {
  const params = value as Record<string, unknown> | undefined;
  if (!params || typeof params !== 'object' || Array.isArray(params)
    || typeof params.message !== 'string' || !params.message.trim()
    || typeof params.title !== 'string' || typeof params.sticky !== 'boolean'
    || typeof params.type !== 'string' || !['info', 'success', 'warning', 'danger'].includes(params.type)) {
    throw contractGapError({ kind: 'contract_defect', missing: 'result.raw_action.params',
      requiredDeclarationLayer: 'P0: native action result normalizer' }, 'Invalid native notification declaration');
  }
  return { title: params.title, message: params.message, sticky: params.sticky,
    type: params.type as NativeActionNotification['type'] };
}
