<template>
  <div ref="root" class="native-action-overflow native-action-more" data-semantic-component="NativeActionOverflowMenu">
    <ScButton
      ref="trigger"
      type="button"
      class="native-action-overflow__trigger native-action-btn native-action-btn--smart native-action-btn--more"
      size="small"
      variant="ghost"
      aria-haspopup="menu"
      :aria-expanded="open"
      :aria-controls="menuId"
      @click="toggle"
      @keydown.down.stop.prevent="openMenu('first')"
      @keydown.up.stop.prevent="openMenu('last')"
    >
      {{ label }}
    </ScButton>
    <div
      v-if="open"
      :id="menuId"
      ref="menu"
      class="native-action-overflow__menu native-action-more-menu"
      role="menu"
      @keydown="onMenuKeydown"
    >
      <ScButton
        v-for="(action, index) in actions"
        :key="keyResolver(action, index)"
        v-bind="evidenceResolver(action)"
        type="button"
        class="native-action-overflow__item native-action-more-item"
        size="small"
        variant="ghost"
        role="menuitem"
        tabindex="-1"
        :disabled="disabledResolver(action)"
        :title="titleResolver(action)"
        @click.stop.prevent="select(action)"
      >
        <span v-if="iconResolver(action)" :class="['native-action-overflow__icon', iconResolver(action)]" aria-hidden="true" />
        <span class="native-action-overflow__label">{{ labelResolver(action) }}</span>
      </ScButton>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, useId } from 'vue';
import ScButton from '../design-system/ScButton.vue';

type OverflowAction = Record<string, unknown>;

const props = withDefaults(defineProps<{
  actions: OverflowAction[];
  identity: string;
  label?: string;
  keyResolver: (action: OverflowAction, index: number) => string;
  evidenceResolver: (action: OverflowAction) => Record<string, string | undefined>;
  labelResolver: (action: OverflowAction) => string;
  iconResolver: (action: OverflowAction) => string;
  disabledResolver: (action: OverflowAction) => boolean;
  titleResolver: (action: OverflowAction) => string;
}>(), { label: '更多' });

const emit = defineEmits<{ (event: 'select', action: OverflowAction): void }>();
const root = ref<HTMLElement | null>(null);
const menu = ref<HTMLElement | null>(null);
const trigger = ref<{ $el?: HTMLElement } | null>(null);
const open = ref(false);
const instanceId = useId().replace(/[^a-zA-Z0-9_-]/g, '-');
const menuId = computed(() => `native-action-overflow-${instanceId}-${props.identity.replace(/[^a-zA-Z0-9_-]/g, '-')}`);

function enabledItems(): HTMLButtonElement[] {
  return Array.from(menu.value?.querySelectorAll<HTMLButtonElement>('[role="menuitem"]:not(:disabled)') || []);
}

async function openMenu(position: 'first' | 'last' = 'first') {
  open.value = true;
  await nextTick();
  const items = enabledItems();
  items[position === 'last' ? items.length - 1 : 0]?.focus();
}

function toggle() {
  if (open.value) close(true);
  else void openMenu();
}

function close(restoreFocus = false) {
  if (!open.value) return;
  open.value = false;
  if (restoreFocus) trigger.value?.$el?.focus();
}

function select(action: OverflowAction) {
  emit('select', action);
  close(true);
}

function onMenuKeydown(event: KeyboardEvent) {
  const items = enabledItems();
  if (!items.length) return;
  const current = items.indexOf(document.activeElement as HTMLButtonElement);
  let target = current;
  if (event.key === 'ArrowDown') target = (current + 1 + items.length) % items.length;
  else if (event.key === 'ArrowUp') target = (current - 1 + items.length) % items.length;
  else if (event.key === 'Home') target = 0;
  else if (event.key === 'End') target = items.length - 1;
  else if (event.key === 'Escape') {
    event.preventDefault();
    event.stopPropagation();
    close(true);
    return;
  } else if (event.key === 'Tab') {
    close();
    return;
  } else return;
  event.preventDefault();
  items[target]?.focus();
}

function onDocumentPointerDown(event: PointerEvent) {
  if (open.value && !root.value?.contains(event.target as Node)) close();
}

onMounted(() => document.addEventListener('pointerdown', onDocumentPointerDown));
onBeforeUnmount(() => document.removeEventListener('pointerdown', onDocumentPointerDown));
</script>

<style scoped>
.native-action-overflow {
  position: relative;
  display: inline-flex;
  min-width: 0;
  width: 100%;
}

.native-action-overflow__trigger {
  width: 100%;
  justify-content: center;
}

.native-action-overflow__menu {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  z-index: var(--sc-component-button-overflow-z-index);
  min-width: 160px;
  max-width: min(280px, 80vw);
  display: grid;
  gap: 2px;
  padding: 6px;
  background: var(--sc-app-panel);
  border: 1px solid var(--sc-app-border-strong);
  border-radius: 6px;
  box-shadow: var(--sc-semantic-shadow-modal);
}

.native-action-overflow__item {
  width: 100%;
  justify-content: flex-start;
  text-align: left;
}

.native-action-overflow__icon {
  flex: 0 0 auto;
  width: 18px;
  text-align: center;
  color: var(--sc-semantic-surface-interactive);
}

.native-action-overflow__label {
  min-width: 0;
  overflow-wrap: anywhere;
  line-height: 1.25;
}
</style>
