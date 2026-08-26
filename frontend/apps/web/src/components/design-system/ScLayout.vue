<template>
  <TDesignLayout data-semantic-component="ScLayout" data-semantic-layer="primitive" data-primitive-driver="tdesign">
    <slot />
  </TDesignLayout>
</template>
<script setup lang="ts">
import { TDesignLayout } from './tdesignPrimitiveBridge';
</script>
