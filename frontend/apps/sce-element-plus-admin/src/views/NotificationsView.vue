<template>
  <div class="notification-page">
    <div class="page-heading">
      <div>
        <h1>消息中心</h1>
        <p>查看发送给当前账号的业务消息和关联单据提醒。</p>
      </div>
      <div class="heading-actions">
        <el-button :disabled="!unreadCount" :loading="markingAll" @click="markAllRead">全部已读</el-button>
        <el-button :icon="Refresh" :loading="loading" @click="load">刷新</el-button>
      </div>
    </div>

    <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" />

    <section class="notification-surface">
      <div class="notification-toolbar">
        <el-segmented v-model="filter" :options="filterOptions" />
        <el-input v-model="search" clearable placeholder="搜索主题、内容或关联单据" :prefix-icon="Search" />
        <span class="unread-summary">{{ unreadCount }} 条未读</span>
      </div>

      <el-skeleton v-if="loading && !items.length" :rows="6" animated />
      <el-empty v-else-if="!filteredItems.length" description="暂无符合条件的消息" :image-size="90" />
      <div v-else class="notification-list">
        <article
          v-for="item in filteredItems"
          :key="item.id"
          class="notification-item"
          :class="{ unread: !item.is_read }"
          @click="openNotification(item)"
        >
          <span class="status-dot" aria-hidden="true" />
          <div class="notification-copy">
            <div class="notification-title">
              <strong>{{ item.sc_subject || item.sc_record_name || '业务消息' }}</strong>
              <el-tag v-if="!item.is_read" size="small" type="primary" effect="light">未读</el-tag>
            </div>
            <p>{{ plainText(item.sc_body) || '暂无消息内容' }}</p>
            <div class="notification-meta">
              <span v-if="relationLabel(item.author_id)">发送人：{{ relationLabel(item.author_id) }}</span>
              <span v-if="item.sc_record_name">关联：{{ item.sc_record_name }}</span>
              <time>{{ formatDate(item.sc_message_date) }}</time>
            </div>
          </div>
          <div class="notification-actions" @click.stop>
            <el-button
              v-if="item.sc_source_model && item.sc_source_res_id"
              link
              type="primary"
              @click="openNotification(item)"
            >打开单据</el-button>
            <el-button link @click="toggleRead(item)">{{ item.is_read ? '标记未读' : '标记已读' }}</el-button>
          </div>
        </article>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onActivated, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Refresh, Search } from '@element-plus/icons-vue'

import { listNotifications, setNotificationRead } from '@/api/odoo'
import type { Dictionary } from '@/types/contracts'

type NotificationFilter = 'all' | 'unread' | 'read'

const router = useRouter()
const items = ref<Dictionary[]>([])
const filter = ref<NotificationFilter>('all')
const search = ref('')
const loading = ref(false)
const markingAll = ref(false)
const error = ref('')
const loaded = ref(false)
const filterOptions = [
  { label: '全部', value: 'all' },
  { label: '未读', value: 'unread' },
  { label: '已读', value: 'read' },
]
const unreadCount = computed(() => items.value.filter((item) => !item.is_read).length)
const filteredItems = computed(() => {
  const keyword = search.value.trim().toLowerCase()
  return items.value.filter((item) => {
    if (filter.value === 'unread' && item.is_read) return false
    if (filter.value === 'read' && !item.is_read) return false
    if (!keyword) return true
    return [item.sc_subject, plainText(item.sc_body), item.sc_record_name, relationLabel(item.author_id)]
      .join(' ')
      .toLowerCase()
      .includes(keyword)
  })
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    const result = await listNotifications(100)
    items.value = result.records || result.rows || []
    loaded.value = true
    emitUnreadCount()
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '消息加载失败'
  } finally {
    loading.value = false
  }
}

async function toggleRead(item: Dictionary) {
  const read = !item.is_read
  await setNotificationRead(Number(item.id), read)
  item.is_read = read
  emitUnreadCount()
  ElMessage.success(read ? '已标记为已读' : '已标记为未读')
}

async function markAllRead() {
  const unread = items.value.filter((item) => !item.is_read)
  if (!unread.length) return
  markingAll.value = true
  try {
    await Promise.all(unread.map((item) => setNotificationRead(Number(item.id), true)))
    unread.forEach((item) => { item.is_read = true })
    emitUnreadCount()
    ElMessage.success('全部消息已标记为已读')
  } finally {
    markingAll.value = false
  }
}

async function openNotification(item: Dictionary) {
  if (!item.is_read) {
    await setNotificationRead(Number(item.id), true)
    item.is_read = true
    emitUnreadCount()
  }
  const model = String(item.sc_source_model || '')
  const id = Number(item.sc_source_res_id || 0)
  if (model && id) {
    await router.push({ name: 'Record', params: { model, id }, query: { mode: 'view' } })
  }
}

function plainText(value: unknown) {
  const html = String(value || '')
  if (!html) return ''
  const container = document.createElement('div')
  container.innerHTML = html
  return (container.textContent || '').replace(/\s+/g, ' ').trim()
}

function relationLabel(value: unknown) {
  if (Array.isArray(value)) return String(value[1] || value[0] || '')
  if (value && typeof value === 'object') {
    const row = value as Dictionary
    return String(row.display_name || row.name || row.label || '')
  }
  return value ? String(value) : ''
}

function formatDate(value: unknown) {
  const text = String(value || '')
  return text ? text.replace('T', ' ').replace('Z', '').slice(0, 19) : ''
}

function emitUnreadCount() {
  window.dispatchEvent(new CustomEvent('sce:notifications-updated', { detail: { unread: unreadCount.value } }))
}

onMounted(load)
onActivated(() => { if (loaded.value) void load() })
</script>

<style scoped>
.notification-page { display: grid; gap: 18px; max-width: 1180px; margin: 0 auto; }
.page-heading { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; }
.page-heading h1 { margin: 0 0 7px; font-size: 25px; }
.page-heading p { margin: 0; color: var(--el-text-color-secondary); }
.heading-actions { display: flex; gap: 8px; }
.notification-surface { min-height: 420px; padding: 20px 24px; background: #fff; border-radius: 4px; }
.notification-toolbar { display: grid; grid-template-columns: auto minmax(220px, 420px) 1fr; align-items: center; gap: 14px; padding-bottom: 16px; border-bottom: 1px solid var(--el-border-color-lighter); }
.unread-summary { justify-self: end; color: var(--el-text-color-secondary); font-size: 13px; }
.notification-list { display: grid; }
.notification-item { display: grid; grid-template-columns: 10px minmax(0, 1fr) auto; gap: 12px; align-items: start; min-height: 104px; padding: 18px 4px; border-bottom: 1px solid var(--el-border-color-lighter); cursor: pointer; }
.notification-item:hover { background: var(--el-fill-color-extra-light); }
.status-dot { width: 7px; height: 7px; margin-top: 7px; border-radius: 50%; background: var(--el-border-color); }
.notification-item.unread .status-dot { background: var(--el-color-primary); }
.notification-item.unread .notification-title strong { color: var(--el-text-color-primary); }
.notification-copy { min-width: 0; }
.notification-title { display: flex; align-items: center; gap: 8px; }
.notification-copy p { display: -webkit-box; overflow: hidden; margin: 8px 0; color: var(--el-text-color-regular); line-height: 1.6; -webkit-box-orient: vertical; -webkit-line-clamp: 2; }
.notification-meta { display: flex; flex-wrap: wrap; gap: 6px 18px; color: var(--el-text-color-secondary); font-size: 12px; }
.notification-actions { display: flex; gap: 4px; padding-top: 1px; }
@media (max-width: 760px) {
  .page-heading { align-items: stretch; flex-direction: column; }
  .heading-actions .el-button { flex: 1; }
  .notification-surface { padding: 16px; }
  .notification-toolbar { grid-template-columns: 1fr; }
  .unread-summary { justify-self: start; }
  .notification-item { grid-template-columns: 10px minmax(0, 1fr); }
  .notification-actions { grid-column: 2; }
}
</style>
