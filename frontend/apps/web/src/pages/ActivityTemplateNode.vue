<template>
  <span
    v-if="node.field"
    class="activity-template-field"
    :class="fieldClasses"
    :data-native-locator="node.field.nativeLocator"
    :data-widget="node.field.widget || undefined"
  >
    <span v-if="node.field.label" class="activity-template-field__label">{{ node.field.label }}</span>
    <span class="activity-template-field__value">{{ activityCellText(record[node.field.name], node.field, record) }}</span>
  </span>
  <div v-else class="activity-template-container" :class="node.classes">
    <span v-if="node.text" class="activity-template-text">{{ node.text }}</span>
    <ActivityTemplateNode
      v-for="child in node.children"
      :key="child.key"
      :node="child"
      :record="record"
    />
  </div>
  <span v-if="node.tail" class="activity-template-tail">{{ node.tail }}</span>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { activityCellText, type ActivityTemplateNode } from '../app/contracts/actionViewActivityContract';
import { evaluateNativeModifierValue } from './contractForm/nativeLayoutUtils';

const props = defineProps<{ node: ActivityTemplateNode; record: Record<string, unknown> }>();
const fieldClasses = computed(() => {
  const field = props.node.field;
  if (!field) return {};
  const classes: Record<string, boolean> = {
    'activity-template-field--badge': field.widget === 'badge',
    'activity-template-field--monetary': field.widget === 'monetary',
  };
  field.decorations.forEach((decoration) => {
    const tone = String(decoration.class || '').trim();
    if (!tone) return;
    classes[`activity-template-field--${tone}`] = evaluateNativeModifierValue(
      decoration.expr,
      (fieldName) => props.record[fieldName],
    );
  });
  return classes;
});
</script>

<style scoped>
.activity-template-container { display: grid; gap: 10px; min-width: 0; }
.activity-template-text { color: var(--sc-app-text-secondary); font-size: 12px; }
.activity-template-tail { color: var(--sc-app-text-secondary); font-size: 12px; }
.activity-template-container.d-flex { display: flex; align-items: flex-start; justify-content: space-between; flex-wrap: wrap; gap: 12px; }
.activity-template-container.d-flex > * { min-width: 0; max-width: 100%; }
.activity-template-field { display: inline-flex; flex: 1 1 220px; gap: 6px; align-items: baseline; min-width: 0; }
.activity-template-field__label { color: var(--sc-app-text-secondary); font-size: 11px; }
.activity-template-field__value { overflow-wrap: anywhere; font-weight: 650; }
.activity-template-field--badge .activity-template-field__value { padding: 3px 8px; border-radius: 999px; background: var(--sc-app-muted-bg); font-size: 12px; }
.activity-template-field--info .activity-template-field__value { background: var(--sc-app-info-bg); color: var(--sc-app-info-text); }
.activity-template-field--success .activity-template-field__value { background: var(--sc-app-success-bg); color: var(--sc-app-success-text); }
.activity-template-field--monetary .activity-template-field__value { font-variant-numeric: tabular-nums; }
@media (max-width: 680px) {
  .activity-template-container.d-flex { display: grid; grid-template-columns: 1fr; gap: 8px; }
  .activity-template-field { display: grid; grid-template-columns: minmax(68px, .55fr) minmax(0, 1.45fr); width: 100%; }
  .activity-template-field__value { min-width: 0; }
}
</style>
