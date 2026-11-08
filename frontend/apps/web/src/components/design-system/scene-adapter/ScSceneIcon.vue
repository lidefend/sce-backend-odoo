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
if (props.decorative === false && !String(props.label ?? '').trim()) {
  throw new Error('SCENE_PRIMITIVE_CONTRACT_ERROR: Icon label is required when decorative=false');
}
const iconSize = computed(() => props.size ?? 20);
const isDecorative = computed(() => props.decorative !== false && !props.label);
const resolvedLabel = computed(() => isDecorative.value || !props.label ? undefined : props.label);
const scName = computed(() => props.name === 'file' ? 'file-text' : props.name);
</script>
