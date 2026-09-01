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
  >
    <TDesignTabPanel
      v-for="page in pages"
      :key="page.key"
      :value="page.key"
      :label="page.title"
      removable
      :destroy-on-close="false"
    >
      <!-- 内容由路由渲染，此处不渲染 -->
    </TDesignTabPanel>
  </TDesignTabs>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { TDesignTabs, TDesignTabPanel } from '../design-system/tdesignPrimitiveBridge';
import type { ActivityPage } from '../../stores/session';
import { shouldShowActivityPageTabs } from './activityPageTabKeyboard';

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
</script>

<style scoped>
.activity-page-tabs {
  width: 100%;
  min-height: 36px;
  padding: 0 12px;
  border-bottom: 1px solid var(--sc-app-border);
  background: var(--sc-app-panel);
}

.activity-page-tabs :deep(.t-tabs__nav) {
  min-height: 36px;
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
}
</style>
