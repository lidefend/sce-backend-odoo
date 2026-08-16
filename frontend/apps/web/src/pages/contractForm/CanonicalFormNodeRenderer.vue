<template>
  <section
    v-if="node.visible && hasContent"
    class="canonical-form-node"
    :data-canonical-node-id="node.nodeId"
    :data-canonical-node-kind="node.kind"
    :data-section-navigation-role="node.zoneRole"
    :data-group-title="node.title || undefined"
  >
    <FormSection
      v-if="fields.length"
      :title="node.title"
      :columns="columns"
      :fields="fields"
      :relation-adapter="relationAdapter"
      @field-change="emit('field-change', $event)"
    />
    <h3 v-else-if="node.title && children.length" class="canonical-form-node-title">{{ node.title }}</h3>
    <CanonicalFormNodeRenderer
      v-for="child in children"
      :key="child.nodeId"
      :node="child"
      :relation-adapter="relationAdapter"
      @field-change="emit('field-change', $event)"
    />
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { CanonicalFormNode } from '../../app/presentation/canonicalFormRenderModel';
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
}>();
const emit = defineEmits<{ 'field-change': [payload: FormSectionFieldChange] }>();

const fields = computed(() => canonicalSectionFields(props.node).map(canonicalFieldToFormSection));
const children = computed(() => visibleCanonicalChildren(props.node));
const columns = computed<1 | 2 | 3>(() => Math.max(1, Math.min(3, Number(props.node.columns || 1))) as 1 | 2 | 3);
const hasContent = computed(() => canonicalNodeHasContent(props.node));
</script>

<style scoped>
.canonical-form-node { min-width: 0; }
.canonical-form-node + .canonical-form-node { margin-top: 16px; }
.canonical-form-node-title {
  margin: 0 0 12px;
  color: var(--sc-app-text-primary);
  font-size: 15px;
}
</style>
