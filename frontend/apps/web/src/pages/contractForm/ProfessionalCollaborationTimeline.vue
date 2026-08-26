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
          <ScButton v-if="entry.activity?.can_complete" variant="ghost" size="small" class="native-chatter-entry-action" :loading="isUpdating(entry)" @click="emit('update-activity', entry, 'done')">完成</ScButton>
          <ScButton v-if="entry.activity?.can_cancel" variant="ghost" size="small" class="native-chatter-entry-action" :disabled="isUpdating(entry)" @click="emit('update-activity', entry, 'cancel')">取消</ScButton>
        </div>
        <ScButton v-if="entry.type === 'attachment' && entry.attachment" variant="ghost" size="small" class="native-attachment-download" @click="emit('open-attachment', entry.attachment)">{{ attachmentViewLabel }}</ScButton>
      </li>
    </ul>
    <ScInlineState
      v-else
      class="native-chatter-empty"
      :state="timelineLoading ? 'loading' : 'empty'"
      :label="timelineLoading ? '活动记录加载中...' : '暂无活动记录'"
    />
    <ScButton v-if="timelineHasMore" variant="ghost" :loading="timelineLoading" loading-label="加载中" class="native-chatter-load-more" @click="emit('load-more')">{{ timelineLoading ? '加载中...' : '加载更多' }}</ScButton>
  </section>
</template>

<script setup lang="ts">
import type { ChatterTimelineEntry } from '../../api/chatter';
import ScButton from '../../components/design-system/ScButton.vue';
import ScInlineState from '../../components/design-system/ScInlineState.vue';
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
