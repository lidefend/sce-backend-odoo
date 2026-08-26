<template>
  <div class="role-home-surface" data-role-home data-role-home-renderer="workspace-contract" data-semantic-component="WorkspaceHome" :data-state="loading ? 'loading' : error ? 'error' : 'ready'" :aria-busy="loading || undefined">
    <h1 class="sc-visually-hidden">{{ title }}</h1>
    <p class="sc-visually-hidden">{{ subtitle }}</p>

    <section class="role-home-surface__tasks" aria-labelledby="role-home-task-title">
      <div class="role-home-surface__section-heading">
        <div>
          <p>当前事项</p>
          <h2 id="role-home-task-title">待我处理</h2>
        </div>
        <ScButton type="button" variant="ghost" @click="navigate('/my-work')">查看全部</ScButton>
      </div>
      <ScInlineState v-if="loading" state="loading" label="正在加载当前事项。" />
      <ScInlineState v-else-if="error" state="error" :label="error">
        <template #actions><ScButton type="button" variant="secondary" @click="load">重试</ScButton></template>
      </ScInlineState>
      <div v-else-if="tasks.length" class="role-home-surface__task-list">
        <article v-for="task in tasks" :key="task.key">
          <div>
            <h3>{{ task.label }}</h3>
            <p v-if="task.detail">{{ task.detail }}</p>
          </div>
          <ScButton type="button" variant="ghost" @click="navigate(task.route)">打开</ScButton>
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
            <ScButton v-for="link in quickLinks" :key="link.key" type="button" variant="ghost" @click="navigate(link.route)">
              <ScIcon :name="entryIcon(link.key)" :size="18" />
              <span><strong>{{ link.label }}</strong><small v-if="link.detail && link.detail !== link.label">{{ link.detail }}</small></span>
              <ScIcon name="arrow-right" :size="16" />
            </ScButton>
          </div>
          <p v-else class="role-home-surface__state">当前没有可用入口。</p>
        </div>
        <div>
          <h3>最近访问</h3>
          <div v-if="recentItems.length" class="role-home-surface__link-list role-home-surface__link-list--recent">
            <ScButton v-for="item in recentItems" :key="item.key" type="button" variant="ghost" @click="navigate(item.route)">
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

type HomeIconName = 'briefcase' | 'folder' | 'building' | 'apps';

function summaryIcon(key: string): HomeIconName {
  return String(key || '').trim() ? 'briefcase' : 'apps';
}

function entryIcon(key: string): HomeIconName {
  return String(key || '').trim() ? 'apps' : 'folder';
}

const {
  title,
  subtitle,
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

.role-home-surface :deep(.sc-btn) {
  min-height: 32px;
  border: 1px solid var(--sc-app-border-strong);
  border-radius: 4px;
  background: var(--sc-app-input-bg);
  color: var(--sc-app-text-primary);
  cursor: pointer;
}

.role-home-surface :deep(.sc-btn:hover) {
  border-color: var(--sc-app-border-strong);
  background: var(--sc-app-hover-bg);
  color: var(--sc-app-text-primary);
}

.role-home-surface :deep(.sc-btn:focus-visible) {
  outline: 2px solid var(--sc-app-focus-ring);
  outline-offset: 2px;
}

.role-home-surface__task-list {
  display: grid;
  gap: var(--sc-space-2, 8px);
}

.role-home-surface__task-list article {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sc-space-3, 12px);
  padding: var(--sc-space-3, 12px);
  border: 1px solid var(--sc-app-border);
  border-radius: 4px;
}

.role-home-surface__task-list :deep(.sc-btn),
.role-home-surface__section-heading :deep(.sc-btn) {
  flex: none;
  padding: 0 var(--sc-space-3, 12px);
}

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
  border: 1px solid var(--sc-app-border);
  border-radius: var(--sc-product-radius-control);
  border-color: var(--sc-app-border);
  border-left: 3px solid var(--sc-app-border);
  background: var(--sc-app-panel);
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
  display: grid;
  grid-template-columns: 32px minmax(0, 1fr) 18px;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: var(--sc-space-3, 12px);
  text-align: left;
  border-left: 3px solid var(--sc-app-border);
  transition: transform var(--sc-motion-fast, 120ms) ease, border-color var(--sc-motion-fast, 120ms) ease;
}

.role-home-surface__link-list--quick :deep(.sc-btn > .sc-btn__content > .sc-icon:first-child) {
  width: 32px;
  height: 32px;
  padding: 7px;
  border-radius: 8px;
  background: var(--sc-app-subtle-bg);
  color: var(--sc-text-link);
}

.role-home-surface__link-list--quick :deep(.sc-btn > .sc-btn__content > span) {
  display: grid;
  gap: 2px;
}

.role-home-surface__link-list :deep(.sc-btn small) {
  color: var(--sc-app-text-secondary);
  font-size: 12px;
}

.role-home-surface__link-list--recent :deep(.sc-btn) {
  display: block;
  width: 100%;
  min-width: 0;
  min-height: 40px;
  padding: 8px 12px;
  overflow-wrap: anywhere;
  text-align: left;
  white-space: normal;
}

.role-home-surface__link-list :deep(.sc-btn:hover) {
  transform: translateY(-1px);
  border-left-color: var(--sc-app-border-strong);
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

  .role-home-surface__tasks { order: 1; }
  .role-home-surface__overview { order: 2; }
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
    flex-direction: column;
  }

  .role-home-surface :deep(.sc-btn) {
    min-height: 44px;
  }
}
</style>
