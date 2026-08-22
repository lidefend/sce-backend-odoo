<template>
  <div class="scene-runtime">
    <section class="scene-header">
      <div class="scene-header__copy">
        <span class="scene-header__type">业务场景</span>
        <h1>{{ title }}</h1>
        <p v-if="description">{{ description }}</p>
      </div>
      <t-space size="small" break-line>
        <t-button
          v-for="action in headerActions"
          :key="actionKey(action)"
          :theme="action.tier === 'primary' ? 'primary' : 'default'"
          :variant="action.tier === 'primary' ? 'base' : 'outline'"
          :loading="busyAction === actionKey(action)"
          @click="runAction(action)"
        >
          {{ actionLabel(action) }}
        </t-button>
        <t-button variant="outline" :loading="loading" @click="load">
          <template #icon><t-icon name="refresh" /></template>
          刷新
        </t-button>
      </t-space>
    </section>

    <t-alert v-if="error" theme="error" :message="error" />
    <suggested-action-bar
      v-if="error"
      :action="suggestedAction"
      :trace-id="errorTraceId"
      :reason-code="errorReasonCode"
      :message="error"
      :on-retry="load"
    />
    <t-alert v-if="diagnosticsMessage" theme="info" :message="diagnosticsMessage" />
    <t-alert v-if="sceneAccessDenied" theme="error" message="当前账号无权访问该业务场景" />
    <t-alert
      v-for="diagnostic in zoneDiagnostics"
      :key="`${diagnostic.zone}:${diagnostic.reasonCode}`"
      theme="warning"
      :message="`${diagnostic.zone} 存在未声明类型的场景区块（${diagnostic.reasonCode}）`"
    />

    <div v-if="loading" class="scene-loading">
      <t-loading size="small" text="正在加载场景数据" />
    </div>

    <template v-else-if="!sceneAccessDenied">
      <section
        v-for="zone in renderedZones"
        :key="zone.key"
        class="scene-zone"
        :class="[`scene-zone--${safeClass(zone.zoneType)}`, `scene-zone--${safeClass(zone.displayMode)}`]"
      >
        <header v-if="zone.title || zone.description" class="scene-zone__header">
          <h2 v-if="zone.title">{{ zone.title }}</h2>
          <p v-if="zone.description">{{ zone.description }}</p>
        </header>
        <div class="scene-zone__body">
          <scene-block-runtime
            v-for="block in zone.blocks"
            :key="String(block.key)"
            :block="block"
            @action="runAction"
          />
        </div>
      </section>
      <t-empty v-if="!renderedZones.length" description="当前场景暂无可展示内容" />
    </template>
  </div>
</template>
<script setup lang="ts">
import { MessagePlugin } from 'tdesign-vue-next';
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { intent, OdooApiError } from '@/api/odoo';
import SuggestedActionBar from '@/components/result/SuggestedActionBar.vue';

import {
  normalizeSceneBlockKind,
  resolveSceneBlockRegistryEntry,
  sceneBlockReasonCode,
} from './scene/sceneBlockRegistry';
import SceneBlockRuntime from './scene/SceneBlockRuntime.vue';

type Dict = Record<string, any>;

const route = useRoute();
const router = useRouter();
const loading = ref(false);
const error = ref('');
const errorReasonCode = ref('');
const errorTraceId = ref('');
const suggestedAction = ref('');
const busyAction = ref('');
const payload = ref<Dict>({});
const hydratedBlocks = ref<Dict[]>([]);
const sceneKey = computed(() => String(route.params.sceneKey || route.meta.sceneKey || '').trim());
const sceneEntry = computed(() => {
  const ready = asDict(payload.value.scene_ready_contract_v1);
  const entries = normalizeRows(ready.scenes);
  return (
    entries.find((item) => String(asDict(item.scene).key || item.scene_key || '') === sceneKey.value) ||
    entries[0] ||
    {}
  );
});
const scene = computed(() => {
  const entry = sceneEntry.value;
  return asDict(payload.value.scene || payload.value.scene_contract || payload.value.contract || entry);
});
const sceneMeta = computed(() => asDict(scene.value.scene || scene.value));
const workspace = computed(() => asDict(payload.value.workspace_home));
const capabilityKeys = computed(() => {
  const source = payload.value.capabilities || asDict(payload.value.ext_facts).capabilities || [];
  const keys = new Set<string>();
  const collect = (value: unknown) => {
    if (typeof value === 'string' && value.trim()) {
      keys.add(value.trim());
    } else if (Array.isArray(value)) {
      value.forEach(collect);
    } else if (value && typeof value === 'object') {
      const row = value as Dict;
      const key = String(row.key || row.code || row.capability_key || '').trim();
      if (key && row.allowed !== false && row.enabled !== false) keys.add(key);
      Object.values(row).forEach((item) => {
        if (Array.isArray(item)) collect(item);
      });
    }
  };
  collect(source);
  return keys;
});
const sceneAccessDenied = computed(() => !isVisibleContractNode(scene.value));
const contractBlocks = computed(() =>
  normalizeRows(scene.value.scene_blocks || scene.value.blocks || scene.value.sections),
);
const contractZones = computed(() => {
  const orchestration = asDict(
    scene.value.page_orchestration_v1 || scene.value.pageOrchestrationV1 || payload.value.page_orchestration_v1,
  );
  return normalizeRows(orchestration.zones || scene.value.zones || asDict(payload.value.page).zones);
});
const zoneDiagnostics = computed(() =>
  contractZones.value.flatMap((zone) =>
    normalizeRows(zone.blocks)
      .filter(
        (block) =>
          block.visible !== false && !resolveSceneBlockRegistryEntry(block.kind || block.type || block.block_type),
      )
      .map((block) => ({
        zone: String(zone.key || zone.zone_key || 'zone'),
        block,
        reasonCode: sceneBlockReasonCode(block.kind || block.type || block.block_type),
      })),
  ),
);
const headerBlock = computed(() => contractBlocks.value.find((block) => blockKind(block) === 'header_bar') || {});
const headerPayload = computed(() => asDict(headerBlock.value.payload));
const title = computed(() =>
  String(
    headerPayload.value.title ||
      sceneMeta.value.title ||
      sceneMeta.value.label ||
      sceneMeta.value.name ||
      sceneKey.value ||
      '业务场景',
  ),
);
const description = computed(() =>
  String(headerPayload.value.summary || sceneMeta.value.description || sceneMeta.value.subtitle || ''),
);
const headerActions = computed(() => normalizeRows(headerBlock.value.actions));
const diagnosticsMessage = computed(() => {
  const diagnostics = asDict(workspace.value.diagnostics || scene.value.diagnostics);
  const message = diagnostics.message || diagnostics.reason || diagnostics.fallback_reason;
  return message ? String(message) : '';
});
const renderedBlocks = computed(() => {
  const supplements = sceneKey.value === 'workspace.home' ? workspaceBlocks(workspace.value) : [];
  const merged = [...supplements, ...hydratedBlocks.value]
    .filter(isVisibleContractNode)
    .sort((left, right) => Number(left.order || 0) - Number(right.order || 0));
  const seen = new Set<string>();
  return merged.filter((block, index) => {
    const key = String(block.key || `${blockKind(block)}:${index}`);
    if (seen.has(key)) return false;
    seen.add(key);
    block.key = key;
    return !['page_shell', 'header_bar', 'footer', 'pagination'].includes(blockKind(block));
  });
});
const renderedZones = computed(() => {
  const zones = contractZones.value
    .filter(isVisibleContractNode)
    .sort((left, right) => Number(left.order ?? left.priority ?? 0) - Number(right.order ?? right.priority ?? 0))
    .map((zone, index) => {
      const key = String(zone.key || zone.zone_key || `zone-${index}`);
      const blockKeys = new Set(normalizeRows(zone.blocks).map((block) => String(block.key || block.block_key || '')));
      const blocks = renderedBlocks.value.filter(
        (block) =>
          String(block.__zoneKey || block.zone || block.zone_key || '') === key ||
          blockKeys.has(String(block.key || block.block_key || '')),
      );
      return {
        key,
        title: String(zone.title || zone.label || ''),
        description: String(zone.description || zone.summary || ''),
        zoneType: String(zone.zone_type || zone.type || 'supporting'),
        displayMode: String(zone.display_mode || zone.layout || 'stack'),
        blocks,
      };
    })
    .filter((zone) => zone.blocks.length > 0 || zone.title || zone.description);

  if (zones.length) return zones;
  return renderedBlocks.value.length
    ? [
        {
          key: 'default',
          title: '',
          description: '',
          zoneType: 'primary',
          displayMode: 'stack',
          blocks: renderedBlocks.value,
        },
      ]
    : [];
});

function asDict(value: unknown): Dict {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Dict) : {};
}

function normalizeRows(value: unknown): Dict[] {
  return Array.isArray(value) ? value.filter((item): item is Dict => Boolean(item && typeof item === 'object')) : [];
}

function isVisibleContractNode(node: Dict) {
  const permissions = asDict(node.permission_surface || node.permissions || node.permission || node.access);
  const policy = asDict(node.policy || node.visibility);
  const effective = asDict(permissions.effective);
  const rights = asDict(effective.rights || permissions.rights);
  const required = Array.isArray(permissions.required_capabilities)
    ? permissions.required_capabilities.map(String).filter(Boolean)
    : Array.isArray(permissions.requiredCapabilities)
      ? permissions.requiredCapabilities.map(String).filter(Boolean)
      : [];
  return (
    node.visible !== false &&
    permissions.allowed !== false &&
    policy.allowed !== false &&
    policy.visible !== false &&
    rights.read !== false &&
    required.every((key) => capabilityKeys.value.has(key))
  );
}

function safeClass(value: unknown) {
  return String(value || 'default')
    .toLowerCase()
    .replace(/[^a-z0-9_-]/g, '-');
}

function blockKind(block: Dict) {
  return normalizeSceneBlockKind(block.kind || block.type || block.block_type || 'content');
}

function workspaceBlocks(home: Dict): Dict[] {
  const risk = asDict(home.risk);
  const blocks: Dict[] = [
    {
      key: 'workspace.metrics',
      kind: 'metric_row',
      title: '工作概览',
      order: 31,
      payload: { metrics: home.metrics || home.platform_metrics },
    },
    {
      key: 'workspace.today_actions',
      kind: 'todo_list',
      title: '今日行动',
      order: 41,
      payload: { items: home.today_actions },
    },
    {
      key: 'workspace.risk',
      kind: 'warning_list',
      title: '关键事项',
      order: 42,
      payload: { items: risk.actions || risk.items },
    },
    {
      key: 'workspace.quick_links',
      kind: 'shortcut_grid',
      title: '常用功能',
      order: 43,
      payload: { items: home.scene_groups || home.quick_links },
    },
  ];
  return blocks.filter((block) => {
    const source = asDict(block.payload).metrics || asDict(block.payload).items;
    return Array.isArray(source) && source.length > 0;
  });
}

function actionKey(action: Dict) {
  return String(action.key || action.intent || action.label || JSON.stringify(action));
}

function actionLabel(action: Dict) {
  const key = String(action.key || '');
  const labels: Record<string, string> = {
    open_my_work: '打开我的工作',
    open_risk_center: '打开风险中心',
    open_scene: '打开场景',
    quick_search: '快速检索',
  };
  return String(action.label && action.label !== key ? action.label : labels[key] || key || '执行');
}

async function load() {
  loading.value = true;
  error.value = '';
  errorReasonCode.value = '';
  errorTraceId.value = '';
  suggestedAction.value = '';
  try {
    payload.value = await intent<Dict>('system.init', {
      scene: 'web',
      scene_key: sceneKey.value,
      scene_ready_mode: 'full',
      with_preload: false,
      with: ['workspace_home'],
    });
    const zonedBlocks = contractZones.value.flatMap((zone, zoneIndex) => {
      const zoneKey = String(zone.key || zone.zone_key || `zone-${zoneIndex}`);
      return normalizeRows(zone.blocks).map((block) => ({ ...block, __zoneKey: zoneKey }));
    });
    hydratedBlocks.value = await hydrateBlocks(zonedBlocks.length ? zonedBlocks : contractBlocks.value);
  } catch (cause) {
    captureError(cause, '场景加载失败');
    hydratedBlocks.value = [];
  } finally {
    loading.value = false;
  }
}

function captureError(cause: unknown, fallback: string) {
  error.value = cause instanceof Error ? cause.message : fallback;
  if (cause instanceof OdooApiError) {
    errorReasonCode.value = cause.reasonCode || cause.code;
    errorTraceId.value = cause.traceId;
    suggestedAction.value = cause.suggestedAction;
  }
}

async function hydrateBlocks(blocks: Dict[]) {
  return Promise.all(
    blocks.map(async (block) => {
      const dataDeps = asDict(block.data_deps);
      const dependencies = normalizeRows(
        Array.isArray(block.data_deps)
          ? block.data_deps
          : dataDeps.dependencies || dataDeps.queries || dataDeps.sources,
      ).filter((dependency) => String(dependency.intent || '').trim());
      if (!dependencies.length) return block;
      const datasets: Dict = {};
      await Promise.all(
        dependencies.map(async (dependency, index) => {
          const result = await intent<Dict>(String(dependency.intent).trim(), {
            ...asDict(dependency.params),
            scene_key: sceneKey.value,
          });
          datasets[String(dependency.key || dependency.name || index)] = result;
        }),
      );
      const first = Object.values(datasets)[0] as Dict | undefined;
      const blockPayload = asDict(block.payload);
      return {
        ...block,
        payload: {
          ...blockPayload,
          datasets,
          ...(!blockPayload.rows && !blockPayload.records && !blockPayload.items && first
            ? { rows: first.rows || first.records || first.items }
            : {}),
        },
      };
    }),
  );
}

async function runAction(action: Dict) {
  const key = actionKey(action);
  if (!key || busyAction.value) return;
  busyAction.value = key;
  error.value = '';
  try {
    const target = asDict(action.target);
    if (openKnownAction(action) || openTarget(Object.keys(target).length ? target : action)) return;
    const actionIntent = String(action.intent || '').trim();
    if (!actionIntent || actionIntent === 'ui.contract') {
      MessagePlugin.warning('后端没有为该动作提供可访问目标');
      return;
    }
    const result = await intent<Dict>(actionIntent, {
      ...target,
      ...asDict(action.params),
      scene_key: sceneKey.value,
    });
    const responseTarget = asDict(result.target || result.action || result.navigation);
    if (!openTarget(responseTarget)) {
      MessagePlugin.success(String(result.message || `${actionLabel(action)}已完成`));
      await load();
    }
  } catch (cause) {
    captureError(cause, `${actionLabel(action)}执行失败`);
  } finally {
    busyAction.value = '';
  }
}

function openKnownAction(action: Dict) {
  const key = String(action.key || '').trim();
  if (key === 'open_my_work') {
    void router.push('/my-work/index');
    return true;
  }
  if (key === 'open_risk_center') {
    void router.push({ path: '/my-work/index', query: { section: 'risk' } });
    return true;
  }
  return false;
}

function openTarget(target: Dict) {
  const routePath = String(target.route || target.path || '').trim();
  if (routePath.startsWith('/')) {
    void router.push(routePath);
    return true;
  }
  if (target.scene_key || target.sceneKey) {
    void router.push(`/s/${String(target.scene_key || target.sceneKey)}`);
    return true;
  }
  const wantedAction = Number(target.action_id || target.actionId || 0);
  const wantedMenu = Number(target.menu_id || target.menuId || 0);
  const wantedXmlid = String(target.action_xmlid || target.actionXmlid || '');
  if (!wantedAction && !wantedMenu && !wantedXmlid) return false;
  const match = router.getRoutes().find((item) => {
    const routeMeta = item.meta as Dict;
    const source = asDict(routeMeta.action);
    return (
      (wantedAction > 0 && Number(routeMeta.actionId || 0) === wantedAction) ||
      (wantedMenu > 0 && Number(routeMeta.menuId || 0) === wantedMenu) ||
      (wantedXmlid &&
        String(source.action_xmlid || source.actionXmlid || asDict(source.meta).action_xmlid || '') === wantedXmlid)
    );
  });
  if (match) {
    void router.push({ name: match.name, query: wantedMenu ? { menu_id: String(wantedMenu) } : {} });
  } else {
    MessagePlugin.warning('当前账号的动态菜单中没有该目标入口');
  }
  return true;
}

onMounted(load);
watch(sceneKey, (next, previous) => {
  if (next && next !== previous) void load();
});
</script>
<style scoped>
.scene-runtime {
  display: grid;
  gap: 16px;
}
.scene-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  padding: 24px 28px;
  border: 1px solid var(--td-border-level-1-color);
  border-radius: 8px;
  background: var(--td-bg-color-container);
}
.scene-header__copy {
  min-width: 0;
}
.scene-header__type {
  color: var(--td-brand-color);
  font-size: 13px;
}
.scene-header h1,
.scene-header p {
  margin: 0;
}
.scene-header h1 {
  margin-top: 5px;
  font-size: 28px;
  overflow-wrap: anywhere;
}
.scene-header p {
  margin-top: 8px;
  color: var(--td-text-color-secondary);
}
.scene-loading {
  display: grid;
  min-height: 320px;
  place-items: center;
  border: 1px solid var(--td-border-level-1-color);
  border-radius: 8px;
  background: var(--td-bg-color-container);
}
.scene-zone {
  display: grid;
  gap: 12px;
  min-width: 0;
}
.scene-zone__header h2,
.scene-zone__header p {
  margin: 0;
}
.scene-zone__header h2 {
  font-size: 18px;
}
.scene-zone__header p {
  margin-top: 5px;
  color: var(--td-text-color-secondary);
}
.scene-zone__body {
  display: grid;
  gap: 16px;
  min-width: 0;
}
.scene-zone--grid .scene-zone__body {
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
}
.scene-zone--two-column .scene-zone__body,
.scene-zone--two_column .scene-zone__body {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
@media (width <= 720px) {
  .scene-header {
    flex-direction: column;
    padding: 18px;
  }
  .scene-zone--two-column .scene-zone__body,
  .scene-zone--two_column .scene-zone__body {
    grid-template-columns: 1fr;
  }
}
</style>
