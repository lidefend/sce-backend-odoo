<template>
  <section
    class="product-loading-shell"
    :class="`mode-${mode}`"
    role="status"
    aria-live="polite"
    aria-busy="true"
  >
    <header class="loading-toolbar">
      <div class="loading-title">
        <h2>{{ title }}</h2>
        <span>{{ loadingLabel }}</span>
      </div>
      <div class="loading-controls" aria-hidden="true">
        <i />
        <i />
        <i />
      </div>
    </header>

    <section v-if="mode === 'kanban'" class="loading-secondary-toolbar" aria-hidden="true">
      <i />
      <i />
      <i />
    </section>

    <section v-if="mode === 'kanban'" class="loading-card-grid" aria-hidden="true">
      <article v-for="index in 20" :key="index" class="loading-card">
        <i class="skeleton-line line-title" />
        <i class="skeleton-line line-wide" />
        <i class="skeleton-line line-medium" />
        <i class="skeleton-line line-short" />
      </article>
    </section>

    <section v-else class="loading-table" aria-hidden="true">
      <div class="loading-table-head">
        <i v-for="index in 6" :key="index" />
      </div>
      <div v-for="row in 8" :key="row" class="loading-table-row">
        <i v-for="column in 6" :key="column" :class="`cell-${column}`" />
      </div>
    </section>

    <footer class="loading-footer" :class="`mode-${mode}`" aria-hidden="true">
      <i />
      <i />
      <i />
      <i />
    </footer>
  </section>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    title: string;
    mode?: 'list' | 'kanban';
    loadingLabel?: string;
  }>(),
  {
    mode: 'list',
    loadingLabel: '正在载入数据',
  },
);
</script>

<style scoped>
.product-loading-shell {
  display: grid;
  align-content: start;
  gap: var(--sc-product-workspace-stack-gap);
  width: 100%;
  min-width: 0;
}

.loading-toolbar {
  box-sizing: border-box;
  display: flex;
  height: 42px;
  min-height: 42px;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border: 1px solid var(--sc-app-border);
  border-radius: 8px;
  background: var(--sc-app-panel);
  padding: 4px 12px;
  box-shadow: 0 8px 18px var(--sc-app-shadow);
}

.mode-kanban .loading-toolbar {
  height: 47px;
  min-height: 47px;
}

.loading-title {
  min-width: 0;
}

.loading-title h2 {
  margin: 0;
  overflow: hidden;
  color: var(--sc-app-text-primary);
  font-size: 16px;
  line-height: 1.25;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.loading-title span {
  display: block;
  margin-top: 3px;
  color: var(--sc-app-text-secondary);
  font-size: 12px;
}

.loading-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.loading-controls i,
.loading-table i,
.loading-card i {
  display: block;
  border-radius: 6px;
  background: linear-gradient(
    90deg,
    var(--sc-app-muted-bg) 20%,
    var(--sc-app-border) 38%,
    var(--sc-app-muted-bg) 56%
  );
  background-size: 240% 100%;
  animation: product-loading-shimmer 1.35s ease-in-out infinite;
}

.loading-controls i {
  width: 74px;
  height: 30px;
}

.loading-controls i:first-child {
  width: clamp(180px, 24vw, 330px);
}

.loading-table {
  box-sizing: border-box;
  height: max(420px, calc(100vh - 210px));
  overflow: hidden;
  border-block: 1px solid var(--sc-app-border);
  border-inline: 0;
  border-radius: 0;
  background: var(--sc-app-panel);
  box-shadow: none;
}

.loading-footer {
  box-sizing: border-box;
  display: flex;
  height: 32px;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
}

.loading-footer.mode-kanban {
  height: 47px;
  border: 1px solid var(--sc-app-border);
  border-radius: 10px;
  background: var(--sc-app-panel);
  padding: 0 12px;
}

.loading-footer i {
  display: block;
  width: 54px;
  height: 26px;
  border-radius: 6px;
  background: var(--sc-app-muted-bg);
}

.loading-footer i:first-child {
  width: 84px;
}

.loading-table-head,
.loading-table-row {
  display: grid;
  grid-template-columns: 72px minmax(140px, 1.25fr) minmax(120px, 1fr) minmax(120px, 1fr) 120px 104px;
  align-items: center;
  gap: 18px;
  min-width: 820px;
  padding: 0 16px;
}

.loading-table-head {
  min-height: 46px;
  border-bottom: 1px solid var(--sc-app-border);
  background: var(--sc-app-muted-bg);
}

.loading-table-row {
  min-height: 54px;
  border-bottom: 1px solid var(--sc-app-border);
}

.loading-table-row:last-child {
  border-bottom: 0;
}

.loading-table-head i {
  width: 64%;
  height: 10px;
}

.loading-table-row i {
  width: 78%;
  height: 12px;
}

.loading-table-row .cell-2 {
  width: 90%;
}

.loading-table-row .cell-5,
.loading-table-row .cell-6 {
  width: 58%;
}

.loading-card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
}

.loading-card {
  box-sizing: border-box;
  display: grid;
  gap: 12px;
  height: 175px;
  border: 1px solid var(--sc-app-border);
  border-radius: 8px;
  background: var(--sc-app-panel);
  padding: 16px;
  box-shadow: 0 16px 30px var(--sc-app-shadow);
}

.loading-secondary-toolbar {
  box-sizing: border-box;
  display: flex;
  height: 42px;
  align-items: center;
  gap: 8px;
  border: 1px solid var(--sc-app-border);
  border-radius: 8px;
  background: var(--sc-app-panel);
  padding: 4px 10px;
  box-shadow: 0 8px 18px var(--sc-app-shadow);
}

.loading-secondary-toolbar i {
  display: block;
  width: 78px;
  height: 28px;
  border-radius: 6px;
  background: var(--sc-app-muted-bg);
}

.loading-secondary-toolbar i:first-child {
  width: min(330px, 40%);
}

.skeleton-line {
  width: 72%;
  height: 11px;
}

.skeleton-line.line-title {
  width: 48%;
  height: 16px;
}

.skeleton-line.line-wide {
  width: 92%;
}

.skeleton-line.line-medium {
  width: 68%;
}

.skeleton-line.line-short {
  width: 42%;
}

@keyframes product-loading-shimmer {
  from {
    background-position: 100% 0;
  }
  to {
    background-position: -100% 0;
  }
}

@media (max-width: 720px) {
  .loading-controls i:not(:first-child) {
    display: none;
  }

  .loading-controls i:first-child {
    width: 112px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .loading-controls i,
  .loading-table i,
  .loading-card i {
    animation: none;
  }
}
</style>
