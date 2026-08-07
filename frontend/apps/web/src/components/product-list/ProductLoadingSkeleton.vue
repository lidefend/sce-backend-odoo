<template>
  <section
    class="product-loading-shell"
    :class="`mode-${mode}`"
    role="status"
    aria-live="polite"
    aria-busy="true"
  >
    <header class="loading-toolbar">
      <p class="sc-visually-hidden">{{ title }}，{{ loadingLabel }}</p>
      <div class="loading-search" aria-hidden="true">
        <i class="loading-search-input" />
        <i class="loading-search-submit" />
        <i class="loading-search-menu" />
      </div>
      <div class="loading-utilities" aria-hidden="true">
        <i class="loading-utility-primary" />
        <i class="loading-utility-secondary" />
      </div>
    </header>

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
  gap: 0;
  width: 100%;
  min-width: 0;
}

.product-loading-shell.mode-kanban {
  gap: var(--sc-product-workspace-stack-gap);
}

.loading-toolbar {
  box-sizing: border-box;
  display: grid;
  grid-template-columns: minmax(0, 1fr) max-content;
  grid-template-areas: 'search utility';
  min-height: var(--sc-product-toolbar-height);
  align-items: center;
  gap: var(--sc-toolbar-group-gap);
  border: 1px solid var(--sc-app-border);
  border-radius: 0;
  background: var(--sc-app-panel);
  padding: 0 var(--sc-space-sm);
  box-shadow: none;
}

.loading-search {
  grid-area: search;
  display: flex;
  align-items: center;
  min-height: 44px;
  min-width: 0;
  gap: var(--sc-toolbar-gap);
  border: 1px solid var(--sc-app-border-strong);
  border-radius: var(--sc-product-radius-control);
  padding: 3px;
}

.loading-search i,
.loading-utilities i,
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

.loading-search-input {
  flex: 1 1 auto;
  min-width: 72px;
  height: 28px;
}

.loading-search-submit {
  flex: 0 0 68px;
  height: 36px;
}

.loading-search-menu {
  flex: 0 0 28px;
  height: 28px;
}

.loading-utilities {
  grid-area: utility;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--sc-toolbar-gap);
}

.loading-utilities i {
  width: 72px;
  height: 36px;
}

.loading-utility-secondary {
  width: 82px;
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
  .loading-toolbar {
    min-height: calc(var(--sc-product-toolbar-height) * 2 + 2px);
    grid-template-columns: minmax(0, 1fr);
    grid-template-areas:
      'search'
      'utility';
    align-content: start;
    row-gap: 0;
    padding: 0 var(--sc-space-xs);
  }

  .loading-utilities {
    min-height: var(--sc-product-toolbar-height);
    justify-self: end;
  }

  .loading-utilities i {
    width: 44px;
    height: 44px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .loading-search i,
  .loading-utilities i,
  .loading-table i,
  .loading-card i {
    animation: none;
  }
}
</style>
