import { onScopeDispose, shallowRef, watch, type Ref } from 'vue';
import { triggerOnchange } from '../../api/onchange';
import type { ContractV2NormalizedStore } from '../../app/contracts/v2/types';
import {
  FEEDBACK_DRAFT_CAPABILITY,
  FEEDBACK_EVALUATION_VERSION,
  FEEDBACK_MESSAGE_CAPABILITY,
  decodeFeedbackEvaluationData,
  type FeedbackBinding,
  type FeedbackDescribeResult,
  type FeedbackEvaluateRequest,
  type FeedbackEvaluateResult,
  type FeedbackInput,
} from '../../app/contracts/onchangeFeedbackEvaluation';

export const FEEDBACK_EVALUATION_DEBOUNCE_MS = 300;

export type DraftFeedbackState = {
  containerId: string;
  status: 'describing' | 'pending' | 'ready' | 'unavailable';
  content: string;
  visible: boolean;
  binding?: FeedbackBinding;
  diagnostic?: string;
  revision: number;
};

type FeedbackHost = {
  containerId: string;
  viewId: number;
};

type HostRuntime = {
  host: FeedbackHost;
  binding?: FeedbackBinding;
  revision: number;
  sequence: number;
  timer: ReturnType<typeof setTimeout> | null;
};

type Ticket = {
  epoch: number;
  runtime: HostRuntime;
  requestId: string;
  revision: number;
  sequence: number;
  recordKey: string;
  model: string;
  viewId: number;
  contractSha256: string;
  contextIdentity: string;
  bindingEtag: string;
  containerId: string;
  inputs: FeedbackInput[];
};

type Transport = (params: Parameters<typeof triggerOnchange>[0]) => ReturnType<typeof triggerOnchange>;

function object(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {};
}

function text(value: unknown): string {
  return typeof value === 'string' ? value.trim() : '';
}

function positiveInteger(value: unknown): number {
  return Number.isInteger(value) && Number(value) > 0 ? Number(value) : 0;
}

function relationPresent(value: unknown): boolean {
  if (Array.isArray(value)) return positiveInteger(value[0]) > 0;
  if (typeof value === 'object' && value !== null) {
    return positiveInteger((value as Record<string, unknown>).id) > 0;
  }
  return positiveInteger(value) > 0;
}

function draftHosts(store: ContractV2NormalizedStore | null): FeedbackHost[] {
  if (!store) return [];
  const nodes: Array<Record<string, unknown>> = [];
  function visit(rows: unknown[]) {
    rows.forEach((value) => {
      const node = object(value);
      nodes.push(node);
      const children = Array.isArray(node.children) ? node.children : [];
      visit(children);
    });
  }
  visit(store.snapshot.layoutContract.containerTree as unknown[]);
  const byId = new Map(nodes.map((node) => [text(node.containerId), node]));
  return nodes.flatMap((host) => {
    const config = object(host.componentConfig);
    const evaluation = object(config.evaluation);
    if (host.componentKey !== 'sc.feedback.message' || config.purpose !== 'advisory'
      || evaluation.capability !== FEEDBACK_DRAFT_CAPABILITY
      || evaluation.visibilityOwner !== 'feedback_evaluation') return [];
    const sourceId = text(object(config.contentRef).containerId);
    const source = byId.get(sourceId);
    const authority = object(source?.sourceAuthority || source?.source_authority);
    const viewId = positiveInteger(authority.view_id || authority.viewId);
    const containerId = text(host.containerId);
    return containerId && viewId ? [{ containerId, viewId }] : [];
  });
}

function requestId(epoch: number, sequence: number, operation: string): string {
  return `feedback_${epoch}_${sequence}_${operation}`;
}

function failureCode(error: unknown): string {
  const candidate = error as { reasonCode?: unknown; message?: unknown };
  const reason = text(candidate?.reasonCode);
  if (reason) return reason;
  const message = text(candidate?.message);
  return message.startsWith('FEEDBACK_') || message.startsWith('COMPONENT_')
    ? message.split(':')[0]
    : 'FEEDBACK_EVALUATION_FAILED';
}

export function useDraftFeedbackEvaluation(options: {
  store: Ref<ContractV2NormalizedStore | null>;
  model: () => string;
  recordId: () => number | null;
  formData: Record<string, unknown>;
  presence: Ref<Set<string>>;
  contextIdentity: () => string;
  context: () => Record<string, unknown>;
  active?: () => boolean;
  transport?: Transport;
}) {
  const transport = options.transport || triggerOnchange;
  const states = shallowRef<Map<string, DraftFeedbackState>>(new Map());
  const runtimes = new Map<string, HostRuntime>();
  let epoch = 0;
  let contextKey = '';
  let disposed = false;

  const publish = (containerId: string, state: DraftFeedbackState) => {
    if (disposed) return;
    const next = new Map(states.value);
    next.set(containerId, Object.freeze({ ...state }));
    states.value = next;
  };
  const clearTimer = (runtime: HostRuntime) => {
    if (runtime.timer) clearTimeout(runtime.timer);
    runtime.timer = null;
  };

  const recordKey = () => `${options.model()}:${options.recordId() ?? 'new'}`;
  const contractSha256 = () => text(options.store.value?.snapshot.meta.lifecycle.integrity.contractSha256);

  const dependencyInputs = (binding: FeedbackBinding): FeedbackInput[] => binding.dependencies.map((dependency) => {
    if (!options.presence.value.has(dependency.field)) return { field: dependency.field, present: false };
    const raw = options.formData[dependency.field];
    if (dependency.type === 'number_nonzero') {
      if (raw === false || raw === null || raw === '') return { field: dependency.field, present: true, value: false };
      if (typeof raw !== 'number' || !Number.isFinite(raw)) return { field: dependency.field, present: false };
      return { field: dependency.field, present: true, value: raw !== 0 };
    }
    if (dependency.type === 'selection') {
      if (raw === false || raw === null || raw === '') return { field: dependency.field, present: true, value: false };
      if (typeof raw !== 'string') return { field: dependency.field, present: false };
      return { field: dependency.field, present: true, value: raw };
    }
    if (dependency.type === 'many2one_presence') {
      return { field: dependency.field, present: true, value: relationPresent(raw) };
    }
    if (dependency.type === 'many2many_presence') {
      if (raw === false || raw === null) return { field: dependency.field, present: true, value: false };
      // Native default_get uses a single SET command for a complete snapshot.
      // Partial commands cannot establish presence without an original record.
      const command = Array.isArray(raw) && raw.length === 1 ? raw[0] : null;
      const ids = Array.isArray(command) && command.length === 3
        && command[0] === 6 && command[1] === 0 ? command[2] : raw;
      if (!Array.isArray(ids) || !ids.every((id) => positiveInteger(id) > 0)) {
        return { field: dependency.field, present: false };
      }
      return { field: dependency.field, present: true, value: ids.length > 0 };
    }
    if (dependency.type === 'date') {
      const value = raw === false || raw === null || raw === undefined || raw === '' ? false : String(raw);
      return { field: dependency.field, present: true, value };
    }
    const value = raw === false || raw === null || raw === undefined ? false : String(raw);
    return { field: dependency.field, present: true, value };
  });

  const ticketStillCurrent = (ticket: Ticket) => (
    !disposed
    && ticket.epoch === epoch
    && ticket.runtime === runtimes.get(ticket.containerId)
    && ticket.revision === ticket.runtime.revision
    && ticket.sequence === ticket.runtime.sequence
    && ticket.recordKey === recordKey()
    && ticket.model === options.model()
    && ticket.viewId === ticket.runtime.host.viewId
    && ticket.contractSha256 === contractSha256()
    && ticket.contextIdentity === options.contextIdentity()
    && ticket.bindingEtag === ticket.runtime.binding?.etag
  );

  const evaluate = async (runtime: HostRuntime) => {
    const binding = runtime.binding;
    if (!binding) return;
    const inputs = dependencyInputs(binding);
    if (inputs.some((entry) => entry.present === false)) {
      publish(runtime.host.containerId, {
        containerId: runtime.host.containerId,
        status: 'unavailable',
        content: '',
        visible: false,
        binding,
        diagnostic: 'FEEDBACK_INPUT_INVALID',
        revision: runtime.revision,
      });
      return;
    }
    runtime.sequence += 1;
    const ticket: Ticket = {
      epoch,
      runtime,
      requestId: requestId(epoch, runtime.sequence, 'evaluate'),
      revision: runtime.revision,
      sequence: runtime.sequence,
      recordKey: recordKey(),
      model: options.model(),
      viewId: runtime.host.viewId,
      contractSha256: contractSha256(),
      contextIdentity: options.contextIdentity(),
      bindingEtag: binding.etag,
      containerId: runtime.host.containerId,
      inputs,
    };
    const request: FeedbackEvaluateRequest = {
      version: FEEDBACK_EVALUATION_VERSION,
      operation: 'evaluate',
      request_id: ticket.requestId,
      view_id: ticket.viewId,
      container_id: ticket.containerId,
      binding_etag: ticket.bindingEtag,
      inputs,
    };
    publish(runtime.host.containerId, {
      containerId: runtime.host.containerId,
      status: 'pending',
      content: '',
      visible: false,
      binding,
      revision: runtime.revision,
    });
    try {
      const response = await transport({
        model: ticket.model,
        res_id: options.recordId(),
        values: {},
        changed_fields: [],
        context: options.context(),
        feedback_evaluation: request,
        client_contract_capabilities: [FEEDBACK_MESSAGE_CAPABILITY, FEEDBACK_DRAFT_CAPABILITY],
      });
      if (!ticketStillCurrent(ticket)) return;
      const decoded = decodeFeedbackEvaluationData(response, 'evaluate', {
        requestId: ticket.requestId,
        bindingEtag: ticket.bindingEtag,
        containerId: ticket.containerId,
      }) as FeedbackEvaluateResult;
      if (!ticketStillCurrent(ticket)) return;
      publish(ticket.containerId, {
        containerId: ticket.containerId,
        status: 'ready',
        content: decoded.result.content,
        visible: decoded.result.visible,
        binding,
        revision: ticket.revision,
      });
    } catch (error) {
      if (!ticketStillCurrent(ticket)) return;
      publish(ticket.containerId, {
        containerId: ticket.containerId,
        status: 'unavailable',
        content: '',
        visible: false,
        binding,
        diagnostic: failureCode(error),
        revision: ticket.revision,
      });
    }
  };

  const schedule = (runtime: HostRuntime) => {
    clearTimer(runtime);
    if (!runtime.binding) return;
    if (dependencyInputs(runtime.binding).some((entry) => entry.present === false)) {
      void evaluate(runtime);
      return;
    }
    runtime.timer = setTimeout(() => {
      runtime.timer = null;
      void evaluate(runtime);
    }, FEEDBACK_EVALUATION_DEBOUNCE_MS);
  };

  const describe = async (host: FeedbackHost, runtime: HostRuntime, describeEpoch: number) => {
    runtime.sequence += 1;
    const id = requestId(describeEpoch, runtime.sequence, 'describe');
    publish(host.containerId, {
      containerId: host.containerId,
      status: 'describing',
      content: '',
      visible: false,
      revision: runtime.revision,
    });
    try {
      const response = await transport({
        model: options.model(),
        res_id: options.recordId(),
        values: {},
        changed_fields: [],
        context: options.context(),
        feedback_evaluation: {
          version: FEEDBACK_EVALUATION_VERSION,
          operation: 'describe',
          request_id: id,
          view_id: host.viewId,
          container_id: host.containerId,
        },
        client_contract_capabilities: [FEEDBACK_MESSAGE_CAPABILITY, FEEDBACK_DRAFT_CAPABILITY],
      });
      if (disposed || describeEpoch !== epoch || runtimes.get(host.containerId) !== runtime) return;
      const decoded = decodeFeedbackEvaluationData(response, 'describe', {
        requestId: id,
        containerId: host.containerId,
      }) as FeedbackDescribeResult;
      const binding = decoded.binding;
      if (binding.model !== options.model() || binding.view_id !== host.viewId
        || binding.container_id !== host.containerId) {
        throw new Error('FEEDBACK_BINDING_STALE');
      }
      runtime.binding = binding;
      schedule(runtime);
    } catch (error) {
      if (disposed || describeEpoch !== epoch || runtimes.get(host.containerId) !== runtime) return;
      publish(host.containerId, {
        containerId: host.containerId,
        status: 'unavailable',
        content: '',
        visible: false,
        diagnostic: failureCode(error),
        revision: runtime.revision,
      });
    }
  };

  const reset = () => {
    epoch += 1;
    contextKey = `${options.model()}|${options.recordId() ?? 'new'}|${contractSha256()}|${options.contextIdentity()}`;
    Array.from(runtimes.values()).forEach(clearTimer);
    runtimes.clear();
    states.value = new Map();
    draftHosts(options.store.value).forEach((host) => {
      const runtime: HostRuntime = {
        host,
        revision: 0,
        sequence: 0,
        timer: null,
      };
      runtimes.set(host.containerId, runtime);
      void describe(host, runtime, epoch);
    });
  };

  const onDraftChanged = (name: string) => {
    runtimes.forEach((runtime) => {
      if (!runtime.binding?.dependencies.some((dependency) => dependency.field === name)) return;
      runtime.revision += 1;
      clearTimer(runtime);
      publish(runtime.host.containerId, {
        containerId: runtime.host.containerId,
        status: 'pending',
        content: '',
        visible: false,
        binding: runtime.binding,
        revision: runtime.revision,
      });
      schedule(runtime);
    });
  };

  const invalidate = () => {
    epoch += 1;
    Array.from(runtimes.values()).forEach(clearTimer);
    states.value = new Map(Array.from(states.value, ([containerId, state]) => [containerId, {
      ...state, status: 'unavailable' as const, content: '', visible: false, diagnostic: 'FEEDBACK_BINDING_STALE',
    }]));
  };

  watch(
    () => [
      options.store.value?.snapshot.meta.lifecycle.integrity.contractSha256 || '',
      options.model(),
      options.recordId() ?? 0,
      options.contextIdentity(),
    ].join('|'),
    () => {
      const next = `${options.model()}|${options.recordId() ?? 'new'}|${contractSha256()}|${options.contextIdentity()}`;
      if (next !== contextKey) reset();
    },
    { immediate: true },
  );
  watch(options.presence, () => {
    runtimes.forEach((runtime) => {
      if (runtime.binding && !runtime.timer) schedule(runtime);
    });
  });
  if (options.active) {
    watch(options.active, (active) => {
      if (active) reset();
      else invalidate();
    });
  }
  onScopeDispose(() => {
    disposed = true;
    Array.from(runtimes.values()).forEach(clearTimer);
  });

  return { states, invalidate, onDraftChanged, reset, reevaluate: schedule };
}
