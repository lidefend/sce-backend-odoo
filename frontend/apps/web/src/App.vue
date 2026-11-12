<template>
  <TDesignConfigProvider :global-config="tdesignGlobalConfig">
    <ScPanel v-if="isPublicAuthPage && !session.token && session.publicPageContractStatus === 'error'" role="alert">
      账号入口配置加载失败，请重试。
      <ScButton @click="session.loadPublicPageContracts(true)">重试加载</ScButton>
    </ScPanel>
    <ScPanel v-else-if="isPublicAuthPage && !session.token && session.publicPageContractStatus === 'loading'" role="status">
      正在加载账号入口…
    </ScPanel>
    <RouterView v-slot="{ Component, route: slotRoute }">
      <AppShell
        v-if="shellComposition.adopted"
        :data-shell-composition="shellComposition.composition"
        :data-shell-composition-reason="shellComposition.reason"
      >
        <KeepAlive :max="6">
          <component
            :is="Component"
            v-if="activityCacheKey(slotRoute)"
            :key="activityCacheKey(slotRoute)"
          />
        </KeepAlive>
        <component
          :is="Component"
          v-if="!activityCacheKey(slotRoute)"
          :key="slotRoute.fullPath"
        />
      </AppShell>
      <component :is="Component" v-else />
    </RouterView>
  </TDesignConfigProvider>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useRoute, type RouteLocationNormalizedLoaded } from 'vue-router';
import { resolveStandardShellComposition } from './app/presentation/standardShellComposition';
import { PRODUCT_APP_TITLE } from './app/pageIdentity';
import { usePageIdentityRuntime } from './app/pageIdentityRuntime';
import { TDesignConfigProvider } from './components/design-system/tdesignPrimitiveBridge';
import AppShell from './layouts/AppShell.vue';
import ScPanel from './components/design-system/ScPanel.vue';
import ScButton from './components/design-system/ScButton.vue';
import { useSessionStore } from './stores/session';
import { tdesignGlobalConfig } from './styles/tdesignGlobalConfig';
import { useThemeApplicationRuntime } from './styles/themeApplicationRuntime';
import { resolveActivityRouteKey } from './app/activityPageCacheIdentity';

const session = useSessionStore();
const pageIdentity = usePageIdentityRuntime();
const retainedActivityActorId = ref(0);

useThemeApplicationRuntime();

const route = useRoute();
const isPublicAuthPage = computed(() => ['login', 'platform-admin-login', 'account-activation', 'password-recovery'].includes(String(route.name || '')));
watch([isPublicAuthPage, () => session.token], ([isPublic, token]) => {
  if (isPublic && !token) void session.loadPublicPageContracts();
}, { immediate: true });

// The shell adoption decision is a pure presentation policy, resolved here so
// the shell gate and its published identity cannot drift apart. A route that is
// not adopted renders its page component exactly as it did before.
const shellComposition = computed(() => resolveStandardShellComposition({
  layout: route.meta?.layout,
  embeddedRelationDialog: isEmbeddedRelationDialog(route),
}));

watch(
  () => positiveInteger(session.user?.id),
  (userId) => {
    // clearSession() runs before the router leaves a protected page. Retain
    // the last authenticated actor through that short transition so logout
    // cannot remount the current record under an anonymous cache key.
    if (userId > 0) retainedActivityActorId.value = userId;
  },
  { immediate: true },
);

watch(
  [() => pageIdentity.identity.value.documentTitle, () => session.token],
  ([documentTitle, token]) => {
    document.title = token ? documentTitle : `登录 - ${PRODUCT_APP_TITLE}`;
  },
  { immediate: true },
);

function routeText(value: unknown): string {
  if (Array.isArray(value)) return String(value[0] || '').trim();
  return String(value || '').trim();
}

function isEmbeddedRelationDialog(route: RouteLocationNormalizedLoaded): boolean {
  return routeText(route.query.relation_create_mode) === 'dialog'
    && Boolean(routeText(route.query.relation_dialog_nonce));
}

function positiveInteger(value: unknown): number {
  const parsed = Number(value || 0);
  if (!Number.isFinite(parsed) || parsed <= 0) return 0;
  return Math.trunc(parsed);
}

function activityActorPart(): string {
  return `user:${retainedActivityActorId.value || 0}`;
}

function activityRouteKey(route: RouteLocationNormalizedLoaded): string {
  return resolveActivityRouteKey({
    routeName: route.name,
    params: route.params,
    query: route.query,
    meta: route.meta,
    selectedRecordId: session.recordContext?.selected?.id,
  });
}

function activityCacheKey(route: RouteLocationNormalizedLoaded): string {
  const routeKey = activityRouteKey(route);
  if (!routeKey) return '';
  const epoch = Number(session.activityPageCacheEpochs[routeKey] || 0);
  return `activity:${activityActorPart()}:${routeKey}:${epoch}`;
}
</script>
