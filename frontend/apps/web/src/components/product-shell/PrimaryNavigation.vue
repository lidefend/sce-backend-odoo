<template>
  <div class="primary-navigation">
    <nav class="primary-navigation__shortcuts" aria-label="工作入口">
      <button type="button" :aria-current="homeActive ? 'page' : undefined" @click="emit('navigate', '/')"><ScIcon name="home" :size="16" /><span>首页</span></button>
      <button type="button" :aria-current="workActive ? 'page' : undefined" @click="emit('navigate', '/my-work')"><ScIcon name="briefcase" :size="16" /><span>我的工作</span></button>
    </nav>
    <label class="primary-navigation__search">
      <span class="sr-only">搜索菜单</span>
      <ScIcon name="search" :size="16" />
      <input :value="search" type="search" placeholder="搜索菜单..." @input="emitSearch" />
    </label>
    <div class="primary-navigation__tree">
      <MenuTree
        :nodes="nodes"
        :active-menu-id="activeMenuId"
        :capabilities="capabilities"
        :search-active="Boolean(search.trim())"
        @select="emit('select', $event)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { NavNode } from '@sc/schema';
import MenuTree from '../MenuTree.vue';
import ScIcon from '../design-system/ScIcon.vue';

const props = defineProps<{
  nodes: NavNode[];
  capabilities: string[];
  activeMenuId?: number;
  activePath: string;
  search: string;
}>();

const emit = defineEmits<{
  (event: 'select', node: NavNode): void;
  (event: 'navigate', path: string): void;
  (event: 'update:search', value: string): void;
}>();

const homeActive = computed(() => props.activePath === '/' || props.activePath === '/s/workspace.home');
const workActive = computed(() => props.activePath === '/my-work' || props.activePath === '/s/my_work.workspace');

function emitSearch(event: Event) {
  emit('update:search', (event.target as HTMLInputElement).value);
}
</script>

<style scoped>
.primary-navigation {
  display: grid;
  gap: var(--sc-space-3, 12px);
  min-height: 0;
}

.primary-navigation__shortcuts {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1px;
}

.primary-navigation__shortcuts button {
  min-height: 32px;
  padding: 5px 10px;
  border: 0;
  border-radius: 4px;
  background: transparent;
  color: var(--sc-app-text-secondary);
  text-align: left;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 9px;
  transition: background-color var(--sc-motion-fast, 120ms) ease, color var(--sc-motion-fast, 120ms) ease;
}

.primary-navigation__shortcuts button:hover {
  background: var(--sc-app-hover-bg);
  color: var(--sc-app-text-primary);
}

.primary-navigation__shortcuts button[aria-current='page'] {
  background: linear-gradient(90deg, color-mix(in srgb, var(--sc-app-accent) 14%, transparent), color-mix(in srgb, var(--sc-app-accent) 6%, transparent));
  color: var(--sc-app-info-text);
  font-weight: 600;
  box-shadow: inset 3px 0 0 var(--sc-semantic-surface-interactive);
}

.primary-navigation__shortcuts button:focus-visible,
.primary-navigation__search input:focus-visible {
  outline: 2px solid var(--sc-semantic-surface-interactive);
  outline-offset: -2px;
}

.primary-navigation__search input {
  width: 100%;
  min-height: var(--sc-product-control-height);
  padding: 0 var(--sc-space-3, 12px);
  border: 1px solid var(--sc-app-border);
  border-radius: var(--sc-radius-md, 8px);
  background: var(--sc-app-input-bg);
  color: var(--sc-app-text-primary);
}

.primary-navigation__search {
  position: relative;
  display: flex;
  align-items: center;
}

.primary-navigation__search > .sc-icon {
  position: absolute;
  z-index: 1;
  left: 11px;
  color: var(--sc-app-text-muted);
  pointer-events: none;
}

.primary-navigation__search input {
  padding-left: 34px;
}

.primary-navigation__tree {
  min-height: 0;
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

@media (min-width: 961px) {
  .primary-navigation {
    gap: 14px;
  }

  .primary-navigation__shortcuts {
    gap: 4px;
  }

  .primary-navigation__shortcuts button {
    min-height: 38px;
    padding: 7px 12px;
    border-radius: 8px;
    font-size: 13px;
  }

  .primary-navigation__search input {
    min-height: 38px;
    border-color: var(--sc-app-border);
    border-radius: 9px;
    background: color-mix(in srgb, var(--sc-app-panel) 86%, transparent);
    box-shadow: inset 0 1px 2px color-mix(in srgb, var(--sc-app-shadow) 6%, transparent);
  }

  .primary-navigation__search input:focus {
    border-color: var(--sc-semantic-surface-interactive);
    outline: 3px solid var(--sc-app-focus-ring);
  }
}
</style>
