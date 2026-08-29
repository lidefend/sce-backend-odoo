<template>
  <section
    data-professional-collaboration-component="timeline"
    :data-collaboration-entry-count="entries.length"
  >
    <ScList v-if="entries.length" class="native-chatter-timeline" :items="entries.map((entry) => ({ ...entry, key: entry.key }))">
      <template #item="{ item: rawEntry }">
        <article class="native-chatter-entry" :data-collaboration-entry-type="entryFrom(rawEntry)?.type">
          <template v-if="entryFrom(rawEntry)">
        <template v-for="entry in [entryFrom(rawEntry)!]" :key="entry.key">
        <!-- 附件类型：专门的显示模板 -->
        <template v-if="entry.type === 'attachment'">
          <div class="native-chatter-attachment-item">
            <span class="native-chatter-attachment-icon">{{ attachmentInfo(entry).icon }}</span>
            <div class="native-chatter-attachment-content">
              <span class="native-chatter-attachment-name" :title="attachmentInfo(entry).name">{{ attachmentInfo(entry).name }}</span>
              <span class="native-chatter-attachment-meta">
                <span v-if="attachmentInfo(entry).typeLabel" class="native-chatter-attachment-type">{{ attachmentInfo(entry).typeLabel }}</span>
                <span v-if="attachmentInfo(entry).sizeLabel" class="native-chatter-attachment-size">{{ attachmentInfo(entry).sizeLabel }}</span>
              </span>
            </div>
            <ScButton
              v-if="entry.attachment?.can_download !== false"
              variant="ghost"
              size="small"
              class="native-attachment-download"
              @click="emit('open-attachment', entry.attachment!)"
            >{{ attachmentViewLabel }}</ScButton>
          </div>
          <span v-if="entry.at" class="native-chatter-meta">{{ formatCollaborationTimelineMeta(entry.at) }}</span>
        </template>
        <!-- 消息类型：专门的显示模板 -->
        <template v-else-if="entry.type === 'message'">
          <div class="native-chatter-message-item">
            <span class="native-chatter-message-icon">{{ messageInfo(entry).icon }}</span>
            <div class="native-chatter-message-content">
              <div class="native-chatter-message-header">
                <span class="native-chatter-message-author">{{ messageInfo(entry).author }}</span>
                <span v-if="messageInfo(entry).atLabel" class="native-chatter-message-time">{{ messageInfo(entry).atLabel }}</span>
                <ScButton variant="ghost" size="small" class="native-chatter-message-reply" @click="emit('reply', entry)">回复</ScButton>
              </div>
              <span class="native-chatter-message-body">{{ messageInfo(entry).body }}</span>
            </div>
          </div>
        </template>
        <!-- 活动类型：专门的显示模板 -->
        <template v-else-if="entry.type === 'activity'">
          <div class="native-chatter-activity-item" :data-activity-status="activityInfo(entry).status">
            <span class="native-chatter-activity-icon">{{ activityInfo(entry).icon }}</span>
            <div class="native-chatter-activity-content">
              <div class="native-chatter-activity-header">
                <span class="native-chatter-activity-title">{{ activityInfo(entry).title }}</span>
                <span class="native-chatter-activity-status" :class="`status-${activityInfo(entry).status}`">{{ activityInfo(entry).statusLabel }}</span>
              </div>
              <div class="native-chatter-activity-meta">
                <span v-if="activityInfo(entry).assignee" class="native-chatter-activity-assignee">负责人：{{ activityInfo(entry).assignee }}</span>
                <span v-if="activityInfo(entry).deadlineLabel" class="native-chatter-activity-deadline">截止：{{ activityInfo(entry).deadlineLabel }}</span>
                <span v-if="activityInfo(entry).activityType" class="native-chatter-activity-type">{{ activityInfo(entry).activityType }}</span>
              </div>
              <div v-if="activityInfo(entry).canComplete || activityInfo(entry).canCancel" class="native-chatter-activity-actions">
                <ScButton v-if="activityInfo(entry).canComplete" variant="primary" size="small" class="native-chatter-activity-action" :loading="isUpdating(entry)" @click="emit('update-activity', entry, 'done')">完成</ScButton>
                <ScButton v-if="activityInfo(entry).canCancel" variant="ghost" size="small" class="native-chatter-activity-action" :disabled="isUpdating(entry)" @click="emit('update-activity', entry, 'cancel')">取消</ScButton>
              </div>
            </div>
          </div>
        </template>
        <!-- 其他类型：通用显示模板 -->
        <template v-else>
        <span class="native-chatter-type">{{ entry.typeLabel }}</span>
        <span class="native-chatter-body">{{ entry.body || entry.title }}</span>
        <span class="native-chatter-meta">{{ formatCollaborationTimelineMeta(entry.meta) }}</span>
        </template>
        </template>
          </template>
        </article>
      </template>
    </ScList>
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
import ScList, { type ScListItem } from '../../components/design-system/ScList.vue';
import { formatCollaborationTimelineMeta, parseAttachmentEntry, parseMessageEntry, parseActivityEntry, type ParsedAttachmentInfo, type ParsedMessageInfo, type ParsedActivityInfo } from './professionalCollaborationModel';

const props = defineProps<{ entries: ChatterTimelineEntry[]; activityUpdatingIds: number[]; attachmentViewLabel: string; timelineHasMore: boolean; timelineLoading: boolean }>();
const emit = defineEmits<{
  'update-activity': [entry: ChatterTimelineEntry, action: 'done' | 'cancel'];
  'open-attachment': [attachment: NonNullable<ChatterTimelineEntry['attachment']>];
  'load-more': [];
  'reply': [entry: ChatterTimelineEntry];
}>();

function entryId(entry: ChatterTimelineEntry) { return Number(entry.activity?.id || entry.id || 0); }
function isUpdating(entry: ChatterTimelineEntry) { const id = entryId(entry); return Boolean(id && props.activityUpdatingIds.includes(id)); }
function entryFrom(item: ScListItem): ChatterTimelineEntry | null { return item as unknown as ChatterTimelineEntry; }
function attachmentInfo(entry: ChatterTimelineEntry): ParsedAttachmentInfo { return parseAttachmentEntry(entry); }
function messageInfo(entry: ChatterTimelineEntry): ParsedMessageInfo { return parseMessageEntry(entry); }
function activityInfo(entry: ChatterTimelineEntry): ParsedActivityInfo { return parseActivityEntry(entry); }
</script>

<style scoped src="./NativeCollaborationPanel.css"></style>
