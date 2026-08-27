<template>
  <main class="login-page sc-page" data-semantic-component="LoginView" :data-state="loading ? 'loading' : error ? 'error' : 'ready'" :aria-busy="loading || undefined">
    <header class="login-masthead" aria-label="产品品牌">
      <span class="login-masthead__mark" aria-hidden="true">S</span>
      <strong>{{ pageText('brand_name', config.appBrand.name) }}</strong>
    </header>
    <section class="login-layout">
      <section class="brand-panel" aria-label="平台介绍">
        <div class="brand-visual" aria-hidden="true">
          <span class="brand-visual__wireframe" />
          <span class="brand-visual__dashboard">
            <i class="brand-visual__dashboard-line brand-visual__dashboard-line--short" />
            <i class="brand-visual__dashboard-line" />
            <i class="brand-visual__dashboard-line" />
            <i class="brand-visual__dashboard-line brand-visual__dashboard-line--short" />
          </span>
          <span class="brand-visual__ring" />
          <span class="brand-visual__brand-cube"><b>S</b></span>
          <span class="brand-visual__plane brand-visual__plane--primary" />
          <span class="brand-visual__plane brand-visual__plane--secondary" />
          <span class="brand-visual__orb brand-visual__orb--primary" />
          <span class="brand-visual__orb brand-visual__orb--success" />
          <span class="brand-visual__orb brand-visual__orb--neutral" />
          <span class="brand-visual__grid" />
        </div>
        <div v-if="brandSlogan || valueLines.length" class="brand-copy">
          <p v-if="brandSlogan" class="brand-slogan">{{ brandSlogan }}</p>
          <ul v-if="valueLines.length" class="value-list" aria-label="价值主张">
            <li v-for="line in valueLines" :key="line">{{ line }}</li>
          </ul>
        </div>
      </section>

      <section class="auth-panel">
        <section v-if="headerActions.length" class="page-actions">
          <ScButton
            v-for="action in headerActions"
            :key="`login-header-${action.key}`"
            class="ghost sc-btn sc-btn-ghost sc-btn-sm"
            appearance="outline-action"
            variant="ghost"
            size="small"
            :disabled="loading"
            @click="executeHeaderAction(action.key)"
          >
            {{ action.label || action.key }}
          </ScButton>
        </section>

        <ScCard
          v-if="pageSectionEnabled('card', true) && pageSectionTagIs('card', 'section')"
          class="login-card sc-panel"
          appearance="auth"
          :style="{ ...pageSectionStyle('card'), '--sc-card-body-padding': '0' }"
        >
          <header class="brand-header">
            <span v-if="config.appBrand.productBadge" class="product-badge">{{ config.appBrand.productBadge }}</span>
            <p v-if="config.appBrand.kicker" class="brand-kicker">{{ config.appBrand.kicker }}</p>
            <h1>
              <span>{{ pageText('title', loginTitleFallback) }}</span>
              <strong>{{ pageText('brand_name', config.appBrand.name) }}</strong>
            </h1>
          </header>

          <p v-if="activationAction" class="auth-onboarding">
            <span>{{ pageText('activation_prompt', '没有账号？') }}</span>
            <ScButton
              class="auth-entry-link"
              appearance="auth-link"
              type="button"
              variant="ghost"
              :disabled="loading"
              @click="executeHeaderAction(activationAction.key)"
            >
              {{ activationAction.label || activationAction.key }}
            </ScButton>
          </p>

          <form
            v-if="pageSectionEnabled('form', true) && pageSectionTagIs('form', 'section')"
            class="sc-form"
            :style="pageSectionStyle('form')"
            @submit.prevent="onSubmit"
          >
            <label class="sc-form-label">
              {{ pageText('username_label', '账号') }}
              <ScInput
                id="login-username"
                v-model="username"
                class="sc-input"
                size="large"
                autocomplete="username"
                :placeholder="pageText('username_placeholder', '请输入账号')"
                :disabled="loading"
                required
                :status="error ? 'error' : 'default'"
                :described-by="error ? 'login-error' : undefined"
              >
                <template #prefix><ScIcon name="user" :size="18" /></template>
              </ScInput>
            </label>
            <label class="sc-form-label">
              {{ pageText('password_label', '密码') }}
              <ScInput
                id="login-password"
                v-model="password"
                class="sc-input"
                size="large"
                type="password"
                autocomplete="current-password"
                :placeholder="pageText('password_placeholder', '请输入密码')"
                :disabled="loading"
                required
                :status="error ? 'error' : 'default'"
                :described-by="error ? 'login-error' : undefined"
              >
                <template #prefix><ScIcon name="lock" :size="18" /></template>
              </ScInput>
            </label>
            <div v-if="passwordRecoveryAction" class="auth-form-support">
              <ScButton
                class="auth-entry-link"
                appearance="auth-link"
                type="button"
                variant="ghost"
                :disabled="loading"
                @click="executeHeaderAction(passwordRecoveryAction.key)"
              >
                {{ passwordRecoveryAction.label || passwordRecoveryAction.key }}
              </ScButton>
            </div>
            <label v-if="!dbInputDisabled" class="sc-form-label">
              {{ pageText('db_label', '数据库') }}
              <ScInput
                v-model="dbName"
                class="sc-input"
                size="large"
                autocomplete="off"
                :placeholder="pageText('db_placeholder', '请输入数据库名（如 sc_minimal）')"
                :disabled="dbInputDisabled"
              />
            </label>
            <p
              v-if="pageSectionEnabled('error', true) && pageSectionTagIs('error', 'section') && error"
              id="login-error"
              class="error sc-alert sc-alert-danger"
              role="alert"
              :style="pageSectionStyle('error')"
            >
              {{ error }}
            </p>
            <ScButton class="submit" appearance="primary-submit" variant="primary" size="large" type="submit" :disabled="loading" :loading="loading">{{ loading ? pageText('submit_loading', '系统正在登录，请稍候…') : pageText('submit_idle', '登录') }}</ScButton>
          </form>
        </ScCard>
      </section>
    </section>

    <footer class="page-footer">
      <p>{{ footerPrimary }}</p>
      <p v-if="config.appBrand.footerSecondary">{{ config.appBrand.footerSecondary }}</p>
    </footer>
  </main>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useSessionStore } from '../stores/session';
import { usePageContract } from '../app/pageContract';
import { executePageContractAction } from '../app/pageContractActionRuntime';
import { isConfiguredDbPinned, isPlatformAdminEntryRuntime, resolveConfiguredDb } from '../services/dbContext';
import { config } from '../config';
import { normalizeLegacyWorkbenchPath } from '../app/routeQuery';
import ScButton from '../components/design-system/ScButton.vue';
import ScCard from '../components/design-system/ScCard.vue';
import ScInput from '../components/design-system/ScInput.vue';
import ScIcon from '../components/design-system/ScIcon.vue';

const router = useRouter();
const route = useRoute();
const session = useSessionStore();
const pageContract = usePageContract('login');
const pageText = pageContract.text;
const pageSectionEnabled = pageContract.sectionEnabled;
const pageSectionStyle = pageContract.sectionStyle;
const pageSectionTagIs = pageContract.sectionTagIs;
const pageActionIntent = pageContract.actionIntent;
const pageActionTarget = pageContract.actionTarget;
const pageGlobalActions = pageContract.globalActions;

const username = ref('');
const password = ref('');
const dbName = ref(
  resolveConfiguredDb(String(config.odooDb || '').trim()),
);
const loading = ref(false);
const error = ref('');
const authActionKeys = new Set(['open_account_activation', 'open_password_recovery']);
const authEntryActions = computed(() => pageGlobalActions.value.filter((action) => authActionKeys.has(action.key)));
const activationAction = computed(() => authEntryActions.value.find((action) => action.key === 'open_account_activation'));
const passwordRecoveryAction = computed(() => authEntryActions.value.find((action) => action.key === 'open_password_recovery'));
const headerActions = computed(() => pageGlobalActions.value.filter((action) => !authActionKeys.has(action.key)));
const dbInputDisabled = computed(() => loading.value || isConfiguredDbPinned());
const loginTitleFallback = computed(() => isPlatformAdminEntryRuntime() ? '登录到平台管理端' : '登录到');
const brandSlogan = computed(() => pageText('brand_slogan', config.appBrand.slogan).trim());
const valueLines = computed(() => config.appBrand.valueLines.map((line, index) => pageText(`value_line_${index + 1}`, line)));
const footerPrimary = computed(() => config.appBrand.footerPrimary || `Copyright © ${new Date().getFullYear()} ${pageText('brand_name', config.appBrand.name)}`);

watch([username, password], () => {
  if (error.value) error.value = '';
});

watch(
  () => route.fullPath,
  () => {
    if (!loading.value) {
      dbName.value = resolveConfiguredDb(String(config.odooDb || '').trim());
    }
  },
);

function normalizeLoginError(err: unknown): string {
  const fallback = pageText('error_login_failed', '登录失败，请稍后重试');
  if (!(err instanceof Error)) return fallback;
  const raw = String(err.message || '').trim();
  const lower = raw.toLowerCase();
  if (!raw) return fallback;
  if (lower.includes('invalid') || lower.includes('wrong') || lower.includes('password') || lower.includes('401')) {
    return pageText('error_invalid_credentials', '账号或密码错误，请重新输入');
  }
  if (lower.includes('timeout') || lower.includes('network') || lower.includes('failed to fetch')) {
    return pageText('error_network', '网络异常，请稍后重试');
  }
  return fallback;
}

async function onSubmit() {
  error.value = '';
  loading.value = true;
  try {
    await session.login(username.value, password.value, dbName.value);
    await session.loadAppInit();
    const rawRedirect = typeof route.query.redirect === 'string' ? route.query.redirect : '';
    const isLikelyUnboundActionRoute =
      /^\/(f|a|r)\//.test(rawRedirect)
      && !/[?&](action_id|menu_id|scene_key|scene)=/.test(rawRedirect);
    const normalizedRedirect = normalizeLegacyWorkbenchPath(rawRedirect);
    const redirect = (normalizedRedirect && !isLikelyUnboundActionRoute)
      ? normalizedRedirect
      : isPlatformAdminEntryRuntime() ? '/?platform_admin=1' : session.resolveLandingPath('/');
    await router.push(redirect);
  } catch (err) {
    error.value = normalizeLoginError(err);
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
    query: {},
    onRefresh: async () => {
      error.value = '';
      username.value = '';
      password.value = '';
    },
    onFallback: async (key) => {
      if (key === 'open_account_activation') {
        await router.push('/activate-account');
        return true;
      }
      if (key === 'open_password_recovery') {
        await router.push('/password-recovery');
        return true;
      }
      if (key === 'open_landing' || key === 'open_workbench') {
        await router.push('/');
        return true;
      }
      return false;
    },
  });
  if (!handled) {
    error.value = pageText('error_login_failed', '登录失败，请稍后重试');
  }
}
</script>

<style scoped>
.login-page {
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

.login-masthead {
  position: absolute;
  z-index: var(--sc-component-login-layer-content);
  top: 14px;
  left: 24px;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  color: var(--sc-app-text-primary);
  font-size: 16px;
}

.login-masthead__mark {
  display: grid;
  width: 30px;
  height: 30px;
  place-items: center;
  border-radius: var(--sc-product-radius-control);
  background: var(--sc-semantic-surface-interactive);
  color: var(--sc-semantic-text-on-interactive);
  font-weight: 800;
}

.login-layout {
  width: 100%;
  min-height: calc(100vh - 56px);
  display: grid;
  grid-template-areas: 'auth brand';
  grid-template-columns: minmax(420px, 39vw) minmax(0, 1fr);
  gap: 0;
  align-items: stretch;
  position: relative;
  z-index: var(--sc-component-login-layer-base);
}

.brand-panel {
  grid-area: brand;
  position: relative;
  display: grid;
  min-height: calc(100vh - 56px);
  align-items: end;
  overflow: hidden;
  padding: 64px 64px 54px;
  background:
    radial-gradient(circle at 42% 44%, color-mix(in srgb, var(--sc-app-panel) 88%, transparent) 0 16%, transparent 43%),
    linear-gradient(145deg, var(--sc-app-panel) 0%, var(--sc-app-subtle-bg) 54%, var(--sc-app-info-bg) 100%);
}

.brand-panel::before {
  content: '';
  position: absolute;
  z-index: var(--sc-component-login-layer-content);
  inset: -14% auto -18% -22%;
  width: 34%;
  background: var(--sc-app-panel);
  transform: skewX(-17deg);
  transform-origin: 100% 50%;
}

.auth-panel {
  grid-area: auth;
  width: 100%;
  display: grid;
  justify-items: stretch;
  align-self: stretch;
  align-content: start;
  padding: clamp(130px, 20vh, 190px) clamp(32px, 5vw, 72px) 88px;
}

.brand-visual { position: absolute; inset: 0; overflow: hidden; }
.brand-visual__grid {
  position: absolute;
  inset: 7% -8% auto 28%;
  height: 46%;
  opacity: .34;
  transform: rotate(-8deg);
  background-image: linear-gradient(var(--sc-app-border) 1px, transparent 1px), linear-gradient(90deg, var(--sc-app-border) 1px, transparent 1px);
  background-size: 38px 38px;
}
.brand-visual__wireframe {
  position: absolute;
  z-index: var(--sc-component-login-layer-base);
  width: min(68vw, 860px);
  aspect-ratio: 1.35;
  left: -18%;
  top: 9%;
  border: 1px solid color-mix(in srgb, var(--sc-app-border) 72%, transparent);
  border-radius: 48% 52% 44% 56%;
  transform: rotate(18deg);
  box-shadow:
    inset 0 0 0 92px color-mix(in srgb, var(--sc-app-panel) 42%, transparent),
    inset 0 0 0 94px color-mix(in srgb, var(--sc-app-border) 45%, transparent);
}
.brand-visual__dashboard {
  position: absolute;
  z-index: var(--sc-component-login-layer-content);
  left: 16%;
  bottom: -7%;
  width: 72%;
  height: 48%;
  padding: 12% 9%;
  border-radius: 22px;
  background: color-mix(in srgb, var(--sc-app-panel) 84%, transparent);
  box-shadow: var(--sc-app-shadow-modal);
  transform: rotate(30deg) skewX(-7deg);
}
.brand-visual__dashboard-line {
  display: block;
  width: 72%;
  height: 12px;
  margin-bottom: 24px;
  border-radius: 999px;
  background: var(--sc-app-border);
}
.brand-visual__dashboard-line--short { width: 38%; }
.brand-visual__ring {
  position: absolute;
  z-index: var(--sc-component-login-layer-content);
  left: 17%;
  top: 18%;
  width: min(46vw, 590px);
  aspect-ratio: 1;
  border-radius: 50%;
  border: min(8vw, 106px) solid color-mix(in srgb, var(--sc-app-border) 56%, var(--sc-app-panel));
  box-shadow: var(--sc-app-shadow-modal);
}
.brand-visual__brand-cube {
  position: absolute;
  z-index: var(--sc-component-login-layer-modal);
  top: 31%;
  left: 45%;
  display: grid;
  width: 150px;
  height: 150px;
  place-items: center;
  border: 10px solid color-mix(in srgb, var(--sc-app-panel) 72%, transparent);
  border-radius: 34px;
  background: linear-gradient(145deg, var(--sc-semantic-surface-interactive), color-mix(in srgb, var(--sc-semantic-surface-interactive) 66%, white));
  color: var(--sc-semantic-text-on-interactive);
  box-shadow: 0 30px 52px color-mix(in srgb, var(--sc-semantic-surface-interactive) 30%, transparent);
  transform: rotate(30deg);
}
.brand-visual__brand-cube b { font-size: 82px; line-height: 1; transform: rotate(-30deg); }
.brand-visual__plane,
.brand-visual__orb { position: absolute; z-index: var(--sc-component-login-layer-content); box-shadow: var(--sc-app-shadow-modal); }
.brand-visual__plane { width: 280px; height: 86px; border-radius: 18px; transform: rotate(32deg); }
.brand-visual__plane--primary { z-index: var(--sc-component-login-layer-content); top: 28%; left: -1%; background: linear-gradient(135deg, var(--sc-app-info-bg), var(--sc-semantic-surface-interactive)); }
.brand-visual__plane--secondary { z-index: var(--sc-component-login-layer-content); right: 7%; bottom: 17%; background: var(--sc-app-panel); }
.brand-visual__orb { width: 116px; height: 116px; border-radius: 50%; }
.brand-visual__orb--primary { top: 39%; left: 27%; background: linear-gradient(145deg, var(--sc-semantic-surface-interactive), var(--sc-app-info-bg)); }
.brand-visual__orb--success { top: 52%; left: 19%; width: 92px; height: 92px; background: var(--sc-app-success-bg); }
.brand-visual__orb--neutral { top: 62%; left: 13%; width: 78px; height: 78px; background: var(--sc-app-panel); }
.brand-copy { position: relative; z-index: var(--sc-component-login-layer-modal); max-width: 520px; margin-left: 4%; }

.page-actions {
  width: 100%;
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  margin-bottom: 8px;
}

.auth-onboarding,
.auth-form-support {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0;
  color: var(--sc-app-text-secondary);
  font-size: 13px;
}

.auth-form-support {
  justify-content: flex-end;
  margin-top: -8px;
}

.auth-entry-link {
  padding: 6px 0;
  text-decoration: underline;
  text-underline-offset: 3px;
}

.auth-entry-link:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.ghost {
  transition: border-color 120ms ease, transform 120ms ease;
}

.ghost:hover:not(:disabled) {
  transform: translateY(-1px);
}

.login-card {
  width: 100%;
  border: 0;
  box-shadow: none;
  background: transparent;
  max-width: 400px;
}

.brand-header {
  display: grid;
  gap: 8px;
}

.product-badge {
  width: fit-content;
  padding: calc(var(--sc-component-badge-padding-y) * 1px) calc(var(--sc-component-badge-padding-x) * 1px);
  border: 1px solid var(--sc-app-border);
  border-radius: var(--sc-component-badge-radius);
  background: var(--sc-app-subtle-bg);
  color: var(--sc-app-text-secondary);
  font-size: 11px;
  letter-spacing: 0;
  font-weight: 500;
}

.brand-kicker {
  margin: 0;
  color: var(--sc-app-text-secondary);
  font-size: 12px;
  letter-spacing: 0.5px;
}

h1 {
  margin: 0;
  display: grid;
  gap: 6px;
  font-size: 16px;
  color: var(--sc-app-text-secondary);
  font-weight: 500;
  line-height: 1.3;
}

h1 strong {
  color: var(--sc-app-text-primary);
  font-size: clamp(28px, 3vw, 38px);
  font-weight: 700;
  letter-spacing: -0.03em;
}

.brand-title {
  margin: 0 0 12px;
  color: var(--sc-semantic-surface-interactive);
  font-weight: 600;
  font-size: 32px;
  line-height: 1.2;
}

.brand-subtitle,
.brand-slogan {
  margin: 0;
  color: var(--sc-app-text-secondary);
  font-size: 16px;
  line-height: 1.45;
}

.brand-slogan {
  margin-top: 20px;
  margin-bottom: 24px;
  font-size: 15px;
}

.value-list {
  margin: 2px 0 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 6px;
  color: var(--sc-app-text-secondary);
  font-size: 14px;
}

.value-list li {
  border-inline-start: 2px solid var(--sc-semantic-surface-interactive);
  padding-inline-start: 8px;
}

form {
  display: grid;
  gap: 14px;
}

label {
  display: grid;
  gap: 6px;
  font-size: 12px;
  color: var(--sc-app-text-secondary);
  font-weight: 500;
}

.submit {
  min-height: 44px;
  padding: 11px 14px;
  font-weight: 600;
  font-size: 16px;
  transition: transform 120ms ease, box-shadow 120ms ease, opacity 120ms ease;
}

.submit:hover:not(:disabled) {
  transform: translateY(-1px);
}

.error {
  font-size: 13px;
}

.page-footer {
  position: absolute;
  bottom: 24px;
  left: clamp(32px, 5vw, 72px);
  text-align: left;
  color: var(--sc-app-text-secondary);
  font-size: 12px;
  line-height: 1.45;
  z-index: var(--sc-component-login-layer-base);
}

.page-footer p {
  margin: 0;
}

@media (max-width: 920px) {
  .login-layout {
    grid-template-areas: 'auth';
    grid-template-columns: 1fr;
    gap: 18px;
  }

  .brand-panel { display: none; }

  .auth-panel {
    justify-items: stretch;
    padding-top: 96px;
  }
}

@media (max-width: 640px) {
  .login-page {
    padding: 72px 16px 56px;
    place-items: center;
  }

  .brand-panel {
    gap: 0;
    padding-left: 0;
  }

  .brand-title {
    font-size: 26px;
  }

  .brand-subtitle,
  .brand-slogan {
    font-size: 14px;
  }

  .login-card {
    border-radius: 16px;
  }

  .page-footer { left: 16px; bottom: 16px; }

  h1 {
    font-size: 19px;
  }

  .capability-strip {
    grid-template-columns: 1fr;
  }
}
</style>
