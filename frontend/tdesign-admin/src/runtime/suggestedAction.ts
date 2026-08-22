export type SuggestedActionKind =
  | 'refresh'
  | 'retry'
  | 'go_back'
  | 'relogin'
  | 'open_login'
  | 'open_home'
  | 'open_dashboard'
  | 'open_my_work'
  | 'open_scene'
  | 'open_menu'
  | 'open_action'
  | 'open_record'
  | 'open_route'
  | 'open_url'
  | 'copy_trace'
  | 'copy_reason'
  | 'copy_message'
  | '';

export interface SuggestedAction {
  kind: SuggestedActionKind;
  raw: string;
  value?: string;
  model?: string;
  recordId?: number;
  sceneKey?: string;
  menuId?: number;
  actionId?: number;
  url?: string;
}

const aliases: Record<string, SuggestedActionKind> = {
  refresh: 'refresh',
  refresh_list: 'refresh',
  retry: 'retry',
  retry_later: 'retry',
  back: 'go_back',
  go_back: 'go_back',
  relogin: 'relogin',
  login_again: 'relogin',
  open_login: 'open_login',
  go_login: 'open_login',
  open_home: 'open_home',
  go_home: 'open_home',
  open_dashboard: 'open_dashboard',
  open_my_work: 'open_my_work',
  open_scene: 'open_scene',
  open_menu: 'open_menu',
  open_action: 'open_action',
  open_record: 'open_record',
  open_route: 'open_route',
  open_url: 'open_url',
  copy_trace: 'copy_trace',
  copy_trace_id: 'copy_trace',
  copy_reason: 'copy_reason',
  copy_reason_code: 'copy_reason',
  copy_message: 'copy_message',
  copy_error_message: 'copy_message',
};

function safePath(value: string) {
  if (!value.startsWith('/') || value.startsWith('//')) return false;
  try {
    const decoded = decodeURIComponent(value).toLowerCase();
    return !decoded.includes('javascript:') && !decoded.startsWith('//');
  } catch {
    return false;
  }
}

export function parseSuggestedAction(value: unknown): SuggestedAction {
  const raw = typeof value === 'string' ? value.trim() : '';
  const normalized = raw.toLowerCase();
  if (!normalized) return { kind: '', raw: '' };
  if (aliases[normalized]) return { kind: aliases[normalized], raw };
  let match = normalized.match(/^(?:open_record|go_record):([^:]+):(\d+)$/);
  if (match) return { kind: 'open_record', raw, model: match[1], recordId: Number(match[2]) };
  match = normalized.match(/^(?:open_scene|goto_scene):(.+)$/);
  if (match) return { kind: 'open_scene', raw, sceneKey: match[1] };
  match = normalized.match(/^(?:open_menu|goto_menu):(\d+)$/);
  if (match) return { kind: 'open_menu', raw, menuId: Number(match[1]) };
  match = normalized.match(/^(?:open_action|goto_action):(\d+)$/);
  if (match) return { kind: 'open_action', raw, actionId: Number(match[1]) };
  const pathMatch = raw.match(/^(?:open_route|open_url):(.+)$/i);
  if (pathMatch && safePath(pathMatch[1].trim())) {
    const kind = normalized.startsWith('open_url:') ? 'open_url' : 'open_route';
    return { kind, raw, url: pathMatch[1].trim() };
  }
  return { kind: '', raw };
}

export function suggestedActionLabel(action: SuggestedAction) {
  const labels: Partial<Record<SuggestedActionKind, string>> = {
    refresh: '刷新重试',
    retry: '重新执行',
    go_back: '返回上一页',
    relogin: '重新登录',
    open_login: '打开登录页',
    open_home: '返回首页',
    open_dashboard: '打开工作台',
    open_my_work: '打开我的工作',
    open_scene: '打开相关场景',
    open_menu: '打开相关菜单',
    open_action: '打开相关动作',
    open_record: '打开相关记录',
    open_route: '打开相关页面',
    open_url: '打开链接',
    copy_trace: '复制 Trace ID',
    copy_reason: '复制原因码',
    copy_message: '复制错误信息',
  };
  return labels[action.kind] || '执行建议操作';
}

export function canExecuteSuggestedAction(action: SuggestedAction) {
  return Boolean(
    action.kind &&
    (action.kind === 'refresh' ||
      action.kind === 'retry' ||
      action.kind === 'go_back' ||
      action.kind === 'relogin' ||
      action.kind === 'open_login' ||
      action.kind === 'open_home' ||
      action.kind === 'open_dashboard' ||
      action.kind === 'open_my_work' ||
      action.kind === 'open_scene' ||
      Boolean(action.menuId) ||
      Boolean(action.actionId) ||
      Boolean(action.recordId && action.model) ||
      Boolean(action.url) ||
      action.kind.startsWith('copy_')),
  );
}

async function copyText(value: string) {
  if (!value) return false;
  try {
    await navigator.clipboard.writeText(value);
    return true;
  } catch {
    return false;
  }
}

export async function executeSuggestedAction(
  action: SuggestedAction,
  options: { onRetry?: () => void; traceId?: string; reasonCode?: string; message?: string } = {},
) {
  if (!canExecuteSuggestedAction(action)) return false;
  if (action.kind === 'refresh' || action.kind === 'retry') {
    options.onRetry?.();
    return true;
  }
  if (action.kind === 'go_back') {
    window.history.back();
    return true;
  }
  if (action.kind === 'relogin') {
    window.location.assign(
      `/login?redirect=${encodeURIComponent(`${window.location.pathname}${window.location.search}`)}`,
    );
    return true;
  }
  if (action.kind === 'open_login') return Boolean(window.location.assign('/login'));
  const paths: Partial<Record<SuggestedActionKind, string>> = {
    open_home: '/',
    open_dashboard: '/dashboard/base',
    open_my_work: '/my-work',
    open_scene: action.sceneKey ? `/s/${encodeURIComponent(action.sceneKey)}` : undefined,
    open_menu: action.menuId ? `/m/${action.menuId}` : undefined,
    open_action: action.actionId ? `/a/${action.actionId}` : undefined,
    open_record:
      action.model && action.recordId ? `/r/${encodeURIComponent(action.model)}/${action.recordId}` : undefined,
    open_route: action.url,
    open_url: action.url,
  };
  if (paths[action.kind]) {
    window.location.assign(paths[action.kind] as string);
    return true;
  }
  if (action.kind === 'copy_trace') return copyText(options.traceId || '');
  if (action.kind === 'copy_reason') return copyText(options.reasonCode || '');
  if (action.kind === 'copy_message') return copyText(options.message || '');
  return false;
}
