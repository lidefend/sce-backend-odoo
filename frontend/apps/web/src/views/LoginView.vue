<template>
  <main class="login-page sc-page" data-semantic-component="LoginView" :data-state="loading ? 'loading' : error ? 'error' : 'ready'" :aria-busy="loading || undefined">
    <section class="login-layout">
      <section class="brand-panel" aria-label="平台介绍">
        <p class="brand-title">{{ pageText('brand_name', config.appBrand.name) }}</p>
        <p class="brand-subtitle">{{ pageText('brand_subtitle', config.appBrand.subtitle) }}</p>
        <p v-if="brandSlogan" class="brand-slogan">{{ brandSlogan }}</p>

        <ul v-if="valueLines.length" class="value-list" aria-label="价值主张">
          <li v-for="line in valueLines" :key="line">{{ line }}</li>
        </ul>
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
          :style="pageSectionStyle('card')"
        >
          <header class="brand-header">
            <span v-if="config.appBrand.productBadge" class="product-badge">{{ config.appBrand.productBadge }}</span>
            <p v-if="config.appBrand.kicker" class="brand-kicker">{{ config.appBrand.kicker }}</p>
            <h1>{{ pageText('title', loginTitleFallback) }}</h1>
          </header>

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
              />
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
              />
            </label>
            <label class="sc-form-label">
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
          <nav v-if="authEntryActions.length" class="auth-entry-links" aria-label="账号帮助">
            <ScButton
              v-for="action in authEntryActions"
              :key="`login-auth-${action.key}`"
              class="auth-entry-link"
              appearance="auth-link"
              type="button"
              variant="ghost"
              :disabled="loading"
              @click="executeHeaderAction(action.key)"
            >
              {{ action.label || action.key }}
            </ScButton>
          </nav>
        </ScCard>
      </section>
    </section>

    <footer v-if="config.appBrand.footerPrimary || config.appBrand.footerSecondary" class="page-footer">
      <p v-if="config.appBrand.footerPrimary">{{ config.appBrand.footerPrimary }}</p>
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
const headerActions = computed(() => pageGlobalActions.value.filter((action) => !authActionKeys.has(action.key)));
const dbInputDisabled = computed(() => loading.value || isConfiguredDbPinned());
const loginTitleFallback = computed(() => isPlatformAdminEntryRuntime() ? '平台管理员登录' : '登录');
const brandSlogan = computed(() => pageText('brand_slogan', config.appBrand.slogan).trim());
const valueLines = computed(() => config.appBrand.valueLines.map((line, index) => pageText(`value_line_${index + 1}`, line)));

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
  --ink: var(--sc-app-text-primary);
  --muted: var(--sc-app-text-secondary);
  --accent: var(--sc-semantic-surface-interactive);
  min-height: 100vh;
  display: grid;
  place-items: center;
  gap: 18px;
  background: var(--sc-app-bg);
  color: var(--ink);
  font-family: "Space Grotesk", "IBM Plex Sans", system-ui, sans-serif;
  padding: 30px 16px;
  position: relative;
  overflow: hidden;
}

.login-layout {
  width: min(1180px, 100%);
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(360px, 420px);
  gap: clamp(28px, 5vw, 80px);
  align-items: center;
  position: relative;
  z-index: 1;
}

.brand-panel {
  display: grid;
  gap: 0;
  max-width: 620px;
  padding-left: clamp(20px, 4.5vw, 60px);
}

.auth-panel {
  width: 100%;
  display: grid;
  justify-items: end;
}

.page-actions {
  width: 100%;
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  margin-bottom: 8px;
}

.auth-entry-links {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-top: 16px;
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
  font-size: 20px;
  color: var(--sc-app-text-secondary);
  font-weight: 500;
}

.brand-title {
  margin: 0 0 12px;
  color: var(--accent);
  font-weight: 600;
  font-size: 32px;
  line-height: 1.2;
}

.brand-subtitle,
.brand-slogan {
  margin: 0;
  color: var(--muted);
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
  text-align: center;
  color: var(--sc-app-text-secondary);
  font-size: 12px;
  line-height: 1.45;
  position: relative;
  z-index: 1;
}

.page-footer p {
  margin: 0;
}

@media (max-width: 920px) {
  .login-layout {
    grid-template-columns: 1fr;
    gap: 18px;
  }

  .auth-panel {
    justify-items: stretch;
  }
}

@media (max-width: 640px) {
  .login-page {
    padding: 16px 10px 18px;
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

  h1 {
    font-size: 19px;
  }

  .capability-strip {
    grid-template-columns: 1fr;
  }
}
</style>
