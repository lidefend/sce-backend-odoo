<template>
  <header
    class="product-page-header"
    data-semantic-component="ProductPageHeader"
    :data-state="model.renderProfile"
    :class="[
      `product-page-header--${model.variant}`,
      `product-page-header--${model.presentationMode}`,
      { 'product-page-header--title-hidden': hideTitle },
    ]"
    data-product-page-header
    data-workspace-page-header
    :data-presentation-mode="model.presentationMode"
    :data-render-profile="model.renderProfile"
    :data-dirty-state="model.dirtyState"
    :data-header-variant="model.variant"
    :data-title-visibility="hideTitle ? 'semantic-only' : 'visible'"
  >
    <div class="product-page-header__identity">
      <p v-if="eyebrow" class="product-page-header__eyebrow">{{ eyebrow }}</p>
      <nav v-if="model.breadcrumb.length" class="product-page-header__breadcrumb" aria-label="页面路径">
        <span v-for="(item, index) in model.breadcrumb" :key="`${item}-${index}`">{{ item }}</span>
      </nav>
      <h1 :class="{ 'sc-visually-hidden': hideTitle }">{{ model.title }}</h1>
      <p v-if="!hideTitle && model.subtitle" class="product-page-header__subtitle">{{ model.subtitle }}</p>
      <slot name="meta" />
    </div>
    <div v-if="$slots.status" class="product-page-header__status"><slot name="status" /></div>
    <div v-if="$slots.actions" class="product-page-header__actions" data-workspace-action-bar><slot name="actions" /></div>
  </header>
</template>

<script setup lang="ts">
import { computed, useSlots } from 'vue';
import {
  resolveProductPageHeaderModel,
  type ProductPageDirtyState,
  type ProductPageHeaderVariant,
  type ProductPageHeaderAction,
  type ProductPagePresentationMode,
  type ProductPageRenderProfile,
} from '../../app/presentation/productPageHeader';

const props = withDefaults(defineProps<{
  title: string;
  subtitle?: string;
  eyebrow?: string;
  breadcrumb?: string[];
  presentationMode?: ProductPagePresentationMode;
  renderProfile?: ProductPageRenderProfile;
  dirtyState?: ProductPageDirtyState;
  variant?: ProductPageHeaderVariant;
  hideTitle?: boolean;
  primaryActions?: ProductPageHeaderAction[];
  overflowActions?: ProductPageHeaderAction[];
  exitAction?: ProductPageHeaderAction | null;
}>(), {
  subtitle: '', eyebrow: '', breadcrumb: () => [], presentationMode: 'workspace',
  renderProfile: 'readonly', dirtyState: 'clean', variant: 'standalone', hideTitle: false,
  primaryActions: () => [], overflowActions: () => [], exitAction: null,
});

const model = computed(() => resolveProductPageHeaderModel({
  title: props.title,
  subtitle: props.subtitle,
  breadcrumb: props.breadcrumb,
  presentationMode: props.presentationMode,
  renderProfile: props.renderProfile,
  dirtyState: props.dirtyState,
  statusbar: Boolean(useSlots().status),
  primaryActions: props.primaryActions,
  overflowActions: props.overflowActions,
  exitAction: props.exitAction,
  variant: props.variant,
}));

</script>

<style scoped>
.product-page-header {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sc-space-sm);
  min-width: 0;
  min-height: 44px;
  border: 1px solid var(--sc-app-border);
  border-radius: var(--sc-product-panel-radius);
  background: var(--sc-app-panel);
  box-shadow: var(--sc-app-shadow);
  padding: var(--sc-space-xs) var(--sc-space-sm);
}
.product-page-header__identity { display:grid; flex:1 1 auto; min-width:0; }
.product-page-header h1,.product-page-header p { margin:0; }
.product-page-header h1 { color:var(--sc-app-text-primary); font-size:22px; font-weight:700; line-height:1.2; overflow-wrap:anywhere; }
.product-page-header__eyebrow,.product-page-header__subtitle,.product-page-header__breadcrumb { color:var(--sc-semantic-text-muted); font-size:12px; }
.product-page-header__eyebrow { margin-bottom:var(--sc-space-2xs); }
.product-page-header__subtitle { margin-top:2px; }
.product-page-header__breadcrumb { display:flex; flex-wrap:wrap; gap:var(--sc-space-2xs); margin-bottom:var(--sc-space-2xs); }
.product-page-header__breadcrumb span + span::before { content:'›'; margin-right:var(--sc-space-2xs); }
.product-page-header__status { display:grid; flex:1 1 auto; min-width:0; margin-left:auto; text-align:right; }
.product-page-header__status:empty,.product-page-header__actions:empty { display:none; }
.product-page-header__actions { display:flex; flex:0 0 auto; flex-wrap:wrap; align-items:center; justify-content:flex-end; gap:var(--sc-space-xs); }
.product-page-header--title-hidden { min-height:54px; padding-block:var(--sc-space-xs); }
.product-page-header--title-hidden .product-page-header__identity { position:absolute; width:1px; height:1px; overflow:hidden; }
.product-page-header--title-hidden .product-page-header__status { margin-left:0; text-align:left; }
.product-page-header--collection {
  min-height:72px;
  border:0;
  border-radius:0;
  background:transparent;
  box-shadow:none;
  padding:12px 8px;
}
.product-page-header--collection h1 { font-size:24px; letter-spacing:-.01em; }
.product-page-header--task,.product-page-header--workspace { border-color:var(--sc-app-border-strong); }
.product-page-header--dialog { box-shadow:none; border-width:0 0 1px; border-radius:0; }
@media(max-width:860px){.product-page-header{align-items:stretch;flex-direction:column}.product-page-header--title-hidden{align-items:stretch}.product-page-header__status{width:100%;margin-left:0;text-align:left}.product-page-header__actions{width:100%}.product-page-header h1{font-size:20px}}
</style>
