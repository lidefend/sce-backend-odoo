export type Dictionary = Record<string, any>

export interface OdooUser {
  id: number
  login: string
  name: string
  email?: string
  company_name?: string
  company_id?: number | null
  groups_xmlids?: string[]
  allowed_company_ids?: number[]
  is_platform_admin?: boolean
  is_system_admin?: boolean
}

export interface NavNode {
  id?: number
  menu_id?: number
  action_id?: number
  key?: string
  label?: string
  name?: string
  title?: string
  route?: string
  model?: string
  scene_key?: string
  entry_target?: Dictionary
  meta?: Dictionary
  children?: NavNode[]
}

export interface SystemInit {
  user?: OdooUser
  navigation?: {
    nav?: NavNode[]
    route_authority?: Dictionary
    contract_version?: string
  }
  navigation_v1?: { nav?: NavNode[]; route_authority_v1?: Dictionary }
  role_surface?: Dictionary
  workspace_home?: Dictionary
  record_context?: Dictionary
  capabilities?: unknown[] | Dictionary
  scenes?: unknown[]
  page_contracts?: unknown[] | Dictionary
  intents?: unknown[] | Dictionary
  default_route?: string | Dictionary
  product_version?: string
  source_revision?: string
  contract_mode?: string
}

export interface PageContract {
  raw: Dictionary
  pageInfo: Dictionary
  layoutContract: Dictionary
  statusContract: Dictionary
  actionContract: Dictionary
  dataContract: Dictionary
  runtimeContract: Dictionary
  searchContract: Dictionary
  workflowContract: Dictionary
}

export interface FieldSpec {
  code: string
  label: string
  type: string
  hidden?: boolean
  defaultVisible?: boolean
  sortable?: boolean
  required: boolean
  readonly: boolean
  relation: string
  selection: Array<{ label: string; value: unknown }>
  config: Dictionary
  semanticRole?: 'summary' | 'task' | 'context' | 'risk' | 'relation' | 'activity' | 'audit' | ''
  semanticSlot?: string
  semanticGroup?: string
  span?: number
  hideLabel?: boolean
  widgetKey?: string
}

export interface SemanticFormNode {
  key: string
  kind: string
  title: string
  text: string
  role: FieldSpec['semanticRole']
  zone: 'primary' | 'subordinate'
  columns: number
  span: number
  visible: boolean
  fields: FieldSpec[]
  children: SemanticFormNode[]
  action?: BusinessAction
  nativeWidget?: string
}

export interface SemanticFormModel {
  presentationMode: 'task' | 'workspace'
  primaryNodes: SemanticFormNode[]
  subordinateNodes: SemanticFormNode[]
  layoutHints: Dictionary
  slots?: Array<{ slot: string; title: string; role: string; groups: Array<{ name: string; title: string; role: string; fieldRefs: string[]; columns?: number }> }>
}

export interface BusinessAction {
  key: string
  label: string
  type: 'primary' | 'success' | 'warning' | 'danger' | 'info' | ''
  intent?: string
  button: Dictionary
  params: Dictionary
  confirmMessage?: string
  enabled?: boolean
  reasonCode?: string
  target?: Dictionary
  actionId?: string
  backendIdentity?: string
  sourceWidgetId?: string
  targetScope?: string
  sourceChannel?: string
  triggerType?: string
  presentationTier?: "primary" | "secondary" | "overflow" | "configuration" | "inline" | ""
}

export interface ListDataResult {
  records?: Dictionary[]
  rows?: Dictionary[]
  total?: number
  aggregates?: Dictionary
  grouped_rows?: Dictionary[]
  group_paging?: Dictionary
}

export interface MyWorkItem {
  id?: number
  key?: string
  title?: string
  label?: string
  section?: string
  section_label?: string
  deadline?: string
  priority?: string
  reason_code?: string
  model?: string
  record_id?: number
  target?: Dictionary
  actions?: Array<{ key: string; label: string; intent: string; params?: Dictionary }>
}

export interface MyWorkSummary {
  summary?: Array<{ key: string; label: string; count: number }>
  items?: MyWorkItem[]
  sections?: Array<{ key: string; label: string; items?: MyWorkItem[] }>
  product_workspace?: { sections?: Array<{ key: string; label: string; count: number; items?: MyWorkItem[] }> }
}
