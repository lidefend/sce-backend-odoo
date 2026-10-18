<template>
  <section
    v-if="duties.length"
    class="platform-duty"
    data-semantic-component="PlatformDutyPanel"
    :data-platform-audience="audience"
  >
    <header class="platform-duty__header">
      <p class="platform-duty__eyebrow">平台管理职责</p>
      <h2 class="platform-duty__title">{{ audienceLabel }}</h2>
      <p class="platform-duty__meta">契约 {{ contractVersion }} · 来源 {{ source }}</p>
    </header>
    <ul class="platform-duty__grid">
      <li
        v-for="duty in duties"
        :key="duty.key"
        class="platform-duty__card"
        :data-duty-key="duty.key"
        :data-duty-state="duty.state || 'available'"
        :data-duty-action="actionOf(duty).kind"
      >
        <h3 class="platform-duty__card-title">{{ duty.label || duty.key }}</h3>
        <p class="platform-duty__capabilities">{{ (duty.capabilities || []).join(' · ') }}</p>
        <ScButton
          v-if="actionOf(duty).kind === 'navigate'"
          type="button"
          class="platform-duty__action"
          @click="open(duty)"
        >
          打开
        </ScButton>
        <ScButton
          v-else-if="actionOf(duty).kind === 'inline' && !isWriteAction(duty)"
          type="button"
          class="platform-duty__action"
          :disabled="inlineOf(duty.key).status === 'loading'"
          @click="loadInline(duty.key, actionOf(duty))"
        >
          {{ inlineActionLabel(duty.key) }}
        </ScButton>
        <span v-else-if="isWriteAction(duty)" class="platform-duty__pending">
          写操作入口，需专用表单，未启用
        </span>
        <span v-else-if="actionOf(duty).kind === 'intent'" class="platform-duty__pending">
          入口：{{ duty.intent }}
        </span>
        <span v-else class="platform-duty__pending">暂无入口</span>
      </li>
    </ul>

    <section
      v-if="tenantRegistry.visible"
      class="platform-duty__inline"
      data-semantic-component="PlatformTenantRegistry"
      :data-tenant-registry-status="tenantRegistry.status"
    >
      <header class="platform-duty__inline-header">
        <h3 class="platform-duty__inline-title">租户登记表</h3>
        <p class="platform-duty__inline-meta">
          来源 GET /api/ops/tenants · 共 {{ tenantRegistry.count }} 条
        </p>
      </header>
      <p v-if="tenantRegistry.status === 'loading'" class="platform-duty__pending">正在读取登记数据…</p>
      <p v-else-if="tenantRegistry.status === 'error'" class="platform-duty__error">
        读取失败：{{ tenantRegistry.message }}
        <ScButton type="button" class="platform-duty__action" @click="loadTenantRegistry">重试</ScButton>
      </p>
      <p v-else-if="!tenantRegistry.rows.length" class="platform-duty__empty" data-tenant-registry-empty="true">
        当前没有已登记的租户命名空间。租户需先完成平台登记与数据库注册，登记后会出现在此表。
      </p>
      <ScTable
        v-else
        class="platform-duty__table"
        data-tenant-registry-table="true"
        label="租户登记表"
        :data="tenantRegistry.rows"
        :columns="TENANT_COLUMNS"
        row-key="namespace_id"
        size="small"
      >
        <template #tenant_name="{ row }">{{ row.tenant_name || '-' }}</template>
        <template #lifecycle_state="{ row }">{{ row.lifecycle_state || '-' }}</template>
        <template #alias="{ row }">
          {{ row.alias || '-' }}<span v-if="row.path_prefix" class="platform-duty__muted">（{{ row.path_prefix }}）</span>
        </template>
        <template #billing_bound="{ row }">{{ row.billing_bound ? '已绑定' : '未绑定' }}</template>
      </ScTable>
    </section>

    <section
      v-if="generic.status !== 'idle'"
      class="platform-duty__inline"
      data-semantic-component="PlatformDutyInlineData"
      :data-inline-endpoint="generic.endpoint"
    >
      <header class="platform-duty__inline-header">
        <h3 class="platform-duty__inline-title">{{ generic.label }}</h3>
        <p class="platform-duty__inline-meta">来源 GET {{ generic.endpoint }}</p>
      </header>
      <p v-if="generic.status === 'loading'" class="platform-duty__pending">正在读取…</p>
      <p v-else-if="generic.status === 'error'" class="platform-duty__error">
        读取失败：{{ generic.message }}
      </p>
      <p v-else-if="generic.isEmpty" class="platform-duty__empty">该职责当前没有返回数据。</p>
      <pre v-else class="platform-duty__payload">{{ generic.payload }}</pre>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive } from 'vue';
import { useRouter } from 'vue-router';
import { apiRequest } from '../../api/client';
import { useSessionStore } from '../../stores/session';
import { resolveDutyAction, isWriteEndpoint, type DutyAction } from './dutyAction';
import ScButton from '../design-system/ScButton.vue';
import ScTable from '../design-system/ScTable.vue';

interface PlatformDutyEntry {
  key?: string;
  label?: string;
  capabilities?: string[];
  state?: string;
  route?: string | null;
  intent?: string | null;
  scene_key?: string;
}

interface TenantRegistryRow {
  namespace_id: string;
  tenant_name?: string | null;
  lifecycle_state?: string | null;
  alias?: string | null;
  path_prefix?: string | null;
  billing_bound?: boolean;
}

interface OpsTenantsResponse {
  ok?: boolean;
  data?: { tenants?: TenantRegistryRow[]; count?: number };
}

const TENANT_REGISTRY_ENDPOINT = '/api/ops/tenants';

const TENANT_COLUMNS = [
  { colKey: 'namespace_id', title: '命名空间' },
  { colKey: 'tenant_name', title: '租户名称' },
  { colKey: 'lifecycle_state', title: '生命周期' },
  { colKey: 'alias', title: '别名/路径前缀' },
  { colKey: 'billing_bound', title: '计费绑定' },
];

const router = useRouter();
const session = useSessionStore();

const surface = computed(() => session.user?.platform_duty);
const audience = computed(() => surface.value?.audience || 'none');
const duties = computed(() =>
  ((surface.value?.duties || []) as PlatformDutyEntry[]).filter((duty) => Boolean(duty?.key)),
);
const audienceLabel = computed(() => (audience.value === 'platform-admin' ? '平台控制台' : '租户配置'));
const contractVersion = computed(() => surface.value?.contract_version || '-');
const source = computed(() => surface.value?.source || '-');
const isPlatformAudience = computed(() => audience.value === 'platform-admin');

const inlineState = reactive<Record<string, { status: string; message?: string }>>({});
const tenantRegistry = reactive({
  visible: false,
  status: 'idle' as 'idle' | 'loading' | 'ready' | 'error',
  rows: [] as TenantRegistryRow[],
  count: 0,
  message: '',
});
const generic = reactive({
  endpoint: '',
  label: '',
  status: 'idle' as 'idle' | 'loading' | 'ready' | 'error',
  payload: '',
  isEmpty: false,
  message: '',
});

function actionOf(duty: PlatformDutyEntry): DutyAction {
  return resolveDutyAction(duty);
}

function isWriteAction(duty: PlatformDutyEntry) {
  const action = actionOf(duty);
  return action.kind === 'inline' && isWriteEndpoint(action.endpoint);
}

function inlineOf(key: string) {
  return inlineState[key] || { status: 'idle' };
}

function inlineActionLabel(key: string) {
  const status = inlineOf(key).status;
  if (status === 'loading') return '读取中…';
  if (status === 'error') return '重试';
  return '读取';
}

function open(duty: PlatformDutyEntry) {
  const action = actionOf(duty);
  if (action.kind !== 'navigate') return;
  void router.push(action.route);
}

async function loadTenantRegistry() {
  tenantRegistry.visible = true;
  tenantRegistry.status = 'loading';
  tenantRegistry.message = '';
  inlineState['platform.tenant_registry'] = { status: 'loading' };
  try {
    const payload = await apiRequest<OpsTenantsResponse>(TENANT_REGISTRY_ENDPOINT);
    const rows = payload?.data?.tenants ?? [];
    tenantRegistry.rows = Array.isArray(rows) ? rows : [];
    tenantRegistry.count = Number(payload?.data?.count ?? tenantRegistry.rows.length) || tenantRegistry.rows.length;
    tenantRegistry.status = 'ready';
    inlineState['platform.tenant_registry'] = { status: 'ready' };
  } catch (error) {
    tenantRegistry.rows = [];
    tenantRegistry.count = 0;
    tenantRegistry.status = 'error';
    tenantRegistry.message = error instanceof Error ? error.message : 'unknown error';
    inlineState['platform.tenant_registry'] = { status: 'error', message: tenantRegistry.message };
  }
}

async function loadGeneric(key: string, endpoint: string, label: string) {
  generic.endpoint = endpoint;
  generic.label = label;
  generic.status = 'loading';
  generic.message = '';
  inlineState[key] = { status: 'loading' };
  try {
    const payload = await apiRequest<Record<string, unknown>>(endpoint);
    generic.payload = JSON.stringify(payload, null, 2);
    generic.isEmpty = !payload || Object.keys(payload).length === 0;
    generic.status = 'ready';
    inlineState[key] = { status: 'ready' };
  } catch (error) {
    generic.payload = '';
    generic.isEmpty = false;
    generic.status = 'error';
    generic.message = error instanceof Error ? error.message : 'unknown error';
    inlineState[key] = { status: 'error', message: generic.message };
  }
}

function loadInline(key: string, action: DutyAction) {
  if (action.kind !== 'inline') return;
  const duty = duties.value.find((entry) => entry.key === key);
  const label = duty?.label || key;
  if (isWriteEndpoint(action.endpoint)) return;
  if (action.endpoint === TENANT_REGISTRY_ENDPOINT) {
    void loadTenantRegistry();
    return;
  }
  void loadGeneric(key, action.endpoint, label);
}

onMounted(() => {
  if (!isPlatformAudience.value) return;
  const registryDuty = duties.value.find((duty) => duty.key === 'platform.tenant_registry');
  const action = resolveDutyAction(registryDuty);
  if (action.kind === 'inline' && action.endpoint === TENANT_REGISTRY_ENDPOINT && !isWriteEndpoint(action.endpoint)) {
    void loadTenantRegistry();
  }
});
</script>

<style scoped>
.platform-duty {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1rem 0;
}
.platform-duty__header {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.platform-duty__eyebrow {
  margin: 0;
  font-size: 0.75rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  opacity: 0.7;
}
.platform-duty__title {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
}
.platform-duty__meta {
  margin: 0;
  font-size: 0.75rem;
  opacity: 0.65;
}
.platform-duty__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(16rem, 1fr));
  gap: 0.75rem;
  margin: 0;
  padding: 0;
  list-style: none;
}
.platform-duty__card {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.875rem 1rem;
  border: 1px solid rgba(15, 23, 42, 0.12);
  border-radius: 0.75rem;
  background: #ffffff;
}
.platform-duty__card[data-duty-state='available_unverified'] {
  border-style: dashed;
}
.platform-duty__card-title {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 600;
}
.platform-duty__capabilities {
  margin: 0;
  font-size: 0.75rem;
  opacity: 0.7;
  word-break: break-all;
}
.platform-duty__action {
  align-self: flex-start;
  padding: 0.35rem 0.9rem;
  border: 1px solid rgba(37, 99, 235, 0.4);
  border-radius: 0.5rem;
  background: rgba(37, 99, 235, 0.08);
  color: #1d4ed8;
  font-size: 0.8rem;
  cursor: pointer;
}
.platform-duty__action:disabled {
  opacity: 0.6;
  cursor: progress;
}
.platform-duty__pending {
  font-size: 0.75rem;
  color: #64748b;
}
.platform-duty__inline {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.875rem 1rem;
  border: 1px solid rgba(15, 23, 42, 0.12);
  border-radius: 0.75rem;
  background: #ffffff;
}
.platform-duty__inline-header {
  display: flex;
  align-items: baseline;
  gap: 0.75rem;
}
.platform-duty__inline-title {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 600;
}
.platform-duty__inline-meta {
  margin: 0;
  font-size: 0.75rem;
  opacity: 0.65;
}
.platform-duty__table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8rem;
}
.platform-duty__table th,
.platform-duty__table td {
  padding: 0.4rem 0.6rem;
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
  text-align: left;
}
.platform-duty__table th {
  font-weight: 600;
  color: #475569;
}
.platform-duty__muted {
  opacity: 0.65;
}
.platform-duty__empty,
.platform-duty__error {
  margin: 0;
  font-size: 0.8rem;
  color: #64748b;
}
.platform-duty__error {
  color: #b91c1c;
}
.platform-duty__payload {
  margin: 0;
  max-height: 18rem;
  overflow: auto;
  font-size: 0.75rem;
  background: #f8fafc;
  padding: 0.5rem;
  border-radius: 0.5rem;
}
</style>
