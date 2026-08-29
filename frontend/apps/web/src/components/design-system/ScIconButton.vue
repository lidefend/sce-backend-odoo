<template>
  <TDesignButton ref="buttonRef" variant="text" theme="default" shape="square" size="medium"
    :class="['sc-icon-button', attrs.class]" :style="attrs.style" type="button" :aria-label="label" :title="label" :disabled="disabled"
    :data-appearance="appearance"
    v-bind="restAttrs"
    data-semantic-component="ScIconButton" data-semantic-driver="tdesign-button" data-semantic-layer="primitive">
    <span aria-hidden="true"><slot /></span>
  </TDesignButton>
</template>
<script setup lang="ts">
import { computed, ref, useAttrs } from 'vue';
import { TDesignButton } from './tdesignPrimitiveBridge';
const props = withDefaults(defineProps<{ label: string; disabled?: boolean; appearance?: 'default' | 'toolbar-menu-toggle' | 'favorite-toggle' | 'outline-action' | 'column-handle' | 'activity-rail' }>(), {
  appearance: 'default',
});

const attrs = useAttrs();
const restAttrs = computed(() => {
  const { class: _class, style: _style, ...rest } = attrs;
  return rest;
});

const buttonRef = ref<{ $el?: HTMLElement } | null>(null);

defineExpose({
  focus: () => {
    const root = buttonRef.value?.$el;
    const target = root instanceof HTMLButtonElement ? root : root?.querySelector<HTMLButtonElement>('button');
    target?.focus();
  },
});
</script>
<script lang="ts">
export default { inheritAttrs: false };
</script>
