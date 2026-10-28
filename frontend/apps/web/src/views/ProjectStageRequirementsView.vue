<template>
  <ScPage data-semantic-component="ProjectStageRequirementsView">
    <ScLoading v-if="loading" />
    <StatusPanel v-else-if="error" title="" variant="error" :error-code="error.status" :reason-code="error.reason" :trace-id="error.trace" :on-retry="load" />
    <ScCard v-else-if="data">
      <header class="requirements-header">
        <h1>{{ data.title }}</h1>
        <ScButton type="button" variant="secondary" @click="back">{{ data.labels.back }}</ScButton>
      </header>
      <dl>
        <dt>{{ data.labels.project }}</dt><dd>{{ data.project.name }}</dd>
        <dt>{{ data.labels.stage }}</dt><dd>{{ data.stage.label }}</dd>
      </dl>
      <ScInlineState v-if="data.items.length === 0" state="empty" :label="data.labels.empty" />
      <ul v-else class="requirements-list">
        <li v-for="(item, index) in data.items" :key="index">
          <strong>{{ item.title }}</strong>
          <span>{{ item.required ? data.labels.required : data.labels.optional }}</span>
          <span>{{ item.done ? data.labels.done : data.labels.pending }}</span>
        </li>
      </ul>
    </ScCard>
  </ScPage>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import ScPage from '../components/design-system/ScPage.vue';
import ScCard from '../components/design-system/ScCard.vue';
import ScButton from '../components/design-system/ScButton.vue';
import ScLoading from '../components/design-system/ScLoading.vue';
import ScInlineState from '../components/design-system/ScInlineState.vue';
import StatusPanel from '../components/StatusPanel.vue';
import { ApiError } from '../api/client';
import { readProjectStageRequirements, type StageRequirements } from '../api/projectStageRequirements';
import { currentContextEpoch } from '../app/contextEpoch';
import { useSessionStore } from '../stores/session';
import { usePublishedPageIdentity } from '../app/usePublishedPageIdentity';

const session = useSessionStore();
const route = useRoute();
const router = useRouter();
const data = ref<StageRequirements | null>(null);
const loading = ref(true);
const error = ref<{ status: number | null; reason: string; trace: string } | null>(null);
usePublishedPageIdentity(computed(() => ({
  kind: 'page' as const, actionName: data.value?.title,
  subtitle: data.value?.project.name,
})), { routeKey: () => route.fullPath, active: () => Boolean(data.value) });
let generation = 0;
async function load() {
  const ticket = ++generation;
  const epoch = currentContextEpoch();
  data.value = null;
  error.value = null;
  loading.value = true;
  try {
    const result = await readProjectStageRequirements(Number(route.params.projectId));
    if (ticket === generation && epoch === currentContextEpoch()) data.value = result;
  } catch (e) {
    if (ticket !== generation || epoch !== currentContextEpoch()) return;
    error.value = e instanceof ApiError
      ? { status: e.status, reason: e.reasonCode || '', trace: e.traceId || '' }
      : { status: null, reason: '', trace: '' };
  } finally {
    if (ticket === generation && epoch === currentContextEpoch()) loading.value = false;
  }
}
function back() {
  if (!data.value) return;
  if (window.history.state?.back) router.back();
  else void router.replace(data.value.return_path);
}
watch(() => [route.params.projectId, session.token, session.user?.id, JSON.stringify(session.recordContext)], load, { immediate: true, flush: 'post' });
onBeforeUnmount(() => { generation += 1; });
</script>

<style scoped>
.requirements-header { display: flex; align-items: center; justify-content: space-between; gap: 1rem; }
dl { display: grid; grid-template-columns: auto 1fr; gap: .5rem 1rem; }
dd { margin: 0; overflow-wrap: anywhere; }
.requirements-list { padding-inline-start: 1.5rem; }
.requirements-list li { display: flex; flex-wrap: wrap; gap: .75rem; padding-block: .75rem; }
.requirements-list strong { flex: 1 1 15rem; overflow-wrap: anywhere; }
</style>
