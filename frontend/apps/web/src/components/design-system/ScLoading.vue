<template>
  <TDesignLoading
    v-bind="semanticPrimitiveIdentity('ScLoading')"
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
  showOverlay: false,
});
</script>
