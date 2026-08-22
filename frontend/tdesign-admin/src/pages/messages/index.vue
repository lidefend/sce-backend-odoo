<template>
  <div class="messages-page">
    <div class="page-heading">
      <div>
        <p class="eyebrow">协作中心</p>
        <h1>消息中心</h1>
        <p>查看会话、系统通知并向协作用户发送消息。</p>
      </div>
      <t-button variant="outline" :loading="loading" @click="loadConversations"
        ><template #icon><t-icon name="refresh" /></template>刷新</t-button
      >
    </div>
    <t-alert v-if="error" theme="error" :message="error" />
    <div class="messages-layout">
      <t-card class="conversation-panel" :bordered="false">
        <template #title>最近会话</template
        ><template #actions><t-button size="small" theme="primary" @click="newConversation">新建</t-button></template>
        <t-list v-if="conversations.length" split>
          <t-list-item
            v-for="item in conversations"
            :key="item.key"
            class="conversation-item"
            :class="{ active: item.key === activeKey }"
            @click="select(item)"
          >
            <div>
              <strong>{{ item.title || '未命名会话' }}</strong>
              <p>{{ item.latest_message?.body || '暂无消息' }}</p>
            </div>
            <t-badge v-if="item.unread_count" :count="item.unread_count" />
          </t-list-item> </t-list
        ><t-empty v-else-if="!loading" description="暂无会话" />
      </t-card>
      <t-card class="thread-panel" :bordered="false">
        <template #title>{{ compose ? '新建消息' : active?.title || '选择会话' }}</template>
        <div v-if="compose" class="recipient-box">
          <t-select
            v-model="recipientIds"
            multiple
            filterable
            remote
            :options="userOptions"
            placeholder="搜索并选择接收人"
            :on-search="searchUsers"
          />
        </div>
        <div class="thread-list">
          <t-button
            v-if="threadHasMore"
            class="load-more"
            variant="text"
            :loading="threadLoading"
            @click="loadMoreThread"
            >加载更多</t-button
          >
          <div
            v-for="message in messages"
            :key="message.id"
            class="message-item"
            :class="{ outgoing: message.is_outgoing }"
          >
            <strong>{{ message.author_name || '系统' }}</strong>
            <p>{{ message.body }}</p>
            <small>{{ message.date }}</small>
          </div>
          <t-empty v-if="!messages.length" description="暂无消息" />
        </div>
        <t-alert v-if="sendError" class="send-error" theme="error" :message="sendError">
          <template #操作><t-button size="small" variant="outline" @click="retrySend">重试发送</t-button></template>
        </t-alert>
        <div class="composer">
          <t-textarea
            v-model="body"
            :disabled="!compose && !active"
            placeholder="输入消息内容"
            :autosize="{ minRows: 3, maxRows: 6 }"
          /><t-button theme="primary" :loading="sending" @click="send">发送</t-button>
        </div>
      </t-card>
    </div>
  </div>
</template>
<script setup lang="ts">
import { MessagePlugin } from 'tdesign-vue-next';
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { useRoute } from 'vue-router';

import type { GlobalMessageConversation, GlobalMessageItem } from '@/api/odoo';
import {
  fetchGlobalMessageConversations,
  fetchGlobalMessageInbox,
  markGlobalMessagesRead,
  searchCollaborationUsers,
  sendGlobalMessage,
} from '@/api/odoo';

const loading = ref(false);
const sending = ref(false);
const threadLoading = ref(false);
const threadLimit = ref(50);
const threadHasMore = ref(false);
const sendError = ref('');
const pendingSend = ref<{ recipients: number[]; body: string } | null>(null);
let refreshTimer: ReturnType<typeof setInterval> | undefined;
const error = ref('');
const compose = ref(true);
const activeKey = ref('');
const body = ref('');
const recipientIds = ref<number[]>([]);
const messages = ref<GlobalMessageItem[]>([]);
const conversations = ref<GlobalMessageConversation[]>([]);
const userOptions = ref<Array<{ label: string; value: number }>>([]);
const active = computed(() => conversations.value.find((item) => item.key === activeKey.value));
const route = useRoute();
async function loadConversations() {
  loading.value = true;
  error.value = '';
  try {
    const result = await fetchGlobalMessageConversations({ limit: 50 });
    conversations.value = result.items || [];
    const requestedConversation = String(route.query.conversation || '');
    if (requestedConversation) {
      const target = conversations.value.find((item) => item.key === requestedConversation);
      if (target) await select(target);
    }
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '会话加载失败';
  } finally {
    loading.value = false;
  }
}
async function select(item: GlobalMessageConversation) {
  compose.value = false;
  activeKey.value = item.key;
  recipientIds.value = [...(item.participant_user_ids || [])];
  threadLimit.value = 50;
  threadHasMore.value = false;
  await loadThread(item.key);
  await markGlobalMessagesRead({ conversationKey: item.key });
  item.unread_count = 0;
}

async function loadThread(conversationKey: string) {
  threadLoading.value = true;
  try {
    const result = await fetchGlobalMessageInbox({ limit: threadLimit.value });
    const rows = (result.items || []).filter((message) => message.conversation_key === conversationKey);
    messages.value = rows;
    threadHasMore.value = (result.items || []).length >= threadLimit.value && threadLimit.value < 100;
  } finally {
    threadLoading.value = false;
  }
}
async function loadMoreThread() {
  if (!activeKey.value || threadLoading.value || !threadHasMore.value) return;
  threadLoading.value = true;
  try {
    threadLimit.value = Math.min(threadLimit.value + 50, 100);
    const result = await fetchGlobalMessageInbox({ limit: threadLimit.value });
    messages.value = (result.items || []).filter((message) => message.conversation_key === activeKey.value);
    threadHasMore.value = (result.items || []).length >= threadLimit.value && threadLimit.value < 100;
  } finally {
    threadLoading.value = false;
  }
}
async function refreshActiveThread() {
  if (activeKey.value) await loadThread(activeKey.value);
}
function newConversation() {
  compose.value = true;
  activeKey.value = '';
  messages.value = [];
  recipientIds.value = [];
  body.value = '';
  sendError.value = '';
  pendingSend.value = null;
}
async function searchUsers(value: string) {
  const result = await searchCollaborationUsers(value, 20);
  userOptions.value = (result.items || []).map((user) => ({
    value: user.id,
    label: `${user.name}${user.login ? ` · ${user.login}` : ''}`,
  }));
}
async function send() {
  const recipients = recipientIds.value.length ? recipientIds.value : active.value?.participant_user_ids || [];
  if (!body.value.trim() || !recipients.length) {
    MessagePlugin.warning('请选择接收人并输入消息');
    return;
  }
  sending.value = true;
  sendError.value = '';
  pendingSend.value = { recipients, body: body.value.trim() };
  try {
    await sendGlobalMessage({ recipientUserIds: recipients, body: pendingSend.value.body });
    MessagePlugin.success('消息已发送');
    body.value = '';
    await loadConversations();
    if (activeKey.value) await loadThread(activeKey.value);
  } catch (cause) {
    sendError.value = cause instanceof Error ? cause.message : '发送失败';
    MessagePlugin.error(cause instanceof Error ? cause.message : '发送失败');
  } finally {
    sending.value = false;
  }
}
async function retrySend() {
  if (!pendingSend.value || sending.value) return;
  sending.value = true;
  try {
    await sendGlobalMessage({ recipientUserIds: pendingSend.value.recipients, body: pendingSend.value.body });
    sendError.value = '';
    body.value = '';
    pendingSend.value = null;
    await loadConversations();
    if (activeKey.value) await loadThread(activeKey.value);
    MessagePlugin.success('消息已发送');
  } catch (cause) {
    sendError.value = cause instanceof Error ? cause.message : '发送失败';
  } finally {
    sending.value = false;
  }
}
onMounted(() => {
  void loadConversations();
  refreshTimer = setInterval(() => void refreshActiveThread(), 30_000);
});
onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer);
});
</script>
<style scoped>
.messages-page {
  display: grid;
  gap: 16px;
}
.page-heading {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}
.page-heading h1 {
  margin: 4px 0 8px;
  font-size: 28px;
}
.page-heading p {
  margin: 0;
  color: var(--td-text-color-secondary);
}
.eyebrow {
  color: var(--td-brand-color) !important;
  font-size: 13px;
}
.messages-layout {
  display: grid;
  grid-template-columns: minmax(260px, 340px) 1fr;
  gap: 16px;
  min-height: 620px;
}
.conversation-panel,
.thread-panel {
  border: 1px solid var(--td-border-level-1-color);
}
.conversation-item {
  cursor: pointer;
}
.conversation-item.active {
  background: var(--td-brand-color-light);
}
.conversation-item p {
  margin: 4px 0 0;
  color: var(--td-text-color-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 240px;
}
.thread-panel {
  display: grid;
  grid-template-rows: auto auto 1fr auto;
}
.thread-list {
  min-height: 360px;
  overflow: auto;
  padding: 16px 0;
}
.load-more {
  display: block;
  margin: 0 auto 12px;
}
.send-error {
  margin-bottom: 10px;
}
.message-item {
  max-width: 72%;
  margin: 0 0 12px;
  padding: 10px 12px;
  border-radius: 6px;
  background: var(--td-bg-color-secondarycontainer);
}
.message-item.outgoing {
  margin-left: auto;
  background: var(--td-brand-color-light);
}
.message-item p {
  margin: 5px 0;
  white-space: pre-wrap;
}
.message-item small {
  color: var(--td-text-color-placeholder);
}
.composer {
  display: flex;
  gap: 12px;
  align-items: flex-end;
}
.composer .t-textarea {
  flex: 1;
}
.recipient-box {
  padding-top: 8px;
}
@media (max-width: 760px) {
  .messages-layout {
    grid-template-columns: 1fr;
  }
}
</style>
