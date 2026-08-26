<template>
  <ScCheckbox
    class="collection-selection-control"
    appearance="menu-choice"
    :class="`size-${size}`"
    data-semantic-component="CollectionSelectionControl"
    :data-selection-state="presentation.state"
    :data-selection-interactive="presentation.interactive"
    :data-selection-scope="scope"
    :checked="checked"
    :indeterminate="indeterminate"
    :disabled="disabled"
    :label="label"
    hide-label
    :size="size === 'touch' ? 'medium' : 'small'"
    @click.stop
    @change="emit('change', $event)"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { resolveCollectionSelectionPresentation } from '../../app/presentation/collectionSelectionPresentation';
import ScCheckbox from '../design-system/ScCheckbox.vue';

const props = withDefaults(defineProps<{
  checked: boolean;
  indeterminate?: boolean;
  disabled?: boolean;
  label: string;
  size?: 'table' | 'touch';
  scope?: 'row' | 'page' | 'group';
}>(), {
  indeterminate: false,
  disabled: false,
  size: 'table',
  scope: 'row',
});

const emit = defineEmits<{ change: [checked: boolean] }>();
const presentation = computed(() => resolveCollectionSelectionPresentation(props));
</script>

<style scoped src="./CollectionSelectionControl.css"></style>
