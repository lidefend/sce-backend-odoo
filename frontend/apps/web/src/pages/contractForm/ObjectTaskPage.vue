<template>
  <article
    class="object-task-page"
    :class="{
      'object-task-page--with-context': contextNodes.length,
      'object-task-page--context-only': contextNodes.length && !taskNodes.length,
    }"
    data-object-task-page
    data-canonical-form-zones
  >
    <section
      v-if="summaryNodes.length"
      class="object-task-page__summary"
      aria-label="关键业务摘要"
      data-floorplan-region="summary"
      data-canonical-zone="primary"
    >
      <CanonicalFormNodeRenderer
        v-for="node in summaryNodes"
        :key="node.nodeId"
        :node="node"
        :relation-adapter="relationAdapter"
        @field-change="emit('field-change', $event)"
      />
    </section>
    <slot name="blocking" />
    <section
      v-if="riskNodes.length"
      class="object-task-page__risk"
      aria-label="风险与阻断"
      data-floorplan-region="risk"
      data-canonical-zone="primary"
    >
      <CanonicalFormNodeRenderer
        v-for="node in riskNodes"
        :key="node.nodeId"
        :node="node"
        :relation-adapter="relationAdapter"
        @field-change="emit('field-change', $event)"
      />
    </section>
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
    <details
      v-if="overflowContextNodes.length"
      class="object-task-page__overflow-context"
      data-floorplan-region="overflow-context"
    >
      <summary>更多业务信息</summary>
      <CanonicalFormNodeRenderer
        v-for="node in overflowContextNodes"
        :key="node.nodeId"
        :node="node"
        :relation-adapter="relationAdapter"
        @field-change="emit('field-change', $event)"
      />
    </details>
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
    <details v-if="auditNodes.length" class="object-task-page__audit" data-floorplan-region="audit">
      <summary>审批与历史审计</summary>
      <CanonicalFormNodeRenderer
        v-for="node in auditNodes"
        :key="node.nodeId"
        :node="node"
        :relation-adapter="relationAdapter"
        @field-change="emit('field-change', $event)"
      />
    </details>
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
  summaryNodes: CanonicalFormNode[];
  taskNodes: CanonicalFormNode[];
  contextNodes: CanonicalFormNode[];
  overflowContextNodes: CanonicalFormNode[];
  riskNodes: CanonicalFormNode[];
  auditNodes: CanonicalFormNode[];
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
.object-task-page--context-only .object-task-page__body {
  grid-template-columns: minmax(0, 1fr);
}
.object-task-page--context-only .object-task-page__canvas {
  display: none;
}
.object-task-page__canvas,
.object-task-page__context,
.object-task-page__summary,
.object-task-page__risk,
.object-task-page__audit,
.object-task-page__overflow-context,
.object-task-page__subordinate {
  min-width: 0;
}
.object-task-page__summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  padding: 16px;
  border: 1px solid var(--sc-app-border);
  border-radius: 12px;
  background: var(--sc-app-panel);
}
.object-task-page__risk {
  padding: 14px 16px;
  border: 1px solid var(--sc-app-warning-border);
  border-radius: 12px;
  background: var(--sc-app-warning-bg);
}
.object-task-page__audit {
  padding: 12px 16px;
  border: 1px solid var(--sc-app-border);
  border-radius: 12px;
  background: var(--sc-app-panel);
}
.object-task-page__overflow-context {
  padding: 12px 16px;
  border: 1px solid var(--sc-app-border);
  border-radius: 12px;
  background: var(--sc-app-panel);
}
.object-task-page__overflow-context > summary { cursor: pointer; font-weight: 600; }
.object-task-page__audit > summary { cursor: pointer; font-weight: 600; }
.object-task-page__context {
  padding: 16px;
  border: 1px solid var(--sc-app-border);
  border-radius: 12px;
  background: var(--sc-app-panel);
}
.object-task-page__subordinate {
  padding-top: 16px;
  border-top: 1px solid var(--sc-app-border);
}
.object-task-page__actions {
  position: sticky;
  z-index: 10;
  bottom: 0;
  min-width: 0;
  border-top: 1px solid var(--sc-app-border);
  background: color-mix(in srgb, var(--sc-app-panel) 94%, transparent);
  backdrop-filter: blur(8px);
}
@media (max-width: 960px) {
  .object-task-page__summary { grid-template-columns: minmax(0, 1fr); }
  .object-task-page--with-context .object-task-page__body {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
