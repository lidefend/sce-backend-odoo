<template>
  <TDesignSubmenu
    v-if="node.children.length"
    :value="node.key"
    :disabled="blocked"
    data-navigation-node="canonical"
    :data-navigation-key="node.key"
    :data-navigation-menu-id="node.menuId ?? ''"
    :data-navigation-action-id="node.actionId ?? ''"
    :data-navigation-state="node.state"
    :data-navigation-depth="depth"
    :title="blockedTitle"
  >
    <template #icon><ScIcon :name="icon" :size="depth === 0 ? 16 : 14" /></template>
    <template #title>
      <span class="navigation-node__label" :title="blockedTitle || node.label">{{ node.label }}</span>
      <span v-if="badge" class="navigation-node__badge">{{ badge }}</span>
    </template>
    <CanonicalNavigationMenuNode
      v-for="child in node.children"
      :key="child.key"
      :node="child"
      :depth="depth + 1"
    />
  </TDesignSubmenu>
  <TDesignMenuItem
    v-else
    :value="node.key"
    :disabled="blocked"
    data-navigation-node="canonical"
    :data-navigation-key="node.key"
    :data-navigation-menu-id="node.menuId ?? ''"
    :data-navigation-action-id="node.actionId ?? ''"
    :data-navigation-state="node.state"
    :data-navigation-depth="depth"
    :title="blockedTitle || node.label"
    :aria-current="active ? 'page' : undefined"
  >
    <template #icon><ScIcon :name="icon" :size="depth === 0 ? 16 : 14" /></template>
    <span class="navigation-node__label">{{ node.label }}</span>
    <span v-if="badge" class="navigation-node__badge">{{ badge }}</span>
  </TDesignMenuItem>
</template>

<script setup lang="ts">
import { computed, inject, type ComputedRef } from 'vue';
import type { CanonicalNavigationNode } from '@sc/schema';
import { TDesignMenuItem, TDesignSubmenu } from '../design-system/tdesignPrimitiveBridge';
import ScIcon from '../design-system/ScIcon.vue';

type NavigationIconName = 'apps' | 'briefcase' | 'building' | 'clipboard' | 'construction' | 'contract' | 'file-text' | 'folder' | 'home' | 'project' | 'settings' | 'user';

const props = defineProps<{ node: CanonicalNavigationNode; depth: number }>();
const activeKey = inject<ComputedRef<string>>('canonical-navigation-active-key');
const knownIcons = new Set<NavigationIconName>([
  'apps', 'briefcase', 'building', 'clipboard', 'construction', 'contract', 'file-text', 'folder', 'home', 'project', 'settings', 'user',
]);

const blocked = computed(() => props.node.state === 'disabled');
const blockedTitle = computed(() => props.node.disabledReason || undefined);
const badge = computed(() => String(props.node.source.meta?.badge_label || '').trim());
const active = computed(() => activeKey?.value === props.node.key);
const icon = computed<NavigationIconName>(() => {
  const requested = String(props.node.icon || '').trim() as NavigationIconName;
  return knownIcons.has(requested) ? requested : props.node.children.length ? 'folder' : 'file-text';
});
</script>

<style scoped>
.navigation-node__label {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.navigation-node__badge {
  margin-left: auto;
  padding: 1px 6px;
  border-radius: 999px;
  color: var(--sc-app-accent);
  background: var(--sc-app-accent-soft);
  font-size: 11px;
  line-height: 16px;
}
</style>
