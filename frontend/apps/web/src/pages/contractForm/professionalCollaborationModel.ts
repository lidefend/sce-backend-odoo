import type { ChatterTimelineEntry } from '../../api/chatter';

export type ProfessionalCollaborationCapability = 'comment' | 'attachment' | 'activity' | 'follower';
export type ProfessionalCollaborationReadiness = 'ready' | 'fail_closed';

export function collaborationCapabilityReadiness(input: {
  hasCommentAction: boolean;
  hasAttachmentAuthority: boolean;
  hasActivityAction: boolean;
}): Readonly<Record<ProfessionalCollaborationCapability, ProfessionalCollaborationReadiness>> {
  return Object.freeze({
    comment: input.hasCommentAction ? 'ready' : 'fail_closed',
    attachment: input.hasAttachmentAuthority ? 'ready' : 'fail_closed',
    activity: input.hasActivityAction ? 'ready' : 'fail_closed',
    follower: 'fail_closed',
  });
}

export function visibleCollaborationTimeline(entries: readonly ChatterTimelineEntry[]): ChatterTimelineEntry[] {
  return entries.filter((entry) => entry.type !== 'audit');
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
