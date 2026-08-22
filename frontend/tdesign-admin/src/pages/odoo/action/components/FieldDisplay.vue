<template>
  <span v-if="displayKind === 'status'" class="field-display field-display--status">
    <t-tag :theme="statusTheme" variant="light" size="small">{{ displayText }}</t-tag>
  </span>
  <span
    v-else-if="displayKind === 'direction'"
    class="field-display field-display--direction"
    :class="`is-${directionKind}`"
  >
    <span class="direction-icon" aria-hidden="true"
      ><t-icon :name="directionKind === 'in' ? 'arrow-down' : 'arrow-up'"
    /></span>
    <span>{{ displayText }}</span>
  </span>
  <span v-else-if="displayKind === 'selection'" class="field-display field-display--selection">
    <t-tag :theme="selectionTheme" variant="light" size="small">{{ displayText }}</t-tag>
  </span>
  <span v-else-if="displayKind === 'unit'" class="field-display field-display--unit">
    <t-tag :theme="unitTheme" variant="light" size="small">{{ displayText }}</t-tag>
  </span>
  <t-tag
    v-else-if="normalizedType === 'boolean'"
    :theme="Boolean(value) ? 'success' : 'default'"
    variant="light"
    size="small"
  >
    {{ Boolean(value) ? '是' : '否' }}
  </t-tag>
  <span v-else class="field-display">{{ displayText }}</span>
</template>
<script setup lang="ts">
import { computed } from 'vue';

import { normalizeFieldType } from '@/runtime/fieldType';

type Dict = Record<string, any>;

const props = defineProps<{
  value: unknown;
  fieldCode?: string;
  fieldLabel?: string;
  fieldType?: string;
  config?: Dict;
  relationOptions?: Array<{ label: string; value: string | number }>;
}>();

const normalizedCode = computed(() => String(props.fieldCode || '').toLowerCase());
const normalizedLabel = computed(() => String(props.fieldLabel || '').toLowerCase());
const normalizedType = computed(() => normalizeFieldType(props.fieldType));
const rawText = computed(() => {
  const value = props.value;
  if (value === null || value === undefined || value === false || value === '') return '—';
  if (Array.isArray(value)) {
    if (value.length === 2 && typeof value[1] === 'string') return value[1];
    return (
      value
        .map((item) =>
          Array.isArray(item)
            ? item[1]
            : typeof item === 'object' && item
              ? (item as Dict).display_name || (item as Dict).name
              : item,
        )
        .filter(Boolean)
        .join(', ') || '—'
    );
  }
  if (typeof value === 'object') {
    const item = value as Dict;
    return String(item.display_name || item.name || item.label || JSON.stringify(value));
  }
  const relation = props.relationOptions?.find((item) => String(item.value) === String(value));
  if (relation) return relation.label;
  const selection = props.config?.selection;
  if (Array.isArray(selection)) {
    const match = selection.find((item) => Array.isArray(item) && String(item[0]) === String(value));
    if (match) return String(match[1]);
    const row = selection.find(
      (item) =>
        item && typeof item === 'object' && String((item as Dict).value ?? (item as Dict).key) === String(value),
    );
    if (row) return String((row as Dict).label ?? (row as Dict).value ?? value);
  }
  return String(value);
});
const statusValue = computed(() => `${normalizedCode.value} ${normalizedLabel.value} ${rawText.value}`.toLowerCase());
const isStatusField = computed(
  () =>
    /(?:^|[._-])(?:state|status|stage|phase|approval_state|workflow_state)(?:[._-]|$)/.test(normalizedCode.value) ||
    /状态|审核|审批|进度|阶段|履行|发布|结算状态/.test(normalizedLabel.value) ||
    /^(?:草稿|待审核|审批中|审核中|已审核|审核通过|审核失败|已驳回|待履行|履行中|已完成|已取消|已作废|生效|已发布)$/.test(
      rawText.value,
    ),
);
const isDirectionField = computed(
  () =>
    /direction|payment_type|receipt|pay_type|inout|income|expense/.test(normalizedCode.value) ||
    /收付款|收支|方向/.test(normalizedLabel.value),
);
const directionKind = computed<'in' | 'out' | ''>(() => {
  if (!isDirectionField.value) return '';
  if (/收款|收入|流入|inbound|income|receipt|receive|入账/.test(statusValue.value)) return 'in';
  if (/付款|支出|流出|outbound|expense|pay|出账/.test(statusValue.value)) return 'out';
  return '';
});
const isSelectionField = computed(() => normalizedType.value === 'selection' || Array.isArray(props.config?.selection));
const isUnitField = computed(
  () =>
    /(?:^|[._-])(?:unit|uom|measure|measurement)(?:[._-]|$)/.test(normalizedCode.value) ||
    /单位|计量单位|度量单位/.test(normalizedLabel.value),
);
const displayKind = computed(() => {
  if (directionKind.value) return 'direction';
  if (isStatusField.value) return 'status';
  if (isSelectionField.value) return 'selection';
  if (isUnitField.value) return 'unit';
  return 'text';
});
const displayText = computed(() => rawText.value);
const statusTheme = computed<'success' | 'warning' | 'danger' | 'primary'>(() => {
  const text = statusValue.value;
  if (/失败|驳回|拒绝|作废|取消|error|fail|reject|cancel/.test(text)) return 'danger';
  if (/待|草稿|draft|pending|wait|review|审核中|审批中/.test(text)) return 'warning';
  if (/完成|通过|批准|生效|发布|履行中|执行中|success|done|approved|effective|active/.test(text)) return 'success';
  return 'primary';
});
const selectionTheme = computed<'success' | 'warning' | 'danger' | 'primary'>(() => {
  const text = `${normalizedCode.value} ${normalizedLabel.value} ${displayText.value}`.toLowerCase();
  if (/联营|合作|joint|partner/.test(text)) return 'success';
  if (/分包|代建|委托|subcontract|entrust/.test(text)) return 'warning';
  if (/停用|禁用|inactive|disabled/.test(text)) return 'danger';
  if (/直营|自营|公司|direct|self/.test(text)) return 'primary';
  const themes = ['primary', 'success', 'warning'] as const;
  const hash = [...displayText.value].reduce((sum, character) => sum + character.charCodeAt(0), 0);
  return themes[hash % themes.length];
});
const unitTheme = computed<'success' | 'warning' | 'danger' | 'primary'>(() => {
  const text = displayText.value.toLowerCase();
  if (/m²|平方米|㎡|吨|kg|公斤|t\b/.test(text)) return 'success';
  if (/m³|立方|方|l\b|升/.test(text)) return 'warning';
  if (/[项套件个台组]/.test(text)) return 'primary';
  if (/[天月年]|小时|h\b/.test(text)) return 'danger';
  return 'primary';
});
</script>
<style scoped>
.field-display {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  line-height: 1.5;
}

.field-display--status :deep(.t-tag) {
  min-width: 56px;
  justify-content: center;
  font-weight: 500;
}

.field-display--direction {
  gap: 6px;
  font-weight: 500;
}

.direction-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border-radius: 50%;
}

.is-in {
  color: var(--td-success-color-7);
}

.is-in .direction-icon {
  color: var(--td-success-color-6);
  background: var(--td-success-color-2);
}

.is-out {
  color: var(--td-error-color-7);
}

.is-out .direction-icon {
  color: var(--td-error-color-6);
  background: var(--td-error-color-2);
}
</style>
