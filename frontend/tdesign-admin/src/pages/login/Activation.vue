<template>
  <div class="auth-flow">
    <t-card class="auth-flow__card" :bordered="false">
      <div class="auth-flow__heading">
        <t-button variant="text" @click="router.push('/login')"
          ><template #icon><t-icon name="chevron-left" /></template>返回登录</t-button
        >
        <h1>激活账号</h1>
        <p>请输入组织管理员发放的激活码，并设置正式登录密码。</p>
      </div>
      <t-alert v-if="message" theme="error" :message="message" />
      <t-result v-if="stage === 'done'" theme="success" title="账号激活成功" description="现在可以使用正式密码登录。">
        <template #extra><t-button theme="primary" @click="router.push('/login')">返回登录</t-button></template>
      </t-result>
      <t-form v-else :data="formData" :rules="rules" @submit="submit">
        <t-form-item v-if="stage === 'code'" name="activationCode" label="激活码">
          <t-input v-model="formData.activationCode" autocomplete="one-time-code" />
        </t-form-item>
        <template v-else>
          <t-form-item name="password" label="正式密码"
            ><t-input v-model="formData.password" type="password" autocomplete="new-password"
          /></t-form-item>
          <t-form-item name="confirmPassword" label="确认密码"
            ><t-input v-model="formData.confirmPassword" type="password" autocomplete="new-password"
          /></t-form-item>
          <t-alert theme="info" message="密码至少 12 位，并同时包含字母和数字。" />
        </template>
        <t-button theme="primary" type="submit" block :loading="busy">{{
          stage === 'code' ? '验证激活码' : '设置正式密码'
        }}</t-button>
      </t-form>
    </t-card>
  </div>
</template>
<script setup lang="ts">
import type { FormRule, SubmitContext } from 'tdesign-vue-next';
import { MessagePlugin } from 'tdesign-vue-next';
import { computed, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';

import { beginAccountActivation, completeAccountActivation } from '@/api/odoo';

const router = useRouter();
const stage = ref<'code' | 'password' | 'done'>('code');
const busy = ref(false);
const message = ref('');
const activationContext = ref('');
const formData = reactive({ activationCode: '', password: '', confirmPassword: '' });
const rules = computed<Record<string, FormRule[]>>(() => ({
  activationCode: [{ required: true, message: '请输入激活码', type: 'error' }],
  password: [{ required: true, min: 12, message: '密码至少 12 位', type: 'error' }],
  confirmPassword: [{ required: true, message: '请确认密码', type: 'error' }],
}));

async function submit(context: SubmitContext) {
  if (context.validateResult !== true || busy.value) return;
  busy.value = true;
  message.value = '';
  try {
    if (stage.value === 'code') {
      const result = await beginAccountActivation(formData.activationCode.trim());
      if (!result.ok || !result.activation_context) throw new Error(result.message || '激活码验证失败');
      activationContext.value = result.activation_context;
      stage.value = 'password';
    } else {
      if (formData.password !== formData.confirmPassword) throw new Error('两次密码输入不一致');
      const result = await completeAccountActivation(
        activationContext.value,
        formData.password,
        formData.confirmPassword,
      );
      if (!result.ok) throw new Error(result.message || '账号激活失败');
      stage.value = 'done';
      MessagePlugin.success('账号激活成功');
    }
  } catch (cause) {
    message.value = cause instanceof Error ? cause.message : '请求未完成';
  } finally {
    busy.value = false;
  }
}
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
  padding: 16px;
}
.auth-flow__heading {
  margin-bottom: 24px;
}
.auth-flow__heading h1 {
  margin: 20px 0 8px;
  font-size: 28px;
}
.auth-flow__heading p {
  margin: 0;
  color: var(--td-text-color-secondary);
}
</style>
