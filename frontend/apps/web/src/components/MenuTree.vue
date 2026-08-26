<template>
  <TDesignMenu
    class="sc-navigation-menu"
    data-semantic-component="MenuTree"
    data-semantic-driver="tdesign-menu"
    :data-state="nodes.length ? 'ready' : 'empty'"
    theme="light"
    expand-type="normal"
    :expand-mutex="false"
    :value="activeKey"
    :expanded="effectiveExpandedKeys"
    @change="onChange"
    @expand="onExpand"
  >
    <CanonicalNavigationMenuNode
      v-for="node in nodes"
      :key="node.key"
      :node="node"
      :depth="0"
    />
  </TDesignMenu>
</template>

<script setup lang="ts">
import { computed, provide, watchEffect } from 'vue';
import type { CanonicalNavigationNode } from '@sc/schema';
import { TDesignMenu } from './design-system/tdesignPrimitiveBridge';
import CanonicalNavigationMenuNode from './product-shell/CanonicalNavigationMenuNode.vue';

const props = withDefaults(defineProps<{
  nodes: CanonicalNavigationNode[];
  activeMenuId?: number;
  expandedKeys?: string[];
  searchActive?: boolean;
}>(), {
  activeMenuId: undefined,
  expandedKeys: () => [],
  searchActive: false,
});

const emit = defineEmits<{
  (event: 'select', node: CanonicalNavigationNode): void;
  (event: 'toggle', key: string): void;
  (event: 'ensure-expanded', keys: string[]): void;
}>();

const flatNodes = computed(() => flatten(props.nodes));
const nodeByKey = computed(() => new Map(flatNodes.value.map((node) => [node.key, node])));
const activeNode = computed(() => flatNodes.value.find((node) => node.menuId === props.activeMenuId));
const activeKey = computed(() => activeNode.value?.key || '');
const effectiveExpandedKeys = computed(() => props.searchActive
  ? flatNodes.value.filter((node) => node.children.length).map((node) => node.key)
  : props.expandedKeys);

provide('canonical-navigation-active-key', activeKey);

function flatten(nodes: CanonicalNavigationNode[]): CanonicalNavigationNode[] {
  return nodes.flatMap((node) => [node, ...flatten(node.children)]);
}

function onChange(value: string | number) {
  const node = nodeByKey.value.get(String(value));
  if (node && node.state !== 'disabled' && node.state !== 'container') emit('select', node);
}

function onExpand(values: Array<string | number>) {
  if (props.searchActive) return;
  const previous = new Set(props.expandedKeys);
  const next = new Set(values.map(String));
  for (const key of new Set([...previous, ...next])) {
    if (previous.has(key) !== next.has(key)) emit('toggle', key);
  }
}

watchEffect(() => {
  const required = new Set<string>();
  for (const parent of activeNode.value?.parentChain || []) required.add(parent.key);
  for (const node of flatNodes.value) {
    if (node.children.length && node.source.meta?.default_expanded === true) required.add(node.key);
  }
  const expanded = new Set(props.expandedKeys);
  const missing = [...required].filter((key) => !expanded.has(key));
  if (missing.length) emit('ensure-expanded', missing);
});
</script>

<style scoped>
.sc-navigation-menu {
  width: 100%;
  min-width: 0;
  border-right: 0;
  background: transparent;
}

.sc-navigation-menu :deep(.t-menu__item),
.sc-navigation-menu :deep(.t-submenu__title) {
  min-height: var(--sc-shell-navigation-item-height);
  margin: 1px 0;
  border-radius: var(--sc-product-radius-control);
}

.sc-navigation-menu :deep(.t-menu__item.t-is-active) {
  color: var(--sc-app-accent);
  background: var(--sc-app-accent-soft);
}

.sc-navigation-menu :deep(.t-menu__item:hover),
.sc-navigation-menu :deep(.t-submenu__title:hover) {
  background: var(--sc-app-hover-bg);
}

</style>
