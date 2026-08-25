import type { CanonicalFormAction } from '../../app/presentation/canonicalFormRenderModel';
import type { CanonicalFormFloorplan } from '../../app/presentation/canonicalFormFloorplan';

export function resolveCanonicalHeaderActionPresentation(input: {
  floorplan: CanonicalFormFloorplan | null;
  actions: CanonicalFormAction[];
  renderProfile: 'create' | 'edit' | 'readonly';
  rendererActive: boolean;
  dirty: boolean;
}) {
  const visible = input.actions.filter((action) => action.visible);
  const authorizedLocalSave = visible.find((action) => action.actionRef.actionId === 'form.save');
  const localSavePrimary = Boolean(
    input.rendererActive
    && (input.renderProfile === 'create' || input.renderProfile === 'edit')
    && authorizedLocalSave?.enabled,
  );
  const withoutLocalSave = (actions: CanonicalFormAction[]) => localSavePrimary
    ? actions.filter((action) => action.actionRef.actionId !== 'form.save')
    : actions;
  return {
    direct: withoutLocalSave(input.floorplan?.decisionMode
      ? input.floorplan.directActions
      : visible.filter((action) => ['primary', 'secondary'].includes(action.tier))),
    overflow: withoutLocalSave(input.floorplan?.decisionMode
      ? input.floorplan.overflowActions
      : visible.filter((action) => ['overflow', 'configuration'].includes(action.tier))),
    localSavePrimary,
  };
}
