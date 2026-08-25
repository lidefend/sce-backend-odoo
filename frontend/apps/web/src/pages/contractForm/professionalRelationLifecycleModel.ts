export type ProfessionalRelationLifecycleContext = {
  nonce: string;
  fieldName: string;
  parentModel: string;
  relationModel: string;
};

export type ProfessionalRelationCreatedMessage = ProfessionalRelationLifecycleContext & {
  type: 'sc.relation_record_created.v1';
  id: number;
  label: string;
};

export type ProfessionalRelationCancelledMessage = ProfessionalRelationLifecycleContext & {
  type: 'sc.relation_record_cancelled.v1';
};

export type ProfessionalRelationLifecycleMessage = ProfessionalRelationCreatedMessage | ProfessionalRelationCancelledMessage;

export type ProfessionalRelationLifecycleEvent =
  | { kind: 'cancelled' }
  | { kind: 'created'; result: { fieldName: string; relationModel: string; id: number; label: string } };

export function resolveProfessionalRelationLifecycleContext(params: {
  query: Record<string, unknown>;
  relationModel: string;
}): ProfessionalRelationLifecycleContext | null {
  if (String(params.query.relation_create_mode || '').trim() !== 'dialog') return null;
  const context = {
    nonce: String(params.query.relation_dialog_nonce || '').trim(),
    fieldName: String(params.query.relation_return_field || '').trim(),
    parentModel: String(params.query.relation_return_model || '').trim(),
    relationModel: String(params.relationModel || '').trim(),
  };
  return isProfessionalRelationLifecycleContext(context) ? context : null;
}

export function isProfessionalRelationLifecycleContext(value: ProfessionalRelationLifecycleContext): boolean {
  return /^[a-zA-Z0-9-]{8,128}$/.test(value.nonce)
    && /^[a-zA-Z_][a-zA-Z0-9_]*$/.test(value.fieldName)
    && /^[a-zA-Z0-9_.]+$/.test(value.parentModel)
    && /^[a-zA-Z0-9_.]+$/.test(value.relationModel);
}

export function buildProfessionalRelationCreatedMessage(params: {
  query: Record<string, unknown>;
  createdId: number | string;
  relationModel: string;
  label?: string;
}): ProfessionalRelationCreatedMessage | null {
  const context = resolveProfessionalRelationLifecycleContext(params);
  const id = Number(params.createdId || 0);
  if (!context || !Number.isFinite(id) || id <= 0) return null;
  return {
    type: 'sc.relation_record_created.v1',
    ...context,
    id: Math.trunc(id),
    label: String(params.label || '').trim() || `记录 ${Math.trunc(id)}`,
  };
}

export function buildProfessionalRelationCancelledMessage(params: {
  query: Record<string, unknown>;
  relationModel: string;
}): ProfessionalRelationCancelledMessage | null {
  const context = resolveProfessionalRelationLifecycleContext(params);
  return context ? { type: 'sc.relation_record_cancelled.v1', ...context } : null;
}

export function resolveProfessionalRelationLifecycleEvent(params: {
  active: boolean;
  context: ProfessionalRelationLifecycleContext;
  eventOrigin: string;
  expectedOrigin: string;
  sourceMatches: boolean;
  payload: unknown;
}): ProfessionalRelationLifecycleEvent | null {
  if (!params.active
    || !isProfessionalRelationLifecycleContext(params.context)
    || params.eventOrigin !== params.expectedOrigin
    || !params.sourceMatches
    || !params.payload
    || typeof params.payload !== 'object'
    || Array.isArray(params.payload)) return null;
  const payload = params.payload as Record<string, unknown>;
  if (String(payload.nonce || '') !== params.context.nonce
    || String(payload.fieldName || '') !== params.context.fieldName
    || String(payload.parentModel || '') !== params.context.parentModel
    || String(payload.relationModel || '') !== params.context.relationModel) return null;
  if (payload.type === 'sc.relation_record_cancelled.v1') return { kind: 'cancelled' };
  if (payload.type !== 'sc.relation_record_created.v1') return null;
  const id = Number(payload.id || 0);
  if (!Number.isFinite(id) || id <= 0) return null;
  return {
    kind: 'created',
    result: {
      fieldName: params.context.fieldName,
      relationModel: params.context.relationModel,
      id: Math.trunc(id),
      label: String(payload.label || '').trim() || `记录 ${Math.trunc(id)}`,
    },
  };
}

export function settleProfessionalRelationLifecycle(params: {
  active: boolean;
  closeLifecycle: () => void;
  kind: ProfessionalRelationLifecycleEvent['kind'];
  restoreSearchOnCancel: boolean;
  restoreSearch: () => void;
  closeSearch: () => void;
  onCreated?: () => void;
}): boolean {
  if (!params.active) return false;
  params.closeLifecycle();
  if (params.kind === 'created') {
    try {
      params.onCreated?.();
    } finally {
      params.closeSearch();
    }
  } else if (params.restoreSearchOnCancel) {
    params.restoreSearch();
  }
  return true;
}
