<template>
  <div
    v-if="presentation.kind === 'feedback'"
    class="native-explicit-feedback"
    :data-purpose="presentation.purpose"
    :data-contract-container-id="containerId"
    tabindex="-1"
  >
    <TDesignAlert
      v-if="presentation.purpose !== 'explanation'"
      :theme="presentation.purpose === 'error' ? 'error' : presentation.purpose === 'warning' ? 'warning' : 'info'"
      :role="presentation.role"
      :aria-live="presentation.purpose === 'error' ? 'assertive' : 'polite'"
    >{{ presentation.content }}</TDesignAlert>
    <p v-else>{{ presentation.content }}</p>
  </div>
  <ScButton
    v-else-if="presentation.kind === 'anchor'"
    type="button"
    variant="ghost"
    :data-contract-container-id="containerId"
    @click="$emit('navigate', $event)"
  >{{ presentation.content }}</ScButton>
  <div
    v-else-if="presentation.kind === 'ribbon'"
    class="native-ribbon"
    :class="presentation.styleClass"
    :data-contract-container-id="containerId"
    data-native-widget="web_ribbon"
  >{{ presentation.content }}</div>
</template>

<script setup lang="ts">
import type { NodeComponentPresentation } from '../../app/presentation/nodeComponentPresentation';
import ScButton from '../design-system/ScButton.vue';

defineProps<{
  presentation: NodeComponentPresentation;
  containerId: string;
}>();

defineEmits<{
  navigate: [event: Event];
}>();
</script>

<style scoped>
.native-ribbon {
  font: var(--sc-font-mark-small);
  justify-self: end;
  max-width: 100%;
  border-radius: 4px;
  background: var(--sc-app-danger-text);
  color: var(--sc-semantic-text-on-interactive);
  padding: 4px 10px;
  overflow-wrap: anywhere;
}

.native-ribbon.text-bg-danger {
  background: var(--sc-app-danger-text);
}
</style>
