<template>
  <header
    class="collection-group-header"
    data-semantic-component="CollectionGroupHeader"
    :data-group-key="groupKey"
    :data-group-state="collapsed ? 'collapsed' : 'expanded'"
  >
    <ScButton
      class="collection-group-header__toggle"
      appearance="toolbar-chip"
      size="small"
      variant="secondary"
      :aria-expanded="!collapsed"
      :aria-label="toggleLabel"
      @click="$emit('toggle')"
    >
      {{ toggleLabel }}
    </ScButton>
    <div class="collection-group-header__identity">
      <h3>{{ label }}</h3>
      <span aria-live="polite">{{ countText }}</span>
    </div>
    <slot name="pagination" />
    <ScButton
      v-if="openEnabled"
      class="collection-group-header__open"
      appearance="outline-action"
      size="small"
      variant="secondary"
      @click="$emit('open')"
    >
      {{ openLabel }}
    </ScButton>
  </header>
</template>

<script setup lang="ts">
import ScButton from '../design-system/ScButton.vue';

defineProps<{
  groupKey: string;
  label: string;
  countText: string;
  collapsed: boolean;
  toggleLabel: string;
  openEnabled: boolean;
  openLabel: string;
}>();

defineEmits<{
  toggle: [];
  open: [];
}>();
</script>

<style scoped src="./CollectionGroupHeader.css"></style>
