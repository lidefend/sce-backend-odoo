export type WorkflowReasonKeyboardEvent = Pick<
  KeyboardEvent,
  'key' | 'target' | 'currentTarget' | 'preventDefault'
>;

/**
 * A disabled native button cannot own focus. A focusable denial trigger wraps it
 * and forwards Enter/Space to the existing ScPopover click activation. Only the
 * trigger itself may activate the explanation, never a bubbled key from a child.
 */
export function activateWorkflowReasonTrigger(event: WorkflowReasonKeyboardEvent): void {
  if (event.currentTarget !== event.target) return;
  if (event.key !== 'Enter' && event.key !== ' ') return;
  event.preventDefault();
  (event.currentTarget as HTMLElement | null)?.click();
}
