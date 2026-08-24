<template>
  <details
    v-if="declared || events.length || fallbackAvailable"
    class="professional-audit-timeline"
    data-professional-audit-timeline
    :data-audit-event-count="events.length"
  >
    <summary>{{ summary }}</summary>
    <ol v-if="events.length" aria-label="审计事件">
      <li v-for="event in events" :key="event.key">
        <ProfessionalAuditEvent :event="event" />
      </li>
    </ol>
    <div v-else-if="fallbackAvailable" data-audit-readable-fallback><slot /></div>
    <ScEmptyState v-else title="暂无审计记录" description="当前记录尚未产生可显示的审计事件。" />
  </details>
</template>

<script setup lang="ts">
import type { CanonicalAuditEvent } from '../../app/presentation/canonicalFormRenderModel';
import ScEmptyState from '../../components/design-system/ScEmptyState.vue';
import ProfessionalAuditEvent from './ProfessionalAuditEvent.vue';

withDefaults(defineProps<{
  events: CanonicalAuditEvent[];
  declared?: boolean;
  fallbackAvailable?: boolean;
  summary?: string;
}>(), { declared: false, fallbackAvailable: false, summary: '审批与历史审计' });
</script>

<style scoped>
.professional-audit-timeline > summary { cursor: pointer; font-weight: 700; }
.professional-audit-timeline ol { display: grid; gap: var(--sc-product-space-2); margin: var(--sc-product-space-2) 0 0; padding: 0; list-style: none; }
.professional-audit-timeline li { padding-block: var(--sc-product-space-2); border-bottom: 1px solid var(--sc-app-border); }
</style>
