export const FEEDBACK_EVALUATION_VERSION = '1.0.0' as const;
export const FEEDBACK_DRAFT_CAPABILITY = 'form.feedback.draft.v1' as const;
export const FEEDBACK_MESSAGE_CAPABILITY = 'form.feedback.message.v1' as const;

export type FeedbackDependency = {
  field: string;
  type: 'date' | 'text' | 'many2one_presence';
};

export type FeedbackBinding = {
  etag: string;
  model: string;
  view_id: number;
  container_id: string;
  source_container_id: string;
  native_locator: string;
  occurrence_index: number;
  component_key: 'sc.feedback.message';
  component_version: '1.0.0';
  purpose: 'advisory';
  dependencies: FeedbackDependency[];
  visibility_owner: 'feedback_evaluation';
};

export type FeedbackInput =
  | { field: string; present: false }
  | { field: string; present: true; value: string | boolean };

export type FeedbackDescribeRequest = {
  version: typeof FEEDBACK_EVALUATION_VERSION;
  operation: 'describe';
  request_id: string;
  view_id: number;
  container_id: string;
};

export type FeedbackEvaluateRequest = {
  version: typeof FEEDBACK_EVALUATION_VERSION;
  operation: 'evaluate';
  request_id: string;
  view_id: number;
  container_id: string;
  binding_etag: string;
  inputs: FeedbackInput[];
};

export type FeedbackDescribeResult = {
  version: typeof FEEDBACK_EVALUATION_VERSION;
  request_id: string;
  status: 'described';
  binding: FeedbackBinding;
};

export type FeedbackEvaluateResult = {
  version: typeof FEEDBACK_EVALUATION_VERSION;
  request_id: string;
  status: 'ready';
  binding_etag: string;
  container_id: string;
  result: {
    content: string;
    visible: boolean;
  };
};

export type FeedbackFailure = {
  version: typeof FEEDBACK_EVALUATION_VERSION;
  request_id?: string;
  status: 'failed';
  diagnostic: {
    code: string;
    path: string;
  };
};

const REQUEST_ID = /^[A-Za-z0-9_-]{1,128}$/;
const SHA256 = /^[0-9a-f]{64}$/;

function invalid(path: string): never {
  throw new Error(`FEEDBACK_PROTOCOL_INVALID:${path}`);
}

function record(value: unknown, path: string): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) invalid(path);
  return value as Record<string, unknown>;
}

function exact(value: unknown, keys: readonly string[], path: string): Record<string, unknown> {
  const row = record(value, path);
  const actual = Object.keys(row).sort();
  const expected = [...keys].sort();
  if (actual.length !== expected.length || actual.some((key, index) => key !== expected[index])) invalid(path);
  return row;
}

function text(value: unknown, path: string): string {
  if (typeof value !== 'string' || !value) invalid(path);
  return value;
}

function positiveInteger(value: unknown, path: string): number {
  if (!Number.isInteger(value) || Number(value) <= 0) invalid(path);
  return Number(value);
}

function decodeDependencies(value: unknown): FeedbackDependency[] {
  if (!Array.isArray(value) || !value.length) invalid('feedback_evaluation.binding.dependencies');
  const seen = new Set<string>();
  return value.map((item, index) => {
    const row = exact(item, ['field', 'type'], `feedback_evaluation.binding.dependencies[${index}]`);
    const field = text(row.field, `feedback_evaluation.binding.dependencies[${index}].field`);
    const type = row.type;
    if (seen.has(field)
      || (type !== 'date' && type !== 'text' && type !== 'many2one_presence')) {
      invalid(`feedback_evaluation.binding.dependencies[${index}]`);
    }
    seen.add(field);
    return { field, type };
  });
}

function decodeBinding(value: unknown): FeedbackBinding {
  const row = exact(value, [
    'etag', 'model', 'view_id', 'container_id', 'source_container_id', 'native_locator',
    'occurrence_index', 'component_key', 'component_version', 'purpose', 'dependencies',
    'visibility_owner',
  ], 'feedback_evaluation.binding');
  if (typeof row.etag !== 'string' || !SHA256.test(row.etag)) invalid('feedback_evaluation.binding.etag');
  if (row.component_key !== 'sc.feedback.message' || row.component_version !== '1.0.0'
    || row.purpose !== 'advisory' || row.visibility_owner !== 'feedback_evaluation') invalid('feedback_evaluation.binding.identity');
  return {
    etag: row.etag as string,
    model: text(row.model, 'feedback_evaluation.binding.model'),
    view_id: positiveInteger(row.view_id, 'feedback_evaluation.binding.view_id'),
    container_id: text(row.container_id, 'feedback_evaluation.binding.container_id'),
    source_container_id: text(row.source_container_id, 'feedback_evaluation.binding.source_container_id'),
    native_locator: text(row.native_locator, 'feedback_evaluation.binding.native_locator'),
    occurrence_index: positiveInteger(row.occurrence_index, 'feedback_evaluation.binding.occurrence_index'),
    component_key: 'sc.feedback.message',
    component_version: '1.0.0',
    purpose: 'advisory',
    dependencies: decodeDependencies(row.dependencies),
    visibility_owner: 'feedback_evaluation',
  };
}

export function decodeFeedbackDescribeResult(value: unknown, expectedRequestId: string): FeedbackDescribeResult {
  const row = exact(value, ['version', 'request_id', 'status', 'binding'], 'feedback_evaluation');
  if (row.version !== FEEDBACK_EVALUATION_VERSION || row.status !== 'described'
    || typeof row.request_id !== 'string' || !REQUEST_ID.test(row.request_id)
    || row.request_id !== expectedRequestId) invalid('feedback_evaluation.request_id');
  return {
    version: FEEDBACK_EVALUATION_VERSION,
    request_id: row.request_id,
    status: 'described',
    binding: decodeBinding(row.binding),
  };
}

export function decodeFeedbackEvaluateResult(
  value: unknown,
  ticket: { requestId: string; bindingEtag: string; containerId: string },
): FeedbackEvaluateResult {
  const row = exact(value, ['version', 'request_id', 'status', 'binding_etag', 'container_id', 'result'], 'feedback_evaluation');
  if (row.version !== FEEDBACK_EVALUATION_VERSION || row.status !== 'ready'
    || row.request_id !== ticket.requestId || row.binding_etag !== ticket.bindingEtag
    || row.container_id !== ticket.containerId) invalid('feedback_evaluation.identity');
  const result = exact(row.result, ['content', 'visible'], 'feedback_evaluation.result');
  if (typeof result.visible !== 'boolean' || typeof result.content !== 'string'
    || (result.visible === false && result.content !== '')
    || (result.visible === true && !result.content)) invalid('feedback_evaluation.result');
  return {
    version: FEEDBACK_EVALUATION_VERSION,
    request_id: row.request_id as string,
    status: 'ready',
    binding_etag: row.binding_etag as string,
    container_id: row.container_id as string,
    result: { content: result.content as string, visible: result.visible as boolean },
  };
}

export function decodeFeedbackFailure(value: unknown): FeedbackFailure | null {
  const outer = record(value, 'feedback_evaluation');
  const row = record(outer.feedback_evaluation, 'feedback_evaluation');
  const allowed = ['version', 'request_id', 'status', 'diagnostic'];
  if (Object.keys(row).some((key) => !allowed.includes(key))) invalid('feedback_evaluation');
  if (row.version !== FEEDBACK_EVALUATION_VERSION || row.status !== 'failed') invalid('feedback_evaluation.status');
  const diagnostic = exact(row.diagnostic, ['code', 'path'], 'feedback_evaluation.diagnostic');
  return {
    version: FEEDBACK_EVALUATION_VERSION,
    ...(typeof row.request_id === 'string' && REQUEST_ID.test(row.request_id) ? { request_id: row.request_id } : {}),
    status: 'failed',
    diagnostic: {
      code: text(diagnostic.code, 'feedback_evaluation.diagnostic.code'),
      path: text(diagnostic.path, 'feedback_evaluation.diagnostic.path'),
    },
  };
}

export function decodeFeedbackEvaluationData(
  data: unknown,
  operation: 'describe' | 'evaluate',
  expected: { requestId: string; bindingEtag?: string; containerId: string },
): FeedbackDescribeResult | FeedbackEvaluateResult {
  const outer = record(data, 'data');
  if (!Object.hasOwn(outer, 'feedback_evaluation')) invalid('data.feedback_evaluation');
  if (outer.patch && Object.keys(record(outer.patch, 'data.patch')).length) invalid('data.patch');
  if (outer.modifiers_patch && Object.keys(record(outer.modifiers_patch, 'data.modifiers_patch')).length) invalid('data.modifiers_patch');
  if (Array.isArray(outer.line_patches) && outer.line_patches.length) invalid('data.line_patches');
  if (Array.isArray(outer.warnings) && outer.warnings.length) invalid('data.warnings');
  if (operation === 'describe') return decodeFeedbackDescribeResult(outer.feedback_evaluation, expected.requestId);
  if (!expected.bindingEtag) invalid('feedback_evaluation.binding_etag');
  return decodeFeedbackEvaluateResult(outer.feedback_evaluation, {
    requestId: expected.requestId,
    bindingEtag: expected.bindingEtag,
    containerId: expected.containerId,
  });
}
