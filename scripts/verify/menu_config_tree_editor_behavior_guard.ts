#!/usr/bin/env node
import * as assert from 'assert/strict';
import { useMenuTreeEditor } from '../../frontend/apps/web/src/views/menuConfig/useMenuTreeEditor';
import type { MenuConfigMenu } from '../../frontend/apps/web/src/api/menuConfig';
import { menuDropPosition, menuTreeExpandedIds } from '../../frontend/apps/web/src/views/menuConfig/menuTreeContract';

type Box<T> = { value: T };

function box<T>(value: T): Box<T> {
  return { value };
}

function menu(id: number, parentId: number, runtimeGroup = false): MenuConfigMenu {
  return {
    id,
    menu_id: id,
    name: `menu-${id}`,
    display_name: `menu-${id}`,
    complete_name: `menu-${id}`,
    parent_id: parentId,
    parent_name: `parent-${parentId}`,
    sequence: id * 10,
    action: '',
    web_icon: '',
    xmlid: '',
    group_ids: [],
    group_names: [],
    children: [],
    ...(runtimeGroup ? { runtime_group: true } : {}),
  } as MenuConfigMenu;
}

type Draft = { target_parent_menu_id: number; sequence_override: number };

function createHarness(options: { enabled: boolean; allowedParentIds?: number[] }) {
  const root = menu(2, 1);
  const sibling = menu(3, 1);
  const child = menu(4, 2);
  const runtimeGroup = menu(5, 1, true);
  root.children = [child];
  const tree = box<MenuConfigMenu[]>([root, sibling, runtimeGroup]);
  const drafts: Record<number, Draft> = {
    2: { target_parent_menu_id: 1, sequence_override: 10 },
    3: { target_parent_menu_id: 1, sequence_override: 20 },
    5: { target_parent_menu_id: 1, sequence_override: 30 },
  };
  const allowedParentIds = new Set<number>(options.allowedParentIds ?? [1]);
  const editor = useMenuTreeEditor({
    selectedMenuId: box(0) as any,
    collapsedMenuIds: box(new Set<number>()) as any,
    treeDragEnabled: box(options.enabled) as any,
    tree: tree as any,
    message: box('') as any,
    selectedMenuPath: () => new Set<number>(),
    menuById: (menuId) => findMenu(tree.value, menuId),
    treeMenuById: (menuId) => findMenu(tree.value, menuId),
    isRuntimeMenuGroup: (item) => Boolean((item as MenuConfigMenu & { runtime_group?: boolean } | null)?.runtime_group),
    parentOptionIds: () => allowedParentIds,
    draftFor: (menuId) => drafts[menuId],
    setSaveNotice: () => undefined,
  });
  return { editor, tree, drafts };
}

function findMenu(items: MenuConfigMenu[], menuId: number): MenuConfigMenu | null {
  for (const item of items) {
    if (Number(item.id) === Number(menuId)) return item;
    const found = findMenu(item.children || [], menuId);
    if (found) return found;
  }
  return null;
}

/** A visual sibling may be reordered while drag is enabled. */
function assertEnabledDragAllowsSiblingReorder() {
  const harness = createHarness({ enabled: true });
  assert.equal(harness.editor.canDropTree({ sourceId: 2, targetId: 3, position: 'after' }), true);
  assert.equal(harness.editor.canDropTree({ sourceId: 2, targetId: 3, position: 'before' }), true);
}

/** Disabling drag (search active) must reject every drop. */
function assertDisabledDragAllowsNoDrop() {
  const harness = createHarness({ enabled: false });
  assert.equal(harness.editor.canDropTree({ sourceId: 2, targetId: 3, position: 'after' }), false);
  assert.equal(harness.editor.canDropTree({ sourceId: 4, targetId: 2, position: 'inside' }), false);
}

/** Runtime navigation groups are never a drag source. */
function assertRuntimeGroupCannotBeDragged() {
  const harness = createHarness({ enabled: true });
  assert.equal(harness.editor.canDropTree({ sourceId: 5, targetId: 2, position: 'after' }), false);
  assert.equal(harness.editor.canDropTree({ sourceId: 5, targetId: 2, position: 'inside' }), false);
}

/** A node can never be dropped onto itself. */
function assertSelfDropRejected() {
  const harness = createHarness({ enabled: true });
  assert.equal(harness.editor.canDropTree({ sourceId: 2, targetId: 2, position: 'after' }), false);
}

/** Cross-parent moves stay limited to the declared legal parents of the source. */
function assertCrossParentDropRequiresAllowedParent() {
  const childScope = createHarness({ enabled: true, allowedParentIds: [2] });
  assert.equal(childScope.editor.canDropTree({ sourceId: 4, targetId: 2, position: 'inside' }), true);
  assert.equal(childScope.editor.canDropTree({ sourceId: 4, targetId: 3, position: 'inside' }), false);
  assert.equal(childScope.editor.canDropTree({ sourceId: 4, targetId: 3, position: 'after' }), false);

  const rootScope = createHarness({ enabled: true, allowedParentIds: [1] });
  assert.equal(rootScope.editor.canDropTree({ sourceId: 2, targetId: 4, position: 'after' }), false);
}

/** The accepted drop still moves the branch and resequences the affected drafts. */
function assertAcceptedDropMovesBranchAndDrafts() {
  const harness = createHarness({ enabled: true });
  harness.editor.applyTreeReorder({ sourceId: 3, targetId: 2, position: 'before' });
  assert.deepEqual(harness.tree.value.map((item) => item.id), [3, 2, 5]);
  assert.equal(harness.drafts[3].sequence_override, 10);
  assert.equal(harness.drafts[2].sequence_override, 20);
  assert.equal(harness.drafts[5].sequence_override, 30);
}

/** Official drop positions map onto the editor's business vocabulary. */
function assertOfficialDropPositionMapping() {
  assert.equal(menuDropPosition(-1), 'before');
  assert.equal(menuDropPosition(0), 'inside');
  assert.equal(menuDropPosition(1), 'after');
}

/** Expansion handed to the official tree follows the editor's collapsed set. */
function assertExpansionFollowsCollapsedSet() {
  const root = menu(2, 1);
  root.children = [menu(4, 2)];
  assert.deepEqual(menuTreeExpandedIds([root], new Set<number>()), [2]);
  assert.deepEqual(menuTreeExpandedIds([root], new Set<number>([2])), []);
}

assertEnabledDragAllowsSiblingReorder();
assertDisabledDragAllowsNoDrop();
assertRuntimeGroupCannotBeDragged();
assertSelfDropRejected();
assertCrossParentDropRequiresAllowedParent();
assertAcceptedDropMovesBranchAndDrafts();
assertOfficialDropPositionMapping();
assertExpansionFollowsCollapsedSet();
function assertSiblingInsideMovesParent() {
  const h = createHarness({ enabled: true, allowedParentIds: [1, 3] });
  const drop = { sourceId: 2, targetId: 3, position: menuDropPosition(0) };
  assert.equal(h.editor.canDropTree(drop), true);
  h.editor.applyTreeReorder(drop);
  assert.deepEqual(h.tree.value.map(row => row.id), [3, 5]);
  assert.equal(findMenu(h.tree.value, 3)?.children?.[0]?.id, 2);
  assert.equal(findMenu(h.tree.value, 2)?.parent_id, 3);
  assert.equal(findMenu(h.tree.value, 2)?.children?.[0]?.id, 4);
  assert.equal(h.drafts[2].target_parent_menu_id, 3);
}
function assertRejectedDropDoesNotMutate() {
  for (const options of [{ enabled: true }, { enabled: false, allowedParentIds: [3] }]) {
    const h = createHarness(options);
    const before = JSON.stringify({ tree: h.tree.value, drafts: h.drafts });
    const drop = { sourceId: 2, targetId: 3, position: 'inside' as const };
    assert.equal(h.editor.canDropTree(drop), false);
    h.editor.applyTreeReorder(drop);
    assert.equal(JSON.stringify({ tree: h.tree.value, drafts: h.drafts }), before);
  }
}
function assertSiblingAfterStillReorders() {
  const h = createHarness({ enabled: true });
  h.editor.applyTreeReorder({ sourceId: 2, targetId: 3, position: 'after' });
  assert.deepEqual(h.tree.value.map(row => row.id), [3, 2, 5]);
  assert.equal(h.drafts[2].target_parent_menu_id, 1);
}
assertSiblingInsideMovesParent();
assertRejectedDropDoesNotMutate();
assertSiblingAfterStillReorders();
console.log('[menu_config_tree_editor_behavior_guard] PASS cases=11');
