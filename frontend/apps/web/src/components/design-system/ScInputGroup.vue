<template>
  <TDesignInputAdornment
    class="sc-input-group"
    data-semantic-component="ScInputGroup"
    data-semantic-layer="primitive"
    data-primitive-driver="tdesign"
  >
    <slot />
    <template v-if="$slots.prepend" #prepend><slot name="prepend" /></template>
    <template v-if="$slots.append" #append><slot name="append" /></template>
  </TDesignInputAdornment>
</template>

<script setup lang="ts">
import { TDesignInputAdornment } from './tdesignPrimitiveBridge';
</script>

<style scoped>
.sc-input-group {
  width: 100%;
  min-width: 0;
}

.sc-input-group :deep(.t-input) {
  min-width: 0;
}

.sc-input-group :deep(.t-input-adornment__append) {
  display: inline-flex;
  align-items: stretch;
  background: transparent;
}

.sc-input-group :deep(.t-input-adornment__append .sc-btn) {
  height: 100%;
  margin-left: -1px;
  border-radius: 0;
}

.sc-input-group :deep(.t-input-adornment__append .sc-btn:last-child) {
  border-radius: 0 var(--td-radius-default) var(--td-radius-default) 0;
}
</style>
