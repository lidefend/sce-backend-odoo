<template>
  <ul class="tree" :class="[`depth-${level}`, { 'tree--root': level === 0 }]" data-semantic-component="MenuTree" :data-state="nodes.length ? 'ready' : 'empty'">
    <li
      v-for="node in nodes"
      :key="node.key"
      data-navigation-node="canonical"
      :data-navigation-key="node.key"
      :data-navigation-menu-id="node.menuId ?? ''"
      :data-navigation-action-id="node.actionId ?? ''"
      :data-navigation-state="node.state"
      :data-navigation-depth="level"
    >
      <div
        class="node"
        :class="{
          active: activeMenuId === node.menuId,
          ancestor: activeParents.has(node.key),
          expanded: Boolean(node.children.length) && expanded.has(node.key),
          group: Boolean(node.children.length),
          leaf: !node.children.length,
          disabled: isBlocked(node),
        }"
      >
        <span class="node-icon" aria-hidden="true">
          <ScIcon :name="nodeIcon(node)" :size="level === 0 ? 16 : 14" />
        </span>
        <button
          class="label"
          :disabled="isBlocked(node)"
          :title="blockedTitle(node) || nodeLabel(node)"
          :aria-current="activeMenuId === node.menuId ? 'page' : undefined"
          @click="onSelect(node)"
        >
          <span class="label-text" :title="nodeLabel(node)">{{ nodeLabel(node) }}</span>
          <span v-if="nodeBadge(node)" class="label-badge">{{ nodeBadge(node) }}</span>
        </button>
        <button
          v-if="node.children.length"
          class="toggle"
          :aria-label="`${expanded.has(node.key) ? '收起' : '展开'}${node.label}`"
          :aria-expanded="expanded.has(node.key)"
          :title="`${expanded.has(node.key) ? '收起' : '展开'}${node.label}`"
          @click="emit('toggle', node.key)"
        >
          <ScIcon name="chevron-right" :size="14" :class="{ 'is-expanded': expanded.has(node.key) }" />
        </button>
        <span v-else class="toggle-spacer" aria-hidden="true"></span>
      </div>
      <transition name="expand">
        <MenuTree
          v-if="node.children.length"
          v-show="searchActive || expanded.has(node.key)"
          :nodes="node.children"
          :active-menu-id="activeMenuId"
          :expanded-keys="expandedKeys"
          :level="level + 1"
          :search-active="searchActive"
          @select="emit('select', $event)"
          @toggle="emit('toggle', $event)"
          @ensure-expanded="emit('ensure-expanded', $event)"
        />
      </transition>
    </li>
  </ul>
</template>

<script setup lang="ts">
import { computed, watchEffect } from 'vue';
import type { CanonicalNavigationNode } from '@sc/schema';
import ScIcon from './design-system/ScIcon.vue';

const props = withDefaults(defineProps<{ nodes: CanonicalNavigationNode[]; activeMenuId?: number; expandedKeys?: string[]; level?: number; searchActive?: boolean }>(), {
  activeMenuId: undefined,
  expandedKeys: () => [],
  level: 0,
  searchActive: false,
});
const emit = defineEmits<{
  (event: 'select', node: CanonicalNavigationNode): void;
  (event: 'toggle', key: string): void;
  (event: 'ensure-expanded', keys: string[]): void;
}>();

const expanded = computed(() => new Set(props.expandedKeys));
const activeParents = computed(() => {
  const active = findNode(props.nodes, props.activeMenuId);
  return new Set(active?.parentChain.map((parent) => parent.key) || []);
});

type NavigationIconName = 'apps' | 'briefcase' | 'building' | 'clipboard' | 'construction' | 'contract' | 'file-text' | 'folder' | 'home' | 'project' | 'settings' | 'user';
const navigationIconNames = new Set<NavigationIconName>([
  'apps', 'briefcase', 'building', 'clipboard', 'construction', 'contract', 'file-text', 'folder', 'home', 'project', 'settings', 'user',
]);

const level = computed(() => Number(props.level || 0));

function nodeLabel(node: CanonicalNavigationNode) {
  return node.label;
}

function nodeIcon(node: CanonicalNavigationNode): NavigationIconName {
  const requested = String(node.icon || '').trim() as NavigationIconName;
  if (navigationIconNames.has(requested)) return requested;
  return node.children.length ? 'folder' : 'file-text';
}

function nodeBadge(node: CanonicalNavigationNode): string {
  return String(node.source.meta?.badge_label || '').trim();
}

function onSelect(node: CanonicalNavigationNode) {
  if (isBlocked(node)) {
    return;
  }
  if (node.state === 'container') {
    emit('toggle', node.key);
    return;
  }
  emit('select', node);
}

function findNode(nodes: CanonicalNavigationNode[], menuId?: number): CanonicalNavigationNode | null {
  if (!menuId) return null;
  for (const node of nodes) {
    if (node.menuId === menuId) return node;
    const child = findNode(node.children, menuId);
    if (child) return child;
  }
  return null;
}

function ensureExpandedForDefaultGroups(nodes: CanonicalNavigationNode[]): Set<string> {
  const next = new Set<string>();
  const walk = (items: CanonicalNavigationNode[]) => {
    for (const node of items) {
      if (node.children.length && node.source.meta?.default_expanded === true) {
        next.add(node.key);
      }
      if (node.children.length) {
        walk(node.children);
      }
    }
  };
  walk(nodes);
  return next;
}

watchEffect(() => {
  const parents = activeParents.value;
  const defaults = ensureExpandedForDefaultGroups(props.nodes);
  const required = new Set([...parents, ...defaults]);
  const missing = [...required].filter((key) => !expanded.value.has(key));
  if (missing.length) emit('ensure-expanded', missing);
});

function isBlocked(node: CanonicalNavigationNode) {
  return node.state === 'disabled';
}

function blockedTitle(node: CanonicalNavigationNode) {
  return node.disabledReason || undefined;
}
</script>

<style scoped>
.tree {
  list-style: none;
  padding-left: 0;
  margin: 0;
  display: grid;
  gap: 1px;
}

.tree:not(.tree--root) {
  margin-top: 1px;
  margin-bottom: 3px;
  padding-left: 0;
}

.tree.depth-1,
.tree.depth-2,
.tree.depth-3,
.tree.depth-4,
.tree.depth-5 {
  padding: 1px 0 3px;
}

.node {
  display: grid;
  grid-template-columns: 20px minmax(0, 1fr) 20px;
  align-items: center;
  gap: 4px;
  min-height: 34px;
  padding: 0 6px 0 8px;
  border-radius: 6px;
  color: var(--sc-app-text-secondary);
  transition: background-color var(--sc-motion-fast, 120ms) ease, color var(--sc-motion-fast, 120ms) ease;
}

.node-icon {
  width: 20px;
  min-width: 20px;
  display: grid;
  place-items: center;
  color: var(--sc-app-text-muted);
  transition: color var(--sc-motion-fast, 120ms) ease;
}

.label {
  background: transparent;
  border: none;
  text-align: left;
  cursor: pointer;
  color: var(--sc-app-text-primary);
  display: inline-flex;
  align-items: center;
  gap: 7px;
  max-width: 100%;
  min-width: 0;
}

.node.active .label {
  font-weight: 600;
  color: var(--sc-app-info-text);
  background: transparent;
  box-shadow: none;
}

.node.ancestor .label {
  color: var(--sc-app-text-primary);
  background: transparent;
  font-weight: 550;
}

.node.active {
  background: var(--sc-navigation-active-bg);
  color: var(--sc-app-info-text);
  box-shadow: inset 3px 0 0 var(--sc-semantic-surface-interactive);
}

.node:not(.active):hover {
  background: var(--sc-app-hover-bg);
}

.node.expanded:not(.active):not(.ancestor) {
  background: color-mix(in srgb, var(--sc-navigation-active-bg) 42%, transparent);
}

.node.active .node-icon,
.node.active .toggle,
.node.ancestor .node-icon,
.node.ancestor .toggle {
  color: var(--sc-app-info-text);
}

.node.disabled .label {
  cursor: not-allowed;
  color: var(--sc-app-text-secondary);
}

.node.disabled .label:hover {
  background-color: transparent;
}

.toggle {
  width: 20px;
  height: 28px;
  border: none;
  border-radius: 6px;
  background: transparent;
  cursor: pointer;
  color: var(--sc-semantic-text-muted);
  font-size: 12px;
  line-height: 1;
  display: grid;
  place-items: center;
}

.toggle .sc-icon {
  transition: transform var(--sc-motion-fast, 120ms) ease;
}

.toggle .sc-icon.is-expanded {
  transform: rotate(90deg);
}

.toggle:hover {
  background: transparent;
  color: var(--sc-app-text-primary);
}

.toggle-spacer {
  width: 20px;
  display: inline-block;
  flex: 0 0 20px;
}

.label {
  width: 100%;
  min-height: 30px;
  padding: 5px 0;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
  line-height: 1.35;
  transition: color var(--sc-motion-fast, 120ms) ease;
}

.tree--root > li > .node .label {
  min-height: 34px;
  padding: 6px 0;
  font-weight: 650;
  letter-spacing: 0;
}

.depth-1 > li > .node .label {
  font-weight: 500;
}

.depth-1 > li > .node.leaf .label,
.depth-2 > li > .node .label,
.depth-3 > li > .node .label,
.depth-4 > li > .node .label,
.depth-5 > li > .node .label {
  color: var(--sc-app-text-secondary);
  font-weight: 450;
}

.depth-1 > li > .node.group .label {
  color: var(--sc-app-text-primary);
  font-weight: 550;
}

.label-text {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.label-badge {
  flex: 0 0 auto;
  border: 1px solid var(--sc-app-border);
  color: var(--sc-app-text-secondary);
  background: var(--sc-app-subtle-bg);
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  line-height: 1;
  padding: 2px 4px;
}

.label:hover {
  background-color: transparent;
}

.label:focus-visible,
.toggle:focus-visible {
  outline: 2px solid var(--sc-semantic-surface-interactive);
  outline-offset: -2px;
}

.expand-enter-active,
.expand-leave-active {
  transition: all 0.18s ease;
}

.expand-enter-from,
.expand-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
