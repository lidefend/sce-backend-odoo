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

export type RelationCreateDialogEvent = ProfessionalRelationLifecycleEvent;

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
  return resolveProfessionalRelationLifecycleEvent({
    active: params.dialog.open,
    context: params.dialog,
    eventOrigin: params.eventOrigin,
    expectedOrigin: params.expectedOrigin,
    sourceMatches: params.sourceMatches,
    payload: params.payload,
  });
}

export function settleRelationCreateDialog(params: {
  dialog: RelationCreateDialogState;
  kind: RelationCreateDialogEvent['kind'];
  restoreSearch: () => void;
  closeSearch: () => void;
  onCreated?: () => void;
}): boolean {
  return settleProfessionalRelationLifecycle({
    active: params.dialog.open,
    closeLifecycle: () => Object.assign(params.dialog, closedRelationCreateDialogState()),
    kind: params.kind,
    restoreSearchOnCancel: params.dialog.restoreSearchOnCancel,
    restoreSearch: params.restoreSearch,
    closeSearch: params.closeSearch,
    onCreated: params.onCreated,
  });
}
import {
  resolveProfessionalRelationLifecycleEvent,
  settleProfessionalRelationLifecycle,
  type ProfessionalRelationLifecycleEvent,
} from './professionalRelationLifecycleModel';
