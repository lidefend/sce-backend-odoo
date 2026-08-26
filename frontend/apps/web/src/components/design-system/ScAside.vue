<template>
  <TDesignAside :width="width" data-semantic-component="ScAside" data-semantic-layer="primitive" data-primitive-driver="tdesign">
    <slot />
  </TDesignAside>
</template>
<script setup lang="ts">
import { TDesignAside } from './tdesignPrimitiveBridge';
withDefaults(defineProps<{ width?: string }>(), { width: 'var(--sc-shell-sidebar-width)' });
</script>
