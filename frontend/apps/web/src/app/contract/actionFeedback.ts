import type { PageBlockActionFeedback } from '@sc/schema';
import { contractGapError } from './contractGap';

const FEEDBACK_KEYS = new Set([
  'schemaVersion',
  'actionId',
  'status',
  'reasonCode',
  'message',
  'traceId',
]);

function gap(path: string, message: string): never {
  throw contractGapError({
    kind: 'contract_defect',
    missing: path,
    requiredDeclarationLayer: 'P0: page-block-action runtime feedback producer',
  }, message);
}

function record(value: unknown, path: string): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    gap(path, '契约声明必须是对象');
  }
  return value as Record<string, unknown>;
}

function text(value: unknown, path: string): string {
  if (typeof value !== 'string' || !value.trim()) {
    gap(path, '契约声明的非空文本缺失');
  }
  return value.trim();
}

function decodeFeedback(value: unknown, index: number): PageBlockActionFeedback {
  const path = `runtimePatch.actionFeedback[${index}]`;
  const row = record(value, path);
  const unknown = Object.keys(row).filter((key) => !FEEDBACK_KEYS.has(key));
  if (unknown.length) {
    gap(`${path}.${unknown[0]}`, '动作反馈包含未声明属性');
  }
  if (row.schemaVersion !== '1.0.0') {
    gap(`${path}.schemaVersion`, '动作反馈版本必须为 1.0.0');
  }
  const status = text(row.status, `${path}.status`);
  if (!['success', 'denied', 'failed'].includes(status)) {
    gap(`${path}.status`, '动作反馈状态非法');
  }
  const actionId = text(row.actionId, `${path}.actionId`);
  const traceId = text(row.traceId, `${path}.traceId`);
  const reasonCode = typeof row.reasonCode === 'string' ? row.reasonCode.trim() : '';
  const message = typeof row.message === 'string' ? row.message.trim() : '';
  if (status !== 'success' && (!reasonCode || !message)) {
    gap(path, 'denied/failed 动作反馈必须声明 reasonCode 与 message');
  }
  return {
    schemaVersion: '1.0.0',
    actionId,
    status: status as PageBlockActionFeedback['status'],
    reasonCode,
    message,
    traceId,
  };
}

export function decodeActionFeedbackRuntimePatch(value: unknown): PageBlockActionFeedback[] {
  if (value === undefined || value === null) return [];
  const patch = record(value, 'runtimePatch');
  const raw = patch.actionFeedback;
  if (raw === undefined) return [];
  if (!Array.isArray(raw)) {
    gap('runtimePatch.actionFeedback', '动作反馈必须为数组');
  }
  return raw.map((row, index) => decodeFeedback(row, index));
}

export function firstActionFeedback(value: unknown): PageBlockActionFeedback | undefined {
  return decodeActionFeedbackRuntimePatch(value)[0];
}
