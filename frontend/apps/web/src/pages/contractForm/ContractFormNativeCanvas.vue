<template>
  <section v-if="showDefaultSectionTitle || mode !== 'readonly'" class="native-default-section-head">
    <div>
      <h3>{{ mode === 'create' ? '填写业务信息' : mode === 'edit' ? '编辑业务信息' : '基本信息' }}</h3>
      <p v-if="mode !== 'readonly'">
        {{ mode === 'create' ? '按业务顺序填写；带必填标识的项目需要完成后才能保存。' : '修改会保留在当前页面，保存成功后才会更新业务记录。' }}
        只读信息不可修改，自动计算结果以保存后的记录为准。
      </p>
    </div>
    <span v-if="mode !== 'readonly'" class="native-form-mode-note">{{ dirty ? '有未保存修改' : '尚未修改' }}</span>
  </section>
  <section
    v-if="useNativeFormTree"
    ref="canvasRef"
    class="contract-form-canvas-shell"
    data-form-canvas
    :class="{ 'contract-form-designer-canvas': designerMode }"
    aria-label="表单配置画布"
  >
    <header v-if="designerMode" class="contract-form-canvas-head">
      <div>
        <strong>表单画布</strong>
        <span>{{ selectedFieldRowLabel ? `正在编辑：${selectedFieldRowLabel}` : '点选字段后在右侧调整属性' }}</span>
      </div>
      <em>{{ rootColumns }} 栏布局</em>
    </header>
    <nav v-if="sectionItems.length > 2" class="contract-form-section-nav" aria-label="表单章节导航">
      <span class="contract-form-section-nav-label">章节</span>
      <button
        v-for="item in sectionItems"
        :key="item.title"
        type="button"
        :class="{ 'is-active': activeSection === item.title, 'has-error': item.hasError }"
        :aria-current="activeSection === item.title ? 'location' : undefined"
        @click="scrollToSection(item.title)"
      >{{ item.title }}<span v-if="item.hasError" class="section-error-dot" aria-label="本章节存在错误"></span></button>
    </nav>
    <NativeFormTreeRenderer
      :key="layoutVisibilityRevision"
      class="contract-form-canvas-body"
      :nodes="layoutNodes"
      :field-schemas-for-nodes="fieldSchemasForNodes"
      :is-node-visible="isNodeVisible"
      :button-label-resolver="buttonLabelResolver"
      :native-action-handler="nativeActionHandler"
      :native-action-state-resolver="nativeActionStateResolver"
      :relation-adapter="relationAdapter"
      :field-actions="fieldActions"
      :field-order-editable="fieldOrderEditable"
      :field-order-index="fieldOrderIndex"
      :field-order-count="fieldOrderCount"
      :field-order-dragging-key="fieldOrderDraggingKey"
      :field-order-drop-target-key="fieldOrderDropTargetKey"
      :field-order-drop-placement="fieldOrderDropPlacement"
      :field-config-editable="fieldConfigEditable"
      :field-selection-mode="fieldSelectionMode"
      :selected-field-key="selectedFieldKey"
      :columns="rootColumns"
      @field-change="emit('field-change', $event)"
      @field-action="emit('field-action', $event)"
      @field-order-move="emit('field-order-move', $event)"
      @field-order-drag-start="emit('field-order-drag-start', $event)"
      @field-order-drag-over="emit('field-order-drag-over', $event)"
      @field-order-drag-leave="emit('field-order-drag-leave', $event)"
      @field-order-drop="emit('field-order-drop', $event)"
      @field-order-group-drop="emit('field-order-group-drop', $event)"
      @field-order-drag-end="emit('field-order-drag-end', $event)"
      @field-label-change="emit('field-label-change', $event)"
      @field-add-after="emit('field-add-after', $event)"
      @field-select="emit('field-select', $event)"
      @group-rename="emit('group-rename', $event)"
      @group-add-field="emit('group-add-field', $event)"
      @native-action="emit('native-action', $event)"
    >
      <template #readonly="{ field }">
        <span class="contract-readonly-value" :class="{ 'contract-readonly-value--empty': isEmptyValue(field.value, field.type) }">
          <span v-if="isEmptyValue(field.value, field.type)">未填写</span>
          <FieldValue v-else :value="field.value" :field="field.descriptor" />
        </span>
      </template>
      <template #chatter>
        <NativeCollaborationPanel
          v-if="showCollaborationPanel"
          v-bind="collaborationPanelProps"
          v-on="collaborationPanelListeners"
        />
      </template>
    </NativeFormTreeRenderer>
  </section>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, onUpdated, ref, watch } from 'vue';
import FieldValue from '../../components/FieldValue.vue';
import NativeFormTreeRenderer, { type NativeFormLayoutNode } from '../../components/template/NativeFormTreeRenderer.vue';
import type {
  FormSectionFieldAction,
  FormSectionFieldActionPayload,
  FormSectionFieldChange,
  FormSectionFieldSchema,
} from '../../components/template/formSection.types';
import type { RelationFieldAdapter } from '../../components/template/relationField.types';
import NativeCollaborationPanel, {
  type NativeCollaborationPanelListeners,
  type NativeCollaborationPanelProps,
} from './NativeCollaborationPanel.vue';

type NativeColumns = 1 | 2 | 3;
type FieldOrderPlacement = 'before' | 'after' | '';

const props = defineProps<{
  mode: 'create' | 'edit' | 'readonly';
  dirty: boolean;
  showDefaultSectionTitle: boolean;
  useNativeFormTree: boolean;
  designerMode: boolean;
  selectedFieldRowLabel: string;
  rootColumns: NativeColumns;
  layoutVisibilityRevision: number;
  layoutNodes: NativeFormLayoutNode[];
  fieldSchemasForNodes: (nodes: NativeFormLayoutNode[]) => FormSectionFieldSchema[];
  isNodeVisible: (node: NativeFormLayoutNode) => boolean;
  buttonLabelResolver: (node: NativeFormLayoutNode) => string | undefined;
  nativeActionHandler: (payload: Record<string, unknown>) => void | Promise<void>;
  nativeActionStateResolver: (payload: Record<string, unknown>) => { disabled?: boolean; title?: string } | null | undefined;
  relationAdapter: RelationFieldAdapter;
  fieldActions: (field: FormSectionFieldSchema) => FormSectionFieldAction[];
  fieldOrderEditable: boolean;
  fieldOrderIndex: (field: FormSectionFieldSchema) => number;
  fieldOrderCount: number;
  fieldOrderDraggingKey: string;
  fieldOrderDropTargetKey: string;
  fieldOrderDropPlacement: FieldOrderPlacement;
  fieldConfigEditable: boolean;
  fieldSelectionMode: boolean;
  selectedFieldKey: string;
  showCollaborationPanel: boolean;
  collaborationPanelProps: NativeCollaborationPanelProps;
  collaborationPanelListeners: NativeCollaborationPanelListeners;
}>();

type SectionItem = { title: string; hasError: boolean };
const canvasRef = ref<HTMLElement | null>(null);
const sectionItems = ref<SectionItem[]>([]);
const activeSection = ref('');
let sectionObserver: IntersectionObserver | null = null;
let sectionMutationObserver: MutationObserver | null = null;
let refreshQueued = false;

function visibleSectionElements() {
  return [...(canvasRef.value?.querySelectorAll<HTMLElement>('[data-group-title]') || [])]
    .filter((element) => Boolean(element.dataset.groupTitle?.trim()) && element.getClientRects().length > 0);
}

function refreshSectionNavigation() {
  const elements = visibleSectionElements();
  const seen = new Set<string>();
  const next = elements.reduce<SectionItem[]>((items, element) => {
    const title = String(element.dataset.groupTitle || '').trim();
    if (!title || seen.has(title)) return items;
    seen.add(title);
    items.push({ title, hasError: Boolean(element.querySelector('[aria-invalid="true"], .field-error-text')) });
    return items;
  }, []);
  if (JSON.stringify(next) !== JSON.stringify(sectionItems.value)) sectionItems.value = next;
  if (!activeSection.value && next.length) activeSection.value = next[0].title;
  sectionObserver?.disconnect();
  sectionObserver = new IntersectionObserver((entries) => {
    const visible = entries.filter((entry) => entry.isIntersecting).sort((left, right) => left.boundingClientRect.top - right.boundingClientRect.top)[0];
    const title = String((visible?.target as HTMLElement | undefined)?.dataset.groupTitle || '').trim();
    if (title) activeSection.value = title;
  }, { rootMargin: '-18% 0px -70% 0px', threshold: 0 });
  elements.forEach((element) => sectionObserver?.observe(element));
}

function queueSectionRefresh() {
  if (refreshQueued) return;
  refreshQueued = true;
  void nextTick(() => {
    refreshQueued = false;
    refreshSectionNavigation();
  });
}

function scrollToSection(title: string) {
  const target = visibleSectionElements().find((element) => element.dataset.groupTitle === title);
  if (!target) return;
  activeSection.value = title;
  target.setAttribute('tabindex', '-1');
  target.focus({ preventScroll: true });
  target.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function isEmptyValue(value: unknown, type: unknown) {
  if (Array.isArray(value)) return value.length === 0;
  if (String(type || '').toLowerCase() === 'boolean') return value === null || value === undefined;
  return value === null || value === undefined || value === false || String(value).trim() === '';
}

onMounted(() => {
  sectionMutationObserver = new MutationObserver(queueSectionRefresh);
  if (canvasRef.value) {
    sectionMutationObserver.observe(canvasRef.value, {
      subtree: true,
      childList: true,
      attributes: true,
      attributeFilter: ['aria-invalid', 'class'],
    });
  }
  queueSectionRefresh();
});
onUpdated(queueSectionRefresh);
watch(() => [props.layoutVisibilityRevision, props.layoutNodes], queueSectionRefresh, { deep: true });
onBeforeUnmount(() => {
  sectionObserver?.disconnect();
  sectionMutationObserver?.disconnect();
});

const emit = defineEmits<{
  'field-change': [payload: FormSectionFieldChange];
  'field-action': [payload: FormSectionFieldActionPayload];
  'field-order-move': [payload: { field: FormSectionFieldSchema; delta: number }];
  'field-order-drag-start': [payload: { field: FormSectionFieldSchema; event: DragEvent }];
  'field-order-drag-over': [payload: { field: FormSectionFieldSchema; groupTitle?: string; placement?: FieldOrderPlacement }];
  'field-order-drag-leave': [payload: { field: FormSectionFieldSchema; groupTitle?: string }];
  'field-order-drop': [payload: { field: FormSectionFieldSchema; groupTitle?: string; placement?: FieldOrderPlacement }];
  'field-order-group-drop': [payload: { groupTitle: string; groupIndex: number }];
  'field-order-drag-end': [payload: { field: FormSectionFieldSchema }];
  'field-label-change': [payload: { field: FormSectionFieldSchema; label: string }];
  'field-add-after': [payload: { field: FormSectionFieldSchema; groupTitle: string }];
  'field-select': [payload: { field: FormSectionFieldSchema; groupTitle: string }];
  'group-rename': [payload: { oldTitle: string; newTitle: string }];
  'group-add-field': [payload: { groupTitle: string }];
  'native-action': [payload: Record<string, unknown>];
}>();
</script>

<style scoped>
.contract-form-section-nav {
  position: sticky;
  top: 72px;
  z-index: 8;
  display: flex;
  align-items: center;
  gap: 4px;
  min-width: 0;
  padding: 7px 8px;
  border: 1px solid var(--sc-app-border);
  border-radius: 7px;
  background: color-mix(in srgb, var(--sc-app-panel) 96%, transparent);
  box-shadow: var(--sc-app-shadow-popover);
  overflow-x: auto;
  scrollbar-width: thin;
}

.contract-form-section-nav-label {
  flex: 0 0 auto;
  padding: 0 6px;
  color: var(--sc-app-text-muted);
  font-size: 11px;
  font-weight: 600;
}

.contract-form-section-nav button {
  flex: 0 0 auto;
  position: relative;
  min-height: 28px;
  padding: 4px 9px;
  border: 0;
  border-radius: 5px;
  background: transparent;
  color: var(--sc-app-text-secondary);
  font-size: 12px;
  line-height: 1.25;
  cursor: pointer;
  white-space: nowrap;
}

.contract-form-section-nav button:hover {
  background: var(--sc-app-hover-bg);
  color: var(--sc-app-text-primary);
}

.contract-form-section-nav button:focus-visible {
  outline: 2px solid var(--sc-semantic-surface-interactive);
  outline-offset: -2px;
}

.contract-form-section-nav button.is-active {
  background: var(--sc-navigation-active-bg);
  color: var(--sc-app-info-text);
  font-weight: 650;
}

.section-error-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  margin-left: 5px;
  border-radius: 999px;
  background: var(--sc-app-danger-text);
  vertical-align: 1px;
}

.contract-readonly-value--empty {
  color: var(--sc-app-text-muted);
  font-weight: 400;
}

@media (max-width: 860px) {
  .contract-form-section-nav {
    position: static;
    border-inline: 0;
    border-radius: 0;
    box-shadow: none;
  }
}
</style>
