<template>
  <div v-if="enabled" class="business-context-switcher">
    <el-dropdown v-if="companyOptions.length" trigger="click" @command="selectCompany">
      <el-button text class="context-button"><el-icon><OfficeBuilding /></el-icon><span>{{ companyLabel }}</span><el-icon><ArrowDown /></el-icon></el-button>
      <template #dropdown><el-dropdown-menu><el-dropdown-item v-for="item in companyOptions" :key="item.company_id" :command="item.company_id" :class="{ active: item.active }">{{ item.company_name || `公司 ${item.company_id}` }}</el-dropdown-item></el-dropdown-menu></template>
    </el-dropdown>
    <el-dropdown v-if="projectSelectorVisible" trigger="click" popper-class="project-context-popper" @visible-change="loadProjects" @command="selectProject">
      <el-button text class="context-button"><el-icon><FolderOpened /></el-icon><span>{{ projectLabel }}</span><el-icon><ArrowDown /></el-icon></el-button>
      <template #dropdown><el-dropdown-menu class="project-context-menu"><el-dropdown-item command="__all__">全部项目</el-dropdown-item><el-dropdown-item v-for="item in projectOptions" :key="item.id" :command="String(item.id)" :class="{ active: item.id === selectedProjectId }"><span class="project-option-label">{{ item.name || item.display_name || item.code || item.id }}</span></el-dropdown-item></el-dropdown-menu></template>
    </el-dropdown>
    <el-dropdown v-if="operationOptions.length" trigger="click" @command="selectOperation">
      <el-button text class="context-button"><el-icon><SetUp /></el-icon><span>{{ operationLabel }}</span><el-icon><ArrowDown /></el-icon></el-button>
      <template #dropdown><el-dropdown-menu><el-dropdown-item v-for="item in operationOptions" :key="String(item.operation_strategy)" :command="String(item.operation_strategy || '__all__')" :disabled="item.disabled === true" :class="{ active: item.active }">{{ item.operation_strategy_label || item.operation_strategy || '全部' }}</el-dropdown-item></el-dropdown-menu></template>
    </el-dropdown>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ArrowDown, FolderOpened, OfficeBuilding, SetUp } from '@element-plus/icons-vue'
import { useSessionStore } from '@/stores/session'
import type { Dictionary } from '@/types/contracts'

const session = useSessionStore()
const refreshing = ref(false)
const contract = computed(() => session.recordContext || {})
const enabled = computed(() => contract.value.enabled !== false && Boolean(companyOptions.value.length || projectOptions.value.length || operationOptions.value.length))
const companyOptions = computed<Dictionary[]>(() => Array.isArray(contract.value.company_options) ? contract.value.company_options : [])
const projectOptions = computed<Dictionary[]>(() => Array.isArray(contract.value.options) ? contract.value.options : [])
const operationOptions = computed<Dictionary[]>(() => Array.isArray(contract.value.operation_options) ? contract.value.operation_options : [])
const projectSelectorVisible = computed(() => contract.value.enabled !== false && Boolean(contract.value.model || projectOptions.value.length))
const selectedProjectId = computed(() => Number(contract.value.selected?.id || 0) || 0)
const companyLabel = computed(() => String(contract.value.company_name || companyOptions.value.find((item) => item.active)?.company_name || session.user?.company_name || '公司'))
const projectLabel = computed(() => String(contract.value.selected?.name || contract.value.selected?.display_name || '全部项目'))
const operationLabel = computed(() => String(contract.value.operation_strategy_label || operationOptions.value.find((item) => item.active)?.operation_strategy_label || '全部'))

async function apply(change: Dictionary) { await session.switchBusinessContext(change); window.location.reload() }
async function selectCompany(companyId: number | string) { await apply({ company_id: Number(companyId), current_project_id: null }) }
async function selectProject(command: string) {
  if (command === '__all__') return apply({ current_project_id: null })
  const option = projectOptions.value.find((item) => String(item.id) === String(command))
  await apply(option?.request_context || { current_project_id: Number(command) })
}
async function selectOperation(command: string) { await apply({ operation_strategy: command === '__all__' ? null : command }) }
async function loadProjects(visible: boolean) {
  if (!visible || refreshing.value) return
  refreshing.value = true
  try { await session.refreshRecordContext() } finally { refreshing.value = false }
}
</script>

<style scoped>
.business-context-switcher{display:inline-flex;align-items:center;gap:2px}.context-button{max-width:180px;padding:8px}.context-button span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.context-button .el-icon:first-child{margin-right:3px}.context-button .el-icon:last-child{margin-left:2px;font-size:11px}.project-option-label{display:block;max-width:280px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
:global(.project-context-popper .project-context-menu){width:320px;max-width:calc(100vw - 24px);height:min(480px,calc(100vh - 120px));max-height:min(480px,calc(100vh - 120px));overflow-x:hidden;overflow-y:auto;overscroll-behavior:contain;scrollbar-gutter:stable}
:global(.project-context-popper .project-context-menu .el-dropdown-menu__item){min-height:36px;padding:0 16px}
:global(.project-context-popper .project-context-menu .project-option-label){display:block;min-width:0;max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
</style>
