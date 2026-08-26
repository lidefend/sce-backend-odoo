<template>
  <main class="recovery-page sc-page" data-semantic-component="PasswordRecoveryView" data-state="ready">
    <ScCard class="recovery-card" appearance="account" aria-labelledby="recovery-title">
      <h1 id="recovery-title">忘记密码</h1>
      <p>{{ message }}</p>
      <p class="hint">为保护账号安全，本页面不会确认某个账号是否存在。</p>
      <RouterLink to="/login">返回登录</RouterLink>
    </ScCard>
  </main>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { getPasswordRecoveryStatus } from '../services/accountActivation';
import ScCard from '../components/design-system/ScCard.vue';

const message = ref('当前请通过已批准的组织身份核验流程申请密码恢复。');
onMounted(async () => {
  try {
    const result = await getPasswordRecoveryStatus();
    if (result.message) message.value = result.message;
  } catch {
    // Keep the same non-enumerating fallback for network and service errors.
  }
});
</script>

<style scoped>
.recovery-page { min-height: 100vh; display: grid; place-items: center; padding: 24px; background: var(--sc-app-bg); }
.recovery-card { width: min(460px, 100%); }
.hint { color: var(--sc-app-text-secondary); }
</style>
