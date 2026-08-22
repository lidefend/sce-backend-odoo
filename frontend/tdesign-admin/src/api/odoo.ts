import type { AxiosRequestConfig } from 'axios';
import axios from 'axios';

export interface OdooUser {
  id: number;
  login: string;
  name: string;
  company_name?: string;
  groups_xmlids?: string[];
  email?: string;
  lang?: string;
  tz?: string;
  is_platform_admin?: boolean;
  is_system_admin?: boolean;
  company_id?: number | null;
  allowed_company_ids?: number[];
  company?: { id?: number | null; name?: string; display_name?: string } | null;
}
export interface NavNode {
  key?: string;
  label?: string;
  name?: string;
  title?: string;
  id?: number;
  menu_id?: number;
  action_id?: number;
  model?: string;
  route?: string;
  children?: NavNode[];
  meta?: Record<string, unknown>;
  entry_target?: Record<string, unknown>;
  scene_key?: string;
}
export interface SystemInit {
  user?: OdooUser;
  navigation_v1?: { nav?: NavNode[]; route_authority_v1?: Record<string, unknown> };
  role_surface?: {
    role_label?: string;
    role_code?: string;
    role_codes?: string[];
    primary_role_code?: string;
    is_platform_admin?: boolean;
    is_system_admin?: boolean;
    admin?: boolean;
    capabilities?: unknown;
  };
  workspace_home?: Record<string, unknown>;
  record_context?: Record<string, unknown>;
  ext_facts?: Record<string, unknown>;
  brand?: Record<string, unknown>;
  capabilities?: unknown[] | Record<string, unknown>;
  scenes?: unknown[];
  page_contracts?: unknown[] | Record<string, unknown>;
  intents?: unknown[] | Record<string, unknown>;
  scene_ready_contract_v1?: Record<string, unknown>;
  init_meta?: Record<string, unknown>;
  init_contract_v1?: Record<string, unknown>;
  nav_meta?: Record<string, unknown>;
  default_route?: string;
  version?: unknown;
  product_version?: string;
  source_revision?: string;
  contract_mode?: string;
}
const db = String(import.meta.env.VITE_ODOO_DB || 'sc_dev_demo').trim();
const tenant = String(import.meta.env.VITE_TENANT || 'default').trim();
const http = axios.create({ baseURL: String(import.meta.env.VITE_API_BASE_URL || ''), timeout: 30000 });
const lastRequestMeta = { intent: '', traceId: '', completedAt: '', status: 0 };
export class OdooApiError extends Error {
  code: string;
  reasonCode: string;
  status: number;
  traceId: string;
  retryable: boolean;
  suggestedAction: string;
  details: Record<string, unknown>;

  constructor(
    message: string,
    options: {
      code?: string;
      reasonCode?: string;
      status?: number;
      traceId?: string;
      retryable?: boolean;
      suggestedAction?: string;
      details?: Record<string, unknown>;
    } = {},
  ) {
    super(message);
    this.name = 'OdooApiError';
    this.code = String(options.code || 'BUSINESS_REQUEST_FAILED');
    this.reasonCode = String(options.reasonCode || options.code || 'BUSINESS_REQUEST_FAILED');
    this.status = Number(options.status || 0);
    this.traceId = String(options.traceId || '');
    this.retryable = options.retryable === true;
    this.suggestedAction = String(options.suggestedAction || '');
    this.details = options.details || {};
  }
}

interface IntentErrorPayload {
  code?: string;
  reason_code?: string;
  message?: string;
  retryable?: boolean;
  suggested_action?: string;
  details?: Record<string, unknown>;
}
function traceId() {
  return crypto.randomUUID?.() || `trace_${Date.now()}`;
}
function token() {
  return localStorage.getItem('sc-odoo-token') || '';
}
export async function intent<T>(name: string, params: Record<string, unknown> = {}, options: AxiosRequestConfig = {}) {
  const trace = traceId();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'X-Odoo-DB': db,
    'X-Tenant': tenant,
    'X-Trace-Id': trace,
  };
  if (!['login', 'auth.login', 'session.bootstrap', 'sys.intents'].includes(name) && token())
    headers.Authorization = `Bearer ${token()}`;
  try {
    const response = await http.post<{
      ok?: boolean;
      data?: T;
      error?: IntentErrorPayload;
      meta?: { trace_id?: string; suggested_action?: string; reason_code?: string };
    }>(
      `/api/v1/intent?db=${encodeURIComponent(db)}`,
      { intent: name, params: withStoredBusinessContext(params) },
      { ...options, headers: { ...headers, ...(options.headers || {}) } },
    );
    const body = response.data;
    Object.assign(lastRequestMeta, {
      intent: name,
      traceId: String(body?.meta?.trace_id || trace),
      completedAt: new Date().toISOString(),
      status: response.status,
    });
    if (body?.ok === false || body?.error) {
      throw new OdooApiError(body.error?.message || '业务请求失败', {
        code: body.error?.code,
        reasonCode: body.error?.reason_code || body.meta?.reason_code,
        status: response.status,
        traceId: body.meta?.trace_id || trace,
        retryable: body.error?.retryable,
        suggestedAction: body.error?.suggested_action || body.meta?.suggested_action,
        details: body.error?.details,
      });
    }
    return (body?.data ?? body) as T;
  } catch (cause) {
    if (cause instanceof OdooApiError) throw cause;
    if (axios.isAxiosError(cause)) {
      const body = cause.response?.data as
        | { error?: IntentErrorPayload; meta?: { trace_id?: string; suggested_action?: string; reason_code?: string } }
        | undefined;
      const status = Number(cause.response?.status || 0);
      Object.assign(lastRequestMeta, {
        intent: name,
        traceId: String(body?.meta?.trace_id || trace),
        completedAt: new Date().toISOString(),
        status,
      });
      if (status === 401) clearToken();
      throw new OdooApiError(body?.error?.message || cause.message || '网络请求失败', {
        code: body?.error?.code || (status ? `HTTP_${status}` : 'NETWORK_ERROR'),
        reasonCode: body?.error?.reason_code || body?.meta?.reason_code,
        status,
        traceId: body?.meta?.trace_id || trace,
        retryable: body?.error?.retryable === true || status === 429 || status >= 500,
        suggestedAction: body?.error?.suggested_action || body?.meta?.suggested_action,
        details: body?.error?.details,
      });
    }
    throw cause;
  }
}

export function getLastRequestMeta() {
  return { ...lastRequestMeta };
}

function withStoredBusinessContext(params: Record<string, unknown>) {
  if (typeof window === 'undefined') return params;
  try {
    const stored = JSON.parse(localStorage.getItem('sc-odoo-business-context') || '{}') as Record<string, unknown>;
    const context = Object.fromEntries(
      Object.entries(stored).filter(([, value]) => value !== undefined && value !== null && value !== ''),
    );
    return Object.keys(context).length ? { ...context, ...params } : params;
  } catch {
    return params;
  }
}

async function authEndpoint<T>(path: string, body?: Record<string, string>) {
  const response = await http.request<T>({
    url: path,
    method: body ? 'POST' : 'GET',
    data: body,
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      'X-Odoo-DB': db,
      'X-Tenant': tenant,
    },
  });
  return response.data;
}

export function beginAccountActivation(activationCode: string) {
  return authEndpoint<{ ok: boolean; message?: string; activation_context?: string }>('/api/v1/auth/activation/start', {
    activation_code: activationCode,
  });
}

export function completeAccountActivation(activationContext: string, password: string, confirmPassword: string) {
  return authEndpoint<{ ok: boolean; message?: string }>('/api/v1/auth/activation/complete', {
    activation_context: activationContext,
    password,
    confirm_password: confirmPassword,
  });
}

export function getPasswordRecoveryStatus() {
  return authEndpoint<{ ok: boolean; self_service_enabled: boolean; message?: string }>(
    '/api/v1/auth/password-recovery/status',
  );
}
export async function login(loginName: string, password: string) {
  const result = await intent<{ token?: string; session?: { token?: string }; user?: OdooUser }>(
    'login',
    { login: loginName, password, contract_mode: 'default', db },
    { headers: { 'X-Anonymous-Intent': '1' } },
  );
  const accessToken = String(result.session?.token || result.token || '');
  if (!accessToken) throw new Error('登录响应没有 token');
  localStorage.setItem('sc-odoo-token', accessToken);
  return { token: accessToken, user: result.user };
}
export function clearToken() {
  localStorage.removeItem('sc-odoo-token');
}
export async function systemInit(context: Record<string, unknown> = {}) {
  return intent<SystemInit>('system.init', {
    scene: 'web',
    with_preload: false,
    scene_ready_mode: 'registry',
    with: ['workspace_home'],
    ...context,
  });
}

export async function searchRecordContext(params: Record<string, unknown> = {}) {
  return intent<Record<string, unknown>>('record.context.search', params);
}

export interface IntentCatalogResult {
  intents?: string[];
  intents_meta?: Record<string, unknown>;
  intent_catalog?: Array<Record<string, unknown>>;
}

export async function fetchIntentCatalog() {
  return intent<IntentCatalogResult>('meta.intent_catalog', {});
}

export async function validateRouteAuthority(params: Record<string, unknown>) {
  return intent<{ allowed?: boolean }>('route.authority.validate', params);
}
export async function logout() {
  if (!token()) {
    clearToken();
    return;
  }
  try {
    await intent('auth.logout', {});
  } finally {
    clearToken();
  }
}

export interface GroupSummaryItem {
  group_key?: string;
  field?: string;
  value?: unknown;
  label?: string;
  count?: number;
  domain?: unknown[];
}

export interface GroupedDataRow extends GroupSummaryItem {
  total_count?: number;
  sample_rows?: Array<Record<string, unknown>>;
  sample_count?: number;
  is_sampled?: boolean;
  page_applied_offset?: number;
  page_applied_size?: number;
  page_offset?: number;
  page_size?: number;
  page_current?: number;
  page_total?: number;
  page_range_start?: number;
  page_range_end?: number;
  page_has_prev?: boolean;
  page_has_next?: boolean;
  aggregates?: Record<string, Record<string, unknown>>;
}

export interface GroupPaging {
  group_offset?: number;
  group_limit?: number;
  group_count?: number;
  group_total?: number;
  group_window_start?: number;
  group_window_end?: number;
  window_start?: number;
  window_end?: number;
  has_prev?: boolean;
  has_next?: boolean;
  has_more?: boolean;
  prev_group_offset?: number | null;
  next_group_offset?: number | null;
}

export interface ListDataResult {
  records?: Array<Record<string, unknown>>;
  rows?: Array<Record<string, unknown>>;
  total?: number;
  aggregates?: Record<string, Record<string, unknown>>;
  group_summary?: GroupSummaryItem[];
  grouped_rows?: GroupedDataRow[];
  group_paging?: GroupPaging;
}

export async function listData(params: {
  model: string;
  fields: string[];
  domain?: unknown[];
  order?: string;
  limit?: number;
  offset?: number;
  search_term?: string;
  context?: Record<string, unknown>;
  group_by?: string | string[];
  group_offset?: number;
  need_group_total?: boolean;
  group_sample_limit?: number;
  group_limit?: number;
  group_page_size?: number;
  group_page_offsets?: Record<string, number>;
  need_aggregates?: boolean;
}) {
  return intent<ListDataResult>('api.data', {
    op: 'list',
    model: params.model,
    fields: params.fields,
    domain: params.domain || [],
    order: params.order || '',
    search_term: params.search_term || '',
    limit: params.limit || 20,
    offset: params.offset || 0,
    context: params.context || {},
    need_total: true,
    group_by: params.group_by || undefined,
    group_offset: params.group_offset || 0,
    need_group_total: params.need_group_total === true,
    group_sample_limit: params.group_sample_limit,
    group_limit: params.group_limit,
    group_page_size: params.group_page_size,
    group_page_offsets: params.group_page_offsets || {},
    need_aggregates: params.need_aggregates === true,
  });
}

export interface OdooNotificationRecord {
  id: number;
  is_read?: boolean;
  sc_subject?: string;
  sc_body?: string;
  sc_message_date?: string;
  sc_record_name?: string;
  author_id?: unknown;
  notification_type?: string;
  sc_source_model?: string;
  sc_source_res_id?: number | string;
}

export async function listNotifications(limit = 100) {
  return listData({
    model: 'mail.notification',
    fields: [
      'id',
      'is_read',
      'sc_subject',
      'sc_body',
      'sc_message_date',
      'sc_record_name',
      'author_id',
      'notification_type',
      'sc_source_model',
      'sc_source_res_id',
    ],
    domain: [
      ['sc_is_current_recipient', '=', true],
      ['notification_type', '=', 'inbox'],
    ],
    order: 'sc_message_date desc, id desc',
    limit: Math.min(Math.max(limit, 1), 100),
    offset: 0,
  });
}

export async function markNotificationRead(id: number, read = true) {
  return updateRecord('mail.notification', id, {
    is_read: read,
    read_date: read ? odooDateNow() : false,
  });
}

function odooDateNow() {
  const date = new Date();
  const pad = (value: number) => String(value).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(
    date.getMinutes(),
  )}:${pad(date.getSeconds())}`;
}

export async function formContract(params: {
  model: string;
  actionId?: number;
  menuId?: number;
  recordId?: number;
  context?: Record<string, unknown>;
}) {
  return intent<Record<string, unknown>>('ui.contract.v2', {
    op: 'model',
    model: params.model,
    view_type: 'form',
    action_id: params.actionId || undefined,
    menu_id: params.menuId || undefined,
    record_id: params.recordId || undefined,
    context: params.context || {},
    contractVersion: '2.0.0',
    accepted_contract_versions: ['2.0.x'],
    client_contract_capabilities: [
      'container_tree.v2',
      'data_source.v2',
      'action_rule.v2',
      'relation_entry.v2',
      'status_contract.v2',
    ],
    client_type: 'web_pc',
    delivery_profile: 'full',
  });
}

export async function relationOptions(params: {
  model: string;
  searchTerm?: string;
  domain?: unknown[];
  limit?: number;
  context?: Record<string, unknown>;
}) {
  const result = await listData({
    model: params.model,
    fields: ['id', 'display_name'],
    domain: params.domain || [],
    search_term: params.searchTerm || '',
    limit: params.limit || 60,
    context: params.context || {},
  });
  return result.records || result.rows || [];
}

function requestIdentity(prefix: string) {
  const id = crypto.randomUUID?.() || `${Date.now()}_${Math.random().toString(16).slice(2)}`;
  return { request_id: `${prefix}_${id}`, idempotency_key: `${prefix}_${id}` };
}

export async function createRecord(
  model: string,
  vals: Record<string, unknown>,
  context: Record<string, unknown> = {},
) {
  return intent<{ id: number; model: string }>('api.data.create', {
    model,
    vals,
    context,
    ...requestIdentity('create'),
  });
}

export async function updateRecord(
  model: string,
  id: number,
  vals: Record<string, unknown>,
  context: Record<string, unknown> = {},
  ifMatch = '',
) {
  return intent<{ id: number; model: string }>('api.data.write', {
    model,
    id,
    vals,
    context,
    if_match: ifMatch || undefined,
    ...requestIdentity('write'),
  });
}

export async function deleteRecords(model: string, ids: number[], context: Record<string, unknown> = {}) {
  return intent<{ ids: number[]; deleted_count: number; model: string }>('api.data.unlink', {
    model,
    ids,
    context,
    ...requestIdentity('unlink'),
  });
}

export interface ExportCsvResult {
  file_name?: string;
  filename?: string;
  mime_type?: string;
  content_b64?: string;
  content?: string;
  count?: number;
  fields?: string[];
  column_labels?: Record<string, string>;
}

export async function exportRecordsCsv(params: {
  model: string;
  fields?: string[] | '*';
  domain?: unknown[];
  ids?: number[];
  order?: string;
  limit?: number;
  columnLabels?: Record<string, string>;
}) {
  return intent<ExportCsvResult>('api.data', {
    op: 'export_csv',
    model: params.model,
    fields: params.fields || ['id', 'name'],
    domain: params.domain || [],
    ids: params.ids || [],
    order: params.order || '',
    limit: params.limit || 2000,
    column_labels: params.columnLabels || {},
  });
}

export interface BatchUpdateResult {
  model?: string;
  action?: string;
  requested_ids?: number[];
  succeeded?: number;
  failed?: number;
  results?: Array<{ id: number; ok: boolean; reason_code?: string; message?: string }>;
  failed_preview?: Array<{ id: number; ok: boolean; reason_code?: string; message?: string }>;
}

export async function batchUpdateRecords(params: {
  model: string;
  ids: number[];
  action?: 'archive' | 'activate' | 'assign' | string;
  assigneeId?: number;
  vals?: Record<string, unknown>;
  reason?: string;
  failedPreviewLimit?: number;
}) {
  return intent<BatchUpdateResult>('api.data.batch', {
    model: params.model,
    ids: params.ids,
    action: params.action || '',
    assignee_id: params.assigneeId,
    vals: params.vals || {},
    reason: params.reason || undefined,
    failed_preview_limit: params.failedPreviewLimit || 10,
    context: {},
  });
}

export async function saveSearchFavorite(params: {
  model: string;
  name: string;
  domain?: unknown[];
  order?: string;
  actionId?: number;
  isDefault?: boolean;
  isShared?: boolean;
}) {
  return intent<{ id: number; name: string }>('search.favorite.set', {
    model: params.model,
    name: params.name,
    domain: params.domain || [],
    order: params.order || '',
    action_id: params.actionId,
    is_default: Boolean(params.isDefault),
    is_shared: Boolean(params.isShared),
  });
}

export async function executeButton(params: {
  model: string;
  recordId?: number;
  button: Record<string, unknown>;
  context?: Record<string, unknown>;
}) {
  return intent<Record<string, unknown>>('execute_button', {
    model: params.model,
    res_id: params.recordId,
    button: params.button,
    context: params.context || {},
  });
}

export interface OnchangeResult {
  patch?: Record<string, unknown>;
  modifiers_patch?: Record<string, Record<string, unknown>>;
  warnings?: Array<{ title?: string; message?: string }>;
  line_patches?: Array<Record<string, unknown>>;
}

export async function triggerOnchange(params: {
  model: string;
  recordId?: number | null;
  values: Record<string, unknown>;
  changedFields: string[];
}) {
  return intent<OnchangeResult>('api.onchange', {
    model: params.model,
    res_id: params.recordId || undefined,
    values: params.values,
    changed_fields: params.changedFields,
    context: {},
  });
}

export interface ChatterTimelineEntry {
  key: string;
  type: string;
  typeLabel?: string;
  title?: string;
  meta?: string;
  body?: string;
  at?: string;
  id?: number;
  activity?: {
    id?: number;
    assignee_user_id?: number;
    assignee_name?: string;
    deadline?: string;
    activity_type?: string;
    can_complete?: boolean;
    can_cancel?: boolean;
  };
  attachment?: { id?: number; name?: string; mimetype?: string };
}

export interface CollaborationUserOption {
  id: number;
  name: string;
  login?: string;
  email?: string;
  partner_id?: number;
  partner_name?: string;
}

export async function fetchChatterTimeline(params: {
  model: string;
  recordId: number;
  limit?: number;
  offset?: number;
}) {
  return intent<{
    items: ChatterTimelineEntry[];
    counts?: Record<string, number>;
    paging?: { offset?: number; limit?: number; next_offset?: number | null; has_more?: boolean };
  }>('chatter.timeline', {
    model: params.model,
    res_id: params.recordId,
    limit: params.limit || 40,
    offset: params.offset || 0,
    include_audit: true,
  });
}

export async function postChatterMessage(params: {
  model: string;
  recordId: number;
  body: string;
  subject?: string;
  mode?: 'message' | 'note';
  mentionUserIds?: number[];
}) {
  return intent<{ result?: { message_id?: number } }>('chatter.post', {
    model: params.model,
    res_id: params.recordId,
    body: params.body,
    subject: params.subject,
    mode: params.mode || 'message',
    mention_user_ids: params.mentionUserIds || [],
  });
}

export async function scheduleChatterActivity(params: {
  model: string;
  recordId: number;
  summary: string;
  dateDeadline?: string;
  note?: string;
  activityTypeXmlid?: string;
  userId?: number;
}) {
  return intent<{ result?: { activity_id?: number } }>('chatter.activity.schedule', {
    model: params.model,
    res_id: params.recordId,
    summary: params.summary,
    date_deadline: params.dateDeadline,
    note: params.note,
    activity_type_xmlid: params.activityTypeXmlid,
    user_id: params.userId,
  });
}

export async function updateChatterActivity(params: {
  model: string;
  recordId: number;
  activityId: number;
  action: 'done' | 'cancel';
  note?: string;
}) {
  return intent<{ result?: { activity_id?: number; action?: string } }>('chatter.activity.update', {
    model: params.model,
    res_id: params.recordId,
    activity_id: params.activityId,
    action: params.action,
    note: params.note,
  });
}

export async function searchCollaborationUsers(query = '', limit = 20) {
  return intent<{ items?: CollaborationUserOption[] }>('collaboration.users.search', { query, limit });
}

export async function listRecordFollowers(model: string, recordId: number) {
  const result = await listData({
    model: 'mail.followers',
    fields: ['id', 'partner_id'],
    domain: [
      ['res_model', '=', model],
      ['res_id', '=', recordId],
    ],
    limit: 100,
  });
  return result.records || result.rows || [];
}

export async function addRecordFollower(model: string, recordId: number, partnerId: number) {
  return createRecord('mail.followers', { res_model: model, res_id: recordId, partner_id: partnerId });
}

export async function removeRecordFollower(followerId: number) {
  return deleteRecords('mail.followers', [followerId]);
}

export async function uploadFile(params: {
  model: string;
  recordId: number;
  name: string;
  mimetype: string;
  data: string;
}) {
  return intent<Record<string, unknown>>('file.upload', {
    model: params.model,
    res_id: params.recordId,
    name: params.name,
    mimetype: params.mimetype,
    data: params.data,
  });
}

export async function downloadFile(params: { attachmentId: number }) {
  return intent<{ content_b64?: string; filename?: string; mimetype?: string }>('file.download', {
    attachment_id: params.attachmentId,
  });
}

export async function getUserViewPreference(params: {
  model: string;
  actionId?: number;
  viewType?: string;
  preferenceKey?: string;
}) {
  return intent<{ preference?: Record<string, unknown> }>('user.view.preference.get', {
    model: params.model,
    action_id: params.actionId,
    view_type: params.viewType || 'list',
    preference_key: params.preferenceKey || 'list_columns',
  });
}

export async function setUserViewPreference(params: {
  model: string;
  actionId?: number;
  viewType?: string;
  preferenceKey?: string;
  preference: Record<string, unknown>;
}) {
  return intent<{ preference?: Record<string, unknown> }>('user.view.preference.set', {
    model: params.model,
    action_id: params.actionId,
    view_type: params.viewType || 'list',
    preference_key: params.preferenceKey || 'list_columns',
    preference: params.preference,
  });
}

export interface MyWorkItem {
  id?: number;
  key?: string;
  title?: string;
  label?: string;
  model?: string;
  record_id?: number;
  deadline?: string;
  priority?: string;
  section?: string;
  section_label?: string;
  reason_code?: string;
  target?: {
    route?: string;
    scene_key?: string;
    model?: string;
    record_id?: number;
    action_id?: number;
    menu_id?: number;
  };
  actions?: Array<{
    key: string;
    label: string;
    intent: string;
    params?: Record<string, unknown>;
    requires_reason?: boolean;
  }>;
}

export interface MyWorkSummary {
  generated_at?: string;
  summary?: Array<{ key: string; label: string; count: number }>;
  items?: MyWorkItem[];
  sections?: Array<{ key: string; label: string; count?: number; items?: MyWorkItem[] }>;
  status?: { state?: string; message?: string };
  product_workspace?: {
    sections?: Array<{ key: string; label: string; count: number; items: MyWorkItem[] }>;
    counts?: Record<string, number>;
    total?: number;
  };
}

export async function fetchMyWorkSummary(
  params: {
    page?: number;
    pageSize?: number;
    section?: string;
    search?: string;
    sortBy?: string;
    sortDir?: 'asc' | 'desc';
  } = {},
) {
  return intent<MyWorkSummary>('my.work.summary', {
    product_workspace: true,
    page: params.page || 1,
    page_size: params.pageSize || 40,
    section: params.section || 'all',
    source: 'all',
    reason_code: 'all',
    search: params.search || '',
    sort_by: params.sortBy || 'id',
    sort_dir: params.sortDir || 'desc',
  });
}

export async function completeMyWorkItemsBatch(params: { ids: number[]; source?: string; note?: string }) {
  return intent<{ success?: boolean; done_count?: number; failed_count?: number; message?: string }>(
    'my.work.complete_batch',
    {
      ids: params.ids,
      source: params.source || 'todo',
      note: params.note || '',
    },
  );
}

export async function completeMyWorkItem(params: { id: number; source?: string; note?: string }) {
  return intent<{ success?: boolean; message?: string }>('my.work.complete', params);
}

export async function executeMyWorkAction(action: { intent: string; params?: Record<string, unknown> }, reason = '') {
  return intent<{ success?: boolean; message?: string }>(action.intent, {
    ...(action.params || {}),
    ...(reason ? { reason } : {}),
  });
}

export interface UsageReport {
  generated_at?: string;
  totals?: { scene_open_total?: number; capability_open_total?: number };
  daily?: {
    scene_open?: Array<{ day: string; count: number }>;
    capability_open?: Array<{ day: string; count: number }>;
  };
  scene_top?: Array<{ key: string; count: number }>;
  capability_top?: Array<{ key: string; count: number }>;
  role_top?: Array<{
    role_code: string;
    combined_total?: number;
    scene_open_total?: number;
    capability_open_total?: number;
  }>;
  user_top?: Array<{
    user_id: number;
    combined_total?: number;
    scene_open_total?: number;
    capability_open_total?: number;
  }>;
  filters?: Record<string, unknown>;
}

export async function fetchUsageReport(
  params: {
    top?: number;
    days?: number;
    roleCode?: string;
    userId?: number;
    scenePrefix?: string;
    capabilityPrefix?: string;
  } = {},
) {
  return intent<UsageReport>('usage.report', {
    top: params.top || 10,
    days: params.days || 7,
    role_code: params.roleCode || '',
    user_id: params.userId || 0,
    scene_key_prefix: params.scenePrefix || '',
    capability_key_prefix: params.capabilityPrefix || '',
  });
}

export async function exportUsageCsv(params: Record<string, unknown>) {
  return intent<{ filename?: string; content?: string }>('usage.export.csv', params);
}

export async function fetchSceneHealth(params: { mode?: string; limit?: number; offset?: number } = {}) {
  return intent<Record<string, unknown>>('scene.health', {
    mode: params.mode || 'summary',
    limit: params.limit || 100,
    offset: params.offset || 0,
  });
}

export async function scenePackageList() {
  return intent<Record<string, unknown>>('scene.package.list', {});
}

export async function fetchCapabilityVisibilityReport() {
  return intent<Record<string, unknown>>('capability.visibility.report', {});
}

export interface AuthCredential {
  credential_id: string;
  name: string;
  state: 'active' | 'revoked' | 'expired' | string;
  scope?: string[];
  company_ids?: number[];
  expires_at?: string | false;
  last_used_at?: string | false;
  usage_count?: number;
  created_at?: string | false;
}

export async function listAuthCredentials() {
  const result = await intent<{ credentials?: AuthCredential[] }>('auth.credential.list', {});
  return result.credentials || [];
}

export async function createAuthCredential(params: {
  name: string;
  password: string;
  scope: string[];
  companyIds: number[];
  expiresAt?: string;
}) {
  return intent<{ api_key?: string; credential?: AuthCredential }>('auth.credential.create', {
    name: params.name,
    scope: params.scope,
    company_ids: params.companyIds,
    expires_at: params.expiresAt || false,
    credential: { type: 'password', secret: params.password },
  });
}

export async function revokeAuthCredential(credentialId: string) {
  return intent<{ credential?: AuthCredential }>('auth.credential.revoke', { credential_id: credentialId });
}

export async function rotateAuthCredential(credentialId: string, password: string) {
  return intent<{ api_key?: string; credential?: AuthCredential }>('auth.credential.rotate', {
    credential_id: credentialId,
    credential: { type: 'password', secret: password },
  });
}

export async function fetchGlobalMessageInbox(
  params: { limit?: number; offset?: number; unreadOnly?: boolean; sinceId?: number } = {},
) {
  return intent<{ items?: GlobalMessageItem[]; latest_id?: number }>('global.message.inbox', {
    limit: params.limit || 50,
    offset: params.offset || 0,
    unread_only: Boolean(params.unreadOnly),
    since_id: params.sinceId || undefined,
  });
}

export interface GlobalMessageItem {
  id: number;
  body: string;
  author_name?: string;
  conversation_key?: string;
  date?: string;
  is_outgoing?: boolean;
}

export interface GlobalMessageConversation {
  key: string;
  title?: string;
  participant_user_ids?: number[];
  latest_message?: GlobalMessageItem;
  unread_count?: number;
}

export async function fetchGlobalMessageConversations(params: { limit?: number; offset?: number } = {}) {
  return intent<{ items?: GlobalMessageConversation[]; total_unread?: number }>('global.message.conversations', {
    limit: params.limit || 50,
    offset: params.offset || 0,
  });
}

export async function sendGlobalMessage(params: { recipientUserIds: number[]; body: string }) {
  return intent<Record<string, unknown>>('global.message.send', {
    recipient_user_ids: params.recipientUserIds,
    body: params.body,
  });
}

export async function markGlobalMessagesRead(params: { conversationKey?: string; messageIds?: number[] }) {
  return intent<Record<string, unknown>>('global.message.read', {
    conversation_key: params.conversationKey || undefined,
    message_ids: params.messageIds || undefined,
  });
}

export function setSceneChannel(params: { channel: string; reason: string; companyId?: number }) {
  return intent<Record<string, unknown>>('scene.governance.set_channel', {
    channel: params.channel,
    reason: params.reason,
    company_id: params.companyId,
  });
}

export function rollbackSceneGovernance(reason: string) {
  return intent<Record<string, unknown>>('scene.governance.rollback', { reason });
}

export function pinStableSceneGovernance(reason: string) {
  return intent<Record<string, unknown>>('scene.governance.pin_stable', { reason });
}

export function exportSceneContract(params: { channel: string; reason: string }) {
  return intent<Record<string, unknown>>('scene.governance.export_contract', params);
}

export function exportScenePackage(params: {
  packageName: string;
  packageVersion: string;
  channel: string;
  reason: string;
}) {
  return intent<Record<string, unknown>>('scene.package.export', {
    package_name: params.packageName,
    package_version: params.packageVersion,
    scene_channel: params.channel,
    reason: params.reason,
  });
}

export function dryRunScenePackageImport(packagePayload: Record<string, unknown>) {
  return intent<Record<string, unknown>>('scene.package.dry_run_import', { package: packagePayload });
}

export function importScenePackage(params: {
  packagePayload: Record<string, unknown>;
  strategy: string;
  reason: string;
}) {
  return intent<Record<string, unknown>>('scene.package.import', {
    package: params.packagePayload,
    strategy: params.strategy,
    reason: params.reason,
  });
}

export async function loadMenuConfigurationPanel() {
  return intent<Record<string, unknown>>('ui.menu_config.panel.get', {});
}

export async function saveMenuConfigurationPanel(rows: Array<Record<string, unknown>>) {
  return intent<Record<string, unknown>>('ui.menu_config.panel.set', { rows });
}

export function createMenuConfigurationEntry(params: Record<string, unknown>) {
  return intent<Record<string, unknown>>('ui.menu_config.menu.create', params);
}

export function deleteMenuConfigurationEntry(menuId: number, recursive = false) {
  return intent<Record<string, unknown>>('ui.menu_config.menu.delete', { menu_id: menuId, recursive });
}

export function loadMenuConfigurationAudit(includeInactive = true) {
  return intent<Record<string, unknown>>('ui.menu_config.audit', { include_inactive: includeInactive });
}

export function loadMenuConfigurationVersions() {
  return intent<Record<string, unknown>>('ui.menu_config.versions', {});
}

export function rollbackMenuConfiguration(versionNo?: number) {
  return intent<Record<string, unknown>>('ui.menu_config.rollback', { version_no: versionNo });
}

export async function loadBusinessConfigSurface() {
  return intent<Record<string, unknown>>('ui.business_config.surface.get', {});
}

export function openBusinessConfigChangeSet(name = '') {
  return intent<Record<string, unknown>>('ui.business_config.change_set.open', { name });
}

export function loadBusinessConfigChangeSet(changeSetToken: string, roleKey = '') {
  return intent<Record<string, unknown>>('ui.business_config.change_set.get', {
    change_set_token: changeSetToken,
    role_key: roleKey || undefined,
  });
}

export function stageBusinessConfigChangeSetItem(params: Record<string, unknown>) {
  return intent<Record<string, unknown>>('ui.business_config.change_set.stage', params);
}

export function validateBusinessConfigChangeSet(changeSetToken: string) {
  return intent<Record<string, unknown>>('ui.business_config.change_set.validate', {
    change_set_token: changeSetToken,
  });
}

export function previewBusinessConfigChangeSet(changeSetToken: string, device = 'web_pc') {
  return intent<Record<string, unknown>>('ui.business_config.change_set.preview', {
    change_set_token: changeSetToken,
    device,
  });
}

export function publishBusinessConfigChangeSet(changeSetToken: string) {
  return intent<Record<string, unknown>>('ui.business_config.change_set.publish', {
    change_set_token: changeSetToken,
    ...requestIdentity('business_config_publish'),
  });
}

export function rollbackBusinessConfigChangeSet(changeSetToken: string) {
  return intent<Record<string, unknown>>('ui.business_config.change_set.rollback', {
    change_set_token: changeSetToken,
    ...requestIdentity('business_config_rollback'),
  });
}

export function discardBusinessConfigChangeSet(changeSetToken: string) {
  return intent<Record<string, unknown>>('ui.business_config.change_set.discard', { change_set_token: changeSetToken });
}

export function scanBusinessConfigCoverage(model = '') {
  return intent<Record<string, unknown>>('ui.business_config.coverage.scan', { model: model || undefined });
}

export function bootstrapBusinessConfigCoverage(params: Record<string, unknown> = {}) {
  return intent<Record<string, unknown>>('ui.business_config.coverage.bootstrap_missing', params);
}

export function listBusinessConfigContracts(params: Record<string, unknown> = {}) {
  return intent<Record<string, unknown>>('ui.business_config.contract.list', params);
}

export function getBusinessConfigContract(params: Record<string, unknown> = {}) {
  return intent<Record<string, unknown>>('ui.business_config.contract.get', params);
}

export function loadBusinessConfigContractVersions(model = '') {
  return intent<Record<string, unknown>>('ui.business_config.contract.versions', { model: model || undefined });
}

export function rollbackBusinessConfigContract(params: Record<string, unknown>) {
  return intent<Record<string, unknown>>('ui.business_config.contract.rollback', params);
}

export function compareBusinessConfigSnapshot(snapshot: Record<string, unknown>) {
  return intent<Record<string, unknown>>('ui.business_config.snapshot.compare', { snapshot });
}

export function exportBusinessConfigSnapshot() {
  return intent<Record<string, unknown>>('ui.business_config.snapshot.export', {});
}

export function auditBusinessListSearchConfig(params: Record<string, unknown>) {
  return intent<Record<string, unknown>>('ui.business_config.list_search.audit', params);
}

export function auditBusinessAnalysisConfig(params: Record<string, unknown>) {
  return intent<Record<string, unknown>>('ui.business_config.analysis.audit', params);
}

export function saveBusinessListSearchConfig(params: Record<string, unknown>) {
  return intent<Record<string, unknown>>('ui.business_config.list_search.set', params);
}

export function saveBusinessAnalysisConfig(params: Record<string, unknown>) {
  return intent<Record<string, unknown>>('ui.business_config.analysis.set', params);
}

export function auditBusinessFormConfig(params: Record<string, unknown>) {
  return intent<Record<string, unknown>>('ui.business_config.form.audit', params);
}

export function applyBusinessConfigLowCode(params: Record<string, unknown>) {
  return intent<Record<string, unknown>>('ui.business_config.lowcode.apply', params);
}

export function saveBusinessConfigContract(params: Record<string, unknown>) {
  return intent<Record<string, unknown>>('ui.business_config.contract.save', params);
}

export function publishBusinessConfigContract(params: Record<string, unknown>) {
  return intent<Record<string, unknown>>('ui.business_config.contract.publish', params);
}

export function snapshotBusinessConfigMutationAudit(params: Record<string, unknown> = {}) {
  return intent<Record<string, unknown>>('ui.business_config.mutation_audit.snapshot', params);
}

export function bootstrapBusinessListSearchConfig(params: Record<string, unknown>) {
  return intent<Record<string, unknown>>('ui.business_config.list_search.bootstrap', params);
}

export function bootstrapBusinessAnalysisConfig(params: Record<string, unknown>) {
  return intent<Record<string, unknown>>('ui.business_config.analysis.bootstrap', params);
}

export function bootstrapBusinessFormConfig(params: Record<string, unknown>) {
  return intent<Record<string, unknown>>('ui.business_config.form.bootstrap', params);
}

export function loadBusinessConfigApproval(model: string) {
  return intent<Record<string, unknown>>('sc.approval_policy.config.get', { model });
}

export function saveBusinessConfigApproval(params: Record<string, unknown>) {
  return intent<Record<string, unknown>>('sc.approval_policy.config.set', params);
}

export function saveBusinessConfigApprovalSteps(params: Record<string, unknown>) {
  return intent<Record<string, unknown>>('sc.approval_policy.steps.set', params);
}

export function setFormFieldPolicy(params: Record<string, unknown>) {
  return intent<Record<string, unknown>>('ui.form_field_policy.set', params);
}

export function createFormCustomField(params: Record<string, unknown>) {
  return intent<Record<string, unknown>>('ui.form_custom_field.create', params);
}

export function setFormFieldOrder(params: Record<string, unknown>) {
  return intent<Record<string, unknown>>('ui.form_field_order.set', params);
}

export function batchSetFormFieldConfig(params: Record<string, unknown>) {
  return intent<Record<string, unknown>>('ui.form_field_config.batch_set', params);
}

export interface ReleaseOperatorSurface {
  copy?: Record<string, unknown>;
  identity?: Record<string, unknown>;
  products?: Array<{ product_key: string; label?: string }>;
  product_delivery_console?: Record<string, unknown>;
  control_scope?: Record<string, unknown>;
  release_pipeline?: Record<string, unknown>;
  release_state?: Record<string, unknown>;
  pending_approval?: { actions?: Array<Record<string, unknown>> };
  candidate_snapshots?: Array<Record<string, unknown>>;
  release_history?: { actions?: Array<Record<string, unknown>>; snapshots?: Array<Record<string, unknown>> };
  available_actions?: Record<string, { enabled?: boolean; params?: Record<string, unknown> }>;
}

export function fetchReleaseOperatorSurface(productKey = '') {
  return intent<ReleaseOperatorSurface>('release.operator.surface', { product_key: productKey, action_limit: 20 });
}

export function executeReleaseOperatorAction(
  name:
    | 'release.operator.promote'
    | 'release.operator.approve'
    | 'release.operator.freeze'
    | 'release.operator.sync_policy'
    | 'release.operator.update_policy'
    | 'release.operator.update_page_policy'
    | 'release.operator.rollback',
  params: Record<string, unknown>,
) {
  return intent<{ surface?: ReleaseOperatorSurface }>(name, params);
}

export interface StarterRouteItem {
  path: string;
  name: string;
  component?: string;
  redirect?: string;
  meta: Record<string, unknown>;
  children?: StarterRouteItem[];
}

export function navigationToRoutes(nodes: NavNode[], parent = ''): StarterRouteItem[] {
  const flattenedRoot = !parent ? nodes.find((node) => isSystemMenuRoot(node)) : undefined;
  if (flattenedRoot) {
    const rootIndex = nodes.indexOf(flattenedRoot);
    const rootSegment = routeSegment(
      String(
        flattenedRoot.key ||
          flattenedRoot.meta?.menu_xmlid ||
          flattenedRoot.menu_id ||
          flattenedRoot.id ||
          'system_menu',
      ),
      rootIndex,
    );
    return nodes.flatMap((node, index) => {
      if (node !== flattenedRoot) return [buildRoute(node, index, '', true)];
      return (node.children || []).map((child, childIndex) => buildRoute(child, childIndex, `/${rootSegment}`, true));
    });
  }

  return nodes.map((node, index) => buildRoute(node, index, parent, !parent));

  function buildRoute(node: NavNode, index: number, routeParent: string, topLevel: boolean): StarterRouteItem {
    const key = String(node.key || node.meta?.menu_xmlid || node.menu_id || node.id || index);
    const menuId = Number(node.menu_id || node.id || node.meta?.menu_id || 0) || undefined;
    const segment = routeSegment(key, index, menuId);
    const label = String(node.label || node.title || node.name || '未命名入口');
    const childParent = routeParent ? `${routeParent}/${segment}` : `/${segment}`;
    const children = node.children?.length ? navigationToRoutes(node.children, childParent) : [];
    const routePath = topLevel ? (routeParent ? `${routeParent}/${segment}` : `/${segment}`) : segment;
    const meta = {
      title: { zh_CN: label, en_US: label },
      icon: String(node.meta?.icon || (children.length ? 'folder-open-1' : 'file')),
      menuKey: key,
      menuId,
      actionId: Number(node.action_id || node.meta?.action_id || 0) || undefined,
      model: String(node.model || node.meta?.model || ''),
      action: node,
      sceneKey: String(node.scene_key || node.entry_target?.scene_key || node.meta?.scene_key || ''),
      entryTarget: node.entry_target,
    };
    const sceneTarget =
      node.entry_target &&
      typeof node.entry_target === 'object' &&
      String(node.entry_target.type || '').toLowerCase() === 'scene';
    if (sceneTarget && !children.length) {
      if (topLevel) {
        return {
          path: routePath,
          name: `OdooScene_${safeName(key)}_${index}`,
          component: 'LAYOUT',
          meta: { ...meta, sceneKey: String(node.entry_target?.scene_key || node.scene_key || key), single: true },
          children: [
            {
              path: '',
              name: `OdooScenePage_${safeName(key)}_${index}`,
              component: '/SceneRuntimeView.vue',
              meta: { ...meta, sceneKey: String(node.entry_target?.scene_key || node.scene_key || key) },
            },
          ],
        };
      }
      return {
        path: routePath,
        name: `OdooScene_${safeName(key)}_${index}`,
        component: topLevel ? 'LAYOUT' : '/SceneRuntimeView.vue',
        meta: { ...meta, sceneKey: String(node.entry_target?.scene_key || node.scene_key || key) },
      };
    }
    // Only the top-level dynamic route owns the application shell. Nested menu
    // groups are router-view parents; wrapping each one in LAYOUT duplicates
    // the sidebar and header for deeply nested Odoo menus.
    if (children.length) {
      return {
        path: routePath,
        name: `OdooMenu_${safeName(key)}_${index}`,
        component: topLevel ? 'LAYOUT' : 'BLANK',
        redirect: `${routePath}/${children[0].path}`.replace('//', '/'),
        meta,
        children,
      };
    }
    if (topLevel) {
      // A top-level action owns the application shell, but remains one menu
      // entry instead of rendering an empty wrapper plus a duplicate child.
      return {
        path: routePath,
        name: `OdooAction_${safeName(key)}_${index}`,
        component: 'LAYOUT',
        meta: { ...meta, single: true },
        children: [
          {
            path: '',
            name: `OdooActionPage_${safeName(key)}_${index}`,
            component: '/odoo/action/index.vue',
            meta,
          },
        ],
      };
    }
    return { path: routePath, name: `OdooAction_${safeName(key)}_${index}`, component: '/odoo/action/index.vue', meta };
  }
}

function isSystemMenuRoot(node: NavNode) {
  const key = String(node.key || node.meta?.menu_xmlid || '').toLowerCase();
  const label = String(node.label || node.title || node.name || '').trim();
  return (
    label === '系统菜单' || key === 'root-system_menu' || key.endsWith('.system_menu') || key.endsWith('_system_menu')
  );
}

function routeSegment(value: string, index: number, stableId?: number) {
  const raw = value
    .toLowerCase()
    .replace(/[^a-z0-9_-]+/g, '-')
    .replace(/^-+|-+$/g, '');
  const fallback = raw || String(index);
  const suffix = stableId && !new RegExp(`(?:^|[-_])${stableId}$`).test(fallback) ? `-${stableId}` : '';
  return `m-${fallback}${suffix}`;
}

function safeName(value: string) {
  return value.replace(/\W/g, '_').slice(0, 60) || 'item';
}
