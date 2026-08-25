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
    <p v-if="unavailableMessage" class="native-chatter-empty">{{ unavailableMessage }}</p>
    <div v-else-if="!readonly" class="chips">
      <button
        v-for="action in actions"
        :key="`chatter-${action.key}`"
        class="chip-btn"
        type="button"
        :disabled="busy || posting || !action.enabled"
        :title="action.hint"
        @click="$emit('open-action', action)"
      >
        {{ action.label }}
      </button>
    </div>
    <section v-if="!readonly && !unavailableMessage && activeMode" class="native-chatter-compose" data-professional-collaboration-component="composer" :data-composer-mode="activeIsActivity ? 'activity' : 'comment'">
      <template v-if="activeIsActivity">
        <label class="native-chatter-field">
          <span>{{ activityAssigneeLabel }}</span>
          <select
            class="input"
            :value="activityAssigneeId || ''"
            :disabled="posting || usersLoading"
            @change="emitActivityAssignee"
          >
            <option value="">当前用户</option>
            <option v-for="user in activityAssigneeOptions" :key="`activity-user-${user.id}`" :value="user.id">
              {{ collaborationUserLabel(user) }}
            </option>
          </select>
        </label>
        <label class="native-chatter-field">
          <span>{{ activitySummaryLabel }}</span>
          <input
            class="input"
            type="text"
            :value="activitySummary"
            :placeholder="activitySummaryPlaceholder"
            :disabled="posting"
            @input="$emit('update:activitySummary', inputValue($event))"
          />
        </label>
        <label class="native-chatter-field">
          <span>{{ activityDeadlineLabel }}</span>
          <input
            class="input"
            type="date"
            :value="activityDeadline"
            :disabled="posting"
            @input="$emit('update:activityDeadline', inputValue($event))"
          />
        </label>
        <label class="native-chatter-field">
          <span>{{ activityNoteLabel }}</span>
          <textarea
            class="native-chatter-input"
            :value="activityNote"
            :placeholder="activityNotePlaceholder"
            :disabled="posting"
            @input="$emit('update:activityNote', inputValue($event))"
          />
        </label>
      </template>
      <template v-else>
        <label class="native-chatter-field">
          <span>提醒对象</span>
          <input
            class="input"
            type="text"
            :value="collaborationUserQuery"
            :disabled="posting || usersLoading"
            placeholder="搜索姓名或账号"
            @input="emitCollaborationUserQuery"
          />
        </label>
        <div v-if="selectedMentionUsers.length" class="native-collab-selected">
          <button
            v-for="user in selectedMentionUsers"
            :key="`mention-selected-${user.id}`"
            class="chip-btn"
            type="button"
            :disabled="posting"
            @click="$emit('remove-mention-user', user.id)"
          >
            @{{ collaborationUserLabel(user) }} x
          </button>
        </div>
        <div v-if="collaborationUserChoices.length" class="native-collab-options">
          <button
            v-for="user in collaborationUserChoices.slice(0, 6)"
            :key="`mention-choice-${user.id}`"
            class="ghost mini"
            type="button"
            :disabled="posting"
            @click="$emit('select-mention-user', user)"
          >
            @{{ collaborationUserLabel(user) }}
          </button>
        </div>
        <textarea
          class="native-chatter-input"
          :value="chatterDraft"
          :placeholder="activePlaceholder"
          :disabled="posting"
          @input="$emit('update:chatterDraft', inputValue($event))"
        />
      </template>
      <div class="native-chatter-compose-actions">
        <button class="primary" type="button" :disabled="submitDisabled" @click="$emit('send-chatter')">
          {{ posting ? activePostingLabel : activeSubmitLabel }}
        </button>
        <button class="ghost" type="button" :disabled="posting" @click="$emit('close-composer')">取消</button>
      </div>
    </section>
    <p v-if="chatterError" class="validation-error native-chatter-message">{{ chatterError }}</p>
    <section
      v-if="!readonly && hasAttachments"
      class="native-attachment-tools"
      data-collaboration-capability="attachments"
    >
      <label class="chip-btn native-attachment-upload">
        {{ attachmentUploading ? attachmentUploadingLabel : attachmentUploadLabel }}
        <input type="file" :disabled="attachmentUploading" @change="$emit('attachment-selected', $event)" />
      </label>
      <p v-if="attachmentError" class="validation-error native-chatter-message">{{ attachmentError }}</p>
    </section>
    <ul v-if="pendingAttachments.length" class="native-pending-attachments">
      <li v-for="item in pendingAttachments" :key="item.key">
        <span>{{ item.name }}</span>
        <button
          class="ghost native-attachment-download"
          type="button"
          :disabled="attachmentUploading"
          @click="$emit('remove-pending-attachment', item.key)"
        >
          移除
        </button>
      </li>
    </ul>
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
import { collaborationCapabilityReadiness, visibleCollaborationTimeline } from './professionalCollaborationModel';

type PendingNativeAttachment = {
  key: string;
  name: string;
  size: number;
  file: File;
};

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
  pendingAttachments: PendingNativeAttachment[];
  timeline: ChatterTimelineEntry[];
  timelineHasMore: boolean;
  timelineLoading: boolean;
  activityUpdatingIds: number[];
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
  'attachment-selected': (event: Event) => void;
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
  'attachment-selected': [event: Event];
  'remove-pending-attachment': [key: string];
  'update-activity': [entry: ChatterTimelineEntry, action: 'done' | 'cancel'];
  'open-attachment': [attachment: NonNullable<ChatterTimelineEntry['attachment']>];
  'load-more-timeline': [];
}>();

function inputValue(event: Event) {
  return String((event.target as HTMLInputElement | HTMLTextAreaElement).value || '');
}

function emitCollaborationUserQuery(event: Event) {
  const value = inputValue(event);
  emit('update:collaborationUserQuery', value);
  emit('load-users', value);
}

function emitActivityAssignee(event: Event) {
  const value = Number((event.target as HTMLSelectElement).value || 0);
  emit('select-activity-assignee', Number.isFinite(value) && value > 0 ? value : 0);
}

function forwardActivityUpdate(entry: ChatterTimelineEntry, action: 'done' | 'cancel') {
  emit('update-activity', entry, action);
}

function collaborationUserLabel(user: CollaborationUserOption) {
  return String(user.name || user.login || user.email || user.id || '').trim();
}

</script>

<style scoped src="./NativeCollaborationPanel.css"></style>
