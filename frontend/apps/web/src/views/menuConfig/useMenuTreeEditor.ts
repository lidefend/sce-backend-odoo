import type { Ref } from 'vue';
import type { MenuConfigMenu } from '../../api/menuConfig';
import type { MenuConfigDropPosition as DropPosition, MenuConfigDropRequest } from './menuTreeContract';

type EditableDraft = { target_parent_menu_id: number; sequence_override: number };

export function useMenuTreeEditor(options: {
  selectedMenuId: Ref<number>;
  collapsedMenuIds: Ref<Set<number>>;
  treeDragEnabled: Readonly<Ref<boolean>>;
  tree: Ref<MenuConfigMenu[]>;
  message: Ref<string>;
  selectedMenuPath: (items: MenuConfigMenu[], menuId: number) => Set<number>;
  menuById: (menuId: number) => MenuConfigMenu | null;
  treeMenuById: (menuId: number) => MenuConfigMenu | null;
  isRuntimeMenuGroup: (menu: MenuConfigMenu | null | undefined) => boolean;
  parentOptionIds: (menuId: number) => Set<number>;
  draftFor: (menuId: number) => EditableDraft | undefined;
  setSaveNotice: (value: string) => void;
}) {
  const {
    selectedMenuId,
    collapsedMenuIds,
    treeDragEnabled,
    tree,
    message,
  } = options;
  const {
    selectedMenuPath,
    menuById,
    treeMenuById,
    isRuntimeMenuGroup,
    parentOptionIds,
    draftFor,
    setSaveNotice,
  } = options;
  function initializeTreeCollapse(items: MenuConfigMenu[]) {
    const selectedPath = selectedMenuPath(items, selectedMenuId.value);
    const next = new Set<number>();
    const walk = (rows: MenuConfigMenu[]) => {
      rows.forEach((item) => {
        if (item.children?.length) {
          if (!selectedPath.has(item.id)) next.add(item.id);
          walk(item.children);
        }
      });
    };
    walk(items);
    collapsedMenuIds.value = next;
  }

  function toggleTreeNodeCollapse(menuId: number) {
    const next = new Set(collapsedMenuIds.value);
    if (next.has(menuId)) next.delete(menuId);
    else next.add(menuId);
    collapsedMenuIds.value = next;
  }

  // The official tree asks the editor whether a drop is allowed; the business
  // rules stay here instead of in a bespoke drag implementation.
  function canDropTree(request: MenuConfigDropRequest): boolean {
    const sourceId = Number(request.sourceId || 0);
    const targetId = Number(request.targetId || 0);
    if (!treeDragEnabled.value) return false;
    if (!sourceId || !targetId || sourceId === targetId) return false;
    if (isRuntimeMenuGroup(treeMenuById(sourceId))) return false;
    if (areVisualSiblings(tree.value, sourceId, targetId)) return true;
    const allowedParentIds = parentOptionIds(sourceId);
    if (request.position === 'inside') return allowedParentIds.has(targetId);
    const targetMenu = menuById(targetId);
    return Boolean(targetMenu && allowedParentIds.has(Number(targetMenu.parent_id || 0)));
  }

  function resequenceBranch(items: MenuConfigMenu[]) {
    return items.map((item, index) => {
      const draft = draftFor(item.id);
      if (draft) {
        draft.sequence_override = (index + 1) * 10;
      }
      return item;
    });
  }

  function reorderSiblingBranch(items: MenuConfigMenu[], sourceId: number, targetId: number, position: DropPosition): MenuConfigMenu[] {
    const ids = items.map((item) => item.id);
    if (ids.includes(sourceId) && ids.includes(targetId)) {
      const source = items.find((item) => item.id === sourceId);
      if (!source) return items;
      const next = items.filter((item) => item.id !== sourceId);
      const targetIndex = next.findIndex((item) => item.id === targetId);
      if (targetIndex < 0) return items;
      next.splice(position === 'before' ? targetIndex : targetIndex + 1, 0, source);
      return resequenceBranch(next);
    }

    return items.map((item) => {
      if (!item.children?.length) return item;
      return { ...item, children: reorderSiblingBranch(item.children, sourceId, targetId, position) };
    });
  }

  function removeTreeNode(items: MenuConfigMenu[], sourceId: number): { rows: MenuConfigMenu[]; removed: MenuConfigMenu | null } {
    let removed: MenuConfigMenu | null = null;
    const rows = items.flatMap((item) => {
      if (Number(item.id) === Number(sourceId)) {
        removed = item;
        return [];
      }
      if (!item.children?.length) return [item];
      const result = removeTreeNode(item.children, sourceId);
      if (result.removed) {
        removed = result.removed;
        return [{ ...item, children: resequenceBranch(result.rows) }];
      }
      return [item];
    });
    return { rows, removed };
  }

  function insertTreeNodeInside(items: MenuConfigMenu[], parentId: number, source: MenuConfigMenu): { rows: MenuConfigMenu[]; inserted: boolean } {
    let inserted = false;
    const rows = items.map((item) => {
      if (Number(item.id) === Number(parentId)) {
        inserted = true;
        const nextChild = { ...source, parent_id: parentId, parent_name: item.complete_name || item.name };
        const children = resequenceBranch([...(item.children || []), nextChild]);
        return { ...item, children };
      }
      if (!item.children?.length) return item;
      const result = insertTreeNodeInside(item.children, parentId, source);
      inserted = inserted || result.inserted;
      return result.inserted ? { ...item, children: result.rows } : item;
    });
    return { rows, inserted };
  }

  function moveTreeNodeToParent(sourceId: number, parentId: number): boolean {
    if (!sourceId || !parentId || sourceId === parentId || !parentOptionIds(sourceId).has(parentId)) return false;
    const result = removeTreeNode(tree.value, sourceId);
    if (!result.removed) return false;
    const inserted = insertTreeNodeInside(result.rows, parentId, result.removed);
    if (!inserted.inserted) return false;
    const draft = draftFor(sourceId);
    if (draft) {
      draft.target_parent_menu_id = parentId;
    }
    tree.value = inserted.rows;
    setSaveNotice('');
    return true;
  }

  function insertTreeNodeRelative(
    items: MenuConfigMenu[],
    source: MenuConfigMenu,
    targetId: number,
    parentId: number,
    position: Exclude<DropPosition, 'inside'>,
  ): { rows: MenuConfigMenu[]; inserted: boolean } {
    const ids = items.map((item) => Number(item.id));
    if (ids.includes(Number(targetId))) {
      const target = items.find((item) => Number(item.id) === Number(targetId));
      const nextSource = { ...source, parent_id: parentId, parent_name: target?.parent_name || source.parent_name };
      const withoutSource = items.filter((item) => Number(item.id) !== Number(source.id));
      const targetIndex = withoutSource.findIndex((item) => Number(item.id) === Number(targetId));
      if (targetIndex < 0) return { rows: items, inserted: false };
      withoutSource.splice(position === 'before' ? targetIndex : targetIndex + 1, 0, nextSource);
      return { rows: resequenceBranch(withoutSource), inserted: true };
    }
    let inserted = false;
    const rows = items.map((item) => {
      if (!item.children?.length) return item;
      const result = insertTreeNodeRelative(item.children, source, targetId, parentId, position);
      inserted = inserted || result.inserted;
      return result.inserted ? { ...item, children: result.rows } : item;
    });
    return { rows, inserted };
  }

  function moveTreeNodeRelative(sourceId: number, targetId: number, position: Exclude<DropPosition, 'inside'>): boolean {
    if (!sourceId || !targetId || sourceId === targetId) return false;
    const target = menuById(targetId);
    const parentId = Number(target?.parent_id || 0);
    if (!target || !parentId || !parentOptionIds(sourceId).has(parentId)) return false;
    const result = removeTreeNode(tree.value, sourceId);
    if (!result.removed) return false;
    const inserted = insertTreeNodeRelative(result.rows, result.removed, targetId, parentId, position);
    if (!inserted.inserted) return false;
    const draft = draftFor(sourceId);
    if (draft) {
      draft.target_parent_menu_id = parentId;
    }
    tree.value = inserted.rows;
    setSaveNotice('');
    return true;
  }

  function applyTreeReorder(payload: { sourceId: number; targetId: number; position: DropPosition }) {
    if (!payload.sourceId || !payload.targetId || payload.sourceId === payload.targetId) return;
    if (!areVisualSiblings(tree.value, payload.sourceId, payload.targetId)) {
      const moved = payload.position === 'inside'
        ? moveTreeNodeToParent(payload.sourceId, payload.targetId)
        : moveTreeNodeRelative(payload.sourceId, payload.targetId, payload.position);
      if (moved) {
        message.value = '';
        setSaveNotice('');
      }
      return;
    }
    tree.value = reorderSiblingBranch(tree.value, payload.sourceId, payload.targetId, payload.position);
    message.value = '';
    setSaveNotice('');
  }

  function areVisualSiblings(items: MenuConfigMenu[], sourceId: number, targetId: number): boolean {
    const ids = items.map((item) => item.id);
    if (ids.includes(sourceId) && ids.includes(targetId)) return true;
    return items.some((item) => item.children?.length && areVisualSiblings(item.children, sourceId, targetId));
  }
  return {
    initializeTreeCollapse,
    toggleTreeNodeCollapse,
    canDropTree,
    applyTreeReorder,
  };
}
