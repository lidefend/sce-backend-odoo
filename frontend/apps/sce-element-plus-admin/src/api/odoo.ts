import axios, { type AxiosRequestConfig } from "axios";

import type {
  Dictionary,
  ListDataResult,
  MyWorkSummary,
  OdooUser,
  SystemInit,
} from "@/types/contracts";

const database = String(import.meta.env.VITE_ODOO_DB || "sc_dev_demo").trim();
const tenant = String(import.meta.env.VITE_TENANT || "default").trim();
const http = axios.create({
  baseURL: String(import.meta.env.VITE_API_BASE_URL || ""),
  timeout: 30_000,
});
const cache = new Map<string, { data: unknown; etag: string }>();
const cacheable = new Set([
  "system.init",
  "ui.contract",
  "ui.contract.v2",
  "meta.intent_catalog",
]);

export class OdooApiError extends Error {
  code: string;
  reasonCode: string;
  status: number;
  traceId: string;
  retryable: boolean;
  suggestedAction: string;
  details: Dictionary;

  constructor(message: string, options: Partial<OdooApiError> = {}) {
    super(message);
    this.name = "OdooApiError";
    this.code = options.code || "BUSINESS_REQUEST_FAILED";
    this.reasonCode = options.reasonCode || this.code;
    this.status = options.status || 0;
    this.traceId = options.traceId || "";
    this.retryable = options.retryable === true;
    this.suggestedAction = options.suggestedAction || "";
    this.details = options.details || {};
  }
}

function stableJson(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(stableJson).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.entries(value as Dictionary)
      .filter(([, item]) => item !== undefined)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([key, item]) => `${JSON.stringify(key)}:${stableJson(item)}`)
      .join(",")}}`;
  }
  return JSON.stringify(value) ?? "null";
}

function getToken() {
  return localStorage.getItem("sce-element-token") || "";
}

function businessContext(): Dictionary {
  try {
    return JSON.parse(
      localStorage.getItem("sce-element-business-context") || "{}",
    ) as Dictionary;
  } catch {
    return {};
  }
}

function requestContextFromBusinessContext(value: Dictionary): Dictionary {
  const nested = value.request_context ?? value.requestContext;
  const nestedContext = nested && typeof nested === "object" && !Array.isArray(nested)
    ? nested as Dictionary
    : {};
  const flatContext = Object.fromEntries(
    Object.entries(value).filter(([key]) => !["request_context", "requestContext"].includes(key)),
  );
  return { ...flatContext, ...nestedContext };
}

export function clearToken() {
  localStorage.removeItem("sce-element-token");
  cache.clear();
}

function redirectToFrontendLogin() {
  if (typeof window === "undefined" || window.location.pathname === "/login") return;
  const redirect = `${window.location.pathname}${window.location.search}${window.location.hash}`;
  window.location.replace(`/login?redirect=${encodeURIComponent(redirect)}`);
}

export async function intent<T>(
  name: string,
  params: Dictionary = {},
  options: AxiosRequestConfig = {},
  envelope: { context?: Dictionary; meta?: Dictionary } = {},
): Promise<T> {
  const traceId = crypto.randomUUID?.() || `trace-${Date.now()}`;
  const storedBusinessContext = businessContext();
  const requestParams = { ...storedBusinessContext, ...params };
  delete requestParams.request_context;
  delete requestParams.requestContext;
  const contextFreeIntents = new Set([
    "login",
    "auth.login",
    "auth.logout",
    "session.bootstrap",
    "sys.intents",
    "record.context.search",
  ]);
  const requestContext = requestContextFromBusinessContext(storedBusinessContext);
  const explicitParamContext = requestParams.context && typeof requestParams.context === "object" && !Array.isArray(requestParams.context)
    ? requestParams.context as Dictionary
    : {};
  const explicitEnvelopeContext = envelope.context && typeof envelope.context === "object" && !Array.isArray(envelope.context)
    ? envelope.context
    : {};
  const effectiveContext = !contextFreeIntents.has(name) && Object.keys(requestContext).length
    ? { ...requestContext, ...explicitParamContext }
    : explicitParamContext;
  if (Object.keys(effectiveContext).length) requestParams.context = effectiveContext;
  const key = `${name}:${stableJson(requestParams)}`;
  const cached = cacheable.has(name) ? cache.get(key) : undefined;
  const headers: Dictionary = {
    "Content-Type": "application/json",
    "X-Odoo-DB": database,
    "X-Tenant": tenant,
    "X-Trace-Id": traceId,
    ...(options.headers || {}),
  };
  if (cached?.etag) headers["If-None-Match"] = cached.etag;
  if (!["login", "auth.login"].includes(name) && getToken())
    headers.Authorization = `Bearer ${getToken()}`;

  try {
    const response = await http.post(
      `/api/v1/intent?db=${encodeURIComponent(database)}`,
      {
        intent: name,
        params: requestParams,
        ...(Object.keys(effectiveContext).length ? { context: { ...effectiveContext, ...explicitEnvelopeContext } } : envelope.context ? { context: envelope.context } : {}),
        ...(envelope.meta ? { meta: envelope.meta } : {}),
      },
      {
        ...options,
        headers,
        validateStatus: (status) =>
          (status >= 200 && status < 300) || status === 304,
      },
    );
    if (response.status === 304 && cached) return cached.data as T;
    const body = response.data as Dictionary;
    if (body?.ok === false || body?.error) {
      const error = (body.error || {}) as Dictionary;
      const meta = (body.meta || {}) as Dictionary;
      throw new OdooApiError(String(error.message || "业务请求失败"), {
        code: String(error.code || "BUSINESS_REQUEST_FAILED"),
        reasonCode: String(
          error.reason_code || meta.reason_code || error.code || "",
        ),
        status: response.status,
        traceId: String(meta.trace_id || traceId),
        retryable: error.retryable === true,
        suggestedAction: String(
          error.suggested_action || meta.suggested_action || "",
        ),
        details: (error.details || {}) as Dictionary,
      });
    }
    const data = (body?.data ?? body) as T;
    const etag = String(response.headers.etag || "");
    if (cacheable.has(name) && etag) cache.set(key, { data, etag });
    if (
      /create|write|unlink|batch|execute|save|publish|rollback|complete/.test(
        name,
      )
    )
      cache.clear();
    return data;
  } catch (cause) {
    if (cause instanceof OdooApiError) throw cause;
    if (axios.isAxiosError(cause)) {
      const body = (cause.response?.data || {}) as Dictionary;
      const error = (body.error || {}) as Dictionary;
      const meta = (body.meta || {}) as Dictionary;
      const status = Number(cause.response?.status || 0);
      if (status === 401) {
        clearToken();
        redirectToFrontendLogin();
      }
      throw new OdooApiError(
        String(error.message || cause.message || "网络请求失败"),
        {
          code: String(
            error.code || (status ? `HTTP_${status}` : "NETWORK_ERROR"),
          ),
          reasonCode: String(error.reason_code || meta.reason_code || ""),
          status,
          traceId: String(meta.trace_id || traceId),
          retryable:
            error.retryable === true || status === 429 || status >= 500,
          suggestedAction: String(
            error.suggested_action || meta.suggested_action || "",
          ),
          details: (error.details || {}) as Dictionary,
        },
      );
    }
    throw cause;
  }
}

export async function login(loginName: string, password: string) {
  const result = await intent<{
    token?: string;
    session?: { token?: string };
    user?: OdooUser;
  }>(
    "login",
    { login: loginName, password, contract_mode: "default", db: database },
    { headers: { "X-Anonymous-Intent": "1" } },
  );
  const token = String(result.session?.token || result.token || "");
  if (!token) throw new Error("登录响应没有 token");
  localStorage.setItem("sce-element-token", token);
  return { token, user: result.user };
}

export async function logout() {
  try {
    if (getToken()) await intent("auth.logout");
  } finally {
    clearToken();
  }
}

export function systemInit(context: Dictionary = {}) {
  return intent<SystemInit>("system.init", {
    scene: "web",
    with_preload: false,
    scene_ready_mode: "registry",
    with: ["workspace_home"],
    ...context,
  });
}

export function searchRecordContext(params: Dictionary = {}) {
  return intent<Dictionary>("record.context.search", params);
}

export function loadPageContract(params: {
  model?: string;
  actionId?: number;
  menuId?: number;
  recordId?: number;
  sceneKey?: string;
  renderProfile?: string;
  source?: "model" | "action";
}) {
  const wizardModel = /(^|\.)wizard$/i.test(String(params.model || "").trim());
  const actionSource = params.source === "action" || wizardModel;
  return intent<Dictionary>("ui.contract.v2", {
    op: actionSource
      ? "action_open"
      : params.recordId ||
      params.renderProfile === "create" ||
      params.renderProfile === "edit" ||
      params.renderProfile === "readonly"
        ? "model"
        : undefined,
    model: params.model,
    view_type: params.renderProfile ? "form" : undefined,
    action_id: params.actionId,
    menu_id: params.menuId,
    record_id: params.recordId,
    scene_key: params.sceneKey,
    render_profile:
      params.renderProfile || (params.recordId ? "readonly" : actionSource ? "create" : "list"),
    contract_version: "2.0.0",
    accepted_contract_versions: ["2.0.x", "2.1.x", "2.2.x"],
    client_contract_capabilities: [
      "container_tree.v2",
      "data_source.v2",
      "action_rule.v2",
      "relation_entry.v2",
      "status_contract.v2",
      "form_layout.children_owner.v1",
    ],
    client_type: "web_pc",
    delivery_profile: "full",
  });
}

export function listData(params: {
  model: string;
  fields: string[];
  domain?: unknown[];
  order?: string;
  limit?: number;
  offset?: number;
  searchTerm?: string;
  context?: Dictionary;
  groupBy?: string;
  groupOffset?: number;
  groupLimit?: number;
  groupPageSize?: number;
  groupPageOffsets?: Record<string, number>;
  needAggregates?: boolean;
}) {
  return intent<ListDataResult>("api.data", {
    op: "list",
    model: params.model,
    fields: params.fields,
    domain: params.domain || [],
    order: params.order || "",
    limit: params.limit || 20,
    offset: params.offset || 0,
    search_term: params.searchTerm || "",
    context: params.context || {},
    group_by: params.groupBy || undefined,
    group_offset: params.groupOffset || 0,
    group_limit: params.groupLimit || 20,
    group_page_size: params.groupPageSize || 5,
    group_page_offsets: params.groupPageOffsets || {},
    need_group_total: Boolean(params.groupBy),
    need_aggregates: params.needAggregates === true,
    need_total: true,
  });
}

export function readRecord(
  model: string,
  id: number,
  fields: string[],
  context: Dictionary = {},
) {
  return intent<{ records?: Dictionary[]; rows?: Dictionary[] }>("api.data", {
    op: "read",
    model,
    ids: [id],
    fields,
    context,
  });
}

export function createRecord(
  model: string,
  values: Dictionary,
  context: Dictionary = {},
) {
  const requestId = `create-${crypto.randomUUID?.() || Date.now()}`;
  return intent<{ id?: number }>("api.data", {
    op: "create",
    model,
    vals: values,
    context,
    request_id: requestId,
    idempotency_key: requestId,
  });
}

export function updateRecord(
  model: string,
  id: number,
  values: Dictionary,
  context: Dictionary = {},
  ifMatch = "",
) {
  const requestId = `write-${crypto.randomUUID?.() || Date.now()}`;
  return intent<{ id?: number }>("api.data", {
    op: "write",
    model,
    id,
    ids: [id],
    vals: values,
    context,
    if_match: ifMatch || undefined,
    request_id: requestId,
    idempotency_key: requestId,
  });
}

export function deleteRecords(
  model: string,
  ids: number[],
  context: Dictionary = {},
) {
  return intent("api.data.unlink", { model, ids, context });
}

export function relationOptions(params: {
  model: string;
  search?: string;
  domain?: unknown[];
  limit?: number;
  fields?: string[];
  order?: string;
  context?: Dictionary;
}) {
  return intent<{ records?: Dictionary[]; rows?: Dictionary[] }>("api.data", {
    op: "list",
    model: params.model,
    fields: params.fields || ["id", "display_name", "name"],
    search_term: params.search || "",
    domain: params.domain || [],
    limit: params.limit || 30,
    order: params.order || "",
    context: params.context || {},
  });
}

export function triggerOnchange(params: {
  model: string;
  values: Dictionary;
  fieldName: string;
  recordId?: number;
}) {
  return intent<{
    patch?: Dictionary;
    values?: Dictionary;
    value?: Dictionary;
    modifiers_patch?: Record<string, Dictionary>;
    warnings?: Array<{ title?: string; message?: string }>;
    line_patches?: Dictionary[];
  }>("api.onchange", {
    model: params.model,
    values: params.values,
    changed_fields: [params.fieldName],
    field_name: params.fieldName,
    res_id: params.recordId,
    record_id: params.recordId,
  });
}

export function batchUpdateRecords(params: {
  model: string;
  ids: number[];
  action: string;
  vals?: Dictionary;
  assigneeId?: number;
  reason?: string;
}) {
  return intent<Dictionary>("api.data.batch", {
    model: params.model,
    ids: params.ids,
    action: params.action,
    vals: params.vals || {},
    assignee_id: params.assigneeId,
    reason: params.reason,
  });
}
export function saveSearchFavorite(params: {
  model: string;
  name: string;
  domain: unknown[];
  actionId?: number;
  isDefault?: boolean;
}) {
  return intent<Dictionary>("search.favorite.set", {
    model: params.model,
    name: params.name,
    domain: params.domain,
    action_id: params.actionId,
    is_default: params.isDefault === true,
  });
}
export function getUserViewPreference(params: {
  model: string;
  actionId?: number;
  preferenceKey?: string;
}) {
  return intent<{ preference?: Dictionary }>("user.view.preference.get", {
    model: params.model,
    action_id: params.actionId,
    view_type: "list",
    preference_key: params.preferenceKey || "list_columns",
  });
}
export function setUserViewPreference(params: {
  model: string;
  actionId?: number;
  preferenceKey?: string;
  preference: Dictionary;
}) {
  return intent<{ preference?: Dictionary }>("user.view.preference.set", {
    model: params.model,
    action_id: params.actionId,
    view_type: "list",
    preference_key: params.preferenceKey || "list_columns",
    preference: params.preference,
  });
}

export function executeButton(params: {
  model: string;
  recordId: number;
  button: Dictionary;
  values?: Dictionary;
  context?: Dictionary;
  meta?: Dictionary;
}) {
  return intent<Dictionary>("execute_button", {
    model: params.model,
    record_id: params.recordId,
    ids: [params.recordId],
    button: params.button,
    values: params.values || {},
  }, {}, { context: params.context || {}, meta: params.meta || {} });
}

export function uploadFile(params: {
  model: string;
  recordId: number;
  name: string;
  mimetype: string;
  data: string;
}) {
  return intent<Dictionary>("file.upload", {
    model: params.model,
    res_id: params.recordId,
    name: params.name,
    mimetype: params.mimetype,
    data: params.data,
  });
}
export function downloadFile(attachmentId: number) {
  return intent<{ content_b64?: string; filename?: string; mimetype?: string }>(
    "file.download",
    { attachment_id: attachmentId },
  );
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
export function fetchChatterTimeline(
  model: string,
  recordId: number,
  offset = 0,
) {
  return intent<{
    items?: ChatterTimelineEntry[];
    counts?: Dictionary;
    paging?: Dictionary;
  }>("chatter.timeline", {
    model,
    res_id: recordId,
    limit: 40,
    offset,
    include_audit: true,
  });
}
export function postChatterMessage(params: {
  model: string;
  recordId: number;
  body: string;
  mode: "message" | "note";
  mentionUserIds?: number[];
}) {
  return intent<Dictionary>("chatter.post", {
    model: params.model,
    res_id: params.recordId,
    body: params.body,
    mode: params.mode,
    mention_user_ids: params.mentionUserIds || [],
  });
}
export function scheduleChatterActivity(params: {
  model: string;
  recordId: number;
  summary: string;
  dateDeadline?: string;
  note?: string;
  userId?: number;
}) {
  return intent<Dictionary>("chatter.activity.schedule", {
    model: params.model,
    res_id: params.recordId,
    summary: params.summary,
    date_deadline: params.dateDeadline,
    note: params.note,
    user_id: params.userId,
  });
}
export function updateChatterActivity(params: {
  model: string;
  recordId: number;
  activityId: number;
  action: "done" | "cancel";
  note?: string;
}) {
  return intent<Dictionary>("chatter.activity.update", {
    model: params.model,
    res_id: params.recordId,
    activity_id: params.activityId,
    action: params.action,
    note: params.note,
  });
}
export function searchCollaborationUsers(query = "", limit = 20) {
  return intent<{ items?: Dictionary[] }>("collaboration.users.search", {
    query,
    limit,
  });
}
export async function listRecordFollowers(model: string, recordId: number) {
  const result = await listData({
    model: "mail.followers",
    fields: ["id", "partner_id"],
    domain: [
      ["res_model", "=", model],
      ["res_id", "=", recordId],
    ],
    limit: 100,
  });
  return result.records || result.rows || [];
}
export function addRecordFollower(
  model: string,
  recordId: number,
  partnerId: number,
) {
  return createRecord("mail.followers", {
    res_model: model,
    res_id: recordId,
    partner_id: partnerId,
  });
}
export function removeRecordFollower(followerId: number) {
  return deleteRecords("mail.followers", [followerId]);
}

export function exportCsv(params: {
  model: string;
  fields: string[];
  domain?: unknown[];
  ids?: number[];
}) {
  return intent<{ content?: string; csv?: string; filename?: string }>(
    "api.data.export_csv",
    params,
  );
}

export function fetchMyWorkSummary(params: Dictionary = {}) {
  return intent<MyWorkSummary>("my.work.summary", params);
}

export function completeMyWorkItem(id: number) {
  return intent<Dictionary>("my.work.complete", { id });
}

export function completeMyWorkItems(ids: number[]) {
  return intent<Dictionary>("my.work.complete.batch", { ids });
}

export function listNotifications(limit = 30) {
  return listData({
    model: "mail.notification",
    fields: [
      "id",
      "is_read",
      "sc_subject",
      "sc_body",
      "sc_message_date",
      "sc_record_name",
      "sc_source_model",
      "sc_source_res_id",
      "author_id",
      "read_date",
    ],
    domain: [
      ["sc_is_current_recipient", "=", true],
      ["notification_type", "=", "inbox"],
    ],
    order: "sc_message_date desc, id desc",
    limit,
  });
}

export function setNotificationRead(notificationId: number, read: boolean) {
  return executeButton({
    model: "mail.notification",
    recordId: notificationId,
    button: {
      name: read ? "action_sc_mark_read" : "action_sc_mark_unread",
      type: "object",
    },
  });
}

export function validateRouteAuthority(params: Dictionary) {
  return intent<{ allowed?: boolean }>("route.authority.validate", params);
}

export function fetchIntentCatalog() {
  return intent<{ intents?: string[]; intent_catalog?: Dictionary[] }>(
    "meta.intent_catalog",
  );
}

export function hasToken() {
  return Boolean(getToken());
}
