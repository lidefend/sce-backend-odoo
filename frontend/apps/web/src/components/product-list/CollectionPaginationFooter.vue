<template>
  <nav class="pagination-footer" data-semantic-component="CollectionPaginationFooter" :data-pagination-mode="mode" :data-state="loading ? 'loading' : 'ready'" :aria-busy="loading || undefined" :aria-label="labels.region">
    <div class="pagination-actions pagination-actions--bottom">
      <span class="pagination-total" aria-live="polite">{{ recordCountText }}</span>
      <template v-if="mode === 'grouped'">
        <ScButton class="pagination-btn" appearance="outline-action" size="small" :disabled="loading || !canPrevious" @click="$emit('previous')">{{ labels.groupPrevious }}</ScButton>
        <span aria-live="polite">{{ pageText }}</span>
        <ScButton class="pagination-btn" appearance="outline-action" size="small" :disabled="loading || !canNext" @click="$emit('next')">{{ labels.groupNext }}</ScButton>
      </template>
      <ScPagination v-else-if="mode === 'paged'" :current="currentPage" :page-size="listLimit" :total="totalRecords" :disabled="loading" :page-size-options="showPageSize ? pageLimitOptions : []" @update:current="$emit('page-select', $event)" @update:page-size="$emit('page-limit-select', String($event))" />
    </div>
  </nav>
</template>
<script setup lang="ts">
import ScButton from '../design-system/ScButton.vue';
import ScPagination from '../design-system/ScPagination.vue';
export type CollectionPaginationMode = 'count' | 'grouped' | 'paged';
withDefaults(defineProps<{
  mode: CollectionPaginationMode; recordCountText: string; loading: boolean; canPrevious: boolean; canNext: boolean;
  pageText: string; pageJumpValue: string; pageLimitValue: string; listLimit: number; totalPages: number;
  currentPage?: number; totalRecords?: number; pageLimitOptions: number[]; showPageSize?: boolean;
  labels: { region: string; previous: string; next: string; groupPrevious: string; groupNext: string; pageInput: string; jump: string; pageSize: string; pageSizeInput: string; pageSizeSelect: string };
}>(), { showPageSize: true, currentPage: 1, totalRecords: 0 });
defineEmits<{ previous: []; next: []; 'page-jump-input': [value: string]; 'page-jump': []; 'page-limit-input': [value: string]; 'page-limit-apply': []; 'page-limit-select': [value: string]; 'page-select': [value: number] }>();
</script>
<style scoped src="./CollectionPaginationFooter.css"></style>
