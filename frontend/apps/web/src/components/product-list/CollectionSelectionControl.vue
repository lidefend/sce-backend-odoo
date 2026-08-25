<template>
  <label
    class="collection-selection-control"
    :class="`size-${size}`"
    data-semantic-component="CollectionSelectionControl"
    :data-selection-state="presentation.state"
    :data-selection-interactive="presentation.interactive"
    @click.stop
  >
    <input
      ref="inputRef"
      type="checkbox"
      :checked="checked"
      :disabled="disabled"
      :aria-label="label"
      @change="emitChange"
    />
    <span class="collection-selection-control__indicator" aria-hidden="true"></span>
  </label>
</template>

<script setup lang="ts">
import { computed, ref, watchEffect } from 'vue';
import { resolveCollectionSelectionPresentation } from '../../app/presentation/collectionSelectionPresentation';

const props = withDefaults(defineProps<{
  checked: boolean;
  indeterminate?: boolean;
  disabled?: boolean;
  label: string;
  size?: 'table' | 'touch';
}>(), {
  indeterminate: false,
  disabled: false,
  size: 'table',
});

const emit = defineEmits<{ change: [checked: boolean] }>();
const inputRef = ref<HTMLInputElement | null>(null);
const presentation = computed(() => resolveCollectionSelectionPresentation(props));

watchEffect(() => {
  if (inputRef.value) inputRef.value.indeterminate = props.indeterminate;
});

function emitChange(event: Event) {
  emit('change', Boolean((event.target as HTMLInputElement | null)?.checked));
}
</script>

<style scoped src="./CollectionSelectionControl.css"></style>
