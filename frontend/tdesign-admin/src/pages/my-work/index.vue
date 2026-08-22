<template>
  <div class="my-work-page">
    <div class="page-heading">
      <div>
        <p class="eyebrow">工作台</p>
        <h1>我的工作</h1>
        <p>待办、我发起的事项和需要关注的业务记录。</p>
      </div>
      <t-button variant="outline" :loading="loading" @click="load"
        ><template #icon><t-icon name="refresh" /></template>刷新</t-button
      >
    </div>
    <t-alert v-if="error" theme="error" :message="error" />
    <section class="summary-grid">
      <t-card v-for="item in summary" :key="item.key" :bordered="false"
        ><span>{{ item.label }}</span
        ><strong>{{ item.count }}</strong></t-card
      >
    </section>
    <t-card :bordered="false" class="work-panel">
      <div class="work-toolbar">
        <t-input v-model="search" clearable placeholder="搜索事项" @enter="load" @clear="load"
          ><template #suffix-icon><t-icon name="search" /></template></t-input
        ><t-select v-model="section" :options="sectionOptions" @change="load" /><t-select
          v-model="sortBy"
          :options="sortOptions"
          @change="load"
        /><t-button :disabled="!selectedIds.length" :loading="batching" @click="completeBatch"
          >批量完成 ({{ selectedIds.length }})</t-button
        >
      </div>
      <t-loading v-if="loading" text="正在加载工作事项" />
      <t-empty v-else-if="!items.length" description="当前没有待处理事项" />
      <div v-else class="work-list">
        <article v-for="item in items" :key="String(item.key || item.id || item.title)" class="work-item">
          <t-checkbox v-if="item.id" :checked="selectedIds.includes(item.id)" @change="toggleSelected(item.id)" />
          <div class="work-item__main">
            <div class="work-item__title">
              <t-tag v-if="item.priority" :theme="priorityTheme(item.priority)" variant="light">{{
                priorityLabel(item.priority)
              }}</t-tag>
              <h3>{{ item.title || item.label || '未命名事项' }}</h3>
            </div>
            <p>
              {{ item.section_label || item.section || ''
              }}<span v-if="item.deadline"> · 截止 {{ item.deadline }}</span>
            </p>
            <small v-if="item.reason_code">原因：{{ item.reason_code }}</small>
          </div>
          <div class="work-item__actions">
            <t-button
              v-for="action in item.actions || []"
              :key="action.key"
              size="small"
              :theme="action.key.includes('delete') || action.key.includes('cancel') ? 'danger' : 'primary'"
              variant="outline"
              :loading="busyKey === `${item.id}:${action.key}`"
              @click="runAction(item, action)"
              >{{ action.label }}</t-button
            ><t-button size="small" variant="text" @click="openItem(item)">打开</t-button>
          </div>
        </article>
      </div>
    </t-card>
  </div>
</template>
<script setup lang="ts">
import { MessagePlugin } from 'tdesign-vue-next';
import { onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';

import type { MyWorkItem } from '@/api/odoo';
import { completeMyWorkItem, completeMyWorkItemsBatch, executeMyWorkAction, fetchMyWorkSummary } from '@/api/odoo';
import { resolveBusinessTarget } from '@/utils/route/businessTarget';

const router = useRouter();
const loading = ref(false);
const error = ref('');
const search = ref('');
const section = ref('all');
const summary = ref<Array<{ key: string; label: string; count: number }>>([]);
const items = ref<MyWorkItem[]>([]);
const sectionOptions = ref([{ value: 'all', label: '全部事项' }]);
const busyKey = ref('');
const batching = ref(false);
const selectedIds = ref<number[]>([]);
const sortBy = ref('id:desc');
const sortOptions = [
  { label: '最新事项', value: 'id:desc' },
  { label: '最早事项', value: 'id:asc' },
  { label: '截止日期升序', value: 'deadline:asc' },
  { label: '优先级降序', value: 'priority:desc' },
];

async function load() {
  loading.value = true;
  error.value = '';
  try {
    const [sortField, sortDir] = sortBy.value.split(':');
    const result = await fetchMyWorkSummary({
      section: section.value,
      search: search.value,
      sortBy: sortField,
      sortDir: sortDir as 'asc' | 'desc',
    });
    summary.value = result.summary || [];
    const productSections = result.product_workspace?.sections || [];
    if (productSections.length) {
      sectionOptions.value = [
        { value: 'all', label: '全部事项' },
        ...productSections.map((item) => ({ value: item.key, label: `${item.label} (${item.count})` })),
      ];
      items.value = productSections.flatMap((item) => item.items || []);
      if (section.value !== 'all')
        items.value = productSections.find((item) => item.key === section.value)?.items || [];
    } else {
      items.value = result.items || result.sections?.flatMap((item) => item.items || []) || [];
      sectionOptions.value = [
        { value: 'all', label: '全部事项' },
        ...(result.sections || []).map((item) => ({ value: item.key, label: item.label })),
      ];
    }
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '工作事项加载失败';
  } finally {
    loading.value = false;
  }
}

function priorityTheme(priority: string) {
  return priority === 'high' || priority === 'urgent' ? 'danger' : priority === 'medium' ? 'warning' : 'default';
}
function priorityLabel(priority: string) {
  return priority === 'high' || priority === 'urgent' ? '高优先级' : priority === 'medium' ? '中优先级' : '普通';
}

function openItem(item: MyWorkItem) {
  const target = resolveBusinessTarget(
    item.target || { model: item.model, record_id: item.record_id },
    router.getRoutes(),
  );
  if (target) void router.push(target);
  else MessagePlugin.warning('当前事项没有可用的业务入口');
}

function toggleSelected(id: number) {
  selectedIds.value = selectedIds.value.includes(id)
    ? selectedIds.value.filter((item) => item !== id)
    : [...selectedIds.value, id];
}
async function completeBatch() {
  if (!selectedIds.value.length) return;
  batching.value = true;
  try {
    const result = await completeMyWorkItemsBatch({ ids: selectedIds.value });
    MessagePlugin.success(result.message || `已完成 ${result.done_count || selectedIds.value.length} 项`);
    selectedIds.value = [];
    await load();
  } catch (cause) {
    MessagePlugin.error(cause instanceof Error ? cause.message : '批量完成失败');
  } finally {
    batching.value = false;
  }
}

async function runAction(item: MyWorkItem, action: NonNullable<MyWorkItem['actions']>[number]) {
  if (!action.intent) return;
  busyKey.value = `${item.id}:${action.key}`;
  try {
    if (action.intent === 'my.work.complete' && item.id)
      await completeMyWorkItem({ id: item.id, source: item.section || 'todo' });
    else await executeMyWorkAction(action);
    MessagePlugin.success(`${action.label}已完成`);
    await load();
  } catch (cause) {
    MessagePlugin.error(cause instanceof Error ? cause.message : `${action.label}失败`);
  } finally {
    busyKey.value = '';
  }
}

onMounted(load);
</script>
<style scoped>
.my-work-page {
  display: grid;
  gap: 16px;
}
.page-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}
.page-heading h1 {
  margin: 4px 0 8px;
  font-size: 28px;
}
.page-heading p {
  margin: 0;
  color: var(--td-text-color-secondary);
}
.eyebrow {
  color: var(--td-brand-color) !important;
  font-size: 13px;
}
.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 16px;
}
.summary-grid :deep(.t-card) {
  display: grid;
  gap: 8px;
  border: 1px solid var(--td-border-level-1-color);
}
.summary-grid span {
  color: var(--td-text-color-secondary);
}
.summary-grid strong {
  font-size: 28px;
}
.work-panel {
  border: 1px solid var(--td-border-level-1-color);
}
.work-toolbar {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
}
.work-toolbar .t-input {
  max-width: 420px;
}
.work-list {
  display: grid;
  gap: 10px;
}
.work-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 16px;
  border: 1px solid var(--td-border-level-1-color);
  border-radius: 6px;
}
.work-item__title {
  display: flex;
  align-items: center;
  gap: 10px;
}
.work-item h3 {
  margin: 0;
  font-size: 15px;
}
.work-item p,
.work-item small {
  margin: 6px 0 0;
  color: var(--td-text-color-secondary);
  font-size: 12px;
}
.work-item__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}
@media (width <= 720px) {
  .page-heading,
  .work-item {
    align-items: flex-start;
    flex-direction: column;
  }
  .work-item__actions {
    justify-content: flex-start;
  }
  .work-toolbar {
    flex-direction: column;
  }
  .work-toolbar .t-input {
    max-width: none;
  }
}
</style>
