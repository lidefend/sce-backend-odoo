export function resolveHierarchyTreeKeyboardAction(options: {
  key: string;
  hasChildren: boolean;
  expanded: boolean;
}): 'expand' | 'collapse' | null {
  if (!options.hasChildren) return null;
  if (options.key === 'ArrowRight' && !options.expanded) return 'expand';
  if (options.key === 'ArrowLeft' && options.expanded) return 'collapse';
  return null;
}
