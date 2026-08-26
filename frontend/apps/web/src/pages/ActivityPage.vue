<template>
  <section
    class="activity-page"
    data-activity-surface="native-readonly"
    :data-state="loading ? 'loading' : !model.ok ? 'error' : model.records.length ? 'ready' : 'empty'"
  >
    <slot name="toolbar" />
    <header class="activity-page__head">
      <div>
        <p class="activity-page__eyebrow">{{ labels.eyebrow }}</p>
        <h2>{{ title }}</h2>
      </div>
      <span class="activity-page__count">{{ model.records.length }} {{ labels.countSuffix }}</span>
    </header>
    <ScLoading v-if="loading" class="activity-page__state" :label="labels.loading" />
    <ScErrorState
      v-else-if="!model.ok"
      class="activity-page__state activity-page__state--error"
      :title="labels.unavailable"
      :description="model.reasonCode"
    />
    <div v-else-if="model.records.length" class="activity-page__grid">
      <ScButton
        v-for="(record, recordIndex) in model.records"
        :key="String(record.id || recordIndex)"
        :data-record-id="record.id || undefined"
        type="button"
        variant="ghost"
        class="activity-card"
        appearance="surface-tile"
        @click="$emit('open-record', record)"
      >
        <span class="activity-card__identity">{{ labels.record }} #{{ record.id || recordIndex + 1 }}</span>
        <ActivityTemplateNode
          v-for="node in model.templateNodes"
          :key="node.key"
          :node="node"
          :record="record"
        />
      </ScButton>
    </div>
    <ScEmptyState v-else class="activity-page__state" :title="labels.emptyTitle" :description="labels.emptyHint" />
  </section>
</template>

<script setup lang="ts">
import type { ActivitySurfaceModel } from '../app/contracts/actionViewActivityContract';
import ActivityTemplateNode from './ActivityTemplateNode.vue';
import ScEmptyState from '../components/design-system/ScEmptyState.vue';
import ScButton from '../components/design-system/ScButton.vue';
import ScErrorState from '../components/design-system/ScErrorState.vue';
import ScLoading from '../components/design-system/ScLoading.vue';

type ActivityPageLabels = {
  eyebrow: string;
  countSuffix: string;
  loading: string;
  unavailable: string;
  record: string;
  emptyTitle: string;
  emptyHint: string;
};

defineProps<{ title: string; loading: boolean; model: ActivitySurfaceModel; labels: ActivityPageLabels }>();
defineEmits<{ 'open-record': [record: Record<string, unknown>] }>();
</script>

<style scoped>
.activity-page { display: grid; gap: 18px; padding: 22px; border: 1px solid var(--sc-app-border); border-radius: 18px; background: linear-gradient(145deg, var(--sc-app-panel), var(--sc-app-muted-bg)); }
.activity-page__head { display: flex; align-items: end; justify-content: space-between; gap: 18px; }
.activity-page__head h2 { margin: 2px 0 0; font-family: 'Noto Serif SC', serif; font-size: clamp(22px, 3vw, 34px); color: var(--sc-app-text-primary); }
.activity-page__eyebrow { margin: 0; color: var(--sc-text-link); font-size: 12px; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; }
.activity-page__count { color: var(--sc-app-text-secondary); font-size: 13px; }
.activity-page__grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 12px; }
.activity-card { display: grid; gap: 10px; padding: 16px; text-align: left; }
.activity-card:hover { transform: translateY(-1px); }
.activity-card__identity { color: var(--sc-text-link); font-size: 12px; font-weight: 700; }
.activity-card__field { display: grid; grid-template-columns: minmax(90px, .7fr) 1.3fr; gap: 10px; align-items: baseline; }
.activity-card__label { color: var(--sc-app-text-secondary); font-size: 12px; }
.activity-card__value { overflow-wrap: anywhere; font-weight: 600; }
.activity-page__state { display: grid; gap: 4px; min-height: 130px; place-content: center; text-align: center; color: var(--sc-app-text-secondary); }
.activity-page__state--error { color: var(--sc-app-danger-text); }
@media (prefers-reduced-motion: reduce) { .activity-card { transition: none; } .activity-card:hover { transform: none; } }
@media (max-width: 680px) { .activity-page { padding: 16px; } .activity-page__grid { grid-template-columns: 1fr; } }
</style>
