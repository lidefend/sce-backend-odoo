<template>
  <ScDisclosure
    v-if="declared || events.length || fallbackAvailable"
    class="professional-audit-timeline"
    data-professional-audit-timeline
    data-floorplan-region="audit"
    :data-audit-event-count="events.length"
    :title="summary"
  >
    <ScTimeline v-if="events.length" aria-label="审计事件" :items="events.map((event) => ({ ...event, key: event.key }))">
      <template #item="{ item }"><ProfessionalAuditEvent :event="item as CanonicalAuditEvent" /></template>
    </ScTimeline>
    <div v-else-if="fallbackAvailable" data-audit-readable-fallback><slot /></div>
    <ScEmptyState v-else title="暂无审计记录" description="当前记录尚未产生可显示的审计事件。" />
  </ScDisclosure>
</template>

<script setup lang="ts">
import type { CanonicalAuditEvent } from '../../app/presentation/canonicalFormRenderModel';
import ScEmptyState from '../../components/design-system/ScEmptyState.vue';
import ScDisclosure from '../../components/design-system/ScDisclosure.vue';
import ScTimeline from '../../components/design-system/ScTimeline.vue';
import ProfessionalAuditEvent from './ProfessionalAuditEvent.vue';

withDefaults(defineProps<{
  events: CanonicalAuditEvent[];
  declared?: boolean;
  fallbackAvailable?: boolean;
  summary?: string;
}>(), { declared: false, fallbackAvailable: false, summary: '审批与历史审计' });
</script>

<style scoped>
.professional-audit-timeline :deep(.t-timeline) { margin-top: var(--sc-product-space-2); }
</style>
