export type RelationCreateDialogState = {
  open: boolean;
  title: string;
  src: string;
  nonce: string;
  fieldName: string;
  parentModel: string;
  relationModel: string;
  restoreSearchOnCancel: boolean;
};

export type RelationCreatedDialogResult = {
  fieldName: string;
  relationModel: string;
  id: number;
  label: string;
};

export type RelationCreateDialogEvent =
  | { kind: 'cancelled' }
  | { kind: 'created'; result: RelationCreatedDialogResult };

export function closedRelationCreateDialogState(): RelationCreateDialogState {
  return {
    open: false,
    title: '',
    src: '',
    nonce: '',
    fieldName: '',
    parentModel: '',
    relationModel: '',
    restoreSearchOnCancel: false,
  };
}

export function resolveRelationCreateDialogEvent(params: {
  dialog: RelationCreateDialogState;
  eventOrigin: string;
  expectedOrigin: string;
  sourceMatches: boolean;
  payload: unknown;
}): RelationCreateDialogEvent | null {
  const dialogIdentityValid = /^[a-zA-Z0-9-]{8,128}$/.test(params.dialog.nonce)
    && /^[a-zA-Z_][a-zA-Z0-9_]*$/.test(params.dialog.fieldName)
    && /^[a-zA-Z0-9_.]+$/.test(params.dialog.parentModel)
    && /^[a-zA-Z0-9_.]+$/.test(params.dialog.relationModel);
  if (!params.dialog.open
    || !dialogIdentityValid
    || params.eventOrigin !== params.expectedOrigin
    || !params.sourceMatches
    || !params.payload
    || typeof params.payload !== 'object'
    || Array.isArray(params.payload)) return null;
  const payload = params.payload as Record<string, unknown>;
  if (String(payload.nonce || '') !== params.dialog.nonce
    || String(payload.fieldName || '') !== params.dialog.fieldName
    || String(payload.parentModel || '') !== params.dialog.parentModel
    || String(payload.relationModel || '') !== params.dialog.relationModel) return null;
  if (payload.type === 'sc.relation_record_cancelled.v1') return { kind: 'cancelled' };
  if (payload.type !== 'sc.relation_record_created.v1') return null;
  const id = Number(payload.id || 0);
  if (!Number.isFinite(id) || id <= 0) return null;
  return {
    kind: 'created',
    result: {
      fieldName: params.dialog.fieldName,
      relationModel: params.dialog.relationModel,
      id: Math.trunc(id),
      label: String(payload.label || '').trim() || `记录 ${Math.trunc(id)}`,
    },
  };
}

export function settleRelationCreateDialog(params: {
  dialog: RelationCreateDialogState;
  kind: RelationCreateDialogEvent['kind'];
  restoreSearch: () => void;
  closeSearch: () => void;
  onCreated?: () => void;
}): boolean {
  if (!params.dialog.open) return false;
  const restoreSearch = params.dialog.restoreSearchOnCancel;
  Object.assign(params.dialog, closedRelationCreateDialogState());
  if (params.kind === 'created') {
    try {
      params.onCreated?.();
    } finally {
      params.closeSearch();
    }
  } else if (restoreSearch) {
    params.restoreSearch();
  }
  return true;
}
