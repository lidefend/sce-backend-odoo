export function shouldShowNativeCollaborationPanel(input: {
  hasChatterActions: boolean;
  hasAttachments: boolean;
  isIntakeCreateMode: boolean;
  collaborationSuppressed?: boolean;
}) {
  // 派发型临时上下文工作台自身没有协作能力：上下文只用于本次派发，沟通、备注与附件
  // 属于打开的正式单据。合同通过 form_governance.create_flow_mode 声明后，这些入口
  // 不渲染协作章节，正式单据的协作能力不受影响。
  if (input.collaborationSuppressed) return false;
  // 系统级统一：只要模型支持协作（消息或附件），就显示协作日志面板
  // 创建模式下保留面板，但消息/活动功能因无 recordId 自动禁用
  // hasChatterActions 依赖后端契约的 chatterActions 列表，可能为空但模型仍支持消息
  // hasAttachments 依赖后端契约的 attachments 数据，可能为空但模型仍支持附件
  // 因此只要任一为 true 就显示；未来可通过模型元数据精确判断
  return input.hasChatterActions || input.hasAttachments || !input.isIntakeCreateMode;
}
