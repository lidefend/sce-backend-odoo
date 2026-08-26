<template>
  <TDesignEmpty class="sc-empty" :size="density === 'compact' ? 'small' : 'medium'" :data-density="density" data-semantic-component="ScEmptyState" data-semantic-driver="tdesign-empty" data-semantic-layer="primitive" data-state="empty" role="status" :aria-labelledby="titleId">
    <template #title><component :is="titleTag" :id="titleId" class="sc-empty__title">{{ title }}</component></template>
    <template v-if="description" #description><p>{{ description }}</p></template>
    <template v-if="$slots.actions" #action><div class="sc-action-group"><slot name="actions" /></div></template>
  </TDesignEmpty>
</template>
<script setup lang="ts">
import { computed, useId } from 'vue';
import { TDesignEmpty } from './tdesignPrimitiveBridge';
const props = withDefaults(defineProps<{
  title: string;
  description?: string;
  density?: 'regular' | 'compact';
  headingLevel?: 2 | 3 | 4 | 5 | 6;
}>(), { density: 'regular', headingLevel: 2 });
const titleId = `sc-empty-${useId()}`;
const titleTag = computed(() => `h${props.headingLevel}`);
</script>
<style scoped>.sc-empty__title,.sc-empty p{margin:0}.sc-empty__title{font:inherit}.sc-empty p{max-width:56ch;margin-inline:auto}.sc-empty .sc-action-group{justify-content:center}</style>
