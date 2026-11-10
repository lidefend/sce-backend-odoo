<template>
  <!-- eslint-disable vue/no-v-html -- ScRichText is the single reviewed sanitizer owner. -->
  <div
    class="sc-rich-text"
    data-semantic-component="ScRichText"
    :data-policy="policy"
    v-bind="$attrs"
    v-html="sanitizedHtml"
  ></div>
  <!-- eslint-enable vue/no-v-html -->
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { sanitizeReadonlyHtml } from '../../utils/sanitizeReadonlyHtml';
import { sanitizeRestrictedHtml } from '../../utils/sanitizeRestrictedHtml';

defineOptions({ inheritAttrs: false });

const props = defineProps<{
  content?: unknown;
  policy?: 'readonly' | 'restricted';
}>();

const sanitizedHtml = computed(() => (
  props.policy === 'restricted'
    ? sanitizeRestrictedHtml(props.content ?? '')
    : sanitizeReadonlyHtml(props.content ?? '')
));
</script>

<style scoped>
.sc-rich-text {
  min-width: 0;
  max-width: 100%;
  overflow-x: auto;
  overflow-wrap: anywhere;
}

.sc-rich-text :deep(:first-child) {
  margin-top: 0;
}

.sc-rich-text :deep(:last-child) {
  margin-bottom: 0;
}

.sc-rich-text :deep(table) {
  max-width: 100%;
  border-collapse: collapse;
}
</style>
