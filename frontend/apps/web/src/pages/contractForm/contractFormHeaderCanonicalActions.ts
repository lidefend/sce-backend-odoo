import type { CanonicalFormAction } from '../../app/presentation/canonicalFormRenderModel';
import type { CanonicalFormFloorplan } from '../../app/presentation/canonicalFormFloorplan';

export function resolveCanonicalHeaderActionPresentation(input: {
  floorplan: CanonicalFormFloorplan | null;
  actions: CanonicalFormAction[];
  renderProfile: 'create' | 'edit' | 'readonly';
  rendererActive: boolean;
}) {
  const visible = input.actions.filter((action) => action.visible);
  return {
    direct: input.floorplan?.decisionMode ? input.floorplan.directActions : visible.filter((action) => ['primary', 'secondary'].includes(action.tier)),
    overflow: input.floorplan?.decisionMode ? input.floorplan.overflowActions : visible.filter((action) => ['overflow', 'configuration'].includes(action.tier)),
    localSavePrimary: input.rendererActive && ['create', 'edit'].includes(input.renderProfile),
  };
}
