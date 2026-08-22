<template>
  <div class="operations-page">
    <div class="page-heading">
      <div>
        <p class="eyebrow">运营分析</p>
        <h1>使用分析</h1>
        <p>基于真实场景和能力访问记录统计。</p>
      </div>
      <t-space
        ><t-button variant="outline" :loading="loading" @click="load">刷新</t-button
        ><t-button theme="primary" :loading="exporting" @click="exportCsv">导出 CSV</t-button></t-space
      >
    </div>
    <t-alert v-if="error" theme="error" :message="error" />
    <t-card :bordered="false" class="filters"
      ><t-space break-line
        ><t-input-number v-model="filters.top" :min="5" :max="100" /><t-select
          v-model="filters.days"
          :options="[
            { label: '最近 7 天', value: 7 },
            { label: '最近 30 天', value: 30 },
          ]"
        /><t-input v-model="filters.roleCode" placeholder="角色编码" /><t-input-number
          v-model="filters.userId"
          :min="0"
          placeholder="用户 ID"
        /><t-input v-model="filters.scenePrefix" placeholder="Scene 前缀" /><t-input
          v-model="filters.capabilityPrefix"
          placeholder="Capability 前缀"
        /><t-button theme="primary" @click="load">应用筛选</t-button></t-space
      ></t-card
    >
    <div class="metric-grid">
      <t-card v-for="item in metrics" :key="item.label" :bordered="false"
        ><span>{{ item.label }}</span
        ><strong>{{ item.value }}</strong></t-card
      >
    </div>
    <div class="tables">
      <t-card :bordered="false" class="panel"
        ><template #title>热门场景</template><t-table :data="sceneTop" :columns="columns" row-key="key" /></t-card
      ><t-card :bordered="false" class="panel"
        ><template #title>热门能力</template><t-table :data="capabilityTop" :columns="columns" row-key="key" /></t-card
      ><t-card :bordered="false" class="panel"
        ><template #title>每日趋势</template><t-table :data="dailyRows" :columns="dailyColumns" row-key="day"
      /></t-card>
    </div>
  </div>
</template>
<script setup lang="ts">
import { MessagePlugin } from 'tdesign-vue-next';
import { computed, onMounted, ref } from 'vue';

import type { UsageReport } from '@/api/odoo';
import { exportUsageCsv, fetchUsageReport } from '@/api/odoo';

const loading = ref(false);
const error = ref('');
const exporting = ref(false);
const filters = ref({ top: 10, days: 7, roleCode: '', userId: 0, scenePrefix: '', capabilityPrefix: '' });
const report = ref<UsageReport>({});
const metrics = computed(() => [
  { label: '场景访问次数', value: report.value.totals?.scene_open_total ?? 0 },
  { label: '能力访问次数', value: report.value.totals?.capability_open_total ?? 0 },
]);
const sceneTop = computed(() => report.value.scene_top || []);
const capabilityTop = computed(() => report.value.capability_top || []);
const dailyRows = computed(() =>
  (report.value.daily?.scene_open || []).map((row, index) => ({
    ...row,
    capability_count: report.value.daily?.capability_open?.[index]?.count || 0,
  })),
);
const columns = [
  { colKey: 'key', title: '场景', ellipsis: true },
  { colKey: 'count', title: '访问次数', width: 140 },
];
const dailyColumns = [
  { colKey: 'day', title: '日期' },
  { colKey: 'count', title: '场景访问' },
  { colKey: 'capability_count', title: '能力访问' },
];
async function load() {
  loading.value = true;
  error.value = '';
  try {
    report.value = await fetchUsageReport({
      top: filters.value.top,
      days: filters.value.days,
      roleCode: filters.value.roleCode,
      userId: filters.value.userId,
      scenePrefix: filters.value.scenePrefix,
      capabilityPrefix: filters.value.capabilityPrefix,
    });
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '使用分析加载失败';
  } finally {
    loading.value = false;
  }
}
async function exportCsv() {
  exporting.value = true;
  try {
    const result = await exportUsageCsv({
      top: filters.value.top,
      days: filters.value.days,
      role_code: filters.value.roleCode,
      user_id: filters.value.userId,
      scene_key_prefix: filters.value.scenePrefix,
      capability_key_prefix: filters.value.capabilityPrefix,
    });
    const blob = new Blob([result.content || ''], { type: 'text/csv;charset=utf-8' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = result.filename || 'usage-report.csv';
    link.click();
    URL.revokeObjectURL(link.href);
  } catch (cause) {
    MessagePlugin.error(cause instanceof Error ? cause.message : '导出失败');
  } finally {
    exporting.value = false;
  }
}
onMounted(load);
</script>
<style scoped>
.operations-page {
  display: grid;
  gap: 16px;
}
.page-heading {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}
.page-heading h1 {
  margin: 4px 0 8px;
  font-size: 28px;
}
.page-heading p {
  margin: 0;
  color: var(--td-text-color-secondary);
}
.eyebrow {
  color: var(--td-brand-color) !important;
  font-size: 13px;
}
.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
}
.filters {
  border: 1px solid var(--td-border-level-1-color);
}
.tables {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 16px;
}
.metric-grid :deep(.t-card),
.panel {
  border: 1px solid var(--td-border-level-1-color);
}
.metric-grid span {
  color: var(--td-text-color-secondary);
}
.metric-grid strong {
  display: block;
  margin-top: 8px;
  font-size: 28px;
}
</style>
