import { intentRequestRaw } from '../api/intents';
import type { MutationContract } from './sceneActionProtocol';

export interface SceneMutationExecuteInput {
  mutation: Partial<MutationContract> & Record<string, unknown>;
  actionKey: string;
  recordId?: number | null;
  model?: string;
  context?: Record<string, unknown>;
  params?: Record<string, unknown>;
}

export interface SceneMutationExecuteResult {
  intent: string;
  traceId: string;
  data: Record<string, unknown>;
}

function asText(value: unknown): string {
  return typeof value === 'string' ? value.trim() : '';
}

function asInt(value: unknown): number {
  const num = Number(value || 0);
  return Number.isFinite(num) && num > 0 ? Math.trunc(num) : 0;
}

function valueAtPath(source: Record<string, unknown>, path: string): unknown {
  return path.split('.').reduce<unknown>((value, key) => (
    value && typeof value === 'object' && !Array.isArray(value)
      ? (value as Record<string, unknown>)[key]
      : undefined
  ), source);
}

function resolveParamValue(value: unknown, sources: Record<string, unknown>): unknown {
  if (typeof value === 'string' && value.startsWith('$')) {
    return valueAtPath(sources, value.slice(1));
  }
  if (Array.isArray(value)) return value.map((item) => resolveParamValue(item, sources));
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.entries(value as Record<string, unknown>)
      .map(([key, item]) => [key, resolveParamValue(item, sources)]));
  }
  return value;
}

function buildParams(input: SceneMutationExecuteInput): Record<string, unknown> {
  const context = (input.context && typeof input.context === 'object')
    ? (input.context as Record<string, unknown>)
    : {};
  const params = (input.params && typeof input.params === 'object')
    ? (input.params as Record<string, unknown>)
    : {};
  const template = input.mutation.params;
  if (!template || typeof template !== 'object' || Array.isArray(template)) return {};
  return resolveParamValue(template, {
    record_id: asInt(input.recordId),
    action_key: asText(input.actionKey),
    operation: asText(input.mutation.operation),
    context,
    params,
  }) as Record<string, unknown>;
}

export async function executeSceneMutation(input: SceneMutationExecuteInput): Promise<SceneMutationExecuteResult> {
  const intent = asText(input.mutation.intent);
  if (!intent) {
    throw new Error('mutation intent is required by the backend contract');
  }
  const params = buildParams(input);
  const response = await intentRequestRaw<Record<string, unknown>>({
    intent,
    params,
  });
  return {
    intent,
    traceId: response.traceId,
    data: response.data,
  };
}
