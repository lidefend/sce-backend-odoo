<template>
  <ul class="tree" :class="[`depth-${level}`, { 'tree--root': level === 0 }]">
    <li v-for="node in sorted" :key="nodeKey(node)">
      <div
        class="node"
        :class="{
          active: activeMenuId === (node.menu_id ?? node.id),
          ancestor: activeParents.has(nodeKey(node)),
          disabled: isBlocked(node),
        }"
      >
        <button v-if="node.children?.length" class="toggle" @click="toggle(nodeKey(node))">
          {{ expanded.has(nodeKey(node)) ? '▾' : '▸' }}
        </button>
        <span v-else class="toggle-spacer" aria-hidden="true"></span>
        <button
          class="label"
          :disabled="isBlocked(node)"
          :title="blockedTitle(node)"
          @click="onSelect(node)"
        >
          <span class="label-text">{{ nodeLabel(node) }}</span>
          <span v-if="isHandlingGroup(node)" class="label-badge">办理</span>
        </button>
      </div>
      <transition name="expand">
        <MenuTree
          v-if="node.children?.length"
          v-show="searchActive || expanded.has(nodeKey(node))"
          :nodes="node.children"
          :active-menu-id="activeMenuId"
          :capabilities="capabilities"
          :level="level + 1"
          :search-active="searchActive"
          @select="emit('select', $event)"
        />
      </transition>
    </li>
  </ul>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, watchEffect } from 'vue';
import type { NavNode } from '@sc/schema';
import { capabilityTooltip, evaluateCapabilityPolicy } from '../app/capabilityPolicy';
import { useSessionStore } from '../stores/session';

const props = withDefaults(defineProps<{ nodes: NavNode[]; activeMenuId?: number; capabilities?: string[]; level?: number; searchActive?: boolean }>(), {
  activeMenuId: undefined,
  capabilities: () => [],
  level: 0,
  searchActive: false,
});
const emit = defineEmits<{ (e: 'select', node: NavNode): void }>();

const session = useSessionStore();
const expanded = computed(() => new Set(session.menuExpandedKeys));
const activeParents = ref<Set<string>>(new Set());

const sorted = computed(() => {
  const nodes = hideEmptyDirectoryLeaves(hideDuplicateLeafBesideGroup(props.nodes));
  return [...nodes];
});

function hideEmptyDirectoryLeaves(nodes: NavNode[]) {
  return nodes.filter((node) => {
    if (node.children?.length) return true;
    const raw = node as NavNode & {
      target_type?: unknown;
      delivery_mode?: unknown;
      is_clickable?: unknown;
    };
    const targetType = String(raw.target_type || node.meta?.target_type || '').trim();
    const deliveryMode = String(raw.delivery_mode || node.meta?.delivery_mode || '').trim();
    return !(targetType === 'directory' && deliveryMode === 'none' && raw.is_clickable === false);
  });
}

function hideDuplicateLeafBesideGroup(nodes: NavNode[]) {
  const groupLabels = new Set(
    nodes
      .filter((node) => Boolean(node.children?.length))
      .map((node) => normalizedNodeLabel(node))
      .filter(Boolean),
  );
  if (!groupLabels.size) return [...nodes];
  return nodes.filter((node) => {
    if (node.children?.length) return true;
    return !groupLabels.has(normalizedNodeLabel(node));
  });
}

const level = computed(() => Number(props.level || 0));

function toggle(key: string) {
  session.toggleMenuExpanded(key);
}

function nodeKey(node: NavNode) {
  return (node as NavNode & { xmlid?: string }).xmlid || node.key || `menu_${node.menu_id || node.id}`;
}

function nodeLabel(node: NavNode) {
  const raw = String(node.title || node.name || node.label || 'Unnamed');
  return raw
    .replace(/\s*\(\d+\)\s*$/g, '')
    .replace(/^project\s*manager$/i, '负责人')
    .replace(/^purchase\s*manager$/i, '采购经理')
    .replace(/^finance$/i, '财务主管')
    .replace(/^executive$/i, '管理层')
    .replace(/^ops$/i, '运维专员')
    .replace(/^admin$/i, '系统管理员')
    .replace(/^workbench$/i, '诊断页')
    .replace(/^dashboard$/i, '看板');
}

function normalizedNodeLabel(node: NavNode) {
  return nodeLabel(node).trim();
}

function isHandlingGroup(node: NavNode) {
  return Boolean(node.children?.length) && (
    /办理$/.test(normalizedNodeLabel(node))
    || String(node.meta?.intent_group || '').trim() === 'handling'
  );
}

function onSelect(node: NavNode) {
  if (isBlocked(node)) {
    return;
  }
  if (node.children?.length && !hasNavigationTarget(node)) {
    toggle(nodeKey(node));
    return;
  }
  emit('select', node);
}

function hasNavigationTarget(node: NavNode) {
  const raw = node as NavNode & {
    action?: unknown;
    action_id?: unknown;
    actionId?: unknown;
    model?: unknown;
    route?: unknown;
    scene_key?: unknown;
    sceneKey?: unknown;
  };
  const meta = (node.meta && typeof node.meta === 'object') ? node.meta : {};
  return Boolean(
    raw.action
      || raw.action_id
      || raw.actionId
      || raw.model
      || raw.route
      || raw.scene_key
      || raw.sceneKey
      || meta.action_id
      || meta.actionId
      || meta.model
      || meta.route
      || meta.scene_key
      || meta.sceneKey,
  );
}

function ensureExpandedForActive(nodes: NavNode[], menuId?: number): Set<string> {
  if (!menuId) {
    return new Set();
  }
  const next = new Set<string>();
  const walk = (items: NavNode[], parents: string[] = []) => {
    for (const node of items) {
      const key = nodeKey(node);
      if ((node.menu_id ?? node.id) === menuId) {
        parents.forEach((p) => next.add(p));
      }
      if (node.children?.length) {
        walk(node.children, [...parents, key]);
      }
    }
  };
  walk(nodes);
  return next;
}

function ensureExpandedForDefaultGroups(nodes: NavNode[]): Set<string> {
  const next = new Set<string>();
  const walk = (items: NavNode[], insideJointAcceptance = false) => {
    for (const node of items) {
      const key = nodeKey(node);
      const label = normalizedNodeLabel(node);
      const isJointAcceptanceRoot = label === '联营项目数据核对';
      const shouldExpand = isJointAcceptanceRoot || isHandlingGroup(node) || (insideJointAcceptance && Boolean(node.children?.length));
      if (shouldExpand) {
        next.add(key);
      }
      if (node.children?.length) {
        walk(node.children, insideJointAcceptance || isJointAcceptanceRoot);
      }
    }
  };
  walk(nodes);
  return next;
}

watchEffect(() => {
  const parents = ensureExpandedForActive(props.nodes, props.activeMenuId);
  const defaults = ensureExpandedForDefaultGroups(props.nodes);
  if (parents.size) {
    session.ensureMenuExpanded([...parents]);
  }
  if (defaults.size) {
    session.ensureMenuExpanded([...defaults]);
  }
  activeParents.value = parents;
});

function isBlocked(node: NavNode) {
  return evaluateCapabilityPolicy({ source: node.meta, available: props.capabilities }).state !== 'enabled';
}

function blockedTitle(node: NavNode) {
  const policy = evaluateCapabilityPolicy({ source: node.meta, available: props.capabilities });
  const tip = capabilityTooltip(policy);
  return tip || undefined;
}

// 调试：打印接收到的节点
onMounted(() => {
  if (import.meta.env.DEV) {
    console.info('[MenuTree] Received nodes:', props.nodes.length);
    if (props.nodes.length > 0) {
      console.info('[MenuTree] First node:', {
        key: props.nodes[0].key,
        name: props.nodes[0].name,
        label: props.nodes[0].label,
        menu_id: props.nodes[0].menu_id,
        children: props.nodes[0].children?.length || 0,
        meta: props.nodes[0].meta
      });
    }
  }
});
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

.tree.depth-1 {
  padding: 1px 0 3px 18px;
}

.tree.depth-2,
.tree.depth-3,
.tree.depth-4,
.tree.depth-5 {
  padding: 1px 0 3px 16px;
}

.node {
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr);
  align-items: center;
  gap: 2px;
  min-height: 32px;
  border-radius: 4px;
  color: var(--sc-app-text-secondary);
  transition: background-color var(--sc-motion-fast, 120ms) ease, color var(--sc-motion-fast, 120ms) ease;
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
  font-weight: 600;
}

.node.active {
  background: var(--sc-navigation-active-bg);
  color: var(--sc-app-info-text);
}

.node:not(.active):hover {
  background: var(--sc-app-hover-bg);
}

.node.disabled .label {
  cursor: not-allowed;
  color: var(--sc-app-text-secondary);
}

.node.disabled .label:hover {
  background-color: transparent;
}

.toggle {
  width: 22px;
  height: 28px;
  border: none;
  border-radius: 6px;
  background: transparent;
  cursor: pointer;
  color: var(--sc-semantic-text-muted);
  font-size: 12px;
  line-height: 1;
}

.toggle:hover {
  background: transparent;
  color: var(--sc-app-text-primary);
}

.node.active .toggle,
.node.ancestor .toggle {
  color: var(--sc-app-info-text);
}

.toggle-spacer {
  width: 22px;
  display: inline-block;
  flex: 0 0 22px;
}

.label {
  width: 100%;
  min-height: 30px;
  padding: 5px 8px 5px 4px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
  line-height: 1.35;
  transition: color var(--sc-motion-fast, 120ms) ease;
}

.tree--root > li > .node .label {
  min-height: 34px;
  padding: 6px 8px 6px 4px;
  font-weight: 600;
  letter-spacing: 0;
}

.depth-1 > li > .node .label {
  font-weight: 500;
}

.depth-2 > li > .node .label,
.depth-3 > li > .node .label,
.depth-4 > li > .node .label,
.depth-5 > li > .node .label {
  color: var(--sc-app-text-secondary);
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
