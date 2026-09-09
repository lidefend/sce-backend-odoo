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
    <nav v-if="sectionLinks.length > 1" class="object-task-page__section-nav" aria-label="表单章节" data-form-section-navigation>
      <ScButton
        v-for="item in sectionLinks"
        :key="item.region"
        type="button"
        variant="ghost"
        size="small"
        appearance="context-action"
        :data-section-link="item.region"
        @click="scrollToRegion(item.region)"
      >{{ item.label }}</ScButton>
    </nav>
    <ScCard
      v-if="summaryNodes.length"
      class="object-task-page__summary"
      aria-label="关键业务摘要"
      data-floorplan-region="summary"
      data-section-title="概览"
      data-canonical-zone="primary"
      :bordered="true"
      appearance="summary"
    >
      <div class="object-task-page__summary-grid">
        <CanonicalFormNodeRenderer
          v-for="node in summaryNodes"
          :key="node.nodeId"
          :node="node"
          :relation-adapter="relationAdapter"
          prefer-readonly-facts
          @field-change="emit('field-change', $event)"
          @field-action="emit('field-action', $event)"
        />
      </div>
    </ScCard>
    <ScCard
      v-if="decisionInputNodes.length"
      class="object-task-page__decision-input"
      aria-label="关键办理金额"
      data-floorplan-region="decision-input"
      data-section-title="关键金额"
      title="关键金额"
      data-canonical-zone="primary"
      :bordered="true"
      appearance="task-section"
    >
      <CanonicalFormNodeRenderer
        v-for="node in decisionInputNodes"
        :key="node.nodeId"
        :node="node"
        :relation-adapter="relationAdapter"
        prefer-readonly-facts
        @field-change="emit('field-change', $event)"
        @field-action="emit('field-action', $event)"
      />
    </ScCard>
    <ScCard
      v-if="decisionMode && (taskNodes.length || riskNodes.length || $slots.actions || $slots.blocking)"
      class="object-task-page__current-task"
      aria-label="办理提示"
      data-floorplan-region="current-task"
      data-section-title="办理提示"
      title="办理提示"
      :bordered="true"
      appearance="task"
      body-class-name="object-task-page__current-task-body"
    >
      <div class="object-task-page__current-task-copy">
        <slot name="blocking" />
        <CanonicalFormNodeRenderer
          v-for="node in taskNodes"
          :key="node.nodeId"
          :node="node"
          :relation-adapter="relationAdapter"
          prefer-readonly-facts
          density="compact-task"
          @field-change="emit('field-change', $event)"
          @field-action="emit('field-action', $event)"
        />
        <div v-if="riskNodes.length" class="object-task-page__current-task-facts" data-floorplan-region="risk">
          <CanonicalFormNodeRenderer
            v-for="node in riskNodes"
            :key="node.nodeId"
            :node="node"
            :relation-adapter="relationAdapter"
            prefer-readonly-facts
            density="compact-task"
            @field-change="emit('field-change', $event)"
          @field-action="emit('field-action', $event)"
          />
        </div>
      </div>
      <template v-if="$slots.actions" #actions>
        <div class="object-task-page__current-task-actions" data-floorplan-region="action-bar" data-mobile-action-surface>
          <slot name="actions" />
        </div>
      </template>
    </ScCard>
    <ScCard
      v-if="coreInputNodes.length"
      class="object-task-page__core-input"
      aria-label="基本信息"
      data-floorplan-region="core-input"
      data-section-title="基本信息"
      title="基本信息"
      data-canonical-zone="primary"
      :bordered="true"
      appearance="task-section"
    >
      <CanonicalFormNodeRenderer
        v-for="node in coreInputNodes"
        :key="node.nodeId"
        :node="node"
        :relation-adapter="relationAdapter"
        prefer-readonly-facts
        @field-change="emit('field-change', $event)"
          @field-action="emit('field-action', $event)"
      />
    </ScCard>
    <ScCard
      v-if="conditionInputNodes.length"
      class="object-task-page__condition-input"
      aria-label="当前办理条件"
      data-floorplan-region="condition-input"
      data-section-title="办理条件"
      data-canonical-zone="primary"
      title="当前办理条件"
      :bordered="true"
      appearance="task-section"
    >
      <CanonicalFormNodeRenderer
        v-for="node in conditionInputNodes"
        :key="node.nodeId"
        :node="node"
        :relation-adapter="relationAdapter"
        prefer-readonly-facts
        @field-change="emit('field-change', $event)"
          @field-action="emit('field-action', $event)"
      />
    </ScCard>
    <ScCard
      v-if="preExecutionInputTitle && preExecutionInputNodes.length"
      class="object-task-page__pre-execution-input"
      :aria-label="preExecutionInputTitle"
      data-floorplan-region="pre-execution-input"
      :data-section-title="preExecutionInputTitle"
      data-canonical-zone="primary"
      :title="preExecutionInputTitle"
      :bordered="true"
      appearance="task-section"
    >
      <CanonicalFormNodeRenderer
        v-for="node in preExecutionInputNodes"
        :key="node.nodeId"
        :node="node"
        :relation-adapter="relationAdapter"
        prefer-readonly-facts
        @field-change="emit('field-change', $event)"
          @field-action="emit('field-action', $event)"
      />
    </ScCard>
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
          @field-action="emit('field-action', $event)"
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
          @field-action="emit('field-action', $event)"
          />
        </template>
      </main>
      <ScCard
        v-if="contextNodes.length"
        class="object-task-page__context"
        aria-label="业务上下文"
        data-floorplan-region="business-context"
        data-section-title="基本资料"
        title="基本资料"
        data-canonical-zone="primary"
        :bordered="true"
        appearance="context"
      >
        <CanonicalFormNodeRenderer
          v-for="node in contextNodes"
          :key="node.nodeId"
          :node="node"
          :relation-adapter="relationAdapter"
          prefer-readonly-facts
          @field-change="emit('field-change', $event)"
          @field-action="emit('field-action', $event)"
        />
      </ScCard>
    </div>
    <ScCard
      v-if="presentableRelationNodes.length"
      class="object-task-page__relation"
      role="region"
      aria-label="关系明细"
      data-floorplan-region="relation"
      data-section-title="关系明细"
      data-canonical-zone="primary"
      title="关系明细"
      :bordered="true"
      appearance="relation"
    >
      <CanonicalFormNodeRenderer
        v-for="node in presentableRelationNodes"
        :key="node.nodeId"
        :node="node"
        :relation-adapter="relationAdapter"
        prefer-readonly-facts
        @field-change="emit('field-change', $event)"
          @field-action="emit('field-action', $event)"
      />
    </ScCard>
    <ScDisclosure
      v-if="supplementaryInputNodes.length"
      class="object-task-page__supplementary-input"
      data-floorplan-region="supplementary-input"
      data-section-title="补充信息"
      title="补充信息"
    >
      <CanonicalFormNodeRenderer
        v-for="node in supplementaryInputNodes"
        :key="node.nodeId"
        :node="node"
        :relation-adapter="relationAdapter"
        prefer-readonly-facts
        @field-change="emit('field-change', $event)"
        @field-action="emit('field-action', $event)"
      />
    </ScDisclosure>
    <ScDisclosure
      v-if="overflowContextNodes.length"
      class="object-task-page__overflow-context"
      data-floorplan-region="overflow-context"
      data-section-title="更多信息"
      title="更多业务信息"
    >
      <CanonicalFormNodeRenderer
        v-for="node in overflowContextNodes"
        :key="node.nodeId"
        :node="node"
        :relation-adapter="relationAdapter"
        prefer-readonly-facts
        @field-change="emit('field-change', $event)"
        @field-action="emit('field-action', $event)"
      />
    </ScDisclosure>
    <section
      v-if="subordinateNodes.length"
      class="object-task-page__subordinate"
      aria-label="附件与从属信息"
      data-floorplan-region="subordinate"
      data-section-title="附件与辅助信息"
      data-canonical-zone="subordinate"
    >
      <CanonicalFormNodeRenderer
        v-for="node in subordinateNodes"
        :key="node.nodeId"
        :node="node"
        :relation-adapter="relationAdapter"
        prefer-readonly-facts
        @field-change="emit('field-change', $event)"
          @field-action="emit('field-action', $event)"
      />
    </section>
    <section
      v-if="hasCollaboration"
      class="object-task-page__activity"
      aria-label="活动"
      data-floorplan-region="activity"
      data-section-title="协作记录"
      data-canonical-zone="subordinate"
    ><slot name="collaboration" /></section>
    <section v-if="hasAudit || auditNodes.length || auditEvents.length" class="object-task-page__audit" data-floorplan-region="audit">
      <ProfessionalAuditTimeline :events="auditEvents" :declared="hasAudit" :fallback-available="auditNodes.length > 0">
        <div data-audit-content>
        <CanonicalFormNodeRenderer
          v-for="node in auditNodes"
          :key="node.nodeId"
          :node="node"
          :relation-adapter="relationAdapter"
          prefer-readonly-facts
          @field-change="emit('field-change', $event)"
          @field-action="emit('field-action', $event)"
        />
        </div>
      </ProfessionalAuditTimeline>
    </section>
    <footer v-if="!decisionMode && $slots.actions" class="object-task-page__actions" data-floorplan-region="action-bar">
      <slot name="actions" />
    </footer>
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { CanonicalAuditEvent, CanonicalFormNode } from '../../app/presentation/canonicalFormRenderModel';
import type { FormSectionFieldActionPayload, FormSectionFieldChange } from '../../components/template/formSection.types';
import type { RelationFieldAdapter } from '../../components/template/relationField.types';
import CanonicalFormNodeRenderer from './CanonicalFormNodeRenderer.vue';
import ProfessionalAuditTimeline from './ProfessionalAuditTimeline.vue';
import ScCard from '../../components/design-system/ScCard.vue';
import ScDisclosure from '../../components/design-system/ScDisclosure.vue';
import ScButton from '../../components/design-system/ScButton.vue';
import { canonicalNodeHasPresentableContent } from './canonicalFormRenderer';

const props = defineProps<{
  summaryNodes: CanonicalFormNode[];
  decisionInputNodes: CanonicalFormNode[];
  taskNodes: CanonicalFormNode[];
  coreInputNodes: CanonicalFormNode[];
  conditionInputNodes: CanonicalFormNode[];
  preExecutionInputNodes: CanonicalFormNode[];
  preExecutionInputTitle?: string;
  supplementaryInputNodes: CanonicalFormNode[];
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
const emit = defineEmits<{ 'field-change': [payload: FormSectionFieldChange]; 'field-action': [payload: FormSectionFieldActionPayload] }>();
const presentableRelationNodes = computed(() => props.relationNodes.filter((node) => (
  canonicalNodeHasPresentableContent(node, props.relationAdapter)
)));
const sectionLinks = computed(() => [
  props.summaryNodes.length ? { region: 'summary', label: '概览' } : null,
  props.decisionInputNodes.length ? { region: 'decision-input', label: '关键金额' } : null,
  props.decisionMode && (props.taskNodes.length || props.riskNodes.length) ? { region: 'current-task', label: '办理提示' } : null,
  props.coreInputNodes.length ? { region: 'core-input', label: '基本信息' } : null,
  props.contextNodes.length ? { region: 'business-context', label: '基本资料' } : null,
  presentableRelationNodes.value.length ? { region: 'relation', label: '关系明细' } : null,
  props.supplementaryInputNodes.length ? { region: 'supplementary-input', label: '补充信息' } : null,
  props.overflowContextNodes.length ? { region: 'overflow-context', label: '更多信息' } : null,
  props.subordinateNodes.length ? { region: 'subordinate', label: '附件与辅助信息' } : null,
  props.hasCollaboration ? { region: 'activity', label: '协作记录' } : null,
].filter((item): item is { region: string; label: string } => Boolean(item)));

function scrollToRegion(region: string) {
  const target = document.querySelector<HTMLElement>(`[data-object-task-page] [data-floorplan-region="${region}"]`);
  target?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

</script>

<style scoped>
.object-task-page {
  display: grid;
  grid-auto-rows: max-content;
  align-content: start;
  gap: 12px;
  min-width: 0;
}
.object-task-page__section-nav {
  position: sticky;
  z-index: 18;
  top: var(--sc-form-command-bar-height, 72px);
  display: flex;
  gap: 4px;
  min-width: 0;
  padding: 6px 0;
  overflow-x: auto;
  border-bottom: 1px solid var(--sc-app-border);
  background: var(--sc-app-panel);
  scrollbar-width: thin;
}
.object-task-page__section-nav :deep(.sc-btn) { flex: 0 0 auto; }
.object-task-page [data-section-title] { scroll-margin-top: calc(var(--sc-form-command-bar-height, 72px) + 52px); }
.object-task-page__body {
  display: grid;
  grid-auto-rows: max-content;
  align-content: start;
  grid-template-columns: minmax(0, 1fr);
  gap: 12px;
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
.object-task-page__decision-input,
.object-task-page__current-task,
.object-task-page__core-input,
.object-task-page__condition-input,
.object-task-page__pre-execution-input,
.object-task-page__supplementary-input,
.object-task-page__risk,
.object-task-page__audit,
.object-task-page__overflow-context,
.object-task-page__relation,
.object-task-page__activity,
.object-task-page__subordinate {
  min-width: 0;
}
.object-task-page__summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0;
}
.object-task-page__summary {
  border: 0;
  background: var(--sc-app-subtle-bg);
}
.object-task-page__current-task,
.object-task-page__context {
  border: 0;
  border-top: 1px solid var(--sc-app-border);
  border-radius: 0;
  box-shadow: none;
}
.object-task-page__summary-grid :deep(.canonical-form-node) {
  grid-column: auto !important;
  height: auto;
  margin-top: 0 !important;
  padding: 10px 14px;
  border: 0;
  border-right: 1px solid var(--sc-app-border);
  border-radius: 0;
  background: transparent;
}
.object-task-page__summary-grid :deep([data-value-emphasis='monetary']) {
  grid-column: span 2 !important;
  background: var(--sc-app-panel);
}
.object-task-page__summary-grid :deep([data-value-emphasis='monetary'] .readonly-value),
.object-task-page__summary-grid :deep([data-value-emphasis='monetary'] .contract-readonly-value) {
  font-size: 18px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.object-task-page__summary-grid :deep(.canonical-form-node:last-child) { border-right:0; }
.object-task-page__summary-grid > :deep(.canonical-form-node:nth-child(4n)) { border-right: 0; }
.object-task-page__summary-grid > :deep(.canonical-form-node:nth-child(n + 5)) { border-top: 1px solid var(--sc-app-border); }
.object-task-page__current-task {
  min-width: 0;
}
.object-task-page__current-task :deep(.object-task-page__current-task-body) { padding-block: 4px 10px; }
.object-task-page__current-task-copy {
  display: grid;
  grid-auto-rows: max-content;
  align-content: start;
  gap: 6px;
}
.object-task-page__current-task-facts {
  padding-top: 8px;
  border-top: 1px solid var(--sc-app-warning-border);
  color: var(--sc-app-text-secondary);
}
.object-task-page__current-task-actions { min-width: max-content; }
.object-task-page__risk {
  padding: 12px 14px;
  border: 1px solid var(--sc-app-warning-border);
  border-radius: var(--sc-product-radius-panel);
  background: var(--sc-app-warning-bg);
}
.object-task-page__core-input,
.object-task-page__condition-input,
.object-task-page__pre-execution-input {
  overflow: hidden;
}
.object-task-page__condition-input {
  border-color: var(--sc-app-warning-border);
}
.object-task-page__pre-execution-input {
  border-color: var(--sc-app-info-border);
}
.object-task-page__supplementary-input {
  padding: 2px 0;
  border-block: 1px solid var(--sc-app-border);
  background: transparent;
}
.object-task-page__audit {
  padding: 12px 16px;
  border: 1px solid var(--sc-app-border);
  border-radius: var(--sc-product-radius-panel);
  background: var(--sc-app-panel);
}
.object-task-page__overflow-context {
  padding: 2px 0;
  border-bottom: 1px solid var(--sc-app-border);
  background: transparent;
}
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
  min-width: 0;
}
.object-task-page__subordinate {
  padding-top: 16px;
  border-top: 1px solid var(--sc-app-border);
}
.object-task-page__activity {
  padding: 14px 16px;
  border: 1px solid var(--sc-app-border);
  border-radius: var(--sc-product-radius-panel);
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
  .object-task-page__summary-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .object-task-page__summary-grid :deep(.canonical-form-node:nth-child(2n)) { border-right:0; }
  .object-task-page__summary-grid :deep(.canonical-form-node:nth-child(n + 3)) { border-top:1px solid var(--sc-app-border); }
  .object-task-page__current-task-actions { min-width: 0; }
  .object-task-page--with-context .object-task-page__body {
    grid-template-columns: minmax(0, 1fr);
  }
}
@media (max-width: 560px) {
  .object-task-page--decision {
    padding-bottom: calc(72px + env(safe-area-inset-bottom, 0px));
  }
  .object-task-page__summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
    padding: 10px;
  }
  .object-task-page__summary-grid :deep(.canonical-form-node) {
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
