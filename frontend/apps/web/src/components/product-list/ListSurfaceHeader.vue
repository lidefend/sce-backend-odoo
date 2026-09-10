<template>
  <ProductListHeader
    v-if="!contextual"
    data-list-surface-header
    :loading="loading"
    :show-search="showSearch"
    :search-value="searchValue"
    :search-label="searchLabel"
    :search-placeholder="searchPlaceholder"
    @search-input="$emit('search-input', $event)"
    @search-submit="$emit('search-submit')"
    @search-clear="$emit('search-clear')"
    @composition-start="$emit('composition-start')"
    @composition-end="$emit('composition-end', $event)"
  >
    <slot />
    <template #auxiliary>
      <div v-if="showFallbackCreate || columns.length" class="list-surface-utilities">
        <ScButton
          v-if="showFallbackCreate"
          variant="primary"
          :disabled="loading"
          @click="$emit('create')"
        >
          <ScIcon name="plus" :size="16" />
          {{ createLabel }}
        </ScButton>
        <div v-if="columns.length" ref="columnManager" class="list-surface-column-manager">
          <ScPopover placement="bottom-right" trigger="click" :disabled="loading" :visible="columnPanelOpen" @visible-change="columnPanelOpen = $event">
            <template #trigger>
              <ScButton
                type="button"
                variant="secondary"
                class="list-surface-column-button"
                appearance="outline-action"
                :aria-label="settingsDescription"
                :aria-expanded="columnPanelOpen"
                :aria-controls="columnPanelId"
                :title="settingsDescription"
                :disabled="loading"
                @keydown.esc.stop.prevent="closeColumnPanel"
              >
                <ScIcon name="columns" :size="16" />
                <span class="list-surface-column-label">列设置</span>
              </ScButton>
            </template>
            <div :id="columnPanelId" class="list-surface-column-panel" aria-label="列设置" @keydown.esc.stop.prevent="closeColumnPanel">
              <div class="list-surface-column-heading">
                <p class="list-surface-column-summary">已启用 {{ enabledCount }} 列，共 {{ columns.length }} 列</p>
                <ScButton type="button" variant="ghost" size="small" aria-label="关闭列设置" @click="closeColumnPanel">关闭</ScButton>
              </div>
              <p v-if="columnSettingsMessage" class="list-surface-column-summary" role="note">{{ columnSettingsMessage }}</p>
              <ScCheckbox
                v-for="column in columns"
                :key="column.name"
                class="list-surface-column-choice"
                appearance="menu-choice"
                size="small"
                :checked="visibleColumns.includes(column.name)"
                :disabled="loading || Boolean(columnDisabledReasons?.[column.name]) || lastVisibleColumn === column.name"
                :label="column.label"
                :title="columnDisabledReasons?.[column.name] || (lastVisibleColumn === column.name ? '至少保留一列' : undefined)"
                @change="(checked) => emitVisibility(column.name, checked)"
              />
              <ScButton type="button" class="list-surface-column-reset" appearance="outline-action" variant="secondary" size="small" :disabled="loading" @click="$emit('column-reset')">恢复默认</ScButton>
              <p v-if="saveStatusText" class="list-surface-save-message" :class="`is-${saveStatus}`">{{ saveStatusText }}</p>
            </div>
          </ScPopover>
          <span v-if="saveStatusText" class="list-surface-save-badge" :class="`is-${saveStatus}`">{{ saveStatusText }}</span>
        </div>
      </div>
    </template>
  </ProductListHeader>
  <div
    v-else
    class="list-surface-contextual-toolbar"
    data-semantic-component="ListSurfaceHeader"
    data-state="contextual"
    aria-label="批量操作"
  >
    <slot name="contextual" />
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, useId, watch } from 'vue';
import ScButton from '../design-system/ScButton.vue';
import ScCheckbox from '../design-system/ScCheckbox.vue';
import ScIcon from '../design-system/ScIcon.vue';
import ScPopover from '../design-system/ScPopover.vue';
import ProductListHeader from './ProductListHeader.vue';

type ColumnChoice = { name: string; label: string };

const props = defineProps<{
  loading: boolean;
  showSearch: boolean;
  searchValue: string;
  searchLabel: string;
  searchPlaceholder: string;
  columns: ColumnChoice[];
  visibleColumns: string[];
  lastVisibleColumn?: string;
  columnDisabledReasons?: Record<string, string>;
  columnSettingsMessage?: string;
  saveStatus?: 'idle' | 'saving' | 'saved' | 'error';
  saveStatusText?: string;
  contextual?: boolean;
  showFallbackCreate?: boolean;
  createLabel?: string;
}>();

const emit = defineEmits<{
  'search-input': [value: string];
  'search-submit': [];
  'search-clear': [];
  'composition-start': [];
  'composition-end': [event: CompositionEvent];
  'column-visibility-change': [payload: { name: string; checked: boolean }];
  'column-reset': [];
  create: [];
}>();

const enabledCount = computed(() => props.visibleColumns.length);
const columnPanelOpen = ref(false);
const columnPanelId = `column-panel-${useId()}`;
const columnManager = ref<HTMLElement | null>(null);

async function closeColumnPanel() {
  columnPanelOpen.value = false;
  await nextTick();
  columnManager.value?.querySelector<HTMLButtonElement>('button')?.focus();
}

watch(() => props.loading, (loading) => { if (loading) columnPanelOpen.value = false; });
const settingsDescription = computed(() => `列设置，已启用 ${enabledCount.value} 列，共 ${props.columns.length} 列`);

function emitVisibility(name: string, checked: boolean) {
  emit('column-visibility-change', {
    name,
    checked,
  });
}
</script>

<style scoped>
.list-surface-utilities { display: inline-flex; align-items: center; justify-content: flex-end; gap: var(--sc-toolbar-gap); min-width: 0; }
.list-surface-column-manager { position: relative; display: inline-flex; align-items: center; gap: var(--sc-toolbar-gap); }
.list-surface-column-button { font-size: 12px; }
.list-surface-column-button:disabled { opacity: .6; cursor: not-allowed; }
.list-surface-column-summary { margin: 0; color: var(--sc-app-text-secondary); font-size: 12px; font-variant-numeric: tabular-nums; }
.list-surface-column-heading { display: flex; align-items: center; justify-content: space-between; gap: var(--sc-toolbar-gap); }
.list-surface-column-heading :deep(.sc-btn) { min-width: 44px; min-height: 44px; }
.list-surface-save-badge, .list-surface-save-message { border: 1px solid var(--sc-app-success-border); border-radius: var(--sc-product-radius-control); background: var(--sc-app-success-bg); color: var(--sc-app-success-text); padding: 2px var(--sc-space-2xs); font-size: 12px; }
.list-surface-save-badge.is-saving, .list-surface-save-message.is-saving { border-color: var(--sc-app-info-border); background: var(--sc-app-info-bg); color: var(--sc-app-info-text); }
.list-surface-save-badge.is-error, .list-surface-save-message.is-error { border-color: var(--sc-app-danger-border); background: var(--sc-app-danger-bg); color: var(--sc-app-danger-text); }
.list-surface-column-panel { display: grid; gap: var(--sc-space-2xs); min-width: 210px; max-height: min(320px, 70vh); overflow: auto; }
.list-surface-column-choice { display: flex; align-items: center; gap: var(--sc-space-xs); min-height: 44px; font-size: 13px; white-space: nowrap; }
.list-surface-column-reset { min-height: 40px; margin-top: var(--sc-space-2xs); }
.list-surface-save-message { margin: 2px 0 0; padding: var(--sc-space-2xs) var(--sc-space-xs); }
.list-surface-contextual-toolbar { min-height: 44px; display: flex; align-items: center; width: 100%; }
@media (max-width: 520px) {
  .list-surface-column-label { display: none; }
  .list-surface-column-button { width: 44px; min-height: 44px; padding-inline: 0; }
}
</style>
