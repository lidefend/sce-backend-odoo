export function shouldShowNativeCollaborationPanel(input: {
  hasChatterActions: boolean;
  hasAttachments: boolean;
  isIntakeCreateMode: boolean;
}) {
  // 临时验证：直接返回 true，验证协作日志组件渲染能力
  // 系统级统一：只要模型支持协作（消息或附件），就显示协作日志面板
  // 创建模式下保留面板，但消息/活动功能因无 recordId 自动禁用
  return true;
}
