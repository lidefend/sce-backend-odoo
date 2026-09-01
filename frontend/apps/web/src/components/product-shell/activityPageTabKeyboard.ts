export function resolveActivityTabKeyboardIndex(input: {
  key: string;
  currentIndex: number;
  count: number;
}): number | null {
  if (input.count <= 0 || input.currentIndex < 0 || input.currentIndex >= input.count) return null;
  if (input.key === 'Home') return 0;
  if (input.key === 'End') return input.count - 1;
  if (input.key === 'ArrowLeft') return (input.currentIndex - 1 + input.count) % input.count;
  if (input.key === 'ArrowRight') return (input.currentIndex + 1) % input.count;
  return null;
}

export function shouldShowActivityPageTabs(pageCount: number): boolean {
  return Number.isFinite(pageCount) && pageCount > 0;
}
