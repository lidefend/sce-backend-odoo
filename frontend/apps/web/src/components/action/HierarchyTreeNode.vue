<template>
  <div class="tree-branch" data-semantic-component="HierarchyTreeNode" :data-state="node.children.length ? 'branch' : 'leaf'">
    <button class="tree-node" :class="{ active: selectedKey === node.key }" @click="$emit('select', node)">
      <span v-if="node.children.length" class="tree-arrow" @click.stop="$emit('toggle', node)">{{ expandedKeys.has(node.key) ? '▾' : '▸' }}</span>
      <span v-else class="tree-arrow" />
      <strong v-if="node.code">{{ node.code }}</strong><span>{{ node.label }}</span>
    </button>
    <div v-if="node.children.length && expandedKeys.has(node.key)" class="tree-children">
      <HierarchyTreeNode v-for="child in node.children" :key="child.key" :node="child" :selected-key="selectedKey" :expanded-keys="expandedKeys" :empty-children-label="emptyChildrenLabel" @select="$emit('select', $event)" @toggle="$emit('toggle', $event)" />
    </div>
  </div>
</template>
<script setup lang="ts">
defineOptions({ name: 'HierarchyTreeNode' });
type TreeNode = { key: string; id: number; levelKey?: string; code: string; label: string; children: TreeNode[] };
defineProps<{ node: TreeNode; selectedKey: string; expandedKeys: Set<string>; emptyChildrenLabel: string }>();
defineEmits<{ select: [node: TreeNode]; toggle: [node: TreeNode] }>();
</script>
<style scoped>
.tree-node {
  display: flex;
  align-items: center;
  gap: var(--sc-space-xs);
  width: 100%;
  min-height: var(--sc-touch-target-min);
  padding: var(--sc-space-xs);
  border: 0;
  border-radius: var(--sc-product-radius-control);
  background: transparent;
  color: var(--sc-app-text-primary);
  text-align: left;
  cursor: pointer;
}
.tree-node span:last-child { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tree-node:hover { background: var(--sc-app-hover-bg); }
.tree-node.active { background: var(--sc-app-selected-bg); color: var(--sc-app-selected-text); }
.tree-arrow { flex: 0 0 var(--sc-space-sm); width: var(--sc-space-sm); }
.tree-children { padding-left: var(--sc-space-md); }
</style>
