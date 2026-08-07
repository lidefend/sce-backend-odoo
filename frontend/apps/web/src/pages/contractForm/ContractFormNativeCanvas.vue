<template>
  <section v-if="!designerMode && (showDefaultSectionTitle || mode === 'create')" class="native-default-section-head">
    <div>
      <h3>{{ mode === 'create' ? '填写业务信息' : mode === 'edit' ? '编辑业务信息' : '基本信息' }}</h3>
      <p v-if="mode !== 'readonly'">
        {{ mode === 'create' ? '按业务顺序填写，带 * 为必填；只读及计算字段将在保存后更新。' : '修改仅在保存成功后更新业务记录；只读及计算字段不可直接修改。' }}
      </p>
    </div>
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
    <div
      v-if="sectionItems.length > 2"
      class="form-section-nav-shell"
      :class="{ 'has-more-before': sectionHasMoreBefore, 'has-more-after': sectionHasMoreAfter }"
    >
      <nav ref="sectionNavRef" class="form-section-nav" aria-label="表单章节导航" @scroll="updateSectionOverflow">
        <span class="form-section-nav-label">章节</span>
        <button
          v-for="item in sectionItems"
          :key="item.title"
          type="button"
          :data-section-tab="item.title"
          :class="{ 'is-active': activeSection === item.title, 'has-error': item.hasError }"
          :aria-current="activeSection === item.title ? 'location' : undefined"
          @click="scrollToSection(item.title)"
        >{{ item.title }}<span v-if="item.hasError" class="section-error-dot" aria-label="本章节存在错误"></span></button>
      </nav>
      <span class="form-section-progress" aria-live="polite">
        {{ activeSectionIndex + 1 }}/{{ sectionItems.length }}<span v-if="sectionHasMoreBefore || sectionHasMoreAfter"> · 横向滑动</span>
      </span>
    </div>
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
        <span class="form-readonly-value" :class="{ 'form-readonly-value--empty': isEmptyValue(field.value, field.type) }">
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
import { computed, nextTick, onBeforeUnmount, onMounted, onUpdated, ref, watch } from 'vue';
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
const sectionNavRef = ref<HTMLElement | null>(null);
const sectionItems = ref<SectionItem[]>([]);
const activeSection = ref('');
const sectionHasMoreBefore = ref(false);
const sectionHasMoreAfter = ref(false);
const activeSectionIndex = computed(() => Math.max(0, sectionItems.value.findIndex((item) => item.title === activeSection.value)));
let sectionObserver: IntersectionObserver | null = null;
let sectionMutationObserver: MutationObserver | null = null;
let sectionNavResizeObserver: ResizeObserver | null = null;
let formShell: HTMLElement | null = null;
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
  void nextTick(() => {
    const navShell = sectionNavRef.value?.closest<HTMLElement>('.form-section-nav-shell');
    if (navShell) sectionNavResizeObserver?.observe(navShell);
    syncSectionNavHeight();
    scrollActiveSectionTabIntoView(false);
    updateSectionOverflow();
  });
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
  const commandBottom = document.querySelector<HTMLElement>('.contract-form-command-bar')?.getBoundingClientRect().bottom || 0;
  const stickyNav = sectionNavRef.value?.closest<HTMLElement>('.form-section-nav-shell');
  const navStyle = stickyNav ? getComputedStyle(stickyNav) : null;
  const navBottom = navStyle?.position === 'sticky' ? stickyNav?.getBoundingClientRect().bottom || 0 : 0;
  const obstructionBottom = Math.max(commandBottom, navBottom);
  const targetTop = target.getBoundingClientRect().top;
  const scrollHost = (() => {
    let parent = target.parentElement;
    while (parent) {
      const style = getComputedStyle(parent);
      if (/(auto|scroll)/.test(style.overflowY) && parent.scrollHeight > parent.clientHeight + 1) return parent;
      parent = parent.parentElement;
    }
    return null;
  })();
  const delta = targetTop - obstructionBottom - 12;
  if (scrollHost) scrollHost.scrollBy({ top: delta, behavior: 'auto' });
  else window.scrollBy({ top: delta, behavior: 'auto' });
  void nextTick(() => scrollActiveSectionTabIntoView(true));
}

function updateSectionOverflow() {
  const nav = sectionNavRef.value;
  if (!nav) return;
  sectionHasMoreBefore.value = nav.scrollLeft > 2;
  sectionHasMoreAfter.value = nav.scrollLeft + nav.clientWidth < nav.scrollWidth - 2;
}

function syncSectionNavHeight() {
  const navShell = sectionNavRef.value?.closest<HTMLElement>('.form-section-nav-shell');
  formShell = navShell?.closest<HTMLElement>('.contract-form-native-shell') || null;
  formShell?.style.setProperty('--sc-form-section-nav-height', `${Math.ceil(navShell?.getBoundingClientRect().height || 0)}px`);
}

function scrollActiveSectionTabIntoView(smooth: boolean) {
  const nav = sectionNavRef.value;
  const active = nav?.querySelector<HTMLElement>('[aria-current="location"]');
  if (!nav || !active) return;
  const left = Math.max(0, active.offsetLeft - (nav.clientWidth - active.offsetWidth) / 2);
  nav.scrollTo({ left, behavior: smooth ? 'smooth' : 'auto' });
  window.setTimeout(updateSectionOverflow, smooth ? 220 : 0);
}

function isEmptyValue(value: unknown, type: unknown) {
  if (Array.isArray(value)) return value.length === 0;
  const normalizedType = String(type || '').trim().toLowerCase();
  if (normalizedType === 'boolean') return value === null || value === undefined;
  const normalizedValue = String(value ?? '').trim().toLowerCase();
  return value === null || value === undefined || value === false || normalizedValue === '' || normalizedValue === 'false';
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
  sectionNavResizeObserver = new ResizeObserver(syncSectionNavHeight);
  void nextTick(() => {
    const navShell = sectionNavRef.value?.closest<HTMLElement>('.form-section-nav-shell');
    if (navShell) sectionNavResizeObserver?.observe(navShell);
    syncSectionNavHeight();
  });
  queueSectionRefresh();
});
onUpdated(queueSectionRefresh);
watch(() => [props.layoutVisibilityRevision, props.layoutNodes], queueSectionRefresh, { deep: true });
watch(activeSection, () => void nextTick(() => scrollActiveSectionTabIntoView(true)));
onBeforeUnmount(() => {
  sectionObserver?.disconnect();
  sectionMutationObserver?.disconnect();
  sectionNavResizeObserver?.disconnect();
  formShell?.style.removeProperty('--sc-form-section-nav-height');
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
.form-section-nav-shell {
  position: sticky;
  top: calc(var(--sc-form-command-bar-height, 72px) + var(--sc-form-sticky-gap, 8px));
  z-index: 8;
  min-width: 0;
  border: 1px solid var(--sc-app-border);
  border-radius: 6px;
  background: color-mix(in srgb, var(--sc-app-panel) 97%, transparent);
  overflow: hidden;
}

.form-section-nav {
  display: flex;
  align-items: center;
  gap: 4px;
  min-width: 0;
  padding: 6px 62px 6px 7px;
  overflow-x: auto;
  scrollbar-width: thin;
}

.form-section-progress {
  position: absolute;
  top: 50%;
  right: 7px;
  z-index: 2;
  transform: translateY(-50%);
  padding-left: 18px;
  background: linear-gradient(90deg, transparent, var(--sc-app-panel) 16px);
  color: var(--sc-app-text-muted);
  font-size: 10px;
  line-height: 28px;
  white-space: nowrap;
  pointer-events: none;
}

.form-section-nav-label {
  flex: 0 0 auto;
  padding: 0 6px;
  color: var(--sc-app-text-muted);
  font-size: 11px;
  font-weight: 600;
}

.form-section-nav button {
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

.form-section-nav button:hover {
  background: var(--sc-app-hover-bg);
  color: var(--sc-app-text-primary);
}

.form-section-nav button:focus-visible {
  outline: 2px solid var(--sc-semantic-surface-interactive);
  outline-offset: -2px;
}

.form-section-nav button.is-active {
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

.form-readonly-value--empty {
  color: var(--sc-app-text-muted);
  font-weight: 400;
}

@media (max-width: 860px) {
  .form-section-nav-shell {
    position: relative;
    top: auto;
    border-inline: 0;
    border-radius: 0;
  }

  .form-section-nav {
    padding-right: 7px;
  }

  .form-section-progress {
    position: static;
    display: block;
    transform: none;
    padding: 0 8px 4px;
    background: none;
    line-height: 16px;
    text-align: right;
  }
}
</style>
