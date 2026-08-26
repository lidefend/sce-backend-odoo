<template>
  <TDesignButton variant="text" theme="default" shape="square" size="medium"
    class="sc-icon-button" type="button" :aria-label="label" :title="label" :disabled="disabled"
    data-semantic-component="ScIconButton" data-semantic-driver="tdesign-button" data-semantic-layer="primitive">
    <span aria-hidden="true"><slot /></span>
  </TDesignButton>
</template>
<script setup lang="ts">
import { TDesignButton } from './tdesignPrimitiveBridge';
defineProps<{ label: string; disabled?: boolean }>();
</script>
