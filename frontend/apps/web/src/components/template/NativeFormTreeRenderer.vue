/* eslint-disable vue/no-dupe-keys */
<template>
  <div class="native-form-tree" data-semantic-component="NativeFormTreeRenderer" :data-state="visibleNodes.length ? 'ready' : 'empty'">
    <template v-for="(node, index) in visibleNodes" :key="nodeKey(node, index)">
      <component
        :is="isDetailCard(node) ? ScCard : 'section'"
        v-if="isContainerNode(node)"
        :bordered="isDetailCard(node) ? false : undefined"
        :title="isDetailCard(node) && !isCollapsibleContainer(node) ? (semanticSectionTitle(node) || containerTitle(node) || undefined) : undefined"
        :body-class-name="isDetailCard(node) ? 'native-detail-card-body' : undefined"
        :data-detail-card="isDetailCard(node) ? 'native-section' : undefined"
        :class="containerClass(node)"
        :data-group-title="containerPolicyTitle(node, index)"
        :data-section-navigation-role="nativeSectionNavigationRole(node)"
        :data-collapsed="isContainerCollapsed(node, index) ? 'true' : 'false'"
        :data-form-semantic-role="semanticFormRole(node) || undefined"
        :data-form-section-target="sectionNavigationTarget(node) || undefined"
        :data-section-content-kind="sectionContentKind(node) || undefined"
        :data-section-source-identity="sectionSourceIdentity(node) || undefined"
        @dragover.prevent
        @drop.prevent.stop="emitGroupFieldOrderDrop(node, $event, index)"
        @mouseup.self="emitGroupFieldOrderPointerDrop(node, index)"
      >
        <header v-if="(!isDetailCard(node) || isCollapsibleContainer(node)) && (semanticSectionTitle(node) || containerTitle(node))" class="native-container-head">
          <ScInput
            v-if="fieldConfigEditable && isEditableGroupNode(node)"
            class="native-container-title-editor"
            type="text"
            size="small"
            :model-value="containerTitle(node)"
            :aria-label="`${containerTitle(node)}区域名称`"
            @change="emitGroupRename(node, $event)"
            @keydown.enter.prevent="emitGroupRename(node, ($event.target as HTMLInputElement).value)"
          />
          <ScButton
            v-else-if="isCollapsibleContainer(node)"
            type="button"
            variant="ghost"
            size="small"
            appearance="context-action"
            :aria-expanded="String(!isContainerCollapsed(node, index))"
            @click="toggleContainerCollapsed(node, index)"
          >{{ semanticSectionTitle(node) || containerTitle(node) }}</ScButton>
          <h3 v-else>{{ semanticSectionTitle(node) || containerTitle(node) }}</h3>
        </header>
        <div
          v-else-if="fieldOrderEditable && nodeType(node) === 'group'"
          class="native-container-drop-strip"
          :data-group-title="containerPolicyTitle(node, index)"
          data-drop-zone="field-group"
          @dragover.prevent.stop
          @drop.prevent.stop="emitGroupFieldOrderDrop(node, $event, index)"
          @mouseup.stop="emitGroupFieldOrderPointerDrop(node, index)"
        >
          <span v-if="fieldOrderDraggingKey">拖到这里加入此分组</span>
        </div>
        <ScInlineState
          v-if="isNativeFeedbackContainer(node)"
          class="native-form-feedback"
          :state="nativeFeedbackState(node)"
          density="compact"
          :data-feedback-tone="nativeTextPresentation(node).tone"
        >
          <div class="native-form-feedback__content">
            <p v-if="nodeText(node)" class="native-form-feedback__copy">{{ nodeText(node) }}</p>
            <FormSection
              v-if="fieldSchemasForNodes(fieldChildren(node)).length"
              title=""
              :columns="1"
              :fields="fieldSchemasForNodes(fieldChildren(node))"
              :relation-adapter="relationAdapter"
              :prefer-readonly-facts="true"
              :fill-orphan-rows="false"
              @field-change="emit('field-change', $event)"
              @field-action="emit('field-action', $event)"
            >
              <template v-if="$slots.readonly" #readonly="{ field }">
                <slot name="readonly" :field="field" />
              </template>
            </FormSection>
          </div>
        </ScInlineState>
        <p
          v-else-if="nodeText(node)"
          class="native-static-text"
          :class="[...nativeTextPresentationClass(node), ...declaredPresentationTokens(node)]"
          :data-native-text-presentation="nativeTextPresentation(node).kind"
          :data-tone="nativeTextPresentation(node).tone"
          :role="nativeTextPresentation(node).role"
        >{{ nodeText(node) }}</p>

        <template v-if="nodeType(node) === 'notebook'">
          <ScTabs
            class="native-tabs"
            :model-value="activePageIndex"
            :items="notebookTabItems(node)"
            size="small"
            @update:model-value="activePageIndex = Number($event)"
          >
            <template #panel="{ item }">
          <div v-if="Number(item.value) === activePageIndex" class="native-tab-panel">
            <NativeFormTreeRenderer
              :nodes="notebookPageChildren(node, activePageIndex)"
              :field-schemas-for-nodes="fieldSchemasForNodes"
              :is-node-visible="isNodeVisible"
              :button-label-resolver="buttonLabelResolver"
              :native-action-handler="nativeActionHandler"
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
              :prefer-readonly-facts="preferReadonlyFacts"
              :inside-detail-card="insideDetailCard || isDetailCard(node)"
              :columns="nodeColumns(node)"
              :inherited-semantic-role="semanticFormRole(node)"
              :authoritative-business-section-mode="authoritativeBusinessSectionMode"
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
              <template v-if="$slots.readonly" #readonly="{ field }">
                <slot name="readonly" :field="field" />
              </template>
              <template #chatter="{ node: chatterNode }">
                <slot name="chatter" :node="chatterNode" />
              </template>
            </NativeFormTreeRenderer>
          </div>
            </template>
          </ScTabs>
        </template>

        <template v-else-if="nodeType(node) === 'h1' && titleFieldForNode(node)">
          <div class="native-title-row" :data-field-name="titleFieldForNode(node)?.name || undefined">
            <ScIconButton
              v-if="titleFieldForNode(node)?.favoriteToggle"
              class="native-title-favorite"
              appearance="favorite-toggle"
              :class="{ 'native-title-favorite--active': titleFieldForNode(node)?.favoriteToggle?.active }"
              :aria-pressed="titleFieldForNode(node)?.favoriteToggle?.active"
              :label="titleFieldForNode(node)?.favoriteToggle?.label || '切换收藏'"
              :disabled="titleFieldForNode(node)?.favoriteToggle?.readonly"
              @click="emitTitleFavoriteToggle(titleFieldForNode(node))"
            >
              <ScIcon :name="titleFieldForNode(node)?.favoriteToggle?.active ? 'star' : 'star-outline'" :size="18" />
            </ScIconButton>
            <ScInput
              v-if="!titleFieldForNode(node)?.readonly"
              class="native-title-input"
              appearance="record-title"
              type="text"
              :model-value="titleFieldValue(titleFieldForNode(node))"
              :aria-label="titleFieldForNode(node)?.label"
              @update:model-value="emitTitleFieldChange(titleFieldForNode(node), $event)"
            />
            <h2 v-else class="native-title-text">{{ titleFieldValue(titleFieldForNode(node)) || titleFieldForNode(node)?.label }}</h2>
          </div>
          <NativeFormTreeRenderer
            v-if="containerChildren(node).length"
            :nodes="containerChildren(node)"
            :field-schemas-for-nodes="fieldSchemasForNodes"
            :is-node-visible="isNodeVisible"
            :button-label-resolver="buttonLabelResolver"
            :native-action-handler="nativeActionHandler"
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
            :prefer-readonly-facts="preferReadonlyFacts"
            :inside-detail-card="insideDetailCard || isDetailCard(node)"
            :columns="nodeColumns(node)"
            :inherited-semantic-role="semanticFormRole(node)"
            :authoritative-business-section-mode="authoritativeBusinessSectionMode"
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
            <template v-if="$slots.readonly" #readonly="{ field }">
              <slot name="readonly" :field="field" />
            </template>
            <template #chatter="{ node: chatterNode }">
              <slot name="chatter" :node="chatterNode" />
            </template>
          </NativeFormTreeRenderer>
        </template>

        <template v-else>
          <template v-for="(segment, segmentIndex) in childSegments(node)" :key="segmentIndex">
          <FormSection
            v-if="segment.kind === 'field' && !isNativeFeedbackContainer(node) && fieldSchemasForNodes(segment.nodes).length"
            :title="segmentIndex === childSegments(node).findIndex((item) => item.kind === 'field') ? fieldSectionTitle(node) : ''"
            :columns="nodeColumns(node)"
            :inherited-semantic-role="semanticFormRole(node)"
            :fields="fieldSchemasForNodes(segment.nodes)"
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
            :prefer-readonly-facts="preferReadonlyFacts"
            :fill-orphan-rows="false"
            :field-group-title="containerPolicyTitle(node, index)"
            tone="core"
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
          >
            <template v-if="$slots.readonly" #readonly="{ field }">
              <slot name="readonly" :field="field" />
            </template>
          </FormSection>
          <div v-if="segment.kind === 'button' && segment.nodes.length" :class="nativeActionsClass(node)">
            <template v-for="(buttonNode, buttonIndex) in visibleActionButtons(node).filter((button) => segment.nodes.includes(button))" :key="nodeKey(buttonNode, buttonIndex)">
              <ScButton
                v-if="!isSmartButtonNode(buttonNode)"
                v-bind="nativeActionEvidenceAttributes(buttonNode)"
                type="button"
                class="native-action-btn"
                size="small"
                variant="secondary"
                :disabled="nativeActionDisabled(buttonNode)"
                :title="nativeActionTitle(buttonNode)"
                @click.stop.prevent="emitNativeAction(buttonNode)"
              >
                <template v-for="icon in [buttonIcon(buttonNode)]" :key="icon">
                  <ScIcon v-if="icon" class="native-action-icon" :name="icon" :size="18" />
                </template>
                <span class="native-action-label">{{ buttonLabel(buttonNode) }}</span>
              </ScButton>
              <NativeSmartAction
                v-else
                v-bind="nativeActionEvidenceAttributes(buttonNode)"
                :label="buttonLabel(buttonNode)"
                :icon="buttonIcon(buttonNode)"
                :disabled="nativeActionDisabled(buttonNode)"
                :title="nativeActionTitle(buttonNode)"
                @click.stop.prevent="emitNativeAction(buttonNode)"
              />
            </template>
            <NativeActionOverflowMenu
              v-if="segment.nodes.includes(overflowActionButtons(node)[0])"
              :actions="overflowActionButtons(node)"
              :identity="nodeKey(node, index)"
              :key-resolver="overflowActionKey"
              :evidence-resolver="nativeActionEvidenceAttributes"
              :label-resolver="buttonLabel"
              :icon-resolver="buttonIcon"
              :disabled-resolver="nativeActionDisabled"
              :title-resolver="nativeActionTitle"
              @select="emitNativeAction"
            />
          </div>
          <template v-for="(widgetNode, widgetIndex) in (segment.kind === 'widget' ? segment.nodes : [])" :key="nodeKey(widgetNode, widgetIndex)">
            <div v-if="widgetName(widgetNode) === 'web_ribbon'" class="native-ribbon" :class="widgetClass(widgetNode)">
              {{ widgetTitle(widgetNode) }}
            </div>
          </template>
          <NativeFormTreeRenderer
            v-if="segment.kind === 'container'"
            :nodes="segment.nodes"
            :field-schemas-for-nodes="fieldSchemasForNodes"
            :is-node-visible="isNodeVisible"
            :button-label-resolver="buttonLabelResolver"
            :native-action-handler="nativeActionHandler"
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
            :prefer-readonly-facts="preferReadonlyFacts"
            :inside-detail-card="insideDetailCard || isDetailCard(node)"
            :columns="nodeColumns(node)"
            :authoritative-business-section-mode="authoritativeBusinessSectionMode"
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
            <template v-if="$slots.readonly" #readonly="{ field }">
              <slot name="readonly" :field="field" />
            </template>
            <template #chatter="{ node: chatterNode }">
              <slot name="chatter" :node="chatterNode" />
            </template>
          </NativeFormTreeRenderer>
          </template>
        </template>
      </component>

      <FormSection
        v-else-if="nodeType(node) === 'field' && fieldSchemasForNodes([node]).length"
        :class="[...nodeClassList(node), ...declaredPresentationTokens(node)]"
        :title="fieldSectionTitle(node)"
        :columns="nodeColumns(node)"
        :fields="fieldSchemasForNodes([node])"
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
        :prefer-readonly-facts="preferReadonlyFacts"
        :fill-orphan-rows="false"
        tone="core"
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
      >
        <template v-if="$slots.readonly" #readonly="{ field }">
          <slot name="readonly" :field="field" />
        </template>
      </FormSection>

      <div v-else-if="nodeType(node) === 'button'" :class="nativeActionsClass(node)">
        <ScButton
          v-if="!isSmartButtonNode(node)"
          v-bind="nativeActionEvidenceAttributes(node)"
          type="button"
          class="native-action-btn"
          size="small"
          variant="secondary"
          :disabled="nativeActionDisabled(node)"
          :title="nativeActionTitle(node)"
          @click.stop.prevent="emitNativeAction(node)"
        >
          <template v-for="icon in [buttonIcon(node)]" :key="icon">
            <ScIcon v-if="icon" class="native-action-icon" :name="icon" :size="18" />
          </template>
          <span class="native-action-label">{{ buttonLabel(node) }}</span>
        </ScButton>
        <NativeSmartAction
          v-else
          v-bind="nativeActionEvidenceAttributes(node)"
          :label="buttonLabel(node)"
          :icon="buttonIcon(node)"
          :disabled="nativeActionDisabled(node)"
          :title="nativeActionTitle(node)"
          @click.stop.prevent="emitNativeAction(node)"
        />
      </div>

      <div v-else-if="nodeType(node) === 'widget' && widgetName(node) === 'web_ribbon'" class="native-ribbon" :class="widgetClass(node)">
        {{ widgetTitle(node) }}
      </div>

      <slot v-else-if="nodeType(node) === 'chatter'" name="chatter" :node="node" />
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import FormSection from './FormSection.vue';
import { nativeChildSegments } from './nativeChildSequence';
import NativeActionOverflowMenu from './NativeActionOverflowMenu.vue';
import NativeSmartAction from './NativeSmartAction.vue';
import ScCard from '../design-system/ScCard.vue';
import { useOptionalStandardDetailComposition } from '../../pages/contractForm/standardDetailCompositionRuntime';
import ScButton from '../design-system/ScButton.vue';
import ScIcon from '../design-system/ScIcon.vue';
import ScIconButton from '../design-system/ScIconButton.vue';
import ScInput from '../design-system/ScInput.vue';
import ScInlineState from '../design-system/ScInlineState.vue';
import ScTabs, { type ScTabItem } from '../design-system/ScTabs.vue';
import { canonicalFormActionIconClass } from '../../pages/contractForm/canonicalFormActionIcon';
import { nativeSectionNavigationRole } from '../../pages/contractForm/nativeSectionNavigation';
import { resolveNativeTextPresentation } from './nativeTextPresentation';
import { isLayoutOnlyGroupContainer } from '../../pages/contractForm/nativeLayoutUtils';
import { collectNativeBusinessSections, nativeBusinessSectionIdentity, resolveNativeSectionHeading } from '../../pages/contractForm/nativeBusinessSection';
import type {
  FormSectionFieldAction,
  FormSectionFieldActionPayload,
  FormSectionFieldChange,
  FormSectionFieldSchema,
} from './formSection.types';
import type { RelationFieldAdapter } from './relationField.types';

defineOptions({ name: 'NativeFormTreeRenderer' });

export type NativeFormLayoutNode = {
  type?: string;
  containerType?: string;
  name?: string;
  string?: string;
  label?: string;
  displayLabel?: string;
  semanticTitle?: string;
  semanticAnchor?: string;
  text?: string;
  cols?: number;
  columns?: number;
  widget?: string;
  visible?: boolean;
  class?: string;
  className?: string;
  styleToken?: string;
  field_size?: string;
  fieldSize?: string;
  size?: string;
  filename?: string;
  badge?: Record<string, unknown>;
  column_invisible?: unknown;
  domain?: unknown;
  context?: unknown;
  options?: unknown;
  col?: number | string;
  formStructure?: Record<string, unknown>;
  attributes?: Record<string, unknown>;
  fieldInfo?: Record<string, unknown>;
  field_info?: Record<string, unknown>;
  sourceAuthority?: Record<string, unknown>;
  source_authority?: Record<string, unknown>;
  fields?: readonly string[];
  buttonType?: string;
  action?: Record<string, unknown> | null;
  modifiers?: Record<string, unknown>;
  invisible?: unknown;
  readonly?: unknown;
  required?: unknown;
  children?: NativeFormLayoutNode[];
  pages?: NativeFormLayoutNode[];
  tabs?: NativeFormLayoutNode[];
  nodes?: NativeFormLayoutNode[];
  items?: NativeFormLayoutNode[];
  widgetList?: NativeFormLayoutNode[];
};

const props = withDefaults(defineProps<{
  nodes: NativeFormLayoutNode[];
  fieldSchemasForNodes: (nodes: NativeFormLayoutNode[]) => FormSectionFieldSchema[];
  isNodeVisible?: (node: NativeFormLayoutNode) => boolean;
  buttonLabelResolver?: (node: NativeFormLayoutNode) => string | undefined;
  nativeActionHandler?: (payload: Record<string, unknown>) => void | Promise<void>;
  nativeActionStateResolver?: (payload: Record<string, unknown>) => { disabled?: boolean; title?: string } | null | undefined;
  relationAdapter?: RelationFieldAdapter;
  fieldActions?: (field: FormSectionFieldSchema) => FormSectionFieldAction[];
  fieldOrderEditable?: boolean;
  fieldOrderIndex?: (field: FormSectionFieldSchema) => number;
  fieldOrderCount?: number;
  fieldOrderDraggingKey?: string;
  fieldOrderDropTargetKey?: string;
  fieldOrderDropPlacement?: 'before' | 'after' | '';
  fieldConfigEditable?: boolean;
  fieldSelectionMode?: boolean;
  selectedFieldKey?: string;
  preferReadonlyFacts?: boolean;
  insideDetailCard?: boolean;
  inheritedSemanticRole?: string;
  authoritativeBusinessSectionMode?: boolean;
  columns?: 1 | 2 | 3;
}>(), {
  columns: 2,
  isNodeVisible: () => true,
  nativeActionHandler: undefined,
  nativeActionStateResolver: undefined,
  relationAdapter: undefined,
  fieldActions: undefined,
  fieldOrderEditable: false,
  fieldOrderIndex: undefined,
  fieldOrderCount: 0,
  fieldOrderDraggingKey: '',
  fieldOrderDropTargetKey: '',
  fieldOrderDropPlacement: '',
  fieldConfigEditable: false,
  fieldSelectionMode: false,
  selectedFieldKey: '',
  preferReadonlyFacts: false,
});

function hasAuthoritativeBusinessSection(nodes: NativeFormLayoutNode[]): boolean {
  return collectNativeBusinessSections(nodes, {
    childrenOf: rawChildren,
    isVisible: (node) => props.isNodeVisible(node),
  }).length > 0;
}

const authoritativeBusinessSectionMode = computed(() => (
  props.authoritativeBusinessSectionMode ?? hasAuthoritativeBusinessSection(props.nodes)
));

const detailComposition = useOptionalStandardDetailComposition();
const adoptedDetail = computed(() => detailComposition?.adopted.value === true
  && props.preferReadonlyFacts && !props.fieldConfigEditable && !props.fieldSelectionMode);
function isDetailCard(node: NativeFormLayoutNode) {
  return adoptedDetail.value && !props.insideDetailCard
    && (Boolean(semanticSectionTitle(node)) || nodeType(node) === 'notebook');
}

const emit = defineEmits<{
  (event: 'field-change', payload: FormSectionFieldChange): void;
  (event: 'field-action', payload: FormSectionFieldActionPayload): void;
  (event: 'field-order-move', payload: { field: FormSectionFieldSchema; delta: number }): void;
  (event: 'field-order-drag-start', payload: { field: FormSectionFieldSchema; event: DragEvent }): void;
  (event: 'field-order-drag-over', payload: { field: FormSectionFieldSchema; groupTitle?: string; placement?: 'before' | 'after' | '' }): void;
  (event: 'field-order-drag-leave', payload: { field: FormSectionFieldSchema; groupTitle?: string }): void;
  (event: 'field-order-drop', payload: { field: FormSectionFieldSchema; groupTitle?: string; placement?: 'before' | 'after' | '' }): void;
  (event: 'field-order-group-drop', payload: { groupTitle: string; groupIndex: number }): void;
  (event: 'field-order-drag-end', payload: { field: FormSectionFieldSchema }): void;
  (event: 'field-label-change', payload: { field: FormSectionFieldSchema; label: string }): void;
  (event: 'field-add-after', payload: { field: FormSectionFieldSchema; groupTitle: string }): void;
  (event: 'field-select', payload: { field: FormSectionFieldSchema; groupTitle: string }): void;
  (event: 'group-rename', payload: { oldTitle: string; newTitle: string }): void;
  (event: 'group-add-field', payload: { groupTitle: string }): void;
  (event: 'native-action', payload: Record<string, unknown>): void;
}>();

const activePageIndex = ref(0);
const collapsedContainers = ref<Record<string, boolean>>({});
const SMART_BUTTON_DIRECT_LIMIT = 4;
const visibleNodes = computed(() => (props.nodes || []).filter((node) => isNodeRenderable(node)));

function isNodeRenderable(node: NativeFormLayoutNode): boolean {
  if (!node) return false;
  if (!props.isNodeVisible(node)) return false;
  const type = nodeType(node);
  // Empty-container guard: a structural container with no title, no static
  // text, and no renderable descendant (field/button/widget) renders as a
  // bare separator line or an empty shell — a visual artifact from backend
  // contracts that define structural nodes without effective content.  This
  // covers page-shell wrappers (header/sheet/footer) and notebooks whose
  // conditional pages are all hidden, besides layout groups.  In field-config
  // edit mode, keep empty groups as drop targets.
  if (
    type === 'group' || type === 'page' || type === 'container' || type === 'h1' || type === 'h2' || type === 'h3'
    || type === 'div' || type === 'span' || type === 'header' || type === 'sheet' || type === 'footer' || type === 'notebook'
  ) {
    if (props.fieldConfigEditable) return true;
    if (containerTitle(node) || nodeText(node)) return true;
    return hasRenderableDescendant(node, new Set<object>());
  }
  return true;
}

function hasRenderableDescendant(node: NativeFormLayoutNode, seen: Set<object>): boolean {
  if (!node || seen.has(node)) return false;
  seen.add(node);
  for (const child of rawChildren(node)) {
    if (!child) continue;
    if (!props.isNodeVisible(child)) continue;
    const childType = nodeType(child);
    if (childType === 'field') {
      // Node-level visibility is not enough: a field only renders when it
      // produces a schema (e.g. create-mode statusbar/invisible companions
      // have a visible node but no schema).  Match the real render branch.
      if (props.fieldSchemasForNodes([child]).length) return true;
      continue;
    }
    if (childType === 'button' || childType === 'widget') return true;
    if (['group', 'page', 'container', 'notebook', 'sheet', 'header', 'footer', 'h1', 'h2', 'h3', 'div', 'span'].includes(childType)) {
      if (hasRenderableDescendant(child, seen)) return true;
    }
  }
  return false;
}

function nodeType(node: NativeFormLayoutNode) {
  return String(node?.type || (node as { containerType?: string })?.containerType || '').trim().toLowerCase();
}

function nodeKey(node: NativeFormLayoutNode, index: number) {
  return `${nodeType(node) || 'node'}-${String(node?.name || node?.string || node?.label || index)}`;
}

function nativeBoolean(value: unknown): boolean {
  return value === true || value === 1 || value === '1' || String(value || '').trim().toLowerCase() === 'true';
}

function isCollapsibleContainer(node: NativeFormLayoutNode) {
  return nativeBoolean(nodeAttributes(node)['data-sc-collapsible']);
}

function isContainerCollapsed(node: NativeFormLayoutNode, index: number) {
  const key = nodeKey(node, index);
  if (Object.prototype.hasOwnProperty.call(collapsedContainers.value, key)) return collapsedContainers.value[key];
  return isCollapsibleContainer(node) && nativeBoolean(nodeAttributes(node)['data-sc-collapsed-by-default']);
}

function toggleContainerCollapsed(node: NativeFormLayoutNode, index: number) {
  if (!isCollapsibleContainer(node)) return;
  const key = nodeKey(node, index);
  collapsedContainers.value = {
    ...collapsedContainers.value,
    [key]: !isContainerCollapsed(node, index),
  };
}

function containerTitle(node: NativeFormLayoutNode) {
  const type = nodeType(node);
  if (type === 'group') return '';
  const raw = String(node?.string || node?.label || '').trim();
  if (!raw) return '';
  const structural = new Set(['header', 'footer', 'sheet', 'container', 'div', 'span', 'h1', 'h2', 'h3']);
  if (structural.has(type)) return '';
  const lowered = raw.toLowerCase();
  if (structural.has(lowered) || lowered === type) return '';
  return raw;
}

function semanticFormRole(node: NativeFormLayoutNode) {
  const direct = String(node?.attributes?.semanticFormRole || '').trim().toLowerCase();
  if (direct) return direct;
  const descendantRoles = [...new Set(rawChildren(node).map(semanticFormRole).filter(Boolean))];
  return descendantRoles.length === 1 ? descendantRoles[0] : '';
}

function sectionNavigationTarget(node: NativeFormLayoutNode) {
  return String(node?.attributes?.sectionNavigationTarget || '').trim();
}

function sectionContentKind(node: NativeFormLayoutNode) {
  return String(node?.attributes?.sectionContentKind || '').trim();
}

function sectionSourceIdentity(node: NativeFormLayoutNode) {
  return String(node?.attributes?.sectionSourceIdentity || '').trim();
}

function semanticSectionTitle(node: NativeFormLayoutNode) {
  // Contract-first: the heading is resolved by the shared section-identity
  // module (released native opt-in, then the contract-authored title). The
  // renderer must not invent a business label from a semantic role, otherwise
  // distinct contract sections collapse onto one placeholder heading.
  return resolveNativeSectionHeading(node, { fieldConfigEditable: props.fieldConfigEditable });
}

function isReadablePolicyTitle(value: unknown) {
  const text = String(value || '').trim();
  if (!text) return false;
  if (['group', 'page', 'notebook', 'sheet', 'container', 'header', 'footer'].includes(text.toLowerCase())) return false;
  if (/^[a-z][a-z0-9_:. -]*$/i.test(text) && /[_:.]/.test(text)) return false;
  return true;
}

function containerPolicyTitle(node: NativeFormLayoutNode, index = 0) {
  const raw = String(node?.string || node?.label || '').trim();
  if (isReadablePolicyTitle(raw)) return raw;
  if (nodeType(node) === 'group' && fieldChildren(node).length) return `默认分组 ${index + 1}`;
  return '';
}

function nodeText(node: NativeFormLayoutNode) {
  return String(node?.text || '').trim();
}

function nativeTextPresentation(node: NativeFormLayoutNode) {
  return resolveNativeTextPresentation(node);
}

function nativeTextPresentationClass(node: NativeFormLayoutNode) {
  const presentation = nativeTextPresentation(node);
  return [
    `native-static-text--${presentation.kind}`,
    `native-static-text--${presentation.tone}`,
  ];
}

function isNativeFeedbackContainer(node: NativeFormLayoutNode) {
  return resolveNativeTextPresentation(node).kind === 'callout';
}

function nativeFeedbackState(node: NativeFormLayoutNode): 'info' | 'error' {
  return resolveNativeTextPresentation(node).tone === 'danger' ? 'error' : 'info';
}

function isContainerNode(node: NativeFormLayoutNode) {
  return ['header', 'footer', 'sheet', 'group', 'notebook', 'page', 'container', 'div', 'span', 'h1', 'h2', 'h3'].includes(nodeType(node));
}

function rawChildren(node: NativeFormLayoutNode) {
  const rows: NativeFormLayoutNode[] = [];
  for (const key of ['children', 'pages', 'tabs', 'nodes', 'items'] as const) {
    const value = node?.[key];
    if (Array.isArray(value)) rows.push(...value);
  }
  return rows;
}

function fieldChildren(node: NativeFormLayoutNode) {
  return rawChildren(node).filter((child) => nodeType(child) === 'field' && isNodeRenderable(child));
}

function childSegments(node: NativeFormLayoutNode) {
  return nativeChildSegments(rawChildren(node).filter(isNodeRenderable), nodeType);
}

function titleFieldForNode(node: NativeFormLayoutNode) {
  return props.fieldSchemasForNodes(fieldChildren(node))[0];
}

function titleFieldValue(field?: FormSectionFieldSchema) {
  if (!field) return '';
  return String(field.inputValue ?? field.value ?? '').trim();
}

function emitTitleFieldChange(field: FormSectionFieldSchema | undefined, value: string) {
  if (!field) return;
  emit('field-change', {
    name: field.name,
    type: field.type,
    widget: field.widget,
    value,
    descriptor: field.descriptor,
  });
}

function emitTitleFavoriteToggle(field: FormSectionFieldSchema | undefined) {
  const favorite = field?.favoriteToggle;
  if (!favorite || favorite.readonly) return;
  emit('field-change', {
    name: favorite.name,
    type: 'boolean',
    value: !favorite.active,
    descriptor: favorite.descriptor,
  });
}

function buttonChildren(node: NativeFormLayoutNode) {
  return rawChildren(node).filter((child) => nodeType(child) === 'button' && isNodeRenderable(child));
}

function visibleActionButtons(node: NativeFormLayoutNode) {
  const children = buttonChildren(node);
  if (!isSmartActionGroup(node)) return children;
  const smartButtons = children.filter((child) => isSmartButtonNode(child));
  if (smartButtons.length <= SMART_BUTTON_DIRECT_LIMIT) return children;
  let smartSeen = 0;
  return children.filter((child) => {
    if (!isSmartButtonNode(child)) return true;
    smartSeen += 1;
    return smartSeen <= SMART_BUTTON_DIRECT_LIMIT;
  });
}

function overflowActionButtons(node: NativeFormLayoutNode) {
  const children = buttonChildren(node);
  if (!isSmartActionGroup(node)) return [];
  const smartButtons = children.filter((child) => isSmartButtonNode(child));
  if (smartButtons.length <= SMART_BUTTON_DIRECT_LIMIT) return [];
  return smartButtons.slice(SMART_BUTTON_DIRECT_LIMIT);
}

function widgetChildren(node: NativeFormLayoutNode) {
  return rawChildren(node).filter((child) => nodeType(child) === 'widget' && isNodeRenderable(child));
}

function containerChildren(node: NativeFormLayoutNode) {
  return rawChildren(node).filter((child) => !['field', 'button', 'widget'].includes(nodeType(child)));
}

function notebookPages(node: NativeFormLayoutNode) {
  const pages = rawChildren(node).filter((child) => nodeType(child) === 'page' && isNodeRenderable(child));
  return pages.length ? pages : rawChildren(node).filter((child) => isNodeRenderable(child));
}

function notebookPageChildren(node: NativeFormLayoutNode, pageIndex: number) {
  const page = notebookPages(node)[pageIndex] || notebookPages(node)[0];
  return page ? rawChildren(page) : [];
}

function sectionRevealTargets(node: NativeFormLayoutNode) {
  const targets: string[] = [];
  const visit = (candidate: NativeFormLayoutNode) => {
    const target = String(nodeAttributes(candidate).sectionNavigationTarget || '').trim();
    if (target && !targets.includes(target)) targets.push(target);
    rawChildren(candidate).forEach(visit);
  };
  visit(node);
  return targets;
}

function notebookTabItems(node: NativeFormLayoutNode): ScTabItem[] {
  return notebookPages(node).map((page, pageIndex) => {
    const label = containerTitle(page) || `页签 ${pageIndex + 1}`;
    return {
      value: pageIndex,
      label,
      labelClass: `native-tab${pageIndex === activePageIndex.value ? ' native-tab--active' : ''}`,
      labelAttributes: {
        'data-section-tab': label,
        'data-section-reveal-targets': JSON.stringify(sectionRevealTargets(page)),
      },
    };
  });
}

function fieldSectionTitle(node?: NativeFormLayoutNode) {
  if (nativeBusinessSectionIdentity(node)) return '';
  if (node && nodeType(node) === 'group') {
    const raw = String(node.string || node.label || '').trim();
    return isReadablePolicyTitle(raw) ? raw : '';
  }
  const semanticTitle = String(node?.semanticTitle || '').trim();
  if (semanticTitle) return semanticTitle;
  return node ? containerTitle(node) : '';
}

function normalizeColumns(value: unknown): 1 | 2 | 3 {
  const columns = Number(value);
  if (columns === 1 || columns === 2 || columns === 3) return columns;
  return 2;
}

function nodeColumns(node?: NativeFormLayoutNode): 1 | 2 | 3 {
  const attrs = node ? nodeAttributes(node) : {};
  const layoutNode = node as { cols?: unknown; columns?: unknown } | undefined;
  return normalizeColumns(attrs.col ?? attrs.columns ?? layoutNode?.cols ?? layoutNode?.columns ?? props.columns);
}

function isEditableGroupNode(node: NativeFormLayoutNode) {
  return ['group', 'page'].includes(nodeType(node));
}

function emitGroupRename(node: NativeFormLayoutNode, rawTitle: string) {
  const oldTitle = containerTitle(node);
  const newTitle = String(rawTitle || '').trim();
  if (!props.fieldConfigEditable || !oldTitle || !newTitle || oldTitle === newTitle) return;
  emit('group-rename', { oldTitle, newTitle });
}

function emitGroupFieldOrderDrop(node: NativeFormLayoutNode, event: DragEvent, index = 0) {
  if (!props.fieldOrderEditable || !props.fieldOrderDraggingKey) return;
  const target = event.target;
  const targetElement = target as unknown as { closest?: (selector: string) => unknown };
  const closest = target && typeof targetElement.closest === 'function'
    ? targetElement.closest.bind(target)
    : null;
  if (closest?.('.field')) return;
  const groupTitle = containerPolicyTitle(node, index);
  if (!groupTitle) return;
  emit('field-order-group-drop', { groupTitle, groupIndex: index });
}

function emitGroupFieldOrderPointerDrop(node: NativeFormLayoutNode, index = 0) {
  if (!props.fieldOrderEditable || !props.fieldOrderDraggingKey) return;
  const groupTitle = containerPolicyTitle(node, index);
  if (!groupTitle) return;
  emit('field-order-group-drop', { groupTitle, groupIndex: index });
  emit('field-order-drag-end', { field: { name: props.fieldOrderDraggingKey } as FormSectionFieldSchema });
}

function isLayoutOnlyGroup(node: NativeFormLayoutNode) {
  // Layout wrappers are groups without a business section identity: no
  // data-sc-anchor section, no semantic role title. They arrange columns
  // only and must not draw the section separator reserved for business
  // sections, otherwise nested wrappers stack a second border line.
  return isLayoutOnlyGroupContainer({
    nodeType: nodeType(node),
    editable: props.fieldConfigEditable,
    sectionTitle: semanticSectionTitle(node),
  });
}

function containerClass(node: NativeFormLayoutNode) {
  return [
    'native-container',
    `native-container--${nodeType(node) || 'node'}`,
    ...declaredPresentationTokens(node),
    {
      'native-container--config-hidden': props.fieldConfigEditable && nodeType(node) === 'group' && node.visible === false,
      'native-container--field-drop-target': Boolean(
        props.fieldOrderEditable
        && props.fieldOrderDraggingKey
        && containerPolicyTitle(node),
      ),
      'native-container--group--layout': isLayoutOnlyGroup(node),
      'native-container--detail-card': isDetailCard(node),
      'native-container--detail-group': adoptedDetail.value && props.insideDetailCard,
    },
  ];
}

function nodeAttributes(node: NativeFormLayoutNode) {
  return node?.attributes && typeof node.attributes === 'object' ? node.attributes : {};
}

function nodeClassList(node: NativeFormLayoutNode) {
  return String(nodeAttributes(node).class || '').split(/\s+/).map((item) => item.trim()).filter(Boolean);
}

/**
 * Presentation tokens declared by the contract for this node.
 *
 * The projection publishes every declared container presentation class on the
 * `styleToken` facet (with the bridge mirroring it on `attributes`).  The
 * renderer consumes that declaration only: a container must never render as an
 * unstyled stack of blocks because a declared class was dropped here, and the
 * renderer must not infer presentation from native markup.
 */
function declaredPresentationTokens(node: NativeFormLayoutNode) {
  const tokens: string[] = [];
  for (const value of [
    node?.styleToken,
    nodeAttributes(node).contractStyleToken,
    nodeAttributes(node).styleToken,
  ]) {
    for (const token of String(value || '').trim().split(/\s+/)) {
      if (token && !tokens.includes(token)) tokens.push(token);
    }
  }
  return tokens;
}

function nodeHasClass(node: NativeFormLayoutNode, className: string) {
  return nodeClassList(node).includes(className);
}

function nodeAction(node: NativeFormLayoutNode) {
  return node.action && typeof node.action === 'object' ? node.action as Record<string, unknown> : {};
}

function isSmartButtonNode(node: NativeFormLayoutNode) {
  return String(nodeAction(node).level || '').trim().toLowerCase() === 'smart' || nodeHasClass(node, 'oe_stat_button');
}

function isButtonBoxNode(node: NativeFormLayoutNode) {
  return nodeHasClass(node, 'oe_button_box') || (nodeType(node) === 'button' && isSmartButtonNode(node));
}

function isSmartActionGroup(node: NativeFormLayoutNode) {
  return isButtonBoxNode(node) || buttonChildren(node).some((child) => isSmartButtonNode(child));
}

function nativeActionsClass(node: NativeFormLayoutNode) {
  const smart = isSmartActionGroup(node);
  return ['native-actions', { 'native-actions--smart': smart }];
}

function nativeActionState(node: NativeFormLayoutNode) {
  return props.nativeActionStateResolver?.(node as Record<string, unknown>) || {};
}

function nativeActionDisabled(node: NativeFormLayoutNode) {
  return nativeActionState(node).disabled === true;
}

function nativeActionTitle(node: NativeFormLayoutNode) {
  return String(nativeActionState(node).title || '').trim();
}

function nativeActionEvidenceAttributes(node: NativeFormLayoutNode) {
  const action = nodeAction(node);
  return {
    'data-action-key': String(action.actionKey || action.key || '').trim() || undefined,
    'data-action-ref': String(action.actionId || action.actionRef || '').trim() || undefined,
    'data-action-tier': String(action.tier || '').trim() || undefined,
    'data-backend-identity': String(action.backendIdentity || '').trim() || undefined,
  };
}

function widgetName(node: NativeFormLayoutNode) {
  const attrs = nodeAttributes(node);
  return String(node?.widget || node?.name || attrs.name || '').trim();
}

function widgetTitle(node: NativeFormLayoutNode) {
  const attrs = nodeAttributes(node);
  return String(node?.label || node?.string || attrs.title || widgetName(node)).trim();
}

function widgetClass(node: NativeFormLayoutNode) {
  const attrs = nodeAttributes(node);
  return String(attrs.bg_color || '').trim();
}

function buttonLabel(node: NativeFormLayoutNode) {
  const action = node.action && typeof node.action === 'object' ? node.action as Record<string, unknown> : {};
  const resolved = props.buttonLabelResolver?.(node);
  return String(resolved || node.displayLabel || action.displayLabel || node.label || node.string || node.name || '操作').trim();
}

function buttonIcon(node: NativeFormLayoutNode) {
  const actionIcon = String(nodeAction(node).icon || '').trim();
  const attrIcon = String(nodeAttributes(node).icon || '').trim();
  const raw = actionIcon || attrIcon;
  return canonicalFormActionIconClass(raw);
}

function emitNativeAction(node: NativeFormLayoutNode) {
  if (nativeActionDisabled(node)) return;
  const buttonType = String(node.buttonType || 'object');
  const rawAction = node.action && typeof node.action === 'object' ? node.action : {};
  const rawPayload = rawAction.payload && typeof rawAction.payload === 'object' && !Array.isArray(rawAction.payload)
    ? rawAction.payload as Record<string, unknown>
    : {};
  const action = {
    ...rawAction,
    name: rawAction.name || node.name || '',
    label: rawAction.label || buttonLabel(node),
    kind: rawAction.kind || (buttonType === 'action' ? 'open' : 'object'),
    buttonType,
    level: rawAction.level || 'body',
    selection: rawAction.selection || 'none',
    payload: {
      ...rawPayload,
      method: rawPayload.method || (buttonType === 'object' ? node.name || '' : ''),
      ref: rawPayload.ref || (buttonType === 'action' ? node.name || '' : ''),
      type: rawPayload.type || buttonType,
    },
  };
  if (props.nativeActionHandler) {
    void props.nativeActionHandler(action);
    return;
  }
  emit('native-action', action);
}

function overflowActionKey(node: Record<string, unknown>, index: number) {
  return `more-${nodeKey(node as NativeFormLayoutNode, index)}`;
}
</script>

<style scoped>
.native-form-tree {
  display: grid;
  grid-auto-rows: max-content;
  align-content: start;
  gap: var(--sc-field-row-gap);
  grid-column: 1 / -1;
  min-width: 0;
}

.native-container {
  min-width: 0;
  position: relative;
}

.native-container:not(.native-container--detail-card) {
  display: grid;
  grid-auto-rows: max-content;
  align-content: start;
  gap: 12px;
}

.native-container--header {
  border-bottom: 1px solid var(--sc-app-border);
  padding-bottom: 12px;
}

.native-container--sheet:not(.native-container--detail-card) {
  gap: 16px;
}

.native-container--group:not(.native-container--detail-card) {
  border-top: 1px solid var(--sc-app-border);
  padding-top: var(--sc-space-sm);
}

/* Layout wrappers arrange columns only; the section separator belongs to
   business sections so nested wrappers never stack a duplicate border. */
.native-container--group.native-container--group--layout:not(.native-container--detail-card) {
  border-top: none;
  padding-top: 0;
}

.native-container:not(.native-container--detail-card)[data-collapsed='true'] > :not(.native-container-head) {
  display: none;
}

.native-container--field-drop-target.native-container--group,
.native-container--field-drop-target.native-container--page {
  outline: 1px dashed var(--sc-semantic-surface-interactive);
  outline-offset: 4px;
}

.native-container--config-hidden {
  border-top-style: dashed;
  opacity: 0.72;
  background: color-mix(in srgb, var(--sc-app-muted-bg) 64%, transparent);
}

.native-container--group > .native-container-head {
  padding-left: 0;
}

/* Official section-title typography: ``--sc-font-title-medium`` (16px / 24px,
 * weight 600) is the TDesign title the official detail and form compositions
 * print for a section head, and it is the same value the task/canonical section
 * heading already renders. The heading is presentation only - it carries no
 * contract meaning - so its type comes from the official token instead of a
 * locally invented size. */
.native-container-head h3 {
  margin: 0;
  font: var(--sc-font-title-medium);
  color: var(--sc-app-text-primary);
}

/* The collapsible heading is the same section head as the plain one, so it
 * carries the same official title typography; only its toggle behaviour is ours. */
.native-container-head > .sc-btn[data-appearance='context-action'] {
  font: var(--sc-font-title-medium);
  color: var(--sc-app-text-primary);
}

.native-container-head {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.native-container-drop-strip {
  font: var(--sc-font-body-small);
  min-height: 44px;
  display: grid;
  place-items: center;
  border: 1px dashed transparent;
  border-radius: 6px;
  margin-bottom: 8px;
  color: var(--sc-app-text-muted);
  pointer-events: auto;
}

.native-container--field-drop-target > .native-container-drop-strip {
  border-color: var(--sc-semantic-surface-interactive);
  background: var(--sc-app-panel-muted);
}

.native-container-title-editor {
  min-width: 140px;
  max-width: 260px;
  font-weight: 600;
}

.native-static-text {
  font: var(--sc-font-body-medium);
  margin: 0;

  overflow-wrap: anywhere;
}

.native-static-text--inline {
  color: var(--sc-app-text-secondary);
  padding: 2px 0;
}

.native-static-text--callout {
  border-radius: 6px;
  border: 1px solid var(--sc-app-info-border);
  background: var(--sc-app-info-bg);
  color: var(--sc-app-info-text);
  padding: 10px 12px;
}

.native-static-text--danger {
  color: var(--sc-app-danger-text);
}

.native-static-text--callout.native-static-text--danger {
  border-color: var(--sc-app-danger-border);
  background: var(--sc-app-danger-bg);
}

.native-static-text--warning {
  color: var(--sc-app-warning-text);
}

.native-static-text--callout.native-static-text--warning {
  border-color: var(--sc-app-warning-border);
  background: var(--sc-app-warning-bg);
}

.native-static-text--success {
  color: var(--sc-app-success-text);
}

.native-static-text--callout.native-static-text--success {
  border-color: var(--sc-app-success-border);
  background: var(--sc-app-success-bg);
}

.native-form-feedback {
  width: 100%;
  min-width: 0;
}

/* The feedback band is a full-width alert, so its body must fill the band and
   wrap. `inline-size: max-content` shrank the band to the content's intrinsic
   width, which is 0 for a body whose only child is a grid-typed fact: the fact
   then received ~2px and every character wrapped onto its own line, and a long
   copy was laid out on one clipped line instead of wrapping. A definite
   `minmax(0, 1fr)` track keeps the copy and any nested fact section wrapping
   inside the band at every width. */
.native-form-feedback__content {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  inline-size: 100%;
  max-inline-size: 100%;
  min-inline-size: 0;
  gap: var(--sc-space-xs);
}

.native-form-feedback__copy {
  margin: 0;
  overflow-wrap: anywhere;
}

.native-ribbon {
  font: var(--sc-font-mark-small);
  justify-self: end;
  max-width: 100%;
  border-radius: 4px;
  background: var(--sc-app-danger-text);
  color: var(--sc-semantic-text-on-interactive);
  padding: 4px 10px;

  overflow-wrap: anywhere;
}

.native-ribbon.text-bg-danger {
  background: var(--sc-app-danger-text);
}

.native-tabs {
  max-width: 100%;
  min-width: 0;
}

.native-tab {
  white-space: nowrap;
}

.native-tab--active {
  font-weight: 600;
}

.native-tab-panel {
  display: grid;
  gap: 14px;
  min-height: 0;
  min-width: 0;
  align-content: start;
}

.native-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  min-width: 0;
}

.native-actions--smart {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(104px, max-content));
  gap: 1px;
  border: 1px solid var(--sc-app-border);
  border-radius: 8px;
  overflow: hidden;
  background: var(--sc-app-border);
  width: fit-content;
  max-width: 100%;
}

.native-action-btn {
  gap: 6px;
  min-width: 0;
  max-width: 100%;
  white-space: nowrap;
}

.native-action-icon {
  flex: 0 0 auto;
  width: 18px;
  text-align: center;
  color: var(--sc-semantic-surface-interactive);
}

.native-action-label {
  min-width: 0;
  overflow-wrap: anywhere;
  font: var(--sc-font-body-medium);
}

.native-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.native-title-favorite {
  font-size: 27px;
  line-height: 1;
  padding: 0 2px;
}

.native-title-favorite:disabled {
  cursor: default;
  opacity: 0.65;
}

.native-title-input {
  flex: 1 1 auto;
  min-width: 0;
  font: var(--sc-font-headline-small);
  padding: 2px 0;
  letter-spacing: 0;
}

.native-title-text {
  font: var(--sc-font-headline-small);
  margin: 0;
  color: var(--sc-app-text-primary);

  overflow-wrap: break-word;
  line-break: strict;
  text-wrap: balance;
}

@media (max-width: 520px) {
  .native-title-row { align-items: flex-start; gap: 8px; }
  .native-title-favorite { flex: 0 0 auto; margin-top: 2px; font-size: 23px; }
  .native-title-input,
  .native-title-text {
  font: var(--sc-font-headline-small);   }
}
/* Card body is an adapter-owned public hook, not a vendor DOM selector. */
.native-container--detail-card :deep(.native-detail-card-body) {
  display: grid;
  gap: var(--sc-space-md);
  min-width: 0;
}
.native-container--detail-card[data-collapsed='true'] :deep(.native-detail-card-body) > :not(.native-container-head) {
  display: none;
}
.native-container--detail-group > .native-container-head h3,
.native-container--detail-group > .native-container-head > .sc-btn[data-appearance='context-action'] {
  font: var(--sc-font-body-medium);
  font-weight: 600;
}

/* ============================ Declared presentation vocabulary ============
 * The contract declares container presentation on the `styleToken` facet
 * (`d-flex`, `mb-3`, `card`, `alert alert-info`, `sc-project-stage`, ...).  This
 * block implements that vocabulary.  It used to be missing entirely, which made
 * every declared class a no-op and collapsed the project overview region into a
 * stack of full-width blocks.
 *
 * The doubled root class is deliberate: the container rules above already set a
 * container `display`, so a declared layout token must win on specificity rather
 * than on stylesheet order.
 */
.native-form-tree.native-form-tree .d-flex { display: flex; }
.native-form-tree.native-form-tree .d-inline-flex { display: inline-flex; }
.native-form-tree.native-form-tree .flex-row { flex-direction: row; }
.native-form-tree.native-form-tree .flex-wrap { flex-wrap: wrap; }
.native-form-tree.native-form-tree .justify-content-between { justify-content: space-between; }
.native-form-tree.native-form-tree .justify-content-start { justify-content: flex-start; }
.native-form-tree.native-form-tree .justify-content-end { justify-content: flex-end; }
.native-form-tree.native-form-tree .align-items-start { align-items: flex-start; }
.native-form-tree.native-form-tree .align-items-center { align-items: center; }
.native-form-tree.native-form-tree .gap-2 { gap: var(--sc-space-sm); }
.native-form-tree.native-form-tree .row {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  align-content: start;
}
.native-form-tree.native-form-tree .g-2 { gap: var(--sc-space-sm); }
.native-form-tree.native-form-tree .col-12 { grid-column: span 12; }
@media (min-width: 768px) {
  .native-form-tree.native-form-tree .col-md-6 { grid-column: span 6; }
  .native-form-tree.native-form-tree .w-md-50 { width: 50%; }
}
@media (min-width: 1024px) {
  .native-form-tree.native-form-tree .col-lg-3 { grid-column: span 3; }
  .native-form-tree.native-form-tree .col-lg-12 { grid-column: span 12; }
  .native-form-tree.native-form-tree .w-lg-25 { width: 25%; }
}

.native-form-tree.native-form-tree .mb-1 { margin-bottom: var(--sc-space-2xs); }
.native-form-tree.native-form-tree .mb-3 { margin-bottom: var(--sc-space-sm); }
.native-form-tree.native-form-tree .mb-4 { margin-bottom: var(--sc-space-md); }
.native-form-tree.native-form-tree .mt-1 { margin-top: var(--sc-space-2xs); }
.native-form-tree.native-form-tree .mt-2 { margin-top: var(--sc-space-xs); }
.native-form-tree.native-form-tree .mt8 { margin-top: var(--sc-space-xs); }
.native-form-tree.native-form-tree .mt16 { margin-top: var(--sc-space-md); }
.native-form-tree.native-form-tree .ps-1 { padding-inline-start: var(--sc-space-2xs); }
.native-form-tree.native-form-tree .pe-0 { padding-inline-end: 0; }
.native-form-tree.native-form-tree .pe-2 { padding-inline-end: var(--sc-space-xs); }
.native-form-tree.native-form-tree .px-0 { padding-inline: 0; }
.native-form-tree.native-form-tree .pb-2 { padding-bottom: var(--sc-space-xs); }
.native-form-tree.native-form-tree .pb-3 { padding-bottom: var(--sc-space-md); }
.native-form-tree.native-form-tree .h-100 { height: 100%; }
.native-form-tree.native-form-tree .w-100 { width: 100%; }

.native-form-tree.native-form-tree .h3 { font: var(--sc-font-title-medium); font-weight: var(--sc-product-text-weight-bold); }
.native-form-tree.native-form-tree .small { font: var(--sc-font-body-small); }
.native-form-tree.native-form-tree .fw-bold { font-weight: var(--sc-product-text-weight-bold); }
.native-form-tree.native-form-tree .text-muted { color: var(--sc-app-text-secondary); }
.native-form-tree.native-form-tree .text-danger { color: var(--sc-app-danger-text); }
.native-form-tree.native-form-tree .text-warning { color: var(--sc-app-warning-text); }

.native-form-tree.native-form-tree .card {
  padding: var(--sc-space-sm);
  border: 1px solid var(--sc-app-border);
  border-radius: var(--sc-product-panel-radius);
  background: var(--sc-app-panel);
}
.native-form-tree.native-form-tree .card-body { gap: var(--sc-space-xs); }
.native-form-tree.native-form-tree .content-group {
  gap: var(--sc-space-sm);
  padding: var(--sc-space-sm);
  border: 1px solid var(--sc-app-border);
  border-radius: var(--sc-product-panel-radius);
  background: var(--sc-app-subtle-bg);
}
.native-form-tree.native-form-tree .alert {
  padding: var(--sc-space-sm) var(--sc-space-md);
  border: 1px solid var(--sc-app-info-border);
  border-radius: var(--sc-product-radius-control);
  background: var(--sc-app-info-bg);
  color: var(--sc-app-info-text);
}
.native-form-tree.native-form-tree .alert-info {
  border-color: var(--sc-app-info-border);
  background: var(--sc-app-info-bg);
  color: var(--sc-app-info-text);
}
.native-form-tree.native-form-tree .alert-warning {
  border-color: var(--sc-app-warning-border);
  background: var(--sc-app-warning-bg);
  color: var(--sc-app-warning-text);
}
.native-form-tree.native-form-tree .alert-danger {
  border-color: var(--sc-app-danger-border);
  background: var(--sc-app-danger-bg);
  color: var(--sc-app-danger-text);
}

/* A declared layout container must apply to its declared children.  The
 * recursive child renderer inserts one wrapper node between a container and its
 * children; that wrapper is a renderer artifact and must not consume the layout
 * the container declares.  With `row` it swallowed the declared 12-column grid
 * (every `col-*` child fell outside it and stretched to the full width, so the
 * overview cards collapsed to one full-width card per row), and with `d-flex`
 * it swallowed the declared flex context.  Transparent wrapper = declared
 * layout reaches the declared children. */
.native-container.row > .native-form-tree,
.native-container.d-flex > .native-form-tree,
.native-container.d-inline-flex > .native-form-tree {
  display: contents;
}
/* A declared row child that declares no column token keeps the previous
 * full-width placement instead of collapsing into a single 1/12 track. */
.native-container.row > .native-form-tree > .native-container:not(.col-12):not(.col-md-6):not(.col-lg-3):not(.col-lg-12) {
  grid-column: 1 / -1;
}

/* Declared product region tokens.  The native arch declares these on its
 * containers; the renderer owns their visual output. */
.native-form-tree.native-form-tree .sc-project-overview { gap: var(--sc-space-md); }
.native-form-tree.native-form-tree .sc-project-overview__header { gap: var(--sc-space-md); }
.native-form-tree.native-form-tree .sc-project-title {
  font: var(--sc-font-title-large);
  font-weight: var(--sc-product-text-weight-bold);
}
.native-form-tree.native-form-tree .sc-project-stage {
  padding: var(--sc-space-sm) var(--sc-space-md);
  border: 1px solid var(--sc-app-border);
  border-radius: var(--sc-product-panel-radius);
  background: var(--sc-app-muted-bg);
}
.native-form-tree.native-form-tree .sc-project-stage__label { font-weight: var(--sc-product-text-weight-semibold); }
.native-form-tree.native-form-tree .sc-project-stage__desc { font: var(--sc-font-body-small); }
.native-form-tree.native-form-tree .sc-project-stage__req { gap: var(--sc-space-xs); }
.native-form-tree.native-form-tree .sc-project-next {
  padding: var(--sc-space-sm) var(--sc-space-md);
  border: 1px solid var(--sc-app-border-strong);
  border-radius: var(--sc-product-panel-radius);
  background: var(--sc-app-subtle-bg);
}
.native-form-tree.native-form-tree .sc-project-next__title { font-weight: var(--sc-product-text-weight-semibold); }
.native-form-tree.native-form-tree .sc-project-cards { gap: var(--sc-space-sm); }
.native-form-tree.native-form-tree .sc-project-cards__title { font-weight: var(--sc-product-text-weight-semibold); }
</style>
