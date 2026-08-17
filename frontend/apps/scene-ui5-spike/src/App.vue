<script setup lang="ts">
import { SceneObjectPage } from '@sc/ui';
import { paymentRequestScene } from './fixtures/paymentRequestScene';
</script>

<template>
  <SceneObjectPage :contract="paymentRequestScene" prototype-mode />
</template>
