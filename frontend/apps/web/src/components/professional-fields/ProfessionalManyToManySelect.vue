<template>
  <div
    class="professional-m2m-select"
    data-semantic-component="ProfessionalManyToManySelect"
    data-semantic-layer="professional-field"
    :data-readonly="field.readonly || undefined"
    :data-busy="adapter.busy || undefined"
  >
    <!-- 只读态：标签展示 -->
    <div v-if="field.readonly" class="m2m-readonly">
      <span
        v-for="option in selectedOptions"
        :key="`m2m-ro-${field.name}-${option.id}`"
        class="m2m-readonly-tag"
        :style="tagColorStyle(option.color)"
      >{{ option.label }}</span>
      <span v-if="!selectedOptions.length && adapter.relationIds(field.name).length" class="m2m-readonly-summary">
        已关联 {{ adapter.relationIds(field.name).length }} 条
      </span>
      <span v-else-if="!selectedOptions.length" class="m2m-readonly-empty">暂无</span>
    </div>

    <!-- 编辑态：TDesign Select 多选 -->
    <TDesignSelect
      v-else
      ref="selectRef"
      v-model="selectedIds"
      :options="selectOptions"
      multiple
      filterable
      :placeholder="field.inputPlaceholder || `选择${field.label || ''}`"
      :disabled="adapter.busy"
      :clearable="false"
      :min-collapsed-num="3"
      size="medium"
      class="m2m-select"
      @search="onSearch"
      @change="onChange"
      @focus="onFocus"
      @blur="onBlur"
    >
      <!-- 自定义选项模板：支持颜色标识 -->
      <template #option="{ option }">
        <div class="m2m-option" :class="{ 'm2m-option-create': option.isCreate }">
          <span v-if="option.color !== undefined" class="m2m-option-swatch" :style="tagColorStyle(option.color)" />
          <span class="m2m-option-label">{{ option.label }}</span>
          <span v-if="option.isCreate" class="m2m-option-hint">回车创建</span>
        </div>
      </template>
    </TDesignSelect>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { TDesignSelect } from '../design-system/tdesignPrimitiveBridge';
import type { FormSectionFieldSchema } from '../template/formSection.types';
import type { RelationFieldAdapter } from '../template/relationField.types';

interface RelationOption {
  id: number;
  label: string;
  color?: unknown;
}

interface SelectOption {
  value: string;
  label: string;
  color?: unknown;
  isCreate?: boolean;
  disabled?: boolean;
}

const props = defineProps<{
  field: FormSectionFieldSchema;
  adapter: RelationFieldAdapter;
}>();

const selectRef = ref<InstanceType<typeof TDesignSelect> | null>(null);
const focused = ref(false);

// ===== 数据适配 =====
const selectedIds = computed<(string | number)[]>({
  get: () => props.adapter.relationIds(props.field.name).map(String),
  set: (ids) => {
    const numericIds = ids.map((id) => Number(id)).filter((id) => Number.isFinite(id));
    props.adapter.setRelationIds(props.field.name, numericIds);
  },
});

const selectedOptions = computed<RelationOption[]>(() =>
  props.adapter.selectedRelationOptions(props.field.name) || [],
);

const filteredOptions = computed<RelationOption[]>(() =>
  props.adapter.filteredRelationOptions(props.field.name) || [],
);

const canInlineCreate = computed(() =>
  Boolean(props.adapter.canInlineCreateRelation?.(props.field.name)),
);

const createOption = computed<SelectOption | null>(() => {
  if (!canInlineCreate.value) return null;
  const keyword = props.adapter.relationKeyword(props.field.name)?.trim();
  if (!keyword) return null;
  // 搜索无精确匹配时显示创建选项
  const exactMatch = filteredOptions.value.some(
    (opt) => opt.label.trim().toLowerCase() === keyword.toLowerCase(),
  );
  if (exactMatch) return null;
  return {
    value: `__create__${keyword}`,
    label: `创建「${keyword}」`,
    isCreate: true,
  };
});

const selectOptions = computed<SelectOption[]>(() => {
  const options: SelectOption[] = filteredOptions.value.map((opt) => ({
    value: String(opt.id),
    label: opt.label,
    color: opt.color,
  }));
  if (createOption.value) {
    options.push(createOption.value);
  }
  return options;
});

// ===== 事件处理 =====
function onSearch(keyword: string) {
  props.adapter.setRelationKeyword(props.field.name, keyword || '');
}

function onChange(value: (string | number)[]) {
  // 检查是否选择了创建选项
  const createVal = value.find((v) => String(v).startsWith('__create__'));
  if (createVal) {
    const keyword = String(createVal).replace('__create__', '');
    // 移除创建选项，触发快速创建
    const normalIds = value.filter((v) => !String(v).startsWith('__create__'));
    selectedIds.value = normalIds;
    if (keyword && canInlineCreate.value) {
      props.adapter.setRelationKeyword(props.field.name, keyword);
      props.adapter.quickCreateRelationMany?.(props.field.name);
    }
    return;
  }
  // 普通选择：同步到 adapter
  const numericIds = value.map((id) => Number(id)).filter((id) => Number.isFinite(id));
  props.adapter.setRelationIds(props.field.name, numericIds);
}

function onFocus() {
  focused.value = true;
  // 聚焦时清空搜索关键词以展示全部选项
  if (!props.adapter.relationKeyword(props.field.name)) {
    props.adapter.setRelationKeyword(props.field.name, '');
  }
}

// 组件挂载时预加载选项数据（空状态字段不会在 hydrate 时加载）
onMounted(() => {
  if (!props.field.readonly) {
    props.adapter.setRelationKeyword(props.field.name, '');
  }
});

function onBlur() {
  focused.value = false;
  // 失焦时清空搜索关键词
  setTimeout(() => {
    if (!focused.value) {
      props.adapter.setRelationKeyword(props.field.name, '');
    }
  }, 200);
}

// ===== 工具函数 =====
function tagColorStyle(color: unknown): Record<string, string> {
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
  ];
  const bg = palette[Math.abs(Math.trunc(idx)) % palette.length];
  return { '--tag-bg': bg, backgroundColor: bg };
}

// 当 adapter 外部更新 relationIds 时，确保 v-model 同步
watch(
  () => props.adapter.relationIds(props.field.name),
  () => {
    // selectedIds 是 computed，自动响应
  },
);
</script>

<style scoped>
.professional-m2m-select {
  width: 100%;
  min-width: 0;
}

.m2m-select {
  width: 100%;
}

/* 只读态 */
.m2m-readonly {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  min-height: 32px;
  align-items: center;
}

.m2m-readonly-tag {
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 13px;
  line-height: 1.6;
  background: var(--sc-app-muted-bg);
  color: var(--sc-app-text-primary);
}

.m2m-readonly-summary,
.m2m-readonly-empty {
  font-size: 13px;
  color: var(--sc-app-text-secondary);
}

/* 选项样式 */
.m2m-option {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}

.m2m-option-swatch {
  width: 10px;
  height: 10px;
  border-radius: 2px;
  flex-shrink: 0;
}

.m2m-option-label {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.m2m-option-create {
  border-top: 1px solid var(--sc-app-border);
  padding-top: 8px;
  margin-top: 4px;
}

.m2m-option-hint {
  font-size: 12px;
  color: var(--sc-app-text-secondary);
  flex-shrink: 0;
}

</style>
