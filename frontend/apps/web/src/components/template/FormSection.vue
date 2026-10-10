<template>
  <ScCard
    v-if="displayFields.length || fieldSelectionMode || fieldConfigEditable || slots.action || hint"
    :bordered="frame ? undefined : false"
    :class="['template-form-section', toneClass, { 'template-form-section--readonly': allFieldsReadonly, 'template-form-section--frameless': !frame }]"
    data-component="FormSection"
    data-semantic-component="FormSection"
    :data-state="allFieldsReadonly ? 'readonly' : 'editable'"
    :data-detail-section-composition="detailSectionDecision.adopted ? 'official-standard-detail' : 'contract-field-extension'"
    :data-detail-section-reason="detailSectionDecision.reason"
    :title="undefined"
    :appearance="preferReadonlyFacts ? 'fact' : 'form-section'"
  >
    <template v-if="showHead && $slots.action" #actions><slot name="action" /></template>
    <p v-if="hint" class="template-form-section-hint">{{ hint }}</p>
    <ScForm
      ref="sectionFormRef"
      :bare="!adoptedComposition"
      class="template-form-section-form"
      label-align="top"
      :rules="adoptedRules"
      :show-error-message="false"
    >
    <!-- 已采纳的只读详情：官方 detail 组合，t-card(:bordered="false") 内以
         t-descriptions 逐项呈现该 section 的契约字段事实（label = 字段标签，
         值槽复用与事实网格同一份只读取值：关系入口、富文本、办理动作、纯文本）。
         可编辑与明细控制不在只读事实的适用范围内，因此这里不复制它们。 -->
    <template v-for="(segment, segmentIndex) in detailFieldSegments" :key="segmentIndex">
    <ScDescriptions
      v-if="segment.facts"
      class="template-form-section-descriptions"
      data-detail-facts="official-standard-detail"
      :bordered="false"
      :column="detailFactColumns"
      :items="segment.fields"
      layout="horizontal"
      item-layout="horizontal"
    >
      <template #item="{ item }">
        <div class="detail-fact-value"
          :data-field-name="detailFactField(item).name"
          :data-field-key="detailFactField(item).key"
          :data-field-type="detailFactField(item).type"
          :data-widget-type="detailFactField(item).widget || undefined"
          :data-component-renderer="detailFactField(item).componentRenderer || undefined"
          :data-native-locator="detailFactField(item).nativeLocator || undefined"
          :data-source-position="detailFactField(item).sourcePosition ?? undefined">
        <ProfessionalBusinessValueControl
          v-if="usesProfessionalBusinessValue(detailFactField(item))"
          :field="detailFactField(item)"
          :control-id="fieldControlId(detailFactField(item))"
          :placeholder="detailFactField(item).inputPlaceholder || businessValuePlaceholderText(detailFactField(item))"
          @update:value="emitFieldChange(detailFactField(item), $event)"
        />
        <ScButton
          v-else-if="detailFactRelationEntry(item)"
          type="button"
          appearance="readonly-relation"
          variant="ghost"
          :title="readonlyText(detailFactField(item))"
          :aria-label="detailFactField(item).many2oneOpenLabel || `打开${detailFactField(item).label}`"
          @click="emitFieldChange(detailFactField(item), detailFactField(item).many2oneOpenToken)"
        ><span class="readonly-relation-label">{{ readonlyText(detailFactField(item)) }}</span></ScButton>
        <div
          v-else-if="detailFactField(item).type === 'html'"
          class="readonly-value readonly-value--html"
          v-html="readonlyHtml(detailFactField(item))"
        />
        <div
          v-else-if="taskActionFor(detailFactField(item))"
          role="button"
          tabindex="0"
          class="readonly-value readonly-value--action"
          :aria-label="`${taskActionLabel(detailFactField(item))}（办理动作）`"
          @click="taskActionRun(detailFactField(item))"
          @keydown.enter.prevent="taskActionRun(detailFactField(item))"
        >{{ taskActionLabel(detailFactField(item)) }}</div>
        <slot v-else name="readonly" :field="detailFactField(item)">
          <span class="readonly-value">{{ readonlyText(detailFactField(item)) }}</span>
        </slot>
        </div>
      </template>
    </ScDescriptions>
    <div v-else :class="['template-form-section-grid', `template-form-section-grid--columns-${columns}`]">
      <template v-if="displayFields.length">
        <div
          v-for="(field, index) in segment.fields"
          :key="field.key"
          :class="fieldClass(field, index, standardDetailComposition?.adopted.value ? segment.fields : fields)"
          :data-field-name="field.name"
          :data-validation-target="fieldValidationTarget(field)"
          :data-field-key="field.key"
          :data-field-type="field.type"
          :data-widget-type="field.widget || undefined"
          :data-native-locator="field.nativeLocator || undefined"
          :data-occurrence-index="field.occurrenceIndex || undefined"
          :data-source-position="field.sourcePosition ?? undefined"
          :data-field-state="fieldState(field)"
          :data-field-auth="field.auth || undefined"
          :data-component-key="field.componentKey || undefined"
          :data-component-readiness="field.componentReadiness || undefined"
          :data-component-renderer="field.componentRenderer || undefined"
          :data-contract-adapter="field.contractAdapter || undefined"
          :data-contract-component-version="field.contractVersion || undefined"
          :data-component-fallback="field.componentFallback || undefined"
          :data-form-semantic-role="field.semanticRole || undefined"
          :data-form-section-target="field.sectionNavigationTarget || undefined"
          :data-section-content-kind="field.sectionContentKind || undefined"
          :data-section-source-identity="field.sectionSourceIdentity || undefined"
          :tabindex="fieldSelectionMode ? 0 : undefined"
          :role="fieldSelectionMode ? 'button' : undefined"
          :aria-pressed="fieldSelectionMode ? selectedFieldKey === fieldIdentity(field) : undefined"
          :draggable="fieldOrderEditable"
          @click.capture="emitFieldSelect(field, $event)"
          @keydown.enter="emitFieldSelect(field, $event)"
          @keydown.space="emitFieldSelect(field, $event)"
          @dragstart.stop="emitFieldOrderDragStart(field, $event)"
          @dragend.stop="emitFieldOrderDragEnd(field)"
          @dragover.prevent="emitFieldOrderDragOver(field, $event)"
          @dragleave="emitFieldOrderDragLeave(field)"
          @drop.prevent="emitFieldOrderDrop(field, $event)"
          @mouseup="emitFieldOrderPointerDrop(field, $event)"
        >
          <div class="field-label-row">
            <label v-if="!fieldConfigEditable && !field.hideLabel && !detailCollectionOwnsVisibleTitle(field) && !attachmentControlOwnsVisibleTitle(field)" class="label" :for="fieldControlId(field)">
              {{ field.label }}
              <span v-if="field.required && !field.readonly" class="field-state field-state--required"><span aria-hidden="true">*</span><span class="sr-only">必填</span></span>
            </label>
            <ScInput
              v-else-if="fieldConfigEditable"
              class="field-label-editor"
              type="text"
              size="small"
              :model-value="field.label"
              :aria-label="`${field.label}显示名称`"
              @change="emitFieldLabelChange(field, $event)"
              @keydown.enter.prevent="emitFieldLabelChange(field, ($event.target as HTMLInputElement).value)"
            />
            <div v-if="fieldActionsFor(field).length" class="field-inline-config">
              <ScRadioGroup
                v-if="fieldActionsFor(field).length"
                class="field-inline-actions"
                :model-value="selectedFieldActionValue(field)"
                :options="fieldActionOptions(field)"
                :name="fieldActionGroupName(field)"
                :label="`${field.label}字段操作`"
                size="small"
                @change="emitFieldActionValue(field, $event)"
              />
            </div>
          </div>
          <ScFormItem
            :bare="!adoptedComposition"
            :class="['field-control-row', { 'field-control-row--favorite': field.favoriteToggle }]"
            :name="field.name"
            :rules="adoptedRules[field.name]"
            :status="field.invalid ? 'error' : undefined"
            :show-error-message="false"
          >
            <ScIconButton
              v-if="field.favoriteToggle"
              class="field-favorite-toggle"
              appearance="favorite-toggle"
              :class="{ 'field-favorite-toggle--active': field.favoriteToggle.active }"
              :aria-pressed="field.favoriteToggle.active"
              :label="field.favoriteToggle.label"
              :disabled="field.favoriteToggle.readonly"
              @click="emitFavoriteToggle(field)"
            >
              <ScIcon :name="field.favoriteToggle.active ? 'star' : 'star-outline'" :size="16" />
            </ScIconButton>
            <div class="field-control-main">
              <div
                v-if="declaresUnknownComponentRenderer(field)"
                class="field-fail-closed"
                role="alert"
                :data-field-fail-closed="String(field.componentRenderer || '')"
              >{{ failClosedRendererText(field) }}</div>
              <ScRadioGroup
                v-else-if="field.type === 'selection' && isRadioWidget(field) && !(preferReadonlyFacts && field.readonly)"
                class="native-radio-group"
                :model-value="String(field.inputValue ?? '')"
                :options="field.selectionOptions || []"
                :name="fieldRadioGroupName(field)"
                :label="field.label"
                :required="field.required"
                :invalid="field.invalid"
                :readonly="field.readonly"
                :described-by="fieldDescribedBy(field)"
                @change="emitFieldChange(field, $event)"
              />
              <ProfessionalBusinessValueControl
                v-else-if="usesProfessionalBusinessValue(field)"
                :field="field"
                :control-id="fieldControlId(field)"
                :placeholder="field.inputPlaceholder || businessValuePlaceholderText(field)"
                @update:value="emitFieldChange(field, $event)"
              />
              <ProfessionalBaseFieldControl
                v-else-if="usesProfessionalBaseField(field)"
                :field="field"
                :control-id="fieldControlId(field)"
                :described-by="fieldDescribedBy(field)"
                :placeholder="field.inputPlaceholder || (field.type === 'selection' ? selectPlaceholderText(field) : inputPlaceholderText(field))"
                :has-readonly-override="Boolean(slots.readonly)"
                @update:value="emitFieldChange(field, $event)"
              >
                <template #readonly="readonlySlot">
                  <slot name="readonly" v-bind="readonlySlot" />
                </template>
              </ProfessionalBaseFieldControl>
              <SceneFieldControl
                v-else-if="usesSceneFieldControl(field) && !(preferReadonlyFacts && field.readonly)"
                :field="sceneField(field)"
                :model-value="contractFormDriverValue(field)"
                @update:model-value="emitFieldChange(field, $event)"
              />
              <ProfessionalRelationFieldControl v-else-if="usesProfessionalMany2many(field) && relationAdapter" :field="field">
                <X2ManyRelationRenderer :field="field" :adapter="relationAdapter" @reload-requested="emitFieldAction(field, { key: 'reload-requested', label: '刷新', value: 'reload-requested' })" />
              </ProfessionalRelationFieldControl>
              <PaymentSettlementDetailCollectionControl
                v-else-if="usesPaymentSettlementDetailCollection(field) && relationAdapter"
                :field="field"
                :adapter="relationAdapter"
                @reload-requested="emitFieldAction(field, { key: 'reload-requested', label: '刷新', value: 'reload-requested' })"
              />
              <ProfessionalDetailCollectionControl
                v-else-if="usesProfessionalOne2many(field) && relationAdapter"
                :field="field"
                :adapter="relationAdapter"
              >
                <template #default="{ adapter: detailAdapter }">
                  <X2ManyRelationRenderer :field="field" :adapter="detailAdapter" @reload-requested="emitFieldAction(field, { key: 'reload-requested', label: '刷新', value: 'reload-requested' })" />
                </template>
              </ProfessionalDetailCollectionControl>
              <ProfessionalRelationFieldControl v-else-if="usesProfessionalMany2one(field) && field.readonly" :field="field">
                <slot name="readonly" :field="field">
                  <ScButton
                    v-if="field.many2oneOpenToken && !fieldHasEmptyValue(field)"
                    type="button"
                    appearance="readonly-relation"
                    variant="ghost"
                    :title="readonlyText(field)"
                    :aria-label="field.many2oneOpenLabel || `打开${field.label}`"
                    @click="emitFieldChange(field, field.many2oneOpenToken)"
                  ><span class="readonly-relation-label">{{ readonlyText(field) }}</span></ScButton>
                  <span v-else class="readonly-value">{{ readonlyText(field) }}</span>
                </slot>
              </ProfessionalRelationFieldControl>
              <!-- JSON 字段没有任何客户端编辑控件：契约声明只读可读展示，这里就必须按事实
                   呈现，而不是把对象值交给可编辑兜底控件。 -->
              <template v-else-if="field.readonly || isJsonField(field)">
                <slot name="readonly" :field="field">
                  <div
                    v-if="field.type === 'html'"
                    class="readonly-value readonly-value--html"
                    v-html="readonlyHtml(field)"
                  />
                  <div
                    v-else-if="taskActionFor(field)"
                    role="button"
                    tabindex="0"
                    class="readonly-value readonly-value--action"
                    :aria-label="`${taskActionLabel(field)}（办理动作）`"
                    @click="taskActionRun(field)"
                    @keydown.enter.prevent="taskActionRun(field)"
                  >{{ taskActionLabel(field) }}</div>
                  <span v-else class="readonly-value">{{ readonlyText(field) }}</span>
                </slot>
              </template>
              <template v-else-if="isLegacyComplexField(field)">
                <ScFileField
                  v-if="field.type === 'binary'"
                  :id="fieldControlId(field)"
                  :required="field.required"
                  :invalid="field.invalid"
                  :described-by="fieldDescribedBy(field)"
                  @change="emitBinaryFieldChange(field, $event[0] || null)"
                />
                <ProfessionalMany2oneFieldControl
                  v-else-if="usesProfessionalMany2one(field)"
                  :field="field"
                  :control-id="fieldControlId(field)"
                  :described-by="fieldDescribedBy(field)"
                  :placeholder="selectPlaceholderText(field)"
                  @select="emitFieldChange(field, $event)"
                  @query="emitMany2oneQuery(field, $event)"
                  @commit="emitMany2oneCommit(field, $event)"
                />
                <ScRelationField
                  v-else-if="field.type === 'many2one'"
                  :id="fieldControlId(field)"
                  class="input"
                  appearance="form-field"
                  :required="field.required"
                  :invalid="field.invalid"
                  :described-by="fieldDescribedBy(field)"
                  :model-value="String(field.inputValue ?? '')"
                  :query-value="field.relationQueryKeyword || ''"
                  :placeholder="selectPlaceholderText(field)"
                  @update:model-value="emitMany2oneCommit(field, $event)"
                  @update:query-value="emitMany2oneQuery(field, $event)"
                />
                <div v-else-if="isDateRangeWidget(field)" class="native-date-range">
                  <div class="native-date-range__control">
                    <label class="native-date-range__label" :for="fieldControlId(field)">开始日期</label>
                    <ScDateField
                      :id="fieldControlId(field)"
                      :model-value="String(field.inputValue ?? '')"
                      class="input"
                      appearance="form-field"
                      clearable
                      aria-label="开始日期"
                      :required="field.required"
                      :invalid="field.invalid"
                      :described-by="fieldDescribedBy(field)"
                      placeholder="请输入开始日期"
                      @update:model-value="emitFieldChange(field, $event)"
                    />
                  </div>
                  <ScIcon v-if="field.dateRangeEndField" class="native-date-range-separator" name="arrow-right" :size="16" />
                  <div v-if="field.dateRangeEndField" class="native-date-range__control">
                    <label class="native-date-range__label" :for="dateRangeEndControlId(field)">结束日期</label>
                    <ScDateField
                      :id="dateRangeEndControlId(field)"
                      :model-value="String(field.dateRangeEndInputValue ?? '')"
                      class="input"
                      appearance="form-field"
                      clearable
                      aria-label="结束日期"
                      :required="field.required"
                      :invalid="field.invalid"
                      :described-by="fieldDescribedBy(field)"
                      placeholder="请输入结束日期"
                      @update:model-value="emitDateRangeEndChange(field, $event)"
                    />
                  </div>
                </div>
                <div v-else-if="field.type === 'monetary'" class="field-monetary-control">
                  <ScInput
                    :id="fieldControlId(field)"
                    :model-value="String(field.inputValue ?? '')"
                    class="input"
                    appearance="form-field"
                    :required="field.required"
                    :status="field.invalid ? 'error' : 'default'"
                    :described-by="fieldDescribedBy(field)"
                    type="number"
                    :step="monetaryInputStep(field.digits, field.currencyLabel)"
                    :placeholder="field.inputPlaceholder || inputPlaceholderText(field)"
                    @update:model-value="emitFieldChange(field, $event)"
                  >
                    <template v-if="field.currencyLabel" #suffix>
                      <span class="field-currency-label">{{ field.currencyLabel }}</span>
                    </template>
                  </ScInput>
                </div>
              </template>
              <template v-else>
                <ScInput
                  :id="fieldControlId(field)"
                  :model-value="String(field.inputValue ?? '')"
                  class="input"
                  appearance="form-field"
                  :required="field.required"
                  :status="field.invalid ? 'error' : 'default'"
                  :described-by="fieldDescribedBy(field)"
                  :type="inputType(field.type)"
                  :placeholder="field.inputPlaceholder || inputPlaceholderText(field)"
                  @update:model-value="emitFieldChange(field, $event)"
                />
              </template>
            </div>
          </ScFormItem>
          <p v-if="field.helpText" :id="fieldHelpId(field)" class="field-supporting-text">{{ field.helpText }}</p>
          <p v-if="field.errorText" :id="fieldErrorId(field)" class="field-error-text" role="alert">{{ field.errorText }}</p>
        </div>
      </template>
      <slot v-else />
    </div>
    </template>
    </ScForm>
  </ScCard>
</template>

<script setup lang="ts">
import { computed, inject, onBeforeUnmount, onMounted, ref, useId, useSlots } from 'vue';
import { useNarrowViewport } from '../../composables/useNarrowViewport';
import { businessErrorKey } from '../../app/businessValidationError';
import { fieldHasEmptyValue, readonlyFactIsPresentable } from './formSection.mapper';
import { SceneFieldControl, useOptionalSceneUiKit } from '@sc/ui/form';
import ScCard from '../design-system/ScCard.vue';
import ScDescriptions from '../design-system/ScDescriptions.vue';
import ScForm from '../design-system/ScForm.vue';
import ScFormItem from '../design-system/ScFormItem.vue';
import type { ScFormInstance } from '../design-system/scFormContract';
import { buildContractFormRules, failedAdoptedFieldNames } from './contractFormValidationRules';
import { useOptionalStandardFormComposition } from '../../pages/contractForm/standardFormCompositionRuntime';
import { useOptionalStandardDetailComposition } from '../../pages/contractForm/standardDetailCompositionRuntime';
import { resolveStandardDetailFactLayout, partitionStandardDetailFields } from '../../app/presentation/standardDetailComposition';
import ScButton from '../design-system/ScButton.vue';
import ScDateField from '../design-system/ScDateField.vue';
import ScFileField from '../design-system/ScFileField.vue';
import ScIcon from '../design-system/ScIcon.vue';
import ScIconButton from '../design-system/ScIconButton.vue';
import ScInput from '../design-system/ScInput.vue';
import ScRelationField from '../design-system/ScRelationField.vue';
import ScRadioGroup, { type ScRadioOption } from '../design-system/ScRadioGroup.vue';
import ProfessionalBaseFieldControl from '../professional-fields/ProfessionalBaseFieldControl.vue';
import ProfessionalBusinessValueControl from '../professional-fields/ProfessionalBusinessValueControl.vue';
import ProfessionalDetailCollectionControl from '../professional-fields/ProfessionalDetailCollectionControl.vue';
import ProfessionalMany2oneFieldControl from '../professional-fields/ProfessionalMany2oneFieldControl.vue';
import ProfessionalRelationFieldControl from '../professional-fields/ProfessionalRelationFieldControl.vue';
import PaymentSettlementDetailCollectionControl from '../professional-fields/PaymentSettlementDetailCollectionControl.vue';
import { isProfessionalBaseFieldCandidate, resolveReadonlyEmptyText } from '../professional-fields/professionalBaseFieldModel';
import { isProfessionalBusinessValueField } from '../professional-fields/professionalBusinessValueModel';
import {
  isProfessionalDetailCollectionField,
  optionalDetailCollectionSpanClass,
} from '../professional-fields/professionalDetailCollectionModel';
import { isProfessionalRelationField } from '../professional-fields/professionalRelationFieldModel';
import { isPaymentSettlementDetailCollectionField } from '../professional-fields/paymentSettlementDetailCollectionModel';
import X2ManyRelationRenderer from './X2ManyRelationRenderer.vue';
import { formatDisplayValue } from '../../utils/display';
import { sanitizeReadonlyHtml } from '../../utils/sanitizeReadonlyHtml';
import { formatMonetaryDisplayValue, monetaryInputStep } from './formSection.mapper';
import type {
  FormSectionFieldAction,
  FormSectionFieldActionPayload,
  FormSectionFieldSchema,
  FormSectionFieldChange,
  TemplateFieldType,
} from './formSection.types';
import type { RelationFieldAdapter } from './relationField.types';
import { resolveInputPlaceholder, resolveSelectPlaceholder } from './placeholder.mapper';
import {
  normalizeContractFormDriverValue,
  toContractFormDriverFieldChange,
  toContractFormSceneField,
  usesContractFormDriverField,
} from './contractFormDriverField';
import {
  ScTaskActionResolverKey,
  type ScTaskActionDescriptor,
} from './taskActionResolver';
import { PROFESSIONAL_COMPONENT_RENDERERS } from '../../app/presentation/professionalComponentRegistry';

const props = withDefaults(defineProps<{
  title: string;
  hint?: string;
  /**
   * Whether this section draws its own surface frame (card + inline-size
   * container).  A declared layout container arranges its declared children
   * itself, so inside one a field batch is a layout item, not a section card;
   * `frame=false` keeps the declared child in the declared layout instead of
   * replacing it with a renderer-invented grid card.
   */
  frame?: boolean;
  columns?: 1 | 2 | 3;
  tone?: 'core' | 'advanced';
  fields?: FormSectionFieldSchema[];
  relationAdapter?: RelationFieldAdapter;
  fieldActions?: (field: FormSectionFieldSchema) => FormSectionFieldAction[];
  fieldOrderEditable?: boolean;
  fieldOrderIndex?: (field: FormSectionFieldSchema) => number;
  fieldOrderCount?: number;
  fieldOrderDraggingKey?: string;
  fieldOrderDropTargetKey?: string;
  fieldOrderDropPlacement?: 'before' | 'after' | '';
  fieldConfigEditable?: boolean;
  fieldGroupTitle?: string;
  fieldSelectionMode?: boolean;
  selectedFieldKey?: string;
  selectPlaceholder?: (label: string) => string;
  inputPlaceholder?: (label: string) => string;
  preferReadonlyFacts?: boolean;
  fillOrphanRows?: boolean;
}>(), {
  hint: '',
  frame: true,
  columns: 2,
  tone: 'core',
  fields: () => [],
  relationAdapter: undefined,
  fieldActions: undefined,
  fieldOrderEditable: false,
  fieldOrderIndex: undefined,
  fieldOrderCount: 0,
  fieldOrderDraggingKey: '',
  fieldOrderDropTargetKey: '',
  fieldOrderDropPlacement: '',
  fieldConfigEditable: false,
  fieldGroupTitle: '',
  fieldSelectionMode: false,
  selectedFieldKey: '',
  selectPlaceholder: (label: string) => resolveSelectPlaceholder(label),
  inputPlaceholder: (label: string) => resolveInputPlaceholder(label),
  preferReadonlyFacts: false,
  fillOrphanRows: true,
});

const sceneUiKit = useOptionalSceneUiKit();
const standardFormComposition = useOptionalStandardFormComposition();
const standardDetailComposition = useOptionalStandardDetailComposition();
const sectionFormRef = ref<unknown>(null);
const sectionId = `form-section-${useId().replace(/[^A-Za-z0-9_-]/g, '-')}`;
/**
 * Adopted sections render through the official form composition; every other
 * section keeps the composition it had. `bare` makes the adapters transparent
 * rather than emulated, so an unadopted surface is not silently half-adopted.
 */
const adoptedComposition = computed(() => standardFormComposition?.adopted.value === true && !props.fieldSelectionMode && !props.fieldConfigEditable);
const adoptedRules = computed(() => (adoptedComposition.value ? buildContractFormRules(props.fields) : {}));
/**
 * Whether this readonly section's facts render through the official detail
 * composition.
 *
 * The page-level term is the page's own readonly-record adoption, not the form
 * composition's: `record-detail` and `record-form` are the two halves of one
 * contract classification, so a page is never both and folding them together
 * would leave the facts layout unreachable. `bare` above still follows the form
 * composition, so a readonly page renders the facts without borrowing the
 * editable form's container or its rules.
 */
const detailSectionDecision = computed(() => resolveStandardDetailFactLayout(
  standardDetailComposition?.decision.value,
  {
    configurationMode: props.fieldSelectionMode || props.fieldConfigEditable,
    readonlyFacts: props.preferReadonlyFacts && allFieldsReadonly.value,
    fields: displayFields.value.map(detailFieldCapability),
  },
));
function detailFieldCapability(field: FormSectionFieldSchema) {
  return {
    type: field.type,
    dedicatedControl: Boolean(field.favoriteToggle)
      || declaresUnknownComponentRenderer(field)
      || usesPaymentSettlementDetailCollection(field)
      || Boolean(field.componentRenderer && !['ProfessionalBaseFieldControl', 'ProfessionalRelationFieldControl', 'ProfessionalBusinessValueControl'].includes(field.componentRenderer)),
  };
}
const detailFieldSegments = computed(() => partitionStandardDetailFields(
  displayFields.value,
  (field) => resolveStandardDetailFactLayout(standardDetailComposition?.decision.value, {
    configurationMode: props.fieldSelectionMode || props.fieldConfigEditable,
    readonlyFacts: props.preferReadonlyFacts && allFieldsReadonly.value,
    fields: [detailFieldCapability(field)],
  }).adopted,
));

/**
 * The official detail page arranges its facts in a label/value table. A narrow
 * viewport keeps one fact per row so a long business value cannot be squeezed
 * into half a phone screen; the contract's own column count is kept elsewhere.
 */
const narrowDetailFactViewport = useNarrowViewport(640);
const detailFactColumns = computed(() => (
  narrowDetailFactViewport.value ? 1 : Math.max(1, Math.min(3, Number(props.columns) || 2))
));
const formSectionDomId = `form-section-${useId().replace(/[^A-Za-z0-9_-]/g, '-')}`;

/**
 * Generic validation of this section, reported as business field codes.
 *
 * The official engine decides when its rules run and how a failure is
 * summarised; the caller decides what a rejected business field means. No
 * second draft is kept: the rules read the values the page already holds.
 */
async function validateAdoptedSection(): Promise<string[]> {
  if (!adoptedComposition.value) return [];
  const instance = (sectionFormRef.value as ScFormInstance | null) || null;
  if (!instance) {
    // A section that hands rules to the engine but has no engine to run them
    // cannot answer "passed"; it must not be read as one.
    if (adoptedRuleFieldNames().length) {
      throw new Error('adopted form section has no engine instance for its declared rules');
    }
    return [];
  }
  const rejected = failedAdoptedFieldNames(await instance.validate());
  if (rejected === null) {
    throw new Error('adopted form engine returned an unrecognised validation result');
  }
  return rejected;
}

/**
 * Positions this section really hands to the official engine.
 *
 * Only a rendered position has a form item, and the engine evaluates rules for
 * registered items only. Reporting the rendered-and-ruled set keeps the save
 * chain honest: a required position that is not rendered here is *not* covered,
 * so the page-level precheck must keep deciding it.
 */
function adoptedRuleFieldNames(): string[] {
  if (!adoptedComposition.value) return [];
  const rules = adoptedRules.value;
  return displayFields.value
    .map((field) => String(field.name || '').trim())
    .filter((name) => Boolean(name && rules[name]));
}

onMounted(() => {
  standardFormComposition?.register({
    sectionId,
    ruleFieldNames: adoptedRuleFieldNames,
    validate: validateAdoptedSection,
  });
});
onBeforeUnmount(() => {
  standardFormComposition?.unregister(sectionId);
});

const emit = defineEmits<{
  (e: 'field-change', payload: FormSectionFieldChange): void;
  (e: 'field-action', payload: FormSectionFieldActionPayload): void;
  (e: 'field-order-move', payload: { field: FormSectionFieldSchema; delta: number }): void;
  (e: 'field-order-drag-start', payload: { field: FormSectionFieldSchema; event: DragEvent }): void;
  (e: 'field-order-drag-over', payload: { field: FormSectionFieldSchema; groupTitle: string; placement: 'before' | 'after' | '' }): void;
  (e: 'field-order-drag-leave', payload: { field: FormSectionFieldSchema; groupTitle: string }): void;
  (e: 'field-order-drop', payload: { field: FormSectionFieldSchema; groupTitle: string; placement: 'before' | 'after' | '' }): void;
  (e: 'field-order-drag-end', payload: { field: FormSectionFieldSchema }): void;
  (e: 'field-label-change', payload: { field: FormSectionFieldSchema; label: string }): void;
  (e: 'field-add-after', payload: { field: FormSectionFieldSchema; groupTitle: string }): void;
  (e: 'field-select', payload: { field: FormSectionFieldSchema; groupTitle: string }): void;
}>();

/**
 * Register the position the error layer may send the user to.
 *
 * Only a position the user can correct is registered: a read-only occurrence of
 * the same field keeps its display role and is not advertised as an error
 * correction site. Registering the key does not make a position focusable by
 * itself; the focus layer still requires a real, enabled control inside it.
 */
function fieldValidationTarget(field: FormSectionFieldSchema) {
  if (props.fieldSelectionMode || props.fieldConfigEditable || field.readonly) return undefined;
  return businessErrorKey({ fieldCode: field.name, row: null }) || undefined;
}

function fieldControlId(field: FormSectionFieldSchema) {
  return `${formSectionDomId}-field-${String(field.key || field.name).replace(/[^A-Za-z0-9_-]/g, '-')}`;
}

function fieldActionGroupName(field: FormSectionFieldSchema) {
  return `${fieldControlId(field)}-action`;
}

function fieldRadioGroupName(field: FormSectionFieldSchema) {
  return `${fieldControlId(field)}-radio`;
}

function fieldHelpId(field: FormSectionFieldSchema) {
  return `${fieldControlId(field)}-help`;
}

function fieldErrorId(field: FormSectionFieldSchema) {
  return `${fieldControlId(field)}-error`;
}

function fieldDescribedBy(field: FormSectionFieldSchema) {
  const ids = [];
  if (field.helpText) ids.push(fieldHelpId(field));
  if (field.errorText) ids.push(fieldErrorId(field));
  return ids.length ? ids.join(' ') : undefined;
}

const slots = useSlots();
const toneClass = computed(() => (props.tone === 'advanced' ? 'template-form-section--advanced' : 'template-form-section--core'));
const showHead = computed(() => Boolean(props.title || slots.action));
const allFieldsReadonly = computed(() => props.fields.length > 0 && props.fields.every((field) => field.readonly));
const knownComponentRenderers: ReadonlySet<string> = new Set<string>(PROFESSIONAL_COMPONENT_RENDERERS);

function declaresUnknownComponentRenderer(field: FormSectionFieldSchema) {
  const renderer = field.componentRenderer;
  return Boolean(renderer) && !knownComponentRenderers.has(renderer);
}

function failClosedRendererText(field: FormSectionFieldSchema) {
  return `字段渲染器未注册：${String(field.componentRenderer || '')}`;
}

function isJsonField(field: FormSectionFieldSchema) {
  return String(field.type || '').trim().toLowerCase() === 'json';
}

function isLegacyComplexField(field: FormSectionFieldSchema) {
  return ['many2one', 'binary', 'monetary'].includes(String(field.type || '').trim().toLowerCase())
    || isDateRangeWidget(field);
}

function isRelationEditorField(field: FormSectionFieldSchema) {
  return ['many2many', 'one2many'].includes(String(field.type || '').trim().toLowerCase());
}

function usesProfessionalBaseField(field: FormSectionFieldSchema) {
  const candidate = isProfessionalBaseFieldCandidate(String(field.type || ''), fieldWidget(field));
  if (!candidate) return false;
  return !field.componentRenderer || field.componentRenderer === 'ProfessionalBaseFieldControl';
}

function usesProfessionalBusinessValue(field: FormSectionFieldSchema) {
  return field.componentRenderer === 'ProfessionalBusinessValueControl'
    && isProfessionalBusinessValueField(field);
}

function usesProfessionalMany2one(field: FormSectionFieldSchema) {
  return field.type === 'many2one'
    && field.componentRenderer === 'ProfessionalRelationFieldControl'
    && isProfessionalRelationField(field);
}

function usesProfessionalMany2many(field: FormSectionFieldSchema) {
  return field.type === 'many2many'
    && field.componentRenderer === 'ProfessionalRelationFieldControl'
    && isProfessionalRelationField(field);
}

function usesProfessionalOne2many(field: FormSectionFieldSchema) {
  return field.type === 'one2many'
    && field.componentRenderer === 'ProfessionalDetailCollectionControl'
    && isProfessionalDetailCollectionField(field);
}

function usesPaymentSettlementDetailCollection(field: FormSectionFieldSchema) {
  return isPaymentSettlementDetailCollectionField(field);
}

function detailCollectionOwnsVisibleTitle(field: FormSectionFieldSchema) {
  if (!props.relationAdapter) return false;
  return usesProfessionalOne2many(field) || usesPaymentSettlementDetailCollection(field);
}

function attachmentControlOwnsVisibleTitle(field: FormSectionFieldSchema) {
  const relation = (field as { descriptor?: { relation?: string } }).descriptor?.relation;
  return usesProfessionalMany2many(field) && String(relation || '').trim().toLowerCase() === 'ir.attachment';
}

function usesSceneFieldControl(field: FormSectionFieldSchema) {
  if (isProfessionalRelationField(field) || isProfessionalDetailCollectionField(field) || isPaymentSettlementDetailCollectionField(field)) return false;
  return usesContractFormDriverField(field, sceneUiKit?.kit.value || 'sc-native');
}

function sceneField(field: FormSectionFieldSchema) {
  const type = String(field.type || '').trim().toLowerCase();
  return toContractFormSceneField(
    field,
    fieldControlId(field),
    field.inputPlaceholder || (type === 'selection' ? selectPlaceholderText(field) : inputPlaceholderText(field)),
  );
}

function contractFormDriverValue(field: FormSectionFieldSchema) {
  return normalizeContractFormDriverValue(field.inputValue, String(field.type || ''));
}

function defaultSpanClass(type: TemplateFieldType) {
  return isMultilineField(type) || isRelationEditorType(type) ? 'field--full' : 'field--normal';
}

function isMultilineField(type: TemplateFieldType) {
  return ['text', 'html'].includes(String(type || '').trim().toLowerCase());
}

function isRelationEditorType(type: TemplateFieldType) {
  return ['many2many', 'one2many'].includes(String(type || '').trim().toLowerCase());
}

function inputType(type: TemplateFieldType) {
  const t = String(type || '').trim().toLowerCase();
  if (t === 'date') return 'date';
  if (t === 'datetime') return 'datetime-local';
  if (['integer', 'float', 'monetary'].includes(t)) return 'number';
  return 'text';
}

function fieldWidget(field: FormSectionFieldSchema) {
  return String(field.widget || '').trim().toLowerCase();
}

function fieldWidgetClass(field: FormSectionFieldSchema) {
  const widget = fieldWidget(field);
  return widget ? `field--widget-${widget.replace(/[^a-z0-9_-]/g, '-')}` : '';
}

function fieldIdentity(field: FormSectionFieldSchema) {
  return String(field.name || field.key || '').trim();
}

// TDesign 24 栅格系统字段宽度映射
const FIELD_SPAN_UNITS: Record<string, number> = {
  'field--compact': 8,
  'field--normal': 12,
  'field--half': 12,
  'field--wide': 16,
  'field--full': 24,
};

function fieldSpanUnits(spanClass: string): number {
  return FIELD_SPAN_UNITS[spanClass] ?? 12;
}

function fieldSpanClass(field: FormSectionFieldSchema, index: number, gridFields: readonly FormSectionFieldSchema[]) {
  const explicitSpan = field.spanClass || '';
  const configuredBase = explicitSpan || (defaultSpanClass(field.type) === 'field--full' || fieldWidget(field) === 'textarea'
    ? 'field--full'
    : 'field--normal');
  const base = optionalDetailCollectionSpanClass(field, configuredBase);
  if (base === 'field--full') return base;
  if (!props.fillOrphanRows) return base;

  // Orphan-column fill (TDesign 24 栅格系统): a normal/half-width field that
  // starts a new row alone leaves blank cells when its row has no pairing fields —
  // either because it is the last field of the section, or because the next field
  // spans the full row. Widen such a field to span the full row (24 units).
  let units = 0;
  for (let i = 0; i < index; i++) {
    const prev = gridFields[i];
    const prevSpan = prev.spanClass || defaultSpanClass(prev.type);
    units += fieldSpanUnits(prevSpan);
  }
  const isLast = index === gridFields.length - 1;
  const next = gridFields[index + 1];
  const nextSpan = next ? (next.spanClass || defaultSpanClass(next.type)) : '';
  const nextIsFullRow = nextSpan === 'field--full';
  if (units % 24 === 0 && (isLast || nextIsFullRow)) {
    return 'field--full';
  }
  return base;
}

function fieldClass(field: FormSectionFieldSchema, index: number, gridFields: readonly FormSectionFieldSchema[]) {
  const fieldKey = fieldIdentity(field);
  const isDropTarget = props.fieldOrderDropTargetKey === fieldKey && props.fieldOrderDraggingKey !== fieldKey;
  return [
    'field',
    fieldSpanClass(field, index, gridFields),
    fieldWidgetClass(field),
    {
      'field--order-editable': props.fieldOrderEditable,
      'field--order-dragging': props.fieldOrderDraggingKey === fieldKey,
      'field--order-drop-target': isDropTarget,
      'field--order-drop-before': isDropTarget && props.fieldOrderDropPlacement !== 'after',
      'field--order-drop-after': isDropTarget && props.fieldOrderDropPlacement === 'after',
      'field--selectable': props.fieldSelectionMode,
      'field--selected': props.fieldSelectionMode && props.selectedFieldKey === fieldKey,
      'field--config-hidden': props.fieldSelectionMode && isFieldMarkedHidden(field),
      'field--empty': fieldHasEmptyValue(field),
      'field--readonly-empty-relation': isReadonlyEmptyRelation(field),
      'field--label-free': !props.fieldConfigEditable && !fieldActionsFor(field).length
        && (field.hideLabel || detailCollectionOwnsVisibleTitle(field) || attachmentControlOwnsVisibleTitle(field)),
    },
  ];
}

function isReadonlyEmptyRelation(field: FormSectionFieldSchema) {
  if (!field.readonly || !props.relationAdapter || !isRelationEditorField(field)) return false;
  if (field.type === 'one2many') {
    return props.relationAdapter.visibleOne2manyRows(field.name).length === 0;
  }
  return props.relationAdapter.selectedRelationOptions(field.name).length === 0
    && props.relationAdapter.relationIds(field.name).length === 0;
}


function fieldState(field: FormSectionFieldSchema) {
  if (field.invalid) return 'invalid';
  if (field.readonly) return 'readonly';
  if (field.required) return 'required';
  if (fieldHasEmptyValue(field)) return 'empty';
  return 'ready';
}

function isRadioWidget(field: FormSectionFieldSchema) {
  return fieldWidget(field) === 'radio';
}

function isDateRangeWidget(field: FormSectionFieldSchema) {
  return fieldWidget(field) === 'daterange';
}

function dateRangeEndControlId(field: FormSectionFieldSchema) {
  return `${fieldControlId(field)}-end`;
}

function selectPlaceholderText(field: FormSectionFieldSchema) {
  return props.selectPlaceholder(field.label);
}

// A business value is typed into the field unless the field really is a choice
// control.  A contract that carries no placeholder must not turn an amount into
// "请选择…": that reads as a picker and misstates the control the user is on.
function businessValuePlaceholderText(field: FormSectionFieldSchema) {
  return field.type === 'selection' ? selectPlaceholderText(field) : inputPlaceholderText(field);
}

function inputPlaceholderText(field: FormSectionFieldSchema) {
  return props.inputPlaceholder(field.label);
}

function readonlyText(field: FormSectionFieldSchema) {
  const fieldType = String(field.type || field.descriptor?.ttype || field.descriptor?.type || '').trim().toLowerCase();
  if (fieldType === 'monetary') {
    return formatMonetaryDisplayValue(
      field.value,
      field.digits,
      field.currencyLabel,
      'zh-CN',
      resolveReadonlyEmptyText(field, '-'),
    );
  }
  const normalizedValue = ['date', 'datetime', 'many2one'].includes(fieldType)
    && String(field.value).trim().toLowerCase() === 'false'
    ? ''
    : field.value;
  return formatDisplayValue(
    normalizedValue,
    { ...(field.descriptor || {}), type: fieldType || field.descriptor?.type },
    { emptyText: resolveReadonlyEmptyText(field, '-') },
  );
}

const taskActionResolver = inject(ScTaskActionResolverKey, null);

const displayFields = computed(() => props.fields.filter((field) => {
  if (!props.preferReadonlyFacts || props.fieldSelectionMode || props.fieldConfigEditable) return true;
  return readonlyFactIsPresentable(field, Boolean(taskActionFor(field)));
}));

/**
 * Resolve a readonly fact into a clickable business action, when the page
 * layer has registered a task-action resolver (see taskActionResolver.ts).
 * Returns null for plain facts - they keep rendering as readonly text.
 */
function taskActionFor(field: FormSectionFieldSchema): ScTaskActionDescriptor | null {
  if (!taskActionResolver) return null;
  return taskActionResolver(field);
}

function taskActionLabel(field: FormSectionFieldSchema): string {
  const action = taskActionFor(field);
  return action ? action.label : '';
}

function taskActionRun(field: FormSectionFieldSchema) {
  const action = taskActionFor(field);
  if (action) void action.run();
}

function readonlyHtml(field: FormSectionFieldSchema) {
  return sanitizeReadonlyHtml(field.value);
}

/**
 * The descriptions slot hands back one item; the item *is* the contract field
 * the entry was built from, so the value is read from the same object the fact
 * grid reads and stays reactive. The cast exists only because the primitive's
 * slot payload is generic.
 */
function detailFactField(item: unknown): FormSectionFieldSchema {
  return item as FormSectionFieldSchema;
}

function detailFactRelationEntry(item: unknown): boolean {
  const field = detailFactField(item);
  return Boolean(field.many2oneOpenToken && !fieldHasEmptyValue(field));
}

function fieldActionsFor(field: FormSectionFieldSchema) {
  return props.fieldActions?.(field) || [];
}

function fieldActionOptions(field: FormSectionFieldSchema): ScRadioOption[] {
  return fieldActionsFor(field).map((action) => ({
    value: action.value,
    label: action.label,
    disabled: Boolean(action.disabled),
  }));
}

function selectedFieldActionValue(field: FormSectionFieldSchema) {
  return fieldActionsFor(field).find((action) => action.checked)?.value || '';
}

function emitFieldActionValue(field: FormSectionFieldSchema, value: string | number | boolean) {
  const action = fieldActionsFor(field).find((candidate) => String(candidate.value) === String(value));
  if (action) emitFieldAction(field, action);
}

function isFieldMarkedHidden(field: FormSectionFieldSchema) {
  return fieldActionsFor(field).some((action) => (
    Boolean(action.checked)
    && String(action.value || action.key || '').trim().toLowerCase() === 'hide'
  ));
}

function emitFieldChange(field: FormSectionFieldSchema, value: string | number | boolean | null) {
  emit('field-change', toContractFormDriverFieldChange(field, value));
}

function emitBinaryFieldChange(field: FormSectionFieldSchema, file: File | null) {
  if (!file) {
    emitFieldChange(field, null);
    return;
  }
  const reader = new FileReader();
  reader.onload = () => {
    const result = String(reader.result || '');
    const separatorIndex = result.indexOf(',');
    emit('field-change', {
      occurrenceKey: field.key,
      name: field.name,
      type: field.type,
      widget: field.widget,
      value: separatorIndex >= 0 ? result.slice(separatorIndex + 1) : result,
      descriptor: field.descriptor,
      fileName: file.name,
    });
  };
  reader.onerror = () => emitFieldChange(field, null);
  reader.readAsDataURL(file);
}

function emitMany2oneQuery(field: FormSectionFieldSchema, value: string) {
  emit('field-change', {
    occurrenceKey: field.key,
    name: field.name,
    type: field.type,
    widget: field.widget,
    value,
    action: 'query',
    descriptor: field.descriptor,
  });
}

function emitMany2oneCommit(field: FormSectionFieldSchema, value: string) {
  emit('field-change', {
    occurrenceKey: field.key,
    name: field.name,
    type: field.type,
    widget: field.widget,
    value,
    action: 'commit',
    descriptor: field.descriptor,
  });
}

function emitDateRangeEndChange(field: FormSectionFieldSchema, value: string | number | boolean | null) {
  const name = String(field.dateRangeEndField || '').trim();
  if (!name) return;
  emit('field-change', {
    name,
    type: field.type,
    widget: field.widget,
    value,
    descriptor: field.descriptor,
  });
}

function emitFavoriteToggle(field: FormSectionFieldSchema) {
  const favorite = field.favoriteToggle;
  if (!favorite || favorite.readonly) return;
  emit('field-change', {
    name: favorite.name,
    type: 'boolean',
    value: !favorite.active,
    descriptor: favorite.descriptor,
  });
}

function emitFieldAction(field: FormSectionFieldSchema, action: FormSectionFieldAction) {
  if (action.disabled) return;
  emit('field-action', { field, action });
}

function emitFieldOrderDragStart(field: FormSectionFieldSchema, event: DragEvent) {
  if (!props.fieldOrderEditable) return;
  emit('field-order-drag-start', { field, event });
}

function resolveFieldOrderDropPlacement(event?: DragEvent | MouseEvent): 'before' | 'after' | '' {
  const target = event?.currentTarget as HTMLElement | null | undefined;
  if (!target || typeof target.getBoundingClientRect !== 'function') return '';
  const rect = target.getBoundingClientRect();
  if (!rect.height) return '';
  const clientY = Number(event?.clientY || 0);
  if (!Number.isFinite(clientY) || clientY <= 0) return '';
  return clientY >= rect.top + rect.height / 2 ? 'after' : 'before';
}

function emitFieldOrderDragOver(field: FormSectionFieldSchema, event?: DragEvent) {
  if (!props.fieldOrderEditable) return;
  emit('field-order-drag-over', { field, groupTitle: props.fieldGroupTitle || '', placement: resolveFieldOrderDropPlacement(event) });
}

function emitFieldOrderDragLeave(field: FormSectionFieldSchema) {
  if (!props.fieldOrderEditable) return;
  emit('field-order-drag-leave', { field, groupTitle: props.fieldGroupTitle || '' });
}

function emitFieldOrderDrop(field: FormSectionFieldSchema, event?: DragEvent | MouseEvent) {
  if (!props.fieldOrderEditable) return;
  emit('field-order-drop', { field, groupTitle: props.fieldGroupTitle || '', placement: resolveFieldOrderDropPlacement(event) });
}

function emitFieldOrderPointerDrop(field: FormSectionFieldSchema, event: MouseEvent) {
  if (!props.fieldOrderEditable || !props.fieldOrderDraggingKey) return;
  emitFieldOrderDrop(field, event);
  emitFieldOrderDragEnd(field);
}

function emitFieldOrderDragEnd(field: FormSectionFieldSchema) {
  if (!props.fieldOrderEditable) return;
  emit('field-order-drag-end', { field });
}

function emitFieldLabelChange(field: FormSectionFieldSchema, label: string) {
  if (!props.fieldConfigEditable) return;
  const normalized = String(label || '').trim();
  if (!normalized || normalized === field.label) return;
  emit('field-label-change', { field, label: normalized });
}

function isInteractiveFieldTarget(event?: Event) {
  const target = event?.target;
  const targetElement = target as unknown as { closest?: (selector: string) => unknown };
  if (!target || typeof targetElement.closest !== 'function') return false;
  if (props.fieldSelectionMode) {
    return Boolean(targetElement.closest('button, a, .field-inline-config, .field-label-editor'));
  }
  return Boolean(targetElement.closest('button, input, select, textarea, a, .field-inline-config, .field-control-row'));
}

function emitFieldSelect(field: FormSectionFieldSchema, event?: Event) {
  if (!props.fieldSelectionMode) return;
  if (isInteractiveFieldTarget(event)) return;
  event?.preventDefault();
  event?.stopPropagation();
  emit('field-select', { field, groupTitle: props.fieldGroupTitle || '' });
}
</script>

<style scoped>
.template-form-section {
  grid-column: 1 / -1;
  min-width: 0;
  container-type: inline-size;
}

/* A declared layout container declares how its declared children are
 * arranged (flex items / grid columns).  Inside one, the field batch is a
 * declared child and must be a layout item, not a section card: without this
 * the frame contributed a full-width grid track plus `inline-size`
 * containment, so its intrinsic width collapsed to 0 and the declared child
 * vanished inside the declared layout (project stage row). */
.template-form-section--frameless {
  grid-column: auto;
  min-width: 0;
  max-width: 100%;
  container-type: normal;
}

.template-form-section-hint {
  font: var(--sc-font-body-small);
  margin: -4px 0 10px;
  color: var(--sc-app-text-primary);
}

.field-supporting-text,
.field-error-text {
  font: var(--sc-font-body-small);
  margin: 6px 0 0;

}

.field-supporting-text {
  color: var(--sc-semantic-text-muted);
}

.field-error-text {
  color: var(--sc-app-danger-text);
}

.field-fail-closed {
  font: var(--sc-font-body-small);
  padding: 6px 8px;
  border: 1px solid var(--sc-app-danger-text);
  border-radius: var(--sc-radius-sm, 4px);

  color: var(--sc-app-danger-text);
}

.template-form-section-grid {
  display: grid;
  grid-template-columns: repeat(24, minmax(0, 1fr));
  row-gap: calc(var(--sc-pattern-task-form-field-gap, 12) * 1px);
  column-gap: calc(var(--sc-pattern-task-form-column-gap, 24) * 1px);
  min-width: 0;
}

/* Native group/page col="1" is authoritative: every child owns the only
   available column even when its field descriptor has no reliable type. */
.template-form-section-grid--columns-1 > .field {
  grid-column: 1 / -1;
}

/* 小屏幕：1 列布局，减小间隙 */
@container (max-width: 479px) {
  .template-form-section-grid {
    grid-template-columns: minmax(0, 1fr);
    column-gap: 0;
  }
}

/* 中等屏幕：2 列布局 */
@container (min-width: 480px) and (max-width: 959px) {
  .template-form-section-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    column-gap: calc(var(--sc-pattern-task-form-column-gap, 24) * 1px);
  }
}

.template-form-section--readonly .template-form-section-grid {
  row-gap: 10px;
}

.field {
  display: grid;
  gap: 0;
  min-width: 0;
  align-content: start;
  border: 1px solid transparent;
  border-radius: 6px;
  transition: border-color 120ms ease, box-shadow 120ms ease, background-color 120ms ease, opacity 120ms ease;
}

.field--order-editable {
  padding: 6px;
  margin: -6px;
  cursor: default;
  background: color-mix(in srgb, var(--sc-app-info-bg) 42%, transparent);
}

.field--order-dragging {
  opacity: 0.56;
}

.field--order-drop-target {
  border-color: var(--sc-semantic-surface-interactive);
  background: var(--sc-app-info-bg);
}

.field--order-drop-before {
  box-shadow: inset 0 3px 0 var(--sc-semantic-surface-interactive);
}

.field--order-drop-after {
  box-shadow: inset 0 -3px 0 var(--sc-semantic-surface-interactive);
}

.field--selectable {
  padding: 6px;
  margin: -6px;
  cursor: pointer;
}

.field--selectable:hover,
.field--selectable:focus-visible {
  border-color: var(--sc-app-border-strong);
  background: var(--sc-app-hover-bg);
  outline: none;
}

.field--selected {
  border-color: var(--sc-semantic-surface-interactive);
  background: var(--sc-app-info-bg);
  box-shadow: 0 0 0 3px var(--sc-app-focus-ring);
}

.field--config-hidden {
  border-style: dashed;
  opacity: 0.68;
  background: color-mix(in srgb, var(--sc-app-muted-bg) 72%, transparent);
}

/* TDesign 24 栅格系统字段宽度映射（大屏幕默认） */
.field--compact {
  grid-column: span 8;
}

.field--normal,
.field--half {
  grid-column: span 12;
}

.field--wide {
  grid-column: span 16;
}

.field--full {
  grid-column: span 24;
}

/* 小屏幕：1 列布局，所有字段全宽 */
@container (max-width: 479px) {
  .field--compact,
  .field--normal,
  .field--half,
  .field--wide,
  .field--full {
    grid-column: 1 / -1;
  }
}

/* 中等屏幕：2 列布局 */
@container (min-width: 480px) and (max-width: 959px) {
  .field--compact,
  .field--normal,
  .field--half {
    grid-column: span 1;
  }
  .field--wide,
  .field--full {
    grid-column: 1 / -1;
  }
}

.field-label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sc-pattern-task-form-label-row-gap, 8px);
  flex-wrap: wrap;
  min-width: 0;
  margin-bottom: var(--sc-pattern-task-form-label-row-margin-bottom, 3px);
}

.label {
  font: var(--sc-font-mark-small);
  color: var(--sc-app-text-primary);
  margin: 0;
  min-width: 0;
  overflow-wrap: anywhere;
}

.field-label-editor {
  flex: 1 1 140px;
  min-width: 96px;
  max-width: 220px;
  font-weight: 600;
}

.field-state {
  display: inline-flex;
  align-items: center;
  min-height: 18px;
  margin-left: 4px;
  padding: 0 5px;
  border: 1px solid var(--sc-app-border);
  border-radius: 999px;
  color: var(--sc-app-text-primary);
  font-size: 10px;
  font-weight: 600;
  line-height: 1;
  vertical-align: 1px;
}

.field-state--required {
  min-height: auto;
  margin-left: 2px;
  padding: 0;
  border: 0;
  color: var(--sc-app-danger-text);
  font-size: 14px;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.field-inline-config {
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: var(--sc-pattern-task-form-inline-config-gap, 6px);
  min-width: 0;
}

.field--order-editable {
  cursor: grab;
}

.field--order-editable:active {
  cursor: grabbing;
}

.field-inline-actions {
  font: var(--sc-font-body-small);
  display: inline-flex;
  align-items: center;
  gap: var(--sc-pattern-task-form-inline-actions-gap, 8px);
  color: var(--sc-semantic-text-muted);

}

.field-control-row {
  display: flex;
  align-items: center;
  flex-wrap: nowrap;
  gap: var(--sc-pattern-task-form-control-row-gap, 6px);
  min-width: 0;
}

.field-control-main {
  flex: 1 1 auto;
  display: grid;
  width: 100%;
  max-width: 100%;
  min-width: 0;
}

/* 官方 detail 组合：只读事实以 t-descriptions 的 label/value 表格呈现。
   取值沿用同一份只读呈现样式（.readonly-value / 关系入口 / 富文本），因此
   这里只负责表格自身的容器约束，不对厂商内部元素做后代选择器覆盖。 */
.template-form-section-descriptions {
  width: 100%;
  min-width: 0;
}

.readonly-value {
  font: var(--sc-font-body-medium);
  box-sizing: border-box;
  display: grid;
  align-items: center;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  color: var(--sc-app-text-primary);
  min-height: 32px;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  word-break: break-word;
}

/* A readonly fact that is actually the next business action (下一步办理).
 * It is rendered as a pressable action link instead of dead text so the
 * "当前任务" card is a real entry point, not a static hint. */
.readonly-value--action {
  padding: 0;
  border: 0;
  background: transparent;
  font: inherit;
  color: var(--sc-text-link, var(--sc-app-accent));
  font-weight: 400;
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 2px;
}

.readonly-value--action:hover {
  opacity: 0.8;
}

.readonly-value--action:focus-visible {
  outline: 2px solid var(--sc-app-accent);
  outline-offset: 2px;
  border-radius: 2px;
}

.readonly-relation-label {
  display: block;
  max-width: 100%;
  white-space: normal;
  text-align: left;
  overflow-wrap: anywhere;
}

.readonly-value--html {
  display: block;
  font: var(--sc-font-body-medium);
}

.readonly-value--html :deep(ul),
.readonly-value--html :deep(ol) {
  margin: 0;
  padding-inline-start: 20px;
}

.readonly-value--html :deep(p) {
  margin: 0 0 6px;
}

.template-form-section--readonly .readonly-value {
  font: var(--sc-font-body-medium);
  min-height: 28px;
  color: var(--sc-app-text-primary);
}

.template-form-section--readonly :deep(.contract-readonly-value) {
  font: var(--sc-font-body-medium);
  min-height: 28px;
  color: var(--sc-app-text-primary);
}

.template-form-section--readonly .template-form-section-grid {
  row-gap: calc(var(--sc-pattern-task-form-field-gap, 12) * 1px);
  column-gap: var(--sc-pattern-task-form-readonly-column-gap, 26px);
}

.template-form-section--readonly .field-control-row {
  align-items: flex-start;
}

.template-form-section--readonly .field--readonly-empty-relation {
  grid-template-columns: minmax(150px, 220px) minmax(0, 1fr);
  align-items: center;
  gap: 12px;
}

.template-form-section--readonly .field--readonly-empty-relation :deep(.relation-readonly-empty) {
  padding: 6px 10px;
}

@media (min-width: 761px) {
  .template-form-section--readonly .field--readonly-empty-relation.field--label-free {
    grid-template-columns: minmax(0, 1fr);
  }

  .template-form-section--readonly .field--readonly-empty-relation.field--label-free > .field-label-row {
    display: none;
  }
}

.template-form-section--readonly .label {
  font: var(--sc-font-body-small);
  color: var(--sc-app-text-secondary);

}

.template-form-section--readonly .readonly-value,
.template-form-section--readonly :deep(.contract-readonly-value) {
  font: var(--sc-font-body-medium);
  min-height: 24px;
  color: var(--sc-app-text-primary);

}

@media (max-width: 760px) {
  .template-form-section--readonly .template-form-section-grid {
    row-gap: 12px;
  }

  .template-form-section--readonly .field--readonly-empty-relation {
    grid-template-columns: minmax(0, 1fr);
    gap: 4px;
  }
}

.field[data-field-type='integer'] .input,
.field[data-field-type='float'] .input,
.field[data-field-type='monetary'] .input,
.field[data-field-type='integer'] :deep(.contract-readonly-value),
.field[data-field-type='float'] :deep(.contract-readonly-value),
.field[data-field-type='monetary'] :deep(.contract-readonly-value) {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.field[data-field-type='date'] .input,
.field[data-field-type='datetime'] .input,
.field[data-field-type='date'] :deep(.contract-readonly-value),
.field[data-field-type='datetime'] :deep(.contract-readonly-value) {
  font-variant-numeric: tabular-nums;
}

.native-radio-group {
  display: grid;
  gap: 8px;
  align-items: start;
}

.native-date-range {
  display: grid;
  grid-template-columns: minmax(130px, 1fr) auto minmax(130px, 1fr);
  gap: 6px;
  align-items: center;
  min-width: 0;
}

.native-date-range__control {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.native-date-range__label {
  font: var(--sc-font-mark-small);
  color: var(--sc-app-text-secondary);

}

.native-date-range-separator {
  font: var(--sc-font-body-medium);
  color: var(--sc-semantic-text-muted);
}

.input[type='date'] {
  min-width: 0;
  padding-right: 10px;
}

@media (max-width: 860px) {
  .native-date-range {
    grid-template-columns: 1fr;
  }

  .native-date-range-separator {
    display: none;
  }
}
.field-monetary-control {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  align-items: center;
  min-width: 0;
}

.field-currency-label {
  font: var(--sc-font-body-medium);
  color: var(--sc-app-text-secondary);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

/* Official composition adoption (TPL-01).
   The official form owns section composition and generic validation. These
   rules only stop its own chrome from competing with the contract-driven field
   grid, which stays the authority for label, identity and error association.

   The adopted row is selected by the primitive identity this project already
   puts on the adapter (`ScFormItem`), never by a vendor class: a TDesign class
   is allowed on an Sc root, but its internal descendants stay uncoupled, so
   swapping the installed version cannot silently change what this styles. */
.template-form-section-form {
  display: block;
  width: 100%;
  max-width: 100%;
  min-width: 0;
}

.template-form-section-form :deep(.field-control-row[data-semantic-component='ScFormItem']) {
  display: block;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  margin: 0;
  padding: 0;
}
</style>
