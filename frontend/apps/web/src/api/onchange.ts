import { intentRequest } from './intents';
import type { FeedbackDescribeRequest, FeedbackEvaluateRequest } from '../app/contracts/onchangeFeedbackEvaluation';

export type OnchangeLinePatch = {
  field: string;
  row_key?: string;
  row_id?: number;
  patch?: Record<string, unknown>;
  modifiers_patch?: Record<string, Record<string, unknown>>;
  warnings?: Array<{ title?: string; message?: string; reason_code?: string }>;
  row_state?: 'create' | 'update' | 'remove' | 'keep' | string;
  command_hint?: number[];
  domain?: unknown[];
};

export type OnchangeResponse = {
  schema_version?: string;
  patch?: Record<string, unknown>;
  modifiers_patch?: Record<string, Record<string, unknown>>;
  line_patches?: OnchangeLinePatch[];
  warnings?: Array<{ title?: string; message?: string; reason_code?: string }>;
  applied_fields?: string[];
  feedback_evaluation?: unknown;
};

export async function triggerOnchange(params: {
  model: string;
  res_id?: number | null;
  view_id?: unknown;
  values: Record<string, unknown>;
  changed_fields: string[];
  context?: Record<string, unknown>;
  feedback_evaluation?: FeedbackDescribeRequest | FeedbackEvaluateRequest;
  client_contract_capabilities?: string[];
}) {
  return intentRequest<OnchangeResponse>({
    intent: 'api.onchange',
    params: {
      model: params.model,
      res_id: params.res_id || undefined,
      view_id: params.view_id,
      values: params.values,
      changed_fields: params.changed_fields,
      context: params.context || {},
      ...(params.feedback_evaluation ? { feedback_evaluation: params.feedback_evaluation } : {}),
      ...(params.client_contract_capabilities
        ? { client_contract_capabilities: params.client_contract_capabilities }
        : {}),
    },
  });
}
