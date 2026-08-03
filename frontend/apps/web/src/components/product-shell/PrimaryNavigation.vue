<template>
  <div class="primary-navigation">
    <nav class="primary-navigation__shortcuts" aria-label="工作入口">
      <button type="button" :aria-current="homeActive ? 'page' : undefined" @click="emit('navigate', '/')">首页</button>
      <button type="button" :aria-current="workActive ? 'page' : undefined" @click="emit('navigate', '/my-work')">我的工作</button>
    </nav>
    <label class="primary-navigation__search">
      <span class="sr-only">搜索菜单</span>
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
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--sc-space-2, 8px);
}

.primary-navigation__shortcuts button {
  min-height: 36px;
  border: 1px solid var(--sc-app-border);
  border-radius: var(--sc-product-radius-control);
  border-color: rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.05);
  color: #d9e2f1;
  cursor: pointer;
  transition: background-color var(--sc-motion-fast, 120ms) ease, border-color var(--sc-motion-fast, 120ms) ease;
}

.primary-navigation__shortcuts button[aria-current='page'] {
  border-color: #4ea1ff;
  background: #2f80ed;
  color: #fff;
  font-weight: 700;
}

.primary-navigation__search input {
  width: 100%;
  min-height: var(--sc-product-control-height);
  padding: 0 var(--sc-space-3, 12px);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: var(--sc-radius-md, 8px);
  background: rgba(255, 255, 255, 0.06);
  color: #f8fafc;
}

.primary-navigation__search input:focus {
  border-color: #4ea1ff;
  outline: 2px solid rgba(78, 161, 255, 0.22);
}

.primary-navigation__tree {
  min-height: 0;
}
</style>
