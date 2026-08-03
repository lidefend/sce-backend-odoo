<template>
  <section ref="queryBar" class="product-list-query-bar sc-product-page-toolbar" data-list-query-action-bar aria-label="列表查询与操作">
    <ScActionBar class="product-list-header__tools" label="列表操作">
      <slot />
    </ScActionBar>
    <form v-if="showSearch" class="product-list-header__search" role="search" @submit.prevent="$emit('search-submit')">
        <label>
          <span class="sc-visually-hidden">{{ searchLabel }}</span>
          <input
            type="search"
            :value="searchValue"
            :disabled="loading"
            :placeholder="searchPlaceholder"
            @compositionstart="$emit('composition-start')"
            @compositionend="$emit('composition-end', $event)"
            @input="$emit('search-input', $event)"
          />
        </label>
        <ScButton type="submit" :disabled="loading">{{ searchLabel }}</ScButton>
        <ScButton v-if="searchValue" variant="ghost" :disabled="loading" @click="$emit('search-clear')">清除</ScButton>
      </form>
  </section>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue';
import ScActionBar from '../design-system/ScActionBar.vue';
import ScButton from '../design-system/ScButton.vue';

defineProps<{
  loading: boolean;
  showSearch: boolean;
  searchValue: string;
  searchLabel: string;
  searchPlaceholder: string;
}>();

defineEmits<{
  'search-input': [event: Event];
  'search-submit': [];
  'search-clear': [];
  'composition-start': [];
  'composition-end': [event: CompositionEvent];
}>();

const queryBar = ref<HTMLElement | null>(null);
let resizeObserver: ResizeObserver | null = null;
let listPage: HTMLElement | null = null;
let scrollHost: HTMLElement | null = null;
let tableSurface: HTMLElement | null = null;
let layoutFrame = 0;

function syncListLayout() {
  layoutFrame = 0;
  const element = queryBar.value;
  if (!element) return;
  listPage = element.closest<HTMLElement>('[data-product-page-mode="list"]');
  const queryRect = element.getBoundingClientRect();
  listPage?.style.setProperty('--sc-list-query-bar-height', `${Math.ceil(queryRect.height)}px`);

  tableSurface = listPage?.querySelector<HTMLElement>('.table') || null;
  const tableHeader = tableSurface?.querySelector<HTMLElement>('thead') || null;
  if (!tableSurface || !tableHeader) {
    listPage?.style.setProperty('--sc-list-header-y-offset', '0px');
    return;
  }

  const tableRect = tableSurface.getBoundingClientRect();
  const headerHeight = tableHeader.getBoundingClientRect().height;
  const paginationHeight =
    tableSurface.querySelector<HTMLElement>('.pagination-footer')?.getBoundingClientRect().height || 0;
  const borderTop = Number.parseFloat(window.getComputedStyle(tableSurface).borderTopWidth) || 0;
  const headerNaturalTop = tableRect.top + borderTop;
  const maximumOffset = Math.max(0, tableRect.height - headerHeight - paginationHeight - borderTop);
  const headerOffset = Math.min(
    Math.max(queryRect.bottom - headerNaturalTop, 0),
    maximumOffset,
  );
  listPage?.style.setProperty('--sc-list-header-y-offset', `${Math.floor(headerOffset)}px`);
}

function scheduleListLayoutSync() {
  if (layoutFrame) return;
  layoutFrame = window.requestAnimationFrame(syncListLayout);
}

onMounted(async () => {
  await nextTick();
  scrollHost = queryBar.value?.closest<HTMLElement>('.router-host') || null;
  syncListLayout();
  scrollHost?.addEventListener('scroll', scheduleListLayoutSync, { passive: true });
  window.addEventListener('resize', scheduleListLayoutSync, { passive: true });
  resizeObserver = new ResizeObserver(scheduleListLayoutSync);
  if (queryBar.value) resizeObserver.observe(queryBar.value);
  if (tableSurface) resizeObserver.observe(tableSurface);
});

onBeforeUnmount(() => {
  resizeObserver?.disconnect();
  scrollHost?.removeEventListener('scroll', scheduleListLayoutSync);
  window.removeEventListener('resize', scheduleListLayoutSync);
  if (layoutFrame) window.cancelAnimationFrame(layoutFrame);
  listPage?.style.removeProperty('--sc-list-query-bar-height');
  listPage?.style.removeProperty('--sc-list-header-y-offset');
});
</script>

<style scoped>
.product-list-query-bar {
  box-sizing: border-box;
  position: sticky;
  top: 0;
  z-index: 4;
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 12px;
  width: 100cqw;
  padding: 8px 12px;
  border: 0;
  border-radius: 0;
  background: var(--sc-app-panel);
  box-shadow: none;
}
@media (min-width: 761px) {
  .product-list-query-bar {
    top: 0;
    padding: 0;
    border: 0;
    border-radius: 0;
    background: transparent;
    box-shadow: none;
  }

  .product-list-header__tools :deep(.native-search) {
    min-height: 42px;
  }
}
.product-list-header__tools {
  display: flex;
  min-width: 0;
  width: 100%;
}
.product-list-header__tools :deep(.action-toolbar) {
  grid-template-columns: max-content minmax(0, 1fr) max-content;
  width: 100%;
  border: 0;
  border-radius: 0;
  background: transparent;
  padding: 0;
}
.product-list-header__tools :deep(.action-toolbar.action-toolbar--without-view) {
  grid-template-columns: minmax(0, 1fr) max-content;
}
.product-list-header__tools :deep(.native-search) {
  justify-self: stretch;
  width: 100%;
  max-width: none;
}
.product-list-header__tools :deep(.toolbar-actions) { width: auto; }
.product-list-header__search { display: flex; gap: var(--sc-product-space-1); align-items: center; }
.product-list-header__search label { min-width: 0; flex: 1; }
.product-list-header__search input {
  width: 100%;
  min-height: 38px;
  padding: 0 12px;
  border: 1px solid var(--sc-app-border-strong);
  border-radius: var(--sc-product-radius-control);
  background: var(--sc-app-panel);
  color: var(--sc-app-text-primary);
}
.product-list-header__search input:focus {
  border-color: var(--sc-semantic-surface-interactive);
  outline: 3px solid var(--sc-app-focus-ring);
  outline-offset: 0;
}
@media (max-width: 720px) {
  .product-list-query-bar {
    padding: 10px;
    border: 1px solid var(--sc-app-border);
    border-radius: 10px;
    box-shadow: 0 5px 16px color-mix(in srgb, var(--sc-app-shadow) 12%, transparent);
  }
  .product-list-header__search { display: grid; grid-template-columns: minmax(0, 1fr) auto; }
  .product-list-header__search .ghost { grid-column: 1 / -1; justify-self: start; }
}
</style>
