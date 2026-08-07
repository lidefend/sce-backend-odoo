<template>
  <RouterView v-slot="{ Component, route }">
    <AppShell v-if="route.meta?.layout === 'shell'">
      <KeepAlive :max="6">
        <component
          :is="Component"
          v-if="activityCacheKey(route)"
          :key="activityCacheKey(route)"
        />
      </KeepAlive>
      <component
        :is="Component"
        v-if="!activityCacheKey(route)"
        :key="route.fullPath"
      />
    </AppShell>
    <component :is="Component" v-else />
  </RouterView>
</template>

<script setup lang="ts">
import { watch } from 'vue';
import type { RouteLocationNormalizedLoaded } from 'vue-router';
import { PRODUCT_APP_TITLE } from './app/pageIdentity';
import { usePageIdentityRuntime } from './app/pageIdentityRuntime';
import AppShell from './layouts/AppShell.vue';
import { useSessionStore } from './stores/session';

const session = useSessionStore();
const pageIdentity = usePageIdentityRuntime();

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

function positiveInteger(value: unknown): number {
  const parsed = Number(value || 0);
  if (!Number.isFinite(parsed) || parsed <= 0) return 0;
  return Math.trunc(parsed);
}

function activityContextPart(): string {
  const selectedId = Number(session.recordContext?.selected?.id || 0) || 0;
  return selectedId > 0 ? `record-context:${selectedId}` : 'all';
}

function activityRouteKey(route: RouteLocationNormalizedLoaded): string {
  if (route.name === 'action') {
    const actionId = positiveInteger(route.params.actionId || route.query.action_id);
    const menuId = positiveInteger(route.query.menu_id);
    return actionId ? `action:${actionId}:menu:${menuId || 0}:${activityContextPart()}` : '';
  }
  if (route.name === 'record' || route.name === 'model-form') {
    const model = routeText(route.params.model);
    const recordId = routeText(route.params.id);
    if (!model || !recordId) return '';
    const actionId = positiveInteger(route.query.action_id);
    const menuId = positiveInteger(route.query.menu_id);
    const viewId = positiveInteger(route.query.view_id || route.query.viewId);
    if (recordId === 'new') {
      const activityInstanceId = routeText(route.query.activity_page_id);
      return `new:${model}:action:${actionId || 0}:menu:${menuId || 0}:view:${viewId || 0}:${activityContextPart()}:${activityInstanceId || 'route'}`;
    }
    // A persisted record id already identifies the activity page. Including the
    // A live selected-record projection makes the KeepAlive key change during
    // route registration, remounting RecordView and duplicating all first-load
    // business requests. Company/scope transitions invalidate cache epochs.
    return `record:${model}:${recordId}:action:${actionId || 0}:menu:${menuId || 0}`;
  }
  if (route.name === 'scene' || String(route.name || '').startsWith('scene-')) {
    const sceneKey = routeText(route.params.sceneKey || route.meta?.sceneKey || route.query.scene_key || route.query.scene);
    if (!sceneKey || sceneKey === 'workspace.home') return '';
    return `scene:${sceneKey}:${activityContextPart()}`;
  }
  if (route.name === 'my-work' || route.name === 'scene-my-work') return 'workspace:my-work';
  return '';
}

function activityCacheKey(route: RouteLocationNormalizedLoaded): string {
  const routeKey = activityRouteKey(route);
  if (!routeKey) return '';
  const epoch = Number(session.activityPageCacheEpochs[routeKey] || 0);
  return `activity:${routeKey}:${epoch}`;
}
</script>
