<template>
  <div v-if="field.type === 'many2many'" class="relation-editor">
    <div v-if="field.readonly" class="relation-readonly" data-readonly-relation>
      <span
        v-for="option in adapter.selectedRelationOptions(field.name)"
        :key="`${field.name}-readonly-${option.id}`"
        class="relation-readonly-item"
      >{{ option.label }}</span>
      <span
        v-if="!adapter.selectedRelationOptions(field.name).length && adapter.relationIds(field.name).length"
        class="relation-readonly-summary"
      >已关联 {{ adapter.relationIds(field.name).length }} 条</span>
      <ScInlineState
        v-else-if="!adapter.selectedRelationOptions(field.name).length"
        class="relation-readonly-empty"
        state="empty"
        label="暂无记录"
      />
    </div>
    <div v-else-if="isMany2manyTags(field)" class="relation-tag-picker">
      <div class="relation-tags-control">
        <div v-if="adapter.selectedRelationOptions(field.name).length" class="relation-tag-list">
          <ScButton
            v-for="option in adapter.selectedRelationOptions(field.name)"
            :key="`${field.name}-tag-${option.id}`"
            type="button"
            class="relation-tag"
            appearance="relation-tag"
            variant="ghost"
            size="small"
            :style="tagColorStyle(option.color)"
            :disabled="adapter.busy"
            :title="`移除${option.label}`"
            @click="toggleRelationId(field.name, option.id, false)"
          >
            {{ option.label }}
            <ScIcon name="close" :size="14" />
          </ScButton>
        </div>
        <ScInput
          class="relation-tags-input"
          appearance="relation-tag-entry"
          type="text"
          :model-value="adapter.relationKeyword(field.name)"
          :placeholder="field.inputPlaceholder || adapter.inputPlaceholder(field.label)"
          @update:model-value="adapter.setRelationKeyword(field.name, $event)"
          @keydown.enter.prevent="commitTagKeyword(field.name)"
        />
        <div v-if="hasTagDropdown(field.name)" class="relation-tag-dropdown">
          <ScButton
            v-for="option in adapter.filteredRelationOptions(field.name).slice(0, 8)"
            :key="`${field.name}-tag-option-${option.id}`"
            type="button"
            class="relation-tag-option"
            appearance="menu-item"
            variant="ghost"
            size="small"
            @mousedown.prevent
            @click="toggleRelationId(field.name, option.id, true)"
          >
            <span class="relation-tag-swatch" :style="tagColorStyle(option.color)" aria-hidden="true"></span>
            <span>{{ option.label }}</span>
          </ScButton>
          <div v-if="hasTagCreateActions(field.name)" class="relation-tag-actions">
            <div
              v-if="adapter.canInlineCreateRelation(field.name)"
              class="relation-tag-hint"
              role="note"
            >
              {{ adapter.relationInlineCreateLabel(field.name) }}
            </div>
            <ScButton
              v-if="adapter.relationCreateMode(field.name) === 'page'"
              type="button"
              class="relation-tag-action"
              variant="secondary"
              size="small"
              @mousedown.prevent
              @click="adapter.openRelationCreate(field.name)"
            >
              {{ adapter.relationCreateLabel(field.name) }}
            </ScButton>
          </div>
        </div>
      </div>
    </div>
    <div v-else class="relation-select-editor">
      <ScInput
        class="relation-search"
        type="text"
        :model-value="adapter.relationKeyword(field.name)"
        :placeholder="field.inputPlaceholder || adapter.inputPlaceholder(field.label)"
        @update:model-value="adapter.setRelationKeyword(field.name, $event)"
      />
      <div
        v-if="adapter.filteredRelationOptions(field.name).length"
        class="relation-multi-options"
        role="listbox"
        aria-multiselectable="true"
        :aria-label="field.label || `${field.name} 选项列表`"
      >
        <ScCheckbox
          v-for="option in adapter.filteredRelationOptions(field.name)"
          :key="`${field.name}-${option.id}`"
          :checked="relationIdSet(field.name).has(option.id)"
          :disabled="adapter.busy"
          :label="option.label"
          @change="toggleRelationId(field.name, option.id, $event)"
        />
      </div>
    </div>
  </div>
  <div v-else-if="field.type === 'one2many'" class="relation-editor">
    <div v-if="field.readonly" class="o2m-readonly" data-readonly-relation>
      <div v-if="adapter.visibleOne2manyRows(field.name).length" class="o2m-readonly-list">
        <article
          v-for="row in paginatedOne2manyRows"
          :key="row.key"
          class="o2m-readonly-row"
        >
          <p v-if="adapter.one2manyRowStateLabel(row)" class="o2m-readonly-state">
            {{ adapter.one2manyRowStateLabel(row) }}
          </p>
          <dl class="o2m-readonly-facts">
            <div
              v-for="column in adapter.one2manyColumns(field.name)"
              :key="`${row.key}-readonly-${column.name}`"
              class="o2m-readonly-fact"
            >
              <dt>{{ column.label }}</dt>
              <dd>{{ adapter.one2manyColumnDisplayValue(column, row.values[column.name]) || '—' }}</dd>
            </div>
          </dl>
        </article>
      </div>
      <ScInlineState v-else class="relation-readonly-empty" state="empty" label="暂无记录" data-readonly-relation-empty />
    </div>
    <template v-else>
    <div class="o2m-toolbar">
      <ScButton
        v-if="adapter.one2manyCanCreate(field.name)"
        class="o2m-create"
        type="button"
        variant="primary"
        size="small"
        :disabled="adapter.busy"
        @click="adapter.addOne2manyRow(field.name)"
      >
        {{ adapter.one2manyCreateLabel(field.name, field.label) }}
      </ScButton>
      <span v-if="adapter.one2manySummary(field.name)" class="o2m-summary">{{ adapter.one2manySummary(field.name) }}</span>
    </div>
    <div v-if="adapter.one2manyColumns(field.name).length" class="o2m-header">
      <span class="o2m-header-cell">状态</span>
      <span class="o2m-header-fields">
        <span
          v-for="column in adapter.one2manyColumns(field.name)"
          :key="`${field.name}-header-${column.name}`"
          class="o2m-header-cell"
        >{{ column.label }}</span>
      </span>
      <span class="o2m-header-cell o2m-header-action">操作</span>
    </div>
    <div class="o2m-list">
      <div v-for="row in paginatedOne2manyRows" :key="row.key" class="o2m-row">
        <p class="o2m-row-state">{{ adapter.one2manyRowStateLabel(row) }}</p>
        <div class="o2m-fields">
          <label
            v-for="column in adapter.one2manyColumns(field.name)"
            :key="`${row.key}-${column.name}`"
            class="o2m-field"
          >
            <span class="meta">{{ column.label }}</span>
            <ScCheckbox
              v-if="column.ttype === 'boolean'"
              class="input-checkbox"
              :disabled="column.readonly || adapter.busy"
              :checked="Boolean(row.values[column.name])"
              :label="column.label"
              @change="adapter.setOne2manyRowField(field.name, row.key, column, $event)"
            />
            <ScSelect
              v-else-if="column.ttype === 'selection'"
              :disabled="column.readonly || adapter.busy"
              :model-value="String(row.values[column.name] ?? '')"
              :placeholder="adapter.selectPlaceholder(column.label)"
              :options="(column.selection || []).map((option) => ({ value: String(option[0]), label: String(option[1]) }))"
              @update:model-value="adapter.setOne2manyRowField(field.name, row.key, column, $event)"
            />
            <ScInput
              v-else
              :type="adapter.one2manyColumnInputType(column)"
              :disabled="column.readonly || adapter.busy"
              :model-value="adapter.one2manyColumnDisplayValue(column, row.values[column.name])"
              :placeholder="column.label"
              @update:model-value="adapter.setOne2manyRowField(field.name, row.key, column, $event)"
            />
          </label>
        </div>
        <ScButton
          class="o2m-row-remove"
          type="button"
          variant="danger"
          size="small"
          :aria-label="`移除${adapter.one2manyRowLabel(field.name, row)}`"
          :disabled="adapter.busy"
          @click="adapter.removeOne2manyRow(field.name, row.key)"
        >移除本条</ScButton>
        <ScInlineState
          v-if="adapter.showOne2manyErrors && adapter.one2manyRowErrors(field.name, row.key).length"
          class="o2m-row-error"
          state="error"
          :label="adapter.one2manyRowErrors(field.name, row.key).join('；')"
        />
        <ScInlineState
          v-if="adapter.one2manyRowHints(field.name, row).length"
          class="o2m-row-hint"
          state="info"
          :label="adapter.one2manyRowHints(field.name, row).join('；')"
        />
      </div>
    </div>
    <div v-if="adapter.removedOne2manyRows(field.name).length" class="o2m-removed">
      <p class="meta">已移除 {{ adapter.removedOne2manyRows(field.name).length }} 行</p>
      <div class="chips">
        <ScButton
          v-for="row in adapter.removedOne2manyRows(field.name)"
          :key="`rm-${row.key}`"
          class="o2m-row-restore"
          type="button"
          variant="ghost"
          size="small"
          :disabled="adapter.busy"
          @click="adapter.restoreOne2manyRow(field.name, row.key)"
        >
          撤销移除 · {{ adapter.one2manyRowLabel(field.name, row) }} · 待删除
        </ScButton>
      </div>
    </div>
    </template>
    <nav v-if="one2manyPageCount > 1" class="o2m-pagination" aria-label="明细分页" data-detail-collection-pagination>
      <ScButton type="button" class="o2m-page-action" variant="ghost" size="small" :disabled="one2manyPage <= 1" @click="one2manyPage -= 1">上一页</ScButton>
      <span>第 {{ one2manyPage }} / {{ one2manyPageCount }} 页</span>
      <ScButton type="button" class="o2m-page-action" variant="ghost" size="small" :disabled="one2manyPage >= one2manyPageCount" @click="one2manyPage += 1">下一页</ScButton>
    </nav>
  </div>
  <ScInput
  v-else
    :model-value="adapter.inputFieldValue(field.name)"
    :type="adapter.fieldInputType(field.type)"
    :placeholder="adapter.inputPlaceholder(field.label)"
    @update:model-value="adapter.setTextField(field.name, $event)"
  />
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import type { FormSectionFieldSchema } from './formSection.types';
import ScButton from '../design-system/ScButton.vue';
import ScCheckbox from '../design-system/ScCheckbox.vue';
import ScIcon from '../design-system/ScIcon.vue';
import ScInput from '../design-system/ScInput.vue';
import ScInlineState from '../design-system/ScInlineState.vue';
import ScSelect from '../design-system/ScSelect.vue';
import type { X2ManyRelationRendererProps } from './relationField.types';

const props = defineProps<X2ManyRelationRendererProps>();
const one2manyPage = ref(1);
const one2manyPageSize = 20;
const one2manyRows = computed(() => props.field.type === 'one2many' ? props.adapter.visibleOne2manyRows(props.field.name) : []);
const one2manyPageCount = computed(() => Math.max(1, Math.ceil(one2manyRows.value.length / one2manyPageSize)));
const paginatedOne2manyRows = computed(() => {
  const start = (one2manyPage.value - 1) * one2manyPageSize;
  return one2manyRows.value.slice(start, start + one2manyPageSize);
});
watch(one2manyPageCount, (count) => {
  if (one2manyPage.value > count) one2manyPage.value = count;
});

function isMany2manyTags(field: FormSectionFieldSchema) {
  return String(field.widget || '').trim().toLowerCase() === 'many2many_tags';
}

function relationIdSet(name: string) {
  return new Set(props.adapter.relationIds(name));
}

function toggleRelationId(name: string, id: number, checked: boolean) {
  const current = relationIdSet(name);
  if (checked) {
    current.add(id);
  } else {
    current.delete(id);
  }
  props.adapter.setRelationIds(name, Array.from(current));
  props.adapter.setRelationKeyword(name, '');
}

function hasTagCreateActions(name: string) {
  const keyword = props.adapter.relationKeyword(name).trim();
  return Boolean(keyword) && (
    props.adapter.canInlineCreateRelation(name) || props.adapter.relationCreateMode(name) === 'page'
  );
}

function hasTagDropdown(name: string) {
  return props.adapter.filteredRelationOptions(name).length > 0 || hasTagCreateActions(name);
}

function commitTagKeyword(name: string) {
  const options = props.adapter.filteredRelationOptions(name);
  if (options.length === 1) {
    toggleRelationId(name, options[0].id, true);
  }
}

function tagColorStyle(color: unknown) {
  const idx = Number(color);
  if (!Number.isFinite(idx)) return {};
  const palette = [
    'var(--sc-app-muted-bg)',
    'var(--sc-app-danger-bg)',
    'var(--sc-app-warning-bg)',
    'var(--sc-app-info-bg)',
    'var(--sc-app-success-bg)',
    'var(--sc-app-subtle-bg)',
    'var(--sc-app-hover-bg)',
    'var(--sc-app-info-bg)',
    'var(--sc-app-muted-bg)',
    'var(--sc-app-warning-bg)',
    'var(--sc-app-danger-bg)',
    'var(--sc-app-border)',
  ];
  const bg = palette[Math.abs(Math.trunc(idx)) % palette.length];
  return { '--tag-bg': bg };
}
</script>

<style scoped>
.relation-editor {
  display: grid;
  gap: 6px;
}

.relation-readonly {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  min-height: 24px;
  align-items: center;
  color: var(--sc-app-text-primary);
}

.relation-readonly-item {
  padding: 3px 8px;
  border-radius: 999px;
  background: var(--sc-app-muted-bg);
}

.relation-readonly-summary,
.relation-readonly-empty {
  color: var(--sc-app-text-secondary);
}

.relation-readonly-empty {
  margin: 0;
  padding: 10px 12px;
  border: 1px dashed var(--sc-app-border);
  border-radius: 8px;
  background: var(--sc-app-muted-bg);
  font-size: 13px;
}

.o2m-readonly-list {
  display: grid;
  gap: 0;
  border: 1px solid var(--sc-app-border);
  border-radius: 6px;
  overflow: hidden;
}

.o2m-readonly-row {
  display: grid;
  grid-template-columns: minmax(72px, max-content) minmax(0, 1fr);
  gap: 12px;
  padding: 8px 12px;
  border: 0;
  border-bottom: 1px solid var(--sc-app-border);
  border-radius: 0;
  background: var(--sc-app-panel);
}

.o2m-readonly-row:last-child { border-bottom: 0; }

.o2m-readonly-state {
  margin: 0;
  color: var(--sc-app-text-secondary);
  font-size: 12px;
  white-space: nowrap;
}

.o2m-readonly-facts {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 6px 18px;
  margin: 0;
}

.o2m-readonly-fact {
  min-width: 0;
}

.o2m-readonly-fact dt,
.o2m-readonly-fact dd {
  margin: 0;
}

.o2m-readonly-fact dt {
  color: var(--sc-app-text-secondary);
  font-size: 12px;
}

.o2m-readonly-fact dd {
  margin-top: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--sc-app-text-primary);
  font-size: 14px;
}

@media (max-width: 760px) {
  .o2m-readonly-row { grid-template-columns: 1fr; gap: 6px; }
  .o2m-readonly-facts { grid-template-columns: 1fr; }
  .o2m-readonly-fact dd { white-space: normal; overflow-wrap: anywhere; }
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.relation-tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.relation-tag-picker,
.relation-select-editor {
  display: grid;
  gap: 8px;
}

.relation-multi-options {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: var(--sc-space-xs);
  max-height: 240px;
  overflow: auto;
  padding: var(--sc-space-sm);
  border: 1px solid var(--sc-app-border-strong);
  border-radius: var(--sc-product-radius-control);
  background: var(--sc-app-input-bg);
}

.relation-tags-control {
  position: relative;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  min-height: 40px;
  padding: 5px 8px;
  border: 1px solid var(--sc-app-border-strong);
  border-radius: 6px;
  background: var(--sc-app-input-bg);
}

.relation-tags-input {
  flex: 1 1 140px;
  min-width: 120px;
  line-height: 1.4;
}

.relation-tag-dropdown {
  position: absolute;
  z-index: var(--sc-component-relation-dropdown-z-index);
  top: calc(100% + 2px);
  left: 0;
  right: 0;
  display: none;
  max-height: var(--sc-component-relation-dropdown-max-height);
  overflow: auto;
  border: 1px solid var(--sc-app-border-strong);
  border-radius: 6px;
  background: var(--sc-app-panel);
  box-shadow: var(--sc-component-relation-dropdown-shadow);
}

.relation-tags-control:focus-within .relation-tag-dropdown {
  display: grid;
}

.relation-tag-hint {
  display: flex;
  align-items: center;
  gap: 7px;
  min-height: 32px;
  border: 0;
  border-bottom: 1px solid var(--sc-app-border);
  background: var(--sc-app-panel);
  padding: 6px 10px;
  color: var(--sc-app-text-primary);
  text-align: left;
  cursor: pointer;
  font-size: 12px;
  line-height: 1.25;
}

.relation-tag-actions {
  display: grid;
  border-top: 1px solid var(--sc-app-border);
}

.relation-tag-action {
  width: 100%;
  justify-content: flex-start;
}

.relation-tag-hint {
  color: var(--sc-app-text-secondary);
  cursor: default;
}

.relation-tag-swatch {
  flex: 0 0 auto;
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: var(--tag-bg, var(--sc-app-muted-bg));
  border: 1px solid var(--sc-app-border);
}

.relation-choice-panel {
  border: 1px solid var(--sc-app-border-strong);
  border-radius: 6px;
  background: var(--sc-app-panel);
}

.relation-choice-panel > summary {
  min-height: 32px;
  padding: 7px 10px;
  color: var(--sc-app-text-primary);
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
}

.relation-choice-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px 10px;
  max-height: 220px;
  overflow: auto;
  padding: 0 8px 8px;
}

.relation-choice {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  min-height: 28px;
  padding: 5px 8px;
  border: 1px solid var(--sc-app-border-strong);
  border-radius: 6px;
  background: var(--sc-app-input-bg);
  color: var(--sc-app-text-primary);
  font-size: 12px;
  line-height: 1.35;
}

.relation-choice-check {
  margin-top: 1px;
  flex: 0 0 auto;
}

.relation-tag {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  max-width: 100%;
  line-height: 1.35;
}

.meta {
  margin: 1px 0;
  color: var(--sc-app-text-secondary);
  font-size: 12px;
}

.required {
  color: var(--sc-app-danger-text);
  margin-left: 2px;
}

.o2m-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
}

.o2m-summary {
  font-size: 12px;
  color: var(--sc-app-text-secondary);
}

.o2m-header {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr) auto;
  align-items: stretch;
  gap: 1px;
  border: 1px solid var(--sc-app-border);
  background: var(--sc-app-border);
  overflow: hidden;
}

.o2m-header-fields {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 1px;
  min-width: 0;
  background: var(--sc-app-border);
}

.o2m-header-action {
  min-width: 76px;
  text-align: center;
}

.o2m-header-cell {
  min-height: 28px;
  padding: 6px 8px;
  background: var(--sc-app-muted-bg);
  color: var(--sc-app-text-secondary);
  font-size: 12px;
  line-height: 1.35;
  font-weight: 600;
}

.o2m-list {
  display: grid;
  gap: 6px;
}

.o2m-row {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr) auto;
  gap: 8px;
  align-items: center;
  padding: 4px 0;
  border-bottom: 1px solid var(--sc-app-border);
}

.o2m-row-state {
  margin: 0;
  font-size: 12px;
  color: var(--sc-app-text-secondary);
  white-space: nowrap;
}

.o2m-fields {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 6px;
  min-width: 0;
}

.o2m-field {
  display: grid;
  min-width: 0;
}

.o2m-field .meta {
  display: none;
}

.o2m-removed {
  display: grid;
  gap: 4px;
}

.o2m-row-error {
  grid-column: 1 / -1;
  margin: 0;
  color: var(--sc-app-danger-text);
  font-size: 12px;
}

.o2m-row-hint {
  grid-column: 1 / -1;
  margin: 0;
  color: var(--sc-app-warning-text);
  font-size: 12px;
}

.relation-search {
  font-size: 14px;
}

@media (max-width: 760px) {
  .o2m-header {
    display: none;
  }

  .o2m-row {
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: start;
    gap: 10px;
    padding: 12px;
    border: 1px solid var(--sc-app-border);
    border-radius: 8px;
    background: var(--sc-app-panel);
  }

  .o2m-row-state {
    grid-column: 1 / -1;
    padding-bottom: 7px;
    border-bottom: 1px solid var(--sc-app-border);
    font-weight: 600;
  }

  .o2m-row-remove {
    align-self: start;
    min-height: 44px;
    white-space: nowrap;
  }

  .o2m-create,
  .o2m-row-restore,
  .o2m-page-action {
    min-height: 44px;
  }

  .o2m-fields {
    grid-template-columns: 1fr;
  }

  .o2m-field {
    gap: 4px;
  }

  .o2m-field .meta {
    display: block;
  }
}

</style>
