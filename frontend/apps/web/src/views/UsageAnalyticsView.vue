<template>
  <section class="usage-analytics">
    <header v-if="pageSectionEnabled('header', true) && pageSectionTagIs('header', 'header')" class="header" :style="pageSectionStyle('header')">
      <div>
        <h2>{{ pageText('title', 'Usage Analytics') }}</h2>
        <p>{{ pageText('subtitle', 'Scene / Capability 使用统计（按公司累计）。') }}</p>
      </div>
      <div class="actions">
        <label>
          {{ pageText('label_top', 'Top') }}
          <ScSelect v-model="topN" :disabled="loading" :options="topOptions" />
        </label>
        <label>
          {{ pageText('label_daily_range', '趋势范围') }}
          <ScSelect v-model="dailyRange" :disabled="loading" :options="dailyRangeOptions" />
        </label>
        <label>
          {{ pageText('label_hidden_reason', '隐藏原因') }}
          <ScSelect v-model="hiddenReasonFilter" :disabled="loading" :options="hiddenReasonOptions" />
        </label>
        <label>
          {{ pageText('label_role_slice', '角色切片') }}
          <ScSelect v-model="roleSlice" :disabled="loading" :options="roleSliceOptions" />
        </label>
        <label>
          {{ pageText('label_user_slice', '用户切片') }}
          <ScInput
            v-model.number="userSlice"
            type="number"
            min="0"
            step="1"
            :placeholder="pageText('placeholder_user_slice', '0=全部')"
            :disabled="loading"
          />
        </label>
        <label>
          {{ pageText('label_scene_prefix', 'Scene 前缀') }}
          <ScInput
            v-model.trim="scenePrefix"
            type="text"
            :placeholder="pageText('placeholder_scene_prefix', '如 workspace.')"
            :disabled="loading"
          />
        </label>
        <label>
          {{ pageText('label_capability_prefix', 'Capability 前缀') }}
          <ScInput
            v-model.trim="capabilityPrefix"
            type="text"
            :placeholder="pageText('placeholder_capability_prefix', '如 contract.')"
            :disabled="loading"
          />
        </label>
        <label class="export-scope">
          <ScCheckbox v-model:checked="exportFilteredOnly">
            {{ pageText('label_export_filtered_only', '仅导出当前筛选') }}
          </ScCheckbox>
        </label>
        <ScButton class="secondary" :disabled="loading" @click="copyExportParams">{{ pageText('action_copy_export_params', '复制导出参数') }}</ScButton>
        <ScButton class="secondary" :disabled="loading" @click="resetFilters">{{ pageText('action_reset_filters', '重置筛选') }}</ScButton>
        <ScButton class="secondary" :disabled="loading || !canExport" @click="exportCsv">{{ pageText('action_export_csv', '导出 CSV') }}</ScButton>
        <ScButton
          v-for="action in headerActions"
          :key="action.key"
          class="secondary"
          :disabled="loading"
          @click="executeHeaderAction(action.key)"
        >
          {{ action.label }}
        </ScButton>
      </div>
    </header>

    <StatusPanel
      v-if="pageSectionEnabled('status_loading', true) && pageSectionTagIs('status_loading', 'section') && loading"
      :title="pageText('loading_title', 'Loading usage report...')"
      variant="info"
      :style="pageSectionStyle('status_loading')"
    />
    <StatusPanel
      v-else-if="pageSectionEnabled('status_error', true) && pageSectionTagIs('status_error', 'section') && errorText"
      :title="errorCopy.title"
      :message="errorCopy.message"
      :trace-id="statusError?.traceId || errorTraceId || undefined"
      :error-code="statusError?.code"
      :reason-code="statusError?.reasonCode"
      :error-category="statusError?.errorCategory"
      :error-details="statusError?.details"
      :retryable="statusError?.retryable"
      :hint="errorCopy.hint"
      :suggested-action="statusError?.suggestedAction"
      variant="error"
      :on-retry="load"
      :style="pageSectionStyle('status_error')"
    />

    <template v-else>
      <section v-if="pageSectionEnabled('slice_bar', true) && pageSectionTagIs('slice_bar', 'section')" class="slice-bar" :style="pageSectionStyle('slice_bar')">
        <span>{{ pageText('slice_window_prefix', '窗口：') }}{{ report?.filters?.day_from || '-' }} ~ {{ report?.filters?.day_to || '-' }}</span>
        <span>{{ pageText('slice_role_prefix', '角色：') }}{{ report?.filters?.role_code || pageText('option_all', '全部') }}</span>
        <span>{{ pageText('slice_user_prefix', '用户：') }}{{ report?.filters?.user_id || 0 }}</span>
        <span>{{ pageText('slice_scene_prefix_label', 'Scene 前缀：') }}{{ report?.filters?.scene_key_prefix || '-' }}</span>
        <span>{{ pageText('slice_capability_prefix_label', 'Capability 前缀：') }}{{ report?.filters?.capability_key_prefix || '-' }}</span>
      </section>

      <section v-if="pageSectionEnabled('summary_usage', true) && pageSectionTagIs('summary_usage', 'section')" class="summary-grid" :style="pageSectionStyle('summary_usage')">
        <ScCard class="summary-card" appearance="metric">
          <p class="label">{{ pageText('summary_scene_open_total', 'Scene Open Total') }}</p>
          <p class="count">{{ report?.totals.scene_open_total ?? 0 }}</p>
        </ScCard>
        <ScCard class="summary-card" appearance="metric">
          <p class="label">{{ pageText('summary_capability_open_total', 'Capability Open Total') }}</p>
          <p class="count">{{ report?.totals.capability_open_total ?? 0 }}</p>
        </ScCard>
        <ScCard class="summary-card" appearance="metric">
          <p class="label">{{ pageText('summary_generated_at', 'Generated At') }}</p>
          <p class="count small">{{ report?.generated_at || '-' }}</p>
        </ScCard>
      </section>

      <section v-if="pageSectionEnabled('summary_visibility', true) && pageSectionTagIs('summary_visibility', 'section')" class="summary-grid" :style="pageSectionStyle('summary_visibility')">
        <ScCard class="summary-card" appearance="metric">
          <p class="label">{{ pageText('summary_capability_total', 'Capability Total') }}</p>
          <p class="count">{{ visibility?.summary.total ?? 0 }}</p>
        </ScCard>
        <ScCard class="summary-card" appearance="metric">
          <p class="label">{{ pageText('summary_visible_hidden', 'Visible / Hidden') }}</p>
          <p class="count small">{{ visibility?.summary.visible ?? 0 }} / {{ visibility?.summary.hidden ?? 0 }}</p>
        </ScCard>
        <ScCard class="summary-card" appearance="metric">
          <p class="label">{{ pageText('summary_ready_preview_locked', 'Ready / Preview / Locked') }}</p>
          <p class="count small">
            {{ visibility?.summary.ready ?? 0 }} / {{ visibility?.summary.preview ?? 0 }} / {{ visibility?.summary.locked ?? 0 }}
          </p>
        </ScCard>
        <ScCard class="summary-card" appearance="metric">
          <p class="label">{{ pageText('summary_role_codes', 'Role Codes') }}</p>
          <p class="count small">{{ (visibility?.role_codes || []).join(', ') || '-' }}</p>
        </ScCard>
      </section>

      <section v-if="pageSectionEnabled('tables_top', true) && pageSectionTagIs('tables_top', 'section')" class="tables" :style="pageSectionStyle('tables_top')">
        <ScCard class="table-card" appearance="table" :title="pageText('table_top_scenes', 'Top Scenes')">
          <ScTable class="usage-table" :label="pageText('table_top_scenes', 'Top Scenes')" :data="sceneTop" row-key="key"
            :columns="usageColumns([['key', pageText('table_scene_key', 'Scene Key')], ['count', pageText('table_count', 'Count')]])" size="small" />
        </ScCard>

        <ScCard class="table-card" appearance="table" :title="pageText('table_top_capabilities', 'Top Capabilities')">
          <ScTable class="usage-table" :label="pageText('table_top_capabilities', 'Top Capabilities')" :data="capabilityTop" row-key="key"
            :columns="usageColumns([['key', pageText('table_capability_key', 'Capability Key')], ['count', pageText('table_count', 'Count')]])" size="small" />
        </ScCard>
      </section>

      <section v-if="pageSectionEnabled('tables_daily', true) && pageSectionTagIs('tables_daily', 'section')" class="tables" :style="pageSectionStyle('tables_daily')">
        <ScCard class="table-card" appearance="table" :title="pageText('table_scene_open_last_7_days', 'Scene Open (Last 7 Days)')">
          <ScTable class="usage-table" :label="pageText('table_scene_open_last_7_days', 'Scene Open (Last 7 Days)')" :data="sceneDaily" row-key="day"
            :columns="usageColumns([['day', pageText('table_date', 'Date')], ['count', pageText('table_count', 'Count')]])" size="small" />
        </ScCard>

        <ScCard class="table-card" appearance="table" :title="pageText('table_capability_open_last_7_days', 'Capability Open (Last 7 Days)')">
          <ScTable class="usage-table" :label="pageText('table_capability_open_last_7_days', 'Capability Open (Last 7 Days)')" :data="capabilityDaily" row-key="day"
            :columns="usageColumns([['day', pageText('table_date', 'Date')], ['count', pageText('table_count', 'Count')]])" size="small" />
        </ScCard>
      </section>

      <section v-if="pageSectionEnabled('tables_visibility', true) && pageSectionTagIs('tables_visibility', 'section')" class="tables" :style="pageSectionStyle('tables_visibility')">
        <ScCard class="table-card" appearance="table" :title="pageText('table_visibility_reason_counts', 'Visibility Reason Counts')">
          <ScTable class="usage-table" :label="pageText('table_visibility_reason_counts', 'Visibility Reason Counts')" :data="reasonCounts" row-key="reason_code"
            :columns="usageColumns([['reason_code', pageText('table_reason_code', 'Reason Code')], ['count', pageText('table_count', 'Count')]])" size="small" />
        </ScCard>

        <ScCard class="table-card" appearance="table" :title="pageText('table_hidden_capability_samples', 'Hidden Capability Samples')">
          <ScTable class="usage-table" :label="pageText('table_hidden_capability_samples', 'Hidden Capability Samples')" :data="hiddenSampleRows" row-key="key"
            :columns="usageColumns([['key', pageText('table_key', 'Key')], ['reasonLabel', pageText('table_reason', 'Reason')]])" size="small" />
        </ScCard>
      </section>

      <section v-if="pageSectionEnabled('tables_role_user', true) && pageSectionTagIs('tables_role_user', 'section')" class="tables" :style="pageSectionStyle('tables_role_user')">
        <ScCard class="table-card" appearance="table" :title="pageText('table_role_top', 'Role Top')">
          <ScTable class="usage-table" :label="pageText('table_role_top', 'Role Top')" :data="roleTop" row-key="role_code"
            :columns="usageColumns([['role_code', pageText('table_role_code', 'Role Code')], ['scene_open_total', pageText('table_scene', 'Scene')], ['capability_open_total', pageText('table_capability', 'Capability')], ['combined_total', pageText('table_total', 'Total')]])" size="small" />
        </ScCard>

        <ScCard class="table-card" appearance="table" :title="pageText('table_user_top', 'User Top')">
          <ScTable class="usage-table" :label="pageText('table_user_top', 'User Top')" :data="userTop" row-key="user_id"
            :columns="usageColumns([['user_id', pageText('table_user_id', 'User ID')], ['scene_open_total', pageText('table_scene', 'Scene')], ['capability_open_total', pageText('table_capability', 'Capability')], ['combined_total', pageText('table_total', 'Total')]])" size="small" />
        </ScCard>
      </section>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { exportUsageCsv, fetchCapabilityVisibilityReport, fetchUsageReport, type CapabilityVisibilityReport, type UsageReport } from '../api/usage';
import StatusPanel from '../components/StatusPanel.vue';
import ScCard from '../components/design-system/ScCard.vue';
import ScButton from '../components/design-system/ScButton.vue';
import ScCheckbox from '../components/design-system/ScCheckbox.vue';
import ScInput from '../components/design-system/ScInput.vue';
import ScSelect from '../components/design-system/ScSelect.vue';
import ScTable from '../components/design-system/ScTable.vue';
import { buildStatusError, resolveErrorCopy, type StatusError } from '../composables/useStatus';
import { collectErrorContextIssue, issueScopeLabel } from '../app/errorContext';
import { usePageContract } from '../app/pageContract';
import { executePageContractAction } from '../app/pageContractActionRuntime';

const loading = ref(false);
const errorText = ref('');
const errorTraceId = ref('');
const statusError = ref<StatusError | null>(null);
const topN = ref(10);
const dailyRange = ref(7);
const hiddenReasonFilter = ref('ALL');
const roleSlice = ref('');
const userSlice = ref(0);
const scenePrefix = ref('');
const capabilityPrefix = ref('');
const exportFilteredOnly = ref(true);
const report = ref<UsageReport | null>(null);
const visibility = ref<CapabilityVisibilityReport | null>(null);
const router = useRouter();
const pageContract = usePageContract('usage_analytics');
const pageText = pageContract.text;
const pageActionIntent = pageContract.actionIntent;
const pageActionTarget = pageContract.actionTarget;
const pageGlobalActions = pageContract.globalActions;
const pageSectionEnabled = pageContract.sectionEnabled;
const pageSectionStyle = pageContract.sectionStyle;
const pageSectionTagIs = pageContract.sectionTagIs;

const sceneTop = computed(() => report.value?.scene_top || []);
const capabilityTop = computed(() => report.value?.capability_top || []);
const roleTop = computed(() => report.value?.role_top || []);
const userTop = computed(() => report.value?.user_top || []);
const sceneDaily = computed(() => report.value?.daily?.scene_open || []);
const capabilityDaily = computed(() => report.value?.daily?.capability_open || []);
const reasonCounts = computed(() => visibility.value?.reason_counts || []);
const roleCodeOptions = computed(() => visibility.value?.role_codes || []);
const topOptions = [5, 10, 20].map((value) => ({ value, label: String(value) }));
const dailyRangeOptions = computed(() => [
  { value: 3, label: pageText('option_recent_3_days', '最近 3 天') },
  { value: 7, label: pageText('option_recent_7_days', '最近 7 天') },
]);
const hiddenReasonOptions = computed(() => [
  { value: 'ALL', label: pageText('option_all', '全部') },
  ...reasonCounts.value.map((item) => ({ value: item.reason_code, label: `${item.reason_code} (${item.count})` })),
]);
const roleSliceOptions = computed(() => [
  { value: '', label: pageText('option_all_roles', '全部角色') },
  ...roleCodeOptions.value.map((code) => ({ value: code, label: code })),
]);
const hiddenSamples = computed(() => visibility.value?.hidden_samples || []);
const filteredHiddenSamples = computed(() => {
  if (hiddenReasonFilter.value === 'ALL') return hiddenSamples.value;
  return hiddenSamples.value.filter((item) => String(item.reason_code || '') === hiddenReasonFilter.value);
});
const hiddenSampleRows = computed(() => filteredHiddenSamples.value.map((item) => ({
  ...item,
  reasonLabel: item.reason_code || item.reason || '-',
})));
const canExport = computed(() => Boolean(report.value || visibility.value));
const errorCopy = computed(() => resolveErrorCopy(statusError.value, errorText.value || pageText('error_fallback', 'Failed to load usage report')));
const headerActions = computed(() => pageGlobalActions.value);

function usageColumns(entries: Array<[string, string]>) {
  return entries.map(([colKey, title]) => ({ colKey, title }));
}

function resolveContextAwareErrorText(err: unknown, fallback: string) {
  const counter = new Map<string, { model: string; op: string; reasonCode: string; count: number }>();
  const issue = collectErrorContextIssue(counter, err, {});
  const scope = issueScopeLabel(issue);
  if (!scope && issue.reasonCode === 'UNKNOWN') return fallback;
  return `${fallback} (${scope || 'unknown'} / ${issue.reasonCode})`;
}

async function exportCsv() {
  if (!canExport.value) return;
  try {
    const data = await exportUsageCsv({
      top: topN.value,
      days: dailyRange.value,
      hidden_reason: hiddenReasonFilter.value,
      export_filtered_only: exportFilteredOnly.value,
      role_code: roleSlice.value || '',
      user_id: Math.max(0, Number(userSlice.value || 0)),
      scene_key_prefix: scenePrefix.value || '',
      capability_key_prefix: capabilityPrefix.value || '',
    });
    const blob = new Blob([data.content || ''], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = data.filename || `usage-analytics-${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  } catch (err) {
    errorText.value = resolveContextAwareErrorText(err, err instanceof Error ? err.message : pageText('error_export_failed', '导出失败'));
    statusError.value = buildStatusError(err, errorText.value);
    errorTraceId.value = statusError.value.traceId || '';
  }
}

async function copyExportParams() {
  const payload = {
    top: topN.value,
    days: dailyRange.value,
    hidden_reason: hiddenReasonFilter.value,
    export_filtered_only: exportFilteredOnly.value,
    role_code: roleSlice.value || '',
    user_id: Math.max(0, Number(userSlice.value || 0)),
    scene_key_prefix: scenePrefix.value || '',
    capability_key_prefix: capabilityPrefix.value || '',
  };
  try {
    await navigator.clipboard.writeText(JSON.stringify(payload, null, 2));
  } catch {
    errorText.value = pageText('error_copy_export_params_failed', '复制导出参数失败');
  }
}

function resetFilters() {
  dailyRange.value = 7;
  hiddenReasonFilter.value = 'ALL';
  roleSlice.value = '';
  userSlice.value = 0;
  scenePrefix.value = '';
  capabilityPrefix.value = '';
  exportFilteredOnly.value = true;
  if (topN.value !== 10) {
    topN.value = 10;
    return;
  }
  void load();
}

async function load() {
  loading.value = true;
  errorText.value = '';
  errorTraceId.value = '';
  statusError.value = null;
  try {
    const [usage, vis] = await Promise.all([
      fetchUsageReport(
        topN.value,
        dailyRange.value,
        roleSlice.value || '',
        Math.max(0, Number(userSlice.value || 0)),
        scenePrefix.value || '',
        capabilityPrefix.value || '',
      ),
      fetchCapabilityVisibilityReport(),
    ]);
    report.value = usage;
    visibility.value = vis;
  } catch (err) {
    errorText.value = resolveContextAwareErrorText(
      err,
      err instanceof Error ? err.message : pageText('error_fallback', 'Failed to load usage report'),
    );
    statusError.value = buildStatusError(err, errorText.value);
    errorTraceId.value = statusError.value.traceId || '';
  } finally {
    loading.value = false;
  }
}

async function executeHeaderAction(actionKey: string) {
  const handled = await executePageContractAction({
    actionKey,
    router,
    actionIntent: pageActionIntent,
    actionTarget: pageActionTarget,
    onRefresh: load,
    onFallback: async (key) => {
      if (key === 'refresh_page') {
        await load();
        return true;
      }
      return false;
    },
  });
  if (!handled && actionKey === 'refresh_page') {
    await load();
  }
}

watch([topN, dailyRange, roleSlice, userSlice, scenePrefix, capabilityPrefix], () => {
  load();
});

onMounted(load);
</script>

<style scoped>
.usage-analytics {
  display: grid;
  gap: 16px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.actions {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.slice-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  color: var(--sc-app-text-secondary);
  font-size: 13px;
}

.slice-bar span {
  border: 1px solid var(--sc-app-border);
  border-radius: 999px;
  padding: 4px 10px;
  background: var(--sc-app-panel);
}

.export-scope {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--sc-app-text-secondary);
}

.secondary {
  border: 1px solid var(--sc-app-info-border);
  border-radius: var(--sc-component-button-radius);
  background: var(--sc-app-info-bg);
  color: var(--sc-app-info-text);
  padding: 8px 10px;
  cursor: pointer;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 10px;
}

.summary-card {
  min-width: 0;
}

.summary-card .label {
  margin: 0;
  color: var(--sc-semantic-text-muted);
}

.summary-card .count {
  margin: 8px 0 0;
  font-size: 24px;
  font-weight: 700;
  color: var(--sc-app-text-primary);
}

.summary-card .count.small {
  font-size: 14px;
}

.tables {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 12px;
}

.table-card {
  overflow: hidden;
}

.usage-table :deep(table) {
  width: 100%;
}

.usage-table :deep(th),
.usage-table :deep(td) {
  padding: 10px 12px;
  border-bottom: 1px solid var(--sc-app-border);
  text-align: left;
}

.empty {
  text-align: center;
  color: var(--sc-semantic-text-muted);
}
</style>
