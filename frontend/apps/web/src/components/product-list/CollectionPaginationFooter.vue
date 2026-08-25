<template>
  <nav
    class="pagination-footer"
    data-semantic-component="CollectionPaginationFooter"
    :data-pagination-mode="mode"
    :aria-label="labels.region"
  >
    <div class="pagination-actions pagination-actions--bottom">
      <span class="pagination-total" aria-live="polite">{{ recordCountText }}</span>
      <template v-if="mode === 'grouped'">
        <ScButton class="pagination-btn" size="small" :disabled="loading || !canPrevious" @click="$emit('previous')">
          {{ labels.groupPrevious }}
        </ScButton>
        <span aria-live="polite">{{ pageText }}</span>
        <ScButton class="pagination-btn" size="small" :disabled="loading || !canNext" @click="$emit('next')">
          {{ labels.groupNext }}
        </ScButton>
      </template>
      <template v-else-if="mode === 'paged'">
        <ScButton class="pagination-btn" size="small" :disabled="loading || !canPrevious" @click="$emit('previous')">
          {{ labels.previous }}
        </ScButton>
        <span aria-live="polite">{{ pageText }}</span>
        <ScButton class="pagination-btn" size="small" :disabled="loading || !canNext" @click="$emit('next')">
          {{ labels.next }}
        </ScButton>
        <ScInput
          class="pagination-input"
          size="small"
          :model-value="pageJumpValue"
          :disabled="loading || totalPages <= 1"
          :aria-label="labels.pageInput"
          inputmode="numeric"
          pattern="[0-9]*"
          @input="(value) => $emit('page-jump-input', value)"
          @keyup.enter="$emit('page-jump')"
        />
        <ScButton class="pagination-btn" size="small" :disabled="loading || totalPages <= 1" @click="$emit('page-jump')">
          {{ labels.jump }}
        </ScButton>
        <label v-if="showPageSize" class="pagination-size-control">
          <span class="pagination-size-label">{{ labels.pageSize }}</span>
          <span class="pagination-size-combo">
            <ScInput
              class="pagination-input pagination-input--size"
              size="small"
              :model-value="pageLimitValue"
              :disabled="loading"
              inputmode="numeric"
              pattern="[0-9]*"
              :aria-label="labels.pageSizeInput"
              @input="(value) => $emit('page-limit-input', value)"
              @change="$emit('page-limit-apply')"
              @keyup.enter="$emit('page-limit-apply')"
            />
            <ScSelect
              class="pagination-size-select"
              size="small"
              :model-value="pageLimitOptions.includes(listLimit) ? String(listLimit) : ''"
              :disabled="loading"
              :aria-label="labels.pageSizeSelect"
              @change="(value) => $emit('page-limit-select', value)"
            >
              <option value="" disabled>{{ labels.pageSizeSelect }}</option>
              <option v-for="option in pageLimitOptions" :key="`page-limit-${option}`" :value="String(option)">{{ option }}</option>
            </ScSelect>
          </span>
        </label>
      </template>
    </div>
  </nav>
</template>

<script setup lang="ts">
import ScButton from '../design-system/ScButton.vue';
import ScInput from '../design-system/ScInput.vue';
import ScSelect from '../design-system/ScSelect.vue';

export type CollectionPaginationMode = 'count' | 'grouped' | 'paged';

withDefaults(defineProps<{
  mode: CollectionPaginationMode;
  recordCountText: string;
  loading: boolean;
  canPrevious: boolean;
  canNext: boolean;
  pageText: string;
  pageJumpValue: string;
  pageLimitValue: string;
  listLimit: number;
  totalPages: number;
  pageLimitOptions: number[];
  showPageSize?: boolean;
  labels: {
    region: string;
    previous: string;
    next: string;
    groupPrevious: string;
    groupNext: string;
    pageInput: string;
    jump: string;
    pageSize: string;
    pageSizeInput: string;
    pageSizeSelect: string;
  };
}>(), { showPageSize: true });

defineEmits<{
  previous: [];
  next: [];
  'page-jump-input': [value: string];
  'page-jump': [];
  'page-limit-input': [value: string];
  'page-limit-apply': [];
  'page-limit-select': [value: string];
}>();
</script>

<style scoped src="./CollectionPaginationFooter.css"></style>
