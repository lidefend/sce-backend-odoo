<template>
  <span class="native-weighted-display" data-semantic-component="NativeWeightedRelationDisplay" :data-display-state="state">
    <ScInlineState v-if="state === 'error'" state="error" label="无法显示结构化关系，请检查字段声明和读取权限" />
    <ScInlineState v-else-if="state === 'loading'" state="loading" label="正在读取关系名称" />
    <span v-else-if="text === declaration?.empty_text">{{ text }}</span>
    <ScPopover
      v-else trigger="click" placement="bottom-left"
      :overlay-style="{ maxWidth: '100vw', whiteSpace: 'normal', overflowWrap: 'anywhere' }">
      <span data-native-weighted-full-value>{{ text }}</span>
      <template #trigger>
        <ScButton
          type="button" appearance="structured-content" variant="ghost" size="small"
          class="native-weighted-trigger" :aria-label="`查看完整内容：${text}`">{{ text }}</ScButton>
      </template>
    </ScPopover>
  </span>
</template>

<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue';
import { readRecord } from '../../api/data';
import ScInlineState from '../design-system/ScInlineState.vue';
import ScPopover from '../design-system/ScPopover.vue';
import ScButton from '../design-system/ScButton.vue';
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

<style scoped>
.native-weighted-display { display: block; min-width: 0; max-width: 100%; }
.native-weighted-trigger {
  display: block; width: 100%; min-width: 0; max-width: 100%; padding: 0;
  overflow: hidden; font: inherit; line-height: inherit; text-align: left;
  text-overflow: ellipsis; white-space: nowrap;
}
.native-weighted-trigger :deep(.sc-btn__content) {
  display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
</style>
