<template>
  <ScErrorSummary
    v-if="errors.length || conflict || fieldErrorEntries.length"
    :errors="displayErrors"
    :targets="errorTargets"
    :title="conflict ? '记录已被其他操作更新' : '请检查以下内容'"
    data-semantic-component="ProductFormErrorSummary"
    :data-state="conflict ? 'conflict' : 'error'"
    @select="emit('focus-error', focusTargetFor($event))"
  >
    <p v-if="conflict">当前页面保留了你的输入。继续编辑前，请先加载最新数据。</p>
    <ScButton v-if="conflict" type="button" variant="secondary" @click="emit('reload-latest')">加载最新数据</ScButton>
  </ScErrorSummary>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { BusinessFieldError } from '../../app/businessValidationError';
import ScErrorSummary from '../design-system/ScErrorSummary.vue';
import ScButton from '../design-system/ScButton.vue';

const props = withDefaults(defineProps<{
  errors: string[];
  /** Errors owned by a business field. The same ownership the fields render from. */
  fieldErrors?: Record<string, BusinessFieldError>;
  conflict?: boolean;
}>(), {
  fieldErrors: () => ({}),
});

const emit = defineEmits<{
  'focus-error': [target: { key: string; sourceOccurrenceKey?: string }];
  'reload-latest': [];
}>();

const fieldErrorEntries = computed(() => Object.entries(props.fieldErrors || {})
  .filter(([name, error]) => Boolean(name && String(error?.message || '').trim())));
const displayErrors = computed(() => fieldErrorEntries.value.length
  ? fieldErrorEntries.value.map(([, error]) => error.message)
  : props.errors);
const errorTargets = computed(() => fieldErrorEntries.value.length
  ? fieldErrorEntries.value.map(([name]) => name)
  : props.errors.map(() => ''));

function focusTargetFor(key: string) {
  const error = props.fieldErrors?.[key];
  return error?.sourceOccurrenceKey ? { key, sourceOccurrenceKey: error.sourceOccurrenceKey } : { key };
}
</script>
