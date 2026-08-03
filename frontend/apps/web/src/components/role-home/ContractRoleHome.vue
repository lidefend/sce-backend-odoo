<template>
  <div class="contract-role-home" data-role-home data-role-home-renderer="contract">
    <header class="contract-role-home__header">
      <div>
        <h1>{{ title }}</h1>
        <p>{{ subtitle }}</p>
      </div>
      <div class="contract-role-home__header-mark"><ScIcon name="briefcase" :size="20" /><span>合同业务工作台</span></div>
    </header>

    <section class="contract-role-home__tasks" aria-labelledby="role-home-task-title">
      <div class="contract-role-home__section-heading">
        <div>
          <p>当前事项</p>
          <h2 id="role-home-task-title">待我处理</h2>
        </div>
        <button type="button" @click="navigate('/my-work')">查看全部</button>
      </div>
      <p v-if="loading" class="contract-role-home__state" role="status" aria-live="polite">正在加载当前事项。</p>
      <div v-else-if="error" class="contract-role-home__state" role="alert">
        <p>{{ error }}</p>
        <button type="button" @click="load">重试</button>
      </div>
      <div v-else-if="tasks.length" class="contract-role-home__task-list">
        <article v-for="task in tasks" :key="task.key">
          <div>
            <h3>{{ task.label }}</h3>
            <p v-if="task.detail">{{ task.detail }}</p>
          </div>
          <button type="button" @click="navigate(task.route)">打开</button>
        </article>
      </div>
      <p v-else class="contract-role-home__state">当前没有待处理事项。</p>
    </section>

    <section class="contract-role-home__overview" aria-labelledby="role-home-overview-title">
      <div class="contract-role-home__section-heading">
        <div>
          <p>工作概览</p>
          <h2 id="role-home-overview-title">当前状态</h2>
        </div>
      </div>
      <div v-if="summaries.length" class="contract-role-home__summary-list">
        <article v-for="summary in summaries" :key="summary.key">
          <span class="contract-role-home__summary-label"><ScIcon :name="summaryIcon(summary.key)" :size="18" />{{ summary.label }}</span>
          <strong>{{ summary.value }}</strong>
        </article>
      </div>
      <p v-else class="contract-role-home__state">当前没有可汇总事项。</p>
    </section>

    <section class="contract-role-home__access" aria-labelledby="role-home-access-title">
      <div class="contract-role-home__section-heading">
        <div>
          <p>工作入口</p>
          <h2 id="role-home-access-title">常用入口与最近访问</h2>
        </div>
      </div>
      <div class="contract-role-home__access-grid">
        <div>
          <h3>常用入口</h3>
          <div v-if="quickLinks.length" class="contract-role-home__link-list">
            <button v-for="link in quickLinks" :key="link.key" type="button" @click="navigate(link.route)">
              <ScIcon :name="entryIcon(link.key)" :size="18" />
              <span><strong>{{ link.label }}</strong><small v-if="link.detail && link.detail !== link.label">{{ link.detail }}</small></span>
              <ScIcon name="arrow-right" :size="16" />
            </button>
          </div>
          <p v-else class="contract-role-home__state">当前没有可用入口。</p>
        </div>
        <div>
          <h3>最近访问</h3>
          <div v-if="recentItems.length" class="contract-role-home__link-list">
            <button v-for="item in recentItems" :key="item.key" type="button" @click="navigate(item.route)">
              <strong>{{ item.label }}</strong>
            </button>
          </div>
          <p v-else class="contract-role-home__state">打开业务页面后，最近访问会显示在这里。</p>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { useContractRoleHome } from '../../composables/shared-surface/useContractRoleHome';
import ScIcon from '../design-system/ScIcon.vue';

type HomeIconName = 'briefcase' | 'folder' | 'building' | 'apps';

function summaryIcon(key: string): HomeIconName {
  return /launch|start|create/i.test(String(key || '')) ? 'folder' : 'briefcase';
}

function entryIcon(key: string): HomeIconName {
  if (/project/i.test(String(key || ''))) return 'folder';
  if (/contract/i.test(String(key || ''))) return 'briefcase';
  return 'apps';
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
} = useContractRoleHome();
</script>

<style scoped>
.contract-role-home {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(300px, .65fr);
  gap: var(--sc-space-4, 16px);
  width: 100%;
  margin: 0;
  min-width: 0;
  align-items: start;
}

.contract-role-home__header,
.contract-role-home__tasks,
.contract-role-home__overview,
.contract-role-home__access {
  border: 1px solid var(--sc-app-border);
  border-radius: var(--sc-product-radius-panel);
  background: var(--sc-app-panel);
}

.contract-role-home__header {
  grid-column: 1 / -1;
  position: relative;
  overflow: hidden;
  min-height: 86px;
  box-sizing: border-box;
  padding: 16px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sc-space-4, 16px);
  border-color: var(--sc-app-info-border);
  background: linear-gradient(118deg, color-mix(in srgb, var(--sc-semantic-surface-interactive) 78%, var(--sc-app-panel)), color-mix(in srgb, var(--sc-semantic-surface-interactive) 62%, var(--sc-app-panel)));
}

.contract-role-home__header-mark {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 38px;
  padding: 0 14px;
  border: 1px solid color-mix(in srgb, var(--sc-semantic-text-on-interactive) 28%, transparent);
  border-radius: 999px;
  background: color-mix(in srgb, var(--sc-semantic-text-on-interactive) 12%, transparent);
  color: var(--sc-semantic-text-on-interactive);
  font-weight: 600;
}

.contract-role-home__header::before {
  position: absolute;
  top: -52px;
  right: -24px;
  width: 164px;
  height: 164px;
  border: 28px solid color-mix(in srgb, var(--sc-semantic-text-on-interactive) 10%, transparent);
  border-radius: 50%;
  content: '';
}

.contract-role-home__header h1,
.contract-role-home__header p,
.contract-role-home__section-heading p,
.contract-role-home__section-heading h2,
.contract-role-home__access h3,
.contract-role-home__task-list h3,
.contract-role-home__task-list p {
  margin: 0;
}

.contract-role-home__header h1 {
  position: relative;
  color: var(--sc-semantic-text-on-interactive);
  font-size: 24px;
  line-height: 1.35;
}

.contract-role-home__header p,
.contract-role-home__task-list p,
.contract-role-home__link-list span,
.contract-role-home__state {
  color: var(--sc-app-text-secondary);
}

.contract-role-home__header p {
  position: relative;
  margin-top: var(--sc-space-2, 8px);
  color: color-mix(in srgb, var(--sc-semantic-text-on-interactive) 88%, transparent);
}

.contract-role-home__tasks,
.contract-role-home__overview,
.contract-role-home__access {
  padding: 14px 16px;
  box-shadow: 0 4px 14px color-mix(in srgb, var(--sc-app-shadow) 9%, transparent);
}

.contract-role-home__access { grid-column: 1 / -1; }

.contract-role-home__section-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sc-space-3, 12px);
  margin-bottom: var(--sc-space-3, 12px);
  padding-bottom: 10px;
  border-bottom: 1px solid var(--sc-app-border);
}

.contract-role-home__section-heading p {
  color: var(--sc-app-text-secondary);
  font-size: 12px;
}

.contract-role-home__section-heading h2 {
  margin-top: 2px;
  font-size: 17px;
}

.contract-role-home button {
  min-height: 32px;
  border: 1px solid var(--sc-app-border-strong);
  border-radius: 4px;
  background: var(--sc-app-input-bg);
  color: var(--sc-app-text-primary);
  cursor: pointer;
}

.contract-role-home button:hover,
.contract-role-home button:focus-visible {
  border-color: var(--sc-semantic-surface-interactive);
  background: var(--sc-app-info-bg);
}

.contract-role-home__task-list {
  display: grid;
  gap: var(--sc-space-2, 8px);
}

.contract-role-home__task-list article {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sc-space-3, 12px);
  padding: var(--sc-space-3, 12px);
  border: 1px solid var(--sc-app-border);
  border-radius: 4px;
}

.contract-role-home__task-list button,
.contract-role-home__section-heading button {
  flex: none;
  padding: 0 var(--sc-space-3, 12px);
}

.contract-role-home__summary-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(128px, 1fr));
  gap: var(--sc-space-3, 12px);
}

.contract-role-home__summary-list article {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--sc-space-2, 8px);
  min-height: 54px;
  padding: 10px 12px;
  border: 1px solid var(--sc-app-border);
  border-radius: var(--sc-product-radius-control);
  border-color: var(--sc-app-border);
  border-left: 3px solid var(--sc-semantic-surface-interactive);
  background: var(--sc-app-panel);
  box-shadow: none;
}

.contract-role-home__summary-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--sc-app-text-secondary);
}

.contract-role-home__summary-label .sc-icon { color: var(--sc-app-info-text); }

.contract-role-home__summary-list strong {
  color: var(--sc-app-info-text);
  font-size: 22px;
}

.contract-role-home__access-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--sc-space-4, 16px);
}

.contract-role-home__link-list {
  display: grid;
  gap: var(--sc-space-2, 8px);
  margin-top: var(--sc-space-2, 8px);
}

.contract-role-home__link-list button {
  display: grid;
  grid-template-columns: 32px minmax(0, 1fr) 18px;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: var(--sc-space-3, 12px);
  text-align: left;
  border-left: 3px solid var(--sc-app-info-border);
  transition: transform var(--sc-motion-fast, 120ms) ease, border-color var(--sc-motion-fast, 120ms) ease;
}

.contract-role-home__link-list button > .sc-icon:first-child {
  width: 32px;
  height: 32px;
  padding: 7px;
  border-radius: 8px;
  background: var(--sc-app-info-bg);
  color: var(--sc-app-info-text);
}

.contract-role-home__link-list button > span {
  display: grid;
  gap: 2px;
}

.contract-role-home__link-list button small {
  color: var(--sc-app-text-secondary);
  font-size: 12px;
}

.contract-role-home__link-list button:hover {
  transform: translateY(-1px);
  border-left-color: var(--sc-semantic-surface-interactive);
}

.contract-role-home__state {
  margin: 0;
  padding: var(--sc-space-3, 12px);
  border-radius: 4px;
  background: var(--sc-app-subtle-bg);
}

@media (max-width: 700px) {
  .contract-role-home {
    grid-template-columns: 1fr;
    gap: var(--sc-space-3, 12px);
  }

  .contract-role-home__tasks { order: 1; }
  .contract-role-home__overview { order: 2; }
  .contract-role-home__access { order: 3; }

  .contract-role-home__header-mark { display: none; }

  .contract-role-home__access-grid {
    grid-template-columns: 1fr;
  }

  .contract-role-home__task-list article {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
