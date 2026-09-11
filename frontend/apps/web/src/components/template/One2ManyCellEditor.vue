<template>
  <div
    class="o2m-cell-editor"
    data-semantic-component="One2ManyCellEditor"
    :data-validation-target="validationTarget"
    :data-relation-query-diagnostic="relationQueryDiagnostic || undefined"
  >
    <ScCheckbox
      v-if="column.ttype === 'boolean'"
      class="input-checkbox"
      :disabled="column.readonly || !adapter.one2manyCanInlineEdit(fieldName) || adapter.busy"
      :checked="Boolean(value)"
      :label="column.label"
      @change="$emit('update', $event)"
    />
    <ScSelect
      v-else-if="column.ttype === 'many2one'"
      :model-value="relationValue"
      :options="relationOptions"
      :required="column.required"
      :invalid="Boolean(errorText)"
      :described-by="errorId"
      :disabled="column.readonly || !adapter.one2manyCanInlineEdit(fieldName) || adapter.busy"
      filterable
      :loading="relationLoading"
      :empty-text="relationEmptyText"
      :placeholder="relationPlaceholder"
      :title="column.disabledReason || relationDisplayLabel"
      @update:model-value="$emit('update', $event)"
      @search="$emit('search', $event)"
      @popup-visible-change="$emit('popup-change', { ...$event, ownerId: popupOwnerId })"
    />
    <ScSelect
      v-else-if="column.ttype === 'selection'"
      :disabled="column.readonly || !adapter.one2manyCanInlineEdit(fieldName) || adapter.busy"
      :required="column.required"
      :invalid="Boolean(errorText)"
      :described-by="errorId"
      :model-value="String(value ?? '')"
      :placeholder="adapter.selectPlaceholder(column.label)"
      :options="(column.selection || []).map((option) => ({ value: String(option[0]), label: String(option[1]) }))"
      :title="selectionDisplayLabel"
      @update:model-value="$emit('update', $event)"
    />
    <ScInput
      v-else
      :appearance="amount ? 'numeric-entry' : 'default'"
      :align="amount ? 'right' : 'left'"
      :type="adapter.one2manyColumnInputType(column)"
      :disabled="column.readonly || !adapter.one2manyCanInlineEdit(fieldName) || adapter.busy"
      :required="column.required"
      :status="errorText ? 'error' : 'default'"
      :described-by="errorId"
      :title="column.disabledReason || readonlyReason || cellDisplayValue"
      :model-value="adapter.one2manyColumnDisplayValue(column, value)"
      :placeholder="column.label"
      @update:model-value="$emit('update', $event)"
    />
    <span v-if="errorText" :id="errorId" class="o2m-cell-error" role="alert">{{ errorText }}</span>
    <span v-if="relationError" class="o2m-relation-failure" role="alert" data-relation-query-state="error">
      <span>{{ relationError }}</span>
      <ScButton type="button" variant="ghost" size="small" @click="$emit('retry')">重试</ScButton>
    </span>
    <span v-else-if="showReadonlyReason && (column.disabledReason || readonlyReason)" class="o2m-disabled-reason">
      {{ column.disabledReason || readonlyReason }}
    </span>
  </div>
</template>

<script setup lang="ts">
import { computed, getCurrentInstance, onBeforeUnmount } from 'vue';
import ScButton from '../design-system/ScButton.vue';
import ScCheckbox from '../design-system/ScCheckbox.vue';
import ScInput from '../design-system/ScInput.vue';
import ScSelect from '../design-system/ScSelect.vue';
import type { RelationFieldAdapter, RelationFieldColumn } from './relationField.types';

const props = withDefaults(defineProps<{
  adapter: RelationFieldAdapter;
  fieldName: string;
  rowKey: string;
  column: RelationFieldColumn;
  value: unknown;
  amount?: boolean;
  error?: string;
  relationError?: string;
  errorId: string;
  validationTarget: string;
  relationOptions?: ReadonlyArray<{ value: string | number; label: string; disabled?: boolean }>;
  relationLoading?: boolean;
  relationEmptyText?: string;
  relationPlaceholder?: string;
  relationQueryDiagnostic?: string;
  showReadonlyReason?: boolean;
}>(), {
  amount: false,
  error: '',
  relationError: '',
  relationOptions: () => [],
  relationLoading: false,
  relationEmptyText: '暂无可选内容',
  relationPlaceholder: '',
  relationQueryDiagnostic: '',
  showReadonlyReason: false,
});

const emit = defineEmits<{
  update: [value: unknown];
  search: [keyword: string];
  'popup-change': [event: { visible: boolean; ownerId: string; trigger: string }];
  retry: [];
}>();

const popupOwnerId = `o2m-editor-${getCurrentInstance()?.uid ?? 'unknown'}`;

onBeforeUnmount(() => emit('popup-change', { visible: false, ownerId: popupOwnerId, trigger: 'owner-unmount' }));

const errorText = computed(() => props.error);
const relationValue = computed(() => {
  const raw = Array.isArray(props.value) ? props.value[0] : props.value;
  const parsed = Number(raw);
  return Number.isFinite(parsed) && parsed > 0 ? Math.trunc(parsed) : '';
});
const readonlyReason = computed(() => props.column.readonly ? '此字段目前仅供查看' : '');
const cellDisplayValue = computed(() => props.adapter.one2manyColumnDisplayValue(props.column, props.value));
const relationDisplayLabel = computed(() => {
  const selected = props.relationOptions.find((option) => String(option.value) === String(relationValue.value));
  return String(selected?.label || cellDisplayValue.value || '');
});
const selectionDisplayLabel = computed(() => {
  const selected = (props.column.selection || []).find((option) => String(option[0]) === String(props.value ?? ''));
  return String(selected?.[1] || cellDisplayValue.value || '');
});
</script>

<style scoped>
.o2m-cell-editor { min-width: 0; }
.o2m-cell-error,
.o2m-disabled-reason { display: block; margin-top: 4px; font-size: 12px; line-height: 1.35; }
.o2m-cell-error { color: var(--sc-app-danger-text); }
.o2m-disabled-reason { color: var(--sc-app-text-secondary); }
.o2m-relation-failure { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-top: 4px; color: var(--sc-app-danger-text); font-size: 12px; line-height: 1.35; }
</style>
