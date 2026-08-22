<template>
  <div class="workbench-page">
    <header class="page-heading">
      <div>
        <span>运行诊断</span>
        <h1>系统工作台</h1>
        <p>读取当前账号的 system.init 与 Intent 目录，用于检查导航、场景、能力、接口覆盖和运行上下文。</p>
      </div>
      <t-button variant="outline" :loading="loading" @click="load">
        <template #icon><t-icon name="refresh" /></template>
        重新诊断
      </t-button>
    </header>

    <t-alert v-if="error" theme="error" :message="error" />

    <div class="summary-grid">
      <article v-for="item in summary" :key="item.label">
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
        <small>{{ item.hint }}</small>
      </article>
    </div>

    <div class="diagnostic-grid">
      <section class="panel">
        <header>
          <h2>账号与上下文</h2>
          <t-tag :theme="payload.user ? 'success' : 'danger'">{{ payload.user ? '已初始化' : '未初始化' }}</t-tag>
        </header>
        <dl>
          <template v-for="row in accountRows" :key="row.label"
            ><dt>{{ row.label }}</dt>
            <dd>{{ row.value }}</dd></template
          >
        </dl>
      </section>

      <section class="panel">
        <header>
          <h2>导航完整性</h2>
          <t-tag :theme="navigationCount ? 'success' : 'warning'">{{ navigationCount ? '可用' : '无菜单' }}</t-tag>
        </header>
        <dl>
          <template v-for="row in navigationRows" :key="row.label"
            ><dt>{{ row.label }}</dt>
            <dd>{{ row.value }}</dd></template
          >
        </dl>
      </section>

      <section class="panel">
        <header>
          <h2>场景运行时</h2>
          <t-tag :theme="sceneCount ? 'success' : 'warning'">{{ sceneCount ? '就绪' : '未下发' }}</t-tag>
        </header>
        <dl>
          <template v-for="row in sceneRows" :key="row.label"
            ><dt>{{ row.label }}</dt>
            <dd>{{ row.value }}</dd></template
          >
        </dl>
      </section>

      <section class="panel">
        <header>
          <h2>请求追踪</h2>
          <t-button v-if="requestMeta.traceId" size="small" variant="text" @click="copyTrace">复制 Trace ID</t-button>
        </header>
        <dl>
          <template v-for="row in runtimeRows" :key="row.label"
            ><dt>{{ row.label }}</dt>
            <dd>{{ row.value }}</dd></template
          >
        </dl>
      </section>
    </div>

    <section class="panel panel--wide">
      <header>
        <h2>初始化元数据</h2>
        <span>以下内容由后端 contract 原样提供</span>
      </header>
      <t-table :data="metadataRows" :columns="metadataColumns" row-key="key" size="small" stripe />
    </section>
  </div>
</template>
<script setup lang="ts">
import { MessagePlugin } from 'tdesign-vue-next';
import { computed, onMounted, ref } from 'vue';

import { apiCapabilityRegistry } from '@/api/capabilityRegistry';
import type { IntentCatalogResult, SystemInit } from '@/api/odoo';
import { fetchIntentCatalog, getLastRequestMeta, systemInit } from '@/api/odoo';

type Dict = Record<string, any>;
interface DisplayRow {
  label: string;
  value: string;
}

const loading = ref(false);
const error = ref('');
const payload = ref<SystemInit>({});
const intentCatalog = ref<IntentCatalogResult>({});
const requestMeta = ref(getLastRequestMeta());
const navigation = computed(() => payload.value.navigation_v1?.nav || []);
const navigationCount = computed(() => countNavigation(navigation.value));
const sceneReady = computed(() => asDict(payload.value.scene_ready_contract_v1));
const sceneRowsRaw = computed(() => normalizeRows(sceneReady.value.scenes));
const sceneCount = computed(() => sceneRowsRaw.value.length || normalizeRows(payload.value.scenes).length);
const capabilityCount = computed(() => countCollection(payload.value.capabilities));
const backendIntentNames = computed(() => {
  const direct = Array.isArray(intentCatalog.value.intents) ? intentCatalog.value.intents.map(String) : [];
  const catalog = normalizeRows(intentCatalog.value.intent_catalog)
    .map((row) => String(row.intent || row.name || row.key || ''))
    .filter(Boolean);
  return [...new Set([...direct, ...catalog])];
});
const registeredIntentNames = new Set(apiCapabilityRegistry.map((entry) => entry.intent));
const intentCount = computed(() => backendIntentNames.value.length || countCollection(payload.value.intents));
const registeredIntentCount = computed(
  () => backendIntentNames.value.filter((name) => registeredIntentNames.has(name)).length,
);
const unregisteredIntentCount = computed(
  () => backendIntentNames.value.filter((name) => !registeredIntentNames.has(name)).length,
);
const pageContractCount = computed(() => countCollection(payload.value.page_contracts));
const summary = computed(() => [
  { label: '动态菜单', value: navigationCount.value, hint: '当前角色可见节点' },
  { label: '能力项', value: capabilityCount.value, hint: '后端授权能力' },
  { label: '可用场景', value: sceneCount.value, hint: 'scene-ready contract' },
  { label: '正式 Intent', value: intentCount.value, hint: 'system.init 下发目录' },
]);
const accountRows = computed<DisplayRow[]>(() => {
  const user = payload.value.user;
  const role = asDict(payload.value.role_surface);
  const context = asDict(payload.value.record_context);
  return [
    { label: '账号', value: String(user?.login || '—') },
    { label: '用户', value: String(user?.name || '—') },
    { label: '角色', value: String(role.role_label || role.role_code || '—') },
    { label: '公司', value: String(user?.company_name || asDict(user?.company).name || context.company_name || '—') },
    { label: '项目', value: String(asDict(context.selected).name || asDict(context.selected).display_name || '—') },
    { label: '经营方式', value: String(context.operation_strategy || '—') },
  ];
});
const navigationRows = computed<DisplayRow[]>(() => {
  const navMeta = asDict(payload.value.nav_meta);
  return [
    { label: '菜单节点', value: String(navigationCount.value) },
    { label: '顶级入口', value: String(navigation.value.length) },
    { label: '默认路由', value: display(payload.value.default_route) },
    { label: '菜单版本', value: String(navMeta.version || navMeta.menu_version || navMeta.revision || '—') },
    { label: '来源', value: String(navMeta.source || navMeta.authority || 'system.init') },
  ];
});
const sceneRows = computed<DisplayRow[]>(() => [
  { label: '场景数量', value: String(sceneCount.value) },
  { label: '活动场景', value: String(sceneReady.value.active_scene_key || '—') },
  { label: '场景通道', value: String(sceneReady.value.scene_channel || '—') },
  {
    label: 'Contract 版本',
    value: String(sceneReady.value.contract_version || sceneReady.value.schema_version || '—'),
  },
  { label: '页面 Contract', value: String(pageContractCount.value) },
]);
const runtimeRows = computed<DisplayRow[]>(() => [
  { label: 'Trace ID', value: requestMeta.value.traceId || '—' },
  { label: '最后 Intent', value: requestMeta.value.intent || '—' },
  { label: 'HTTP 状态', value: requestMeta.value.status ? String(requestMeta.value.status) : '—' },
  { label: '完成时间', value: requestMeta.value.completedAt || '—' },
  { label: 'Contract 模式', value: String(payload.value.contract_mode || '—') },
  { label: '前端接口登记', value: `${apiCapabilityRegistry.length} 项` },
  { label: '后端目录交集', value: `${registeredIntentCount.value} 项` },
  { label: '后端未登记', value: `${unregisteredIntentCount.value} 项` },
]);
const metadataRows = computed(() => {
  const rows: Array<{ key: string; value: string }> = [];
  const sources: Dict = {
    version: payload.value.version,
    product_version: payload.value.product_version,
    source_revision: payload.value.source_revision,
    ...asDict(payload.value.init_meta),
  };
  Object.entries(sources).forEach(([key, value]) => rows.push({ key, value: display(value) }));
  return rows;
});
const metadataColumns = [
  { colKey: 'key', title: '字段', width: 240 },
  { colKey: 'value', title: '后端值', ellipsis: true },
];

function asDict(value: unknown): Dict {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Dict) : {};
}

function normalizeRows(value: unknown): Dict[] {
  return Array.isArray(value) ? value.filter((item): item is Dict => Boolean(item && typeof item === 'object')) : [];
}

function countCollection(value: unknown) {
  if (Array.isArray(value)) return value.length;
  return Object.keys(asDict(value)).length;
}

function countNavigation(nodes: Array<Record<string, unknown>>): number {
  return nodes.reduce(
    (total, node) => total + 1 + countNavigation((node.children as Array<Record<string, unknown>>) || []),
    0,
  );
}

function display(value: unknown) {
  if (value === null || value === undefined || value === '') return '—';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

async function load() {
  loading.value = true;
  error.value = '';
  try {
    [payload.value, intentCatalog.value] = await Promise.all([
      systemInit({ scene_ready_mode: 'full' }),
      fetchIntentCatalog(),
    ]);
    requestMeta.value = getLastRequestMeta();
  } catch (cause) {
    requestMeta.value = getLastRequestMeta();
    error.value = cause instanceof Error ? cause.message : '系统诊断加载失败';
  } finally {
    loading.value = false;
  }
}

async function copyTrace() {
  await navigator.clipboard.writeText(requestMeta.value.traceId);
  MessagePlugin.success('Trace ID 已复制');
}

onMounted(load);
</script>
<style scoped>
.workbench-page {
  display: grid;
  gap: 16px;
}
.page-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}
.page-heading span {
  color: var(--td-brand-color);
  font-size: 13px;
}
.page-heading h1,
.page-heading p {
  margin: 0;
}
.page-heading h1 {
  margin-top: 4px;
  font-size: 28px;
}
.page-heading p {
  margin-top: 8px;
  color: var(--td-text-color-secondary);
}
.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}
.summary-grid article {
  display: grid;
  gap: 6px;
  padding: 16px;
  border: 1px solid var(--td-border-level-1-color);
  border-radius: 8px;
  background: var(--td-bg-color-container);
}
.summary-grid span,
.summary-grid small {
  color: var(--td-text-color-secondary);
}
.summary-grid strong {
  font-size: 26px;
}
.diagnostic-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}
.panel {
  min-width: 0;
  padding: 18px;
  border: 1px solid var(--td-border-level-1-color);
  border-radius: 8px;
  background: var(--td-bg-color-container);
}
.panel > header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}
.panel h2 {
  margin: 0;
  font-size: 18px;
}
.panel header > span {
  color: var(--td-text-color-secondary);
}
.panel dl {
  display: grid;
  grid-template-columns: 120px minmax(0, 1fr);
  gap: 10px 16px;
  margin: 0;
}
.panel dt {
  color: var(--td-text-color-secondary);
}
.panel dd {
  min-width: 0;
  margin: 0;
  overflow-wrap: anywhere;
}
.panel--wide {
  overflow: hidden;
}
@media (width <= 900px) {
  .summary-grid,
  .diagnostic-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (width <= 640px) {
  .page-heading {
    flex-direction: column;
  }
  .summary-grid,
  .diagnostic-grid {
    grid-template-columns: 1fr;
  }
  .panel dl {
    grid-template-columns: 96px minmax(0, 1fr);
  }
}
</style>
