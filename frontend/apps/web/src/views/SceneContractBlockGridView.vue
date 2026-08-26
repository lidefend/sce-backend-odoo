<template>
  <section v-if="pageSectionsReady" class="scene-contract-block-grid" :style="pageSectionStyle('root')" :data-contract-sections="pageSectionsFingerprint" data-semantic-component="SceneContractBlockGridView" :data-state="status">
    <StatusPanel v-if="status === 'loading'" title="正在加载场景..." variant="info" />
    <StatusPanel v-else-if="status === 'error'" title="场景加载失败" :message="errorMessage" variant="error" />
    <PageRenderer
      v-else
      :contract="pageContract"
      :datasets="datasets"
      @action="handleAction"
    />
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import type { NavNode } from '@sc/schema';
import { intentRequest } from '../api/intents';
import StatusPanel from '../components/StatusPanel.vue';
import PageRenderer from '../components/page/PageRenderer.vue';
import { useSessionStore } from '../stores/session';
import { getSceneByKey } from '../app/resolvers/sceneRegistry';
import type { PageBlockActionEvent, PageOrchestrationContract } from '../app/pageOrchestration';
import { usePageContract } from '../app/pageContract';

type SceneBlock = Record<string, unknown> & {
  key?: string;
  type?: string;
  title?: string;
  subtitle?: string;
  value?: unknown;
  items?: Array<Record<string, unknown>>;
  target?: Record<string, unknown>;
};

type SceneContract = {
  schema_version?: string;
  scene?: Record<string, unknown>;
  title?: string;
  summary?: Record<string, unknown>;
  summary_rows?: Array<Record<string, unknown>>;
  blocks?: SceneBlock[];
  page?: {
    layout?: string;
    blocks?: SceneBlock[];
  };
  page_orchestration?: PageOrchestrationContract;
  datasets?: Record<string, unknown>;
};

const props = defineProps<{
  intent: string;
  sceneKey: string;
}>();

const route = useRoute();
const router = useRouter();
const session = useSessionStore();
const runtimePageContract = usePageContract('scene_contract_block_grid');
const pageSectionEnabled = runtimePageContract.sectionEnabled;
const pageSectionStyle = runtimePageContract.sectionStyle;
const pageSectionTagIs = runtimePageContract.sectionTagIs;
const pageSectionsReady = computed(() => (
  pageSectionEnabled('root', true)
  && pageSectionEnabled('main', true)
  && pageSectionTagIs('root', 'section')
  && pageSectionTagIs('main', 'section')
));
const pageSectionsFingerprint = computed(() => JSON.stringify([
  pageSectionStyle('main'),
]));
const status = ref<'loading' | 'error' | 'idle'>('loading');
const errorMessage = ref('');
const rawContract = ref<SceneContract | null>(null);

function asText(value: unknown) {
  return String(value || '').trim();
}

function parseRouteTarget(rawRoute: string) {
  const raw = asText(rawRoute);
  if (!raw) return null;
  const [path, queryRaw] = raw.split('?', 2);
  const query: Record<string, string> = {};
  if (queryRaw) {
    const params = new URLSearchParams(queryRaw);
    params.forEach((value, key) => {
      if (key) query[key] = value;
    });
  }
  return { path: path || raw, query };
}

function positiveRouteInt(...keys: string[]) {
  for (const key of keys) {
    const parsed = Number(route.query[key] || 0);
    if (Number.isFinite(parsed) && parsed > 0) return Math.trunc(parsed);
  }
  return 0;
}

function targetActionKey(blockKey: string) {
  return `open_${blockKey}`;
}

const blocks = computed(() => {
  const page = rawContract.value?.page;
  const pageBlocks = Array.isArray(page?.blocks) ? page.blocks : [];
  const rootBlocks = Array.isArray(rawContract.value?.blocks) ? rawContract.value.blocks : [];
  const summaryRows = Array.isArray(rawContract.value?.summary_rows) ? rawContract.value.summary_rows : [];
  const summaryBlocks: SceneBlock[] = summaryRows.map((row, index) => ({
    key: asText(row.key) || `summary_${index + 1}`,
    type: 'metric_card',
    title: asText(row.label) || asText(row.key) || `指标 ${index + 1}`,
    subtitle: asText(row.copy),
    value: row.value ?? '--',
    tone: 'neutral',
  }));
  return [...summaryBlocks, ...(pageBlocks.length ? pageBlocks : rootBlocks)];
});

const pageContract = computed<PageOrchestrationContract>(() => {
  const contract = rawContract.value?.page_orchestration;
  if (!contract || contract.contract_version !== '2.0.0' || contract.schema_version !== '2.0.0') return {};
  return contract;
});

const datasets = computed<Record<string, unknown>>(() => rawContract.value?.datasets || {});

function findActionNodeByXmlid(nodes: NavNode[], xmlid: string): NavNode | null {
  const wanted = asText(xmlid);
  if (!wanted) return null;
  for (const node of nodes) {
    const nodeXmlid = asText(node.meta?.action_xmlid);
    if (nodeXmlid === wanted && node.meta?.action_id) return node;
    if (node.children?.length) {
      const found = findActionNodeByXmlid(node.children, wanted);
      if (found) return found;
    }
  }
  return null;
}

function findMenuNodeByXmlid(nodes: NavNode[], xmlid: string): NavNode | null {
  const wanted = asText(xmlid);
  if (!wanted) return null;
  for (const node of nodes) {
    const nodeXmlid = asText((node as NavNode & { xmlid?: string }).xmlid || node.meta?.menu_xmlid);
    if (nodeXmlid === wanted) return node;
    if (node.children?.length) {
      const found = findMenuNodeByXmlid(node.children, wanted);
      if (found) return found;
    }
  }
  return null;
}

function findTargetByActionKey(actionKey: string) {
  for (const block of blocks.value) {
    const blockKey = asText(block.key);
    if (targetActionKey(blockKey) === actionKey) {
      return block.target && typeof block.target === 'object' ? block.target : {};
    }
    const items = Array.isArray(block.items) ? block.items : [];
    for (let index = 0; index < items.length; index += 1) {
      const item = items[index] || {};
      const itemActionKey = targetActionKey(`${blockKey}_${asText(item.key) || index + 1}`);
      if (itemActionKey === actionKey) {
        return item.target && typeof item.target === 'object' ? item.target : {};
      }
    }
  }
  return {};
}

async function openTarget(target: Record<string, unknown>) {
  const sceneKey = asText(target.scene_key || target.sceneKey);
  if (sceneKey) {
    const scene = getSceneByKey(sceneKey);
    const rawRoute = asText(target.route || scene?.target?.route || scene?.route || `/s/${sceneKey}`);
    const parsed = parseRouteTarget(rawRoute);
    if (parsed) {
      await router.push({ path: parsed.path, query: { ...route.query, ...parsed.query } });
      return true;
    }
  }
  const routePath = asText(target.route);
  if (routePath) {
    const parsed = parseRouteTarget(routePath);
    await router.push({
      path: parsed?.path || routePath,
      query: {
        ...route.query,
        ...(parsed?.query || {}),
      },
    });
    return true;
  }
  const actionXmlid = asText(target.action_xmlid);
  const actionNode = findActionNodeByXmlid(session.menuTree, actionXmlid);
  if (actionNode?.meta?.action_id) {
    await router.push({
      path: `/a/${actionNode.meta.action_id}`,
      query: {
        action_id: String(actionNode.meta.action_id),
        menu_id: actionNode.menu_id ? String(actionNode.menu_id) : undefined,
      },
    });
    return true;
  }
  const menuXmlid = asText(target.menu_xmlid);
  const menuNode = findMenuNodeByXmlid(session.menuTree, menuXmlid);
  if (menuNode?.meta?.action_id) {
    await router.push({
      path: `/a/${menuNode.meta.action_id}`,
      query: {
        action_id: String(menuNode.meta.action_id),
        menu_id: menuNode.menu_id ? String(menuNode.menu_id) : undefined,
      },
    });
    return true;
  }
  if (menuNode?.menu_id) {
    await router.push({ path: `/m/${menuNode.menu_id}` });
    return true;
  }
  return false;
}

async function handleAction(event: PageBlockActionEvent) {
  const itemTarget = event.item?.target && typeof event.item.target === 'object' ? event.item.target as Record<string, unknown> : {};
  const eventTarget = event.target && Object.keys(event.target).length ? event.target : {};
  const target = Object.keys(eventTarget).length
    ? eventTarget
    : Object.keys(itemTarget).length
      ? itemTarget
      : findTargetByActionKey(event.actionKey);
  await openTarget((target || {}) as Record<string, unknown>);
}

async function loadContract() {
  try {
    status.value = 'loading';
    errorMessage.value = '';
    const data = await intentRequest<SceneContract>({
      intent: props.intent,
      params: {
        record_id: positiveRouteInt('record_id') || undefined,
      },
      context: {
        scene_key: props.sceneKey,
        record_id: positiveRouteInt('record_id') || undefined,
      },
    });
    rawContract.value = (data && typeof data === 'object') ? data : {};
    status.value = 'idle';
  } catch (err) {
    errorMessage.value = err instanceof Error ? err.message : 'unknown error';
    status.value = 'error';
  }
}

watch(
  () => [props.intent, props.sceneKey, route.fullPath],
  () => {
    void loadContract();
  },
  { immediate: true },
);
</script>

<style scoped>
.scene-contract-block-grid {
  display: grid;
  gap: 12px;
  padding: 12px;
}
</style>
