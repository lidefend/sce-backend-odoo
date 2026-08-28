import type { CanonicalFormAction } from '../../app/presentation/canonicalFormRenderModel';
import type { CanonicalFormFloorplan } from '../../app/presentation/canonicalFormFloorplan';

export function resolveCanonicalHeaderActionPresentation(input: {
  floorplan: CanonicalFormFloorplan | null;
  actions: CanonicalFormAction[];
  renderProfile: 'create' | 'edit' | 'readonly';
  rendererActive: boolean;
  dirty: boolean;
}) {
  // 严格按契约渲染：主操作区 = 契约声明的 primary + secondary（保存修改/保存草稿
  // 在契约中为 secondary），overflow = 契约声明的 overflow + configuration。
  // 前端不再发明「保存修改顶替 primary、挤走产品工作流按钮」的 localSave 编排。
  const visible = input.actions.filter((action) => action.visible);
  return {
    direct: input.floorplan?.decisionMode
      ? input.floorplan.directActions
      : visible.filter((action) => ['primary', 'secondary'].includes(action.tier)),
    overflow: input.floorplan?.decisionMode
      ? input.floorplan.overflowActions
      : visible.filter((action) => ['overflow', 'configuration'].includes(action.tier)),
  };
}
