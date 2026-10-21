<template>
  <ScPage class="page" data-semantic-component="AccessDeniedView" data-state="error">
    <StatusPanel title="" variant="error" :error-code="403" />
  </ScPage>
</template>

<script setup lang="ts">
import StatusPanel from '../components/StatusPanel.vue';
import ScPage from '../components/design-system/ScPage.vue';
import { usePageIdentityRuntime } from '../app/pageIdentityRuntime';

usePageIdentityRuntime();

</script>
