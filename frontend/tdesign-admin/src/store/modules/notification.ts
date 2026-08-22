import { defineStore } from 'pinia';

import type { GlobalMessageConversation, OdooNotificationRecord } from '@/api/odoo';
import {
  fetchGlobalMessageConversations,
  listNotifications,
  markGlobalMessagesRead,
  markNotificationRead,
} from '@/api/odoo';
import type { NotificationItem } from '@/types/interface';

function stripHtml(value: unknown) {
  return String(value || '')
    .replace(/<br\s*\/?>(\r?\n)?/gi, '\n')
    .replace(/<[^>]+>/g, '')
    .replace(/&nbsp;/gi, ' ')
    .trim();
}

function relationName(value: unknown) {
  if (Array.isArray(value) && value.length > 1) return String(value[1] || '');
  if (value && typeof value === 'object') {
    const row = value as Record<string, unknown>;
    return String(row.display_name || row.name || row.label || '');
  }
  return '';
}

function normalizeNotification(row: OdooNotificationRecord): NotificationItem {
  const subject = String(row.sc_subject || '').trim();
  const content = stripHtml(row.sc_body) || stripHtml(subject) || '系统通知';
  const type = subject === '[SC_GLOBAL_MESSAGE]' ? '站内消息' : row.sc_record_name ? '业务通知' : '系统通知';
  const sourceId = Number(row.sc_source_res_id || 0) || undefined;
  return {
    id: String(row.id),
    content,
    type,
    status: row.is_read !== true,
    collected: false,
    date: String(row.sc_message_date || ''),
    quality: row.is_read === true ? 'middle' : 'high',
    recordName: String(row.sc_record_name || '') || undefined,
    sourceModel: String(row.sc_source_model || '') || undefined,
    sourceId,
    authorName: relationName(row.author_id) || undefined,
  };
}

export const useNotificationStore = defineStore('notification', {
  state: () => ({
    msgData: [] as NotificationItem[],
    globalConversations: [] as GlobalMessageConversation[],
    globalMessageLoaded: false,
    loading: false,
    error: '',
  }),
  getters: {
    unreadMsg: (state) => state.msgData.filter((item) => item.status),
    readMsg: (state) => state.msgData.filter((item) => !item.status),
    visibleUnreadNotifications: (state) =>
      state.msgData.filter((item) => item.status && (!state.globalMessageLoaded || item.type !== '站内消息')),
    globalUnreadCount: (state) =>
      state.globalConversations.reduce((total, item) => total + Number(item.unread_count || 0), 0),
    totalUnread: (state) =>
      state.msgData.filter((item) => item.status && (!state.globalMessageLoaded || item.type !== '站内消息')).length +
      state.globalConversations.reduce((total, item) => total + Number(item.unread_count || 0), 0),
  },
  actions: {
    setMsgData(data: NotificationItem[]) {
      this.msgData = data;
    },
    async refreshMsgData() {
      if (!localStorage.getItem('sc-odoo-token')) {
        this.msgData = [];
        this.globalConversations = [];
        this.globalMessageLoaded = false;
        return;
      }
      this.loading = true;
      this.error = '';
      const [notificationResult, conversationResult] = await Promise.allSettled([
        listNotifications(),
        fetchGlobalMessageConversations({ limit: 50 }),
      ]);
      const errors: string[] = [];
      if (notificationResult.status === 'fulfilled') {
        const records = notificationResult.value.records || notificationResult.value.rows || [];
        this.msgData = records.map((row) => normalizeNotification(row as unknown as OdooNotificationRecord));
      } else {
        errors.push(notificationResult.reason instanceof Error ? notificationResult.reason.message : '通知加载失败');
      }
      if (conversationResult.status === 'fulfilled') {
        this.globalConversations = conversationResult.value.items || [];
        this.globalMessageLoaded = true;
      } else {
        this.globalConversations = [];
        this.globalMessageLoaded = false;
        errors.push(conversationResult.reason instanceof Error ? conversationResult.reason.message : '会话加载失败');
      }
      if (errors.length === 2) this.error = errors.join('；');
      this.loading = false;
    },
    async setRead(item: NotificationItem, read = false) {
      await markNotificationRead(Number(item.id), read);
      const target = this.msgData.find((entry) => entry.id === item.id);
      if (target) target.status = !read;
    },
    async setAllRead() {
      const unread = this.unreadMsg.slice();
      await Promise.all(unread.map((item) => markNotificationRead(Number(item.id), true)));
      this.msgData.forEach((item) => {
        item.status = false;
      });
    },
    async setConversationRead(conversationKey: string) {
      if (!conversationKey) return;
      await markGlobalMessagesRead({ conversationKey });
      const target = this.globalConversations.find((item) => item.key === conversationKey);
      if (target) target.unread_count = 0;
    },
    async setAllConversationsRead() {
      await markGlobalMessagesRead({});
      this.globalConversations.forEach((item) => {
        item.unread_count = 0;
      });
    },
  },
  persist: false,
});
