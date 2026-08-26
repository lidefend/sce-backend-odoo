<template>
  <main class="activation-page sc-page" data-semantic-component="AccountActivationView" :data-state="busy ? 'loading' : stage">
    <section class="activation-card sc-panel" aria-labelledby="activation-title">
      <h1 id="activation-title">激活账号</h1>
      <p class="hint">请输入经批准渠道单独收到的激活码，并设置自己的正式密码。</p>

      <form v-if="stage === 'code'" @submit.prevent="startActivation">
        <label for="activation-code">激活码</label>
        <input
          id="activation-code"
          ref="codeInput"
          v-model="activationCode"
          autocomplete="one-time-code"
          spellcheck="false"
          required
          :disabled="busy"
        />
        <button type="submit" :disabled="busy || !activationCode.trim()">{{ busy ? '正在验证…' : '继续' }}</button>
      </form>

      <form v-else-if="stage === 'password'" @submit.prevent="finishActivation">
        <p class="hint">密码至少12位，并同时包含字母和数字。</p>
        <label for="activation-password">正式密码</label>
        <input id="activation-password" v-model="password" type="password" autocomplete="new-password" minlength="12" required :disabled="busy" />
        <label for="activation-password-confirm">确认正式密码</label>
        <input id="activation-password-confirm" v-model="confirmPassword" type="password" autocomplete="new-password" minlength="12" required :disabled="busy" />
        <button type="submit" :disabled="busy || !password || !confirmPassword">{{ busy ? '正在设置…' : '设置正式密码' }}</button>
      </form>

      <section v-else class="success" role="status">
        <p>账号激活成功。现在可以使用正式密码登录。</p>
        <RouterLink to="/login">返回登录</RouterLink>
      </section>

      <p v-if="message" class="message" role="alert">{{ message }}</p>
      <RouterLink v-if="stage !== 'done'" class="back-link" to="/login">返回登录</RouterLink>
    </section>
  </main>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref } from 'vue';
import { beginAccountActivation, completeAccountActivation } from '../services/accountActivation';

const stage = ref<'code' | 'password' | 'done'>('code');
const activationCode = ref('');
const activationContext = ref('');
const password = ref('');
const confirmPassword = ref('');
const message = ref('');
const busy = ref(false);
const codeInput = ref<HTMLInputElement | null>(null);

async function startActivation() {
  if (busy.value) return;
  busy.value = true;
  message.value = '';
  try {
    const result = await beginAccountActivation(activationCode.value.trim());
    activationContext.value = String(result.activation_context || '');
    activationCode.value = '';
    if (!result.ok || !activationContext.value) throw new Error(result.message || '激活请求未完成');
    stage.value = 'password';
    await nextTick();
    document.getElementById('activation-password')?.focus();
  } catch (error) {
    activationCode.value = '';
    message.value = error instanceof Error ? error.message : '激活请求未完成';
    await nextTick();
    codeInput.value?.focus();
  } finally {
    busy.value = false;
  }
}

async function finishActivation() {
  if (busy.value) return;
  busy.value = true;
  message.value = '';
  try {
    const result = await completeAccountActivation(activationContext.value, password.value, confirmPassword.value);
    if (!result.ok) throw new Error(result.message || '激活请求未完成');
    activationContext.value = '';
    password.value = '';
    confirmPassword.value = '';
    stage.value = 'done';
  } catch (error) {
    password.value = '';
    confirmPassword.value = '';
    message.value = error instanceof Error ? error.message : '激活请求未完成';
  } finally {
    busy.value = false;
  }
}

onBeforeUnmount(() => {
  activationCode.value = '';
  activationContext.value = '';
  password.value = '';
  confirmPassword.value = '';
});
</script>

<style scoped>
.activation-page { min-height: 100vh; display: grid; place-items: center; padding: 24px; background: var(--sc-app-bg); }
.activation-card { width: min(460px, 100%); display: grid; gap: 16px; padding: 28px; }
form { display: grid; gap: 10px; }
input { min-height: 42px; padding: 8px 10px; }
button { min-height: 42px; margin-top: 8px; }
.hint { color: var(--sc-app-text-secondary); }
.message { color: var(--sc-semantic-state-danger-text); }
.back-link { justify-self: start; }
</style>
