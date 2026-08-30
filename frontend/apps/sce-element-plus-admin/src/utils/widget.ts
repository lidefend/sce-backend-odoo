import type { Dictionary } from '@/types/contracts'

export type StatusTagType = 'success' | 'warning' | 'danger' | 'info' | 'primary'

export function resolveFieldWidget(config: Dictionary, field: Dictionary = {}): string {
  const explicit = String(
    config.widget ||
    config.componentConfig?.widget ||
    config.component_config?.widget ||
    config.fieldInfo?.widget ||
    config.field_info?.widget ||
    '',
  ).trim().toLowerCase()
  if (explicit) return explicit
  const code = String(field.code || field.name || '').toLowerCase()
  const type = String(field.type || '').toLowerCase()
  const relation = String(field.relation || config.relation || '').toLowerCase()
  if (type === 'html') return 'html'
  if (type === 'json' || /(^|_)json($|_)/.test(code)) return 'json'
  if (type === 'binary' && /(image|avatar|logo|photo|signature)/.test(code)) return 'image'
  if ((type === 'many2many' && relation === 'ir.attachment') || /(^|_)attachment_ids$/.test(code)) return 'many2many_binary'
  if (type === 'selection' && /(^|_)(state|status|stage|lifecycle_state|workflow_state|approval_state)$/.test(code)) return 'statusbar'
  return ''
}

export function statusTagType(value: unknown): StatusTagType {
  const text = String(value || '').toLowerCase()
  if (/done|complete|approved|confirmed|success|通过|完成|确认/.test(text)) return 'success'
  if (/reject|cancel|failed|error|danger|驳回|取消|失败|错误/.test(text)) return 'danger'
  if (/pending|waiting|draft|unsubmitted|to_submit|warning|待|草稿|未提交|待提交|未审核/.test(text)) return 'warning'
  if (/submitted|closed|archived|inactive|已提交|已关闭|已归档|停用/.test(text)) return 'info'
  if (/running|in_progress|active|进行中|在建|启用/.test(text)) return 'primary'
  return 'primary'
}

export function normalizeRelationIds(value: unknown): number[] {
  const rows = Array.isArray(value) ? value : value ? [value] : []
  return rows
    .map((item) => Number(
      Array.isArray(item)
        ? item[0]
        : item && typeof item === 'object'
          ? (item as Dictionary).id
          : item,
    ))
    .filter((id) => Number.isInteger(id) && id > 0)
}
