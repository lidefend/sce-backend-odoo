import type { CanonicalFormAction } from '../../app/presentation/canonicalFormRenderModel';
import type { CanonicalFormFloorplan } from '../../app/presentation/canonicalFormFloorplan';
import { normalizeActionSemantics } from '@sc/schema';

export function resolveCanonicalHeaderActionPresentation(input: {
  floorplan: CanonicalFormFloorplan | null;
  actions: CanonicalFormAction[];
  renderProfile: 'create' | 'edit' | 'readonly';
  rendererActive: boolean;
  dirty: boolean;
  busy?: boolean;
  busyKind?: string;
}) {
  const meaning = (action: CanonicalFormAction) => action.actionRef.actionSemanticsInvalid
    ? undefined : (action.actionRef.actionSemantics || normalizeActionSemantics(action.actionRef));
  const visible = input.actions.filter((action) => action.visible
    && !(input.renderProfile === 'readonly' && meaning(action)?.kind === 'persistence'));
  const saves = visible.filter((action) => meaning(action)?.executor === 'record.save');
  // Editing a draft is the workspace task. A decision floorplan owns its
  // explicit primary policy; no global approval-versus-save priority exists.
  const save = !input.floorplan?.decisionMode && saves.length === 1 ? saves[0] : undefined;
  const explicit = visible.filter((action) => action.tier === 'primary'
    && !action.actionRef.actionSemanticsInvalid
    && (meaning(action)?.kind === 'business' || action.safety?.classification !== 'danger')
    && !['reject', 'cancel_record', 'return', 'discard_changes'].includes(meaning(action)?.purpose || ''));
  // Conflicting explicit primaries resolve to none, never last/first wins.
  const primary = save || (explicit.length === 1 ? explicit[0] : undefined);
  const directKeys = new Set(input.floorplan?.decisionMode
    ? input.floorplan.directActions.map((action) => action.key)
    : visible.filter((action) => ['primary', 'secondary'].includes(action.tier)).map((action) => action.key));
  if (primary) directKeys.add(primary.key);
  const adapted = visible.map((action) => ({
    ...action,
    tier: action === primary ? 'primary' as const : action.tier === 'primary' ? 'secondary' as const : action.tier,
    // Dirty is deliberately not a disabling condition: saveRecord owns no-op
    // writes and validation feedback. Busy affects execution, not emphasis.
    enabled: action.enabled && !input.busy,
    loading: input.busyKind === 'save' && meaning(action)?.executor === 'record.save',
  }));
  return {
    direct: adapted.filter((action) => directKeys.has(action.key)).sort((a, b) => Number(b.tier === 'primary') - Number(a.tier === 'primary')),
    overflow: adapted.filter((action) => !directKeys.has(action.key)),
  };
}
