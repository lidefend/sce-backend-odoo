<template>
  <section class="inline-action-tabs" v-if="tabs.length">
    <el-divider />
    <el-tabs v-model="activeKey" @tab-change="onTabChange">
      <el-tab-pane
        v-for="tab in tabs"
        :key="tab.key"
        :label="tab.label"
        :name="tab.key"
        :disabled="props.actions.find((action) => action.key === tab.key)?.enabled === false"
      >
        <div v-if="activeKey === tab.key" class="inline-action-panel">
          <el-skeleton v-if="tab.loading" :rows="6" animated />
          <router-view v-else-if="tab.location" :route="embeddedRouteRef" />
          <el-alert
            v-if="!tab.loading && !tab.location"
            :title="tab.label"
            type="info"
            show-icon
            :closable="false"
          >
            此操作直接作用于当前记录，没有独立的列表或表单页面。
          </el-alert>
        </div>
      </el-tab-pane>
    </el-tabs>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, provide, reactive, ref, watch } from "vue";
import {
  createMemoryHistory,
  createRouter,
  routeLocationKey,
  routerKey,
  routerViewLocationKey,
  viewDepthKey,
  type RouteLocationRaw,
  type Router,
} from "vue-router";
import type { BusinessAction, Dictionary } from "@/types/contracts";

const props = defineProps<{
  actions: BusinessAction[];
  model: string;
  recordId: number | null;
  recordValues: Dictionary;
  currentQuery: Dictionary;
  runAction: (action: BusinessAction) => void | Promise<void>;
}>();

interface InlineTab {
  key: string;
  label: string;
  location: RouteLocationRaw | null;
  loading: boolean;
}

const tabs = ref<InlineTab[]>([]);
const activeKey = ref("");
const pendingActionKey = ref("");

const embeddedRouter: Router = createRouter({
  history: createMemoryHistory(),
  routes: [
    {
      path: "/action/:actionId?",
      name: "Action",
      component: () => import("@/views/ActionView.vue"),
    },
    {
      path: "/record/:model/:id",
      name: "Record",
      component: () => import("@/views/RecordView.vue"),
    },
  ],
});
const embeddedRouteRef = embeddedRouter.currentRoute;

// The embedded views use the normal vue-router composables. Supplying the
// router keys locally keeps their navigation inside this component.
const embeddedRoute = reactive({ ...embeddedRouter.currentRoute.value });
provide(routerKey, embeddedRouter);
provide(routeLocationKey, embeddedRoute as any);
provide(routerViewLocationKey, embeddedRouter.currentRoute);
provide(viewDepthKey, 0);
embeddedRouter.afterEach((to) => Object.assign(embeddedRoute, to));

const query = computed(() => ({ ...props.currentQuery }));

function positiveInt(value: unknown) {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : 0;
}

function object(value: unknown): Dictionary {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Dictionary)
    : {};
}

function firstObject(...values: unknown[]) {
  return values.find((value) => value && typeof value === "object" && !Array.isArray(value)) as Dictionary | undefined;
}

function targetFrom(value: unknown): Dictionary {
  const root = object(value);
  const nested = firstObject(
    root.target,
    root.entry_target,
    root.entryTarget,
    root.raw_action,
    root.rawAction,
  );
  if (nested) {
    const nestedTarget = targetFrom(nested);
    if (Object.keys(nestedTarget).length) return { ...nestedTarget, ...root };
  }
  const refs = firstObject(root.compatibility_refs, root.compatibilityRefs) || {};
  const recordEntry = firstObject(root.record_entry, root.recordEntry) || {};
  const recordId = positiveInt(
    root.record_id ?? root.recordId ?? root.res_id ?? recordEntry.record_id ?? recordEntry.id,
  );
  const actionId = positiveInt(
    root.action_id ?? root.actionId ?? root.action_ref ?? root.id ?? refs.action_id ?? refs.actionId ?? recordEntry.action_id,
  );
  const model = String(
    root.model ?? root.res_model ?? refs.model ?? recordEntry.model ?? "",
  ).trim();
  const route = String(root.route || refs.route || "").trim();
  const kind = String(root.kind || "").toLowerCase();
  return { ...root, ...refs, ...recordEntry, recordId, actionId, model, route, kind };
}

function extractTarget(result: Dictionary) {
  const root = object(result);
  const payload = object(root.result);
  const effect = object(root.effect);
  const candidates = [
    effect.target,
    payload.target,
    payload.entry_target,
    payload.raw_action,
    root.target,
    root.entry_target,
    root.raw_action,
  ];
  for (const candidate of candidates) {
    const target = targetFrom(candidate);
    if (target.recordId || target.actionId || target.route) return target;
  }
  return {};
}

function actionTarget(action: BusinessAction) {
  return targetFrom(action.target || {});
}

function baseQuery(target: Dictionary) {
  const projectId = positiveInt(
    props.recordValues.project_id && typeof props.recordValues.project_id === "object"
      ? props.recordValues.project_id.id
      : Array.isArray(props.recordValues.project_id)
        ? props.recordValues.project_id[0]
        : props.recordValues.project_id,
  );
  return {
    ...query.value,
    action_id: positiveInt(target.actionId) || query.value.action_id || undefined,
    menu_id: query.value.menu_id || undefined,
    project_id: projectId || query.value.project_id || undefined,
    default_project_id: projectId || query.value.default_project_id || undefined,
  };
}

function locationFor(target: Dictionary): RouteLocationRaw | null {
  const model = String(target.model || props.model).trim();
  const recordId = positiveInt(target.recordId);
  const actionId = positiveInt(target.actionId);
  const mode = String(target.mode || target.view_mode || "").toLowerCase();
  const targetKind = String(target.kind || "").toLowerCase();
  const targetQuery = baseQuery(target);
  if ((targetKind === "create" || mode === "create" || target.target === "new") && model)
    return { name: "Record", params: { model, id: "new" }, query: { ...targetQuery, mode: "create" } };
  if ((targetKind === "record" || recordId > 0) && model && recordId > 0)
    return { name: "Record", params: { model, id: recordId }, query: { ...targetQuery, mode: "view" } };
  if (actionId > 0)
    return { name: "Action", params: { actionId: String(actionId) }, query: { ...targetQuery, model: model || undefined } };
  const route = String(target.route || "").trim();
  const match = route.match(/(?:^|\/)(?:action|a)\/(\d+)/);
  if (match) return { name: "Action", params: { actionId: match[1] }, query: { ...targetQuery, model: model || undefined } };
  return null;
}

function ensureTab(action: BusinessAction, location: RouteLocationRaw | null, loading = false) {
  const key = action.key;
  const existing = tabs.value.find((tab) => tab.key === key);
  if (existing) {
    existing.location = location || existing.location;
    existing.loading = loading;
  } else {
    tabs.value.push({ key, label: action.label, location, loading });
  }
  activeKey.value = key;
}

async function openLocation(action: BusinessAction, location: RouteLocationRaw) {
  ensureTab(action, location, true);
  await nextTick();
  await embeddedRouter.push(location);
  const tab = tabs.value.find((item) => item.key === action.key);
  if (tab) tab.loading = false;
}

async function onTabChange(key: string) {
  const tab = tabs.value.find((item) => item.key === key);
  const action = props.actions.find((item) => item.key === key);
  if (!tab || !action) return;
  activeKey.value = key;
  if (tab.location) {
    await embeddedRouter.push(tab.location);
    return;
  }
  tab.loading = true;
  try {
    await props.runAction(action);
  } finally {
    if (!tab.location) tab.loading = false;
  }
}

async function prepareAction(action: BusinessAction) {
  const location = locationFor(actionTarget(action));
  if (!location) {
    pendingActionKey.value = "";
    return false;
  }
  pendingActionKey.value = action.key;
  await openLocation(action, location);
  pendingActionKey.value = "";
  return true;
}

async function handleActionResult(result: Dictionary, action: BusinessAction) {
  if (!pendingActionKey.value || pendingActionKey.value !== action.key) return false;
  const location = locationFor(extractTarget(result));
  if (!location) {
    pendingActionKey.value = "";
    return false;
  }
  await openLocation(action, location);
  pendingActionKey.value = "";
  return true;
}

defineExpose({ prepareAction, handleActionResult });

watch(
  () => props.actions,
  (actions) => {
    const existing = new Map(tabs.value.map((tab) => [tab.key, tab]));
    tabs.value = actions.map((action) =>
      existing.get(action.key) || {
        key: action.key,
        label: action.label,
        location: null,
        loading: false,
      },
    );
    if (activeKey.value && !tabs.value.some((tab) => tab.key === activeKey.value)) activeKey.value = "";
  },
  { immediate: true },
);
</script>

<style scoped>
.inline-action-tabs {
  margin-top: 8px;
  min-width: 0;
  max-width: 100%;
  overflow-x: hidden;
}
.inline-action-tabs :deep(.el-tabs__header) {
  margin-bottom: 16px;
  max-width: 100%;
  overflow: hidden;
}
.inline-action-tabs :deep(.el-tabs__nav) {
  max-width: 100%;
  display: flex;
  flex-wrap: wrap;
}
.inline-action-tabs :deep(.el-tabs__item) {
  min-width: 0;
  max-width: 100%;
  height: auto;
  min-height: 40px;
  line-height: 20px;
  padding-top: 10px;
  padding-bottom: 10px;
  white-space: normal;
  overflow-wrap: anywhere;
  text-align: center;
}
.inline-action-panel {
  min-width: 0;
  max-width: 100%;
  overflow-x: hidden;
  padding: 2px 0 8px;
}
</style>
