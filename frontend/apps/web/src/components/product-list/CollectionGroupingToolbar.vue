<template>
  <header class="grouped-toolbar" data-semantic-component="CollectionGroupingToolbar" :data-group-count="groupCount">
    <div class="grouped-toolbar-title">
      <span>{{ labels.title }}</span>
      <span v-if="windowInfo" class="group-window-info" aria-live="polite">{{ windowInfo }}</span>
    </div>
    <div class="grouped-toolbar-actions">
      <ScButton v-if="hasWindowPrevious" class="grouped-sort-btn" size="small" :disabled="loading || !canWindowPrevious" @click="$emit('window-previous')">{{ labels.windowPrevious }}</ScButton>
      <ScButton v-if="hasWindowNext" class="grouped-sort-btn" size="small" :disabled="loading || !canWindowNext" @click="$emit('window-next')">{{ labels.windowNext }}</ScButton>
      <ScButton class="grouped-sort-btn" size="small" :disabled="!groupCount || !hasCollapsedGroups" @click="$emit('expand-all')">{{ labels.expandAll }}</ScButton>
      <ScButton class="grouped-sort-btn" size="small" :disabled="!groupCount || allGroupsCollapsed" @click="$emit('collapse-all')">{{ labels.collapseAll }}</ScButton>
      <ScButton class="grouped-sort-btn" size="small" :aria-label="labels.sort" @click="$emit('toggle-sort')">{{ sortLabel }}</ScButton>
      <label v-if="sampleLimitEnabled" class="group-sample-limit">
        <span>{{ labels.sampleLimit }}</span>
        <ScSelect class="group-sample-limit-select" size="small" :model-value="String(sampleLimit)" :disabled="loading" :aria-label="labels.sampleLimit" @change="(value) => $emit('sample-limit-change', value)">
          <option v-for="option in sampleLimitOptions" :key="`group-sample-limit-${option}`" :value="String(option)">{{ option }}</option>
        </ScSelect>
      </label>
    </div>
  </header>
</template>

<script setup lang="ts">
import ScButton from '../design-system/ScButton.vue';
import ScSelect from '../design-system/ScSelect.vue';

defineProps<{
  loading: boolean;
  groupCount: number;
  windowInfo: string;
  hasWindowPrevious: boolean;
  hasWindowNext: boolean;
  canWindowPrevious: boolean;
  canWindowNext: boolean;
  hasCollapsedGroups: boolean;
  allGroupsCollapsed: boolean;
  sortLabel: string;
  sampleLimitEnabled: boolean;
  sampleLimit: number;
  sampleLimitOptions: number[];
  labels: { title: string; windowPrevious: string; windowNext: string; expandAll: string; collapseAll: string; sort: string; sampleLimit: string };
}>();

defineEmits<{ 'window-previous': []; 'window-next': []; 'expand-all': []; 'collapse-all': []; 'toggle-sort': []; 'sample-limit-change': [value: string] }>();
</script>

<style scoped src="./CollectionGroupingToolbar.css"></style>
