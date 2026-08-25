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
