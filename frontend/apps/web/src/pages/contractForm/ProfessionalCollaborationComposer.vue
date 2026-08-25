<template>
  <section
    class="native-chatter-compose"
    data-professional-collaboration-component="composer"
    :data-composer-mode="activity ? 'activity' : 'comment'"
  >
    <template v-if="activity">
      <label class="native-chatter-field">
        <span>{{ activityAssigneeLabel }}</span>
        <select class="input" :value="activityAssigneeId || ''" :disabled="posting || usersLoading" @change="emitActivityAssignee">
          <option value="">当前用户</option>
          <option v-for="user in activityAssigneeOptions" :key="`activity-user-${user.id}`" :value="user.id">
            {{ collaborationUserLabel(user) }}
          </option>
        </select>
      </label>
      <label class="native-chatter-field">
        <span>{{ activitySummaryLabel }}</span>
        <input class="input" type="text" :value="activitySummary" :placeholder="activitySummaryPlaceholder" :disabled="posting" @input="emit('update:activitySummary', inputValue($event))" />
      </label>
      <label class="native-chatter-field">
        <span>{{ activityDeadlineLabel }}</span>
        <input class="input" type="date" :value="activityDeadline" :disabled="posting" @input="emit('update:activityDeadline', inputValue($event))" />
      </label>
      <label class="native-chatter-field">
        <span>{{ activityNoteLabel }}</span>
        <textarea class="native-chatter-input" :value="activityNote" :placeholder="activityNotePlaceholder" :disabled="posting" @input="emit('update:activityNote', inputValue($event))" />
      </label>
    </template>
    <template v-else>
      <label class="native-chatter-field">
        <span>提醒对象</span>
        <input class="input" type="text" :value="collaborationUserQuery" :disabled="posting || usersLoading" placeholder="搜索姓名或账号" @input="emitCollaborationUserQuery" />
      </label>
      <div v-if="selectedMentionUsers.length" class="native-collab-selected">
        <button v-for="user in selectedMentionUsers" :key="`mention-selected-${user.id}`" class="chip-btn" type="button" :disabled="posting" @click="emit('remove-mention-user', user.id)">
          @{{ collaborationUserLabel(user) }} x
        </button>
      </div>
      <div v-if="collaborationUserChoices.length" class="native-collab-options">
        <button v-for="user in collaborationUserChoices.slice(0, 6)" :key="`mention-choice-${user.id}`" class="ghost mini" type="button" :disabled="posting" @click="emit('select-mention-user', user)">
          @{{ collaborationUserLabel(user) }}
        </button>
      </div>
      <textarea class="native-chatter-input" :value="draft" :placeholder="placeholder" :disabled="posting" @input="emit('update:draft', inputValue($event))" />
    </template>
    <div class="native-chatter-compose-actions">
      <button class="primary" type="button" :disabled="submitDisabled" @click="emit('submit')">{{ posting ? postingLabel : submitLabel }}</button>
      <button class="ghost" type="button" :disabled="posting" @click="emit('cancel')">取消</button>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { CollaborationUserOption } from '../../api/chatter';

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

function collaborationUserLabel(user: CollaborationUserOption) {
  return String(user.name || user.login || user.email || user.id || '').trim();
}
</script>

<style scoped src="./NativeCollaborationPanel.css"></style>
