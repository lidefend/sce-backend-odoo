<template>
  <el-card v-loading="loading" shadow="never" class="scene-block" :class="`scene-block--${kind}`">
    <template #header><div class="block-header"><div><strong>{{ title }}</strong><small v-if="subtitle">{{ subtitle }}</small></div><el-button v-if="block.action" link type="primary" @click="runAction(block.action)">{{ block.action.label || '打开' }}</el-button></div></template>
    <el-alert v-if="error" :title="error" type="warning" show-icon :closable="false" />
    <div v-else-if="isMetric" class="metric-content"><strong>{{ metricValue }}</strong><span>{{ metricLabel }}</span><el-progress v-if="progress !== null" :percentage="progress" :status="progress >= 100 ? 'success' : undefined" /></div>
    <div v-else-if="isEntryGrid" class="entry-grid"><el-button v-for="item in items" :key="item.key || item.id || item.label" plain @click="runAction(item)"><span>{{ item.label || item.title || item.name }}</span><small>{{ item.help || item.description || '' }}</small></el-button></div>
    <el-table v-else-if="isTable" :data="rows" size="small" stripe><el-table-column v-for="column in columns" :key="column.key" :prop="column.key" :label="column.label" show-overflow-tooltip /><el-table-column v-if="rows.length" label="操作" width="80"><template #default="{row}"><el-button link type="primary" @click="openRow(row)">打开</el-button></template></el-table-column><template #empty><el-empty description="暂无数据" :image-size="54" /></template></el-table>
    <div v-else-if="isKanban" class="kanban"><el-card v-for="item in rows" :key="item.id || item.key" shadow="hover" @click="openRow(item)"><strong>{{ item.title || item.name || item.display_name }}</strong><small>{{ item.status || item.state || item.description || '' }}</small></el-card></div>
    <el-collapse v-else-if="kind === 'accordion_group'"><el-collapse-item v-for="item in items" :key="item.key || item.label" :name="item.key || item.label" :title="item.label || item.title"><p>{{ item.description || item.body || item.value }}</p></el-collapse-item></el-collapse>
    <el-timeline v-else-if="kind === 'activity_feed'"><el-timeline-item v-for="item in items" :key="item.key || item.id" :timestamp="item.at || item.date"><strong>{{ item.title || item.label }}</strong><p>{{ item.body || item.description }}</p></el-timeline-item></el-timeline>
    <div v-else-if="isList" class="block-list"><button v-for="item in items" :key="item.key || item.id || item.label" @click="runAction(item)"><el-icon><Warning v-if="isWarning" /><CircleCheck v-else /></el-icon><span><strong>{{ item.label || item.title || item.name }}</strong><small>{{ item.help || item.description || item.body || '' }}</small></span><el-tag v-if="item.status || item.tone" size="small" :type="tagType(item.tone || item.status)">{{ item.status_label || item.status || item.tone }}</el-tag></button></div>
    <div v-else-if="kind === 'record_summary'" class="summary-grid"><div v-for="(value,key) in summary" :key="key"><span>{{ key }}</span><strong>{{ displayValue(value) }}</strong></div></div>
    <el-empty v-else description="当前区块暂无内容" :image-size="60" />
  </el-card>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { CircleCheck, Warning } from '@element-plus/icons-vue'
import { executeButton, intent } from '@/api/odoo'
import type { Dictionary } from '@/types/contracts'
import { usesExecuteButtonIntent } from '@/utils/action'
import { displayValue } from '@/utils/format'
const props = defineProps<{ block: Dictionary }>(); const emit = defineEmits<{ navigate: [target: Dictionary] }>(); const loading = ref(false); const error = ref(''); const runtimeData = ref<Dictionary>({})
const kind = computed(() => String(props.block.block_type || props.block.type || 'record_summary').replace(/_block$/,''));const title=computed(()=>String(props.block.label||props.block.title||props.block.name||kind.value));const subtitle=computed(()=>String(props.block.subtitle||props.block.help||''));const data=computed<Dictionary>(()=>runtimeData.value.data||runtimeData.value||props.block.data||props.block);const items=computed<Dictionary[]>(()=>data.value.items||data.value.rows||props.block.items||[]);const rows=computed<Dictionary[]>(()=>data.value.records||data.value.rows||props.block.rows||items.value);const summary=computed<Dictionary>(()=>data.value.summary||data.value.values||data.value.metrics||{});const columns=computed(()=>{const source=props.block.columns||data.value.columns||[];if(source.length)return source.map((item:Dictionary)=>({key:String(item.key||item.name||item.field),label:String(item.label||item.title||item.name||item.key)}));const keys=[...new Set(rows.value.flatMap((row)=>Object.keys(row).filter((key)=>!['id','key'].includes(key))))].slice(0,6);return keys.map((key)=>({key,label:key}))});const isMetric=computed(()=>/metric|progress_summary/.test(kind.value));const isEntryGrid=computed(()=>/entry_grid|shortcut_grid|action_list/.test(kind.value));const isTable=computed(()=>/table|record_list|relation|native_view_ref|list_block/.test(kind.value));const isKanban=computed(()=>/kanban/.test(kind.value));const isWarning=computed(()=>/warning|alert/.test(kind.value));const isList=computed(()=>/todo|warning|alert|checklist/.test(kind.value));const metricValue=computed(()=>data.value.value??data.value.total??props.block.value??Object.values(summary.value)[0]??'—');const metricLabel=computed(()=>String(data.value.label||props.block.metric_label||''));const progress=computed(()=>{const value=Number(data.value.progress??props.block.progress);return Number.isFinite(value)?Math.max(0,Math.min(100,value)):null})
function tagType(value:unknown):'success'|'warning'|'danger'|'info'{const text=String(value||'').toLowerCase();return/danger|error|blocked|高/.test(text)?'danger':/warning|pending|待/.test(text)?'warning':/success|done|complete/.test(text)?'success':'info'}
async function hydrate(){const deps=props.block.data_deps||props.block.dataDeps;const dep=Array.isArray(deps)?deps[0]:deps;if(!dep||typeof dep!=='object')return;const name=String(dep.intent||dep.query||'');if(!name)return;loading.value=true;try{runtimeData.value=await intent<Dictionary>(name,dep.params||dep.context||{})}catch(cause){error.value=cause instanceof Error?cause.message:'区块数据加载失败'}finally{loading.value=false}}
async function runAction(action:Dictionary){
  if(action.route)return emit('navigate',action)
  const name=String(action.intent||'').trim()
  const button=action.button&&typeof action.button==='object'?action.button:{}
  const model=String(action.model||action.res_model||'').trim()
  const recordId=Number(action.record_id||action.res_id||0)
  if(usesExecuteButtonIntent(name,button)&&model&&recordId>0){
    try{await executeButton({model,recordId,button});ElMessage.success(`${action.label||action.title||'操作'}已完成`);await hydrate()}catch(cause){ElMessage.error(cause instanceof Error?cause.message:'操作失败')}
    return
  }
  if(action.model||action.record_id)return emit('navigate',action)
  if(!name)return
  try{await intent(name,action.params||{});ElMessage.success(`${action.label||action.title||'操作'}已完成`);await hydrate()}catch(cause){ElMessage.error(cause instanceof Error?cause.message:'操作失败')}
}
function openRow(row:Dictionary){emit('navigate',row.target||row)}
onMounted(hydrate)
</script>

<style scoped>.scene-block{height:100%}.block-header{display:flex;justify-content:space-between;align-items:center}.block-header>div{display:grid;gap:3px}.block-header small,.entry-grid small,.kanban small,.block-list small{color:var(--el-text-color-secondary);font-size:12px}.metric-content{display:grid;gap:7px}.metric-content>strong{font-size:30px}.entry-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:8px}.entry-grid .el-button{height:auto;display:flex;justify-content:flex-start;padding:14px}.entry-grid .el-button span{display:grid;text-align:left}.kanban{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:8px}.kanban .el-card{cursor:pointer}.kanban strong,.kanban small{display:block}.block-list{display:grid}.block-list button{display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:10px;padding:11px 4px;border:0;border-bottom:1px solid var(--el-border-color-lighter);background:transparent;text-align:left;cursor:pointer}.block-list span{display:grid}.summary-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}.summary-grid div{display:grid;gap:5px;padding:12px;background:var(--el-fill-color-light)}.summary-grid span{color:var(--el-text-color-secondary);font-size:12px}.summary-grid strong{font-size:18px}</style>
