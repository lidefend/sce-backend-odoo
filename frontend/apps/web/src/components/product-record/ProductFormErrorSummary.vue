<template>
  <ScErrorSummary
    v-if="errors.length || conflict"
    :errors="displayErrors"
    :targets="errorTargets"
    :title="conflict ? '记录已被其他操作更新' : '请检查以下内容'"
    data-semantic-component="ProductFormErrorSummary"
    :data-state="conflict ? 'conflict' : 'error'"
    @select="$emit('focus-error', $event)"
  >
    <p v-if="conflict">当前页面保留了你的输入。继续编辑前，请先加载最新数据。</p>
    <ScButton v-if="conflict" type="button" variant="secondary" @click="$emit('reload-latest')">加载最新数据</ScButton>
  </ScErrorSummary>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import ScErrorSummary from '../design-system/ScErrorSummary.vue';
import ScButton from '../design-system/ScButton.vue';
const props = withDefaults(defineProps<{ errors: string[]; fieldErrors?: Record<string, string>; conflict?: boolean }>(), {
  fieldErrors: () => ({}),
});
defineEmits<{ 'focus-error': [fieldName: string]; 'reload-latest': [] }>();
const fieldErrorEntries = computed(() => Object.entries(props.fieldErrors).filter(([name, message]) => Boolean(name && String(message || '').trim())));
const displayErrors = computed(() => fieldErrorEntries.value.length
  ? fieldErrorEntries.value.map(([, message]) => message)
  : props.errors);
const errorTargets = computed(() => fieldErrorEntries.value.length
  ? fieldErrorEntries.value.map(([name]) => name)
  : props.errors.map(() => ''));
</script>
