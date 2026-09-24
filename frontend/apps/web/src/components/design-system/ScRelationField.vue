<template>
  <TDesignSelect
    ref="selectRef"
    v-native-control-projection="nativeProjection"
    class="sc-relation-field"
    data-semantic-component="ScRelationField"
    data-semantic-driver="tdesign-select"
    data-semantic-layer="primitive"
    :data-appearance="appearance"
    :data-option-count="tdesignOptions.length"
    :data-relation-panel-id="resolvedPanelId"
    :model-value="modelValue"
    :input-value="inputValue"
    :options="tdesignOptions"
    :filterable="filterable"
    :clearable="clearable"
    :creatable="false"
    :loading="loading"
    :empty="emptyText"
    :reserve-keyword="false"
    :disabled="disabled"
    :readonly="readonly"
    :status="invalid ? 'error' : 'default'"
    :placeholder="placeholder"
    :input-props="{ inputClass: 'sc-relation-field__control', autocomplete: 'off' }"
    :popup-visible="popupOpen"
    :popup-props="popupProps"
    :aria-required="required || undefined"
    :aria-invalid="invalid || undefined"
    :aria-describedby="describedBy"
    :aria-label="ariaLabel"
    @change="onChange"
    @clear="onClear"
    @update:input-value="onInputValueChange"
    @search="onSearch"
    @popup-visible-change="onPopupVisibleChange"
    @focus="onFocus"
    @blur="onBlur"
  >
    <template v-if="$slots['panel-actions']" #panelBottomContent>
      <div class="sc-relation-field__panel-actions">
        <slot name="panel-actions" />
      </div>
    </template>
  </TDesignSelect>
</template>
<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue';
import { TDesignSelect } from './tdesignPrimitiveBridge';
import { nativeControlProjection } from './nativeControlProjection';
import { resolvePrimitiveNativeEvent, selectPopupVisibilityEvent } from './primitiveAdapter';
import {
  nextRelationSelectPanelInstanceId,
  observeRelationSelectPanelA11y,
} from './relationSelectPanelA11y';

export interface ScRelationFieldOption {
  value: string | number;
  label: string;
  disabled?: boolean;
}

const props = withDefaults(defineProps<{
  id?: string;
  modelValue: string | number;
  queryValue?: string;
  options?: readonly ScRelationFieldOption[];
  panelId?: string;
  panelClass?: string;
  placeholder?: string;
  disabled?: boolean;
  readonly?: boolean;
  required?: boolean;
  invalid?: boolean;
  describedBy?: string;
  ariaLabel?: string;
  clearable?: boolean;
  filterable?: boolean;
  loading?: boolean;
  emptyText?: string;
  appearance?: 'default' | 'form-field';
}>(), {
  id: undefined,
  queryValue: '',
  options: () => [],
  panelId: undefined,
  panelClass: undefined,
  placeholder: undefined,
  describedBy: undefined,
  ariaLabel: undefined,
  appearance: 'default',
  clearable: false,
  filterable: true,
  loading: false,
  emptyText: undefined,
});
const emit = defineEmits<{
  'update:modelValue': [value: string];
  'update:queryValue': [value: string];
  select: [payload: { value: string; option?: ScRelationFieldOption }];
  query: [value: string];
  clear: [];
  'popup-visible-change': [payload: { visible: boolean; trigger: string }];
  focus: [event: Event];
  blur: [event: Event];
}>();

const instanceId = nextRelationSelectPanelInstanceId();

const selectRef = ref<{ $el?: HTMLElement } | null>(null);
const popupOpen = ref(false);
const vNativeControlProjection = nativeControlProjection;
const resolvedPanelId = computed(() => props.panelId || `${instanceId}-panel`);
const tdesignOptions = computed(() => (props.options || []).map((option) => ({
  value: option.value,
  label: option.label,
  disabled: Boolean(option.disabled),
})));
const inputValue = computed(() => String(props.queryValue ?? ''));
const popupProps = computed(() => ({
  // Official public extension point: the popup owns its DOM, so the panel needs
  // a stable hook for accessibility projection and acceptance selectors.
  overlayClassName: [instanceId, props.panelClass].filter(Boolean).join(' '),
}));
const nativeProjection = computed(() => ({
  selector: 'input' as const,
  attributes: {
    id: props.id,
    role: 'combobox',
    'aria-autocomplete': 'list',
    'aria-expanded': popupOpen.value ? 'true' : 'false',
    'aria-controls': resolvedPanelId.value,
    'aria-required': props.required || undefined,
    'aria-invalid': props.invalid || undefined,
    'aria-describedby': props.describedBy,
    'aria-label': props.ariaLabel,
  },
}));

let stopPanelProjection: (() => void) | null = null;

function rootElement(): HTMLElement | null {
  const element = selectRef.value?.$el;
  return element instanceof HTMLElement ? element : null;
}

function inputElement(): HTMLInputElement | null {
  return rootElement()?.querySelector('input') || null;
}

function panelElement(): HTMLElement | null {
  return document.querySelector<HTMLElement>(`.${instanceId}`);
}

function startPanelProjection(attempt = 0) {
  const panel = panelElement();
  if (!panel) {
    // The official popup mounts its content on first open.
    if (attempt < 12) window.requestAnimationFrame(() => startPanelProjection(attempt + 1));
    return;
  }
  stopPanelProjection?.();
  stopPanelProjection = observeRelationSelectPanelA11y(panel, inputElement(), {
    panelId: () => resolvedPanelId.value,
    activeValue: () => String(props.modelValue ?? ''),
    optionValues: () => tdesignOptions.value.map((option) => String(option.value)),
  });
}

function stopPanelProjectionNow() {
  stopPanelProjection?.();
  stopPanelProjection = null;
}

function optionOf(value: string): ScRelationFieldOption | undefined {
  return tdesignOptions.value.find((option) => String(option.value) === value);
}

function onChange(value: unknown, context?: { trigger?: string }) {
  const normalized = value === null || value === undefined ? '' : String(value);
  emit('update:modelValue', normalized);
  if (String(context?.trigger || '') === 'clear') return;
  emit('select', { value: normalized, option: optionOf(normalized) });
}

function onClear() {
  emit('clear');
}

function onInputValueChange(value: unknown) {
  emit('update:queryValue', String(value ?? ''));
}

function onSearch(value: unknown) {
  emit('query', String(value ?? ''));
}

function onPopupVisibleChange(visible: unknown, context?: { trigger?: string }) {
  const next = Boolean(visible);
  popupOpen.value = next;
  emit('popup-visible-change', selectPopupVisibilityEvent(visible, context?.trigger));
  if (next) startPanelProjection();
  else stopPanelProjectionNow();
}

function onFocus(context: unknown) {
  const event = resolvePrimitiveNativeEvent(context);
  if (event) emit('focus', event);
}

function onBlur(context: unknown) {
  const event = resolvePrimitiveNativeEvent(context);
  if (event) emit('blur', event);
}

watch(() => props.modelValue, () => {
  if (popupOpen.value) startPanelProjection();
});
onBeforeUnmount(stopPanelProjectionNow);

defineExpose({
  focus: () => inputElement()?.focus(),
  open: () => { popupOpen.value = true; },
  close: () => { popupOpen.value = false; },
});
</script>
<style scoped>
.sc-relation-field {
  min-width: 0;
}

.sc-relation-field__panel-actions {
  display: grid;
  gap: 4px;
  padding: 4px 0 0;
  border-top: 1px solid var(--sc-app-border);
  margin-top: 4px;
}
</style>
