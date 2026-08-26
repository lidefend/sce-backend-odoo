<template>
  <div
    class="sc-inline-state"
    data-semantic-component="ScInlineState"
    data-semantic-layer="primitive"
    :data-state="state"
    :data-density="density"
    :role="state === 'error' ? 'alert' : 'status'"
    :aria-live="state === 'error' ? 'assertive' : 'polite'"
    :aria-busy="state === 'loading' || undefined"
  >
    <span class="sc-inline-state__indicator" aria-hidden="true" />
    <span class="sc-inline-state__label"><slot>{{ label }}</slot></span>
    <span v-if="$slots.actions" class="sc-inline-state__actions"><slot name="actions" /></span>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  state?: 'info' | 'loading' | 'empty' | 'error';
  density?: 'regular' | 'compact';
  label?: string;
}>(), {
  state: 'info',
  density: 'compact',
  label: '',
});
</script>

<style scoped>
.sc-inline-state {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: var(--sc-product-space-2);
  color: var(--sc-app-text-secondary);
  font-size: var(--sc-product-text-sm);
  line-height: 1.45;
}

.sc-inline-state[data-density='regular'] {
  padding-block: var(--sc-product-space-2);
}

.sc-inline-state__indicator {
  width: 6px;
  height: 6px;
  flex: 0 0 auto;
  border-radius: 50%;
  background: currentColor;
}

.sc-inline-state[data-state='loading'] .sc-inline-state__indicator {
  width: 12px;
  height: 12px;
  border: 2px solid var(--sc-app-border);
  border-top-color: var(--sc-app-accent);
  background: transparent;
  animation: sc-inline-state-spin 0.8s linear infinite;
}

.sc-inline-state[data-state='error'] { color: var(--sc-app-danger-text); }
.sc-inline-state__label { min-width: 0; overflow-wrap: anywhere; }
.sc-inline-state__actions { display: inline-flex; flex: 0 0 auto; gap: var(--sc-product-space-1); }

@keyframes sc-inline-state-spin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) {
  .sc-inline-state[data-state='loading'] .sc-inline-state__indicator { animation: none; }
}
</style>
