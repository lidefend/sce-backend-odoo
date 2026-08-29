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
        <!-- 其他类型：原有显示模板 -->
        <template v-else>
        <span class="native-chatter-type">{{ entry.typeLabel }}</span>
        <span class="native-chatter-body">{{ entry.type === 'activity' ? entry.title : (entry.body || entry.title) }}</span>
        <span class="native-chatter-meta">{{ formatCollaborationTimelineMeta(entry.meta) }}</span>
        <div v-if="entry.type === 'activity'" class="native-chatter-entry-actions">
          <ScButton v-if="entry.activity?.can_complete" variant="ghost" size="small" class="native-chatter-entry-action" :loading="isUpdating(entry)" @click="emit('update-activity', entry, 'done')">完成</ScButton>
          <ScButton v-if="entry.activity?.can_cancel" variant="ghost" size="small" class="native-chatter-entry-action" :disabled="isUpdating(entry)" @click="emit('update-activity', entry, 'cancel')">取消</ScButton>
        </div>
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
import { formatCollaborationTimelineMeta, parseAttachmentEntry, type ParsedAttachmentInfo } from './professionalCollaborationModel';

const props = defineProps<{ entries: ChatterTimelineEntry[]; activityUpdatingIds: number[]; attachmentViewLabel: string; timelineHasMore: boolean; timelineLoading: boolean }>();
const emit = defineEmits<{
  'update-activity': [entry: ChatterTimelineEntry, action: 'done' | 'cancel'];
  'open-attachment': [attachment: NonNullable<ChatterTimelineEntry['attachment']>];
  'load-more': [];
}>();

function entryId(entry: ChatterTimelineEntry) { return Number(entry.activity?.id || entry.id || 0); }
function isUpdating(entry: ChatterTimelineEntry) { const id = entryId(entry); return Boolean(id && props.activityUpdatingIds.includes(id)); }
function entryFrom(item: ScListItem): ChatterTimelineEntry | null { return item as unknown as ChatterTimelineEntry; }
function attachmentInfo(entry: ChatterTimelineEntry): ParsedAttachmentInfo { return parseAttachmentEntry(entry); }
</script>

<style scoped src="./NativeCollaborationPanel.css"></style>
