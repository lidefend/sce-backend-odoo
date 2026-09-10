<template>
  <component
    :is="iconComponent"
    class="sc-icon"
    :size="`${size}px`"
    :data-icon-name="name"
    data-icon-source="tdesign"
    aria-hidden="true"
    focusable="false"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { resolveScIconComponent, type ScIconName } from './scIcon';

const props = withDefaults(defineProps<{
  name: ScIconName;
  size?: 14 | 16 | 18 | 20 | 24;
}>(), { size: 20 });

const iconComponent = computed(() => resolveScIconComponent(props.name));
</script>

<style scoped>
.sc-icon { display: inline-block; flex: 0 0 auto; }
</style>
