<template>
  <TDesignLoading v-if="state === 'loading'" class="sc-inline-state" data-semantic-component="ScInlineState"
    data-semantic-driver="tdesign-loading" data-semantic-layer="primitive" :data-state="state" :data-density="density"
    role="status" aria-live="polite" :aria-busy="state === 'loading' || undefined" size="small" :text="label" />
  <TDesignAlert v-else class="sc-inline-state" data-semantic-component="ScInlineState" data-semantic-driver="tdesign-alert"
    data-semantic-layer="primitive" :data-state="state" :data-density="density"
    :theme="state === 'error' ? 'error' : 'info'" :message="label"
    :role="state === 'error' ? 'alert' : 'status'" :aria-live="state === 'error' ? 'assertive' : 'polite'"
    :aria-busy="undefined">
    <slot>{{ label }}</slot><template v-if="$slots.actions" #operation><slot name="actions" /></template>
  </TDesignAlert>
</template>
<script setup lang="ts">
import { TDesignAlert, TDesignLoading } from './tdesignPrimitiveBridge';
withDefaults(defineProps<{state?:'info'|'loading'|'empty'|'error';density?:'regular'|'compact';label?:string}>(),{state:'info',density:'compact',label:''});
</script>
<style scoped>
.sc-inline-state{width:100%}.sc-inline-state[data-density='compact']{padding-block:0}
@media (prefers-reduced-motion: reduce) {
  .sc-inline-state :deep(*) { animation-duration: 0.01ms !important; animation-iteration-count: 1 !important; transition-duration: 0.01ms !important; }
}
</style>
