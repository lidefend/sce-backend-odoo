<template>
  <section
    class="product-list-query-bar sc-product-page-toolbar"
    :class="{ 'product-list-query-bar--without-search': !showSearch }"
    data-list-query-action-bar
    data-semantic-component="ProductListHeader"
    :data-state="loading ? 'loading' : 'ready'"
    :aria-busy="loading || undefined"
    aria-label="列表查询与操作"
  >
    <ScActionBar
      class="product-list-header__tools"
      :class="{ 'product-list-header__tools--aligned': alignedLayout }"
      :style="layoutStyle"
      label="列表操作"
    >
      <div v-if="$slots.leading" class="product-list-header__leading"><slot name="leading" /></div>
      <form v-if="showSearch" class="product-list-header__search" role="search" @submit.prevent="$emit('search-submit')">
        <label>
          <span class="sc-visually-hidden">{{ searchLabel }}</span>
          <ScInput
            type="search"
            :model-value="searchValue"
            :disabled="loading"
            :placeholder="searchPlaceholder"
            @compositionstart="$emit('composition-start')"
            @compositionend="$emit('composition-end', $event)"
            @input="(value) => $emit('search-input', value)"
          />
        </label>
        <ScButton type="submit" :disabled="loading">{{ searchLabel }}</ScButton>
        <ScButton v-if="searchValue" variant="ghost" :disabled="loading" @click="$emit('search-clear')">清除</ScButton>
      </form>
      <div v-if="$slots.actions" class="product-list-header__actions"><slot name="actions" /></div>
      <slot />
      <slot name="auxiliary" />
    </ScActionBar>
  </section>
</template>

<script setup lang="ts">
import type { StyleValue } from 'vue';
import ScActionBar from '../design-system/ScActionBar.vue';
import ScButton from '../design-system/ScButton.vue';
import ScInput from '../design-system/ScInput.vue';

defineProps<{
  loading: boolean;
  showSearch: boolean;
  searchValue: string;
  searchLabel: string;
  searchPlaceholder: string;
  alignedLayout?: boolean;
  layoutStyle?: StyleValue;
}>();

defineEmits<{
  'search-input': [value: string];
  'search-submit': [];
  'search-clear': [];
  'composition-start': [];
  'composition-end': [event: CompositionEvent];
}>();

</script>

<style scoped>
.product-list-query-bar {
  box-sizing: border-box;
  position: sticky;
  top: 0;
  z-index: 4;
  display: block;
  width: 100cqw;
  min-height: 44px;
  padding: 0 var(--sc-space-sm);
  border: 1px solid var(--sc-app-border);
  border-radius: 0;
  background: var(--sc-app-panel);
  box-shadow: none;
}
@media (min-width: 761px) {
  .product-list-query-bar {
    width: 100%;
    position: relative;
    top: 0;
    padding: 0 var(--sc-space-sm);
    border: 1px solid var(--sc-app-border);
    border-radius: 0;
    background: var(--sc-app-panel);
    box-shadow: none;
    min-height: var(--sc-product-list-toolbar-height);
  }
  .product-list-header__tools :deep(.native-search) {
    min-height: 42px;
  }
}
.product-list-header__tools {
  display: grid;
  grid-template-columns: minmax(0, 1fr) max-content;
  grid-template-areas: 'main utility';
  align-items: center;
  gap: var(--sc-toolbar-group-gap);
  min-width: 0;
  width: 100%;
}
.product-list-header__tools :deep(.action-toolbar) {
  grid-area: main;
  width: 100%;
  border: 0;
  border-radius: 0;
  background: transparent;
  padding: 0;
}
.product-list-header__tools :deep(.native-search) {
  justify-self: stretch;
  width: 100%;
  max-width: none;
}
.product-list-header__tools :deep(.toolbar-actions) { width: auto; }
.product-list-header__tools :deep(.list-surface-utilities) { grid-area: utility; }
.product-list-header__search { grid-area: main; display: flex; gap: var(--sc-toolbar-gap); align-items: center; min-width: 320px; }
.product-list-header__search label { min-width: 0; flex: 1; }
.product-list-header__search :deep(.sc-btn) { min-height: 40px; }
.product-list-header__search :deep(.sc-input) {
  width: 100%;
  min-height: 40px;
}
.product-list-header__tools--aligned {
  grid-template-areas: 'leading divider-left search divider-right actions';
}
.product-list-header__tools--aligned .product-list-header__leading { grid-area: leading; min-width: 0; }
.product-list-header__tools--aligned .product-list-header__search { grid-area: search; min-width: 0; }
.product-list-header__tools--aligned .product-list-header__actions {
  grid-area: actions;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--sc-toolbar-gap);
  min-width: 0;
}
@media (max-width: 720px) {
  .product-list-query-bar {
    width: 100%;
    padding: 0 var(--sc-space-xs);
    border: 1px solid var(--sc-app-border);
    border-bottom: 1px solid var(--sc-app-border);
    border-radius: 0;
    background: transparent;
    box-shadow: none;
  }
  .product-list-header__tools :deep(.action-toolbar) { gap: var(--sc-toolbar-gap); }
  .product-list-header__search { min-width: 190px; }
  .product-list-header__search .ghost { display: none; }
}
@media (max-width: 760px) {
  .product-list-header__tools { gap: var(--sc-toolbar-gap); }
  .product-list-header__search { min-width: 0; }
  .product-list-header__search :deep(.sc-btn) { min-width: 44px; min-height: 44px; }
}
</style>
