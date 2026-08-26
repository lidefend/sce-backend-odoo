<template>
  <ScLayout data-semantic-component="ProductAppShell" data-layout-driver="tdesign">
    <slot />
  </ScLayout>
</template>

<script setup lang="ts">
import ScLayout from '../design-system/ScLayout.vue';
defineOptions({ inheritAttrs: true });
</script>
