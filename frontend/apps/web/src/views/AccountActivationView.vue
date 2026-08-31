<template>
  <main class="activation-page sc-page" data-semantic-component="AccountActivationView" :data-state="busy ? 'loading' : stage">
    <header class="activation-masthead" aria-label="产品品牌">
      <span class="activation-masthead__mark" aria-hidden="true">{{ config.appBrand.shellLogoText || 'S' }}</span>
      <strong>{{ pageText('brand_name', config.appBrand.name) }}</strong>
    </header>

    <section class="activation-layout">
      <section class="activation-brand">
        <div class="activation-brand__visual" aria-hidden="true">
          <span class="activation-brand__ring" />
          <span class="activation-brand__plane activation-brand__plane--primary" />
          <span class="activation-brand__plane activation-brand__plane--secondary" />
          <span class="activation-brand__orb activation-brand__orb--large" />
          <span class="activation-brand__orb activation-brand__orb--small" />
        </div>

        <ScPanel tone="raised" class="activation-brand__panel">
          <p class="activation-brand__eyebrow">Identity Setup</p>
          <h1>{{ pageText('title', '激活账号') }}</h1>
          <p class="activation-brand__description">{{ pageText('hint_code', '请输入经批准渠道单独收到的激活码，并设置自己的正式密码。') }}</p>
          <ol class="activation-brand__steps">
            <li :data-active="stage === 'code' || undefined">验证激活码</li>
            <li :data-active="stage === 'password' || undefined">设置正式密码</li>
            <li :data-active="stage === 'done' || undefined">完成并登录</li>
          </ol>
          <p v-if="config.appBrand.slogan" class="activation-brand__slogan">{{ config.appBrand.slogan }}</p>
        </ScPanel>
      </section>

      <section class="activation-panel">
        <ScCard
          v-if="pageSectionEnabled('card', true) && pageSectionTagIs('card', 'section')"
          class="activation-card"
          appearance="account"
          aria-labelledby="activation-title"
          :style="pageSectionStyle('card')"
        >
          <div class="activation-card__header">
            <p class="activation-card__kicker">账号入口</p>
            <h2 id="activation-title">{{ pageText('title', '激活账号') }}</h2>
          </div>

          <ScPanel v-if="stage === 'code'" tone="subtle" class="activation-note">
            <p>{{ pageText('hint_code', '请输入经批准渠道单独收到的激活码，并设置自己的正式密码。') }}</p>
          </ScPanel>

          <form
            v-if="stage === 'code' && pageSectionEnabled('code_form', true) && pageSectionTagIs('code_form', 'section')"
            :style="pageSectionStyle('code_form')"
            @submit.prevent="startActivation"
          >
            <label class="activation-field">
              {{ pageText('activation_code_label', '激活码') }}
              <ScInput
                id="activation-code"
                ref="codeInput"
                v-model="activationCode"
                size="large"
                autocomplete="one-time-code"
                spellcheck="false"
                :placeholder="pageText('activation_code_placeholder', '请输入激活码')"
                required
                :disabled="busy"
              />
            </label>
            <ScButton type="submit" variant="primary" size="large" :disabled="busy || !activationCode.trim()" :loading="busy">
              {{ busy ? pageText('submit_code_loading', '正在验证…') : pageText('submit_code_idle', '继续') }}
            </ScButton>
          </form>

          <form
            v-else-if="stage === 'password' && pageSectionEnabled('password_form', true) && pageSectionTagIs('password_form', 'section')"
            :style="pageSectionStyle('password_form')"
            @submit.prevent="finishActivation"
          >
            <ScPanel tone="subtle" class="activation-note">
              <p>{{ pageText('hint_password', '密码至少12位，并同时包含字母和数字。') }}</p>
            </ScPanel>
            <label class="activation-field">
              {{ pageText('password_label', '正式密码') }}
              <ScInput id="activation-password" v-model="password" size="large" type="password" autocomplete="new-password" :min-length="12" required :disabled="busy" />
            </label>
            <label class="activation-field">
              {{ pageText('password_confirm_label', '确认正式密码') }}
              <ScInput id="activation-password-confirm" v-model="confirmPassword" size="large" type="password" autocomplete="new-password" :min-length="12" required :disabled="busy" />
            </label>
            <ScButton type="submit" variant="primary" size="large" :disabled="busy || !password || !confirmPassword" :loading="busy">
              {{ busy ? pageText('submit_password_loading', '正在设置…') : pageText('submit_password_idle', '设置正式密码') }}
            </ScButton>
          </form>

          <section
            v-else-if="pageSectionEnabled('success', true) && pageSectionTagIs('success', 'section')"
            class="success"
            role="status"
            :style="pageSectionStyle('success')"
          >
            <ScPanel tone="subtle" class="activation-note activation-note--success">
              <p>{{ pageText('success_message', '账号激活成功。现在可以使用正式密码登录。') }}</p>
            </ScPanel>
            <ScButton type="button" appearance="auth-link" variant="ghost" @click="executeHeaderAction('open_login')">
              {{ pageText('back_to_login', '返回登录') }}
            </ScButton>
          </section>

          <ScPanel
            v-if="message && pageSectionEnabled('message', true) && pageSectionTagIs('message', 'section')"
            tone="subtle"
            class="activation-note activation-note--error"
            :style="pageSectionStyle('message')"
          >
            <p role="alert">{{ message }}</p>
          </ScPanel>
          <div
            v-if="stage !== 'done' && pageSectionEnabled('support', true) && pageSectionTagIs('support', 'section')"
            class="back-link"
            :style="pageSectionStyle('support')"
          >
            <ScButton type="button" appearance="auth-link" variant="ghost" @click="executeHeaderAction('open_login')">
              {{ pageText('back_to_login', '返回登录') }}
            </ScButton>
          </div>
        </ScCard>
      </section>
    </section>

    <footer class="activation-footer">
      <p>{{ footerPrimary }}</p>
      <p v-if="config.appBrand.footerSecondary">{{ config.appBrand.footerSecondary }}</p>
    </footer>
  </main>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref } from 'vue';
import { useRouter } from 'vue-router';
import { usePageContract } from '../app/pageContract';
import { executePageContractAction } from '../app/pageContractActionRuntime';
import { beginAccountActivation, completeAccountActivation } from '../services/accountActivation';
import { config } from '../config';
import ScButton from '../components/design-system/ScButton.vue';
import ScCard from '../components/design-system/ScCard.vue';
import ScInput from '../components/design-system/ScInput.vue';
import ScPanel from '../components/design-system/ScPanel.vue';

const router = useRouter();
const pageContract = usePageContract('account_activation');
const pageText = pageContract.text;
const pageSectionEnabled = pageContract.sectionEnabled;
const pageSectionStyle = pageContract.sectionStyle;
const pageSectionTagIs = pageContract.sectionTagIs;
const pageActionIntent = pageContract.actionIntent;
const pageActionTarget = pageContract.actionTarget;
const footerPrimary = computed(() => config.appBrand.footerPrimary || `Copyright © ${new Date().getFullYear()} ${pageText('brand_name', config.appBrand.name)}`);

const stage = ref<'code' | 'password' | 'done'>('code');
const activationCode = ref('');
const activationContext = ref('');
const password = ref('');
const confirmPassword = ref('');
const message = ref('');
const busy = ref(false);
const codeInput = ref<{ focus: () => void } | null>(null);

async function startActivation() {
  if (busy.value) return;
  busy.value = true;
  message.value = '';
  try {
    const result = await beginAccountActivation(activationCode.value.trim());
    activationContext.value = String(result.activation_context || '');
    activationCode.value = '';
    if (!result.ok || !activationContext.value) throw new Error(result.message || pageText('error_incomplete', '激活请求未完成'));
    stage.value = 'password';
    await nextTick();
    document.getElementById('activation-password')?.focus();
  } catch (error) {
    activationCode.value = '';
    message.value = error instanceof Error ? error.message : pageText('error_incomplete', '激活请求未完成');
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
    if (!result.ok) throw new Error(result.message || pageText('error_incomplete', '激活请求未完成'));
    activationContext.value = '';
    password.value = '';
    confirmPassword.value = '';
    stage.value = 'done';
  } catch (error) {
    password.value = '';
    confirmPassword.value = '';
    message.value = error instanceof Error ? error.message : pageText('error_incomplete', '激活请求未完成');
  } finally {
    busy.value = false;
  }
}

async function executeHeaderAction(actionKey: string) {
  await executePageContractAction({
    actionKey,
    router,
    actionIntent: pageActionIntent,
    actionTarget: pageActionTarget,
    query: {},
  });
}

onBeforeUnmount(() => {
  activationCode.value = '';
  activationContext.value = '';
  password.value = '';
  confirmPassword.value = '';
});
</script>

<style scoped>
.activation-page {
  min-height: 100vh;
  display: grid;
  place-items: stretch;
  gap: 18px;
  background: var(--sc-app-panel);
  color: var(--sc-app-text-primary);
  font-family: "Space Grotesk", "IBM Plex Sans", system-ui, sans-serif;
  padding: 56px 0 0;
  position: relative;
  overflow: hidden;
}

.activation-masthead {
  position: absolute;
  top: 14px;
  left: 24px;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  color: var(--sc-app-text-primary);
  font-size: 16px;
  z-index: var(--sc-component-login-layer-content);
}

.activation-masthead__mark {
  display: grid;
  width: 30px;
  height: 30px;
  place-items: center;
  border-radius: var(--sc-product-radius-control);
  background: var(--sc-semantic-surface-interactive);
  color: var(--sc-semantic-text-on-interactive);
  font-weight: 800;
}

.activation-layout {
  width: 100%;
  min-height: calc(100vh - 56px);
  display: grid;
  grid-template-columns: minmax(420px, 42vw) minmax(0, 1fr);
}

.activation-brand {
  position: relative;
  display: grid;
  align-items: end;
  padding: 64px;
  overflow: hidden;
  background:
    radial-gradient(circle at 40% 34%, color-mix(in srgb, var(--sc-app-panel) 88%, transparent) 0 14%, transparent 45%),
    linear-gradient(145deg, var(--sc-app-panel) 0%, var(--sc-app-subtle-bg) 54%, var(--sc-app-info-bg) 100%);
}

.activation-brand__visual {
  position: absolute;
  inset: 0;
}

.activation-brand__ring {
  position: absolute;
  left: 18%;
  top: 16%;
  width: min(40vw, 520px);
  aspect-ratio: 1;
  border-radius: 50%;
  border: min(7vw, 84px) solid color-mix(in srgb, var(--sc-app-border) 56%, var(--sc-app-panel));
}

.activation-brand__plane {
  position: absolute;
  border-radius: 24px;
  box-shadow: var(--sc-app-shadow-modal);
  transform: rotate(28deg);
}

.activation-brand__plane--primary {
  left: 12%;
  bottom: -2%;
  width: 62%;
  height: 34%;
  background: color-mix(in srgb, var(--sc-app-panel) 84%, transparent);
}

.activation-brand__plane--secondary {
  right: 8%;
  top: 24%;
  width: 24%;
  height: 18%;
  background: linear-gradient(135deg, var(--sc-app-info-bg), var(--sc-semantic-surface-interactive));
}

.activation-brand__orb {
  position: absolute;
  border-radius: 50%;
  box-shadow: var(--sc-app-shadow-modal);
}

.activation-brand__orb--large {
  top: 52%;
  left: 22%;
  width: 112px;
  height: 112px;
  background: linear-gradient(145deg, var(--sc-semantic-surface-interactive), var(--sc-app-info-bg));
}

.activation-brand__orb--small {
  top: 30%;
  left: 48%;
  width: 88px;
  height: 88px;
  background: var(--sc-app-panel);
}

.activation-brand__panel {
  position: relative;
  max-width: 520px;
  margin-left: 4%;
  display: grid;
  gap: 12px;
}

.activation-brand__eyebrow,
.activation-brand__description,
.activation-brand__slogan {
  margin: 0;
  color: var(--sc-app-text-secondary);
}

.activation-brand__eyebrow {
  font-size: 12px;
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

.activation-brand h1 {
  margin: 0;
  font-size: clamp(34px, 4vw, 50px);
  line-height: 1.05;
  letter-spacing: -0.04em;
}

.activation-brand__description {
  max-width: 34ch;
  font-size: 16px;
  line-height: 1.5;
}

.activation-brand__steps {
  margin: 6px 0 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 10px;
}

.activation-brand__steps li {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--sc-app-text-secondary);
}

.activation-brand__steps li::before {
  content: '';
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: var(--sc-app-border);
}

.activation-brand__steps li[data-active='true'] {
  color: var(--sc-app-text-primary);
  font-weight: 600;
}

.activation-brand__steps li[data-active='true']::before {
  background: var(--sc-semantic-surface-interactive);
  box-shadow: 0 0 0 6px color-mix(in srgb, var(--sc-semantic-surface-interactive) 18%, transparent);
}

.activation-brand__slogan {
  font-size: 14px;
}

.activation-panel {
  display: grid;
  align-content: start;
  padding: clamp(116px, 20vh, 178px) clamp(24px, 5vw, 72px) 88px;
}

.activation-card {
  width: min(460px, 100%);
  display: grid;
  gap: 16px;
}

.activation-card__header {
  display: grid;
  gap: 8px;
}

.activation-card__kicker {
  margin: 0;
  color: var(--sc-app-text-secondary);
  font-size: 12px;
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

.activation-card h2 {
  margin: 0;
  font-size: 28px;
  line-height: 1.1;
  letter-spacing: -0.03em;
}

form {
  display: grid;
  gap: 12px;
}

.activation-field {
  display: grid;
  gap: 6px;
  font-size: 12px;
  color: var(--sc-app-text-secondary);
  font-weight: 500;
}

.activation-note p {
  margin: 0;
}

.activation-note--error {
  color: var(--sc-app-danger-text);
  background: color-mix(in srgb, var(--sc-app-danger-bg) 84%, white);
}

.activation-note--success {
  background: color-mix(in srgb, var(--sc-app-success-bg) 76%, white);
}

.success {
  display: grid;
  gap: 12px;
}

.back-link {
  justify-self: start;
}

.activation-footer {
  position: absolute;
  bottom: 24px;
  left: clamp(24px, 5vw, 72px);
  color: var(--sc-app-text-secondary);
  font-size: 12px;
  line-height: 1.45;
}

.activation-footer p {
  margin: 0;
}

@media (max-width: 920px) {
  .activation-layout {
    grid-template-columns: 1fr;
  }

  .activation-brand {
    display: none;
  }

  .activation-panel {
    padding-top: 96px;
  }
}

@media (max-width: 640px) {
  .activation-page {
    padding: 72px 16px 56px;
  }

  .activation-panel {
    padding: 16px 0 24px;
  }

  .activation-footer {
    left: 16px;
    bottom: 16px;
  }
}
</style>
