<template>
  <div
    class="cell-sortable"
    data-semantic-component="CollectionColumnHeaderControl"
    :class="[densityClass, { 'is-primary': primary, 'is-sorted': sorted, 'is-dragging': dragging, 'is-sort-disabled': !sortable }]"
    :data-column="field"
    :data-primary="primary || undefined"
    :data-reorderable="reorderable !== false"
    :style="columnStyle"
    :title="sortTitle"
    @dragover="$emit('drag-over', $event)"
    @drop="$emit('drop-column', $event)"
    @dragend="$emit('drag-end')"
    @click="sortable && $emit('sort')"
  >
    <ScIconButton v-if="reorderable !== false" class="column-drag-handle" appearance="column-handle" :label="dragLabel" draggable="true" @click.stop @keydown.stop @dragstart.stop="$emit('drag-start', $event)" @dragend.stop="$emit('drag-end')">
      <ScIcon name="menu" :size="14" />
    </ScIconButton>
    <ScButton type="button" class="column-sort-btn" appearance="context-action" variant="ghost" size="small" :title="sortTitle" :aria-disabled="!sortable" draggable="false" @click.stop="sortable && $emit('sort')">
      <span>{{ label }}</span>
      <ScIcon v-if="sorted" class="sort-indicator" :name="sortIcon" :size="14" />
    </ScButton>
    <ScIconButton class="column-resize-handle" appearance="column-handle" :label="`${label}：${resizeLabel}`" aria-description="使用左右方向键调整列宽，按住 Shift 加快调整。" draggable="false" @click.stop @dragstart.stop.prevent @mousedown.stop.prevent="$emit('resize-start', $event)" @keydown.left.stop.prevent="$emit('resize-step', $event.shiftKey ? -40 : -10)" @keydown.right.stop.prevent="$emit('resize-step', $event.shiftKey ? 40 : 10)" />
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
  reorderable?: boolean;
  primary?: boolean;
  sorted: boolean;
  dragging: boolean;
  sortIcon: 'chevron-down' | 'chevron-up';
  sortTitle: string;
  dragLabel: string;
  resizeLabel: string;
  densityClass: Record<string, boolean>;
  columnStyle: Record<string, string>;
}>();

defineEmits<{ sort: []; 'drag-start': [event: DragEvent]; 'drag-over': [event: DragEvent]; 'drop-column': [event: DragEvent]; 'drag-end': []; 'resize-start': [event: MouseEvent]; 'resize-step': [delta: number] }>();
</script>

<style scoped src="./CollectionColumnHeaderControl.css"></style>
