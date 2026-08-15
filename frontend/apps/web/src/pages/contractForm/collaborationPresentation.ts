export function shouldShowNativeCollaborationPanel(input: {
  hasChatterActions: boolean;
  hasAttachments: boolean;
  isIntakeCreateMode: boolean;
}) {
  return input.hasAttachments || (input.hasChatterActions && !input.isIntakeCreateMode);
}
