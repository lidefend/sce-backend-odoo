<template>
  <ScButton
    data-semantic-component="NativeSmartAction"
    data-semantic-role="smart-action"
    type="button"
    variant="ghost"
    class="native-smart-action native-action-btn native-action-btn--smart"
    appearance="smart-action"
    :disabled="disabled"
    :title="title"
  >
    <span v-if="icon" :class="['native-smart-action__icon', icon]" aria-hidden="true" />
    <span class="native-smart-action__label">{{ label }}</span>
  </ScButton>
</template>

<script setup lang="ts">
import ScButton from '../design-system/ScButton.vue';

defineProps<{
  label: string;
  icon?: string;
  disabled?: boolean;
  title?: string;
}>();
</script>

<style scoped>
.native-smart-action {
  display: inline-flex;
  align-items: center;
  justify-content: flex-start;
  gap: 6px;
  min-width: 0;
  max-width: 100%;
  min-height: 60px;
  font: inherit;
  transition: background-color 120ms ease, color 120ms ease, box-shadow 120ms ease;
}

.native-smart-action__icon {
  flex: 0 0 auto;
  width: 18px;
  text-align: center;
  color: var(--sc-semantic-surface-interactive);
}

.native-smart-action__label {
  min-width: 0;
  overflow-wrap: anywhere;
  line-height: 1.25;
}
</style>
