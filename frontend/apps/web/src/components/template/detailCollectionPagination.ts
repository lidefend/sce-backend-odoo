/**
 * 主从关系（one2many）明细集合分页的唯一消费入口（P0 契约消费层）。
 *
 * 每页记录数是契约声明事实（`relation_entry.page_size`），由声明层给出；
 * 前端只原样消费：缺失或非法即 `ContractGapError` 停机，回声明层要结果。
 * 组件不得再出现硬编码页大小，也不得为非 one2many 集合补默认值。
 */
import { requireDeclaredNumber } from '../../app/contract/contractGap';

export type DetailCollectionFieldRef = {
  name?: string;
  type?: string;
};

const DECLARATION_LAYER = 'P0:smart_core:page_assembler:relation_entry.page_size';

/**
 * 解析某个字段的明细集合页大小。
 *
 * - `one2many`：严格消费声明值，缺失/非法即停机；
 * - 其它字段类型：不参与明细分页，声明不适用，返回 `null`（不是默认值）。
 */
export function resolveDetailCollectionPageSize(
  raw: unknown,
  field: DetailCollectionFieldRef,
): number | null {
  if (String(field.type || '').trim().toLowerCase() !== 'one2many') return null;
  const fieldName = String(field.name || '').trim() || 'one2many';
  return requireDeclaredNumber(raw, {
    missing: `formStructure.relation_entry.page_size(${fieldName})`,
    requiredDeclarationLayer: DECLARATION_LAYER,
  });
}

/** 页数：声明不适用（`null`）时只有一页。 */
export function detailCollectionPageCount(rowCount: number, pageSize: number | null): number {
  if (!pageSize) return 1;
  const total = Number.isFinite(rowCount) ? Math.max(0, Math.trunc(rowCount)) : 0;
  return Math.max(1, Math.ceil(total / pageSize));
}

/** 按声明页大小切片：实际可见记录集合完全由声明值决定。 */
export function paginateDetailCollectionRows<T>(
  rows: readonly T[],
  page: number,
  pageSize: number | null,
): readonly T[] {
  if (!pageSize) return rows;
  const safePage = Number.isFinite(page) && page > 0 ? Math.trunc(page) : 1;
  const start = (safePage - 1) * pageSize;
  return rows.slice(start, start + pageSize);
}
