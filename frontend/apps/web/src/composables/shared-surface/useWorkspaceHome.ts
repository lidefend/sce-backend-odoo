import { computed, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import type { NavNode } from '@sc/schema';
import { fetchMyWorkSummary, type ProductMyWorkItem, type ProductMyWorkWorkspace } from '../../api/myWork';
import { currentContextEpoch, isCurrentContextEpoch } from '../../app/contextEpoch';
import { usePageContract } from '../../app/pageContract';
import { mergeWorkspaceNavigationLinks, resolveWorkspaceNavigationLink } from '../../app/workspaceHomeNavigation';
import { useSessionStore, type ActivityPage } from '../../stores/session';

type SurfaceLink = { key: string; label: string; detail: string; route: string };
type SurfaceCount = { key: string; label: string; value: number };

function text(value: unknown): string {
  return String(value ?? '').trim();
}

function topNodes(nodes: NavNode[]): NavNode[] {
  return nodes.length === 1 && nodes[0]?.children?.length ? nodes[0].children : nodes;
}

function taskLink(item: ProductMyWorkItem): SurfaceLink | null {
  const route = text(item.target?.route);
  const label = text(item.record?.label);
  if (!route || !label) return null;
  return {
    key: text(item.key) || route,
    label,
    detail: [text(item.business_type), text(item.state?.label)].filter(Boolean).join(' · '),
    route,
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
  const workWorkspace = ref<ProductMyWorkWorkspace | null>(null);
  let loadRequestSequence = 0;

  const pageProfile = computed(() => pageContract.contract.value?.page_orchestration?.page || {});
  const title = computed(() => text(pageProfile.value.title) || pageContract.text('title', '首页'));
  const subtitle = computed(() => text(pageProfile.value.subtitle) || pageContract.text('subtitle', '查看当前账号可处理的事项和可用入口。'));
  const taskSection = computed(() => workWorkspace.value?.sections.find((section) => section.key === 'todo') || null);
  const tasks = computed<SurfaceLink[]>(() => (taskSection.value?.items || [])
    .map(taskLink)
    .filter((item): item is SurfaceLink => Boolean(item))
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

  async function load() {
    const requestSequence = ++loadRequestSequence;
    if (!session.token) {
      workWorkspace.value = null;
      return;
    }
    const requestEpoch = currentContextEpoch();
    loading.value = true;
    error.value = '';
    workWorkspace.value = null;
    try {
      const result = await fetchMyWorkSummary(12, 4, { page: 1, pageSize: 12, sortBy: 'priority', sortDir: 'desc' });
      if (isCurrentContextEpoch(requestEpoch) && requestSequence === loadRequestSequence) workWorkspace.value = result.product_workspace || null;
    } catch {
      if (isCurrentContextEpoch(requestEpoch) && requestSequence === loadRequestSequence) {
        error.value = pageContract.text('load_error', '当前页面暂时无法加载，请稍后重试。');
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

  return { title, subtitle, tasks, summaries, quickLinks, recentItems, loading, error, load, navigate };
}
