<template>
  <article
    class="professional-audit-event"
    data-professional-audit-event
    :data-audit-event-key="event.key"
  >
    <header>
      <strong data-audit-event-name>{{ event.event }}</strong>
      <span class="professional-audit-event__result" data-audit-result>{{ event.result }}</span>
    </header>
    <p class="professional-audit-event__meta">
      <span data-audit-actor>{{ event.actor }}</span>
      <time :datetime="event.occurredAt" data-audit-time>{{ formatProfessionalAuditTime(event.occurredAt) }}</time>
    </p>
    <p v-if="event.detail" class="professional-audit-event__detail" data-audit-detail>{{ event.detail }}</p>
  </article>
</template>

<script setup lang="ts">
import type { CanonicalAuditEvent } from '../../app/presentation/canonicalFormRenderModel';
import { formatProfessionalAuditTime } from './professionalAuditModel';

defineProps<{ event: CanonicalAuditEvent }>();
</script>

<style scoped>
.professional-audit-event { display: grid; gap: var(--sc-product-space-1); min-width: 0; }
.professional-audit-event header, .professional-audit-event__meta { display: flex; align-items: baseline; justify-content: space-between; gap: var(--sc-product-space-2); }
.professional-audit-event__result { color: var(--sc-app-text-secondary); }
.professional-audit-event__meta, .professional-audit-event__detail { margin: 0; color: var(--sc-app-text-secondary); }
.professional-audit-event__detail { color: var(--sc-app-text-primary); overflow-wrap: anywhere; }
@media (max-width: 640px) { .professional-audit-event header, .professional-audit-event__meta { align-items: flex-start; flex-direction: column; gap: var(--sc-product-space-1); } }
</style>
