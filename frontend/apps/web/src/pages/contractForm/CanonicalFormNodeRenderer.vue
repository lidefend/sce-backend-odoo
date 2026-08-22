<template>
  <section
    v-if="node.visible && hasContent"
    :class="['canonical-form-node', `canonical-form-node--${nodeKind}`, nativeClass]"
    :data-canonical-node-id="node.nodeId"
    :data-canonical-node-kind="node.kind"
    :data-native-class="nativeClass || undefined"
    :data-section-navigation-role="node.zoneRole"
    :data-group-title="node.title || undefined"
  >
    <span v-if="presentableNodeText" class="canonical-form-native-text">{{ presentableNodeText }}</span>
    <button
      v-if="node.action"
      type="button"
      class="canonical-form-native-action"
      :disabled="!node.action.enabled"
      :title="node.action.reasonCode || undefined"
      :data-action-ref="node.action.actionRef.actionId"
      :data-backend-identity="node.action.actionRef.backendIdentity"
      @click="node.action.enabled && emit('action-ref', node.action.actionRef)"
    >{{ node.title || node.action.label }}</button>
    <div v-else-if="node.nativeWidget" class="canonical-form-native-widget" :data-native-widget="node.nativeWidget" role="status">
      {{ node.title || node.nativeWidget }}
    </div>
    <FormSection
      v-if="fields.length"
      :title="nodeKind === 'field' ? '' : node.title"
      :columns="columns"
      :fields="fields"
      :relation-adapter="relationAdapter"
      :prefer-readonly-facts="preferReadonlyFacts"
      @field-change="emit('field-change', $event)"
      @action-ref="emit('action-ref', $event)"
    />
    <h3 v-else-if="node.title && children.length" class="canonical-form-node-title">{{ node.title }}</h3>
    <CanonicalFormNodeRenderer
      v-for="child in children"
      :key="child.nodeId"
      :node="child"
      :relation-adapter="relationAdapter"
      :prefer-readonly-facts="preferReadonlyFacts"
      @field-change="emit('field-change', $event)"
      @action-ref="emit('action-ref', $event)"
    />
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { CanonicalFormNode } from '../../app/presentation/canonicalFormRenderModel';
import type { ContractV2ActionRule } from '../../app/contracts/v2/types';
import FormSection from '../../components/template/FormSection.vue';
import type { FormSectionFieldChange } from '../../components/template/formSection.types';
import type { RelationFieldAdapter } from '../../components/template/relationField.types';
import {
  canonicalFieldToFormSection,
  canonicalNodeHasContent,
  canonicalSectionFields,
  visibleCanonicalChildren,
} from './canonicalFormRenderer';

const props = defineProps<{
  node: CanonicalFormNode;
  relationAdapter?: RelationFieldAdapter;
  preferReadonlyFacts?: boolean;
}>();
const emit = defineEmits<{
  'field-change': [payload: FormSectionFieldChange];
  'action-ref': [action: ContractV2ActionRule];
}>();

const nodeKind = computed(() => String(props.node.kind || 'container').trim().toLowerCase());
const fields = computed(() => canonicalSectionFields(props.node).map((field) => (
  canonicalFieldToFormSection(field, props.relationAdapter)
)));
const children = computed(() => visibleCanonicalChildren(props.node));
const columns = computed<1 | 2 | 3>(() => Math.max(1, Math.min(3, Number(props.node.columns || 1))) as 1 | 2 | 3);
const hasContent = computed(() => canonicalNodeHasContent(props.node));
const nativeClass = computed(() => String(props.node.attributes.class || '').trim());
const presentableNodeText = computed(() => {
  const text = String(props.node.text || '');
  if (props.preferReadonlyFacts && /^[\s.·•:_-]+$/.test(text)) return '';
  return text;
});
</script>

<style scoped>
.canonical-form-node { min-width: 0; }
.canonical-form-node + .canonical-form-node { margin-top: 16px; }
.canonical-form-node--field {
  display: inline-block;
  max-width: 100%;
  vertical-align: baseline;
}
.canonical-form-node--field + .canonical-form-node--field,
.canonical-form-native-text + .canonical-form-node--field,
.canonical-form-node--field + .canonical-form-native-text { margin-top: 0; }
.canonical-form-node--field :deep(.template-form-section) {
  display: inline;
  padding: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}
.canonical-form-node--field :deep(.template-form-section-grid),
.canonical-form-node--field :deep(.field),
.canonical-form-node--field :deep(.field-control-row),
.canonical-form-node--field :deep(.field-control-main) { display: inline; }
.canonical-form-node--field :deep(.readonly-value),
.canonical-form-node--field :deep(.contract-readonly-value) {
  min-height: 0;
  font: inherit;
  color: inherit;
}
.canonical-form-node-title {
  margin: 0 0 12px;
  color: var(--sc-app-text-primary);
  font-size: 15px;
}
.canonical-form-native-action {
  border: 0;
  background: transparent;
  color: var(--sc-semantic-surface-interactive);
  cursor: pointer;
}
.canonical-form-native-action:disabled { cursor: not-allowed; opacity: 0.55; }
.canonical-form-native-widget { color: var(--sc-app-text-secondary); }
.canonical-form-native-text { white-space: pre-wrap; }
</style>
