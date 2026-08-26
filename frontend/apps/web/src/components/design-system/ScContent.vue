<template>
  <TDesignContent data-semantic-component="ScContent" data-semantic-layer="primitive" data-primitive-driver="tdesign">
    <slot />
  </TDesignContent>
</template>
<script setup lang="ts">
import { TDesignContent } from './tdesignPrimitiveBridge';
</script>
