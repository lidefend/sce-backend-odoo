<template>
  <ScButton
    class="collection-filter-chip"
    :class="{ 'is-active': active }"
    variant="ghost"
    size="small"
    type="button"
    data-semantic-component="CollectionFilterChip"
    :data-filter-key="filterKey || undefined"
    :aria-pressed="active"
    :disabled="disabled"
    :title="disabledReason || title || undefined"
    @click="$emit('activate')"
  >
    <slot>{{ label }}</slot>
  </ScButton>
</template>

<script setup lang="ts">
import ScButton from '../design-system/ScButton.vue';

defineProps<{
  label?: string;
  filterKey?: string;
  active?: boolean;
  disabled?: boolean;
  disabledReason?: string;
  title?: string;
}>();

defineEmits<{ activate: [] }>();
</script>

<style scoped>
.collection-filter-chip{max-width:100%;border-radius:var(--sc-component-tag-radius)}
.collection-filter-chip.is-active{color:var(--sc-app-selected-text);background:var(--sc-app-selected-bg);box-shadow:inset 0 0 0 1px var(--sc-app-selected-border)}
</style>
