<template>
  <section
    class="native-chatter-compose"
    data-professional-collaboration-component="composer"
    data-semantic-component="ProfessionalCollaborationComposer"
    :data-state="posting ? 'loading' : submitDisabled ? 'disabled' : 'ready'"
    :data-composer-mode="activity ? 'activity' : 'comment'"
  >
    <template v-if="activity">
      <label class="native-chatter-field">
        <span>{{ activityAssigneeLabel }}</span>
        <ScSelect :model-value="activityAssigneeId || ''" :disabled="posting || usersLoading" @update:model-value="emitActivityAssignee">
          <option value="">当前用户</option>
          <option v-for="user in activityAssigneeOptions" :key="`activity-user-${user.id}`" :value="user.id">
            {{ collaborationUserLabel(user) }}
          </option>
        </ScSelect>
      </label>
      <label class="native-chatter-field">
        <span>{{ activitySummaryLabel }}</span>
        <ScInput type="text" :model-value="activitySummary" :placeholder="activitySummaryPlaceholder" :disabled="posting" @update:model-value="emit('update:activitySummary', $event)" />
      </label>
      <label class="native-chatter-field">
        <span>{{ activityDeadlineLabel }}</span>
        <ScInput type="date" :model-value="activityDeadline" :disabled="posting" @update:model-value="emit('update:activityDeadline', $event)" />
      </label>
      <label class="native-chatter-field">
        <span>{{ activityNoteLabel }}</span>
        <ScTextarea class="native-chatter-input" :model-value="activityNote" :placeholder="activityNotePlaceholder" :disabled="posting" :loading="posting" @update:model-value="emit('update:activityNote', $event)" />
      </label>
    </template>
    <template v-else>
      <label class="native-chatter-field">
        <span>提醒对象</span>
        <ScInput type="search" :model-value="collaborationUserQuery" :disabled="posting || usersLoading" :loading="usersLoading" placeholder="搜索姓名或账号" @update:model-value="emitCollaborationUserQuery" />
      </label>
      <div v-if="selectedMentionUsers.length" class="native-collab-selected">
        <ScButton v-for="user in selectedMentionUsers" :key="`mention-selected-${user.id}`" size="small" :disabled="posting" @click="emit('remove-mention-user', user.id)">
          @{{ collaborationUserLabel(user) }} x
        </ScButton>
      </div>
      <div v-if="collaborationUserChoices.length" class="native-collab-options">
        <ScButton v-for="user in collaborationUserChoices.slice(0, 6)" :key="`mention-choice-${user.id}`" variant="ghost" size="small" :disabled="posting" @click="emit('select-mention-user', user)">
          @{{ collaborationUserLabel(user) }}
        </ScButton>
      </div>
      <ScTextarea class="native-chatter-input" :model-value="draft" :placeholder="placeholder" :disabled="posting" :loading="posting" @update:model-value="emit('update:draft', $event)" />
    </template>
    <div class="native-chatter-compose-actions">
      <ScButton variant="primary" :disabled="submitDisabled" :loading="posting" :loading-label="postingLabel" @click="emit('submit')">{{ posting ? postingLabel : submitLabel }}</ScButton>
      <ScButton variant="ghost" :disabled="posting" @click="emit('cancel')">取消</ScButton>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { CollaborationUserOption } from '../../api/chatter';
import ScButton from '../../components/design-system/ScButton.vue';
import ScInput from '../../components/design-system/ScInput.vue';
import ScSelect from '../../components/design-system/ScSelect.vue';
import ScTextarea from '../../components/design-system/ScTextarea.vue';

defineProps<{
  activity: boolean;
  posting: boolean;
  usersLoading: boolean;
  draft: string;
  placeholder: string;
  submitLabel: string;
  postingLabel: string;
  submitDisabled: boolean;
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
}>();

const emit = defineEmits<{
  'update:draft': [value: string];
  'update:collaborationUserQuery': [value: string];
  'load-users': [query: string];
  'select-mention-user': [user: CollaborationUserOption];
  'remove-mention-user': [id: number];
  'select-activity-assignee': [id: number];
  'update:activitySummary': [value: string];
  'update:activityDeadline': [value: string];
  'update:activityNote': [value: string];
  submit: [];
  cancel: [];
}>();

function emitCollaborationUserQuery(value: string) {
  emit('update:collaborationUserQuery', value);
  emit('load-users', value);
}

function emitActivityAssignee(rawValue: string) {
  const value = Number(rawValue || 0);
  emit('select-activity-assignee', Number.isFinite(value) && value > 0 ? value : 0);
}

function collaborationUserLabel(user: CollaborationUserOption) {
  return String(user.name || user.login || user.email || user.id || '').trim();
}
</script>

<style scoped src="./NativeCollaborationPanel.css"></style>
