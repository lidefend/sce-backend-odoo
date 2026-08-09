<template>
  <ProductListHeader
    v-if="!contextual"
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
        <div v-if="columns.length" ref="pickerRoot" class="list-surface-column-manager">
          <ScButton
            type="button"
            variant="secondary"
            class="list-surface-column-button"
            :aria-expanded="pickerOpen"
            :aria-label="settingsDescription"
            :title="settingsDescription"
            :disabled="loading"
            @click.stop="pickerOpen = !pickerOpen"
          >
            <ScIcon name="columns" :size="16" />
            <span class="list-surface-column-label">列设置</span>
          </ScButton>
          <span v-if="saveStatusText" class="list-surface-save-badge" :class="`is-${saveStatus}`">{{ saveStatusText }}</span>
          <div v-if="pickerOpen" class="list-surface-column-menu" aria-label="列设置">
            <p class="list-surface-column-summary">已启用 {{ enabledCount }} 列，共 {{ columns.length }} 列</p>
            <label v-for="column in columns" :key="column.name" class="list-surface-column-choice">
              <input
                type="checkbox"
                :checked="visibleColumns.includes(column.name)"
                :disabled="loading || lastVisibleColumn === column.name"
                @change="emitVisibility(column.name, $event)"
              />
              <span>{{ column.label }}</span>
            </label>
            <button type="button" class="list-surface-column-reset" :disabled="loading" @click="$emit('column-reset')">恢复默认</button>
            <p v-if="saveStatusText" class="list-surface-save-message" :class="`is-${saveStatus}`">{{ saveStatusText }}</p>
          </div>
        </div>
      </div>
    </template>
  </ProductListHeader>
  <div v-else class="list-surface-contextual-toolbar" aria-label="批量操作">
    <slot name="contextual" />
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import ScButton from '../design-system/ScButton.vue';
import ScIcon from '../design-system/ScIcon.vue';
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
  saveStatus?: 'idle' | 'saving' | 'saved' | 'error';
  saveStatusText?: string;
  contextual?: boolean;
  showFallbackCreate?: boolean;
  createLabel?: string;
}>();

const emit = defineEmits<{
  'search-input': [event: Event];
  'search-submit': [];
  'search-clear': [];
  'composition-start': [];
  'composition-end': [event: CompositionEvent];
  'column-visibility-change': [payload: { name: string; checked: boolean }];
  'column-reset': [];
  create: [];
}>();

const pickerRoot = ref<HTMLElement | null>(null);
const pickerOpen = ref(false);
const enabledCount = computed(() => props.visibleColumns.length);
const settingsDescription = computed(() => `列设置，已启用 ${enabledCount.value} 列，共 ${props.columns.length} 列`);

function emitVisibility(name: string, event: Event) {
  emit('column-visibility-change', {
    name,
    checked: Boolean((event.target as HTMLInputElement | null)?.checked),
  });
}

function closeOnOutsidePointer(event: PointerEvent) {
  if (!pickerRoot.value?.contains(event.target as Node)) pickerOpen.value = false;
}

onMounted(() => document.addEventListener('pointerdown', closeOnOutsidePointer));
onBeforeUnmount(() => document.removeEventListener('pointerdown', closeOnOutsidePointer));
</script>

<style scoped>
.list-surface-utilities { display: inline-flex; align-items: center; justify-content: flex-end; gap: var(--sc-toolbar-gap); min-width: 0; }
.list-surface-column-manager { position: relative; display: inline-flex; align-items: center; gap: var(--sc-toolbar-gap); }
.list-surface-column-button { color: var(--sc-app-text-secondary); font-size: 12px; }
.list-surface-column-button:focus-visible { outline: 3px solid var(--sc-app-focus-ring); outline-offset: 2px; }
.list-surface-column-button:disabled { opacity: .6; cursor: not-allowed; }
.list-surface-column-summary { margin: 0; color: var(--sc-app-text-secondary); font-size: 12px; font-variant-numeric: tabular-nums; }
.list-surface-save-badge, .list-surface-save-message { border: 1px solid var(--sc-app-success-border); border-radius: var(--sc-product-radius-control); background: var(--sc-app-success-bg); color: var(--sc-app-success-text); padding: 2px var(--sc-space-2xs); font-size: 12px; }
.list-surface-save-badge.is-saving, .list-surface-save-message.is-saving { border-color: var(--sc-app-info-border); background: var(--sc-app-info-bg); color: var(--sc-app-info-text); }
.list-surface-save-badge.is-error, .list-surface-save-message.is-error { border-color: var(--sc-app-danger-border); background: var(--sc-app-danger-bg); color: var(--sc-app-danger-text); }
.list-surface-column-menu { position: absolute; z-index: 40; right: 0; top: calc(100% + var(--sc-space-2xs)); display: grid; gap: var(--sc-space-2xs); min-width: 210px; max-height: min(320px, 70vh); overflow: auto; border: 1px solid var(--sc-app-border-strong); border-radius: var(--sc-product-radius-panel); background: var(--sc-app-panel); padding: var(--sc-space-xs); box-shadow: var(--sc-product-shadow-overlay); }
.list-surface-column-choice { display: flex; align-items: center; gap: var(--sc-space-xs); min-height: 44px; color: var(--sc-app-text-primary); font-size: 13px; white-space: nowrap; }
.list-surface-column-reset { min-height: 40px; margin-top: var(--sc-space-2xs); border: 1px solid var(--sc-app-border); border-radius: var(--sc-product-radius-panel); background: var(--sc-app-muted-bg); color: var(--sc-app-text-secondary); cursor: pointer; }
.list-surface-save-message { margin: 2px 0 0; padding: var(--sc-space-2xs) var(--sc-space-xs); }
.list-surface-contextual-toolbar { min-height: 44px; display: flex; align-items: center; width: 100%; }
@media (max-width: 520px) {
  .list-surface-column-label { display: none; }
  .list-surface-column-button { width: 44px; padding-inline: 0; }
}
</style>
