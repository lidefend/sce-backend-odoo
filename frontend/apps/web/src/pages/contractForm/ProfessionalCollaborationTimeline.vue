<template>
  <section
    data-professional-collaboration-component="timeline"
    :data-collaboration-entry-count="entries.length"
  >
    <ul v-if="entries.length" class="native-chatter-timeline">
      <li v-for="entry in entries" :key="entry.key" class="native-chatter-entry" :data-collaboration-entry-type="entry.type">
        <span class="native-chatter-type">{{ entry.typeLabel }}</span>
        <span class="native-chatter-body">{{ entry.type === 'activity' ? entry.title : (entry.body || entry.title) }}</span>
        <span class="native-chatter-meta">{{ formatCollaborationTimelineMeta(entry.meta) }}</span>
        <div v-if="entry.type === 'activity'" class="native-chatter-entry-actions">
          <button v-if="entry.activity?.can_complete" class="ghost native-chatter-entry-action" type="button" :disabled="isUpdating(entry)" @click="emit('update-activity', entry, 'done')">完成</button>
          <button v-if="entry.activity?.can_cancel" class="ghost native-chatter-entry-action" type="button" :disabled="isUpdating(entry)" @click="emit('update-activity', entry, 'cancel')">取消</button>
        </div>
        <button v-if="entry.type === 'attachment' && entry.attachment" class="ghost native-attachment-download" type="button" @click="emit('open-attachment', entry.attachment)">{{ attachmentViewLabel }}</button>
      </li>
    </ul>
    <button v-if="timelineHasMore" class="ghost native-chatter-load-more" type="button" :disabled="timelineLoading" @click="emit('load-more')">{{ timelineLoading ? '加载中...' : '加载更多' }}</button>
  </section>
</template>

<script setup lang="ts">
import type { ChatterTimelineEntry } from '../../api/chatter';
import { formatCollaborationTimelineMeta } from './professionalCollaborationModel';

const props = defineProps<{ entries: ChatterTimelineEntry[]; activityUpdatingIds: number[]; attachmentViewLabel: string; timelineHasMore: boolean; timelineLoading: boolean }>();
const emit = defineEmits<{
  'update-activity': [entry: ChatterTimelineEntry, action: 'done' | 'cancel'];
  'open-attachment': [attachment: NonNullable<ChatterTimelineEntry['attachment']>];
  'load-more': [];
}>();

function entryId(entry: ChatterTimelineEntry) { return Number(entry.activity?.id || entry.id || 0); }
function isUpdating(entry: ChatterTimelineEntry) { const id = entryId(entry); return Boolean(id && props.activityUpdatingIds.includes(id)); }
</script>

<style scoped src="./NativeCollaborationPanel.css"></style>
