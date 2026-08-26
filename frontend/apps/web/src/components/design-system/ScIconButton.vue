<template>
  <TDesignButton ref="buttonRef" variant="text" theme="default" shape="square" size="medium"
    class="sc-icon-button" type="button" :aria-label="label" :title="label" :disabled="disabled"
    :data-appearance="appearance"
    data-semantic-component="ScIconButton" data-semantic-driver="tdesign-button" data-semantic-layer="primitive">
    <span aria-hidden="true"><slot /></span>
  </TDesignButton>
</template>
<script setup lang="ts">
import { ref } from 'vue';
import { TDesignButton } from './tdesignPrimitiveBridge';
withDefaults(defineProps<{ label: string; disabled?: boolean; appearance?: 'default' | 'toolbar-menu-toggle' }>(), {
  appearance: 'default',
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
