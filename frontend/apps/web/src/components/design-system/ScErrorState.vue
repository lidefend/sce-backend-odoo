<template>
  <TDesignAlert class="sc-error-state" theme="error" :data-density="density" data-semantic-component="ScErrorState" data-semantic-driver="tdesign-alert" data-semantic-layer="primitive" data-state="error" role="alert" :aria-labelledby="titleId">
    <template #title><component :is="titleTag" :id="titleId" class="sc-error-state__title">{{ title }}</component></template>
    <template #message><p>{{ description }}</p></template>
    <template v-if="$slots.actions" #operation><div class="sc-action-group sc-error-state__actions"><slot name="actions" /></div></template>
  </TDesignAlert>
</template>
<script setup lang="ts">
import { computed, useId } from 'vue';
import { TDesignAlert } from './tdesignPrimitiveBridge';
const props = withDefaults(defineProps<{
  title: string;
  description: string;
  density?: 'regular' | 'compact';
  headingLevel?: 2 | 3 | 4 | 5 | 6;
}>(), { density: 'regular', headingLevel: 2 });
const titleId = `sc-error-${useId()}`;
const titleTag = computed(() => `h${props.headingLevel}`);
</script>
<style scoped>.sc-error-state__title,.sc-error-state p{margin:0;overflow-wrap:anywhere}.sc-error-state__title{font:inherit}.sc-error-state__actions{justify-content:flex-start}</style>
