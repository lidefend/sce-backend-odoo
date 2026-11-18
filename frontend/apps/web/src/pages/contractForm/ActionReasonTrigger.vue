<template>
  <ScPopover trigger="click" :disabled="!reason">
    <template #trigger>
      <span
        class="action-reason-trigger"
        :class="{ 'action-reason-trigger--denied': Boolean(reason) }"
        :tabindex="reason ? 0 : undefined"
        :role="reason ? 'button' : undefined"
        data-semantic-component="ActionReasonTrigger"
        :data-state="reason ? 'disabled' : 'ready'"
        :aria-label="reason || undefined"
        :data-workflow-reason-trigger="reason ? triggerKey : undefined"
        @keydown="activateWorkflowReasonTrigger"
      >
        <slot />
      </span>
    </template>
    {{ reason }}
  </ScPopover>
</template>

<script setup lang="ts">
import ScPopover from '../../components/design-system/ScPopover.vue';
import { activateWorkflowReasonTrigger } from './workflowReasonTrigger';

defineProps<{
  reason: string;
  triggerKey: string;
}>();
</script>

<style scoped>
.action-reason-trigger {
  display: inline-flex;
  min-width: 0;
}
.action-reason-trigger--denied:focus-visible {
  outline: var(--sc-component-button-focus-ring-width) solid var(--sc-semantic-focus-ring);
  outline-offset: var(--sc-component-button-focus-inset-offset);
}
.action-reason-trigger--denied :deep(button:disabled) {
  pointer-events: none;
}
</style>
