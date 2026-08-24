<template>
  <TDesignBadge
    v-bind="semanticPrimitiveIdentity('ScBadge')"
    :count="count"
    :dot="dot"
    :max-count="maxCount"
    :status="tdesignStatus"
  >
    <slot />
  </TDesignBadge>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { TDesignBadge } from './tdesignPrimitiveBridge';
import { semanticPrimitiveIdentity, type ScPrimitiveStatus } from './primitiveAdapter';

const props = defineProps<{ count?: string | number; dot?: boolean; maxCount?: number; status?: ScPrimitiveStatus }>();
const tdesignStatus = computed(() => props.status === 'error' ? 'error' : props.status === 'default' ? undefined : props.status);
</script>
