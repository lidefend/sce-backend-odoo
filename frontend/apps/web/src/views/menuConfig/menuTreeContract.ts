import type { MenuConfigMenu } from '../../api/menuConfig';

export type MenuConfigDropPosition = 'before' | 'after' | 'inside';

export type MenuConfigDropRequest = {
  sourceId: number;
  targetId: number;
  position: MenuConfigDropPosition;
};

/** TDesign reports the drop position as -1 (above), 0 (inside) or 1 (below). */
export function menuDropPosition(position: number): MenuConfigDropPosition {
  if (Number(position) === 0) return 'inside';
  return Number(position) < 0 ? 'before' : 'after';
}

/** Official tree expansion is derived from the collapsed set the editor owns. */
export function menuTreeExpandedIds(nodes: MenuConfigMenu[], collapsedMenuIds: Set<number>): number[] {
  const expanded: number[] = [];
  const walk = (rows: MenuConfigMenu[]) => {
    rows.forEach((row) => {
      if (!row.children?.length) return;
      if (!collapsedMenuIds.has(Number(row.id))) expanded.push(Number(row.id));
      walk(row.children);
    });
  };
  walk(nodes);
  return expanded;
}
