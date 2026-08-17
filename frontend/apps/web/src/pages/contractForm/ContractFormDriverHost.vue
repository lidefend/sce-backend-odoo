<template>
  <section
    v-if="error || !renderModel"
    class="contract-form-driver-error"
    role="alert"
    data-contract-form-driver-error
  >
    <strong>页面契约无法渲染</strong>
    <span>{{ error || 'CANONICAL_FORM_RENDER_MODEL_MISSING' }}</span>
  </section>
  <component
    v-else
    :is="nativeCanvasComponent"
    v-bind="$attrs"
    data-contract-form-driver="sc-native"
    :data-source-contract-sha="renderModel.identity.sourceContractSha256"
    :data-render-model-fields="String(fieldCount)"
    :data-render-model-actions="String(renderModel.actionBar.length)"
  />
</template>

<script setup lang="ts">
import { computed, type Component } from 'vue';
import type { CanonicalFormNode, CanonicalFormRenderModel } from '../../app/presentation/canonicalFormRenderModel';
import ContractFormNativeCanvas from './ContractFormNativeCanvas.vue';

defineOptions({ inheritAttrs: false });
const props = defineProps<{
  renderModel: CanonicalFormRenderModel | null;
  error?: string;
}>();
const nativeCanvasComponent = ContractFormNativeCanvas as Component;

function countFields(nodes: CanonicalFormNode[]): number {
  return nodes.reduce((total, node) => total + node.fields.length + countFields(node.children), 0);
}

const fieldCount = computed(() => props.renderModel
  ? countFields([...props.renderModel.zones.primary, ...props.renderModel.zones.subordinate])
  : 0);
</script>

<style scoped>
.contract-form-driver-error {
  display: grid;
  gap: 6px;
  padding: 20px;
  border: 1px solid var(--sc-color-danger-border, #e5a6a6);
  border-radius: 8px;
  background: var(--sc-color-danger-surface, #fff5f5);
  color: var(--sc-color-danger-text, #8a1f1f);
}
</style>
