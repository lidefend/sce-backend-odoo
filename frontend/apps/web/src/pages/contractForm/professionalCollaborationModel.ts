import type { ChatterTimelineEntry } from '../../api/chatter';
import type { NativeChatterAction } from './types';

export type ProfessionalCollaborationCapability = 'comment' | 'attachment' | 'activity' | 'follower';
export type ProfessionalCollaborationReadiness = 'ready' | 'fail_closed';

export function collaborationCapabilityReadiness(input: {
  hasCommentAction: boolean;
  hasAttachmentAuthority: boolean;
  hasActivityAction: boolean;
  hasFollowerAuthority: boolean;
}): Readonly<Record<ProfessionalCollaborationCapability, ProfessionalCollaborationReadiness>> {
  return Object.freeze({
    comment: input.hasCommentAction ? 'ready' : 'fail_closed',
    attachment: input.hasAttachmentAuthority ? 'ready' : 'fail_closed',
    activity: input.hasActivityAction ? 'ready' : 'fail_closed',
    follower: input.hasFollowerAuthority ? 'ready' : 'fail_closed',
  });
}

export function visibleCollaborationTimeline(entries: readonly ChatterTimelineEntry[]): ChatterTimelineEntry[] {
  return entries.filter((entry) => entry.type !== 'audit');
}

export function canDownloadCollaborationAttachment(entry: ChatterTimelineEntry): boolean {
  return entry.type === 'attachment'
    && entry.attachment?.can_download === true
    && entry.attachment.download_intent === 'file.download';
}

export function canDeleteCollaborationAttachment(entry: ChatterTimelineEntry): boolean {
  return entry.type === 'attachment'
    && entry.attachment?.can_delete === true
    && entry.attachment.delete_intent === 'chatter.attachment.delete'
    && Number(entry.attachment.id || entry.id || 0) > 0;
}

export function canUpdateCollaborationActivity(
  entry: ChatterTimelineEntry,
  action: 'done' | 'cancel',
): boolean {
  if (entry.type !== 'activity'
    || entry.activity?.update_intent !== 'chatter.activity.update'
    || Number(entry.activity.id || entry.id || 0) <= 0) return false;
  return action === 'done'
    ? entry.activity?.can_complete === true
    : entry.activity?.can_cancel === true;
}

export function canReplyCollaborationMessage(entry: ChatterTimelineEntry): boolean {
  return entry.type === 'message'
    && entry.message?.can_reply === true
    && entry.message.reply_intent === 'chatter.post'
    && Number(entry.message.id || entry.id || 0) > 0;
}

export function canDeleteCollaborationMessage(entry: ChatterTimelineEntry): boolean {
  return entry.type === 'message'
    && entry.message?.can_delete === true
    && entry.message.delete_intent === 'chatter.message.delete'
    && Number(entry.message.id || entry.id || 0) > 0;
}

export function canExecuteCollaborationCreateAction(
  action: NativeChatterAction | null | undefined,
  mode: string,
): boolean {
  const expectedIntent = mode === 'activity'
    ? 'chatter.activity.schedule'
    : mode === 'message' || mode === 'note'
      ? 'chatter.post'
      : '';
  return Boolean(
    action?.enabled === true
    && expectedIntent
    && action.mode === mode
    && action.payload?.execute_intent === expectedIntent
  );
}

export function formatCollaborationTimelineMeta(value: string): string {
  return String(value || '').replace(
    /\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?/g,
    (raw) => {
      const parsed = new Date(raw);
      if (Number.isNaN(parsed.getTime())) return raw;
      return new Intl.DateTimeFormat('zh-CN', {
        year: 'numeric', month: '2-digit', day: '2-digit',
        hour: '2-digit', minute: '2-digit', hour12: false,
      }).format(parsed);
    },
  );
}

// 文件大小格式化
export function formatFileSize(bytes: number): string {
  if (!bytes || bytes <= 0) return '0 B';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// 文件类型友好显示
const MIMETYPE_LABELS: Record<string, string> = {
  'text/plain': '文本文件',
  'text/csv': 'CSV 表格',
  'text/html': 'HTML 页面',
  'application/pdf': 'PDF 文档',
  'application/msword': 'Word 文档',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'Word 文档',
  'application/vnd.ms-excel': 'Excel 表格',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'Excel 表格',
  'application/vnd.ms-powerpoint': 'PPT 演示',
  'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'PPT 演示',
  'application/json': 'JSON 数据',
  'application/xml': 'XML 数据',
  'application/zip': 'ZIP 压缩包',
  'application/x-rar-compressed': 'RAR 压缩包',
  'application/x-tar': 'TAR 归档',
  'application/gzip': 'GZIP 压缩',
  'image/png': 'PNG 图片',
  'image/jpeg': 'JPEG 图片',
  'image/gif': 'GIF 图片',
  'image/svg+xml': 'SVG 矢量图',
  'image/webp': 'WebP 图片',
  'audio/mpeg': 'MP3 音频',
  'audio/wav': 'WAV 音频',
  'video/mp4': 'MP4 视频',
  'video/webm': 'WebM 视频',
};

export function formatMimeType(mimetype?: string): string {
  if (!mimetype) return '文件';
  return MIMETYPE_LABELS[mimetype] || mimetype.split('/')[1]?.toUpperCase() || '文件';
}

// 文件类型图标（使用 emoji 作为简单图标）
const MIMETYPE_ICONS: Record<string, string> = {
  'text/plain': '📄',
  'text/csv': '📊',
  'application/pdf': '📕',
  'application/msword': '📘',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '📘',
  'application/vnd.ms-excel': '📗',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '📗',
  'application/vnd.ms-powerpoint': '📙',
  'application/vnd.openxmlformats-officedocument.presentationml.presentation': '📙',
  'application/zip': '🗜️',
  'application/x-rar-compressed': '🗜️',
  'image/png': '🖼️',
  'image/jpeg': '🖼️',
  'image/gif': '🖼️',
  'audio/mpeg': '🎵',
  'video/mp4': '🎬',
};

export function getFileIcon(mimetype?: string): string {
  if (!mimetype) return '📎';
  return MIMETYPE_ICONS[mimetype] || '📎';
}

// 解析附件条目信息（从 body/title 中提取文件名、类型、大小）
export interface ParsedAttachmentInfo {
  name: string;
  mimetype?: string;
  size?: number;
  sizeLabel?: string;
  typeLabel?: string;
  icon?: string;
}

export function parseAttachmentEntry(entry: ChatterTimelineEntry): ParsedAttachmentInfo {
  const attachment = entry.attachment;
  const name = attachment?.name || entry.title || entry.body || '未命名文件';

  // 尝试从 body 中解析 mimetype 和大小（格式："filename mimetype · size"）
  let mimetype = attachment?.mimetype;
  let size: number | undefined;

  if (!mimetype || !size) {
    const bodyText = entry.body || '';
    const mimetypeMatch = bodyText.match(/([a-z]+\/[a-z0-9.+-]+)/i);
    if (mimetypeMatch && !mimetype) {
      mimetype = mimetypeMatch[1];
    }
    const sizeMatch = bodyText.match(/·\s*(\d+)\s*$/);
    if (sizeMatch) {
      size = parseInt(sizeMatch[1], 10);
    }
  }

  return {
    name,
    mimetype,
    size,
    sizeLabel: size !== undefined ? formatFileSize(size) : undefined,
    typeLabel: formatMimeType(mimetype),
    icon: getFileIcon(mimetype),
  };
}

// 消息条目解析
export interface ParsedMessageInfo {
  author: string;
  body: string;
  at?: string;
  atLabel?: string;
  icon: string;
}

export function parseMessageEntry(entry: ChatterTimelineEntry): ParsedMessageInfo {
  const body = entry.body || entry.title || '';
  // 尝试从 body 中解析发送者（格式："作者 · 内容" 或 "作者: 内容"）
  let author = entry.typeLabel || '消息';
  let content = body;

  const authorMatch = body.match(/^([^·:：]{1,20})[·:：]\s*(.+)$/);
  if (authorMatch) {
    author = authorMatch[1].trim();
    content = authorMatch[2].trim();
  }

  return {
    author,
    body: content,
    at: entry.at,
    atLabel: entry.at ? formatCollaborationTimelineMeta(entry.at) : undefined,
    icon: '💬',
  };
}

// 活动条目解析
export interface ParsedActivityInfo {
  title: string;
  assignee?: string;
  deadline?: string;
  deadlineLabel?: string;
  activityType?: string;
  canComplete: boolean;
  canCancel: boolean;
  at?: string;
  atLabel?: string;
  icon: string;
  status: 'pending' | 'overdue' | 'unknown';
  statusLabel: string;
}

export function parseActivityEntry(entry: ChatterTimelineEntry): ParsedActivityInfo {
  const activity = entry.activity || {};
  const title = entry.title || entry.body || '待办活动';
  const deadline = activity.deadline ? new Date(activity.deadline) : undefined;
  const status: ParsedActivityInfo['status'] = activity.status === 'pending' || activity.status === 'overdue'
    ? activity.status
    : 'unknown';
  const statusLabel = activity.status_label || '状态未知';

  return {
    title,
    assignee: activity.assignee_name,
    deadline: activity.deadline,
    deadlineLabel: deadline ? formatCollaborationTimelineMeta(activity.deadline!) : undefined,
    activityType: activity.activity_type,
    canComplete: Boolean(activity.can_complete),
    canCancel: Boolean(activity.can_cancel),
    at: entry.at,
    atLabel: entry.at ? formatCollaborationTimelineMeta(entry.at) : undefined,
    icon: '📋',
    status,
    statusLabel,
  };
}
