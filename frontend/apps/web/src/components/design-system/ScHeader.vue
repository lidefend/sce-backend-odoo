<template>
  <TDesignHeader :height="height" data-semantic-component="ScHeader" data-semantic-layer="primitive" data-primitive-driver="tdesign">
    <slot />
  </TDesignHeader>
</template>
<script setup lang="ts">
import { TDesignHeader } from './tdesignPrimitiveBridge';
withDefaults(defineProps<{ height?: string }>(), { height: 'auto' });
</script>
