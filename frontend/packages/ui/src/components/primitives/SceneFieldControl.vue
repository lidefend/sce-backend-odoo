<script setup lang="ts">
import { computed } from 'vue';
import type { SceneField } from '../../contracts/sceneObjectPage';
import { useSceneUiKit } from '../../kits/context';

const props = defineProps<{ field: SceneField; modelValue: string }>();
const emit = defineEmits<{ 'update:modelValue': [value: string] }>();
const { kit, runtime } = useSceneUiKit();
const componentModel = computed(() => runtime.value?.componentModel || 'native');
const driverControl = computed(() => {
  const primitive = props.field.kind === 'amount' || props.field.kind === 'text' ? 'input' : props.field.kind;
  return runtime.value?.components[primitive];
});
const driverOptions = computed(() => (props.field.options || []).map((option) => ({
  label: option.label,
  value: option.key,
})));

function updateFromEvent(event: Event): void {
  const target = event.target as HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement | null;
  emit('update:modelValue', target?.value || '');
}

function updateFromValue(value: unknown): void {
  emit('update:modelValue', String(Array.isArray(value) ? value[0] ?? '' : value ?? ''));
}
</script>

<template>
  <div class="scene-field-control" :data-control-driver="kit">
    <template v-if="componentModel === 'web-components'">
      <ui5-date-picker
        v-if="field.kind === 'date'"
        :id="field.id"
        :value="modelValue"
        format-pattern="yyyy-MM-dd"
        :placeholder="field.placeholder"
        :disabled="field.readonly || undefined"
        :required="field.required || undefined"
        @input="updateFromEvent"
      />
      <ui5-select v-else-if="field.kind === 'select'" :id="field.id" :disabled="field.readonly || undefined" :required="field.required || undefined" @change="updateFromEvent">
        <ui5-option
          v-for="option in field.options || []"
          :key="option.key"
          :selected="option.key === modelValue"
        >
          {{ option.label }}
        </ui5-option>
      </ui5-select>
      <ui5-textarea
        v-else-if="field.kind === 'textarea'"
        :id="field.id"
        :value="modelValue"
        :placeholder="field.placeholder"
        :disabled="field.readonly || undefined"
        :required="field.required || undefined"
        growing
        growing-max-rows="5"
        @input="updateFromEvent"
      />
      <div v-else-if="field.kind === 'amount'" class="scene-primitive-amount">
        <ui5-input :id="field.id" :value="modelValue" :placeholder="field.placeholder" :disabled="field.readonly || undefined" :required="field.required || undefined" inputmode="decimal" @input="updateFromEvent" />
        <span>CNY</span>
      </div>
      <ui5-input v-else :id="field.id" :value="modelValue" :placeholder="field.placeholder" :disabled="field.readonly || undefined" :required="field.required || undefined" @input="updateFromEvent" />
    </template>

    <template v-else-if="componentModel === 'vue' && driverControl">
      <div v-if="field.kind === 'amount'" class="scene-primitive-amount">
        <component
          :is="driverControl"
          :id="field.id"
          :model-value="modelValue"
          :placeholder="field.placeholder"
          :disabled="field.readonly"
          :readonly="field.readonly"
          :status="field.invalid ? 'error' : undefined"
          data-scene-driver-control="amount"
          @update:model-value="updateFromValue"
        />
        <span>CNY</span>
      </div>
      <component
        :is="driverControl"
        v-else
        :id="field.id"
        :model-value="modelValue"
        :placeholder="field.placeholder"
        :disabled="field.readonly"
        :readonly="field.readonly"
        :status="field.invalid ? 'error' : undefined"
        :options="field.kind === 'select' ? driverOptions : undefined"
        :format="field.kind === 'date' ? 'YYYY-MM-DD' : undefined"
        :autosize="field.kind === 'textarea' ? { minRows: 3, maxRows: 5 } : undefined"
        :data-scene-driver-control="field.kind"
        @update:model-value="updateFromValue"
        @change="field.kind === 'select' || field.kind === 'date' ? updateFromValue : undefined"
      />
    </template>

    <template v-else>
      <input
        v-if="field.kind === 'date'"
        :id="field.id"
        class="scene-native-control"
        type="date"
        :value="modelValue"
        :disabled="field.readonly"
        :required="field.required"
        :aria-invalid="field.invalid || undefined"
        @input="updateFromEvent"
      />
      <select v-else-if="field.kind === 'select'" :id="field.id" class="scene-native-control" :value="modelValue" :disabled="field.readonly" :required="field.required" :aria-invalid="field.invalid || undefined" @change="updateFromEvent">
        <option v-for="option in field.options || []" :key="option.key" :value="option.key">
          {{ option.label }}
        </option>
      </select>
      <textarea
        v-else-if="field.kind === 'textarea'"
        :id="field.id"
        class="scene-native-control scene-native-control--textarea"
        :value="modelValue"
        :placeholder="field.placeholder"
        :disabled="field.readonly"
        :required="field.required"
        :aria-invalid="field.invalid || undefined"
        rows="3"
        @input="updateFromEvent"
      />
      <div v-else-if="field.kind === 'amount'" class="scene-primitive-amount">
        <input
          :id="field.id"
          class="scene-native-control"
          type="text"
          inputmode="decimal"
          :value="modelValue"
          :placeholder="field.placeholder"
          :disabled="field.readonly"
          :required="field.required"
          :aria-invalid="field.invalid || undefined"
          @input="updateFromEvent"
        />
        <span>CNY</span>
      </div>
      <input
        v-else
        :id="field.id"
        class="scene-native-control"
        type="text"
        :value="modelValue"
        :placeholder="field.placeholder"
        :disabled="field.readonly"
        :required="field.required"
        :aria-invalid="field.invalid || undefined"
        @input="updateFromEvent"
      />
    </template>
  </div>
</template>

<style scoped>
.scene-field-control {
  width: 100%;
  min-width: 0;
}

.scene-native-control {
  width: 100%;
  min-height: var(--sc-scene-control-height, 36px);
  padding: 7px 10px;
  border: 1px solid #9cadbe;
  border-radius: 5px;
  outline: 0;
  background: white;
  color: #172f43;
  font: 14px/1.4 "Segoe UI", sans-serif;
}

.scene-native-control:focus {
  border-color: #0a6ed1;
  box-shadow: 0 0 0 2px rgba(10, 110, 209, 0.16);
}

.scene-native-control--textarea {
  resize: vertical;
}

.scene-field-control :deep(ui5-input),
.scene-field-control :deep(ui5-select),
.scene-field-control :deep(ui5-date-picker),
.scene-field-control :deep(ui5-textarea) {
  width: 100%;
}

.scene-primitive-amount {
  position: relative;
}

.scene-primitive-amount > :first-child {
  width: 100%;
}

.scene-primitive-amount span {
  position: absolute;
  top: 50%;
  right: 10px;
  transform: translateY(-50%);
  color: #65778a;
  font-size: 11px;
  pointer-events: none;
}
</style>
