<template>
  <nav class="product-side-navigation" aria-label="业务导航" data-semantic-component="ProductSideNavigation">
    <label class="product-side-navigation__search">
      <span class="sr-only">搜索菜单</span>
      <ScIcon name="search" :size="16" />
      <ScInput
        :model-value="search"
        type="search"
        placeholder="搜索菜单..."
        aria-label="搜索菜单"
        @update:model-value="emit('update:search', String($event))"
      />
    </label>
    <div class="product-side-navigation__tree">
      <MenuTree
        :nodes="nodes"
        :active-menu-id="activeMenuId"
        :expanded-keys="expandedKeys"
        :search-active="Boolean(search.trim())"
        @select="emit('select', $event)"
        @toggle="emit('toggle', $event)"
        @ensure-expanded="emit('ensure-expanded', $event)"
      />
    </div>
  </nav>
</template>

<script setup lang="ts">
import type { CanonicalNavigationNode } from '@sc/schema';
import MenuTree from '../MenuTree.vue';
import ScIcon from '../design-system/ScIcon.vue';
import ScInput from '../design-system/ScInput.vue';

withDefaults(defineProps<{
  nodes: CanonicalNavigationNode[];
  activeMenuId?: number;
  expandedKeys?: string[];
  search: string;
}>(), {
  activeMenuId: undefined,
  expandedKeys: () => [],
});

const emit = defineEmits<{
  (event: 'select', node: CanonicalNavigationNode): void;
  (event: 'toggle', key: string): void;
  (event: 'ensure-expanded', keys: string[]): void;
  (event: 'update:search', value: string): void;
}>();
</script>

<style scoped>
.product-side-navigation {
  display: grid;
  grid-template-rows: max-content minmax(0, 1fr);
  gap: var(--sc-nav-row-gap);
  min-height: 0;
}

.product-side-navigation__search {
  position: relative;
  display: flex;
  align-items: center;
}

.product-side-navigation__search > .sc-icon {
  position: absolute;
  z-index: var(--sc-component-shell-navigation-search-icon-z-index);
  left: 11px;
  color: var(--sc-app-text-muted);
  pointer-events: none;
}

.product-side-navigation__search :deep(.sc-input) {
  width: 100%;
  min-height: 38px;
  padding-left: 34px;
  border-color: var(--sc-app-border);
  border-radius: var(--sc-component-input-radius);
  background: color-mix(in srgb, var(--sc-app-panel) 86%, transparent);
  box-shadow: inset 0 1px 2px color-mix(in srgb, var(--sc-app-shadow) 6%, transparent);
  transition:
    border-color var(--sc-motion-fast) ease,
    box-shadow var(--sc-motion-fast) ease,
    background-color var(--sc-motion-fast) ease;
}

.product-side-navigation__search :deep(.sc-input:hover) {
  border-color: var(--sc-app-border-strong);
  background: var(--sc-app-panel);
}

.product-side-navigation__search :deep(.sc-input:focus) {
  border-color: var(--sc-semantic-surface-interactive);
  outline: 3px solid var(--sc-app-focus-ring);
  outline-offset: 0;
  background: var(--sc-app-panel);
}

.product-side-navigation__tree {
  min-height: 0;
  overflow: auto;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
</style>
