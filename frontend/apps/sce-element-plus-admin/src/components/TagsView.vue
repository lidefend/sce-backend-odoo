<template>
  <div class="tags-view" :class="`tags-view--${settings.tabStyle}`">
    <el-button text class="tag-nav-button" :disabled="!canLeft" @click="scroll(-240)"><el-icon><ArrowLeft /></el-icon></el-button>
    <div ref="viewport" class="tags-viewport" @scroll="updateScrollState">
      <div class="tags-track">
        <router-link v-for="tab in tabs" :key="tab.fullPath" :to="tab.fullPath" class="tag-item" :class="{ active: tab.fullPath === route.fullPath }" @contextmenu.prevent="openContextMenu($event, tab)">
          <el-icon v-if="settings.showTabIcons && tab.icon"><component :is="tab.icon" /></el-icon><span>{{ tab.title }}</span>
          <button v-if="tab.closable" class="tag-close" title="关闭页签" @click.prevent.stop="close(tab.fullPath)"><el-icon><Close /></el-icon></button>
        </router-link>
      </div>
    </div>
    <el-button text class="tag-nav-button" :disabled="!canRight" @click="scroll(240)"><el-icon><ArrowRight /></el-icon></el-button>
    <el-dropdown trigger="click" @command="handleCommand"><el-button text class="tag-action-button"><el-icon><ArrowDown /></el-icon></el-button><template #dropdown><el-dropdown-menu><el-dropdown-item command="refresh"><el-icon><Refresh /></el-icon>刷新当前</el-dropdown-item><el-dropdown-item command="others"><el-icon><CircleClose /></el-icon>关闭其他</el-dropdown-item><el-dropdown-item command="all"><el-icon><CloseBold /></el-icon>关闭全部</el-dropdown-item></el-dropdown-menu></template></el-dropdown>
    <el-button text class="tag-refresh-button" @click="refresh"><el-icon><Refresh /></el-icon><span>刷新</span></el-button>
  </div>
  <Teleport to="body">
    <ul v-if="contextMenu.visible" class="tag-context-menu" :style="{ left: `${contextMenu.left}px`, top: `${contextMenu.top}px` }">
      <li @click="runContextCommand('refresh')"><el-icon><Refresh /></el-icon>刷新页面</li>
      <li :class="{ disabled: !contextMenu.tab?.closable }" @click="runContextCommand('close')"><el-icon><Close /></el-icon>关闭当前</li>
      <li @click="runContextCommand('others')"><el-icon><CircleClose /></el-icon>关闭其他</li>
      <li :class="{ disabled: !canCloseLeft }" @click="runContextCommand('left')"><el-icon><ArrowLeft /></el-icon>关闭左侧</li>
      <li :class="{ disabled: !canCloseRight }" @click="runContextCommand('right')"><el-icon><ArrowRight /></el-icon>关闭右侧</li>
      <li @click="runContextCommand('all')"><el-icon><CloseBold /></el-icon>全部关闭</li>
    </ul>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowDown, ArrowLeft, ArrowRight, CircleClose, Close, CloseBold, Refresh } from '@element-plus/icons-vue'
import { useLayoutStore, type VisitedTab } from '@/stores/layout'

const route = useRoute(); const router = useRouter(); const store = useLayoutStore(); const settings = computed(() => store.settings); const tabs = computed(() => store.tabs); const viewport = ref<HTMLElement>(); const canLeft = ref(false); const canRight = ref(false)
const contextMenu = reactive<{ visible: boolean; left: number; top: number; tab: VisitedTab | null }>({ visible: false, left: 0, top: 0, tab: null })
const canCloseLeft = computed(() => { const index = contextMenu.tab ? tabs.value.findIndex((tab) => tab.fullPath === contextMenu.tab?.fullPath) : -1; return index > 0 && tabs.value.slice(0, index).some((tab) => tab.closable) })
const canCloseRight = computed(() => { const index = contextMenu.tab ? tabs.value.findIndex((tab) => tab.fullPath === contextMenu.tab?.fullPath) : -1; return index >= 0 && tabs.value.slice(index + 1).some((tab) => tab.closable) })
function updateScrollState() { const element = viewport.value; if (!element) return; canLeft.value = element.scrollLeft > 2; canRight.value = element.scrollLeft + element.clientWidth < element.scrollWidth - 2 }
function scroll(left: number) { viewport.value?.scrollBy({ left, behavior: 'smooth' }); window.setTimeout(updateScrollState, 250) }
async function close(fullPath: string) { const active = fullPath === route.fullPath; const next = store.closeTab(fullPath); if (active) await router.push(next) }
function refresh() { router.go(0) }
function openContextMenu(event: MouseEvent, tab: VisitedTab) { contextMenu.tab = tab; contextMenu.left = Math.min(event.clientX, window.innerWidth - 175); contextMenu.top = Math.min(event.clientY, window.innerHeight - 220); contextMenu.visible = true }
function closeContextMenu() { contextMenu.visible = false }
async function runContextCommand(command: 'refresh' | 'close' | 'others' | 'left' | 'right' | 'all') { const tab = contextMenu.tab; if (!tab) return closeContextMenu(); if (command === 'refresh') { closeContextMenu(); if (tab.fullPath === route.fullPath) router.go(0); else await router.push(tab.fullPath); return } if (command === 'close') { if (tab.closable) { const active = tab.fullPath === route.fullPath; const next = store.closeTab(tab.fullPath); closeContextMenu(); if (active) await router.push(next) } else closeContextMenu(); return } if (command === 'others') { store.closeOtherTabs(tab.fullPath); closeContextMenu(); if (tab.fullPath !== route.fullPath) await router.push(tab.fullPath); return } if (command === 'left') { if (canCloseLeft.value) store.closeLeftTabs(tab.fullPath); closeContextMenu(); return } if (command === 'right') { if (canCloseRight.value) store.closeRightTabs(tab.fullPath); closeContextMenu(); return } store.closeAllTabs(); closeContextMenu(); await router.push('/dashboard') }
async function handleCommand(command: string) { if (command === 'refresh') return refresh(); if (command === 'others') store.closeOtherTabs(route.fullPath); if (command === 'all') { store.closeAllTabs(); await router.push('/dashboard') } }
watch([tabs, () => route.fullPath], () => nextTick(() => { const active = viewport.value?.querySelector('.tag-item.active') as HTMLElement | null; active?.scrollIntoView({ block: 'nearest', inline: 'nearest' }); updateScrollState() }), { deep: true })
onMounted(updateScrollState); onMounted(() => document.addEventListener('click', closeContextMenu)); onBeforeUnmount(() => document.removeEventListener('click', closeContextMenu))
</script>

<style scoped>
.tags-view{height:36px;display:flex;align-items:center;background:#fff;border-bottom:1px solid var(--el-border-color-lighter);overflow:hidden}.tags-viewport{flex:1;min-width:0;height:100%;overflow-x:auto;overflow-y:hidden;scrollbar-width:none}.tags-viewport::-webkit-scrollbar{display:none}.tags-track{display:inline-flex;align-items:flex-end;min-width:100%;height:100%;white-space:nowrap}.tag-item{height:28px;display:inline-flex;align-items:center;gap:5px;padding:0 10px;margin-left:5px;color:#606266;font-size:12px;text-decoration:none;border:1px solid #d8dce5;border-radius:3px;background:#fff}.tag-item.active{color:#fff;background:var(--el-color-primary);border-color:var(--el-color-primary)}.tag-close{width:15px;height:15px;display:inline-grid;place-items:center;padding:0;border:0;border-radius:50%;color:inherit;background:transparent;cursor:pointer}.tag-close:hover{color:#fff;background:rgba(0,0,0,.22)}.tag-nav-button,.tag-action-button{width:30px;height:36px;margin:0!important;border-radius:0;border-right:1px solid var(--el-border-color-lighter)}.tag-action-button{border-left:1px solid var(--el-border-color-lighter);border-right:0}.tag-refresh-button{height:36px;margin:0!important;border-radius:0;border-left:1px solid var(--el-border-color-lighter);font-size:12px}.tags-view--chrome .tags-track{align-items:flex-end}.tags-view--chrome .tag-item{position:relative;height:32px;margin:0;padding:0 14px;border:0;border-radius:0;background:transparent;font-size:13px}.tags-view--chrome .tag-item+.tag-item:not(.active){border-left:1px solid var(--el-border-color-lighter)}.tags-view--chrome .tag-item.active{color:var(--el-color-primary);background:var(--el-color-primary-light-9);border-radius:8px 8px 0 0}.tags-view--chrome .tag-item.active::before,.tags-view--chrome .tag-item.active::after{content:'';position:absolute;bottom:0;width:8px;height:8px}.tags-view--chrome .tag-item.active::before{left:-8px;border-bottom-right-radius:8px;box-shadow:4px 4px 0 4px var(--el-color-primary-light-9)}.tags-view--chrome .tag-item.active::after{right:-8px;border-bottom-left-radius:8px;box-shadow:-4px 4px 0 4px var(--el-color-primary-light-9)}.tags-view--chrome .tag-item.active+.tag-item{margin-left:8px}.tags-view--chrome .tag-close:hover{background:var(--el-color-primary-light-5)}.tag-context-menu{position:fixed;z-index:4000;min-width:150px;margin:0;padding:5px 0;border:1px solid var(--el-border-color-light);border-radius:4px;background:var(--el-bg-color-overlay);box-shadow:0 2px 12px rgba(0,0,0,.15);list-style:none}.tag-context-menu li{display:flex;align-items:center;gap:8px;height:32px;padding:0 14px;color:var(--el-text-color-regular);font-size:13px;cursor:pointer;white-space:nowrap}.tag-context-menu li:hover{background:var(--el-fill-color-light);color:var(--el-color-primary)}.tag-context-menu li.disabled{color:var(--el-text-color-placeholder);cursor:not-allowed}.tag-context-menu li.disabled:hover{background:transparent;color:var(--el-text-color-placeholder)}
</style>
