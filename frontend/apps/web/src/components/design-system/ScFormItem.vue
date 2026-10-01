<template>
  <div v-if="bare" v-bind="$attrs"><slot /></div>
  <TDesignFormItem v-else v-bind="{ ...$attrs, ...semanticPrimitiveIdentity('ScFormItem'), ...itemBindings }">
    <slot />
  </TDesignFormItem>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { TDesignFormItem } from './tdesignPrimitiveBridge';
import { semanticPrimitiveIdentity } from './primitiveAdapter';
import type { ScFormItemProps } from './scFormContract';

defineOptions({ inheritAttrs: false });

const props = withDefaults(defineProps<ScFormItemProps>(), { bare: false });

const itemBindings = computed(() => ({
  label: props.label,
  name: props.name,
  rules: props.rules,
  status: props.status,
  help: props.help,
  showErrorMessage: props.showErrorMessage,
  labelAlign: props.labelAlign,
  labelWidth: props.labelWidth,
  requiredMark: props.requiredMark,
}));
</script>
