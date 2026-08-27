<template>
  <section
    ref="toolbarRoot"
    class="action-toolbar"
    :class="{ 'action-toolbar--without-view': !showViewSwitch || viewModes.length <= 1 }"
    data-semantic-component="CollectionActionToolbar"
    data-semantic-layer="pattern"
    :data-open-layer="searchMenuOpen ? 'search' : overflowMenuOpen ? 'overflow' : 'none'"
    :aria-label="uiLabel('collection_toolbar', '列表操作')"
  >
    <div v-if="showViewSwitch && viewModes.length > 1" class="toolbar-section view-switch">
      <p class="contract-label">{{ viewLabel }}</p>
      <div class="contract-chips">
        <ScButton
          v-for="mode in viewModes"
          :key="`view-mode-${mode}`"
          class="contract-chip"
          appearance="toolbar-chip"
          variant="ghost"
          size="small"
          :class="{ active: currentViewMode === mode }"
          :disabled="loading"
          :aria-pressed="currentViewMode === mode"
          @click="$emit('switch-view', mode)"
        >
          {{ viewModeLabels[mode] || mode }}
        </ScButton>
      </div>
    </div>

    <div class="native-search">
      <div class="native-searchbox">
        <ScButton
          v-if="activeFilterChip"
          class="search-facet"
          appearance="toolbar-chip"
          type="button"
          variant="ghost"
          size="small"
          aria-pressed="true"
          :disabled="loading"
          @click="$emit('clear-filter')"
        >
          <span>{{ activeFilterChip.label }}</span>
          <span class="facet-remove">{{ clearSymbol }}</span>
        </ScButton>
        <ScButton
          v-if="activeSavedFilterChip"
          class="search-facet"
          appearance="toolbar-chip"
          type="button"
          variant="ghost"
          size="small"
          aria-pressed="true"
          :disabled="loading"
          @click="$emit('clear-saved-filter')"
        >
          <span>{{ activeSavedFilterChip.label }}</span>
          <span class="facet-remove">{{ clearSymbol }}</span>
        </ScButton>
        <ScButton
          v-if="activeCustomFilterLabel"
          class="search-facet"
          appearance="toolbar-chip"
          type="button"
          variant="ghost"
          size="small"
          aria-pressed="true"
          :disabled="loading"
          @click="$emit('clear-custom-filter')"
        >
          <span>{{ activeCustomFilterLabel }}</span>
          <span class="facet-remove">{{ clearSymbol }}</span>
        </ScButton>
        <ScButton
          v-if="activeGroupChip"
          class="search-facet"
          appearance="toolbar-chip"
          type="button"
          variant="ghost"
          size="small"
          aria-pressed="true"
          :disabled="loading"
          @click="$emit('clear-group')"
        >
          <span>{{ activeGroupChip.label }}</span>
          <span class="facet-remove">{{ clearSymbol }}</span>
        </ScButton>
        <ScInputGroup class="collection-search-control">
          <ScInput
            type="search"
            :model-value="searchValue"
            :disabled="loading"
            :loading="loading"
            :placeholder="searchPlaceholder"
            @compositionstart="$emit('search-composition-start')"
            @compositionend="$emit('search-composition-end', $event)"
            @input="$emit('search-input', $event)"
            @keydown.enter.prevent="$emit('search-submit')"
            @keydown.esc.stop="closeSearchMenuAndRestoreFocus"
          />
          <template #append>
            <span class="collection-search-control__actions">
              <ScButton
                class="toolbar-search-submit"
                type="button"
                variant="secondary"
                :disabled="loading"
                @click="$emit('search-submit')"
              >
                <ScIcon name="search" :size="16" />
                {{ uiLabel('search_submit', '搜索') }}
              </ScButton>
              <ScButton
                v-if="searchValue"
                class="toolbar-search-clear"
                type="button"
                variant="ghost"
                :disabled="loading"
                @click="$emit('clear-search')"
              >
                {{ clearLabel }}
              </ScButton>
              <ScIconButton
                ref="searchMenuToggle"
                class="search-menu-toggle"
                appearance="toolbar-menu-toggle"
                :class="{ active: searchMenuOpen }"
                :disabled="loading || !hasSearchMenu"
                :label="uiLabel('search_menu_toggle', '展开搜索菜单')"
                :aria-expanded="searchMenuOpen"
                aria-controls="collection-search-disclosure"
                @click="toggleSearchMenu"
              >
                <ScIcon name="chevron-right" :size="14" class="search-menu-caret" :class="{ 'is-open': searchMenuOpen }" />
              </ScIconButton>
              <ScButton
                v-if="hasStructuredConditions"
                class="toolbar-clear-all"
                type="button"
                variant="ghost"
                size="small"
                :disabled="loading"
                :aria-label="`已应用 ${activeConditionCount} 项查询条件，清除全部`"
                @click="$emit('clear-all')"
              >
                清除全部
              </ScButton>
            </span>
          </template>
        </ScInputGroup>
      </div>
      <div v-if="searchMenuOpen && hasSearchMenu" id="collection-search-disclosure" class="search-dropdown" data-collection-toolbar-layer="search">
        <section v-if="showFilterColumn" class="search-dropdown-section">
          <p class="search-dropdown-title">{{ filterLabel }}</p>
          <div class="search-dropdown-items">
            <ScButton
              v-for="chip in allFilterChips"
              :key="`filter-${chip.key}`"
              class="search-menu-item"
              appearance="menu-item"
              variant="ghost"
              size="small"
              :class="{ selected: activeFilterKey === chip.key }"
              :aria-pressed="activeFilterKey === chip.key"
              :disabled="loading"
              @click="selectFilter(chip.key)"
            >
              <span class="menu-check">{{ activeFilterKey === chip.key ? selectedSymbol : '' }}</span>
              <span>{{ chip.label }}</span>
            </ScButton>
            <p v-if="!allFilterChips.length" class="search-menu-empty">{{ uiLabel('empty_filters', '暂无筛选') }}</p>
            <ScButton
              v-if="customFilterEnabled"
              class="search-menu-item custom-entry"
              appearance="menu-item"
              type="button"
              variant="ghost"
              size="small"
              :disabled="loading"
              @click="customFilterOpen = !customFilterOpen"
            >
              <span class="menu-check"></span>
              <span>{{ customFilterLabel }}</span>
            </ScButton>
            <div v-if="customFilterEnabled && customFilterOpen" class="custom-search-panel">
              <ScSelect v-model="customFilterField" size="small" :placeholder="uiLabel('select_field', '选择字段')" :options="customFilterFields.map((field) => ({ value: field.field, label: field.label }))" />
              <ScSelect v-model="customFilterOperator" size="small" :options="activeCustomFilterOperators.map((operator) => ({ value: operator.value, label: operator.label }))" />
              <ScSelect v-if="activeCustomFilterField?.type === 'selection'" v-model="customFilterValue" size="small" :placeholder="uiLabel('select_value', '选择值')" :options="activeCustomFilterChoices.map((choice) => ({ value: choice.value, label: choice.label }))" />
              <ScSelect v-else-if="activeCustomFilterField?.type === 'boolean'" v-model="customFilterValue" size="small" :options="[{ value: 'true', label: uiLabel('boolean_true', '是') }, { value: 'false', label: uiLabel('boolean_false', '否') }]" />
              <ScInput v-else v-model="customFilterValue" size="small" :type="customFilterInputType" :placeholder="uiLabel('input_value', '输入值')" />
              <div class="custom-search-actions">
                <ScButton type="button" variant="primary" size="small" :disabled="!canApplyCustomFilter || loading" @click="applyCustomFilter">{{ uiLabel('add', '添加') }}</ScButton>
                <ScButton type="button" variant="ghost" size="small" :disabled="loading" @click="resetCustomFilter">{{ uiLabel('cancel', '取消') }}</ScButton>
              </div>
            </div>
          </div>
        </section>

        <section v-if="showGroupColumn" class="search-dropdown-section">
          <p class="search-dropdown-title">{{ groupLabel }}</p>
          <div class="search-dropdown-items">
            <ScButton
              v-for="chip in menuGroupChips"
              :key="`group-${chip.key}`"
              class="search-menu-item"
              appearance="menu-item"
              variant="ghost"
              size="small"
              :class="{ selected: activeGroupKey === chip.key }"
              :aria-pressed="activeGroupKey === chip.key"
              :disabled="loading"
              @click="selectGroup(chip.key)"
            >
              <span class="menu-check">{{ activeGroupKey === chip.key ? selectedSymbol : '' }}</span>
              <span>{{ chip.label }}</span>
            </ScButton>
            <p v-if="!menuGroupChips.length" class="search-menu-empty">{{ uiLabel('empty_group_by', '暂无分组') }}</p>
            <ScSelect
              v-if="customGroupEnabled"
              v-model="customGroupField"
              class="custom-group-select"
              :disabled="loading"
              :options="[{ value: '', label: customGroupLabel }, ...customGroupFields.map((chip) => ({ value: chip.key, label: chip.label }))]"
              @change="applyCustomGroup"
            />
          </div>
        </section>

        <section v-if="showSavedFilterColumn" class="search-dropdown-section">
          <p class="search-dropdown-title">{{ savedFilterLabel }}</p>
          <div class="search-dropdown-items">
            <ScButton
              v-for="chip in allSavedFilterChips"
              :key="`saved-filter-${chip.key}`"
              class="search-menu-item"
              appearance="menu-item"
              variant="ghost"
              size="small"
              :class="{ selected: activeSavedFilterKey === chip.key }"
              :aria-pressed="activeSavedFilterKey === chip.key"
              :disabled="loading"
              @click="selectSavedFilter(chip.key)"
            >
              <span class="menu-check">{{ activeSavedFilterKey === chip.key ? selectedSymbol : '' }}</span>
              <span>{{ chip.label }}</span>
              <span v-if="chip.isDefault" class="menu-badge">{{ uiLabel('default', '默认') }}</span>
              <span v-if="chip.isShared" class="menu-badge">{{ uiLabel('shared', '共享') }}</span>
            </ScButton>
            <p v-if="!allSavedFilterChips.length" class="search-menu-empty">{{ uiLabel('empty_saved_filters', '暂无收藏') }}</p>
            <ScButton
              v-if="favoriteSaveEnabled"
              class="search-menu-item custom-entry"
              appearance="menu-item"
              type="button"
              variant="ghost"
              size="small"
              :disabled="loading"
              @click="favoriteSaveOpen = !favoriteSaveOpen"
            >
              <span class="menu-check"></span>
              <span>{{ favoriteSaveLabel }}</span>
            </ScButton>
            <div v-if="favoriteSaveEnabled && favoriteSaveOpen" class="custom-search-panel">
              <ScInput v-model="favoriteName" size="small" :placeholder="uiLabel('favorite_name', '收藏名称')" />
              <ScCheckbox v-model:checked="favoriteUseByDefault" :label="uiLabel('favorite_use_by_default', '设为默认筛选')" />
              <ScCheckbox v-model:checked="favoriteShared" :label="uiLabel('favorite_shared', '共享给所有用户')" />
              <div class="custom-search-actions">
                <ScButton type="button" variant="primary" size="small" :disabled="!favoriteName.trim() || loading" @click="saveFavorite">{{ uiLabel('save', '保存') }}</ScButton>
                <ScButton type="button" variant="ghost" size="small" :disabled="loading" @click="favoriteSaveOpen = false">{{ uiLabel('cancel', '取消') }}</ScButton>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>

    <span v-if="totalCount !== undefined" class="toolbar-total" aria-live="polite">共 {{ totalCount }} 条</span>

    <div v-if="sortOptions.length" class="toolbar-section sort-switch">
      <p class="contract-label">{{ sortLabel }}</p>
      <div class="contract-chips">
        <ScButton
          v-for="option in sortOptions"
          :key="`sort-${option.value}`"
          class="contract-chip"
          appearance="toolbar-chip"
          variant="ghost"
          size="small"
          :class="{ active: option.value === sortValue }"
          :disabled="loading"
          :aria-pressed="option.value === sortValue"
          @click="$emit('sort', option.value)"
        >
          {{ option.label }}
        </ScButton>
      </div>
    </div>

    <div v-if="hasResponsiveOverflow" class="toolbar-overflow">
      <ScIconButton
        ref="overflowMenuToggle"
        class="toolbar-overflow-toggle"
        appearance="toolbar-menu-toggle"
        :disabled="loading"
        :aria-expanded="overflowMenuOpen"
        :label="uiLabel('more_actions', '更多列表操作')"
        aria-controls="collection-toolbar-overflow"
        @click="toggleOverflowMenu"
      >
        <ScIcon name="menu" :size="18" />
      </ScIconButton>
      <div v-if="overflowMenuOpen" id="collection-toolbar-overflow" class="toolbar-overflow-menu" data-collection-toolbar-layer="overflow" :aria-label="uiLabel('more_actions', '更多列表操作')">
        <section v-if="showViewSwitch && viewModes.length > 1" class="toolbar-overflow-section">
          <p>{{ viewLabel }}</p>
          <ScButton
            v-for="mode in viewModes"
            :key="`overflow-view-mode-${mode}`"
            type="button"
            appearance="menu-item"
            variant="ghost"
            size="small"
            :class="{ active: currentViewMode === mode }"
            :disabled="loading"
            :aria-pressed="currentViewMode === mode"
            @click="selectOverflowView(mode)"
          >
            {{ viewModeLabels[mode] || mode }}
          </ScButton>
        </section>
        <section v-if="sortOptions.length" class="toolbar-overflow-section">
          <p>{{ sortLabel }}</p>
          <ScButton
            v-for="option in sortOptions"
            :key="`overflow-sort-${option.value}`"
            type="button"
            appearance="menu-item"
            variant="ghost"
            size="small"
            :class="{ active: option.value === sortValue }"
            :disabled="loading"
            :aria-pressed="option.value === sortValue"
            @click="selectOverflowSort(option.value)"
          >
            {{ option.label }}
          </ScButton>
        </section>
        <ScButton
          v-if="canCreateRecord"
          class="toolbar-overflow-create"
          type="button"
          variant="primary"
          size="small"
          :disabled="loading"
          @click="createFromOverflow"
        >
          <ScIcon name="plus" :size="16" />
          {{ createLabel }}
        </ScButton>
      </div>
    </div>

    <div v-if="canCreateRecord" class="toolbar-actions">
      <ScButton variant="primary" type="button" :disabled="loading" @click="$emit('create')">
        <ScIcon name="plus" :size="16" />
        {{ createLabel }}
      </ScButton>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import ScButton from '../design-system/ScButton.vue';
import ScCheckbox from '../design-system/ScCheckbox.vue';
import ScIcon from '../design-system/ScIcon.vue';
import ScIconButton from '../design-system/ScIconButton.vue';
import ScInput from '../design-system/ScInput.vue';
import ScInputGroup from '../design-system/ScInputGroup.vue';
import ScSelect from '../design-system/ScSelect.vue';

type SearchChip = { key: string; label: string };
type CustomOperator = { value: string; label: string; needs_value?: boolean };
type CustomFilterField = {
  field: string;
  label: string;
  type: string;
  operators?: CustomOperator[];
  choices?: Array<{ value: string; label: string }>;
};

const props = defineProps<{
  loading: boolean;
  showViewSwitch: boolean;
  viewLabel: string;
  viewModes: string[];
  currentViewMode: string;
  viewModeLabels: Record<string, string>;
  searchValue: string;
  searchPlaceholder: string;
  clearLabel: string;
  showFilter: boolean;
  filterLabel: string;
  filterPrimary: Array<{ key: string; label: string }>;
  filterOverflow: Array<{ key: string; label: string }>;
  activeFilterKey: string;
  showSavedFilter: boolean;
  savedFilterLabel: string;
  savedFilterPrimary: Array<{ key: string; label: string; isDefault?: boolean; isShared?: boolean }>;
  savedFilterOverflow: Array<{ key: string; label: string; isDefault?: boolean; isShared?: boolean }>;
  activeSavedFilterKey: string;
  sortLabel: string;
  sortOptions: Array<{ label: string; value: string }>;
  sortValue: string;
  showGroup: boolean;
  groupLabel: string;
  groupPrimary: Array<{ key: string; label: string }>;
  groupOverflow: Array<{ key: string; label: string }>;
  customFilterEnabled: boolean;
  customFilterLabel: string;
  customFilterFields: CustomFilterField[];
  customGroupEnabled: boolean;
  customGroupLabel: string;
  customGroupFields: Array<{ key: string; label: string }>;
  favoriteSaveEnabled: boolean;
  favoriteSaveLabel: string;
  activeCustomFilterLabel: string;
  activeGroupLabel: string;
  activeGroupKey: string;
  canCreateRecord: boolean;
  createLabel: string;
  totalCount?: number;
  activeConditionCount?: number;
  uiLabels?: Record<string, string>;
}>();

const emit = defineEmits<{
  'switch-view': [mode: string];
  'search-input': [value: string];
  'search-composition-start': [];
  'search-composition-end': [event: CompositionEvent];
  'search-submit': [];
  'clear-search': [];
  filter: [key: string];
  'clear-filter': [];
  'saved-filter': [key: string];
  'clear-saved-filter': [];
  sort: [value: string];
  group: [key: string];
  'clear-group': [];
  'custom-group': [payload: { key: string; label: string }];
  'custom-filter': [payload: { field: string; label: string; operator: string; value: unknown; domain: unknown[] }];
  'clear-custom-filter': [];
  'clear-all': [];
  'save-favorite': [payload: { name: string; isDefault: boolean; isShared: boolean }];
  create: [];
}>();

const searchMenuOpen = ref(false);
const overflowMenuOpen = ref(false);
const customFilterOpen = ref(false);
const favoriteSaveOpen = ref(false);
const customFilterField = ref('');
const customFilterOperator = ref('');
const customFilterValue = ref('');
const customGroupField = ref('');
const favoriteName = ref('');
const favoriteUseByDefault = ref(false);
const favoriteShared = ref(false);
const toolbarRoot = ref<HTMLElement | null>(null);
const searchMenuToggle = ref<HTMLButtonElement | null>(null);
const overflowMenuToggle = ref<HTMLButtonElement | null>(null);
const selectedSymbol = '已选';
const clearSymbol = '清除';

function uiLabel(key: string, fallback: string) {
  return String(props.uiLabels?.[key] || fallback).trim() || fallback;
}

const allFilterChips = computed(() => [...props.filterPrimary, ...props.filterOverflow]);
const allSavedFilterChips = computed(() => [...props.savedFilterPrimary, ...props.savedFilterOverflow]);
const menuGroupChips = computed(() => [...props.groupPrimary, ...props.groupOverflow]);
const allGroupChips = computed(() => [...menuGroupChips.value, ...props.customGroupFields]);
const activeCustomFilterField = computed(() =>
  props.customFilterFields.find((field) => field.field === customFilterField.value) || null,
);
const activeCustomFilterOperators = computed<CustomOperator[]>(() => {
  const operators = activeCustomFilterField.value?.operators || [];
  if (operators.length) return operators;
  return [{ value: '=', label: '等于', needs_value: true }];
});
const activeCustomFilterChoices = computed(() => activeCustomFilterField.value?.choices || []);
const customFilterInputType = computed(() => {
  const type = activeCustomFilterField.value?.type;
  if (type === 'date') return 'date';
  if (type === 'datetime') return 'datetime-local';
  if (type === 'integer' || type === 'float' || type === 'monetary') return 'number';
  return 'text';
});
const canApplyCustomFilter = computed(() =>
  Boolean(activeCustomFilterField.value && customFilterOperator.value && String(customFilterValue.value).trim()),
);
const activeFilterChip = computed<SearchChip | null>(() =>
  allFilterChips.value.find((chip) => chip.key === props.activeFilterKey) || null,
);
const activeSavedFilterChip = computed<SearchChip | null>(() =>
  allSavedFilterChips.value.find((chip) => chip.key === props.activeSavedFilterKey) || null,
);
const activeGroupChip = computed<SearchChip | null>(() =>
  allGroupChips.value.find((chip) => chip.key === props.activeGroupKey)
  || (props.activeGroupKey && props.activeGroupLabel ? { key: props.activeGroupKey, label: props.activeGroupLabel } : null),
);
const showFilterColumn = computed(() =>
  props.showFilter
  || allFilterChips.value.length > 0
  || props.customFilterEnabled,
);
const showGroupColumn = computed(() =>
  props.showGroup
  || allGroupChips.value.length > 0
  || props.customGroupEnabled,
);
const showSavedFilterColumn = computed(() =>
  props.showSavedFilter
  || allSavedFilterChips.value.length > 0
  || props.favoriteSaveEnabled,
);
const hasSearchMenu = computed(() =>
  showFilterColumn.value
  || showGroupColumn.value
  || showSavedFilterColumn.value,
);
const hasStructuredConditions = computed(() => Boolean(
  props.activeFilterKey
  || props.activeSavedFilterKey
  || props.activeCustomFilterLabel
  || props.activeGroupKey,
));
const hasResponsiveOverflow = computed(() =>
  (props.showViewSwitch && props.viewModes.length > 1)
  || props.sortOptions.length > 0
  || props.canCreateRecord,
);

function selectOverflowView(mode: string) {
  overflowMenuOpen.value = false;
  emit('switch-view', mode);
}

function selectOverflowSort(value: string) {
  overflowMenuOpen.value = false;
  emit('sort', value);
}

function createFromOverflow() {
  overflowMenuOpen.value = false;
  emit('create');
}

async function focusOpenLayer(selector: string) {
  await nextTick();
  toolbarRoot.value?.querySelector<HTMLElement>(selector)?.focus();
}

function toggleSearchMenu() {
  searchMenuOpen.value = !searchMenuOpen.value;
  overflowMenuOpen.value = false;
  if (searchMenuOpen.value) void focusOpenLayer('#collection-search-disclosure button:not(:disabled), #collection-search-disclosure select:not(:disabled), #collection-search-disclosure input:not(:disabled)');
}

function toggleOverflowMenu() {
  overflowMenuOpen.value = !overflowMenuOpen.value;
  searchMenuOpen.value = false;
  if (overflowMenuOpen.value) void focusOpenLayer('#collection-toolbar-overflow button:not(:disabled)');
}

function closeSearchMenuAndRestoreFocus() {
  searchMenuOpen.value = false;
  searchMenuToggle.value?.focus();
}

function selectFilter(key: string) {
  searchMenuOpen.value = false;
  emit('filter', key);
}

function selectSavedFilter(key: string) {
  searchMenuOpen.value = false;
  emit('saved-filter', key);
}

function selectGroup(key: string) {
  searchMenuOpen.value = false;
  emit('group', key);
}

function normalizeCustomValue(value: string): unknown {
  const type = activeCustomFilterField.value?.type;
  if (type === 'boolean') return value === 'true';
  if (type === 'integer') return Number.parseInt(value, 10);
  if (type === 'float' || type === 'monetary') return Number(value);
  return value;
}

function applyCustomFilter() {
  const field = activeCustomFilterField.value;
  if (!field || !canApplyCustomFilter.value) return;
  const value = normalizeCustomValue(customFilterValue.value);
  const domain = [[field.field, customFilterOperator.value, value]];
  searchMenuOpen.value = false;
  emit('custom-filter', {
    field: field.field,
    label: `${field.label} ${customFilterValue.value}`,
    operator: customFilterOperator.value,
    value,
    domain,
  });
}

function resetCustomFilter() {
  customFilterOpen.value = false;
  customFilterField.value = '';
  customFilterOperator.value = '';
  customFilterValue.value = '';
}

function applyCustomGroup() {
  const key = String(customGroupField.value || '').trim();
  if (!key) return;
  const found = props.customGroupFields.find((chip) => chip.key === key);
  searchMenuOpen.value = false;
  emit('custom-group', { key, label: found?.label || key });
}

function saveFavorite() {
  const name = favoriteName.value.trim();
  if (!name) return;
  searchMenuOpen.value = false;
  favoriteSaveOpen.value = false;
  emit('save-favorite', {
    name,
    isDefault: favoriteUseByDefault.value,
    isShared: favoriteShared.value,
  });
}

watch(activeCustomFilterField, (field) => {
  customFilterOperator.value = field?.operators?.[0]?.value || '=';
  customFilterValue.value = field?.type === 'boolean' ? 'true' : '';
});

function handleDocumentPointerDown(event: PointerEvent) {
  const root = toolbarRoot.value;
  if (!root || root.contains(event.target as Node | null)) return;
  searchMenuOpen.value = false;
  overflowMenuOpen.value = false;
}

function handleDocumentKeyDown(event: KeyboardEvent) {
  if (event.key !== 'Escape') return;
  if (searchMenuOpen.value) {
    closeSearchMenuAndRestoreFocus();
    return;
  }
  if (overflowMenuOpen.value) {
    overflowMenuOpen.value = false;
    overflowMenuToggle.value?.focus();
  }
}

onMounted(() => {
  document.addEventListener('pointerdown', handleDocumentPointerDown);
  document.addEventListener('keydown', handleDocumentKeyDown);
});

onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', handleDocumentPointerDown);
  document.removeEventListener('keydown', handleDocumentKeyDown);
});
</script>

<style scoped>
.action-toolbar {
  position: relative;
  z-index: 40;
  display: grid;
  grid-template-columns: max-content minmax(320px, 1fr) max-content max-content max-content;
  grid-template-areas: 'view search total sort primary';
  justify-content: stretch;
  align-items: center;
  gap: 8px;
  min-width: 0;
  max-width: 100%;
  border: 1px solid var(--sc-app-border);
  border-radius: 6px;
  background: var(--sc-app-panel);
  padding: 6px;
  box-shadow: none;
}

.action-toolbar--without-view {
  grid-template-columns: minmax(320px, 1fr) max-content max-content max-content;
  grid-template-areas: 'search total sort primary';
}

.view-switch { grid-area: view; }
.native-search { grid-area: search; }
.sort-switch { grid-area: sort; }
.toolbar-actions { grid-area: primary; }
.toolbar-overflow { grid-area: overflow; }
.toolbar-total { grid-area: total; color: var(--sc-app-text-secondary); font-size: 12px; font-variant-numeric: tabular-nums; white-space: nowrap; }

.toolbar-section,
.view-switch,
.filter-switch,
.saved-filter-switch,
.sort-switch,
.group-switch {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  flex-wrap: nowrap;
}

.view-switch {
  width: auto;
  max-width: 240px;
  white-space: nowrap;
}

.view-switch .contract-chips {
  flex-wrap: nowrap;
  gap: 4px;
}

.group-switch {
  flex-wrap: wrap;
}

.filter-switch,
.saved-filter-switch {
  flex-wrap: wrap;
}

.native-search {
  position: relative;
  display: flex;
  align-items: center;
  justify-self: stretch;
  width: 100%;
  min-width: 0;
  max-width: 100%;
}

.native-searchbox {
  display: flex;
  align-items: center;
  flex-wrap: nowrap;
  flex: 1 1 auto;
  min-width: 0;
  gap: 4px;
}

.collection-search-control {
  flex: 1 1 110px;
  min-width: 72px;
}

.collection-search-control__actions {
  display: inline-flex;
  align-items: stretch;
}

.toolbar-search-submit,
.toolbar-search-clear,
.toolbar-clear-all {
  flex: 0 0 auto;
  white-space: nowrap;
}

.toolbar-search-submit {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.search-facet {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  max-width: min(150px, 38%);
  white-space: nowrap;
}

.search-facet span:first-child {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}

.facet-remove {
  color: var(--sc-app-danger-text);
  font-weight: 700;
}

.search-menu-toggle {
  flex: 0 0 auto;
}

/* Search control renders as one seamless unit. The submit button's radius /
 * border are merged with the input in product-patterns.css (global layer, so
 * it can beat TDesign's .t-button radius rule); here only the square
 * search-menu toggle is pinned to the shared 36px control height (its default
 * min-height is 44px via --sc-component-button-touch-target). */
.collection-search-control button.search-menu-toggle {
  height: 36px;
  min-height: 36px;
  max-height: 36px;
  width: 36px;
}

.search-menu-caret {
  display: inline-block;
  line-height: 1;
  transition: transform var(--sc-motion-fast, 120ms) ease;
}

.search-menu-caret.is-open {
  transform: rotate(90deg);
}

.search-dropdown {
  position: absolute;
  top: calc(100% + 6px);
  left: 50%;
  transform: translateX(-50%);
  z-index: 80;
  display: grid;
  grid-template-columns: repeat(3, minmax(180px, 1fr));
  width: min(680px, calc(100vw - 32px));
  max-height: min(640px, calc(100vh - 120px));
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
  border: 1px solid var(--sc-app-border-strong);
  border-radius: 8px;
  background: var(--sc-app-panel);
  box-shadow: 0 16px 36px var(--sc-app-shadow);
  padding: 8px 0 12px;
}

.search-dropdown-section {
  min-width: 0;
}

.search-dropdown-section + .search-dropdown-section {
  border-left: 1px solid var(--sc-app-border);
}

.search-dropdown-title {
  margin: 0;
  padding: 5px 12px;
  color: var(--sc-app-text-secondary);
  font-size: 12px;
  font-weight: 700;
}

.search-dropdown-items {
  display: grid;
}

.search-menu-item {
  display: grid;
  grid-template-columns: 18px minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 6px;
  text-align: left;
  min-width: 0;
}

.search-menu-item span,
.contract-chip {
  min-width: 0;
  overflow-wrap: anywhere;
}

.search-menu-item.custom-entry {
  font-weight: 700;
}

.custom-search-panel {
  display: grid;
  gap: 6px;
  padding: 6px 12px 10px 36px;
}

.custom-group-select {
  width: 100%;
  min-width: 0;
}

.custom-group-select {
  margin: 7px 12px;
  width: calc(100% - 24px);
}

.custom-search-actions {
  display: flex;
  gap: 6px;
}

.search-menu-empty {
  margin: 0;
  padding: 7px 12px 7px 36px;
  color: var(--sc-app-text-secondary);
  font-size: 13px;
}

.menu-check {
  color: var(--sc-app-selected-text);
  font-weight: 700;
}

.menu-badge {
  margin-left: auto;
  border: 1px solid var(--sc-app-border);
  border-radius: 4px;
  color: var(--sc-app-text-secondary);
  padding: 1px 4px;
  font-size: 11px;
}

.toolbar-actions {
  display: flex;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 8px;
  min-width: 0;
  justify-self: end;
  width: 100%;
}

.contract-label {
  margin: 0;
  font-size: 13px;
  color: var(--sc-app-text-primary);
  white-space: nowrap;
}

.contract-chips {
  display: flex;
  flex-wrap: nowrap;
  gap: 5px;
  min-width: 0;
}

.contract-chips.overflow-row {
  flex: 1 1 100%;
  padding-left: 36px;
}

.contract-chip {
  max-width: 100%;
  white-space: nowrap;
}

.toolbar-overflow { position: relative; display: none; }
.toolbar-overflow-toggle { width: 44px; min-height: 44px; }
.toolbar-overflow-menu { position: absolute; z-index: 90; top: calc(100% + var(--sc-space-2xs)); right: 0; display: grid; gap: var(--sc-space-xs); min-width: 220px; max-height: min(420px, 70vh); overflow: auto; padding: var(--sc-space-xs); border: 1px solid var(--sc-app-border-strong); border-radius: var(--sc-product-radius-panel); background: var(--sc-app-panel); box-shadow: var(--sc-product-shadow-overlay); }
.toolbar-overflow-section { display: grid; gap: var(--sc-space-2xs); }
.toolbar-overflow-section p { margin: 0; color: var(--sc-app-text-secondary); font-size: 12px; font-weight: 700; }
.toolbar-overflow-section :deep(.sc-btn),
.toolbar-overflow-create { display: flex; align-items: center; gap: var(--sc-space-xs); width: 100%; min-height: 44px; }
.toolbar-overflow-create { display: none; }

@media (max-width: 1199px) {
  .action-toolbar {
    grid-template-columns: minmax(240px, 1fr) max-content max-content;
    grid-template-areas: 'search primary overflow';
  }

  .view-switch,
  .sort-switch { display: none; }

  .toolbar-overflow { display: block; }

  .native-search {
    width: 100%;
    min-width: 0;
  }

  .search-facet {
    max-width: 34%;
  }

  .native-searchbox {
    min-width: 0;
  }

  .toolbar-search-submit {
    min-height: 44px;
  }

  .search-menu-toggle {
    width: 44px;
    min-height: 44px;
  }

  .search-dropdown {
    left: 0;
    transform: none;
    grid-template-columns: 1fr;
    width: min(520px, 92vw);
    max-height: min(560px, calc(100vh - 132px));
  }

  .search-dropdown-section + .search-dropdown-section {
    border-left: 0;
    border-top: 1px solid var(--sc-app-border);
  }
}

@media (max-width: 760px) {
  .action-toolbar,
  .action-toolbar--without-view {
    grid-template-columns: minmax(190px, 1fr) max-content;
    grid-template-areas:
      'search overflow'
      'primary primary';
  }
  .toolbar-actions { display: flex; justify-self: stretch; }
  .toolbar-actions :deep(.sc-btn) { width: 100%; }
  .toolbar-overflow-create { display: none; }
  .toolbar-search-clear,
  .toolbar-clear-all { display: none; }
  .toolbar-search-submit { width: 44px; min-height: 44px; padding-inline: 0; font-size: 0; justify-content: center; }
  .search-menu-toggle { width: 44px; min-height: 44px; }
  .search-menu-item,
  .toolbar-overflow-section :deep(.sc-btn),
  .toolbar-overflow-create,
  .custom-search-actions :deep(.sc-btn) { min-height: 44px; }
}

@media (prefers-reduced-motion: reduce) {
  .search-menu-caret { transition: none; }
}
</style>
