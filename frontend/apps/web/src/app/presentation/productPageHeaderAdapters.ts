import type { ProductPagePresentationMode, ProductPageRenderProfile } from './productPageHeader';

/**
 * 页头入口权威：`ProductPageHeader` 是唯一实现，这里登记**每个入口**对**每条正式轴**的处置。
 *
 * 任何新增的正式轴（prop 或 slot）都必须在此为每个入口作出显式决策，否则
 * `scripts/verify/frontend_product_page_header_guard.py` 与
 * `frontend/apps/web/scripts/product_page_header_adapter_contract_test.ts` 都会让候选失败——
 * 不存在「新轴悄悄漏过某个入口」的默认路径。
 */
export const PRODUCT_PAGE_HEADER_AXES = [
  'title',
  'subtitle',
  'eyebrow',
  'breadcrumb',
  'presentationMode',
  'renderProfile',
  'dirtyState',
  'variant',
  'hideTitle',
  'primaryActions',
  'overflowActions',
  'exitAction',
  'metaSlot',
  'statusSlot',
  'actionsSlot',
] as const;

export type ProductPageHeaderAxis = (typeof PRODUCT_PAGE_HEADER_AXES)[number];

export type ProductPageHeaderAxisDisposition =
  | { readonly axis: ProductPageHeaderAxis; readonly handling: 'forwarded' }
  | { readonly axis: ProductPageHeaderAxis; readonly handling: 'fixed'; readonly value: string; readonly reason: string }
  | { readonly axis: ProductPageHeaderAxis; readonly handling: 'not_exposed'; readonly reason: string };

export type ProductPageHeaderEntryRegistry = {
  /** 稳定入口标识。 */
  readonly id: string;
  /** 相对 `frontend/apps/web/src` 的入口路径。 */
  readonly path: string;
  /**
   * `adapter`：只把轴向 `ProductPageHeader` 转发的薄入口。
   * `exception_implementation`：受管例外，可携带领域内容，但必须继续转发全部正式轴并委托 authority 渲染。
   */
  readonly kind: 'adapter' | 'exception_implementation';
  readonly reason: string;
  readonly axes: readonly ProductPageHeaderAxisDisposition[];
};

const forwarded = (axis: ProductPageHeaderAxis): ProductPageHeaderAxisDisposition => ({ axis, handling: 'forwarded' });
const notExposed = (axis: ProductPageHeaderAxis, reason: string): ProductPageHeaderAxisDisposition => ({
  axis,
  handling: 'not_exposed',
  reason,
});
const fixedAxis = (
  axis: ProductPageHeaderAxis,
  value: string,
  reason: string,
): ProductPageHeaderAxisDisposition => ({ axis, handling: 'fixed', value, reason });

const entry = (
  id: string,
  path: string,
  kind: ProductPageHeaderEntryRegistry['kind'],
  reason: string,
  axes: readonly ProductPageHeaderAxisDisposition[],
): ProductPageHeaderEntryRegistry => ({ id, path, kind, reason, axes });

export const PRODUCT_PAGE_HEADER_ENTRIES: readonly ProductPageHeaderEntryRegistry[] = [
  entry('page', 'components/page/PageHeader.vue', 'adapter', '列表／看板页的最小页头入口，只承载页面身份与集合密度。', [
    forwarded('title'),
    forwarded('subtitle'),
    fixedAxis('presentationMode', 'collection', '该入口只服务于集合密度页面。'),
    notExposed('eyebrow', '集合页身份由标题与副标题承载，不引入分类语境。'),
    notExposed('breadcrumb', '集合页路径由导航壳层承载，页头不重复。'),
    notExposed('renderProfile', '集合页无创建／编辑态。'),
    notExposed('dirtyState', '集合页无表单脏态。'),
    notExposed('variant', '该入口只用于独立页面，不承载对话框变体。'),
    notExposed('hideTitle', '集合页必须呈现可见标题，否则页面失去唯一 h1。'),
    notExposed('primaryActions', '集合页动作由动作面承载，不由页头模型承载。'),
    notExposed('overflowActions', '同上，集合页溢出动作由动作面承载。'),
    notExposed('exitAction', '集合页无退出动作。'),
    notExposed('metaSlot', '集合页不承载元信息行。'),
    notExposed('statusSlot', '集合页状态由集合状态呈现承载。'),
    notExposed('actionsSlot', '集合页动作由动作面承载；页头不提供平行动作入口。'),
  ]),
  entry('template', 'components/template/PageHeader.vue', 'adapter', '工作区／表单模板的页头入口，需要完整正式轴与状态、动作槽。', [
    forwarded('title'),
    forwarded('subtitle'),
    forwarded('presentationMode'),
    forwarded('renderProfile'),
    forwarded('dirtyState'),
    forwarded('hideTitle'),
    forwarded('primaryActions'),
    forwarded('overflowActions'),
    forwarded('exitAction'),
    forwarded('metaSlot'),
    forwarded('statusSlot'),
    forwarded('actionsSlot'),
    notExposed('eyebrow', '模板页头身份由标题承载；分类语境仅在设计系统入口使用。'),
    notExposed('breadcrumb', '模板页路径由导航壳层承载，页头不重复。'),
    notExposed('variant', '模板页头当前只用于独立页面；对话框变体由 authority 直接渲染。'),
  ]),
  entry('design-system', 'components/design-system/ScPageHeader.vue', 'adapter', '设计系统公开入口，供设置、错误与配置上下文表面复用集合密度页头。', [
    forwarded('title'),
    forwarded('subtitle'),
    forwarded('eyebrow'),
    forwarded('actionsSlot'),
    fixedAxis('presentationMode', 'collection', '设计系统入口统一按集合密度呈现。'),
    notExposed('breadcrumb', '设计系统入口不承载路径语境。'),
    notExposed('renderProfile', '设计系统入口无创建／编辑态。'),
    notExposed('dirtyState', '设计系统入口无表单脏态。'),
    notExposed('variant', '设计系统入口只用于独立页面。'),
    notExposed('hideTitle', '设计系统入口必须呈现可见标题。'),
    notExposed('primaryActions', '动作由 actions 槽内聚，页头模型不承载。'),
    notExposed('overflowActions', '同上。'),
    notExposed('exitAction', '设计系统入口无退出动作。'),
    notExposed('metaSlot', '设计系统入口不承载元信息行。'),
    notExposed('statusSlot', '设计系统入口状态由调用方表面自身承载。'),
  ]),
  entry(
    'contract-form',
    'pages/contractForm/ContractFormProductHeader.vue',
    'exception_implementation',
    '受管例外：合同表单页头转发全部正式轴之外，还持有契约动作证据、原生状态栏绑定与移动端动作结算；该入口必须继续委托 ProductPageHeader 渲染，不得自建 header DOM。',
    [
      forwarded('title'),
      forwarded('subtitle'),
      forwarded('presentationMode'),
      forwarded('renderProfile'),
      forwarded('dirtyState'),
      forwarded('hideTitle'),
      forwarded('primaryActions'),
      forwarded('overflowActions'),
      forwarded('exitAction'),
      forwarded('metaSlot'),
      forwarded('statusSlot'),
      forwarded('actionsSlot'),
      notExposed('eyebrow', '合同表单身份由标题与业务状态承载。'),
      notExposed('breadcrumb', '合同表单路径由导航壳层承载。'),
      notExposed('variant', '合同表单页头只用于独立页面。'),
    ],
  ),
];

/**
 * 直接消费 `ProductPageHeader` 的页面（不经薄入口）。
 * 这些表面自己承担正式轴，因此必须显式登记；新页面直接消费权威而不登记会让入口契约失效。
 */
export const PRODUCT_PAGE_HEADER_DIRECT_CONSUMERS = [
  'views/ActionView.vue',
  'views/HomeView.vue',
  'views/MyWorkView.vue',
] as const;

const ENTRY_BY_ID = new Map(PRODUCT_PAGE_HEADER_ENTRIES.map((item) => [item.id, item]));

export function resolveProductPageHeaderEntry(id: string): ProductPageHeaderEntryRegistry {
  const found = ENTRY_BY_ID.get(id);
  if (!found) throw new Error(`PRODUCT_PAGE_HEADER_ENTRY_UNKNOWN:${id}`);
  return found;
}

function axisDisposition(id: string, axis: ProductPageHeaderAxis): ProductPageHeaderAxisDisposition {
  const disposition = resolveProductPageHeaderEntry(id).axes.find((item) => item.axis === axis);
  if (!disposition) throw new Error(`PRODUCT_PAGE_HEADER_AXIS_UNDECLARED:${id}:${axis}`);
  return disposition;
}

/** 入口对某条轴声明的固定值；轴未被固定时抛错，绝不回落到隐式默认。 */
export function resolveProductPageHeaderFixedAxis(id: string, axis: ProductPageHeaderAxis): string {
  const disposition = axisDisposition(id, axis);
  if (disposition.handling !== 'fixed') throw new Error(`PRODUCT_PAGE_HEADER_AXIS_NOT_FIXED:${id}:${axis}`);
  return disposition.value;
}

export function resolveProductPageHeaderFixedMode(id: string): ProductPagePresentationMode {
  return resolveProductPageHeaderFixedAxis(id, 'presentationMode') as ProductPagePresentationMode;
}

export function resolveProductPageHeaderFixedRenderProfile(id: string): ProductPageRenderProfile | null {
  const disposition = axisDisposition(id, 'renderProfile');
  return disposition.handling === 'fixed' ? (disposition.value as ProductPageRenderProfile) : null;
}

export function resolveProductPageHeaderForwardedAxes(id: string): readonly ProductPageHeaderAxis[] {
  return resolveProductPageHeaderEntry(id)
    .axes.filter((item) => item.handling === 'forwarded')
    .map((item) => item.axis);
}
