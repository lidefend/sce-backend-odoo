export type ModalKeyboardAction = 'none' | 'close' | 'focus-surface' | 'focus-first' | 'focus-last';

export function resolveModalKeyboardAction(input: {
  key: string;
  shiftKey: boolean;
  focusableCount: number;
  activeIndex: number;
  surfaceActive: boolean;
}): ModalKeyboardAction {
  if (input.key === 'Escape') return 'close';
  if (input.key !== 'Tab') return 'none';
  if (input.focusableCount === 0) return 'focus-surface';
  if (input.shiftKey && (input.activeIndex === 0 || input.surfaceActive)) return 'focus-last';
  if (!input.shiftKey && input.activeIndex === input.focusableCount - 1) return 'focus-first';
  return 'none';
}
