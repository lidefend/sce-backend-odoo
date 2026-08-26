<template>
  <ScPage content-layout="record-grid" class="api-key-page" data-semantic-component="ApiKeyManagementView" :data-state="loading ? 'loading' : credentials.length ? 'ready' : 'empty'" :aria-busy="loading || undefined">
    <ScPageHeader
      eyebrow="集成与开发者"
      title="API Key 管理"
      subtitle="为机器集成创建受限凭据。API Key 不会获得超出当前用户、公司和模型权限的能力。"
    >
      <template #actions>
        <ScButton variant="primary" @click="openCreate">创建 API Key</ScButton>
      </template>
    </ScPageHeader>

    <p v-if="errorMessage" class="credential-alert credential-alert--error" role="alert">{{ errorMessage }}</p>

    <ScPanel tone="subtle" class="credential-guidance">
      <strong>安全边界</strong>
      <span>Key 仅在创建或轮换后显示一次；这里只展示 Key ID、范围和使用记录。</span>
      <span>浏览器不会保存 Key，也不会用 Key 替代普通账号登录。</span>
    </ScPanel>

    <ScSection title="机器凭据" description="撤销后，已签发的关联机器会话会立即失效。">
      <template #actions>
        <ScButton variant="ghost" :loading="loading" @click="loadCredentials">刷新</ScButton>
      </template>

      <p v-if="loading && !credentials.length" class="credential-loading" role="status">正在读取凭据...</p>
      <ScEmptyState
        v-else-if="!credentials.length"
        title="尚未创建 API Key"
        description="按集成用途分别创建，使用最小范围，并设置合理的过期时间。"
      >
        <template #actions>
          <ScButton variant="primary" @click="openCreate">创建第一个 API Key</ScButton>
        </template>
      </ScEmptyState>

      <div v-else class="credential-list" data-auth-credential-list>
        <article v-for="item in credentials" :key="item.credential_id" class="credential-card">
          <header>
            <div>
              <h3>{{ item.name }}</h3>
              <code>{{ item.credential_id }}</code>
            </div>
            <ScStatusBadge
              :value="item.state"
              :label="stateLabel(item.state)"
              :semantic="stateSemantic(item.state)"
            />
          </header>
          <dl>
            <div><dt>权限范围</dt><dd>{{ scopeLabel(item.scope) }}</dd></div>
            <div><dt>公司范围</dt><dd>{{ companyLabel(item.company_ids) }}</dd></div>
            <div><dt>到期时间</dt><dd>{{ dateTimeLabel(item.expires_at) || '长期有效，建议设置到期时间' }}</dd></div>
            <div><dt>最后使用</dt><dd>{{ dateTimeLabel(item.last_used_at) || '尚未使用' }}</dd></div>
            <div><dt>使用次数</dt><dd>{{ item.usage_count }}</dd></div>
            <div><dt>创建时间</dt><dd>{{ dateTimeLabel(item.created_at) || '—' }}</dd></div>
          </dl>
          <div v-if="item.state === 'active'" class="sc-action-group">
            <ScButton variant="secondary" @click="openRotate(item)">轮换</ScButton>
            <ScButton variant="danger" :loading="busyCredentialId === item.credential_id" @click="revoke(item)">撤销</ScButton>
          </div>
        </article>
      </div>
    </ScSection>

    <ScDialog :open="createOpen" title="创建机器 API Key" @close="closeCreate">
      <form id="create-api-key-form" class="sc-form credential-form" autocomplete="off" @submit.prevent="createCredential">
        <label class="sc-form-label">
          用途名称
          <ScInput v-model="createForm.name" :max-length="120" required placeholder="例如：报表集成（只读）" />
        </label>
        <fieldset>
          <legend>权限范围</legend>
          <ScCheckbox :checked="createForm.scopes.includes('intent.read')" label="读取 Intent" @change="setScope('intent.read', $event)" />
          <ScCheckbox :checked="createForm.scopes.includes('intent.write')" label="写入 Intent" @change="setScope('intent.write', $event)" />
        </fieldset>
        <fieldset v-if="companyOptions.length">
          <legend>允许公司</legend>
          <ScCheckbox v-for="company in companyOptions" :key="company.id" :checked="createForm.companyIds.includes(company.id)" :label="company.label" @change="setCompany(company.id, $event)" />
        </fieldset>
        <label class="sc-form-label">
          到期时间（可选）
          <ScInput v-model="createForm.expiresAt" type="datetime-local" />
        </label>
        <label class="sc-form-label">
          当前账号密码
          <ScInput v-model="createForm.password" type="password" required autocomplete="current-password" />
        </label>
        <p class="credential-hint">密码仅用于本次敏感操作确认，不会成为 API Key，也不会被保存。</p>
      </form>
      <template #actions>
        <ScButton variant="ghost" @click="closeCreate">取消</ScButton>
        <ScButton form="create-api-key-form" type="submit" variant="primary" :loading="submitting">创建并显示一次</ScButton>
      </template>
    </ScDialog>

    <ScDialog :open="Boolean(rotating)" title="轮换 API Key" @close="closeRotate">
      <form id="rotate-api-key-form" class="sc-form credential-form" autocomplete="off" @submit.prevent="rotateCredential">
        <p>轮换后旧 Key 立即撤销，原有机器会话随即失效。</p>
        <label class="sc-form-label">
          当前账号密码
          <ScInput v-model="rotatePassword" type="password" required autocomplete="current-password" />
        </label>
      </form>
      <template #actions>
        <ScButton variant="ghost" @click="closeRotate">取消</ScButton>
        <ScButton form="rotate-api-key-form" type="submit" variant="primary" :loading="submitting">确认轮换</ScButton>
      </template>
    </ScDialog>

    <ScDialog :open="Boolean(oneTimeSecret)" title="请立即保存 API Key" close-label="我已保存" @close="clearOneTimeSecret">
      <div
        class="one-time-secret"
        data-secret-display="once"
        data-evidence-sensitive="api_key"
      >
        <p class="credential-alert credential-alert--warning">关闭后将无法再次查看。请勿粘贴到聊天、日志或前端配置中。</p>
        <code>{{ oneTimeSecret }}</code>
        <p v-if="copyStatus" role="status">{{ copyStatus }}</p>
      </div>
      <template #actions>
        <ScButton variant="secondary" @click="copySecret">复制</ScButton>
        <ScButton variant="primary" @click="clearOneTimeSecret">我已安全保存</ScButton>
      </template>
    </ScDialog>
  </ScPage>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue';
import {
  createAuthCredential,
  listAuthCredentials,
  revokeAuthCredential,
  rotateAuthCredential,
  type AuthCredentialPolicy,
  type CredentialState,
} from '../api/authCredentials';
import { useSessionStore } from '../stores/session';
import {
  ScButton,
  ScCheckbox,
  ScDialog,
  ScEmptyState,
  ScPage,
  ScPageHeader,
  ScPanel,
  ScSection,
  ScStatusBadge,
  ScInput,
} from '../components/design-system';

type CompanyOption = { id: number; label: string };

const session = useSessionStore();
const credentials = ref<AuthCredentialPolicy[]>([]);
const loading = ref(false);
const submitting = ref(false);
const createOpen = ref(false);
const rotating = ref<AuthCredentialPolicy | null>(null);
const rotatePassword = ref('');
const oneTimeSecret = ref('');
const copyStatus = ref('');
const errorMessage = ref('');
const busyCredentialId = ref('');
const createForm = reactive({ name: '', password: '', scopes: ['intent.read'], companyIds: [] as number[], expiresAt: '' });

const companyOptions = computed<CompanyOption[]>(() => {
  const raw = session.recordContext?.company_options;
  if (!Array.isArray(raw)) return [];
  return raw
    .map((item) => ({ id: Number(item.company_id || 0), label: String(item.company_name || item.company_id || '').trim() }))
    .filter((item) => item.id > 0 && item.label);
});

function defaultCompanyIds(): number[] {
  const selected = Number(session.recordContext?.company_id || session.recordContext?.selected?.company_id || 0);
  if (selected > 0) return [selected];
  return companyOptions.value.length === 1 ? [companyOptions.value[0].id] : [];
}

function setScope(scope: string, checked: boolean) {
  const next = new Set(createForm.scopes);
  if (checked) next.add(scope);
  else next.delete(scope);
  createForm.scopes = [...next];
}

function setCompany(companyId: number, checked: boolean) {
  const next = new Set(createForm.companyIds);
  if (checked) next.add(companyId);
  else next.delete(companyId);
  createForm.companyIds = [...next];
}

function stateLabel(state: CredentialState): string {
  return ({ active: '有效', revoked: '已撤销', expired: '已过期' } as const)[state];
}

function stateSemantic(state: CredentialState): 'success' | 'danger' | 'warning' {
  return state === 'active' ? 'success' : state === 'expired' ? 'warning' : 'danger';
}

function scopeLabel(scopes: string[]): string {
  const labels: Record<string, string> = { 'intent.read': '读取', 'intent.write': '写入' };
  return scopes.map((scope) => labels[scope] || scope.replace(/^intent:/, '指定 Intent：')).join('、');
}

function companyLabel(ids: number[]): string {
  const byId = new Map(companyOptions.value.map((item) => [item.id, item.label]));
  return ids.map((id) => byId.get(id) || `公司 ${id}`).join('、');
}

function dateTimeLabel(value: string | false): string {
  if (!value) return '';
  const normalized = value.includes('T') ? value : value.replace(' ', 'T');
  const date = new Date(normalized.endsWith('Z') ? normalized : `${normalized}Z`);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function expiryPayload(value: string): string | undefined {
  if (!value) return undefined;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return undefined;
  return date.toISOString().slice(0, 19).replace('T', ' ');
}

function resetSensitiveInputs(): void {
  createForm.password = '';
  rotatePassword.value = '';
}

function clearOneTimeSecret(): void {
  oneTimeSecret.value = '';
  copyStatus.value = '';
}

function openCreate(): void {
  errorMessage.value = '';
  createForm.name = '';
  createForm.scopes = ['intent.read'];
  createForm.companyIds = defaultCompanyIds();
  createForm.expiresAt = '';
  resetSensitiveInputs();
  createOpen.value = true;
}

function closeCreate(): void {
  createOpen.value = false;
  resetSensitiveInputs();
}

function openRotate(item: AuthCredentialPolicy): void {
  rotating.value = item;
  rotatePassword.value = '';
  errorMessage.value = '';
}

function closeRotate(): void {
  rotating.value = null;
  resetSensitiveInputs();
}

async function loadCredentials(): Promise<void> {
  loading.value = true;
  errorMessage.value = '';
  try {
    credentials.value = await listAuthCredentials();
  } catch {
    errorMessage.value = '无法读取 API Key 列表，请稍后重试。';
  } finally {
    loading.value = false;
  }
}

async function createCredential(): Promise<void> {
  if (!createForm.scopes.length || !createForm.companyIds.length) {
    errorMessage.value = '至少选择一个权限范围和一个允许公司。';
    return;
  }
  submitting.value = true;
  errorMessage.value = '';
  try {
    const result = await createAuthCredential({
      name: createForm.name,
      password: createForm.password,
      scope: createForm.scopes,
      companyIds: createForm.companyIds,
      expiresAt: expiryPayload(createForm.expiresAt),
    });
    closeCreate();
    oneTimeSecret.value = result.api_key;
    await loadCredentials();
  } catch {
    errorMessage.value = 'API Key 创建被拒绝，请核对密码和授权范围。';
  } finally {
    resetSensitiveInputs();
    submitting.value = false;
  }
}

async function rotateCredential(): Promise<void> {
  if (!rotating.value) return;
  submitting.value = true;
  errorMessage.value = '';
  try {
    const result = await rotateAuthCredential(rotating.value.credential_id, rotatePassword.value);
    closeRotate();
    oneTimeSecret.value = result.api_key;
    await loadCredentials();
  } catch {
    errorMessage.value = 'API Key 轮换被拒绝，请核对当前密码。';
  } finally {
    resetSensitiveInputs();
    submitting.value = false;
  }
}

async function revoke(item: AuthCredentialPolicy): Promise<void> {
  if (!window.confirm(`确认撤销“${item.name}”？关联机器会话将立即失效。`)) return;
  busyCredentialId.value = item.credential_id;
  errorMessage.value = '';
  try {
    await revokeAuthCredential(item.credential_id);
    await loadCredentials();
  } catch {
    errorMessage.value = 'API Key 撤销被拒绝，请刷新后重试。';
  } finally {
    busyCredentialId.value = '';
  }
}

async function copySecret(): Promise<void> {
  if (!oneTimeSecret.value) return;
  try {
    await navigator.clipboard.writeText(oneTimeSecret.value);
    copyStatus.value = '已复制，请立即保存到受控密钥管理工具。';
  } catch {
    copyStatus.value = '浏览器未允许复制，请手动选择并保存。';
  }
}

onMounted(loadCredentials);
onBeforeUnmount(() => {
  clearOneTimeSecret();
  resetSensitiveInputs();
});
</script>

<style scoped>
.api-key-page { display: grid; gap: var(--sc-product-space-4); }
.credential-guidance { display: grid; gap: var(--sc-product-space-1); }
.credential-guidance span, .credential-hint, .credential-loading { color: var(--sc-app-text-secondary); }
.credential-alert { margin: 0; padding: var(--sc-product-space-2); border-radius: var(--sc-component-panel-radius); }
.credential-alert--error { color: var(--sc-app-danger-text); background: var(--sc-app-danger-bg); }
.credential-alert--warning { color: var(--sc-app-warning-text); background: var(--sc-app-warning-bg); }
.credential-list { display: grid; gap: var(--sc-product-space-3); }
.credential-card { display: grid; gap: var(--sc-product-space-3); padding: var(--sc-product-space-3); border: 1px solid var(--sc-app-border); border-radius: var(--sc-component-panel-radius); background: var(--sc-app-panel); }
.credential-card > header { display: flex; justify-content: space-between; align-items: flex-start; gap: var(--sc-product-space-2); }
.credential-card h3 { margin: 0 0 var(--sc-product-space-1); }
.credential-card code { color: var(--sc-app-text-secondary); overflow-wrap: anywhere; }
.credential-card dl { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: var(--sc-product-space-2); margin: 0; }
.credential-card dl div { min-width: 0; }
.credential-card dt { color: var(--sc-app-text-secondary); font-size: var(--sc-product-text-caption); }
.credential-card dd { margin: var(--sc-product-space-1) 0 0; overflow-wrap: anywhere; }
.credential-form fieldset { display: grid; gap: var(--sc-product-space-1); margin: 0; padding: var(--sc-product-space-2); border: 1px solid var(--sc-app-border); border-radius: var(--sc-component-input-radius); }
.credential-form legend { padding: 0 var(--sc-product-space-1); font-weight: 600; }
.credential-form label:not(.sc-form-label) { display: flex; align-items: center; gap: var(--sc-product-space-1); }
.credential-form .sc-input { min-height: calc(var(--sc-component-input-height-md) * 1px); padding: 0 var(--sc-product-space-2); }
.one-time-secret { display: grid; gap: var(--sc-product-space-2); }
.one-time-secret code { display: block; padding: var(--sc-product-space-3); border-radius: var(--sc-component-input-radius); background: var(--sc-app-subtle-bg); font-size: var(--sc-product-text-body); overflow-wrap: anywhere; user-select: all; }
@media (max-width: 720px) {
  .credential-card dl { grid-template-columns: 1fr; }
  .credential-card > header { align-items: flex-start; }
}
</style>
