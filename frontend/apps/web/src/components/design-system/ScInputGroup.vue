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
