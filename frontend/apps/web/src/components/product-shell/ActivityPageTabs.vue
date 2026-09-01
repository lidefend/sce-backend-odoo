<template>
  <TDesignTabs
    v-if="shouldShowActivityPageTabs(pages.length)"
    ref="tabsRef"
    class="activity-page-tabs"
    :value="activeKey"
    placement="top"
    :addable="false"
    @change="handleChange"
    @remove="handleRemove"
    @keydown="handleKeydown"
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
          <span class="activity-page-tab-title">{{ page.title }}</span>
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
</template>

<script setup lang="ts">
import { nextTick, ref } from 'vue';
import { TDesignTabs, TDesignTabPanel } from '../design-system/tdesignPrimitiveBridge';
import ScIconButton from '../design-system/ScIconButton.vue';
import ScIcon from '../design-system/ScIcon.vue';
import type { ActivityPage } from '../../stores/session';
import { resolveActivityTabKeyboardIndex, shouldShowActivityPageTabs } from './activityPageTabKeyboard';

const props = withDefaults(defineProps<{
  pages: ActivityPage[];
  activeKey: string;
  label?: string;
  closeLabel?: string;
}>(), {
  label: '活动页面',
  closeLabel: '关闭',
});

const emit = defineEmits<{
  activate: [page: ActivityPage];
  close: [page: ActivityPage];
  'focus-exit': [];
}>();

const tabsRef = ref<InstanceType<typeof TDesignTabs> | null>(null);

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
  emit('close', page);
}

async function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    event.preventDefault();
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
  emit('activate', nextPage);
  await nextTick();
  const root = event.currentTarget instanceof HTMLElement ? event.currentTarget : null;
  root?.querySelectorAll<HTMLElement>('.activity-page-tab-close')[nextIndex]?.focus();
}
</script>

<style scoped>
.activity-page-tabs {
  width: 100%;
  min-width: 0;
  min-height: 36px;
  overflow: hidden;
  padding: 0 12px;
  border-bottom: 1px solid var(--sc-app-border);
  background: var(--sc-app-panel);
}

.activity-page-tabs :deep(.t-tabs__nav) {
  max-width: 100%;
  min-height: 36px;
}

.activity-page-tabs :deep(.t-tabs__nav-wrap) {
  min-width: 0;
}

.activity-page-tabs :deep(.t-tabs__nav-item) {
  height: 36px;
  padding: 0 12px;
  font-size: 12px;
  font-weight: 500;
}

.activity-page-tabs :deep(.t-tabs__nav-item.t-is-active) {
  font-weight: 600;
}

.activity-page-tabs :deep(.t-tabs__nav-item .t-tabs__nav-item-text) {
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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

.activity-page-tabs :deep(.t-tabs__content) {
  display: none;
}

@media (max-width: 760px) {
  .activity-page-tabs {
    padding-inline: 8px;
  }
  .activity-page-tabs :deep(.t-tabs__nav-item) {
    padding: 0 8px;
  }
  .activity-page-tab-label {
    max-width: 132px;
  }
}
</style>
