<template>
  <div class="operations-page">
    <div class="page-heading"><div><p class="eyebrow">场景治理</p><h1>场景健康</h1><p>读取后端场景校验、运行状态和诊断结果。</p></div><t-button variant="outline" :loading="loading" @click="load"><template #icon><t-icon name="refresh" /></template>刷新</t-button></div>
    <t-alert v-if="error" theme="error" :message="error" close @close="error = ''" />
    <section class="summary-grid"><t-card v-for="item in summaryItems" :key="item.label" bordered><span>{{ item.label }}</span><strong>{{ item.value }}</strong></t-card></section>
    <t-card :bordered="false" class="panel"><template #title>场景治理操作</template><div class="governance-form"><t-select v-model="channel" :options="channels" style="width: 140px" /><t-input v-model="reason" clearable placeholder="填写操作原因" /><t-space><t-button :disabled="!reason.trim()" :loading="busy === 'channel'" @click="setChannel">切换通道</t-button><t-button :disabled="!reason.trim()" :loading="busy === 'pin'" @click="pinStable">固定稳定版</t-button><t-button theme="danger" variant="outline" :disabled="!reason.trim()" :loading="busy === 'rollback'" @click="rollback">回滚</t-button><t-button variant="outline" :disabled="!reason.trim()" :loading="busy === 'export'" @click="exportContract">导出契约</t-button></t-space></div><p class="hint">操作权限和结果均由后端控制；无权限时会显示后端返回的错误。</p></t-card>
    <t-card :bordered="false" class="panel"><template #title>健康检查结果</template><t-table v-if="rows.length" :data="rows" :columns="columns" row-key="key" /><t-empty v-else-if="!loading" description="暂无场景健康数据" /></t-card>
  </div>
</template>
<script setup lang="ts">
import { MessagePlugin } from 'tdesign-vue-next';
import { computed, onMounted, ref } from 'vue';
import { exportSceneContract, fetchSceneHealth, pinStableSceneGovernance, rollbackSceneGovernance, setSceneChannel } from '@/api/odoo';
type Row = Record<string, any>;
const loading = ref(false); const error = ref(''); const payload = ref<Row>({}); const busy = ref(''); const reason = ref(''); const channel = ref('stable');
const channels = ['draft', 'preview', 'stable'].map((value) => ({ value, label: value }));
const rows = computed<Row[]>(() => { const values = payload.value.items || payload.value.scenes || payload.value.checks || payload.value.rows; return Array.isArray(values) ? values.map((row: Row) => ({ ...row, label: row.label || row.name || row.key || row.scene_key || '—', status: row.status || row.state || row.level || '—', message: row.message || row.reason || row.description || '—' })) : []; });
const columns = [{ colKey: 'label', title: '项目', minWidth: 160 }, { colKey: 'status', title: '状态', minWidth: 110 }, { colKey: 'message', title: '说明', minWidth: 240 }] as any;
const summaryItems = computed(() => { const summary = payload.value.summary || payload.value.counts || {}; return [{ label: '检查状态', value: String(payload.value.status || summary.status || '—') }, { label: '场景数量', value: String(summary.total || payload.value.total || rows.value.length) }, { label: '异常数量', value: String(summary.failed || summary.error || summary.blocked || 0) }, { label: '当前通道', value: String(payload.value.channel || payload.value.scene_channel || channel.value) }]; });
async function load() { loading.value = true; error.value = ''; try { payload.value = await fetchSceneHealth(); } catch (cause) { error.value = cause instanceof Error ? cause.message : '场景健康加载失败'; } finally { loading.value = false; } }
async function run(key: string, action: () => Promise<Row>) { busy.value = key; try { await action(); MessagePlugin.success('治理操作已提交'); await load(); } catch (cause) { error.value = cause instanceof Error ? cause.message : '治理操作失败'; } finally { busy.value = ''; } }
function setChannel() { void run('channel', () => setSceneChannel({ channel: channel.value, reason: reason.value.trim() })); }
function pinStable() { void run('pin', () => pinStableSceneGovernance(reason.value.trim())); }
function rollback() { void run('rollback', () => rollbackSceneGovernance(reason.value.trim())); }
function exportContract() { void run('export', () => exportSceneContract({ channel: channel.value, reason: reason.value.trim() })); }
onMounted(load);
</script>
<style scoped>
.operations-page { display: grid; gap: 16px; }.page-heading { display: flex; justify-content: space-between; gap: 16px; }.page-heading h1 { margin: 4px 0 8px; font-size: 28px; }.page-heading p, .hint { margin: 0; color: var(--td-text-color-secondary); }.eyebrow { color: var(--td-brand-color) !important; font-size: 13px; }.summary-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }.summary-grid span { display: block; color: var(--td-text-color-secondary); font-size: 12px; }.summary-grid strong { display: block; margin-top: 8px; font-size: 20px; }.panel { border: 1px solid var(--td-border-level-1-color); }.governance-form { display: flex; align-items: center; flex-wrap: wrap; gap: 10px; }.governance-form :deep(.t-input) { width: min(360px, 100%); }.hint { margin-top: 10px; font-size: 12px; }@media (max-width: 720px) { .page-heading { flex-direction: column; }.summary-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
</style>
