<template>
  <TDesignSelect
    ref="selectRef"
    v-native-control-projection="nativeProjection"
    class="sc-relation-field"
    data-semantic-component="ScRelationField" data-semantic-primitive="ScRelationField"
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
// The official popup resolves the panel width when the panel content mounts, so
// it can only be refreshed by handing it a new style value. Record the viewport
// in force at each open to decide the panel width limit for that open.
const panelViewportWidth = ref(0);
watch(popupOpen, (visible) => {
  if (visible && typeof window !== 'undefined') panelViewportWidth.value = window.innerWidth;
});
const vNativeControlProjection = nativeControlProjection;
const resolvedPanelId = computed(() => props.panelId || `${instanceId}-panel`);
const tdesignOptions = computed(() => (props.options || []).map((option) => ({
  value: option.value,
  label: option.label,
  disabled: Boolean(option.disabled),
})));
const inputValue = computed(() => String(props.queryValue ?? ''));
const PANEL_VIEWPORT_GUTTER_PX = 16;

// Official gap (TDesign Vue Next 1.20.5): `useOverlayInnerStyle` sizes the panel
// as `max(triggerWidth, currentPanelWidth)` and only clamps to a fixed 1000px,
// and `Popup` applies `overlayInnerStyle` when the panel content mounts rather
// than on every open. A panel first opened on a wide viewport therefore keeps
// that width after the viewport narrows and overflows it. `popupProps.overlayInnerStyle`
// is the official override point for the panel width, so the clamp lives here
// instead of in extra interaction code. Remove it once the component re-measures
// the panel on open or on viewport change.
function resolvePanelInnerStyle(trigger: HTMLElement | null, viewportWidth: number) {
  const triggerWidth = trigger?.offsetWidth || 0;
  const limit = viewportWidth > 0 ? viewportWidth - PANEL_VIEWPORT_GUTTER_PX : triggerWidth;
  return { width: `${Math.max(Math.min(triggerWidth, limit), 0)}px` };
}

const popupProps = computed(() => {
  const viewportWidth = panelViewportWidth.value;
  return {
    // Official public extension point: the popup owns its DOM, so the panel needs
    // a stable hook for accessibility projection and acceptance selectors.
    overlayClassName: [instanceId, props.panelClass].filter(Boolean).join(' '),
    overlayInnerStyle: (trigger: HTMLElement) => resolvePanelInnerStyle(trigger, viewportWidth),
  };
});
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

/*
 * Official-capability gap (TDesign Vue Next 1.20.5): `Select` exposes
 * `panelBottomContent` for panel actions, but renders it as an ordinary sibling
 * of the option list inside `.t-popup__content`, which the theme caps at
 * `max-height: 300px; overflow-y: auto`. A panel whose actions are taller than
 * the leftover space therefore pushes them below the scrollport, so the primary
 * actions cannot be clicked without scrolling the candidate list first. The
 * official API has no bottom-anchored action area and the popup has no footer
 * slot, so the anchor is presentation, applied through the official slot:
 * `position: sticky` keeps the block inside the official container and pins it
 * to the scrollport bottom only while the content overflows. Remove this once
 * the official Select provides a footer slot or excludes `panelBottomContent`
 * from the scrolling region.
 */
.sc-relation-field__panel-actions {
  position: sticky;
  bottom: 0;
  z-index: var(--sc-component-overlay-local-action-z-index);
  display: grid;
  gap: 4px;
  padding: 4px 0 0;
  border-top: 1px solid var(--sc-app-border);
  margin-top: 4px;
  background: var(--sc-app-panel);
}
</style>
