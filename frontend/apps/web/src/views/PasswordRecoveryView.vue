<template>
  <main class="recovery-page sc-page" data-semantic-component="PasswordRecoveryView" data-state="ready">
    <header class="recovery-masthead" aria-label="产品品牌">
      <span class="recovery-masthead__mark" aria-hidden="true">{{ config.appBrand.shellLogoText || 'S' }}</span>
      <strong>{{ pageText('brand_name', config.appBrand.name) }}</strong>
    </header>

    <section class="recovery-layout">
      <section class="recovery-brand">
        <ScPanel tone="raised" class="recovery-brand__panel">
          <p class="recovery-brand__eyebrow">Password Support</p>
          <h1>{{ pageText('title', '忘记密码') }}</h1>
          <p class="recovery-brand__description">{{ pageText('message_default', '当前请通过已批准的组织身份核验流程申请密码恢复。') }}</p>
          <ul class="recovery-brand__notes">
            <li>密码恢复请求不会暴露账号存在性。</li>
            <li>恢复动作必须经过已批准的组织身份核验流程。</li>
            <li>完成后请立即返回登录页继续处理。</li>
          </ul>
        </ScPanel>
      </section>

      <section class="recovery-panel">
        <ScCard
          v-if="pageSectionEnabled('card', true) && pageSectionTagIs('card', 'section')"
          class="recovery-card"
          appearance="account"
          aria-labelledby="recovery-title"
          :style="pageSectionStyle('card')"
        >
          <div class="recovery-card__header">
            <p class="recovery-card__kicker">账号恢复</p>
            <h2 id="recovery-title">{{ pageText('title', '忘记密码') }}</h2>
          </div>
          <ScPanel v-if="pageSectionEnabled('message', true) && pageSectionTagIs('message', 'section')" tone="subtle" class="recovery-note" :style="pageSectionStyle('message')">
            <p>{{ message }}</p>
          </ScPanel>
          <ScPanel v-if="pageSectionEnabled('support', true) && pageSectionTagIs('support', 'section')" tone="subtle" class="recovery-note recovery-note--muted" :style="pageSectionStyle('support')">
            <p>{{ pageText('hint', '为保护账号安全，本页面不会确认某个账号是否存在。') }}</p>
          </ScPanel>
          <ScButton type="button" appearance="auth-link" variant="ghost" @click="executeHeaderAction('open_login')">
            {{ pageText('back_to_login', '返回登录') }}
          </ScButton>
        </ScCard>
      </section>
    </section>

    <footer class="recovery-footer">
      <p>{{ footerPrimary }}</p>
      <p v-if="config.appBrand.footerSecondary">{{ config.appBrand.footerSecondary }}</p>
    </footer>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { usePageContract } from '../app/pageContract';
import { executePageContractAction } from '../app/pageContractActionRuntime';
import { getPasswordRecoveryStatus } from '../services/accountActivation';
import { config } from '../config';
import ScButton from '../components/design-system/ScButton.vue';
import ScCard from '../components/design-system/ScCard.vue';
import ScPanel from '../components/design-system/ScPanel.vue';

const router = useRouter();
const pageContract = usePageContract('password_recovery');
const pageText = pageContract.text;
const pageSectionEnabled = pageContract.sectionEnabled;
const pageSectionStyle = pageContract.sectionStyle;
const pageSectionTagIs = pageContract.sectionTagIs;
const pageActionIntent = pageContract.actionIntent;
const pageActionTarget = pageContract.actionTarget;
const footerPrimary = computed(() => config.appBrand.footerPrimary || `Copyright © ${new Date().getFullYear()} ${pageText('brand_name', config.appBrand.name)}`);

const message = ref(pageText('message_default', '当前请通过已批准的组织身份核验流程申请密码恢复。'));
onMounted(async () => {
  try {
    const result = await getPasswordRecoveryStatus();
    if (result.message) message.value = result.message;
  } catch {
    // Keep the same non-enumerating fallback for network and service errors.
  }
});

async function executeHeaderAction(actionKey: string) {
  await executePageContractAction({
    actionKey,
    router,
    actionIntent: pageActionIntent,
    actionTarget: pageActionTarget,
    query: {},
  });
}
</script>

<style scoped>
.recovery-page {
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

.recovery-masthead {
  position: absolute;
  top: 14px;
  left: 24px;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  color: var(--sc-app-text-primary);
  font-size: 16px;
}

.recovery-masthead__mark {
  display: grid;
  width: 30px;
  height: 30px;
  place-items: center;
  border-radius: var(--sc-product-radius-control);
  background: var(--sc-semantic-surface-interactive);
  color: var(--sc-semantic-text-on-interactive);
  font-weight: 800;
}

.recovery-layout {
  width: 100%;
  min-height: calc(100vh - 56px);
  display: grid;
  grid-template-columns: minmax(420px, 42vw) minmax(0, 1fr);
}

.recovery-brand {
  display: grid;
  align-items: end;
  padding: 64px;
  background:
    linear-gradient(150deg, var(--sc-app-panel) 0%, var(--sc-app-subtle-bg) 58%, color-mix(in srgb, var(--sc-app-info-bg) 72%, white) 100%);
}

.recovery-brand__panel {
  max-width: 520px;
  margin-left: 4%;
  display: grid;
  gap: 12px;
}

.recovery-brand__eyebrow,
.recovery-brand__description {
  margin: 0;
  color: var(--sc-app-text-secondary);
}

.recovery-brand__eyebrow {
  font-size: 12px;
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

.recovery-brand h1 {
  margin: 0;
  font-size: clamp(34px, 4vw, 50px);
  line-height: 1.05;
  letter-spacing: -0.04em;
}

.recovery-brand__description {
  max-width: 34ch;
  font-size: 16px;
  line-height: 1.5;
}

.recovery-brand__notes {
  margin: 4px 0 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 8px;
  color: var(--sc-app-text-secondary);
}

.recovery-brand__notes li {
  border-inline-start: 2px solid var(--sc-semantic-surface-interactive);
  padding-inline-start: 8px;
}

.recovery-panel {
  display: grid;
  align-content: start;
  padding: clamp(116px, 20vh, 178px) clamp(24px, 5vw, 72px) 88px;
}

.recovery-card {
  width: min(460px, 100%);
  display: grid;
  gap: 16px;
}

.recovery-card__header {
  display: grid;
  gap: 8px;
}

.recovery-card__kicker {
  margin: 0;
  color: var(--sc-app-text-secondary);
  font-size: 12px;
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

.recovery-card h2 {
  margin: 0;
  font-size: 28px;
  line-height: 1.1;
  letter-spacing: -0.03em;
}

.recovery-note p {
  margin: 0;
}

.recovery-note--muted {
  color: var(--sc-app-text-secondary);
}

.recovery-footer {
  position: absolute;
  bottom: 24px;
  left: clamp(24px, 5vw, 72px);
  color: var(--sc-app-text-secondary);
  font-size: 12px;
  line-height: 1.45;
}

.recovery-footer p {
  margin: 0;
}

@media (max-width: 920px) {
  .recovery-layout {
    grid-template-columns: 1fr;
  }

  .recovery-brand {
    display: none;
  }

  .recovery-panel {
    padding-top: 96px;
  }
}

@media (max-width: 640px) {
  .recovery-page {
    padding: 72px 16px 56px;
  }

  .recovery-panel {
    padding: 16px 0 24px;
  }

  .recovery-footer {
    left: 16px;
    bottom: 16px;
  }
}
</style>
