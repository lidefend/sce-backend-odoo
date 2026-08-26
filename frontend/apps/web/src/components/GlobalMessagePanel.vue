<template>
  <div class="global-message">
    <ScButton
      class="global-message__trigger sc-btn sc-btn-sm"
      size="small"
      title="消息"
      aria-label="消息"
      :class="{ active: open }"
      @click.stop="toggle"
    >
      <ScIcon name="bell" :size="16" />
      <span class="global-message__label">消息</span>
      <span v-if="unreadCount" class="global-message__badge sc-badge sc-badge-danger">{{ unreadCount }}</span>
    </ScButton>

    <ScDrawer
      :open="open"
      title="消息"
      description="站内沟通与协作提醒"
      size="wide"
      panel-class="global-message__panel"
      close-label="关闭消息"
      @close="close"
    >
      <template #header-actions>
        <ScButton data-dialog-primary size="small" variant="primary" type="button" @click="startNewConversation">新建</ScButton>
      </template>
      <main class="global-message__workspace">
        <section class="global-message__conversations sc-panel-flat">
          <div class="global-message__section-head">
            <span>最近会话</span>
            <ScButton size="small" variant="ghost" :disabled="loadingConversations" :loading="loadingConversations" loading-label="刷新中" @click="loadConversations">
              {{ loadingConversations ? '刷新中...' : '刷新' }}
            </ScButton>
          </div>
          <div v-if="conversations.length" class="global-message__conversation-list sc-list">
            <button
              v-for="conversation in conversations"
              :key="conversation.key"
              class="global-message__conversation sc-list-item"
              type="button"
              :class="{ active: conversation.key === activeConversationKey && !composeMode }"
              @click="selectConversation(conversation)"
            >
              <span class="global-message__conversation-title">{{ conversation.title || '未命名会话' }}</span>
              <small>{{ conversation.latest_message?.body || '暂无消息' }}</small>
              <span v-if="conversation.unread_count" class="global-message__dot sc-badge sc-badge-danger">{{ conversation.unread_count }}</span>
            </button>
          </div>
          <ScInlineState
            v-else
            class="global-message__empty"
            :state="loadingConversations ? 'loading' : 'empty'"
            :label="loadingConversations ? '会话加载中...' : '暂无会话'"
          />
        </section>

        <section class="global-message__thread">
          <div class="global-message__thread-head">
            <div>
              <h3>{{ composeMode ? '新建消息' : activeConversation?.title || '选择会话' }}</h3>
              <p>{{ composeMode ? '选择接收人，输入内容后发送' : '当前会话' }}</p>
            </div>
          </div>

          <div v-if="composeMode" class="global-message__recipient-box">
            <label class="global-message__field">
              <span>接收人</span>
              <ScInput
                ref="recipientInputRef"
                v-model="userQuery"
                class="sc-search"
                type="search"
                placeholder="搜索姓名、账号或邮箱"
                @focus="loadUsers"
                @input="queueUserSearch"
              />
            </label>
            <p class="global-message__compose-hint sc-muted">{{ composeHint }}</p>
            <div v-if="selectedUsers.length" class="global-message__chips">
              <button
                v-for="user in selectedUsers"
                :key="`global-msg-selected-${user.id}`"
                class="sc-tag"
                type="button"
                @click="removeUser(user.id)"
              >
                {{ user.name }} <ScIcon name="close" :size="14" />
              </button>
            </div>
            <div v-if="userOptions.length" class="global-message__options sc-list">
              <button
                v-for="user in userOptions"
                :key="`global-msg-user-${user.id}`"
                class="sc-list-item"
                type="button"
                :disabled="isSelected(user.id)"
                @click="selectUser(user)"
              >
                <strong>{{ user.name }}</strong>
                <small>{{ user.login || user.email || '内部用户' }}</small>
              </button>
            </div>
          </div>

          <div class="global-message__items">
            <article
              v-for="item in messages"
              :key="`global-message-${item.id}`"
              class="global-message__item"
              :class="{ 'global-message__item--outgoing': item.is_outgoing }"
            >
              <div class="global-message__meta">
                <strong>{{ item.author_name || '系统' }}</strong>
                <time>{{ formatTime(item.date) }}</time>
              </div>
              <p>{{ item.body }}</p>
            </article>
            <ScInlineState
              v-if="!messages.length"
              class="global-message__empty"
              :state="loadingMessages ? 'loading' : 'empty'"
              :label="loadingMessages ? '消息加载中...' : composeMode ? '发送后将自动形成会话' : '请选择左侧会话'"
            />
          </div>

          <footer class="global-message__composer">
            <ScTextarea
              v-model="body"
              rows="3"
              placeholder="输入沟通内容"
              :disabled="!composeMode && !activeConversation"
              @keydown.ctrl.enter.prevent="send"
              @keydown.meta.enter.prevent="send"
            />
            <div class="global-message__composer-actions">
              <ScInlineState v-if="error" class="global-message__error" state="error" :label="error" />
              <ScButton size="small" variant="primary" :disabled="sending" :loading="sending" loading-label="发送中" @click="send">
                {{ sending ? '发送中...' : '发送' }}
              </ScButton>
            </div>
          </footer>
        </section>
      </main>
    </ScDrawer>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onUnmounted, ref, watch } from 'vue';
import ScButton from './design-system/ScButton.vue';
import ScDrawer from './design-system/ScDrawer.vue';
import ScIcon from './design-system/ScIcon.vue';
import ScInput from './design-system/ScInput.vue';
import ScInlineState from './design-system/ScInlineState.vue';
import ScTextarea from './design-system/ScTextarea.vue';
import { searchCollaborationUsers, type CollaborationUserOption } from '../api/chatter';
import {
  fetchGlobalConversations,
  fetchGlobalMessages,
  markGlobalMessagesRead,
  sendGlobalMessage,
  type GlobalMessageConversation,
  type GlobalMessageItem,
} from '../api/globalMessages';
import { useSessionStore } from '../stores/session';

const session = useSessionStore();
const open = ref(false);
const composeMode = ref(true);
const loadingConversations = ref(false);
const loadingMessages = ref(false);
const sending = ref(false);
const error = ref('');
const body = ref('');
const userQuery = ref('');
const userOptions = ref<CollaborationUserOption[]>([]);
const selectedUsers = ref<CollaborationUserOption[]>([]);
const conversations = ref<GlobalMessageConversation[]>([]);
const messages = ref<GlobalMessageItem[]>([]);
const activeConversationKey = ref('');
const recipientInputRef = ref<{ focus: () => void } | null>(null);
const composeNonce = ref(0);
let userSearchTimer: ReturnType<typeof setTimeout> | null = null;
let pollTimer: ReturnType<typeof setInterval> | null = null;
let closedRefreshTimer: ReturnType<typeof setTimeout> | null = null;

const canUseMessages = computed(() => Boolean(session.token && session.initStatus === 'ready'));
const unreadCount = computed(() => conversations.value.reduce((sum, item) => sum + Number(item.unread_count || 0), 0));
const activeConversation = computed(() =>
  conversations.value.find((item) => item.key === activeConversationKey.value) || null,
);
const composeHint = computed(() =>
  composeNonce.value > 0 ? '请先选择接收人' : '选择接收人后发送第一条消息',
);
const activeRecipientUserIds = computed(() => {
  if (composeMode.value) {
    return selectedUsers.value.map((item) => Number(item.id)).filter(Boolean);
  }
  const currentUserId = Number(session.user?.id || 0);
  return (activeConversation.value?.participant_user_ids || [])
    .map((item) => Number(item))
    .filter((id) => id > 0 && id !== currentUserId);
});

function toggle() {
  open.value = !open.value;
}

function close() {
  open.value = false;
}

function isSelected(userId: number) {
  return selectedUsers.value.some((item) => Number(item.id) === Number(userId));
}

function selectUser(user: CollaborationUserOption) {
  if (isSelected(user.id)) return;
  selectedUsers.value = [...selectedUsers.value, user];
  userQuery.value = '';
}

function removeUser(userId: number) {
  selectedUsers.value = selectedUsers.value.filter((item) => Number(item.id) !== Number(userId));
}

function startNewConversation() {
  composeMode.value = true;
  activeConversationKey.value = '';
  messages.value = [];
  selectedUsers.value = [];
  body.value = '';
  userQuery.value = '';
  error.value = '';
  composeNonce.value += 1;
  void nextTick(() => {
    recipientInputRef.value?.focus();
  });
}

async function selectConversation(conversation: GlobalMessageConversation) {
  composeMode.value = false;
  activeConversationKey.value = conversation.key;
  selectedUsers.value = [];
  userQuery.value = '';
  await loadMessagesForConversation(conversation.key);
  await markRead(conversation.key);
}

async function loadUsers() {
  if (!canUseMessages.value) return;
  try {
    const result = await searchCollaborationUsers({ query: userQuery.value, limit: 12 });
    userOptions.value = result.items || [];
  } catch {
    userOptions.value = [];
  }
}

function queueUserSearch() {
  if (userSearchTimer) clearTimeout(userSearchTimer);
  userSearchTimer = setTimeout(() => {
    userSearchTimer = null;
    void loadUsers();
  }, 220);
}

async function loadConversations() {
  if (!canUseMessages.value) return;
  loadingConversations.value = true;
  try {
    const result = await fetchGlobalConversations({ limit: 40 });
    conversations.value = result.items || [];
    if (!composeMode.value && activeConversationKey.value && !conversations.value.some((item) => item.key === activeConversationKey.value)) {
      startNewConversation();
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : '会话加载失败';
  } finally {
    loadingConversations.value = false;
  }
}

async function loadMessagesForConversation(conversationKey: string) {
  if (!canUseMessages.value || !conversationKey) return;
  loadingMessages.value = true;
  error.value = '';
  try {
    const result = await fetchGlobalMessages({ limit: 80, conversation_key: conversationKey });
    messages.value = result.items || [];
  } catch (err) {
    error.value = err instanceof Error ? err.message : '消息加载失败';
  } finally {
    loadingMessages.value = false;
  }
}

async function markRead(conversationKey: string) {
  if (!canUseMessages.value || !conversationKey) return;
  try {
    await markGlobalMessagesRead({ conversation_key: conversationKey });
    conversations.value = conversations.value.map((item) =>
      item.key === conversationKey ? { ...item, unread_count: 0 } : item,
    );
  } catch {
    // read state is non-critical for sending and viewing
  }
}

async function send() {
  if (!canUseMessages.value) {
    error.value = '当前会话未就绪';
    return;
  }
  const text = body.value.trim();
  const recipientIds = activeRecipientUserIds.value;
  if (!recipientIds.length) {
    error.value = composeMode.value ? '请选择接收人' : '当前会话缺少可回复对象';
    return;
  }
  if (!text) {
    error.value = '请输入消息内容';
    return;
  }
  sending.value = true;
  error.value = '';
  try {
    await sendGlobalMessage({ recipient_user_ids: recipientIds, body: text });
    body.value = '';
    await loadConversations();
    const targetConversation = composeMode.value
      ? conversations.value.find((item) => recipientIds.every((id) => item.participant_user_ids.includes(id)))
      : activeConversation.value;
    if (targetConversation) {
      composeMode.value = false;
      activeConversationKey.value = targetConversation.key;
      await loadMessagesForConversation(targetConversation.key);
      await markRead(targetConversation.key);
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : '消息发送失败';
  } finally {
    sending.value = false;
  }
}

function formatTime(value: string) {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

watch(open, (value) => {
  if (value) {
    void loadUsers();
    void loadConversations();
    if (activeConversationKey.value) void loadMessagesForConversation(activeConversationKey.value);
  }
});

watch(open, (value) => {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
  if (!value) {
    scheduleClosedUnreadRefresh();
    return;
  }
  if (closedRefreshTimer) {
    clearTimeout(closedRefreshTimer);
    closedRefreshTimer = null;
  }
  pollTimer = setInterval(() => {
    void loadConversations();
    if (activeConversationKey.value) void loadMessagesForConversation(activeConversationKey.value);
  }, 12000);
}, { immediate: true });

function scheduleClosedUnreadRefresh() {
  if (closedRefreshTimer) clearTimeout(closedRefreshTimer);
  if (open.value || !canUseMessages.value || document.visibilityState !== 'visible') return;
  closedRefreshTimer = setTimeout(() => {
    closedRefreshTimer = null;
    const refresh = () => {
      if (!open.value && canUseMessages.value && document.visibilityState === 'visible') {
        void loadConversations().finally(scheduleClosedUnreadRefresh);
      }
    };
    if ('requestIdleCallback' in window) window.requestIdleCallback(refresh, { timeout: 4000 });
    else setTimeout(refresh, 1000);
  }, 45000);
}

function handleVisibilityChange() {
  if (document.visibilityState === 'visible') scheduleClosedUnreadRefresh();
  else if (closedRefreshTimer) {
    clearTimeout(closedRefreshTimer);
    closedRefreshTimer = null;
  }
}

watch(canUseMessages, (value) => {
  // Establish the unread badge once after authoritative initialization. The
  // full conversation list then refreshes while its progressive-disclosure
  // panel is open, so background polling cannot contend with page navigation.
  if (value) void loadConversations().finally(scheduleClosedUnreadRefresh);
}, { immediate: true });

document.addEventListener('visibilitychange', handleVisibilityChange);

onUnmounted(() => {
  if (userSearchTimer) clearTimeout(userSearchTimer);
  if (pollTimer) clearInterval(pollTimer);
  if (closedRefreshTimer) clearTimeout(closedRefreshTimer);
  document.removeEventListener('visibilitychange', handleVisibilityChange);
});
</script>

<style scoped>
.global-message {
  position: relative;
}

.global-message__trigger {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.global-message__trigger {
  width: 32px;
  min-width: 32px;
  padding: 0;
  justify-content: center;
  border-color: transparent;
  background: transparent;
  color: var(--sc-app-text-secondary);
}

.global-message__label {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}

.global-message__badge {
  position: absolute;
  top: -3px;
  right: -3px;
  margin: 0;
}

.global-message__trigger.active {
  border-color: var(--sc-app-info-border);
  background: var(--sc-app-info-bg);
  color: var(--sc-app-info-text);
}

.global-message__badge {
  margin-left: 4px;
}

:deep(.global-message__panel) {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  width: min(620px, calc(100vw - 16px));
  height: 100dvh;
  padding: 0;
}

.global-message__section-head,
.global-message__thread-head,
.global-message__meta,
.global-message__composer-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.global-message__thread-head h3,
.global-message__thread-head p {
  margin: 0;
}

.global-message__thread-head h3 {
  font-size: 15px;
  line-height: 1.25;
}

.global-message__thread-head p {
  margin-top: 4px;
  font-size: 12px;
  color: var(--sc-app-text-secondary);
}

.global-message__workspace {
  min-height: 0;
  display: grid;
  grid-template-columns: 190px minmax(0, 1fr);
}

.global-message__conversations {
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 8px;
  padding: 10px;
  border-right: 1px solid var(--sc-app-border);
  border-top: none;
  border-left: none;
  border-bottom: none;
  border-radius: 0;
}

.global-message__section-head {
  font-size: 12px;
  font-weight: 700;
}

.global-message__conversation.active {
  border-color: var(--sc-app-info-border);
  background: var(--sc-app-info-bg);
  color: var(--sc-app-info-text);
}

.global-message__conversation-list {
  min-height: 0;
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 0;
  border-radius: var(--sc-component-table-radius);
}

.global-message__conversation {
  position: relative;
  display: grid;
  gap: 4px;
  width: 100%;
  border: none;
  border-left: 3px solid transparent;
  padding: 8px 9px 8px 8px;
  text-align: left;
  cursor: pointer;
}

.global-message__conversation-title {
  padding-right: 20px;
  font-size: 13px;
  font-weight: 700;
  overflow-wrap: anywhere;
}

.global-message__conversation small {
  color: var(--sc-app-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.global-message__dot {
  position: absolute;
  top: 10px;
  right: 8px;
}

.global-message__thread {
  min-height: 0;
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr) auto;
}

.global-message__thread-head {
  padding: 10px 12px;
  border-bottom: 1px solid var(--sc-app-border);
}

.global-message__recipient-box {
  display: grid;
  gap: 8px;
  padding: 8px 12px;
  border-bottom: 1px solid var(--sc-app-border);
}

.global-message__compose-hint {
  margin: 0;
  font-size: 12px;
}

.global-message__field {
  display: grid;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--sc-app-text-secondary);
}

.global-message__field input,
.global-message__composer textarea {
  width: 100%;
  box-sizing: border-box;
  padding: 8px 10px;
  font: inherit;
}

.global-message__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.global-message__options {
  display: grid;
  gap: 0;
  max-height: 84px;
  overflow: auto;
}

.global-message__options button {
  display: grid;
  gap: 2px;
  width: 100%;
  border: none;
  padding: 7px 8px;
  text-align: left;
  cursor: pointer;
}

.global-message__options button:hover:not(:disabled) {
  background: var(--sc-app-hover-bg);
}

.global-message__options button:disabled {
  opacity: 0.45;
  cursor: default;
}

.global-message__options small {
  color: var(--sc-app-text-secondary);
  overflow-wrap: anywhere;
}

.global-message__items {
  min-height: 0;
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 7px;
  padding: 12px;
}

.global-message__item {
  max-width: 84%;
  border: 1px solid var(--sc-app-border);
  border-radius: var(--sc-component-panel-radius);
  background: var(--sc-app-panel);
  padding: 8px;
}

.global-message__item--outgoing {
  align-self: flex-end;
  border-color: var(--sc-app-info-border);
  background: var(--sc-app-info-bg);
}

.global-message__item p {
  margin: 8px 0 0;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  font-size: 13px;
  line-height: 1.5;
}

.global-message__meta {
  font-size: 12px;
}

.global-message__meta time {
  color: var(--sc-app-text-secondary);
}

.global-message__composer {
  display: grid;
  gap: 8px;
  padding: 10px 12px;
  border-top: 1px solid var(--sc-app-border);
}

.global-message__composer textarea {
  resize: vertical;
  min-height: 56px;
}

.global-message__error {
  margin: 0;
  font-size: 12px;
  padding: 8px 10px;
}

.global-message__empty {
  margin: 20px 0 0;
  font-size: 13px;
  align-self: start;
}

@media (max-width: 720px) {
  :deep(.global-message__panel) {
    width: 100vw;
    height: 100dvh;
    border-radius: 0;
  }

  .global-message__workspace {
    grid-template-columns: 1fr;
  }

  .global-message__conversations {
    max-height: 260px;
    border-right: none;
    border-bottom: 1px solid var(--sc-app-border);
  }
}
</style>
