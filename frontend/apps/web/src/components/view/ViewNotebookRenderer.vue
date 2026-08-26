<template>
  <div class="view-notebook">
    <ScTabs class="tabs" :model-value="activeIndex" :items="tabItems" size="small" @update:model-value="activeIndex = Number($event)">
      <template #panel="{ item }">
    <div v-if="Number(item.value) === activeIndex" class="tab-panel">
      <ViewGroupRenderer
        v-for="(group, index) in groupsForPage(activeIndex)"
        :key="`page-${activeIndex}-group-${index}`"
        :group="group"
        :fields="fields"
        :record="record"
        :editing="editing"
        :draft-name="draftName"
        :edit-mode="editMode"
        :depth="0"
        @update:field="emit('update:field', $event)"
      />
    </div>
      </template>
    </ScTabs>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import type { ViewContract } from '@sc/schema';
import ViewGroupRenderer from './ViewGroupRenderer.vue';
import ScTabs, { type ScTabItem } from '../design-system/ScTabs.vue';

interface ViewPageNode {
  title?: string;
  groups?: Array<Record<string, unknown>>;
}

interface ViewNotebookNode {
  pages?: ViewPageNode[];
}

const props = defineProps<{
  notebook: ViewNotebookNode;
  fields?: ViewContract['fields'];
  record?: Record<string, unknown> | null;
  editing: boolean;
  draftName: string;
  editMode: 'none' | 'name' | 'all';
}>();

const emit = defineEmits<{ (event: 'update:field', payload: { name: string; value: string }): void }>();

const pages = computed(() => (Array.isArray(props.notebook.pages) ? props.notebook.pages : []));
const activeIndex = ref(0);
const tabItems = computed<ScTabItem[]>(() => pages.value.map((page, index) => ({
  value: index,
  label: page.title || `Page ${index + 1}`,
  labelClass: `tab${index === activeIndex.value ? ' active' : ''}`,
})));
function groupsForPage(index: number) {
  const page = pages.value[index];
  if (!page || !Array.isArray(page.groups)) {
    return [];
  }
  return page.groups;
}
</script>

<style scoped>
.view-notebook {
  display: grid;
  gap: 16px;
}

.tabs {
  min-width: 0;
}

.tab {
  white-space: nowrap;
}

.tab.active {
  font-weight: 600;
}

.tab-panel {
  display: grid;
  gap: 16px;
}
</style>
