<template>
  <div ref="focusHost" class="activity-page-tabs-host" @keydown.capture="handleKeydown">
  <TDesignTabs
    v-if="shouldShowActivityPageTabs(pages.length)"
    ref="tabsRef"
    class="activity-page-tabs"
    :value="activeKey"
    placement="top"
    size="medium"
    theme="normal"
    :addable="false"
    @change="handleChange"
    @remove="handleRemove"
  >
    <TDesignTabPanel
      v-for="page in pages"
      :key="page.key"
      :value="page.key"
      :label="page.title"
      :removable="false"
      :destroy-on-close="false"
    >
      <template #label>
        <span class="activity-page-tab-label" :title="page.title" :data-activity-page-key="page.key">
          <ScButton
            class="activity-page-tab-title"
            appearance="auth-link"
            data-navigation-control="activity-page-title"
            variant="ghost"
            :aria-label="`切换至${page.title}`"
            :aria-pressed="page.key === activeKey"
            @click.stop="handleTitleActivate(page)"
          >{{ page.title }}</ScButton>
          <ScIconButton
            class="activity-page-tab-close"
            appearance="activity-tab-close"
            :label="`${closeLabel}“${page.title}”`"
            @click.stop="handleExplicitClose(page)"
          ><ScIcon name="close" :size="14" /></ScIconButton>
        </span>
      </template>
      <!-- 内容由路由渲染，此处不渲染 -->
    </TDesignTabPanel>
  </TDesignTabs>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { TDesignTabs, TDesignTabPanel } from '../design-system/tdesignPrimitiveBridge';
import ScIconButton from '../design-system/ScIconButton.vue';
import ScButton from '../design-system/ScButton.vue';
import ScIcon from '../design-system/ScIcon.vue';
import type { ActivityPage } from '../../stores/session';
import { resolveActivityTabKeyboardIndex, shouldShowActivityPageTabs } from './activityPageTabKeyboard';

const props = withDefaults(defineProps<{
  pages: ActivityPage[];
  activeKey: string;
  activatePage?: (page: ActivityPage) => Promise<void>;
  label?: string;
  closeLabel?: string;
}>(), {
  activatePage: undefined,
  label: '活动页面',
  closeLabel: '关闭',
});

const emit = defineEmits<{
  activate: [page: ActivityPage];
  close: [page: ActivityPage];
  'focus-exit': [];
}>();

const tabsRef = ref<InstanceType<typeof TDesignTabs> | null>(null);
const focusHost = ref<HTMLElement | null>(null);
let pendingFocusKey = '';
// The driver can remount tab labels after the route has already settled.
function restoreKeyboardFocus() {
  if (!pendingFocusKey || props.activeKey !== pendingFocusKey) return;
  const label = Array.from(focusHost.value?.querySelectorAll<HTMLElement>('[data-activity-page-key]') || [])
    .find((element) => element.dataset.activityPageKey === pendingFocusKey);
  const button = label?.querySelector<HTMLElement>('.activity-page-tab-title');
  if (!button) return;
  button.focus();
  pendingFocusKey = '';
}
let focusObserver: MutationObserver | null = null;
onMounted(() => {
  focusObserver = new MutationObserver(restoreKeyboardFocus);
  if (focusHost.value) focusObserver.observe(focusHost.value, { childList: true, subtree: true });
  nextTick(revealActivePageTab);
});
onBeforeUnmount(() => focusObserver?.disconnect());

function revealActivePageTab() {
  const scroller = focusHost.value?.querySelector<HTMLElement>('.t-tabs__nav-scroll');
  const label = Array.from(focusHost.value?.querySelectorAll<HTMLElement>('[data-activity-page-key]') || [])
    .find((element) => element.dataset.activityPageKey === props.activeKey);
  if (!scroller || !label) return;
  const scrollerRect = scroller.getBoundingClientRect();
  const labelRect = label.getBoundingClientRect();
  if (labelRect.left < scrollerRect.left) {
    scroller.scrollBy({ left: labelRect.left - scrollerRect.left, behavior: 'instant' });
  } else if (labelRect.right > scrollerRect.right) {
    scroller.scrollBy({ left: labelRect.right - scrollerRect.right, behavior: 'instant' });
  }
}

watch(() => props.activeKey, async () => {
  await nextTick();
  revealActivePageTab();
});

function handleTitleActivate(page: ActivityPage) {
  pendingFocusKey = '';
  emit('activate', page);
}

function handleChange(value: string | number) {
  const key = String(value);
  const page = props.pages.find((p) => p.key === key);
  if (page) {
    emit('activate', page);
  }
}

function handleRemove(options: { value: string | number; e: MouseEvent }) {
  const key = String(options.value);
  const page = props.pages.find((p) => p.key === key);
  if (page) {
    emit('close', page);
  }
}

function handleExplicitClose(page: ActivityPage) {
  pendingFocusKey = '';
  emit('close', page);
}

async function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    pendingFocusKey = '';
    event.preventDefault();
    event.stopPropagation();
    emit('focus-exit');
    return;
  }
  const target = event.target instanceof HTMLElement ? event.target : null;
  const key = target?.closest<HTMLElement>('[data-activity-page-key]')?.dataset.activityPageKey || '';
  const currentIndex = props.pages.findIndex((page) => page.key === key);
  const nextIndex = resolveActivityTabKeyboardIndex({ key: event.key, currentIndex, count: props.pages.length });
  if (nextIndex === null) return;
  event.preventDefault();
  event.stopPropagation();
  const nextPage = props.pages[nextIndex];
  if (!nextPage) return;
  pendingFocusKey = nextPage.key;
  if (props.activatePage) await props.activatePage(nextPage);
  else emit('activate', nextPage);
  await nextTick();
  restoreKeyboardFocus();
}
</script>

<style scoped>
.activity-page-tabs-host { min-width: 0; }
.activity-page-tabs {
  width: 100%;
  min-width: 0;
  min-height: 36px;
  overflow: hidden;
  padding: 0 12px;
  border-bottom: 1px solid var(--sc-app-border);
  background: var(--sc-app-bg);
}

.activity-page-tab-label {
  display: inline-flex;
  min-width: 0;
  max-width: 180px;
  align-items: center;
  gap: 4px;
}

.activity-page-tab-title {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 760px) {
  .activity-page-tabs {
    overflow: visible;
    padding-inline: 0;
  }

  .activity-page-tabs :deep(.t-tabs__nav) {
    min-width: 0;
  }

  .activity-page-tabs :deep(.t-tabs__nav-container) {
    min-width: 0;
    overflow: hidden;
  }

  .activity-page-tabs :deep(.t-tabs__nav-scroll) {
    overflow-x: auto;
    overflow-y: hidden;
    overscroll-behavior-inline: contain;
    scrollbar-width: thin;
  }

  .activity-page-tabs :deep(.t-tabs__nav-wrap) {
    padding-inline: 8px;
  }

  .activity-page-tabs :deep(.t-tabs__operations--right) {
    display: none;
  }

  .activity-page-tabs :deep(.t-tabs__nav-item) {
    min-height: var(--sc-touch-target-min);
  }

  .activity-page-tab-label {
    min-height: var(--sc-touch-target-min);
    max-width: 160px;
  }

  .activity-page-tab-title,
  .activity-page-tab-close {
    min-height: var(--sc-touch-target-min);
  }

  .activity-page-tab-close {
    width: var(--sc-touch-target-min);
    min-width: var(--sc-touch-target-min);
    opacity: .65;
  }
}
</style>
