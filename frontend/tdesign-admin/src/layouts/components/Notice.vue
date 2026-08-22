<template>
  <t-popup expand-animation placement="bottom-right" trigger="click">
    <template #content>
      <div class="header-msg">
        <div class="header-msg-top">
          <p>{{ t('layout.notice.title') }}</p>
          <t-button v-if="totalUnread > 0" class="clear-btn" variant="text" theme="primary" @click="setAllRead">{{
            t('layout.notice.clear')
          }}</t-button>
        </div>
        <div v-if="loading" class="notice-loading"><t-loading size="small" /> 正在加载通知</div>
        <t-alert v-else-if="error" theme="warning" :message="error" />
        <t-list v-else-if="noticeRows.length > 0" class="narrow-scrollbar" :split="false">
          <t-list-item v-for="item in noticeRows" :key="item.key" @click="openNotice(item)">
            <div>
              <p class="msg-content">{{ item.content }}</p>
              <p class="msg-type">
                {{ item.type }}<span v-if="item.recordName"> · {{ item.recordName }}</span>
              </p>
            </div>
            <p class="msg-time">{{ item.date }}</p>
            <template #action>
              <t-button size="small" variant="outline" @click="setRead(item)">
                {{ t('layout.notice.setRead') }}
              </t-button>
            </template>
          </t-list-item>
        </t-list>

        <div v-else class="empty-list">
          <empty-icon class="empty-list__icon" aria-hidden="true" />
          <p>{{ t('layout.notice.empty') }}</p>
        </div>
        <div v-if="totalUnread > 0" class="header-msg-bottom">
          <t-button class="header-msg-bottom-link" variant="text" theme="default" block @click="goDetail">{{
            t('layout.notice.viewAll')
          }}</t-button>
        </div>
      </div>
    </template>
    <t-badge :count="totalUnread" :offset="[4, 4]">
      <t-button theme="default" shape="square" variant="text">
        <t-icon name="mail" />
      </t-button>
    </t-badge>
  </t-popup>
</template>
<script setup lang="ts">
import { storeToRefs } from 'pinia';
import { computed, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';

import type { GlobalMessageConversation } from '@/api/odoo';
import EmptyIcon from '@/assets/assets-empty.svg?component';
import { t } from '@/locales';
import { useNotificationStore } from '@/store';
import type { NotificationItem } from '@/types/interface';

const router = useRouter();
const store = useNotificationStore();
const { globalConversations, loading, error, totalUnread, visibleUnreadNotifications } = storeToRefs(store);
let refreshTimer: ReturnType<typeof setInterval> | undefined;

type NoticeRow =
  | (NotificationItem & { key: string })
  | {
      key: string;
      content: string;
      type: string;
      date: string;
      recordName?: string;
      conversationKey: string;
      conversation: GlobalMessageConversation;
    };

const noticeRows = computed<NoticeRow[]>(() => [
  ...visibleUnreadNotifications.value.map((item) => ({ ...item, key: `notification:${item.id}` })),
  ...globalConversations.value
    .filter((item) => Number(item.unread_count || 0) > 0)
    .map((item) => ({
      key: `conversation:${item.key}`,
      content: item.latest_message?.body || '新的站内消息',
      type: '站内会话',
      date: item.latest_message?.date || '',
      conversationKey: item.key,
      conversation: item,
    })),
]);

const setRead = async (item: NoticeRow) => {
  if ('conversationKey' in item) await store.setConversationRead(item.conversationKey);
  else await store.setRead(item, true);
};

const setAllRead = async () => {
  await store.setAllRead();
  await store.setAllConversationsRead();
};

const openNotice = (item: NoticeRow) => {
  if ('conversationKey' in item) {
    void router.push({ path: '/messages', query: { conversation: item.conversationKey } });
    return;
  }
  if (item.sourceModel && item.sourceId) {
    void router.push(`/r/${encodeURIComponent(item.sourceModel)}/${item.sourceId}`);
    return;
  }
  void router.push('/messages');
};

const goDetail = () => {
  router.push('/messages');
};

onMounted(() => {
  void store.refreshMsgData();
  refreshTimer = setInterval(() => void store.refreshMsgData(), 60_000);
});

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer);
});
</script>
<style lang="less" scoped>
.header-msg {
  width: 400px;
  margin: calc(0px - var(--td-comp-paddingTB-xs)) calc(0px - var(--td-comp-paddingLR-s));

  .empty-list {
    text-align: center;
    padding: var(--td-comp-paddingTB-xxl) 0;
    font: var(--td-font-body-medium);
    color: var(--td-text-color-secondary);

    &__icon {
      display: block;
      width: 72px;
      height: 72px;
      margin: 0 auto;
    }

    p {
      margin-top: var(--td-comp-margin-xs);
    }
  }

  .notice-loading {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: var(--td-comp-paddingTB-xxl) 0;
    color: var(--td-text-color-secondary);
  }

  &-top {
    position: relative;
    font: var(--td-font-title-medium);
    color: var(--td-text-color-primary);
    text-align: left;
    padding: var(--td-comp-paddingTB-l) var(--td-comp-paddingLR-xl) 0;
    display: flex;
    align-items: center;
    justify-content: space-between;

    .clear-btn {
      right: calc(var(--td-comp-paddingTB-l) - var(--td-comp-paddingLR-xl));
    }
  }

  &-bottom {
    align-items: center;
    display: flex;
    justify-content: center;
    padding: var(--td-comp-paddingTB-s) var(--td-comp-paddingLR-s);
    border-top: 1px solid var(--td-component-stroke);

    &-link {
      text-decoration: none;
      cursor: pointer;
      color: var(--td-text-color-placeholder);
    }
  }

  .t-list {
    height: calc(100% - 104px);
    padding: var(--td-comp-margin-s) var(--td-comp-margin-s);
  }

  .t-list-item {
    overflow: hidden;
    width: 100%;
    padding: var(--td-comp-paddingTB-l) var(--td-comp-paddingLR-l);
    border-radius: var(--td-radius-default);
    font: var(--td-font-body-medium);
    color: var(--td-text-color-primary);
    cursor: pointer;
    transition: background-color 0.2s linear;

    &:hover {
      background-color: var(--td-bg-color-container-hover);

      .msg-content {
        color: var(--td-brand-color);
      }

      .t-list-item__action {
        button {
          bottom: var(--td-comp-margin-l);
          opacity: 1;
        }
      }

      .msg-time {
        bottom: -6px;
        opacity: 0;
      }
    }

    .msg-content {
      margin-bottom: var(--td-comp-margin-s);
    }

    .msg-type {
      color: var(--td-text-color-secondary);
    }

    .t-list-item__action {
      button {
        opacity: 0;
        position: absolute;
        right: var(--td-comp-margin-xxl);
        bottom: -6px;
      }
    }

    .msg-time {
      transition: all 0.2s ease;
      opacity: 1;
      position: absolute;
      right: var(--td-comp-margin-xxl);
      bottom: var(--td-comp-margin-l);
      color: var(--td-text-color-secondary);
    }
  }
}
</style>
