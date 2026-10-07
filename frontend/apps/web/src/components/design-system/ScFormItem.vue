<template>
  <!--
    The bare branch is the primitive's own composition root. It publishes only the
    stable `data-semantic-primitive` marker: adding a `data-semantic-component`
    default there would newly activate the consumer-scoped
    `[data-semantic-component='ScFormItem']` styling that this branch has never
    matched, which is a behaviour change outside this contract.
  -->
  <div v-if="bare" v-bind="{ 'data-semantic-primitive': 'ScFormItem', ...$attrs }"><slot /></div>
  <TDesignFormItem v-else v-bind="{ ...semanticPrimitiveIdentity('ScFormItem'), ...$attrs, ...itemBindings }">
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
