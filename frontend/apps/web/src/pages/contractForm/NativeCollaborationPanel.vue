<template>
  <section
    class="block native-chatter-block"
    data-professional-collaboration-component="panel"
    :data-comment-readiness="capabilityReadiness.comment"
    :data-attachment-readiness="capabilityReadiness.attachment"
    :data-activity-readiness="capabilityReadiness.activity"
    :data-follower-readiness="capabilityReadiness.follower"
  >
    <h3>{{ title }}</h3>
    <ScInlineState v-if="unavailableMessage" class="native-chatter-empty" state="empty" :label="unavailableMessage" />
    <div v-else-if="!readonly" class="chips">
      <ScButton
        v-for="action in actions"
        :key="`chatter-${action.key}`"
        size="small"
        :disabled="busy || posting || !action.enabled"
        :title="action.hint"
        @click="$emit('open-action', action)"
      >
        {{ action.label }}
      </ScButton>
    </div>
    <ProfessionalCollaborationComposer
      v-if="!readonly && !unavailableMessage && activeMode"
      :activity="activeIsActivity"
      :posting="posting"
      :users-loading="usersLoading"
      :draft="chatterDraft"
      :placeholder="activePlaceholder"
      :submit-label="activeSubmitLabel"
      :posting-label="activePostingLabel"
      :submit-disabled="submitDisabled"
      :collaboration-user-query="collaborationUserQuery"
      :selected-mention-users="selectedMentionUsers"
      :collaboration-user-choices="collaborationUserChoices"
      :activity-assignee-options="activityAssigneeOptions"
      :activity-assignee-id="activityAssigneeId"
      :activity-assignee-label="activityAssigneeLabel"
      :activity-summary="activitySummary"
      :activity-deadline="activityDeadline"
      :activity-note="activityNote"
      :activity-summary-label="activitySummaryLabel"
      :activity-deadline-label="activityDeadlineLabel"
      :activity-note-label="activityNoteLabel"
      :activity-summary-placeholder="activitySummaryPlaceholder"
      :activity-note-placeholder="activityNotePlaceholder"
      @update:draft="$emit('update:chatterDraft', $event)"
      @update:collaboration-user-query="$emit('update:collaborationUserQuery', $event)"
      @load-users="$emit('load-users', $event)"
      @select-mention-user="$emit('select-mention-user', $event)"
      @remove-mention-user="$emit('remove-mention-user', $event)"
      @select-activity-assignee="$emit('select-activity-assignee', $event)"
      @update:activity-summary="$emit('update:activitySummary', $event)"
      @update:activity-deadline="$emit('update:activityDeadline', $event)"
      @update:activity-note="$emit('update:activityNote', $event)"
      @submit="$emit('send-chatter')"
      @cancel="$emit('close-composer')"
    />
    <ScInlineState v-if="chatterError" class="validation-error native-chatter-message" state="error" :label="chatterError" />
    <ProfessionalAttachmentManager
      :editable="!readonly"
      :enabled="hasAttachments"
      :uploading="attachmentUploading"
      :upload-label="attachmentUploadLabel"
      :uploading-label="attachmentUploadingLabel"
      :error="attachmentError"
      :pending="pendingAttachments"
      @selected="$emit('attachment-selected', $event)"
      @remove="$emit('remove-pending-attachment', $event)"
    />
    <ProfessionalAuditTimeline
      v-if="showAuditTimeline !== false && auditEvents.length"
      :events="auditEvents"
      declared
      summary="历史审计"
    />
    <ProfessionalCollaborationTimeline
      v-if="!unavailableMessage"
      :entries="visibleTimeline"
      :activity-updating-ids="activityUpdatingIds"
      :attachment-view-label="attachmentViewLabel"
      :timeline-has-more="timelineHasMore"
      :timeline-loading="timelineLoading"
      @update-activity="forwardActivityUpdate"
      @open-attachment="$emit('open-attachment', $event)"
      @load-more="$emit('load-more-timeline')"
    />
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { ChatterTimelineEntry, CollaborationUserOption } from '../../api/chatter';
import type { NativeChatterAction } from './types';
import ProfessionalAuditTimeline from './ProfessionalAuditTimeline.vue';
import { resolveProfessionalAuditEvents } from './professionalAuditModel';
import ProfessionalCollaborationTimeline from './ProfessionalCollaborationTimeline.vue';
import ProfessionalCollaborationComposer from './ProfessionalCollaborationComposer.vue';
import { collaborationCapabilityReadiness, visibleCollaborationTimeline } from './professionalCollaborationModel';
import ProfessionalAttachmentManager, { type PendingProfessionalAttachment } from './ProfessionalAttachmentManager.vue';
import ScButton from '../../components/design-system/ScButton.vue';
import ScInlineState from '../../components/design-system/ScInlineState.vue';

export type NativeCollaborationPanelProps = {
  readonly?: boolean;
  showAuditTimeline?: boolean;
  title: string;
  unavailableMessage: string;
  actions: NativeChatterAction[];
  busy: boolean;
  posting: boolean;
  usersLoading: boolean;
  activeMode: string;
  activeIsActivity: boolean;
  activePlaceholder: string;
  activeSubmitLabel: string;
  activePostingLabel: string;
  chatterDraft: string;
  collaborationUserQuery: string;
  selectedMentionUsers: CollaborationUserOption[];
  collaborationUserChoices: CollaborationUserOption[];
  activityAssigneeOptions: CollaborationUserOption[];
  activityAssigneeId: number;
  activityAssigneeLabel: string;
  activitySummary: string;
  activityDeadline: string;
  activityNote: string;
  activitySummaryLabel: string;
  activityDeadlineLabel: string;
  activityNoteLabel: string;
  activitySummaryPlaceholder: string;
  activityNotePlaceholder: string;
  submitDisabled: boolean;
  chatterError: string;
  hasAttachments: boolean;
  attachmentUploading: boolean;
  attachmentUploadLabel: string;
  attachmentUploadingLabel: string;
  attachmentViewLabel: string;
  attachmentError: string;
  pendingAttachments: PendingProfessionalAttachment[];
  timeline: ChatterTimelineEntry[];
  timelineHasMore: boolean;
  timelineLoading: boolean;
  activityUpdatingIds: number[];
  replyTarget: { id: number; author: string; body: string } | null;
};

export type NativeCollaborationPanelListeners = {
  'open-action': (action: NativeChatterAction) => void;
  'update:chatterDraft': (value: string) => void;
  'update:collaborationUserQuery': (value: string) => void;
  'load-users': (query: string) => void;
  'select-mention-user': (user: CollaborationUserOption) => void;
  'remove-mention-user': (id: number) => void;
  'select-activity-assignee': (id: number) => void;
  'update:activitySummary': (value: string) => void;
  'update:activityDeadline': (value: string) => void;
  'update:activityNote': (value: string) => void;
  'send-chatter': () => void;
  'close-composer': () => void;
  'attachment-selected': (file: File | null) => void;
  'remove-pending-attachment': (key: string) => void;
  'update-activity': (entry: ChatterTimelineEntry, action: 'done' | 'cancel') => void;
  'open-attachment': (attachment: NonNullable<ChatterTimelineEntry['attachment']>) => void;
  'load-more-timeline': () => void;
};

const props = defineProps<NativeCollaborationPanelProps>();
const visibleTimeline = computed(() => visibleCollaborationTimeline(props.timeline));
const auditEvents = computed(() => resolveProfessionalAuditEvents(props.timeline));
const capabilityReadiness = computed(() => collaborationCapabilityReadiness({
  hasCommentAction: props.actions.some((action) => action.mode !== 'activity' && action.enabled),
  hasAttachmentAuthority: props.hasAttachments,
  hasActivityAction: props.actions.some((action) => action.mode === 'activity' && action.enabled),
}));


const emit = defineEmits<{
  'open-action': [action: NativeChatterAction];
  'update:chatterDraft': [value: string];
  'update:collaborationUserQuery': [value: string];
  'load-users': [query: string];
  'select-mention-user': [user: CollaborationUserOption];
  'remove-mention-user': [id: number];
  'select-activity-assignee': [id: number];
  'update:activitySummary': [value: string];
  'update:activityDeadline': [value: string];
  'update:activityNote': [value: string];
  'send-chatter': [];
  'close-composer': [];
  'attachment-selected': [file: File | null];
  'remove-pending-attachment': [key: string];
  'update-activity': [entry: ChatterTimelineEntry, action: 'done' | 'cancel'];
  'open-attachment': [attachment: NonNullable<ChatterTimelineEntry['attachment']>];
  'load-more-timeline': [];
}>();

function forwardActivityUpdate(entry: ChatterTimelineEntry, action: 'done' | 'cancel') {
  emit('update-activity', entry, action);
}

function handleReply(entry: ChatterTimelineEntry) {
  const messageInfo = entry.message;
  if (!messageInfo) return;
  emit('reply', entry);
}

</script>

<style scoped src="./NativeCollaborationPanel.css"></style>
