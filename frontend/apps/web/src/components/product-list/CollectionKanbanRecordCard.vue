<template>
  <article
    class="collection-kanban-record-card"
    :class="`tone-${tone}`"
    data-semantic-component="CollectionKanbanRecordCard"
    :data-record-key="recordKey"
    :data-state="disabled ? 'disabled' : 'ready'"
    role="button"
    :tabindex="disabled ? -1 : 0"
    :aria-label="openAriaLabel"
    :aria-disabled="disabled || undefined"
    :title="disabledReason || undefined"
    @click="openRecord"
    @keydown.enter="openRecord"
    @keydown.space.prevent="openRecord"
  >
    <h3 class="collection-kanban-record-card__title">{{ title }}</h3>
    <div v-if="statuses.length" class="collection-kanban-record-card__statuses" aria-label="记录状态">
      <ScStatusBadge
        v-for="status in statuses"
        :key="status.key"
        :value="status.key"
        :label="`${status.label}: ${status.value}`"
        :semantic="status.semantic || 'info'"
      />
    </div>
    <dl v-if="primaryFacts.length" class="collection-kanban-record-card__facts is-primary">
      <div v-for="fact in primaryFacts" :key="fact.key" class="collection-kanban-record-card__fact" :data-fact-key="fact.key">
        <dt>{{ fact.label }}</dt><dd>{{ fact.value }}</dd>
      </div>
    </dl>
    <dl v-if="secondaryFacts.length" class="collection-kanban-record-card__facts">
      <div v-for="fact in secondaryFacts" :key="fact.key" class="collection-kanban-record-card__fact" :data-fact-key="fact.key">
        <dt>{{ fact.label }}</dt><dd>{{ fact.value }}</dd>
      </div>
    </dl>
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import ScStatusBadge from '../design-system/ScStatusBadge.vue';

export type CollectionKanbanFact = { key: string; label: string; value: string };
export type CollectionKanbanStatus = CollectionKanbanFact & { semantic?: 'default' | 'info' | 'success' | 'warning' | 'danger' };

const props = withDefaults(defineProps<{
  recordKey: string;
  title: string;
  tone?: 'default' | 'neutral' | 'info' | 'success' | 'warning' | 'danger';
  statuses?: CollectionKanbanStatus[];
  primaryFacts?: CollectionKanbanFact[];
  secondaryFacts?: CollectionKanbanFact[];
  openLabel?: string;
  disabled?: boolean;
  disabledReason?: string;
}>(), {
  tone: 'default',
  statuses: () => [],
  primaryFacts: () => [],
  secondaryFacts: () => [],
  openLabel: '打开记录',
  disabled: false,
  disabledReason: '',
});

const emit = defineEmits<{ open: [] }>();
const openAriaLabel = computed(() => `${props.openLabel}：${props.title}`);

function openRecord() {
  if (!props.disabled) emit('open');
}
</script>

<style scoped src="./CollectionKanbanRecordCard.css"></style>
