<template>
  <section
    v-if="renderable"
    class="semantic-form-node"
    :class="[`semantic-form-node--${node.kind}`, `semantic-form-node--${node.role || 'default'}`, { 'is-subordinate': node.zone === 'subordinate', 'is-action-group': isActionGroup }]"
    :data-semantic-role="node.role || undefined"
    :data-semantic-zone="node.zone"
  >
    <template v-if="isNotebook">
      <el-tabs v-model="activePage" class="semantic-form-notebook">
        <el-tab-pane v-for="child in node.children" :key="child.key" :label="child.title || '页面'" :name="child.key">
          <SemanticFormNode
            :node="child"
            :values="values"
            :mode="mode"
            :model="model"
            :record-id="recordId"
            :context="context"
            :field-state="fieldState"
            :onchange="onchange"
            :run-action="runAction"
            :request-edit="requestEdit"
            suppress-title
            :modifier-patch="modifierPatch"
          />
        </el-tab-pane>
      </el-tabs>
    </template>
    <template v-else>
      <header v-if="showContainerTitle" class="semantic-form-node__header">
        <h3>{{ displayTitle }}</h3>
        <p v-if="node.text">{{ node.text }}</p>
        <el-button
          v-if="displayAction"
          size="small"
          type="primary"
          plain
          :disabled="displayAction.enabled === false"
          @click="runNodeAction(displayAction)"
        >{{ displayAction.label }}</el-button>
      </header>
      <div v-else-if="displayAction" class="semantic-form-node__action">
        <el-button size="small" type="primary" plain :disabled="displayAction.enabled === false" @click="runNodeAction(displayAction)">{{ displayAction.label }}</el-button>
      </div>
      <div v-if="displayNativeWidget" class="semantic-form-node__native-widget">{{ node.title || node.nativeWidget }}</div>
      <div
        v-if="node.fields.length"
        class="semantic-form-node__fields"
        :style="{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }"
      >
        <template v-for="(field, index) in node.fields" :key="`${field.code}-${index}`">
          <el-form-item
            v-if="isFieldVisible(field)"
            :label="field.hideLabel ? undefined : field.label"
            :prop="field.code"
            :required="fieldState(field).required"
            :class="{ 'semantic-field--wide': (field.span || 12) >= 24 || ['one2many', 'many2many'].includes(field.type) }"
          >
            <FormFieldControl
              v-model="values[field.code]"
              :field="field"
              :readonly="mode === 'view' || fieldState(field).readonly"
              :allow-view-edit="mode === 'view' && !fieldState(field).readonly && Boolean(recordId)"
              :model="model"
              :record-id="recordId"
              :values="values"
              :context="context"
              :patch="modifierPatch[field.code] || {}"
              @change="onchange(field)"
              @request-edit="requestEdit?.(field, $event)"
            />
          </el-form-item>
        </template>
      </div>
      <div v-if="node.children.length" class="semantic-form-node__children">
        <SemanticFormNode
          v-for="child in node.children"
          :key="child.key"
          :node="child"
          :values="values"
          :mode="mode"
          :model="model"
          :record-id="recordId"
          :context="context"
          :field-state="fieldState"
          :onchange="onchange"
          :run-action="runAction"
          :request-edit="requestEdit"
          :modifier-patch="modifierPatch"
        />
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import FormFieldControl from './FormFieldControl.vue'
import type { BusinessAction, Dictionary, FieldSpec, SemanticFormNode } from '@/types/contracts'

defineOptions({ name: 'SemanticFormNode' })

const props = defineProps<{
  node: SemanticFormNode
  values: Dictionary
  mode: 'view' | 'edit' | 'create'
  model: string
  recordId: number | null
  context: Dictionary
  fieldState: (field: FieldSpec) => { invisible: boolean; readonly: boolean; required: boolean }
  onchange: (field: FieldSpec) => void
  runAction?: (action: BusinessAction) => void | Promise<void>
  requestEdit?: (field: FieldSpec, continueAction?: () => void) => void
  suppressTitle?: boolean
  modifierPatch: Record<string, Dictionary>
}>()

const isNotebook = computed(() => ['notebook', 'notebook_block', 'tabs', 'tabset'].includes(props.node.kind))
const activePage = ref(props.node.children[0]?.key || '')
const columns = computed(() => Math.max(1, Math.min(3, props.node.columns || 1)))
const displayTitle = computed(() => {
  const title = props.suppressTitle ? '' : props.node.title.trim()
  return title && !['form', 'sheet', 'root', 'container'].includes(title.toLowerCase()) ? title : ''
})
const displayAction = computed(() => {
  const action = props.node.action
  if (!action) return undefined
  const actionOnly = !props.node.fields.length && !props.node.children.length
  if (!actionOnly && displayTitle.value && action.label.trim() === displayTitle.value.trim()) return undefined
  return action
})
const displayNativeWidget = computed(() => {
  const widget = String(props.node.nativeWidget || '').trim()
  return Boolean(widget && !/^(sc_insight_banner|web_ribbon)$/i.test(widget))
})
function hasVisibleContent(node: SemanticFormNode): boolean {
  return node.fields.some((field) => !field.hidden && !props.fieldState(field).invisible)
    || node.children.some(hasVisibleContent)
    || Boolean(node.action)
    || Boolean(node.nativeWidget && !/^(sc_insight_banner|web_ribbon)$/i.test(node.nativeWidget))
    || Boolean(node.text.trim())
}
const showContainerTitle = computed(() => Boolean(displayTitle.value && (props.node.fields.some((field) => !field.hidden && !props.fieldState(field).invisible) || props.node.children.some(hasVisibleContent))))
const isActionGroup = computed(() => Boolean(!props.node.fields.length && props.node.children.length && props.node.children.every((child) => !child.fields.length && !child.children.length && Boolean(child.action))))
function runNodeAction(action: BusinessAction) {
  if (props.runAction) void props.runAction(action)
}
function isFieldVisible(field: FieldSpec) {
  if (/^chatter\.field\.\d+$/i.test(field.code)) return false
  if (props.fieldState(field).invisible) return false
  return true
}
function hasRenderableContent(node: SemanticFormNode): boolean {
  if (!node.visible) return false
  if (node.fields.some((field) => isFieldVisible(field))) return true
  if (node.children.some((child) => hasRenderableContent(child))) return true
  return Boolean(node.action || (node.nativeWidget && !/^(sc_insight_banner|web_ribbon)$/i.test(node.nativeWidget)) || node.text)
}
const renderable = computed(() => hasRenderableContent(props.node))
</script>

<style scoped>
.semantic-form-node { min-width: 0; max-width: 100%; }
.semantic-form-node + .semantic-form-node { margin-top: 10px; }
.semantic-form-node__header { margin: 0 0 6px; }
.semantic-form-node__header h3 { margin: 0; color: var(--el-text-color-primary); font-size: 16px; font-weight: 600; }
.semantic-form-node__header p { margin: 4px 0 0; color: var(--el-text-color-secondary); font-size: 13px; }
.semantic-form-node__fields { display: grid; gap: 2px 20px; min-width: 0; }
.semantic-form-node__fields :deep(.el-form-item) { min-width: 0; margin-bottom: 9px; }
.semantic-form-node__fields :deep(.semantic-field--wide) { grid-column: 1 / -1; }
.semantic-form-node__children { min-width: 0; }
.semantic-form-node.is-action-group { display: flex; align-items: center; flex-wrap: wrap; gap: 6px 8px; margin-top: 4px; }
.semantic-form-node.is-action-group > .semantic-form-node__children { display: flex; align-items: center; flex-wrap: wrap; gap: 6px 8px; }
.semantic-form-node.is-action-group .semantic-form-node + .semantic-form-node { margin-top: 0; }
.semantic-form-node--button,
.semantic-form-node--action { display: inline-flex; margin: 0 8px 6px 0; vertical-align: middle; }
.semantic-form-node--button .semantic-form-node__action,
.semantic-form-node--action .semantic-form-node__action { margin: 0; }
.semantic-form-node--summary { padding-bottom: 4px; }
.semantic-form-node--risk { border-left: 3px solid var(--el-color-warning); padding-left: 12px; }
.semantic-form-node--audit,
.semantic-form-node--relation,
.semantic-form-node.is-subordinate { border-top: 1px solid var(--el-border-color-lighter); padding-top: 16px; }
.semantic-form-notebook { min-width: 0; }
.semantic-form-notebook :deep(.el-tabs__content) { overflow: visible; }
@media (max-width: 900px) {
  .semantic-form-node__fields { grid-template-columns: minmax(0, 1fr) !important; }
}
</style>
