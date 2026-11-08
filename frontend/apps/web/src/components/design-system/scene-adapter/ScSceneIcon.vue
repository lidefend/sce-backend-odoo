<template>
  <ScIcon
    :name="scName"
    :size="iconSize"
    :aria-label="resolvedLabel"
    :aria-hidden="isDecorative ? 'true' : undefined"
    :role="isDecorative ? undefined : 'img'"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { IconPortProps, NoPortSlots } from '@sc/ui/primitive-port';
import ScIcon from '../ScIcon.vue';

const props = withDefaults(defineProps<IconPortProps>(), {
  size: 20,
  label: undefined,
  decorative: undefined,
});
defineSlots<NoPortSlots>();
const iconSize = computed(() => props.size ?? 20);
const isDecorative = computed(() => {
  const hasLabel = Boolean(String(props.label ?? '').trim());
  if (props.decorative === false && !hasLabel) {
    throw new Error('SCENE_PRIMITIVE_CONTRACT_ERROR: Icon label is required when decorative=false');
  }
  return props.decorative !== false && !hasLabel;
});
const resolvedLabel = computed(() => isDecorative.value || !props.label ? undefined : props.label);
const scName = computed(() => props.name === 'file' ? 'file-text' : props.name);
</script>
