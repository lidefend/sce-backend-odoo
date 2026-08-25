<template>
  <nav
    class="group-page"
    data-semantic-component="CollectionGroupPageControls"
    :data-group-key="groupKey"
    :aria-label="regionLabel"
  >
    <ScButton size="small" variant="secondary" :disabled="loading || !canPrevious" @click="$emit('previous')">
      {{ previousLabel }}
    </ScButton>
    <span class="group-page__status" aria-live="polite">{{ pageInfo }}</span>
    <ScButton size="small" variant="secondary" :disabled="loading || !canNext" @click="$emit('next')">
      {{ nextLabel }}
    </ScButton>
    <ScInput
      class="group-page__input"
      size="small"
      type="number"
      :model-value="pageInput"
      :disabled="loading || totalPages <= 1"
      :aria-label="pageInputLabel"
      @update:model-value="$emit('update:page-input', String($event))"
      @change="$emit('page-input-change', String($event))"
    />
    <ScButton size="small" variant="secondary" :disabled="loading || totalPages <= 1" @click="$emit('jump')">
      {{ jumpLabel }}
    </ScButton>
  </nav>
</template>

<script setup lang="ts">
import ScButton from '../design-system/ScButton.vue';
import ScInput from '../design-system/ScInput.vue';

defineProps<{
  groupKey: string;
  regionLabel: string;
  pageInfo: string;
  pageInput: string;
  pageInputLabel: string;
  previousLabel: string;
  nextLabel: string;
  jumpLabel: string;
  totalPages: number;
  canPrevious: boolean;
  canNext: boolean;
  loading: boolean;
}>();

defineEmits<{
  previous: [];
  next: [];
  jump: [];
  'update:page-input': [value: string];
  'page-input-change': [value: string];
}>();
</script>

<style scoped src="./CollectionGroupPageControls.css"></style>
