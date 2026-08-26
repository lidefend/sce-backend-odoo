<template>
  <button
    data-semantic-component="NativeSmartAction"
    data-semantic-role="smart-action"
    type="button"
    class="native-smart-action"
    :disabled="disabled"
    :title="title"
  >
    <span v-if="icon" :class="['native-smart-action__icon', icon]" aria-hidden="true" />
    <span class="native-smart-action__label">{{ label }}</span>
  </button>
</template>

<script setup lang="ts">
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
  border: 0;
  border-radius: 0;
  padding: 12px 14px;
  color: var(--sc-app-text-primary);
  background: var(--sc-app-panel);
  font: inherit;
  font-size: 14px;
  font-weight: 600;
  text-align: left;
  cursor: pointer;
  transition: background-color 120ms ease, color 120ms ease, box-shadow 120ms ease;
}

.native-smart-action:hover {
  background: var(--sc-app-hover-bg);
  color: var(--sc-app-text-primary);
}

.native-smart-action:focus-visible {
  box-shadow: inset 0 0 0 2px var(--sc-semantic-surface-interactive), 0 0 0 3px var(--sc-app-focus-ring);
  outline: none;
}

.native-smart-action:disabled {
  cursor: not-allowed;
  opacity: var(--sc-component-button-disabled-opacity);
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
