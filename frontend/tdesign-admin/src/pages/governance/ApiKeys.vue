<template>
  <div class="governance-page">
    <div class="page-heading">
      <div>
        <p class="eyebrow">账户安全</p>
        <h1>API Key 管理</h1>
        <p>密钥仅在创建时显示一次，请妥善保存。</p>
      </div>
      <t-button variant="outline" :loading="loading" @click="load">刷新</t-button>
    </div>
    <t-alert v-if="error" theme="error" :message="error" /><t-card :bordered="false" class="panel"
      ><template #title>已创建密钥</template
      ><template #actions
        ><t-button theme="primary" @click="dialog = true"
          ><template #icon><t-icon name="add" /></template>创建密钥</t-button
        ></template
      ><t-table :data="credentials" :columns="columns" row-key="credential_id"
        ><template #state="{ row }"
          ><t-tag
            :theme="row.state === 'active' ? 'success' : row.state === 'expired' ? 'warning' : 'danger'"
            variant="light"
            >{{ row.state }}</t-tag
          ></template
        ><template #operation="{ row }"
          ><t-space size="small"
            ><t-link theme="primary" @click="openRotate(row.credential_id)">轮换</t-link
            ><t-popconfirm content="确认撤销此密钥？" @confirm="revoke(row.credential_id)"
              ><t-link theme="danger">撤销</t-link></t-popconfirm
            ></t-space
          ></template
        ></t-table
      ><t-empty v-if="!loading && !credentials.length" description="暂无 API Key" /></t-card
    ><t-dialog
      v-model:visible="dialog"
      header="创建 API Key"
      :confirm-btn="{ content: '创建', theme: 'primary', loading: creating }"
      @confirm="create"
      ><t-form :data="form"
        ><t-form-item label="名称"><t-input v-model="form.name" /></t-form-item
        ><t-form-item label="初始密码"><t-input v-model="form.password" type="password" /></t-form-item
        ><t-form-item label="公司范围"
          ><t-select
            v-model="form.companyIds"
            multiple
            :options="companyOptions"
            placeholder="默认当前公司" /></t-form-item
        ><t-form-item label="有效期"
          ><t-date-picker v-model="form.expiresAt" enable-time-picker clearable /></t-form-item
        ><t-form-item label="权限范围"
          ><t-select v-model="form.scope" multiple :options="scopeOptions" /></t-form-item></t-form></t-dialog
    ><t-dialog v-model:visible="secretVisible" header="请立即保存 API Key" :footer="false"
      ><t-alert theme="warning" message="关闭后将无法再次查看完整密钥。" /><t-textarea
        :model-value="createdSecret"
        readonly
        :autosize="{ minRows: 3, maxRows: 6 }"
      /><t-space direction="vertical" style="width: 100%"
        ><t-button block variant="outline" @click="copySecret">复制密钥</t-button
        ><t-button block theme="primary" @click="closeSecret">我已保存</t-button></t-space
      ></t-dialog
    >
    <t-dialog
      v-model:visible="rotateDialog"
      header="轮换 API Key"
      :confirm-btn="{ content: '轮换', theme: 'primary', loading: rotating }"
      @confirm="rotate"
      ><t-alert theme="warning" message="轮换后旧密钥将失效，新密钥只显示一次。" /><t-form :data="rotateForm"
        ><t-form-item label="验证密码"><t-input v-model="rotateForm.password" type="password" /></t-form-item></t-form
    ></t-dialog>
  </div>
</template>
<script setup lang="ts">
import { MessagePlugin } from 'tdesign-vue-next';
import { computed, onMounted, reactive, ref } from 'vue';

import type { AuthCredential } from '@/api/odoo';
import { createAuthCredential, listAuthCredentials, revokeAuthCredential, rotateAuthCredential } from '@/api/odoo';
import { useUserStore } from '@/store';

const loading = ref(false);
const error = ref('');
const credentials = ref<AuthCredential[]>([]);
const dialog = ref(false);
const creating = ref(false);
const secretVisible = ref(false);
const createdSecret = ref('');
const form = reactive({ name: '', password: '', scope: [] as string[], companyIds: [] as number[], expiresAt: '' });
const user = useUserStore();
const companyOptions = computed(() =>
  ((user.recordContext.company_options || []) as Array<Record<string, unknown>>).map((item) => ({
    value: Number(item.company_id),
    label: String(item.company_name || item.company_id),
  })),
);
const rotateDialog = ref(false);
const rotating = ref(false);
const rotatingCredentialId = ref('');
const rotateForm = reactive({ password: '' });
const scopeOptions = [
  { label: '读取 Intent', value: 'intent.read' },
  { label: '写入 Intent', value: 'intent.write' },
];
const columns = [
  { colKey: 'name', title: '名称' },
  { colKey: 'state', title: '状态' },
  {
    colKey: 'scope',
    title: '权限范围',
    cell: ({ row }: any) => (Array.isArray(row.scope) ? row.scope.join(', ') : '—'),
  },
  { colKey: 'last_used_at', title: '最近使用' },
  { colKey: 'usage_count', title: '使用次数' },
  { colKey: 'expires_at', title: '有效期' },
  { colKey: 'operation', title: '操作', width: 130 },
];
async function load() {
  loading.value = true;
  error.value = '';
  try {
    credentials.value = await listAuthCredentials();
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '密钥列表加载失败';
  } finally {
    loading.value = false;
  }
}
async function create() {
  if (!form.name || !form.password) {
    MessagePlugin.warning('请填写名称和初始密码');
    return;
  }
  creating.value = true;
  try {
    const result = await createAuthCredential({
      name: form.name,
      password: form.password,
      scope: form.scope,
      companyIds: form.companyIds,
      expiresAt: form.expiresAt ? new Date(form.expiresAt).toISOString().slice(0, 19).replace('T', ' ') : undefined,
    });
    createdSecret.value = result.api_key || '';
    dialog.value = false;
    secretVisible.value = Boolean(createdSecret.value);
    form.name = '';
    form.password = '';
    form.scope = [];
    form.companyIds = [];
    form.expiresAt = '';
    await load();
  } catch (cause) {
    MessagePlugin.error(cause instanceof Error ? cause.message : '创建失败');
  } finally {
    creating.value = false;
  }
}
async function revoke(id: string) {
  try {
    await revokeAuthCredential(id);
    MessagePlugin.success('密钥已撤销');
    await load();
  } catch (cause) {
    MessagePlugin.error(cause instanceof Error ? cause.message : '撤销失败');
  }
}
async function copySecret() {
  if (!createdSecret.value) return;
  await navigator.clipboard.writeText(createdSecret.value);
  MessagePlugin.success('密钥已复制');
}
function closeSecret() {
  createdSecret.value = '';
  secretVisible.value = false;
}
function openRotate(id: string) {
  rotatingCredentialId.value = id;
  rotateForm.password = '';
  rotateDialog.value = true;
}
async function rotate() {
  if (!rotatingCredentialId.value || !rotateForm.password) {
    MessagePlugin.warning('请填写验证密码');
    return;
  }
  rotating.value = true;
  try {
    const result = await rotateAuthCredential(rotatingCredentialId.value, rotateForm.password);
    createdSecret.value = result.api_key || '';
    rotateDialog.value = false;
    secretVisible.value = Boolean(createdSecret.value);
    await load();
  } catch (cause) {
    MessagePlugin.error(cause instanceof Error ? cause.message : '轮换失败');
  } finally {
    rotating.value = false;
  }
}
onMounted(load);
</script>
<style scoped>
.governance-page {
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
.panel {
  border: 1px solid var(--td-border-level-1-color);
}
</style>
