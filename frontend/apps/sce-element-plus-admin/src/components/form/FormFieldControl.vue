<template>
  <div class="field-control" :data-component-key="componentKey">
    <status-field
      v-if="statusWidgets.includes(fieldWidget)"
      :field="field"
      :model-value="modelValue"
      :widget="fieldWidget as 'statusbar' | 'badge' | 'statinfo' | 'status_with_color'"
      :readonly="readonly"
      @update:model-value="update"
      @change="change"
    />
    <attachment-field
      v-else-if="fieldWidget === 'many2many_binary'"
      :model-value="modelValue"
      :model="model"
      :record-id="recordId"
      :readonly="readonly"
      @update:model-value="update"
      @change="change"
      @uploaded="$emit('uploaded')"
    />
    <rich-text-field
      v-else-if="fieldWidget === 'html' || field.type === 'html'"
      :model-value="modelValue"
      :readonly="readonly"
      @update:model-value="update"
      @change="change"
    />
    <image-field
      v-else-if="fieldWidget === 'image'"
      :model-value="modelValue"
      :readonly="readonly"
      :mimetype="String(field.config.mimetype || field.config.image_mimetype || '')"
      @update:model-value="update"
      @change="change"
    />
    <json-field
      v-else-if="fieldWidget === 'json' || field.type === 'json'"
      :model-value="modelValue"
      :readonly="readonly"
      @update:model-value="update"
      @change="change"
    />
    <div
      v-else-if="readonly && !isCollection && componentKey !== 'sc.input.binary'"
      class="readonly-value"
    >
      {{ displayFieldValue(modelValue, field.code, field.selection, field.type) }}
    </div>
    <relation-field
      v-else-if="
        field.type !== 'selection' &&
        (componentKey === 'sc.select.remote' || componentKey === 'sc.input.many2one' || field.type === 'many2one')
      "
      :field="field"
      :model-value="modelValue"
      :disabled="readonly"
      :values="values"
      :context="context"
      :domain-patch="relationDomain"
      @update:model-value="update"
      @change="change"
    />
    <x2-many-editor
      v-else-if="isCollection"
      :field="field"
      :model-value="modelValue"
      :disabled="readonly"
      :values="values"
      :context="context"
      :domain-patch="relationDomain"
      :allow-view-edit="allowViewEdit"
      @request-edit="$emit('request-edit', $event)"
      @update:model-value="update"
      @change="change"
    />
    <binary-field
      v-else-if="componentKey === 'sc.input.binary' || field.type === 'binary'"
      :model="model"
      :record-id="recordId"
      :disabled="readonly"
      @uploaded="$emit('uploaded')"
    />
    <el-select
      v-else-if="field.selection.length || field.type === 'selection'"
      :model-value="modelValue"
      filterable
      clearable
      :disabled="readonly"
      @change="updateAndChange"
      ><el-option
        v-for="option in field.selection"
        :key="String(option.value)"
        :label="option.label"
        :value="option.value"
    /></el-select>
    <div
      v-else-if="['integer', 'float', 'monetary'].includes(field.type)"
      class="numeric-control"
    >
      <el-input-number
        :model-value="numberValue"
        :precision="precision"
        :disabled="readonly"
        controls-position="right"
        class="full-width"
        @change="updateAndChange"
      /><span v-if="suffix" class="numeric-suffix">{{ suffix }}</span>
    </div>
    <el-switch
      v-else-if="field.type === 'boolean'"
      :model-value="Boolean(modelValue)"
      :disabled="readonly"
      @change="change"
    />
    <el-date-picker
      v-else-if="field.type === 'date'"
      v-model="dateModel"
      type="date"
      value-format="YYYY-MM-DD"
      :disabled="readonly"
      class="full-width"
      :editable="true"
      :teleported="true"
      @change="change"
    />
    <el-date-picker
      v-else-if="field.type === 'datetime'"
      v-model="dateModel"
      type="datetime"
      value-format="YYYY-MM-DD HH:mm:ss"
      :disabled="readonly"
      class="full-width"
      :editable="true"
      :teleported="true"
      @change="change"
    />
    <el-input
      v-else
      :model-value="textValue"
      :disabled="readonly"
      :type="
        field.type === 'text' || field.type === 'html' ? 'textarea' : 'text'
      "
      :rows="field.type === 'text' || field.type === 'html' ? 4 : 2"
      @update:model-value="update"
      @change="change"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import BinaryField from "./BinaryField.vue";
import AttachmentField from "./AttachmentField.vue";
import ImageField from "./ImageField.vue";
import JsonField from "./JsonField.vue";
import RelationField from "./RelationField.vue";
import RichTextField from "./RichTextField.vue";
import StatusField from "./StatusField.vue";
import X2ManyEditor from "./X2ManyEditor.vue";
import type { Dictionary, FieldSpec } from "@/types/contracts";
import { displayFieldValue } from "@/utils/format";
import { resolveFieldWidget } from "@/utils/widget";
import { resolveRelationDomain } from "@/runtime/modifiers";
const props = withDefaults(
  defineProps<{
    field: FieldSpec;
    modelValue: unknown;
    readonly?: boolean;
    allowViewEdit?: boolean;
    model: string;
    recordId?: number | null;
    values?: Dictionary;
    context?: Dictionary;
    patch?: Dictionary;
  }>(),
  { patch: () => ({}) },
);
const emit = defineEmits<{
  "update:modelValue": [value: unknown];
  change: [];
  uploaded: [];
  "request-edit": [continueAction?: () => void];
}>();
const componentKey = computed(() =>
  String(
    props.field.config.componentKey ||
      props.field.config.component_key ||
      componentForType(props.field.type),
  ),
);
const fieldWidget = computed(() => resolveFieldWidget(props.field.config, props.field));
const statusWidgets = ["statusbar", "badge", "statinfo", "status_with_color"];
const relationDomain = computed(() => {
  const config = props.field.config || {};
  const descriptor = config.fieldDescriptor || config.field_descriptor || {};
  const entry = config.relationEntry || config.relation_entry || config.fieldInfo?.relation_entry || config.field_info?.relation_entry || {};
  const source = props.patch.domain ?? config.domain ?? config.domainRaw ?? config.domain_raw ?? descriptor.domain ?? descriptor.domainRaw ?? descriptor.domain_raw ?? entry.domain ?? [];
  return resolveRelationDomain(source, props.values || {}, props.context || {}, props.field.code);
});
const isCollection = computed(
  () =>
    ["one2many", "many2many"].includes(props.field.type) ||
    ["sc.table.data", "sc.table.relation", "sc.select.tags"].includes(
      componentKey.value,
    ),
);
const numberValue = computed(() =>
  props.modelValue === false ||
  props.modelValue === "" ||
  props.modelValue == null
    ? undefined
    : Number(props.modelValue),
);
const textValue = computed(() =>
  props.modelValue === false || props.modelValue == null
    ? ""
    : typeof props.modelValue === "string"
      ? props.modelValue
      : displayFieldValue(props.modelValue, props.field.code, props.field.selection, props.field.type),
);
const dateValue = computed(() =>
  props.modelValue === false || props.modelValue === "" || props.modelValue == null
    ? undefined
    : normalizeDateValue(props.modelValue),
);
const dateModel = computed<string | Date | undefined>({
  get: () => dateValue.value,
  set: (value) => update(value),
});
const precision = computed(() => {
  const raw = props.field.config.precision || props.field.config.digits;
  return Array.isArray(raw)
    ? Number(raw[1] ?? 2)
    : props.field.type === "integer"
      ? 0
      : Number(raw ?? 2);
});
const suffix = computed(() =>
  props.field.config.widget === "percentage" ||
  props.field.config.semantic === "percentage"
    ? "%"
    : String(props.field.config.currency_symbol || ""),
);
function componentForType(type: string) {
  return type === "many2one"
    ? "sc.select.remote"
    : type === "many2many"
      ? "sc.select.tags"
      : type === "one2many"
        ? "sc.table.data"
        : type === "binary"
          ? "sc.input.binary"
          : type === "boolean"
            ? "sc.input.boolean"
            : type === "date"
              ? "sc.input.date"
              : type === "datetime"
                ? "sc.input.datetime"
                : ["integer", "float", "monetary"].includes(type)
                  ? "sc.input.number"
                  : "sc.input.text";
}
function update(value: unknown) {
  emit("update:modelValue", value);
}
function change() {
  emit("change");
}
function updateAndChange(value: unknown) {
  update(value);
  change();
}
function normalizeDateValue(value: unknown): string | Date | undefined {
  if (value instanceof Date) return value;
  if (typeof value === "number") return new Date(value);
  return String(value);
}
</script>

<style scoped>
.field-control {
  width: 100%;
}
.field-control :deep(.el-select),
.full-width {
  width: 100%;
}
.readonly-value {
  min-height: 32px;
  padding: 7px 11px;
  background: var(--el-fill-color-light);
  border-radius: 4px;
  color: var(--el-text-color-regular);
  line-height: 18px;
  white-space: pre-wrap;
  word-break: break-word;
}
.numeric-control {
  display: flex;
  align-items: center;
  gap: 8px;
}
.numeric-suffix {
  color: var(--el-text-color-secondary);
}
</style>
