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

const blocks = computed<SceneBlock[]>(() => {
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
  const stubBlocks: SceneBlock[] = (pageBlocks.length ? pageBlocks : rootBlocks).map((stub) => {
    const key = asText(stub.key);
    const payload = key ? runtimeBlocks.value[key] : undefined;
    return payload ? mergeRuntimeBlock(stub, payload) : stub;
  });
  return [...summaryBlocks, ...stubBlocks];
});

type RuntimeFetchHint = {
  intent?: string;
  params?: Record<string, unknown>;
  project_id?: number;
  block_key?: string;
};

const runtimeBlocks = ref<Record<string, Record<string, unknown>>>({});

function asHint(value: unknown): RuntimeFetchHint | null {
  if (!value || typeof value !== 'object') return null;
  return value as RuntimeFetchHint;
}

async function fetchRuntimeBlock(
  key: string,
  hint: RuntimeFetchHint | null,
): Promise<Record<string, unknown> | null> {
  const intent = String(hint?.intent || '').trim();
  if (!intent) return null;
  const projectId = Number(hint?.project_id || 0) || positiveRouteInt('project_id') || 0;
  const blockKey = String(hint?.block_key || key).trim() || key;
  const params: Record<string, unknown> = {
    block_key: blockKey,
    ...(projectId > 0 ? { project_id: projectId } : {}),
    ...(hint?.params || {}),
  };
  const data = await intentRequest<{ block?: Record<string, unknown> }>({
    intent,
    params,
    context: {
      scene_key: props.sceneKey,
      ...(projectId > 0 ? { project_id: projectId } : {}),
    },
  });
  return data?.block && typeof data.block === 'object' ? data.block : null;
}

async function hydrateDeferredBlocks(): Promise<void> {
  runtimeBlocks.value = {};
  const contract = rawContract.value;
  if (!contract) return;
  const hints = (contract.runtime_fetch_hints &&
    typeof contract.runtime_fetch_hints === 'object' &&
    (contract.runtime_fetch_hints as Record<string, unknown>).blocks &&
    typeof (contract.runtime_fetch_hints as Record<string, unknown>).blocks === 'object'
  ) ? (contract.runtime_fetch_hints as Record<string, unknown>).blocks as Record<string, unknown> : {};
  const entries = Array.isArray(contract.blocks) ? contract.blocks : [];
  for (const block of entries) {
    const key = asText(block?.key);
    if (!key) continue;
    const state = asText(block?.state).toLowerCase();
    if (state && state !== 'deferred') continue;
    const hint = asHint(hints[key]);
    if (!hint) continue;
    try {
      const payload = await fetchRuntimeBlock(key, hint);
      if (payload) {
        runtimeBlocks.value = { ...runtimeBlocks.value, [key]: payload };
      }
    } catch (err) {
      // Fail-soft: a missing runtime block must not break the rest of the
      // scene contract rendering. Surface it under the entry's stub title.
      runtimeBlocks.value = { ...runtimeBlocks.value, [key]: {
        block_key: String(hint?.block_key || key),
        block_type: 'runtime_block_error',
        title: asText(block?.title) || key,
        state: 'error',
        error: err instanceof Error ? { message: err.message } : { message: 'fetch failed' },
      } };
    }
  }
}

function mergeRuntimeBlock(stub: SceneBlock, payload: Record<string, unknown> | undefined): SceneBlock {
  if (!payload) return stub;
  return {
    ...stub,
    ...payload,
    data: (payload as { data?: unknown }).data ?? (stub as { data?: unknown }).data,
    block_type: String(payload.block_type || (stub as { block_type?: string }).block_type || 'runtime_block'),
  } as SceneBlock;
}

const pageContract = computed<PageOrchestrationContract>(() => {
  const contract = rawContract.value?.page_orchestration;
  if (contract && contract.contract_version === '2.0.0' && contract.schema_version === '2.0.0') {
    return contract;
  }
  // Synthesize a v2 page orchestration contract from a scene entry contract
  // (entry response shape: title/summary/blocks + runtime_fetch_hints). This
  // lets PageRenderer present deferred blocks once their payloads arrive.
  const sceneTitle = asText(rawContract.value?.title) || props.sceneKey;
  const summaryRows = (rawContract.value?.summary_rows && Array.isArray(rawContract.value.summary_rows))
    ? rawContract.value.summary_rows
    : [];
  const entryBlocks = Array.isArray(rawContract.value?.blocks) ? (rawContract.value?.blocks || []) : [];
  const blocks: SceneBlock[] = summaryRows.map((row, index) => ({
    key: asText((row as Record<string, unknown>).key) || `summary_${index + 1}`,
    block_type: 'metric_card',
    title: asText((row as Record<string, unknown>).label) || asText((row as Record<string, unknown>).key) || `指标 ${index + 1}`,
    subtitle: asText((row as Record<string, unknown>).copy),
    value: (row as Record<string, unknown>).value ?? '--',
    tone: 'neutral',
  }));
  for (const stub of entryBlocks) {
    const key = asText((stub as Record<string, unknown>).key);
    if (!key) continue;
    const payload = runtimeBlocks.value[key];
    const merged = mergeRuntimeBlock(stub as SceneBlock, payload);
    // 运行时块（progress/risk/boq/next_actions）的 data 需经 ZoneRenderer 的
    // data_source 透传到组件 dataset 投影；无显式 data_source 时以 entry key 兜底。
    if (payload && !asText(merged.data_source)) {
      (merged as SceneBlock).data_source = key;
    }
    blocks.push(merged);
  }
  return {
    contract_version: '2.0.0',
    schema_version: '2.0.0',
    scene_key: props.sceneKey,
    page: {
      key: props.sceneKey,
      title: sceneTitle,
      page_type: 'dashboard',
      layout_mode: 'block_grid',
    },
    zones: [
      {
        key: 'primary',
        title: sceneTitle,
        zone_type: 'primary',
        display_mode: 'stack',
        priority: 100,
        blocks,
      },
    ],
  };
});

// 运行时块投影：key -> payload.data。ZoneRenderer 依据 blocked.data_source
// 从 datasets 取投影，让 progress/risk/boq/next_actions 呈现真实数据而非空态。
const runtimeDatasets = computed<Record<string, unknown>>(() => {
  const out: Record<string, unknown> = {};
  for (const [key, payload] of Object.entries(runtimeBlocks.value)) {
    const data = payload && typeof payload === 'object' ? (payload as { data?: unknown }).data : undefined;
    if (data && typeof data === 'object') out[key] = data;
  }
  return out;
});

const datasets = computed<Record<string, unknown>>(() => ({
  ...(rawContract.value?.datasets || {}),
  ...runtimeDatasets.value,
}));

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
        project_id: positiveRouteInt('project_id') || undefined,
      },
      context: {
        scene_key: props.sceneKey,
        record_id: positiveRouteInt('record_id') || undefined,
        project_id: positiveRouteInt('project_id') || undefined,
      },
    });
    rawContract.value = (data && typeof data === 'object') ? data : {};
    await hydrateDeferredBlocks();
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
