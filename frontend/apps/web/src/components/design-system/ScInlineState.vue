<template>
  <TDesignLoading v-if="state === 'loading'" class="sc-inline-state" data-semantic-component="ScInlineState"
    data-semantic-driver="tdesign-loading" data-semantic-layer="primitive" :data-state="state" :data-density="density"
    role="status" aria-live="polite" :aria-busy="state === 'loading' || undefined" size="small" :text="label" />
  <TDesignAlert v-else class="sc-inline-state" data-semantic-component="ScInlineState" data-semantic-driver="tdesign-alert"
    data-semantic-layer="primitive" :data-state="state" :data-density="density"
    :theme="state === 'error' ? 'error' : 'info'"
    :role="state === 'error' ? 'alert' : 'status'" :aria-live="state === 'error' ? 'assertive' : 'polite'"
    :aria-busy="undefined">
    <span class="sc-inline-state__description"><slot>{{ label }}</slot></span><template v-if="$slots.actions" #operation><slot name="actions" /></template>
  </TDesignAlert>
</template>
<script setup lang="ts">
import { TDesignAlert, TDesignLoading } from './tdesignPrimitiveBridge';
withDefaults(defineProps<{state?:'info'|'loading'|'empty'|'error';density?:'regular'|'compact';label?:string}>(),{state:'info',density:'compact',label:''});
</script>
<style scoped>
.sc-inline-state{width:100%;container-type:inline-size}.sc-inline-state[data-density='compact']{padding-block:0}
/* The official alert lays its body out as a flex item sized from its own content.
   Text carries a real intrinsic width, but a body whose width comes from a grid
   resolves to 0, and the band then squeezes every character onto its own line. The
   locked alert exposes no public slot, prop or CSS variable that sizes that flex
   item, and reaching into the vendor's internal element names would be an internal
   vendor selector, which the design-alignment inventory forbids.
   The width responsibility therefore belongs to this project-owned container: it
   claims the band width through its own track and its own measure element. The
   measure element is a maximum, never a fixed size -- the real width still comes
   from the alert band, so the body stays shrinkable to exactly the space the alert
   reserves for it, and long copy plus nested grid facts wrap inside the band. */
.sc-inline-state__description{display:grid;grid-template-columns:minmax(0,1fr);inline-size:100%;max-inline-size:100%;min-inline-size:0;overflow-wrap:anywhere}
.sc-inline-state__description::after{content:"";display:block;block-size:0;inline-size:100cqi}
.sc-inline-state[data-state='info'] {
  border-color: var(--sc-app-info-border);
  background: var(--sc-app-info-bg);
  color: var(--sc-app-info-text);
}
.sc-inline-state[data-state='info'] .sc-inline-state__description {
  color: var(--sc-app-info-text);
}
@media (prefers-reduced-motion: reduce) {
  .sc-inline-state :deep(*) { animation-duration: 0.01ms !important; animation-iteration-count: 1 !important; transition-duration: 0.01ms !important; }
}
</style>
