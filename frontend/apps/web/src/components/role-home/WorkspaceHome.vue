<template>
  <div class="role-home-surface" data-role-home data-role-home-renderer="workspace-contract" data-semantic-component="WorkspaceHome" :data-state="loading ? 'loading' : error ? 'error' : 'ready'" :aria-busy="loading || undefined">
    <section class="role-home-surface__tasks" aria-labelledby="role-home-task-title">
      <div class="role-home-surface__section-heading">
        <div>
          <p>当前事项</p>
          <h2 id="role-home-task-title">待我处理</h2>
        </div>
        <ScButton type="button" variant="ghost" appearance="dashboard-action" @click="navigate('/my-work')">查看全部</ScButton>
      </div>
      <ScInlineState v-if="loading" state="loading" label="正在加载当前事项。" />
      <ScInlineState v-else-if="error" state="error" :label="error">
        <template #actions><ScButton type="button" variant="secondary" @click="load">重试</ScButton></template>
      </ScInlineState>
      <div v-else-if="tasks.length" class="role-home-surface__task-list">
        <article v-for="task in tasks" :key="task.key" :data-record-id="task.recordId" :data-work-item-state="task.state?.key">
          <div class="role-home-surface__task-copy">
            <div class="role-home-surface__task-heading">
              <h3>{{ task.kind || task.label }}</h3>
              <ScStatusBadge v-if="task.state?.label" :value="task.state.key" :label="task.state.label" />
              <ScMoney v-if="task.amount" class="role-home-surface__task-amount" :label="task.amount.label" :display="formatFact(task.amount)" />
            </div>
            <p v-if="task.kind" class="role-home-surface__task-record" :title="task.label">{{ task.label }}</p>
            <dl v-if="task.facts.length" class="role-home-surface__task-facts">
              <div v-for="fact in task.facts" :key="fact.key">
                <dt>{{ fact.label }}</dt>
                <dd><ScMoney v-if="fact.display_role === 'money'" :display="formatFact(fact)" /><template v-else>{{ formatFact(fact) }}</template></dd>
              </div>
            </dl>
          </div>
          <ScButton type="button" variant="ghost" appearance="dashboard-action" :aria-label="`打开：${task.label}`" @click="navigate(task.route)">打开</ScButton>
        </article>
      </div>
      <ScInlineState v-else state="empty" label="当前没有待处理事项。" />
    </section>

    <section class="role-home-surface__overview" aria-labelledby="role-home-overview-title">
      <div class="role-home-surface__section-heading">
        <div>
          <p>工作概览</p>
          <h2 id="role-home-overview-title">当前状态</h2>
        </div>
      </div>
      <div v-if="summaries.length" class="role-home-surface__summary-list">
        <article v-for="summary in summaries" :key="summary.key">
          <span class="role-home-surface__summary-label"><ScIcon :name="summaryIcon(summary.key)" :size="18" />{{ summary.label }}</span>
          <strong>{{ summary.value }}</strong>
        </article>
      </div>
      <p v-else class="role-home-surface__state">当前没有可汇总事项。</p>
    </section>

    <section class="role-home-surface__access" aria-labelledby="role-home-access-title">
      <div class="role-home-surface__section-heading">
        <div>
          <p>工作入口</p>
          <h2 id="role-home-access-title">常用入口与最近访问</h2>
        </div>
      </div>
      <div class="role-home-surface__access-grid">
        <div>
          <h3>常用入口</h3>
          <div v-if="quickLinks.length" class="role-home-surface__link-list role-home-surface__link-list--quick">
            <ScButton v-for="link in quickLinks" :key="link.key" type="button" variant="ghost" appearance="dashboard-quick-link" @click="navigate(link.route)">
              <ScIcon class="role-home-surface__entry-icon" :name="entryIcon(link.key)" :size="18" />
              <span class="role-home-surface__entry-copy">
                <strong>{{ link.label }}</strong>
                <small v-if="link.detail && link.detail !== link.label">{{ link.detail }}</small>
              </span>
              <ScIcon class="role-home-surface__entry-arrow" name="arrow-right" :size="16" />
            </ScButton>
          </div>
          <p v-else class="role-home-surface__state">当前没有可用入口。</p>
        </div>
        <div>
          <h3>最近访问</h3>
          <div v-if="recentItems.length" class="role-home-surface__link-list role-home-surface__link-list--recent">
            <ScButton v-for="item in recentItems" :key="item.key" type="button" variant="ghost" appearance="dashboard-recent-link" @click="navigate(item.route)">
              <strong>{{ item.label }}</strong>
            </ScButton>
          </div>
          <p v-else class="role-home-surface__state">打开业务页面后，最近访问会显示在这里。</p>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { useWorkspaceHome } from '../../composables/shared-surface/useWorkspaceHome';
import ScButton from '../design-system/ScButton.vue';
import ScIcon from '../design-system/ScIcon.vue';
import ScInlineState from '../design-system/ScInlineState.vue';
import ScStatusBadge from '../design-system/ScStatusBadge.vue';
import ScMoney from '../design-system/ScMoney.vue';
import type { ProductMyWorkFact } from '../../api/myWork';
import { formatProductMyWorkFact } from '../../app/presentation/productMyWorkPresentation';

const formatFact = (fact: ProductMyWorkFact) => formatProductMyWorkFact(fact);

type HomeIconName = 'briefcase' | 'folder' | 'building' | 'apps';

function summaryIcon(key: string): HomeIconName {
  return String(key || '').trim() ? 'briefcase' : 'apps';
}

function entryIcon(key: string): HomeIconName {
  return String(key || '').trim() ? 'apps' : 'folder';
}

const {
  tasks,
  summaries,
  quickLinks,
  recentItems,
  loading,
  error,
  load,
  navigate,
} = useWorkspaceHome();
</script>

<style scoped>
.role-home-surface {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(300px, .65fr);
  gap: var(--sc-space-4, 16px);
  width: 100%;
  margin: 0;
  min-width: 0;
  align-items: start;
}

.role-home-surface__tasks,
.role-home-surface__overview,
.role-home-surface__access {
  background: var(--sc-app-panel);
  min-width: 0;
}

.role-home-surface__section-heading p,
.role-home-surface__section-heading h2,
.role-home-surface__access h3,
.role-home-surface__task-list h3,
.role-home-surface__task-list p {
  margin: 0;
}

.role-home-surface__task-list p,
.role-home-surface__link-list span,
.role-home-surface__state {
  color: var(--sc-app-text-secondary);
}

.role-home-surface__tasks,
.role-home-surface__overview,
.role-home-surface__access {
  padding: var(--sc-surface-padding);
  border: 1px solid var(--sc-app-border);
  border-radius: var(--sc-product-radius-panel);
}

.role-home-surface__access { grid-column: 1 / -1; }

@media (min-width: 961px) {
  .role-home-surface__tasks { grid-row: 1 / span 2; }
  .role-home-surface__overview,
  .role-home-surface__access { grid-column: 2; }
  .role-home-surface__access-grid { grid-template-columns: 1fr; }
  .role-home-surface__access-grid > div + div {
    padding-top: var(--sc-space-3, 12px);
    border-top: 1px solid var(--sc-app-border);
  }
}

.role-home-surface__section-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sc-space-3, 12px);
  margin-bottom: var(--sc-space-3, 12px);
  padding-bottom: 10px;
  border-bottom: 1px solid var(--sc-app-border);
}

.role-home-surface__section-heading p {
  color: var(--sc-app-text-secondary);
  font-size: 12px;
}

.role-home-surface__section-heading h2 {
  margin-top: 2px;
  font-size: 17px;
}

.role-home-surface__task-list {
  display: grid;
  gap: var(--sc-space-2, 8px);
}

.role-home-surface__task-list article {
  display: flex;
  min-width: 0;
  align-items: center;
  justify-content: space-between;
  gap: var(--sc-space-3, 12px);
  padding: var(--sc-space-3, 12px) 0;
  border-bottom: 1px solid var(--sc-app-border);
}

.role-home-surface__task-list article:first-child { padding-top: 0; }
.role-home-surface__task-list article:last-child { padding-bottom: 0; border-bottom: 0; }

.role-home-surface__task-list :deep(.sc-btn),
.role-home-surface__section-heading :deep(.sc-btn) {
  flex: none;
}

.role-home-surface__task-copy { min-width: 0; flex: 1; }
.role-home-surface__task-heading { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; }
.role-home-surface__task-heading h3 { font-size: 14px; line-height: 1.5; overflow-wrap: anywhere; }
.role-home-surface__task-list .role-home-surface__task-record { margin-top: 4px; font-size: 12px; line-height: 1.5; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.role-home-surface__task-amount { margin-left: auto; font-weight: 600; max-width: 100%; overflow-wrap: anywhere; white-space: normal; }
.role-home-surface__task-facts { display: flex; flex-wrap: wrap; gap: 4px 16px; margin: 8px 0 0; font-size: 12px; line-height: 1.5; }
.role-home-surface__task-facts > div { min-width: 0; }
.role-home-surface__task-facts dt { color: var(--sc-app-text-muted); }
.role-home-surface__task-facts dd { margin: 0; color: var(--sc-app-text-primary); overflow-wrap: anywhere; }
.role-home-surface__task-list :deep(.sc-btn) { min-height: 44px; align-self: flex-start; }

.role-home-surface__summary-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(128px, 1fr));
  gap: var(--sc-space-3, 12px);
}

.role-home-surface__summary-list article {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--sc-space-2, 8px);
  min-height: 54px;
  padding: 10px 12px;
  border-radius: var(--sc-product-radius-control);
  background: var(--sc-app-subtle-bg);
  box-shadow: none;
}

.role-home-surface__summary-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--sc-app-text-secondary);
}

.role-home-surface__summary-label .sc-icon { color: var(--sc-app-text-secondary); }

.role-home-surface__summary-list strong {
  color: var(--sc-app-text-primary);
  font-size: 22px;
}

.role-home-surface__access-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--sc-space-4, 16px);
}

.role-home-surface__link-list {
  display: grid;
  gap: var(--sc-space-2, 8px);
  margin-top: var(--sc-space-2, 8px);
}

.role-home-surface__link-list--quick :deep(.sc-btn) {
  width: 100%;
  min-height: 58px;
  height: auto;
  padding: 9px 10px;
  text-align: left;
}

.role-home-surface__link-list--quick :deep(.sc-btn__content) {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--sc-space-3, 12px);
  width: 100%;
}

.role-home-surface__entry-icon,
.role-home-surface__entry-arrow {
  flex: none;
}

.role-home-surface__entry-copy {
  display: grid;
  gap: 2px;
  min-width: 0;
  line-height: 1.35;
}

.role-home-surface__entry-copy strong,
.role-home-surface__entry-copy small {
  display: block;
  min-width: 0;
  overflow-wrap: anywhere;
}

.role-home-surface__entry-copy strong {
  color: var(--sc-app-text-primary);
  font-size: 14px;
}

.role-home-surface__entry-copy small {
  color: var(--sc-app-text-secondary);
  font-size: 12px;
  font-weight: 400;
}

.role-home-surface__entry-arrow {
  color: var(--sc-app-text-muted);
}

.role-home-surface__state {
  margin: 0;
  padding: var(--sc-space-3, 12px);
  border-radius: 4px;
  background: var(--sc-app-subtle-bg);
}

@media (max-width: 960px) {
  .role-home-surface {
    grid-template-columns: 1fr;
    gap: var(--sc-space-3, 12px);
  }

  .role-home-surface__tasks { order: 2; }
  .role-home-surface__overview { order: 1; }
  .role-home-surface__access { order: 3; }

  .role-home-surface__access-grid {
    grid-template-columns: 1fr;
  }

  .role-home-surface__access-grid > div + div {
    padding-top: var(--sc-space-3, 12px);
    border-top: 1px solid var(--sc-app-border);
  }

  .role-home-surface__task-list article {
    align-items: flex-start;
    flex-direction: row;
  }

  .role-home-surface :deep(.sc-btn) {
    min-height: 44px;
  }
}
</style>
