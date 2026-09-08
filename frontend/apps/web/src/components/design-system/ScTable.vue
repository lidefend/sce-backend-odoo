<template>
  <TDesignTable
    ref="tableRef"
    v-native-control-projection="scrollProjection"
    v-bind="semanticPrimitiveIdentity('ScTable')"
    :data="data"
    :columns="columns"
    :row-key="rowKey"
    :size="normalizePrimitiveSize(size)"
    :loading="loading"
    :hover="hover"
    :stripe="stripe"
    :row-class-name="rowClassName"
    :row-attributes="tdesignRowAttributes"
    :keyboard-row-hover="keyboardRowHover"
    :disable-data-page="disableDataPage"
    :table-content-width="tableContentWidth"
    :scroll="tableScroll"
    :foot-data="footData"
    :selected-row-keys="selectedRowKeys"
    :row-selection-type="rowSelectionType"
    :select-on-row-click="selectOnRowClick"
    :aria-label="label"
    :data-row-count="data.length"
    :data-appearance="appearance"
    data-semantic-driver="tdesign-table"
    @row-click="emit('rowClick', $event)"
    @row-dblclick="emit('rowDblclick', $event)"
    @select-change="onSelectChange"
  >
    <template #topContent>
      <slot name="topContent" />
      <div v-if="canScrollLeft || canScrollRight" class="sc-table-scroll-tools" aria-label="表格横向浏览">
        <span>横向浏览更多列</span>
        <ScIconButton label="查看左侧列" :disabled="!canScrollLeft" @click="scrollColumns(-1)">←</ScIconButton>
        <ScIconButton label="查看右侧列" :disabled="!canScrollRight" @click="scrollColumns(1)">→</ScIconButton>
      </div>
    </template>
    <template v-for="name in Object.keys($slots).filter((name) => name !== 'topContent')" #[name]="slotProps">
      <slot :name="name" v-bind="slotProps ?? {}" />
    </template>
  </TDesignTable>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, onUpdated, ref, type ComputedRef } from 'vue';
import ScIconButton from './ScIconButton.vue';
import { TDesignTable } from './tdesignPrimitiveBridge';
import type { TDesignTableRowAttributes, TDesignTableRowData } from './tdesignPrimitiveBridge';
import { normalizePrimitiveSize, semanticPrimitiveIdentity, type ScPrimitiveSize } from './primitiveAdapter';
import { nativeControlProjection } from './nativeControlProjection';
const vNativeControlProjection = nativeControlProjection;

const tableRef = ref<{ $el?: HTMLElement } | null>(null);
const canScrollLeft = ref(false);
const canScrollRight = ref(false);
let scrollContent: HTMLElement | null = null;
let resizeObserver: ResizeObserver | null = null;
function updateScrollEdges() {
  const content = scrollContent;
  // Resize handles can extend a few pixels past a table that otherwise fits.
  const tableWidth = content?.querySelector('table')?.getBoundingClientRect().width ?? 0;
  const overflows = Boolean(content && tableWidth > content.clientWidth + 1);
  canScrollLeft.value = Boolean(overflows && content && content.scrollLeft > 1);
  canScrollRight.value = Boolean(overflows && content && content.scrollWidth - content.clientWidth - content.scrollLeft > 1);
}
function bindScrollContent() {
  const content = tableRef.value?.$el?.querySelector<HTMLElement>('.t-table__content') ?? null;
  if (content !== scrollContent) {
    scrollContent?.removeEventListener('scroll', updateScrollEdges);
    resizeObserver?.disconnect();
    scrollContent = content;
    if (content) {
      content.addEventListener('scroll', updateScrollEdges, { passive: true });
      resizeObserver = new ResizeObserver(updateScrollEdges);
      resizeObserver.observe(content);
      const table = content.querySelector('table');
      if (table) resizeObserver.observe(table);
    }
  }
  updateScrollEdges();
}
function scrollColumns(direction: number) {
  if (!scrollContent) return;
  scrollContent.scrollBy({ left: direction * Math.max(160, scrollContent.clientWidth * 0.75), behavior: 'instant' });
}
onMounted(bindScrollContent);
onUpdated(bindScrollContent);
onBeforeUnmount(() => {
  scrollContent?.removeEventListener('scroll', updateScrollEdges);
  resizeObserver?.disconnect();
});

const props = withDefaults(defineProps<{
  data?: Record<string, unknown>[];
  columns?: Record<string, unknown>[];
  rowKey?: string;
  size?: ScPrimitiveSize;
  loading?: boolean;
  hover?: boolean;
  stripe?: boolean;
  rowClassName?: string | ((context: unknown) => unknown);
  rowAttributes?: Record<string, unknown> | ((context: unknown) => Record<string, unknown>);
  keyboardRowHover?: boolean;
  disableDataPage?: boolean;
  tableContentWidth?: string;
  footData?: Record<string, unknown>[];
  selectedRowKeys?: Array<string | number>;
  rowSelectionType?: 'single' | 'multiple';
  selectOnRowClick?: boolean;
  label: string;
  appearance?: 'default' | 'surface' | 'flush' | 'collection' | 'worksheet' | 'relation-detail';
}>(), {
  data: () => [],
  columns: () => [],
  rowKey: 'id',
  size: 'medium',
  hover: true,
  keyboardRowHover: true,
  disableDataPage: true,
  selectedRowKeys: () => [],
  footData: () => [],
  appearance: 'default',
});
function projectRowAttributes(attributes: Record<string, unknown> | undefined): Record<string, unknown> {
  return Object.fromEntries(Object.entries(attributes || {}).map(([name, value]) => [
    name,
    /^on[A-Z]/.test(name) && typeof value === 'function' ? value : String(value ?? ''),
  ]));
}
const scrollProjection = computed(() => ({
  selector: '.t-table__content' as const,
  attributes: {
    tabindex: props.tableContentWidth ? 0 : undefined,
    role: props.tableContentWidth ? 'region' : undefined,
    'aria-label': props.tableContentWidth ? `${props.label}，可横向滚动` : undefined,
    'aria-description': props.tableContentWidth ? '聚焦表格区域后，可使用左右方向键查看其余列。' : undefined,
    'data-table-scroll-region': props.tableContentWidth ? 'true' : undefined,
  },
}));
const tdesignRowAttributes = computed(() => typeof props.rowAttributes === 'function'
  ? (context: unknown) => projectRowAttributes(props.rowAttributes instanceof Function ? props.rowAttributes(context) : undefined)
  : projectRowAttributes(props.rowAttributes)) as unknown as ComputedRef<TDesignTableRowAttributes<TDesignTableRowData>>;
// 启用水平滚动：当 tableContentWidth 存在时，将其作为 scroll.x
// tdesign TScroll类型要求type字段，但水平滚动不需要，使用类型断言绕过
const tableScroll = computed(() => {
  if (!props.tableContentWidth) return undefined;
  return { x: props.tableContentWidth };
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
}) as any;
const emit = defineEmits<{
  rowClick: [context: unknown];
  rowDblclick: [context: unknown];
  selectChange: [keys: Array<string | number>, context: unknown];
}>();
function onSelectChange(keys: Array<string | number>, context: unknown) { emit('selectChange', keys, context); }
</script>
