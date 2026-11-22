<template>
  <ScPage
    class="page"
    data-semantic-component="RouteErrorView"
    data-state="error"
    :data-route-error-kind="failureKind"
    :data-route-error-status="status || undefined"
    :data-trace-id="traceId || undefined"
  >
    <ScPageHeader :title="presentation.title" />
    <ScErrorState title="请求处理结果" :description="description">
      <template #actions>
        <ScButton variant="primary" :disabled="!from" title="没有可重试的页面" @click="retry">重试</ScButton>
        <ScButton variant="secondary" @click="returnSafely">返回安全页面</ScButton>
      </template>
    </ScErrorState>
  </ScPage>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import ScButton from '../components/design-system/ScButton.vue';
import ScErrorState from '../components/design-system/ScErrorState.vue';
import ScPage from '../components/design-system/ScPage.vue';
import ScPageHeader from '../components/design-system/ScPageHeader.vue';
import { routeFailurePresentation, type RouteFailureKind } from '../app/routeFailure';

const route = useRoute();
const router = useRouter();

function queryText(value: unknown): string {
  return String(Array.isArray(value) ? value[0] || '' : value || '').trim();
}

const failureKind = computed<RouteFailureKind>(() => {
  const value = queryText(route.query.kind);
  return ['conflict', 'service', 'network'].includes(value)
    ? value as RouteFailureKind
    : 'unknown';
});
const presentation = computed(() => routeFailurePresentation(failureKind.value));
const reasonCode = computed(() => queryText(route.query.reason));
const traceId = computed(() => queryText(route.query.trace_id));
const status = computed(() => {
  const parsed = Number(queryText(route.query.status));
  return Number.isInteger(parsed) && parsed > 0 ? parsed : 0;
});
const from = computed(() => queryText(route.query.from));
const description = computed(() => [
  presentation.value.message,
  status.value ? `HTTP ${status.value}` : '',
  reasonCode.value ? `原因：${reasonCode.value}` : '',
  traceId.value ? `追踪 ID：${traceId.value}` : '',
].filter(Boolean).join(' · '));

function retry(): void {
  if (from.value) void router.push(from.value);
}

function returnSafely(): void {
  void router.push('/');
}
</script>
