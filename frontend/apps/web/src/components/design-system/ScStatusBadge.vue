<template>
  <TTag
    :class="['sc-badge', 'sc-design-status', `sc-badge-${semantic}`]"
    :data-status="value"
    :theme="tdTheme"
    variant="light"
    shape="round"
    data-ui-engine="tdesign"
  >
    <span class="sc-visually-hidden">{{ statusPrefix }}</span>{{ label }}
  </TTag>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { TTag } from './tdesignAdapter';

const props = withDefaults(defineProps<{
  value?: string;
  label: string;
  semantic?: 'default' | 'info' | 'success' | 'warning' | 'danger';
  statusPrefix?: string;
}>(), { value: '', semantic: 'default', statusPrefix: '状态：' });
const tdTheme = computed(() => props.semantic === 'info' ? 'primary' : props.semantic);
</script>
