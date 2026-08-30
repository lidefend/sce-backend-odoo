<template>
  <div class="semantic-record-form" :class="`semantic-record-form--${model.presentationMode}`">
    <template v-if="model.presentationMode === 'task'">
      <section v-if="summaryNodes.length" class="semantic-zone semantic-zone--summary">
        <SemanticFormNode v-for="node in summaryNodes" :key="node.key" v-bind="nodeBindings(node)" />
      </section>
      <div class="semantic-task-layout">
        <main class="semantic-zone semantic-zone--task">
          <SemanticFormNode v-for="node in taskNodes" :key="node.key" v-bind="nodeBindings(node)" />
        </main>
        <aside v-if="contextNodes.length" class="semantic-zone semantic-zone--context">
          <SemanticFormNode v-for="node in contextNodes" :key="node.key" v-bind="nodeBindings(node)" />
        </aside>
      </div>
      <section v-if="riskNodes.length" class="semantic-zone semantic-zone--risk">
        <SemanticFormNode v-for="node in riskNodes" :key="node.key" v-bind="nodeBindings(node)" />
      </section>
      <section v-if="nativeNotebookNodes.length" class="semantic-zone semantic-zone--relation">
        <SemanticFormNode v-for="node in nativeNotebookNodes" :key="node.key" v-bind="nodeBindings(node)" />
      </section>
    </template>
    <section v-else class="semantic-zone semantic-zone--workspace">
      <SemanticFormNode v-for="node in model.primaryNodes" :key="node.key" v-bind="nodeBindings(node)" />
    </section>
    <section v-if="relationNodes.length" class="semantic-zone semantic-zone--relation">
      <SemanticFormNode v-for="node in relationNodes" :key="node.key" v-bind="nodeBindings(node)" />
    </section>
    <section v-if="subordinateNodes.length" class="semantic-zone semantic-zone--subordinate">
      <SemanticFormNode v-for="node in subordinateNodes" :key="node.key" v-bind="nodeBindings(node)" />
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import SemanticFormNode from './SemanticFormNode.vue'
import type { BusinessAction, Dictionary, FieldSpec, SemanticFormModel, SemanticFormNode as SemanticNode } from '@/types/contracts'

const props = defineProps<{
  model: SemanticFormModel
  values: Dictionary
  mode: 'view' | 'edit' | 'create'
  recordModel: string
  recordId: number | null
  context: Dictionary
  fieldState: (field: FieldSpec) => { invisible: boolean; readonly: boolean; required: boolean }
  onchange: (field: FieldSpec) => void
  requestEdit?: (field: FieldSpec, continueAction?: () => void) => void
  runAction: (action: BusinessAction) => void | Promise<void>
  modifierPatch: Record<string, Dictionary>
}>()

function projectNode(node: SemanticNode, roles: Set<string>, includeUnassigned = false, inheritedRole = '', excludeNotebook = false): SemanticNode | null {
  if (excludeNotebook && ['notebook', 'notebook_block', 'tabs', 'tabset'].includes(node.kind)) return null
  const nodeRole = node.role || inheritedRole
  const fields = node.fields.filter((field) => {
    const fieldRole = field.semanticRole || nodeRole
    return roles.has(fieldRole || '') || (includeUnassigned && !fieldRole)
  })
  const children = node.children
    .map((child) => projectNode(child, roles, includeUnassigned, nodeRole, excludeNotebook))
    .filter((child): child is SemanticNode => Boolean(child))
  if (!node.visible || (!fields.length && !children.length && !node.text && !node.action && !node.nativeWidget)) return null
  return { ...node, fields, children }
}

function project(roles: string[], includeUnassigned = false, excludeNotebook = false): SemanticNode[] {
  const roleSet = new Set(roles)
  return props.model.primaryNodes
    .map((node) => projectNode(node, roleSet, includeUnassigned, '', excludeNotebook))
    .filter((node): node is SemanticNode => Boolean(node))
}

const summaryNodes = computed(() => project(['summary']))
const riskNodes = computed(() => project(['risk']))
const contextNodes = computed(() => project(['context', 'audit', 'activity']))
function collectNotebooks(nodes: SemanticNode[]): SemanticNode[] {
  return nodes.flatMap((node) => {
    if (['notebook', 'notebook_block', 'tabs', 'tabset'].includes(node.kind)) return [node]
    return collectNotebooks(node.children)
  })
}
const nativeNotebookNodes = computed(() => props.model.presentationMode === 'task' ? collectNotebooks(props.model.primaryNodes) : [])
const relationNodes = computed(() => props.model.presentationMode === 'task' && !nativeNotebookNodes.value.length ? [
  ...project(['relation']),
  ...props.model.subordinateNodes
    .map((node) => projectNode(node, new Set(['relation'])))
    .filter((node): node is SemanticNode => Boolean(node)),
] : [])
const taskNodes = computed(() => project(['task'], true, true))
const subordinateNodes = computed(() => props.model.subordinateNodes
  .map((node) => projectNode(node, new Set(['summary', 'task', 'context', 'risk', 'audit', 'activity']), true))
  .filter((node): node is SemanticNode => Boolean(node)))

function nodeBindings(node: SemanticNode) {
  return {
    node,
    values: props.values,
    mode: props.mode,
    model: props.recordModel,
    recordId: props.recordId,
    context: props.context,
    fieldState: props.fieldState,
    onchange: props.onchange,
    requestEdit: props.requestEdit,
    runAction: props.runAction,
    modifierPatch: props.modifierPatch,
  }
}
</script>

<style scoped>
.semantic-record-form { min-width: 0; max-width: 100%; }
.semantic-zone { min-width: 0; max-width: 100%; }
.semantic-zone + .semantic-zone { margin-top: 20px; }
.semantic-task-layout { display: grid; grid-template-columns: minmax(0, 2fr) minmax(260px, .8fr); gap: 24px; align-items: start; }
.semantic-zone--context { padding-left: 20px; border-left: 1px solid var(--el-border-color-lighter); }
.semantic-zone--summary { padding: 14px 16px; background: var(--el-fill-color-lighter); border-radius: 4px; }
.semantic-zone--risk { padding: 14px 16px; background: var(--el-color-warning-light-9); border-radius: 4px; }
.semantic-zone--relation,
.semantic-zone--subordinate { padding-top: 18px; border-top: 1px solid var(--el-border-color-lighter); }
@media (max-width: 1100px) {
  .semantic-task-layout { grid-template-columns: minmax(0, 1fr); }
  .semantic-zone--context { padding-left: 0; padding-top: 18px; border-left: 0; border-top: 1px solid var(--el-border-color-lighter); }
}
</style>
