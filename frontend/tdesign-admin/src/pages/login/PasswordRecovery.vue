<template>
  <div class="auth-flow">
    <t-card class="auth-flow__card" :bordered="false">
      <t-button variant="text" @click="router.push('/login')"
        ><template #icon><t-icon name="chevron-left" /></template>返回登录</t-button
      >
      <h1>忘记密码</h1>
      <t-alert theme="info" message="为保护账号安全，本页面不会确认某个账号是否存在。" />
      <p class="recovery-message">{{ message }}</p>
      <t-button block theme="primary" @click="router.push('/login')">返回登录</t-button>
    </t-card>
  </div>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';

import { getPasswordRecoveryStatus } from '@/api/odoo';

const router = useRouter();
const message = ref('当前请通过已批准的组织身份核验流程申请密码恢复。');
onMounted(async () => {
  try {
    const result = await getPasswordRecoveryStatus();
    if (result.message) message.value = result.message;
  } catch {
    // Keep the non-enumerating fallback when the endpoint is unavailable.
  }
});
</script>
<style scoped>
.auth-flow {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
  background: var(--td-bg-color-page);
}
.auth-flow__card {
  width: min(520px, 100%);
  padding: 24px;
}
.auth-flow__card h1 {
  margin: 24px 0 16px;
  font-size: 28px;
}
.recovery-message {
  min-height: 80px;
  margin: 20px 0;
  color: var(--td-text-color-secondary);
  line-height: 1.7;
}
</style>
