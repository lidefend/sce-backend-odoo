<template>
  <section class="activity-page" data-activity-surface="native-readonly">
    <slot name="toolbar" />
    <header class="activity-page__head">
      <div>
        <p class="activity-page__eyebrow">{{ labels.eyebrow }}</p>
        <h2>{{ title }}</h2>
      </div>
      <span class="activity-page__count">{{ model.records.length }} {{ labels.countSuffix }}</span>
    </header>
    <p v-if="loading" class="activity-page__state">{{ labels.loading }}</p>
    <p v-else-if="!model.ok" class="activity-page__state activity-page__state--error">{{ labels.unavailable }}：{{ model.reasonCode }}</p>
    <div v-else-if="model.records.length" class="activity-page__grid">
      <button
        v-for="(record, recordIndex) in model.records"
        :key="String(record.id || recordIndex)"
        :data-record-id="record.id || undefined"
        type="button"
        class="activity-card"
        @click="$emit('open-record', record)"
      >
        <span class="activity-card__identity">{{ labels.record }} #{{ record.id || recordIndex + 1 }}</span>
        <ActivityTemplateNode
          v-for="node in model.templateNodes"
          :key="node.key"
          :node="node"
          :record="record"
        />
      </button>
    </div>
    <div v-else class="activity-page__state">
      <strong>{{ labels.emptyTitle }}</strong>
      <span>{{ labels.emptyHint }}</span>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { ActivitySurfaceModel } from '../app/contracts/actionViewActivityContract';
import ActivityTemplateNode from './ActivityTemplateNode.vue';

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
.activity-page { display: grid; gap: 18px; padding: 22px; border: 1px solid #d8d3c8; border-radius: 18px; background: linear-gradient(145deg, #fffdf7, #f2efe6); }
.activity-page__head { display: flex; align-items: end; justify-content: space-between; gap: 18px; }
.activity-page__head h2 { margin: 2px 0 0; font-family: 'Noto Serif SC', serif; font-size: clamp(22px, 3vw, 34px); color: #24342d; }
.activity-page__eyebrow { margin: 0; color: #8a5a2b; font-size: 12px; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; }
.activity-page__count { color: #52635a; font-size: 13px; }
.activity-page__grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 12px; }
.activity-card { display: grid; gap: 10px; padding: 16px; border: 1px solid #d5d9d2; border-radius: 14px; background: rgba(255,255,255,.82); color: #203129; text-align: left; cursor: pointer; box-shadow: 0 8px 24px rgba(46,59,50,.06); }
.activity-card:hover { border-color: #a66a2c; transform: translateY(-1px); }
.activity-card__identity { color: #8a5a2b; font-size: 12px; font-weight: 700; }
.activity-card__field { display: grid; grid-template-columns: minmax(90px, .7fr) 1.3fr; gap: 10px; align-items: baseline; }
.activity-card__label { color: #66736c; font-size: 12px; }
.activity-card__value { overflow-wrap: anywhere; font-weight: 600; }
.activity-page__state { display: grid; gap: 4px; min-height: 130px; place-content: center; text-align: center; color: #67736c; }
.activity-page__state--error { color: #9a332b; }
@media (max-width: 680px) { .activity-page { padding: 16px; } .activity-page__grid { grid-template-columns: 1fr; } }
</style>
