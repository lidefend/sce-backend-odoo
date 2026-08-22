<template>
  <article
    class="object-task-page"
    :class="{
      'object-task-page--with-context': contextNodes.length,
      'object-task-page--context-only': contextNodes.length && !taskNodes.length,
      'object-task-page--decision': decisionMode,
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
        prefer-readonly-facts
        @field-change="emit('field-change', $event)"
      />
    </section>
    <section
      v-if="decisionMode && (taskNodes.length || riskNodes.length || $slots.actions || $slots.blocking)"
      class="object-task-page__current-task"
      aria-label="当前任务"
      data-floorplan-region="current-task"
    >
      <div class="object-task-page__current-task-copy">
        <strong class="object-task-page__current-task-title">当前任务</strong>
        <slot name="blocking" />
        <CanonicalFormNodeRenderer
          v-for="node in taskNodes"
          :key="node.nodeId"
          :node="node"
          :relation-adapter="relationAdapter"
          prefer-readonly-facts
          @field-change="emit('field-change', $event)"
        />
        <div v-if="riskNodes.length" class="object-task-page__current-task-facts" data-floorplan-region="risk">
          <CanonicalFormNodeRenderer
            v-for="node in riskNodes"
            :key="node.nodeId"
            :node="node"
            :relation-adapter="relationAdapter"
            prefer-readonly-facts
            @field-change="emit('field-change', $event)"
          />
        </div>
      </div>
      <div
        v-if="$slots.actions"
        class="object-task-page__current-task-actions"
        data-floorplan-region="action-bar"
        data-mobile-action-surface
      >
        <slot name="actions" />
      </div>
    </section>
    <slot v-if="!decisionMode" name="blocking" />
    <section
      v-if="!decisionMode && riskNodes.length"
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
        prefer-readonly-facts
        @field-change="emit('field-change', $event)"
      />
    </section>
    <div class="object-task-page__body">
      <main class="object-task-page__canvas" data-floorplan-region="task-canvas" data-canonical-zone="primary">
        <template v-if="!decisionMode">
          <CanonicalFormNodeRenderer
            v-for="node in taskNodes"
            :key="node.nodeId"
            :node="node"
            :relation-adapter="relationAdapter"
            prefer-readonly-facts
            @field-change="emit('field-change', $event)"
          />
        </template>
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
          prefer-readonly-facts
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
        prefer-readonly-facts
        @field-change="emit('field-change', $event)"
      />
    </details>
    <section
      v-if="relationNodes.length"
      class="object-task-page__relation"
      aria-label="关系明细"
      data-floorplan-region="relation"
      data-canonical-zone="primary"
    >
      <CanonicalFormNodeRenderer
        v-for="node in relationNodes"
        :key="node.nodeId"
        :node="node"
        :relation-adapter="relationAdapter"
        prefer-readonly-facts
        @field-change="emit('field-change', $event)"
      />
    </section>
    <section
      v-if="subordinateNodes.length"
      class="object-task-page__subordinate"
      aria-label="附件与从属信息"
      data-floorplan-region="subordinate"
      data-canonical-zone="subordinate"
    >
      <CanonicalFormNodeRenderer
        v-for="node in subordinateNodes"
        :key="node.nodeId"
        :node="node"
        :relation-adapter="relationAdapter"
        prefer-readonly-facts
        @field-change="emit('field-change', $event)"
      />
    </section>
    <section
      v-if="hasCollaboration"
      class="object-task-page__activity"
      aria-label="活动"
      data-floorplan-region="activity"
      data-canonical-zone="subordinate"
    ><slot name="collaboration" /></section>
    <details v-if="hasAudit || auditNodes.length || auditEvents.length" class="object-task-page__audit" data-floorplan-region="audit">
      <summary>审批与历史审计</summary>
      <div data-audit-content>
        <ol v-if="auditEvents.length" class="object-task-page__audit-events" aria-label="审计事件">
          <li v-for="event in auditEvents" :key="event.key" class="object-task-page__audit-event" data-audit-event>
            <strong data-audit-event-name>{{ event.event }}</strong>
            <span data-audit-result>{{ event.result }}</span>
            <span data-audit-actor>{{ event.actor }}</span>
            <time :datetime="event.occurredAt" data-audit-time>{{ formatAuditTime(event.occurredAt) }}</time>
            <p v-if="event.detail">{{ event.detail }}</p>
          </li>
        </ol>
        <CanonicalFormNodeRenderer
          v-for="node in auditEvents.length ? [] : auditNodes"
          :key="node.nodeId"
          :node="node"
          :relation-adapter="relationAdapter"
          prefer-readonly-facts
          @field-change="emit('field-change', $event)"
        />
        <p v-if="!auditEvents.length && !auditNodes.length" class="object-task-page__empty-fact">暂无审批与审计记录</p>
      </div>
    </details>
    <footer v-if="!decisionMode && $slots.actions" class="object-task-page__actions" data-floorplan-region="action-bar">
      <slot name="actions" />
    </footer>
  </article>
</template>

<script setup lang="ts">
import type { CanonicalAuditEvent, CanonicalFormNode } from '../../app/presentation/canonicalFormRenderModel';
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
  auditEvents: CanonicalAuditEvent[];
  relationNodes: CanonicalFormNode[];
  subordinateNodes: CanonicalFormNode[];
  relationAdapter?: RelationFieldAdapter;
  hasCollaboration?: boolean;
  hasAudit?: boolean;
  decisionMode?: boolean;
}>();
const emit = defineEmits<{ 'field-change': [payload: FormSectionFieldChange] }>();

function formatAuditTime(value: string) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(parsed);
}
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
.object-task-page--decision .object-task-page__body {
  grid-template-columns: minmax(0, 1fr);
}
.object-task-page--decision .object-task-page__canvas {
  display: none;
}
.object-task-page__canvas,
.object-task-page__context,
.object-task-page__summary,
.object-task-page__current-task,
.object-task-page__risk,
.object-task-page__audit,
.object-task-page__overflow-context,
.object-task-page__relation,
.object-task-page__activity,
.object-task-page__subordinate {
  min-width: 0;
}
.object-task-page__summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  padding: 16px;
  border: 1px solid var(--sc-app-border);
  border-radius: 12px;
  background: var(--sc-app-panel);
}
.object-task-page__summary :deep(.canonical-form-node) {
  height: 100%;
  padding: 12px 14px;
  border: 1px solid var(--sc-app-border);
  border-radius: 10px;
  background: color-mix(in srgb, var(--sc-app-panel) 82%, var(--sc-app-surface));
}
.object-task-page__current-task {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 20px;
  align-items: center;
  padding: 16px 20px;
  border: 1px solid var(--sc-app-border);
  border-radius: 12px;
  background: var(--sc-app-panel);
}
.object-task-page__current-task-copy { display: grid; gap: 8px; }
.object-task-page__current-task-title { color: var(--sc-app-text-primary); font-size: 16px; }
.object-task-page__current-task-facts {
  color: var(--sc-app-text-secondary);
}
.object-task-page__current-task-actions { min-width: max-content; }
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
.object-task-page__audit:not([open]) [data-audit-content] { display: none; }
.object-task-page__audit-events {
  display: grid;
  gap: 10px;
  margin: 12px 0 0;
  padding: 0;
  list-style: none;
}
.object-task-page__audit-event {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 4px 16px;
  padding: 12px;
  border: 1px solid var(--sc-app-border);
  border-radius: 8px;
}
.object-task-page__audit-event [data-audit-result] { color: var(--sc-app-success-text); }
.object-task-page__audit-event [data-audit-actor],
.object-task-page__audit-event time,
.object-task-page__audit-event p { color: var(--sc-app-text-secondary); }
.object-task-page__audit-event p { grid-column: 1 / -1; margin: 4px 0 0; }
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
.object-task-page__relation,
.object-task-page__activity {
  padding: 16px;
  border: 1px solid var(--sc-app-border);
  border-radius: 12px;
  background: var(--sc-app-panel);
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
  .object-task-page__summary { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .object-task-page__current-task { grid-template-columns: minmax(0, 1fr); }
  .object-task-page__current-task-actions { min-width: 0; }
  .object-task-page--with-context .object-task-page__body {
    grid-template-columns: minmax(0, 1fr);
  }
}
@media (max-width: 560px) {
  .object-task-page--decision {
    padding-bottom: calc(72px + env(safe-area-inset-bottom, 0px));
  }
  .object-task-page--decision .object-task-page__current-task { order: -1; }
  .object-task-page__summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
    padding: 10px;
  }
  .object-task-page__summary :deep(.canonical-form-node) {
    padding: 10px;
    overflow-wrap: anywhere;
  }
  .object-task-page__current-task-actions {
    position: fixed;
    z-index: 40;
    right: 0;
    bottom: 0;
    left: 0;
    min-width: 0;
    padding: 10px 12px calc(10px + env(safe-area-inset-bottom, 0px));
    border-top: 1px solid var(--sc-app-border);
    background: color-mix(in srgb, var(--sc-app-panel) 96%, transparent);
    box-shadow: var(--sc-app-shadow-popover);
    backdrop-filter: blur(10px);
  }
}
</style>
