<template>
  <span data-semantic-component="NativeWeightedRelationDisplay" :data-display-state="state">
    <ScInlineState v-if="state === 'error'" state="error" label="无法显示结构化关系，请检查字段声明和读取权限" />
    <ScInlineState v-else-if="state === 'loading'" state="loading" label="正在读取关系名称" />
    <span v-else>{{ text }}</span>
  </span>
</template>

<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue';
import { readRecord } from '../../api/data';
import ScInlineState from '../design-system/ScInlineState.vue';
import { weightedRelationDisplay } from './weightedRelationDisplay';

const props = defineProps<{
  declaration?: Record<string, unknown>;
  value: unknown;
  context?: Record<string, unknown>;
}>();
const text = ref('');
const state = ref<'loading' | 'ready' | 'error'>('loading');
let generation = 0;
watch(() => [props.declaration, props.value, props.context], async () => {
  const current = ++generation;
  text.value = '';
  state.value = 'loading';
  try {
    const result = await weightedRelationDisplay(props.declaration, props.value, props.context, readRecord);
    if (current !== generation) return;
    text.value = result;
    state.value = 'ready';
  } catch {
    if (current === generation) state.value = 'error';
  }
}, { immediate: true, deep: true });
onBeforeUnmount(() => { generation += 1; });
</script>
