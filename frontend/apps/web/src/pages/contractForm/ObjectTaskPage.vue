<template>
  <article
    class="object-task-page"
    :class="{ 'object-task-page--with-context': contextNodes.length }"
    data-object-task-page
    data-canonical-form-zones
  >
    <slot name="blocking" />
    <div class="object-task-page__body">
      <main class="object-task-page__canvas" data-floorplan-region="task-canvas" data-canonical-zone="primary">
        <CanonicalFormNodeRenderer
          v-for="node in taskNodes"
          :key="node.nodeId"
          :node="node"
          :relation-adapter="relationAdapter"
          @field-change="emit('field-change', $event)"
        />
      </main>
      <aside
        v-if="contextNodes.length"
        class="object-task-page__context"
        aria-label="业务上下文"
        data-floorplan-region="business-context"
        data-canonical-zone="primary"
      >
        <CanonicalFormNodeRenderer
          v-for="node in contextNodes"
          :key="node.nodeId"
          :node="node"
          :relation-adapter="relationAdapter"
          @field-change="emit('field-change', $event)"
        />
      </aside>
    </div>
    <section
      v-if="subordinateNodes.length || hasCollaboration"
      class="object-task-page__subordinate"
      aria-label="关系、附件与活动"
      data-floorplan-region="subordinate"
      data-canonical-zone="subordinate"
    >
      <CanonicalFormNodeRenderer
        v-for="node in subordinateNodes"
        :key="node.nodeId"
        :node="node"
        :relation-adapter="relationAdapter"
        @field-change="emit('field-change', $event)"
      />
      <slot name="collaboration" />
    </section>
    <footer v-if="$slots.actions" class="object-task-page__actions" data-floorplan-region="action-bar">
      <slot name="actions" />
    </footer>
  </article>
</template>

<script setup lang="ts">
import type { CanonicalFormNode } from '../../app/presentation/canonicalFormRenderModel';
import type { FormSectionFieldChange } from '../../components/template/formSection.types';
import type { RelationFieldAdapter } from '../../components/template/relationField.types';
import CanonicalFormNodeRenderer from './CanonicalFormNodeRenderer.vue';

defineProps<{
  taskNodes: CanonicalFormNode[];
  contextNodes: CanonicalFormNode[];
  subordinateNodes: CanonicalFormNode[];
  relationAdapter?: RelationFieldAdapter;
  hasCollaboration?: boolean;
}>();
const emit = defineEmits<{ 'field-change': [payload: FormSectionFieldChange] }>();
</script>

<style scoped>
.object-task-page {
  display: grid;
  gap: 20px;
  min-width: 0;
}
.object-task-page__body {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 20px;
  min-width: 0;
}
.object-task-page--with-context .object-task-page__body {
  grid-template-columns: minmax(0, 2fr) minmax(280px, 1fr);
  align-items: start;
}
.object-task-page__canvas,
.object-task-page__context,
.object-task-page__subordinate {
  min-width: 0;
}
.object-task-page__context {
  padding: 16px;
  border: 1px solid var(--sc-app-border, #d7e0e8);
  border-radius: 12px;
  background: var(--sc-app-panel, #fff);
}
.object-task-page__subordinate {
  padding-top: 16px;
  border-top: 1px solid var(--sc-app-border, #d7e0e8);
}
.object-task-page__actions {
  position: sticky;
  z-index: 10;
  bottom: 0;
  min-width: 0;
  border-top: 1px solid var(--sc-app-border, #d7e0e8);
  background: color-mix(in srgb, var(--sc-app-panel, #fff) 94%, transparent);
  backdrop-filter: blur(8px);
}
@media (max-width: 960px) {
  .object-task-page--with-context .object-task-page__body {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
