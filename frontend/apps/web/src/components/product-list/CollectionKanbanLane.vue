<template>
  <section class="collection-kanban-lane" data-semantic-component="CollectionKanbanLane" :data-lane-key="laneKey">
    <header v-if="showHeader" class="collection-kanban-lane__header">
      <h3>{{ label }}</h3>
      <ScBadge :count="recordCount" status="default" :aria-label="`${label}，${recordCount} 条记录`" />
    </header>
    <div class="collection-kanban-lane__cards"><slot /></div>
  </section>
</template>

<script setup lang="ts">
import ScBadge from '../design-system/ScBadge.vue';
defineProps<{ laneKey: string; label: string; recordCount: number; showHeader: boolean }>();
</script>

<style scoped src="./CollectionKanbanLane.css"></style>
