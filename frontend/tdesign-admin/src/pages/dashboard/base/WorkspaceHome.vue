<template>
  <div class="workspace-home">
    <section class="workspace-hero">
      <div>
        <p class="eyebrow">{{ hero.role_label || '当前角色' }}</p>
        <h1>{{ hero.title || '角色首页' }}</h1>
        <p class="hero-subtitle">{{ hero.subtitle || '根据当前公司、项目和权限范围展示实时业务概览。' }}</p>
      </div>
      <div class="hero-meta">
        <t-tag :theme="hero.status_notice ? 'warning' : 'success'" variant="light">{{
          hero.status_notice || '状态正常'
        }}</t-tag>
        <span>更新时间：{{ hero.updated_at || '—' }}</span>
      </div>
    </section>

    <t-alert v-if="error" theme="error" :message="error" />
    <div v-if="loading" class="workspace-loading"><t-skeleton animation="gradient" :row-col="skeletonRows" /></div>
    <template v-else>
      <section class="metric-grid">
        <t-card v-for="metric in metrics" :key="metric.key || metric.label" class="metric-card" :bordered="false">
          <span>{{ metric.label || metric.name || metric.key }}</span>
          <strong>{{ metric.value ?? metric.count ?? '—' }}</strong>
          <small v-if="metric.note">{{ metric.note }}</small>
        </t-card>
      </section>

      <div class="workspace-grid">
        <t-card class="workspace-panel" :bordered="false">
          <template #title>今日行动</template>
          <template #actions><t-button variant="text" @click="router.push('/my-work')">查看全部</t-button></template>
          <div v-if="todayActions.length" class="action-list">
            <div v-for="item in todayActions.slice(0, 8)" :key="item.key || item.id || item.title" class="action-row">
              <div>
                <strong>{{ item.title || item.label || item.name || '待处理事项' }}</strong>
                <p>{{ item.detail || item.subtitle || item.description || '' }}</p>
              </div>
              <t-button size="small" variant="outline" @click="openTarget(item)">{{
                item.action_label || '打开'
              }}</t-button>
            </div>
          </div>
          <t-empty v-else description="当前没有待处理事项" />
        </t-card>

        <t-card class="workspace-panel" :bordered="false">
          <template #title>关键事项</template>
          <div class="risk-buckets">
            <div v-for="bucket in riskBuckets" :key="bucket.key" class="risk-bucket" :data-tone="bucket.tone">
              <span>{{ bucket.label }}</span
              ><strong>{{ bucket.value }}</strong>
            </div>
          </div>
          <div v-if="riskActions.length" class="risk-list">
            <div v-for="item in riskActions.slice(0, 5)" :key="item.key || item.id || item.title" class="risk-row">
              <span>{{ item.title || item.label || item.name }}</span
              ><t-button size="small" variant="text" @click="openTarget(item)">查看</t-button>
            </div>
          </div>
          <t-empty v-else description="当前没有风险事项" />
        </t-card>
      </div>

      <t-card class="workspace-panel" :bordered="false">
        <template #title>常用功能</template>
        <div v-if="quickLinks.length" class="quick-link-grid">
          <t-button
            v-for="link in quickLinks"
            :key="link.key || link.route || link.label"
            variant="outline"
            class="quick-link"
            @click="openTarget(link)"
          >
            <span>{{ link.label || link.title || link.key }}</span
            ><small v-if="link.detail">{{ link.detail }}</small
            ><t-icon name="chevron-right" />
          </t-button>
        </div>
        <t-empty v-else description="当前没有可用入口" />
      </t-card>
    </template>
  </div>
</template>
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';

import { useUserStore } from '@/store';

type Dict = Record<string, any>;
const router = useRouter();
const user = useUserStore();
const loading = ref(false);
const error = ref('');
const home = computed(() => (user.workspaceHome || {}) as Dict);
const hero = computed(() => (home.value.hero || home.value.record?.hero || {}) as Dict);
const metrics = computed(() => normalizeRows(home.value.metrics || home.value.platform_metrics));
const todayActions = computed(() => normalizeRows(home.value.today_actions || home.value.todayActions));
const risk = computed(() => (home.value.risk || {}) as Dict);
const riskActions = computed(() => normalizeRows(risk.value.actions));
const quickLinks = computed(() =>
  normalizeRows(home.value.quick_links || home.value.scene_groups || home.value.group_overview),
);
const riskBuckets = computed(() => {
  const buckets = risk.value.buckets && typeof risk.value.buckets === 'object' ? risk.value.buckets : {};
  return Object.entries(buckets).map(([key, value]) => {
    const row = value && typeof value === 'object' ? (value as Dict) : { value };
    return { key, label: String(row.label || key), value: row.value ?? row.count ?? 0, tone: String(row.tone || key) };
  });
});
const skeletonRows = [
  [{ type: 'rect' as const, width: '100%', height: '96px' }],
  [{ type: 'rect' as const, width: '100%', height: '180px' }],
  [{ type: 'rect' as const, width: '100%', height: '180px' }],
];

function normalizeRows(value: unknown): Dict[] {
  if (!Array.isArray(value)) return [];
  return value.filter((row): row is Dict => Boolean(row && typeof row === 'object'));
}

function openTarget(row: Dict) {
  const route = String(row.route || row.target?.route || row.url || '').trim();
  if (route.startsWith('/')) router.push(route);
  else if (row.action_id || row.actionId) router.push({ query: { action_id: String(row.action_id || row.actionId) } });
}

onMounted(async () => {
  if (Object.keys(home.value).length) return;
  loading.value = true;
  try {
    await user.getUserInfo();
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '工作台加载失败';
  } finally {
    loading.value = false;
  }
});
</script>
<style scoped>
.workspace-home {
  display: grid;
  gap: 16px;
  min-width: 0;
}
.workspace-hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  padding: 24px 28px;
  background: var(--td-bg-color-container);
  border: 1px solid var(--td-border-level-1-color);
  border-radius: 8px;
}
.eyebrow {
  margin: 0 0 8px;
  color: var(--td-brand-color);
  font-size: 13px;
}
.workspace-hero h1 {
  margin: 0;
  font-size: 28px;
}
.hero-subtitle {
  margin: 8px 0 0;
  color: var(--td-text-color-secondary);
}
.hero-meta {
  display: grid;
  justify-items: end;
  gap: 10px;
  color: var(--td-text-color-placeholder);
  font-size: 12px;
}
.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
}
.metric-card {
  display: grid;
  gap: 8px;
  border: 1px solid var(--td-border-level-1-color);
}
.metric-card span,
.metric-card small {
  color: var(--td-text-color-secondary);
}
.metric-card strong {
  font-size: 28px;
  font-weight: 600;
}
.workspace-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(320px, 0.8fr);
  gap: 16px;
}
.workspace-panel {
  border: 1px solid var(--td-border-level-1-color);
}
.action-list,
.risk-list {
  display: grid;
  gap: 10px;
}
.action-row,
.risk-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px;
  border: 1px solid var(--td-border-level-1-color);
  border-radius: 6px;
}
.action-row strong {
  color: var(--td-text-color-primary);
}
.action-row p {
  margin: 4px 0 0;
  color: var(--td-text-color-secondary);
  font-size: 12px;
}
.risk-buckets {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-bottom: 14px;
}
.risk-bucket {
  display: grid;
  gap: 6px;
  padding: 12px;
  border-radius: 6px;
  background: var(--td-bg-color-secondarycontainer);
}
.risk-bucket span {
  color: var(--td-text-color-secondary);
  font-size: 12px;
}
.risk-bucket strong {
  font-size: 22px;
}
.risk-bucket[data-tone*='red'] {
  border-left: 3px solid var(--td-error-color);
}
.risk-bucket[data-tone*='amber'] {
  border-left: 3px solid var(--td-warning-color);
}
.risk-bucket[data-tone*='green'] {
  border-left: 3px solid var(--td-success-color);
}
.quick-link-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 10px;
}
.quick-link {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 6px;
  height: auto;
  padding: 14px;
  text-align: left;
}
.quick-link small {
  grid-column: 1;
  color: var(--td-text-color-secondary);
}
.quick-link .t-icon {
  grid-column: 2;
  grid-row: 1 / span 2;
  align-self: center;
}
.workspace-loading {
  padding: 24px;
  background: var(--td-bg-color-container);
  border-radius: 8px;
}
@media (width <= 820px) {
  .workspace-grid {
    grid-template-columns: minmax(0, 1fr);
  }
  .workspace-hero {
    flex-direction: column;
  }
  .hero-meta {
    justify-items: start;
  }
}
</style>
