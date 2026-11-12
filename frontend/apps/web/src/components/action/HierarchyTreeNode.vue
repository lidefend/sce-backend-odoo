<template>
  <div class="tree-branch" data-semantic-component="HierarchyTreeNode" :data-state="node.children.length ? 'branch' : 'leaf'">
    <ScButton
      class="tree-node"
      appearance="tree-item"
      variant="ghost"
      size="small"
      :class="{ active: selectedKey === node.key }"
      :aria-expanded="node.children.length ? String(expandedKeys.has(node.key)) : undefined"
      @click="$emit('select', node)"
      @keydown="onKeydown"
    >
      <span v-if="node.children.length" class="tree-arrow" @click.stop="$emit('toggle', node)"><ScIcon :name="expandedKeys.has(node.key) ? 'chevron-down' : 'chevron-right'" :size="14" /></span>
      <span v-else class="tree-arrow" />
      <strong v-if="node.code">{{ node.code }}</strong><span :title="node.label">{{ node.label }}</span>
    </ScButton>
    <div v-if="node.children.length && expandedKeys.has(node.key)" class="tree-children">
      <HierarchyTreeNode v-for="child in node.children" :key="child.key" :node="child" :selected-key="selectedKey" :expanded-keys="expandedKeys" :empty-children-label="emptyChildrenLabel" @select="$emit('select', $event)" @toggle="$emit('toggle', $event)" />
    </div>
  </div>
</template>
<script setup lang="ts">
import ScButton from '../design-system/ScButton.vue';
import ScIcon from '../design-system/ScIcon.vue';
import { resolveHierarchyTreeKeyboardAction } from './hierarchyTreeKeyboard';
defineOptions({ name: 'HierarchyTreeNode' });
type TreeNode = { key: string; id: number; levelKey?: string; code: string; label: string; children: TreeNode[] };
const props = defineProps<{ node: TreeNode; selectedKey: string; expandedKeys: Set<string>; emptyChildrenLabel: string }>();
const emit = defineEmits<{ select: [node: TreeNode]; toggle: [node: TreeNode] }>();

function onKeydown(event: KeyboardEvent) {
  const action = resolveHierarchyTreeKeyboardAction({
    key: event.key,
    hasChildren: props.node.children.length > 0,
    expanded: props.expandedKeys.has(props.node.key),
  });
  if (!action) return;
  event.preventDefault();
  emit('toggle', props.node);
}
</script>
<style scoped>
.tree-node {
  display: flex;
  align-items: center;
  gap: var(--sc-space-xs);
  width: 100%;
  min-height: var(--sc-touch-target-min);
  padding: var(--sc-space-xs);
  text-align: left;
}
.tree-node span:last-child { display: -webkit-box; min-width: 0; overflow: hidden; overflow-wrap: anywhere; white-space: normal; -webkit-box-orient: vertical; -webkit-line-clamp: 2; }
.tree-arrow { flex: 0 0 var(--sc-space-sm); width: var(--sc-space-sm); }
.tree-children { padding-left: var(--sc-space-md); }
</style>
