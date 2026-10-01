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
      :class="{ 'product-list-header__tools--aligned': alignedLayout, 'product-list-header__tools--collection': collectionLayout }"
      :style="layoutStyle"
      label="列表操作"
    >
      <div v-if="collectionLayout" class="product-list-header__layout">
      <div v-if="$slots.leading" class="product-list-header__leading"><slot name="leading" /></div>
      <form v-if="showSearch" class="product-list-header__search" role="search" @submit.prevent="$emit('search-submit')">
        <label>
          <span class="sc-visually-hidden">{{ searchLabel }}</span>
          <ScInput
            appearance="collection-search"
            type="search"
            :model-value="searchValue"
            :disabled="loading"
            :placeholder="searchPlaceholder"
            @compositionstart="$emit('composition-start')"
            @compositionend="$emit('composition-end', $event)"
            @input="(value) => $emit('search-input', value)"
          >
            <template #suffix>
              <ScIcon name="search" :size="16" />
            </template>
          </ScInput>
        </label>
        <ScButton type="submit" :disabled="loading">{{ searchLabel }}</ScButton>
        <ScButton v-if="searchValue" variant="ghost" :disabled="loading" @click="$emit('search-clear')">清除</ScButton>
      </form>
      <div v-if="$slots.actions" class="product-list-header__actions"><slot name="actions" /></div>
      <div v-if="$slots.default" class="product-list-header__query"><slot /></div>
      <div v-if="$slots.auxiliary" class="product-list-header__auxiliary"><slot name="auxiliary" /></div>
      </div>
      <template v-else>
      <div v-if="$slots.leading" class="product-list-header__leading"><slot name="leading" /></div>
      <form v-if="showSearch" class="product-list-header__search" role="search" @submit.prevent="$emit('search-submit')">
        <label>
          <span class="sc-visually-hidden">{{ searchLabel }}</span>
          <ScInput
            appearance="collection-search"
            type="search"
            :model-value="searchValue"
            :disabled="loading"
            :placeholder="searchPlaceholder"
            @compositionstart="$emit('composition-start')"
            @compositionend="$emit('composition-end', $event)"
            @input="(value) => $emit('search-input', value)"
          >
            <template #suffix>
              <ScIcon name="search" :size="16" />
            </template>
          </ScInput>
        </label>
        <ScButton type="submit" :disabled="loading">{{ searchLabel }}</ScButton>
        <ScButton v-if="searchValue" variant="ghost" :disabled="loading" @click="$emit('search-clear')">清除</ScButton>
      </form>
      <div v-if="$slots.actions" class="product-list-header__actions"><slot name="actions" /></div>
      <slot />
      <slot name="auxiliary" />
      </template>
    </ScActionBar>
  </section>
</template>

<script setup lang="ts">
import type { StyleValue } from 'vue';
import ScActionBar from '../design-system/ScActionBar.vue';
import ScButton from '../design-system/ScButton.vue';
import ScIcon from '../design-system/ScIcon.vue';
import ScInput from '../design-system/ScInput.vue';

defineProps<{
  loading: boolean;
  showSearch: boolean;
  searchValue: string;
  searchLabel: string;
  searchPlaceholder: string;
  collectionLayout?: boolean;
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
  border: 0;
  border-radius: var(--sc-product-radius-panel) var(--sc-product-radius-panel) 0 0;
  background: var(--sc-app-panel);
  box-shadow: none;
}
@media (min-width: 761px) {
  .product-list-query-bar {
    width: 100%;
    position: relative;
    top: 0;
    padding: 0 var(--sc-space-sm);
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
.product-list-header__search { grid-area: main; display: flex; gap: var(--sc-toolbar-gap); align-items: center; min-width: 320px; --sc-component-input-form-height: 36px; }
.product-list-header__search label { min-width: 0; flex: 1; }
.product-list-header__search :deep(.sc-input) {
  width: 100%;
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
    background: transparent;
    box-shadow: none;
  }
  .product-list-header__tools :deep(.action-toolbar) { gap: var(--sc-toolbar-gap); }
  .product-list-header__search { min-width: 190px; }
  .product-list-header__search .ghost { display: none; }
}
@media (max-width: 760px) {
  .product-list-header__tools { gap: var(--sc-toolbar-gap); }
  .product-list-header__tools :deep(.list-surface-utilities) { align-self: end; }
  .product-list-header__search { min-width: 0; }
  .product-list-header__search { --sc-component-input-form-height: 44px; }
}

.product-list-query-bar:has(.product-list-header__tools--collection) { position: relative; padding: 0; background: transparent; border-radius: 0; box-sizing: border-box; width: 100%; min-width: 0; margin-bottom: var(--sc-space-lg); }
.product-list-header__tools--collection { display: block; width: 100%; min-width: 0; }
.product-list-header__layout { display: flex; flex-wrap: wrap; align-items: center; gap: var(--sc-toolbar-group-gap); min-width: 0; }
.product-list-header__tools--collection .product-list-header__leading { display: flex; flex-wrap: wrap; align-items: center; gap: var(--sc-toolbar-gap); min-width: 0; margin-right: auto; }
.product-list-header__query, .product-list-header__tools--collection .product-list-header__search { flex: 1 1 280px; min-width: 0; }
.product-list-header__query { max-width: 640px; }
.product-list-header__query :deep(.action-toolbar) { width: 100%; border: 0; border-radius: 0; background: transparent; padding: 0; }
/* The query track hosts the list search control, so everything inside it must be
   able to shrink to the declared track. A text input keeps its size-based
   intrinsic width once it holds a query and the input wrap's default
   `min-width: auto` then refuses to shrink, which pushes the trailing submit and
   menu-toggle controls out of the track and over the auxiliary track (where the
   column-settings control sits). Grant the shrink at the declared track owner. */
.product-list-header__query :deep(.native-search) { min-width: 0; width: 100%; max-width: none; }
.product-list-header__query :deep(.sc-input) { min-width: 0; }
.product-list-header__tools--collection .product-list-header__search { display: flex; align-items: center; gap: var(--sc-toolbar-gap); }
.product-list-header__tools--collection .product-list-header__search label { flex: 1; min-width: 0; }
/* The search control owns the trailing query track; its input wrap must be able
   to shrink inside it. A text input keeps the size-based intrinsic width once it
   holds a query, and the wrap's default `min-width: auto` then refuses to shrink,
   pushing the submit/toggle controls out of the declared query track and over the
   auxiliary track. Only the declared track owner can grant the shrink. */
.product-list-header__tools--collection .product-list-header__search :deep(.sc-input) { width: 100%; min-width: 0; }
.product-list-header__auxiliary, .product-list-header__tools--collection .product-list-header__actions { display: flex; align-items: center; gap: var(--sc-toolbar-gap); }
@media (max-width: 760px) {
  .product-list-header__layout { gap: var(--sc-toolbar-gap); }
  .product-list-header__tools--collection .product-list-header__leading :deep(.sc-btn) { min-width: 44px; min-height: 44px; }
  .product-list-header__tools--collection .product-list-header__leading { flex-basis: 100%; }
  .product-list-header__query, .product-list-header__tools--collection .product-list-header__search { flex-basis: calc(100% - 60px); }
  .product-list-header__tools--collection .product-list-header__search { --sc-component-input-form-height: 44px; }
}

</style>
