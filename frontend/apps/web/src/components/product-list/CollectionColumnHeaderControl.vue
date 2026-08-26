<template>
  <div
    class="cell-sortable"
    data-semantic-component="CollectionColumnHeaderControl"
    :class="[densityClass, { 'is-sorted': sorted, 'is-dragging': dragging, 'is-sort-disabled': !sortable }]"
    :data-column="field"
    :style="columnStyle"
    :tabindex="sortable ? 0 : -1"
    :title="sortTitle"
    role="columnheader"
    :aria-sort="ariaSort"
    @dragover="$emit('drag-over', $event)"
    @drop="$emit('drop-column', $event)"
    @dragend="$emit('drag-end')"
    @click="$emit('sort')"
    @keydown.enter.prevent="$emit('sort')"
    @keydown.space.prevent="$emit('sort')"
  >
    <ScIconButton class="column-drag-handle" appearance="column-handle" :label="dragLabel" draggable="true" @click.stop @keydown.stop @dragstart.stop="$emit('drag-start', $event)" @dragend.stop="$emit('drag-end')" />
    <ScButton type="button" class="column-sort-btn" appearance="context-action" variant="ghost" size="small" :title="sortTitle" :aria-disabled="!sortable" draggable="false" @click.stop="$emit('sort')">
      <span>{{ label }}</span>
      <ScIcon v-if="sorted" class="sort-indicator" :name="sortIcon" :size="14" />
    </ScButton>
    <ScIconButton class="column-resize-handle" appearance="column-handle" :label="resizeLabel" draggable="false" @click.stop @dragstart.stop.prevent @mousedown.stop.prevent="$emit('resize-start', $event)" />
  </div>
</template>

<script setup lang="ts">
import ScIcon from '../design-system/ScIcon.vue';
import ScButton from '../design-system/ScButton.vue';
import ScIconButton from '../design-system/ScIconButton.vue';

defineProps<{
  field: string;
  label: string;
  sortable: boolean;
  sorted: boolean;
  dragging: boolean;
  sortIcon: 'chevron-down' | 'chevron-up';
  sortTitle: string;
  ariaSort?: 'none' | 'ascending' | 'descending';
  dragLabel: string;
  resizeLabel: string;
  densityClass: Record<string, boolean>;
  columnStyle: Record<string, string>;
}>();

defineEmits<{ sort: []; 'drag-start': [event: DragEvent]; 'drag-over': [event: DragEvent]; 'drop-column': [event: DragEvent]; 'drag-end': []; 'resize-start': [event: MouseEvent] }>();
</script>

<style scoped src="./CollectionColumnHeaderControl.css"></style>
