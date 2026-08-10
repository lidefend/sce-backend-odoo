<template>
  <div class="sc-file-field" :class="{ 'is-invalid': invalid }">
    <input
      :id="id"
      ref="inputRef"
      class="sc-file-field__native"
      type="file"
      :accept="accept || undefined"
      :disabled="disabled"
      :aria-required="required || undefined"
      :aria-invalid="invalid || undefined"
      :aria-describedby="describedBy"
      @change="handleChange"
    />
    <ScButton class="sc-btn-sm" variant="secondary" type="button" :disabled="disabled" @click="inputRef?.click()">
      {{ chooseLabel }}
    </ScButton>
    <span class="sc-file-field__name" :title="selectedName || emptyLabel">{{ selectedName || emptyLabel }}</span>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import ScButton from './ScButton.vue';

withDefaults(defineProps<{
  id?: string;
  accept?: string;
  disabled?: boolean;
  required?: boolean;
  invalid?: boolean;
  describedBy?: string;
  chooseLabel?: string;
  emptyLabel?: string;
}>(), {
  id: undefined,
  accept: '',
  disabled: false,
  required: false,
  invalid: false,
  describedBy: undefined,
  chooseLabel: '选择文件',
  emptyLabel: '未选择文件',
});

const emit = defineEmits<{ change: [event: Event] }>();
const inputRef = ref<HTMLInputElement | null>(null);
const selectedName = ref('');

function handleChange(event: Event) {
  const input = event.target as HTMLInputElement;
  selectedName.value = input.files?.[0]?.name || '';
  emit('change', event);
}
</script>

<style scoped>
.sc-file-field {
  display: flex;
  align-items: center;
  gap: var(--sc-space-xs);
  width: 100%;
  min-height: calc(var(--sc-component-button-height-md) * 1px);
  box-sizing: border-box;
  border: 1px solid var(--sc-app-border-strong);
  border-radius: var(--sc-component-input-radius);
  background: var(--sc-app-panel);
  padding: 2px;
}

.sc-file-field:focus-within {
  border-color: var(--sc-semantic-surface-interactive);
  box-shadow: 0 0 0 3px var(--sc-app-focus-ring);
}

.sc-file-field.is-invalid {
  border-color: var(--sc-app-danger-border);
}

.sc-file-field__native {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  clip-path: inset(50%);
  white-space: nowrap;
}

.sc-file-field__name {
  min-width: 0;
  overflow: hidden;
  color: var(--sc-app-text-secondary);
  font-size: calc(var(--sc-component-input-font-size) * 1px);
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
