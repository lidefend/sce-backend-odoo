<template>
  <div class="operations-page">
    <div class="page-heading"><div><p class="eyebrow">场景治理</p><h1>场景包管理</h1><p>读取后端已注册的场景包与版本，并执行受控导入导出。</p></div><t-button variant="outline" :loading="loading" @click="load">刷新</t-button></div>
    <t-alert v-if="error" theme="error" :message="error" close @close="error = ''" />
    <t-card :bordered="false" class="panel"><t-table v-if="rows.length" :data="rows" :columns="columns" row-key="key"><template #operation="{ row }"><t-space size="small"><t-button size="small" variant="text" :loading="busy === `export:${itemKey(row)}`" @click="exportPackage(row)">导出</t-button><t-button size="small" variant="text" theme="primary" @click="openImport(row)">导入</t-button></t-space></template></t-table><t-empty v-else-if="!loading" description="暂无场景包记录" /></t-card>
    <t-dialog v-model:visible="importDialog" header="导入场景包" :confirm-btn="{ content: '检查并导入', theme: 'primary', loading: busy === 'import' }" @confirm="importPackage"><t-alert theme="warning" message="导入会按照后端策略处理冲突，请先确认来源和原因。" /><t-textarea v-model="packageText" :autosize="{ minRows: 8, maxRows: 16 }" placeholder="粘贴场景包 JSON" /><t-input v-model="reason" placeholder="填写导入原因" style="margin-top: 12px" /><t-select v-model="strategy" :options="strategies" style="margin-top: 12px" /></t-dialog>
  </div>
</template>
<script setup lang="ts">
import { MessagePlugin } from 'tdesign-vue-next';
import { computed, onMounted, ref } from 'vue';
import { dryRunScenePackageImport, exportScenePackage, importScenePackage, scenePackageList } from '@/api/odoo';
type Row = Record<string, any>;
const loading = ref(false); const error = ref(''); const payload = ref<Row>({}); const busy = ref(''); const importDialog = ref(false); const packageText = ref(''); const reason = ref(''); const strategy = ref('skip_existing'); const selectedRow = ref<Row | null>(null);
const strategies = [{ value: 'skip_existing', label: '跳过已存在' }, { value: 'override_existing', label: '覆盖已存在' }, { value: 'rename_on_conflict', label: '冲突时重命名' }];
const rows = computed<Row[]>(() => { const values = payload.value.packages || payload.value.items; return Array.isArray(values) ? values : []; });
const columns = [{ colKey: 'name', title: '名称' }, { colKey: 'version', title: '版本' }, { colKey: 'status', title: '状态' }, { colKey: 'scene_channel', title: '通道' }, { colKey: 'operation', title: '操作', width: 160 }];
function itemKey(row: Row) { return String(row.package_name || row.name || row.key || row.id || 'package'); }
async function load() { loading.value = true; error.value = ''; try { payload.value = await scenePackageList(); } catch (cause) { error.value = cause instanceof Error ? cause.message : '场景包加载失败'; } finally { loading.value = false; } }
async function exportPackage(row: Row) { const key = itemKey(row); busy.value = `export:${key}`; try { const result = await exportScenePackage({ packageName: String(row.package_name || row.name || key), packageVersion: String(row.version || row.package_version || ''), channel: String(row.scene_channel || row.channel || 'stable'), reason: '前端场景包导出' }); const content = result.content_b64 ? atob(String(result.content_b64)) : JSON.stringify(result.package || result, null, 2); const blob = new Blob([content], { type: 'application/json' }); const url = URL.createObjectURL(blob); const link = document.createElement('a'); link.href = url; link.download = `${key}.json`; link.click(); URL.revokeObjectURL(url); MessagePlugin.success('场景包已导出'); } catch (cause) { error.value = cause instanceof Error ? cause.message : '场景包导出失败'; } finally { busy.value = ''; } }
function openImport(row: Row) { selectedRow.value = row; packageText.value = ''; reason.value = ''; importDialog.value = true; }
async function importPackage() { if (!packageText.value.trim() || !reason.value.trim()) { MessagePlugin.warning('请填写场景包 JSON 和导入原因'); return; } busy.value = 'import'; try { const parsed = JSON.parse(packageText.value); await dryRunScenePackageImport(parsed); await importScenePackage({ packagePayload: parsed, strategy: strategy.value, reason: reason.value.trim() }); MessagePlugin.success('场景包导入已提交'); importDialog.value = false; await load(); } catch (cause) { error.value = cause instanceof Error ? cause.message : '场景包导入失败'; } finally { busy.value = ''; } }
onMounted(load);
</script>
<style scoped>
.operations-page { display: grid; gap: 16px; }.page-heading { display: flex; justify-content: space-between; gap: 16px; }.page-heading h1 { margin: 4px 0 8px; font-size: 28px; }.page-heading p { margin: 0; color: var(--td-text-color-secondary); }.eyebrow { color: var(--td-brand-color) !important; font-size: 13px; }.panel { border: 1px solid var(--td-border-level-1-color); }
</style>
