<template>
  <slot v-if="bare" />
  <TDesignForm v-else ref="formRef" v-bind="{ ...semanticPrimitiveIdentity('ScForm'), ...$attrs, ...formBindings }">
    <slot />
  </TDesignForm>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { TDesignForm } from './tdesignPrimitiveBridge';
import { semanticPrimitiveIdentity } from './primitiveAdapter';
import type { ScFormInstance, ScFormProps } from './scFormContract';

defineOptions({ inheritAttrs: false });

const props = withDefaults(defineProps<ScFormProps>(), { bare: false });
const formRef = ref<unknown>(null);

/**
 * The official form owns composition and generic validation. The bindings are
 * assembled here so the wrapper stays a pass-through: it forwards the
 * capabilities the caller declared and adds none of its own. `bare` renders the
 * slot without a form container so an unadopted surface keeps the exact DOM it
 * had before this adapter existed.
 */
const formBindings = computed(() => (props.bare ? {} : {
  data: props.data,
  disabled: props.disabled,
  layout: props.layout,
  labelAlign: props.labelAlign,
  labelWidth: props.labelWidth,
  requiredMark: props.requiredMark,
  rules: props.rules,
  scrollToFirstError: props.scrollToFirstError,
  showErrorMessage: props.showErrorMessage,
  resetType: props.resetType,
  preventSubmitDefault: props.preventSubmitDefault,
}));

function instance(): ScFormInstance | null {
  return (formRef.value as ScFormInstance | null) || null;
}

defineExpose({
  clearValidate: (fields?: string[]) => instance()?.clearValidate(fields),
  reset: (params?: Record<string, unknown>) => instance()?.reset(params),
  setValidateMessage: (message: Record<string, unknown>) => instance()?.setValidateMessage(message),
  submit: (params?: Record<string, unknown>) => instance()?.submit(params),
  validate: (params?: Record<string, unknown>) => instance()?.validate(params),
  validateOnly: (params?: Record<string, unknown>) => instance()?.validateOnly(params),
});
</script>
