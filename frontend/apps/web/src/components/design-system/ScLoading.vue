<template>
  <TDesignLoading
    v-bind="semanticPrimitiveIdentity('ScLoading')"
    :data-state="loading ? 'loading' : 'idle'"
    :aria-busy="loading || undefined"
    :aria-live="loading ? 'polite' : undefined"
    :loading="loading"
    :size="normalizePrimitiveSize(size)"
    :text="label"
    :fullscreen="fullscreen"
    :show-overlay="showOverlay"
  >
    <slot />
  </TDesignLoading>
</template>

<script setup lang="ts">
import { TDesignLoading } from './tdesignPrimitiveBridge';
import { normalizePrimitiveSize, semanticPrimitiveIdentity, type ScPrimitiveSize } from './primitiveAdapter';

withDefaults(defineProps<{ loading?: boolean; size?: ScPrimitiveSize; label?: string; fullscreen?: boolean; showOverlay?: boolean }>(), {
  loading: true,
  size: 'medium',
  label: undefined,
  showOverlay: false,
});
</script>
