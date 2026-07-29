<template>
  <header class="product-list-header sc-product-page-toolbar" data-workspace-page-header>
    <div class="product-list-header__identity">
      <p class="product-list-header__eyebrow">业务列表</p>
      <div class="product-list-header__title-row">
        <h2>{{ title }}</h2>
        <span v-if="resultSummary" class="product-list-header__result">{{ resultSummary }}</span>
      </div>
      <p v-if="subtitle">{{ subtitle }}</p>
    </div>
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
  </header>
</template>

<script setup lang="ts">
import ScActionBar from '../design-system/ScActionBar.vue';
import ScButton from '../design-system/ScButton.vue';

defineProps<{
  title: string;
  subtitle?: string;
  loading: boolean;
  showSearch: boolean;
  searchValue: string;
  searchLabel: string;
  searchPlaceholder: string;
  resultSummary?: string;
}>();

defineEmits<{
  'search-input': [event: Event];
  'search-submit': [];
  'search-clear': [];
  'composition-start': [];
  'composition-end': [event: CompositionEvent];
}>();
</script>

<style scoped>
.product-list-header {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 12px;
  align-items: start;
  padding: 2px 0 0;
}
.product-list-header__identity h2,
.product-list-header__identity p { margin: 0; }
.product-list-header__identity > p:not(.product-list-header__eyebrow) {
  margin-top: 5px;
  max-width: 76ch;
  color: var(--sc-app-text-secondary);
  font-size: 13px;
  line-height: 1.45;
}
.product-list-header__eyebrow {
  margin-bottom: 5px !important;
  color: var(--sc-app-text-secondary);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
}
.product-list-header__title-row {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 8px 12px;
}
.product-list-header__title-row h2 {
  color: var(--sc-app-text-primary);
  font-size: clamp(22px, 2vw, 28px);
  line-height: 1.2;
  letter-spacing: -0.02em;
}
.product-list-header__result {
  color: var(--sc-app-text-secondary);
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}
.product-list-header__tools { min-width: 0; }
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
  .product-list-header__search { display: grid; grid-template-columns: minmax(0, 1fr) auto; }
  .product-list-header__search .ghost { grid-column: 1 / -1; justify-self: start; }
}
</style>
