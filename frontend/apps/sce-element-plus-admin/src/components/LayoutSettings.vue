<template>
  <el-drawer v-model="visible" title="布局设置" size="320px" append-to-body>
    <section class="setting-section">
      <h3>菜单导航设置</h3>
      <div class="nav-previews">
        <el-tooltip content="左侧菜单">
          <button class="nav-preview side" aria-label="左侧菜单" :class="{ active: settings.navMode === 'side' }" @click="update('navMode', 'side')"><i /><b /></button>
        </el-tooltip>
        <el-tooltip content="混合菜单">
          <button class="nav-preview mix" aria-label="混合菜单" :class="{ active: settings.navMode === 'mix' }" @click="update('navMode', 'mix')"><i /><b /></button>
        </el-tooltip>
        <el-tooltip content="顶部菜单">
          <button class="nav-preview top" aria-label="顶部菜单" :class="{ active: settings.navMode === 'top' }" @click="update('navMode', 'top')"><i /><b /></button>
        </el-tooltip>
      </div>
    </section>

    <section class="setting-section">
      <h3>侧栏风格设置</h3>
      <div class="theme-previews">
        <button class="theme-preview dark" aria-label="深色侧栏" :class="{ active: settings.sideTheme === 'dark' }" @click="update('sideTheme', 'dark')"><i /><b /></button>
        <button class="theme-preview light" aria-label="浅色侧栏" :class="{ active: settings.sideTheme === 'light' }" @click="update('sideTheme', 'light')"><i /><b /></button>
      </div>
      <div class="setting-row"><span>主题颜色</span><el-color-picker :model-value="settings.primaryColor" :predefine="colors" @change="updateColor" /></div>
    </section>

    <el-divider />
    <section class="setting-section">
      <h3>系统布局配置</h3>
      <div class="setting-row"><span>开启页签</span><el-switch :model-value="settings.showTabs" @change="updateBoolean('showTabs', $event)" /></div>
      <div class="setting-row"><span>持久化标签页</span><el-switch :model-value="settings.persistTabs" :disabled="!settings.showTabs" @change="updateBoolean('persistTabs', $event)" /></div>
      <div class="setting-row"><span>显示页签图标</span><el-switch :model-value="settings.showTabIcons" :disabled="!settings.showTabs" @change="updateBoolean('showTabIcons', $event)" /></div>
      <div class="setting-row"><span>标签页样式</span><el-segmented :model-value="settings.tabStyle" :options="tabStyles" size="small" :disabled="!settings.showTabs" @change="updateTabStyle" /></div>
      <div class="setting-row"><span>固定 Header</span><el-switch :model-value="settings.fixedHeader" @change="updateBoolean('fixedHeader', $event)" /></div>
      <div class="setting-row"><span>显示 Logo</span><el-switch :model-value="settings.showLogo" @change="updateBoolean('showLogo', $event)" /></div>
      <div class="setting-row"><span>动态标题</span><el-switch :model-value="settings.dynamicTitle" @change="updateBoolean('dynamicTitle', $event)" /></div>
      <div class="setting-row"><span>底部版权</span><el-switch :model-value="settings.showFooter" @change="updateBoolean('showFooter', $event)" /></div>
    </section>

    <template #footer>
      <div class="drawer-footer"><el-button type="primary" plain @click="save"><el-icon><DocumentAdd /></el-icon>保存配置</el-button><el-button @click="reset"><el-icon><Refresh /></el-icon>重置配置</el-button></div>
    </template>
  </el-drawer>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { DocumentAdd, Refresh } from '@element-plus/icons-vue'

import { type LayoutSettings, type TabStyle, useLayoutStore } from '@/stores/layout'

const store = useLayoutStore()
const settings = computed(() => store.settings)
const visible = ref(false)
const colors = ['#409eff', '#1890ff', '#00b96b', '#13c2c2', '#722ed1', '#f5222d', '#fa8c16']
const tabStyles = [{ label: '卡片', value: 'card' }, { label: '谷歌', value: 'chrome' }]

function update<K extends keyof LayoutSettings>(key: K, value: LayoutSettings[K]) { store.update(key, value) }
function updateBoolean(key: 'showTabs' | 'persistTabs' | 'showTabIcons' | 'fixedHeader' | 'showLogo' | 'dynamicTitle' | 'showFooter', value: string | number | boolean) { update(key, Boolean(value)) }
function updateColor(value: string | null) { if (value) update('primaryColor', value) }
function updateTabStyle(value: string | number | boolean) { update('tabStyle', String(value) as TabStyle) }
function open() { visible.value = true }
function save() { store.saveSettings(); ElMessage.success('布局配置已保存') }
function reset() { store.resetSettings(); ElMessage.success('布局配置已重置') }
defineExpose({ open })
</script>

<style scoped>
.setting-section h3{margin:0 0 16px;font-size:14px;color:#303133}.setting-section+.setting-section{margin-top:24px}.nav-previews,.theme-previews{display:flex;gap:16px;margin-bottom:22px}.nav-preview,.theme-preview{position:relative;width:58px;height:48px;padding:0;border:2px solid transparent;border-radius:4px;background:#f0f2f5;cursor:pointer;overflow:hidden}.nav-preview.active,.theme-preview.active{border-color:var(--el-color-primary)}.nav-preview i,.nav-preview b,.theme-preview i,.theme-preview b{display:block;position:absolute}.nav-preview.side i{left:0;top:0;width:30%;height:100%;background:#1f2d3d}.nav-preview.side b{left:30%;top:0;width:70%;height:28%;background:#fff}.nav-preview.mix i{left:0;top:0;width:100%;height:28%;background:#1f2d3d}.nav-preview.mix b{left:0;top:28%;width:30%;height:72%;background:#1f2d3d}.nav-preview.top i{left:0;top:0;width:100%;height:28%;background:#1f2d3d}.theme-preview i{left:0;top:0;width:32%;height:100%}.theme-preview b{left:32%;top:0;width:68%;height:28%}.theme-preview.dark i{background:#1f2d3d}.theme-preview.dark b{background:#fff}.theme-preview.light{background:#fff;border-color:#e4e7ed}.theme-preview.light.active{border-color:var(--el-color-primary)}.theme-preview.light i{background:#fff;border-right:1px solid #dcdfe6}.theme-preview.light b{background:#f5f7fa}.setting-row{min-height:44px;display:flex;align-items:center;justify-content:space-between;color:#606266;font-size:14px}.drawer-footer{display:flex;justify-content:flex-start}
</style>
