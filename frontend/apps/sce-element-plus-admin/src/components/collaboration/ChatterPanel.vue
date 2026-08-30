<template>
  <section class="chatter-panel">
    <div class="chatter-header">
      <div><strong>沟通记录</strong><span>消息、备注、活动与附件</span></div>
      <el-button :loading="loading" :icon="Refresh" @click="load"
        >刷新</el-button
      >
    </div>
    <el-tabs v-model="mode" class="composer-tabs">
      <el-tab-pane label="发送消息" name="message" /><el-tab-pane
        label="内部备注"
        name="note"
      /><el-tab-pane label="计划活动" name="activity" />
    </el-tabs>
    <div v-if="mode !== 'activity'" class="composer">
      <el-input
        v-model="draft"
        type="textarea"
        :rows="3"
        :placeholder="mode === 'note' ? '记录内部备注' : '输入沟通内容'"
      />
      <div class="composer-actions">
        <el-select
          v-model="mentionIds"
          multiple
          filterable
          remote
          reserve-keyword
          collapse-tags
          placeholder="提醒成员"
          :remote-method="loadUsers"
          class="mention-select"
          ><el-option
            v-for="user in users"
            :key="user.id"
            :label="user.name || user.login"
            :value="user.id" /></el-select
        ><el-button
          type="primary"
          :disabled="!draft.trim()"
          :loading="posting"
          @click="post"
          >{{ mode === "note" ? "记录备注" : "发送" }}</el-button
        >
      </div>
    </div>
    <div v-else class="activity-composer">
      <el-input
        v-model="activity.summary"
        placeholder="活动主题"
      /><el-date-picker
        v-model="activity.deadline"
        type="date"
        value-format="YYYY-MM-DD"
        placeholder="截止日期"
      /><el-select
        v-model="activity.userId"
        filterable
        remote
        clearable
        placeholder="负责人"
        :remote-method="loadUsers"
        ><el-option
          v-for="user in users"
          :key="user.id"
          :label="user.name || user.login"
          :value="user.id" /></el-select
      ><el-input v-model="activity.note" placeholder="备注" /><el-button
        type="primary"
        :disabled="!activity.summary.trim()"
        :loading="posting"
        @click="schedule"
        >创建活动</el-button
      >
    </div>
    <div class="collaboration-tools">
      <binary-field :model="model" :record-id="recordId" @uploaded="load" />
      <div class="followers">
        <span>关注者</span
        ><el-tag
          v-for="follower in followers"
          :key="follower.id"
          closable
          @close="removeFollower(Number(follower.id))"
          >{{ relationLabel(follower.partner_id) }}</el-tag
        ><el-select
          v-model="newFollower"
          filterable
          remote
          clearable
          placeholder="添加关注者"
          :remote-method="loadUsers"
          class="follower-select"
          @change="addFollower"
          ><el-option
            v-for="user in users.filter((item) => item.partner_id)"
            :key="user.partner_id"
            :label="user.partner_name || user.name"
            :value="user.partner_id"
        /></el-select>
      </div>
    </div>
    <el-empty
      v-if="!loading && !items.length"
      description="暂无沟通记录"
      :image-size="64"
    />
    <el-timeline v-else class="timeline"
      ><el-timeline-item
        v-for="item in items"
        :key="item.key"
        :timestamp="item.at"
        placement="top"
        ><el-card shadow="never"
          ><div class="timeline-title">
            <strong>{{ item.title || item.typeLabel || "记录" }}</strong
            ><el-tag size="small" effect="plain">{{
              item.typeLabel || item.type
            }}</el-tag>
          </div>
          <p v-if="item.body" class="timeline-body">{{ item.body }}</p>
          <small v-if="item.meta">{{ item.meta }}</small>
          <div v-if="item.attachment?.id" class="timeline-actions">
            <el-button
              link
              type="primary"
              @click="download(Number(item.attachment.id))"
              >下载 {{ item.attachment.name }}</el-button
            >
          </div>
          <div v-if="item.activity?.id" class="timeline-actions">
            <span v-if="item.activity.assignee_name"
              >负责人：{{ item.activity.assignee_name }}</span
            ><span v-if="item.activity.deadline"
              >截止：{{ item.activity.deadline }}</span
            ><el-button
              v-if="item.activity.can_complete"
              link
              type="success"
              @click="updateActivity(Number(item.activity.id), 'done')"
              >完成</el-button
            ><el-button
              v-if="item.activity.can_cancel"
              link
              type="danger"
              @click="updateActivity(Number(item.activity.id), 'cancel')"
              >取消</el-button
            >
          </div></el-card
        ></el-timeline-item
      ></el-timeline
    >
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { Refresh } from "@element-plus/icons-vue";
import BinaryField from "@/components/form/BinaryField.vue";
import {
  addRecordFollower,
  downloadFile,
  fetchChatterTimeline,
  listRecordFollowers,
  postChatterMessage,
  removeRecordFollower,
  scheduleChatterActivity,
  searchCollaborationUsers,
  updateChatterActivity,
  type ChatterTimelineEntry,
} from "@/api/odoo";
import type { Dictionary } from "@/types/contracts";
const props = defineProps<{ model: string; recordId: number }>();
const mode = ref<"message" | "note" | "activity">("message");
const draft = ref("");
const mentionIds = ref<number[]>([]);
const items = ref<ChatterTimelineEntry[]>([]);
const users = ref<Dictionary[]>([]);
const followers = ref<Dictionary[]>([]);
const newFollower = ref<number>();
const loading = ref(false);
const posting = ref(false);
const activity = reactive({
  summary: "",
  deadline: "",
  note: "",
  userId: undefined as number | undefined,
});
async function load() {
  loading.value = true;
  try {
    const [timeline, followerRows] = await Promise.all([
      fetchChatterTimeline(props.model, props.recordId),
      listRecordFollowers(props.model, props.recordId),
    ]);
    items.value = timeline.items || [];
    followers.value = followerRows;
  } finally {
    loading.value = false;
  }
}
async function loadUsers(query = "") {
  const result = await searchCollaborationUsers(query, 30);
  users.value = result.items || [];
}
async function post() {
  posting.value = true;
  try {
    await postChatterMessage({
      model: props.model,
      recordId: props.recordId,
      body: draft.value.trim(),
      mode: mode.value as "message" | "note",
      mentionUserIds: mentionIds.value,
    });
    draft.value = "";
    mentionIds.value = [];
    ElMessage.success("沟通记录已保存");
    await load();
  } finally {
    posting.value = false;
  }
}
async function schedule() {
  posting.value = true;
  try {
    await scheduleChatterActivity({
      model: props.model,
      recordId: props.recordId,
      summary: activity.summary.trim(),
      dateDeadline: activity.deadline || undefined,
      note: activity.note || undefined,
      userId: activity.userId,
    });
    Object.assign(activity, {
      summary: "",
      deadline: "",
      note: "",
      userId: undefined,
    });
    ElMessage.success("活动已创建");
    await load();
  } finally {
    posting.value = false;
  }
}
async function updateActivity(activityId: number, action: "done" | "cancel") {
  await updateChatterActivity({
    model: props.model,
    recordId: props.recordId,
    activityId,
    action,
  });
  ElMessage.success(action === "done" ? "活动已完成" : "活动已取消");
  await load();
}
async function addFollower(partnerId: number) {
  if (!partnerId) return;
  await addRecordFollower(props.model, props.recordId, partnerId);
  newFollower.value = undefined;
  await load();
}
async function removeFollower(id: number) {
  await removeRecordFollower(id);
  await load();
}
function relationLabel(value: unknown) {
  return Array.isArray(value)
    ? String(value[1] || value[0])
    : String(value || "关注者");
}
async function download(id: number) {
  const file = await downloadFile(id);
  if (!file.content_b64) return;
  const bytes = Uint8Array.from(atob(file.content_b64), (char) =>
    char.charCodeAt(0),
  );
  const url = URL.createObjectURL(
    new Blob([bytes], { type: file.mimetype || "application/octet-stream" }),
  );
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = file.filename || "attachment";
  anchor.click();
  URL.revokeObjectURL(url);
}
onMounted(() => {
  void load();
  void loadUsers();
});
</script>

<style scoped>
.chatter-panel {
  margin-top: 20px;
  padding: 20px;
  background: #fff;
  border-radius: 4px;
}
.chatter-header,
.composer-actions,
.collaboration-tools,
.followers,
.timeline-title,
.timeline-actions {
  display: flex;
  align-items: center;
}
.chatter-header {
  justify-content: space-between;
}
.chatter-header div {
  display: grid;
  gap: 4px;
}
.chatter-header span,
.timeline-body + small {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.composer {
  display: grid;
  gap: 10px;
}
.composer-actions {
  justify-content: space-between;
  gap: 10px;
}
.mention-select {
  max-width: 420px;
}
.activity-composer {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 2fr auto;
  gap: 8px;
}
.collaboration-tools {
  justify-content: space-between;
  gap: 16px;
  margin: 16px 0;
  padding: 12px 0;
  border-top: 1px solid var(--el-border-color-lighter);
  border-bottom: 1px solid var(--el-border-color-lighter);
}
.followers {
  gap: 6px;
  flex-wrap: wrap;
}
.follower-select {
  width: 150px;
}
.timeline {
  padding-top: 12px;
}
.timeline-title {
  justify-content: space-between;
}
.timeline-body {
  white-space: pre-wrap;
}
.timeline-actions {
  gap: 10px;
  flex-wrap: wrap;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
@media (max-width: 900px) {
  .activity-composer {
    grid-template-columns: 1fr;
  }
  .collaboration-tools {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
