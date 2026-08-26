<template>
  <nav class="product-side-navigation" aria-label="业务导航" data-semantic-component="ProductSideNavigation">
    <label class="product-side-navigation__search">
      <span class="sr-only">搜索菜单</span>
      <ScInput
        :model-value="search"
        type="search"
        placeholder="搜索菜单..."
        aria-label="搜索菜单"
        clearable
        appearance="navigation-search"
        @update:model-value="emit('update:search', String($event))"
      >
        <template #prefix><ScIcon name="search" :size="16" /></template>
      </ScInput>
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

.product-side-navigation__search :deep(.sc-input) { width: 100%; }

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
