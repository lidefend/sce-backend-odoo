export const fieldLabelMap: Record<string, string> = {
  child_ids: '联系人',
  bank_ids: '账户明细',
  category_id: '标签',
  project_ids: '关联项目',
  task_ids: '任务',
  user_ids: '关联用户',
  company_ids: '所属公司',
  comment: '备注',
  sc_supplier_note: '供应商备注',
  validation_status: '校验状态',
  can_review: '允许审核',
  archived: '已归档',
  engineering_category_text: '工程类别',
  received_amount: '已收金额',
  unreceived_amount: '未收金额',
  visible_unreceived_rate: '未收比例',
  affiliated_person: '挂靠人',
  engineering_address: '工程地址',
  engineering_content: '工程内容',
  entry_user_text: '录入人',
  entry_time: '录入时间',
  attachment_text: '附件',
  contract_duration_text: '合同工期',
}

export const statusLabelMap: Record<string, string> = {
  draft: '草稿',
  no: '否',
  yes: '是',
}

export function fieldLabel(code: string, fallback?: unknown): string {
  const codeKey = normalizeLabelKey(code)
  const fallbackText = String(fallback ?? '')
  return fieldLabelMap[codeKey] || fieldLabelMap[normalizeLabelKey(fallbackText)] || fallbackText || code
}

function normalizeLabelKey(value: string): string {
  return value
    .replace(/([a-z])([A-Z])/g, '$1_$2')
    .trim()
    .replace(/[\s.-]+/g, '_')
    .toLowerCase()
}

export function displayValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return '-'
  if (value === false) return '否'
  if (value === true) return '是'
  if (Array.isArray(value)) {
    if (value.length === 2 && typeof value[0] === 'number' && typeof value[1] === 'string') return value[1]
    return value.map(displayValue).join('、')
  }
  if (typeof value === 'object') {
    const row = value as Record<string, unknown>
    return String(row.display_name ?? row.name ?? row.label ?? JSON.stringify(value))
  }
  const text = String(value)
  return statusLabelMap[text.toLowerCase()] || text
}

export function displayFieldValue(
  value: unknown,
  code: string,
  selection: Array<{ label: string; value: unknown }> = [],
  fieldType = '',
): string {
  const option = selection.find((item) => String(item.value) === String(value))
  if (option) return option.label
  if (value === false && fieldType && fieldType.toLowerCase() !== 'boolean') return '-'
  return displayValue(value)
}

export function downloadText(content: string, filename: string, type = 'text/csv;charset=utf-8') {
  const blob = new Blob(['\ufeff', content], { type })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}
