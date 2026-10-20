import { computed, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import type { NavNode } from '@sc/schema';
import { fetchMyWorkSummary, type ProductMyWorkItem, type ProductMyWorkWorkspace } from '../../api/myWork';
import { currentContextEpoch, isCurrentContextEpoch } from '../../app/contextEpoch';
import { usePageContract } from '../../app/pageContract';
import { mergeWorkspaceNavigationLinks, resolveWorkspaceNavigationLink } from '../../app/workspaceHomeNavigation';
import {
  isProductCapabilityCatalogGap,
  projectLoginHomeBlocks,
} from '../../app/productCapabilityCatalogProjection';
import type { ProductCapabilityLoginHomeBlock } from '../../api/productCapabilityCatalog';
import { useSessionStore, type ActivityPage } from '../../stores/session';

type SurfaceLink = { key: string; label: string; detail: string; route: string };
type SurfaceTask = SurfaceLink & { kind: string; recordId: number; state: ProductMyWorkItem['state']; facts: ProductMyWorkItem['facts']; amount?: ProductMyWorkItem['facts'][number] };
type SurfaceCount = { key: string; label: string; value: number };
type HomeRiskItem = { key: string; label: string; detail: string; route: string; tone: string; actionLabel: string };
type HomeObjectItem = {
  key: string;
  label: string;
  detail: string;
  route: string;
  state: string;
  reason: string;
  kind: string;
  model: string;
  recordId: number;
  amountDisplay: string;
};

function text(value: unknown): string {
  return String(value ?? '').trim();
}

function topNodes(nodes: NavNode[]): NavNode[] {
  return nodes.length === 1 && nodes[0]?.children?.length ? nodes[0].children : nodes;
}

function taskLink(item: ProductMyWorkItem): SurfaceTask | null {
  const route = text(item.target?.route);
  const label = text(item.record?.label);
  if (!route || !label) return null;
  return {
    key: text(item.key) || route,
    label,
    detail: [text(item.business_type), text(item.state?.label)].filter(Boolean).join(' · '),
    route,
    kind: text(item.business_type),
    recordId: Number(item.target?.record_id || 0),
    state: item.state,
    facts: [],
    amount: (item.facts || []).find((fact) => fact.field_group !== 'audit' && fact.display_role === 'money'),
  };
}

function recentMatchesCompany(page: ActivityPage, companyId: number): boolean {
  if (!companyId) return true;
  const pageCompanyId = Number(page.record_context?.company_id || page.record_context?.selected?.company_id || 0);
  return !pageCompanyId || pageCompanyId === companyId;
}

export function useWorkspaceHome() {
  const router = useRouter();
  const session = useSessionStore();
  const pageContract = usePageContract('home');
  const loading = ref(false);
  const error = ref('');
  const unsupported = ref(false);
  const workWorkspace = ref<ProductMyWorkWorkspace | null>(null);
  const catalogLoading = ref(false);
  const catalogError = ref('');
  const catalogGap = ref('');
  const loginBlocks = ref<ProductCapabilityLoginHomeBlock[]>([]);
  let loadRequestSequence = 0;

  const pageProfile = computed(() => pageContract.contract.value?.page_orchestration?.page || {});
  const title = computed(() => text(pageProfile.value.title) || pageContract.text('title', '首页'));
  const subtitle = computed(() => text(pageProfile.value.subtitle) || pageContract.text('subtitle', '查看当前账号可处理的事项和可用入口。'));
  const taskSection = computed(() => workWorkspace.value?.sections.find((section) => section.key === 'todo') || null);
  const tasks = computed<SurfaceTask[]>(() => (taskSection.value?.items || [])
    .map(taskLink)
    .filter((item): item is SurfaceTask => Boolean(item))
    .slice(0, 3));
  const summaries = computed<SurfaceCount[]>(() => (workWorkspace.value?.sections || [])
    .map((section) => ({ key: section.key, label: section.label, value: section.count }))
    .slice(0, 4));
  const quickLinks = computed<SurfaceLink[]>(() => {
    const workspaceLinks = (workWorkspace.value?.presentation.quick_links || [])
      .filter((item) => text(item.route) && text(item.label))
      .map((item) => ({ key: text(item.key) || text(item.route), label: text(item.label), detail: text(item.detail), route: text(item.route) }));
    const navigationLinks = topNodes(session.menuTree)
      .map(resolveWorkspaceNavigationLink)
      .filter((item): item is SurfaceLink => Boolean(item));
    return mergeWorkspaceNavigationLinks(navigationLinks, workspaceLinks)
      .slice(0, 7);
  });
  const recentItems = computed<SurfaceLink[]>(() => {
    const companyId = Number(session.recordContext?.company_id || 0);
    return session.activityPages
      .filter((page) => page.route && page.title && recentMatchesCompany(page, companyId))
      .sort((left, right) => right.last_active_at - left.last_active_at)
      .slice(0, 4)
      .map((page) => ({ key: page.key, label: page.title, detail: '', route: page.route }));
  });
  const riskItems = computed<HomeRiskItem[]>(() => session.workspaceRiskAlertRows
    .map((row) => ({
      key: row.id,
      label: row.title,
      detail: row.description,
      route: row.path || (row.sceneKey ? `/s/${row.sceneKey}` : ''),
      tone: row.tone,
      actionLabel: row.actionLabel,
    }))
    .filter((item) => Boolean(item.label))
    .slice(0, 4));
  const objectItems = computed<HomeObjectItem[]>(() => session.workspaceHomeObjectRows
    .map((row) => ({
      key: row.key || row.id,
      label: row.title,
      detail: [row.kindLabel, row.subtitle, row.stateLabel, row.amountDisplay].filter(Boolean).join(' · '),
      route: row.route,
      state: row.state,
      reason: row.reason,
      kind: row.kind,
      model: row.model,
      recordId: row.recordId,
      amountDisplay: row.amountDisplay,
    }))
    .filter((item) => Boolean(item.label))
    .slice(0, 6));
  const myObjectsTitle = computed(() => text(session.workspaceHome?.layout?.texts?.['my_objects.title']));
  const myObjectsEmpty = computed(() => text(session.workspaceHome?.layout?.texts?.['my_objects.empty']));

  async function loadCatalog() {
    if (!session.token) {
      loginBlocks.value = [];
      return;
    }
    catalogLoading.value = true;
    catalogError.value = '';
    catalogGap.value = '';
    try {
      await session.loadProductCapabilityCatalog();
      loginBlocks.value = projectLoginHomeBlocks(session.productCapabilityCatalog);
    } catch (err) {
      loginBlocks.value = [];
      if (isProductCapabilityCatalogGap(err)) {
        catalogGap.value = String(err.message || '');
      } else {
        catalogError.value = pageContract.text('load_error', '当前页面暂时无法加载，请稍后重试。');
      }
    } finally {
      catalogLoading.value = false;
    }
  }

  async function load() {
    const requestSequence = ++loadRequestSequence;
    if (!session.token) {
      workWorkspace.value = null;
      loginBlocks.value = [];
      return;
    }
    const navMeta = ((session.initMeta as Record<string, unknown> | null)?.nav_meta ?? {}) as Record<string, unknown>;
    if (navMeta.platform_minimum_surface === true) {
      workWorkspace.value = null;
      error.value = '';
      unsupported.value = true;
      loginBlocks.value = [];
      return;
    }
    const requestEpoch = currentContextEpoch();
    loading.value = true;
    error.value = '';
    unsupported.value = false;
    workWorkspace.value = null;
    void loadCatalog();
    try {
      const result = await fetchMyWorkSummary(undefined, undefined, { page: 1, sortBy: 'priority', sortDir: 'desc' });
      if (isCurrentContextEpoch(requestEpoch) && requestSequence === loadRequestSequence) workWorkspace.value = result.product_workspace || null;
    } catch (err) {
      if (isCurrentContextEpoch(requestEpoch) && requestSequence === loadRequestSequence) {
        if (text((err as { reasonCode?: unknown } | null)?.reasonCode) === 'INTENT_NOT_FOUND') {
          unsupported.value = true;
        } else {
          error.value = pageContract.text('load_error', '当前页面暂时无法加载，请稍后重试。');
        }
      }
    } finally {
      if (isCurrentContextEpoch(requestEpoch) && requestSequence === loadRequestSequence) loading.value = false;
    }
  }

  async function navigate(route: string) {
    if (route) await router.push(route);
  }

  watch(
    [
      () => session.token,
      () => session.recordContext?.company_id,
      () => session.recordContext?.selected?.id,
    ],
    () => { void load(); },
    { immediate: true },
  );

  return {
    title,
    subtitle,
    tasks,
    summaries,
    quickLinks,
    recentItems,
    riskItems,
    objectItems,
    myObjectsTitle,
    myObjectsEmpty,
    loading,
    error,
    unsupported,
    loginBlocks,
    catalogLoading,
    catalogError,
    catalogGap,
    load,
    loadCatalog,
    navigate,
  };
}
