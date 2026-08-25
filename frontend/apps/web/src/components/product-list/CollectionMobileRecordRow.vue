<template>
  <article
    class="collection-mobile-record-row"
    data-semantic-component="CollectionMobileRecordRow"
    :data-record-key="recordKey"
    :data-selection-state="selected ? 'selected' : 'unselected'"
    :class="{ 'is-selected': selected }"
    :role="selectionEnabled ? 'option' : undefined"
    :aria-selected="selectionEnabled ? selected : undefined"
  >
    <CollectionSelectionControl
      v-if="selectionEnabled"
      class="collection-mobile-record-row__selection"
      size="touch"
      :checked="selected"
      :disabled="selectionDisabled"
      :label="selectionLabel"
      @click.stop
      @change="emit('selection-change', $event)"
    />
    <ScMobileRecordCard
      class="collection-mobile-record-row__card"
      as="button"
      :aria-label="openAriaLabel"
      @click="emit('open')"
    >
      <template #identity>
        <strong class="collection-mobile-record-row__identity">{{ identity }}</strong>
      </template>
      <template #status>
        <ScStatusBadge
          v-if="statusLabel"
          :value="statusValue"
          :label="statusLabel"
          :semantic="statusSemantic"
        />
      </template>
      <span
        v-for="fact in facts"
        :key="fact.key"
        class="collection-mobile-record-row__fact"
        :data-fact-key="fact.key"
      >
        <small>{{ fact.label }}</small>
        <b>{{ fact.value }}</b>
      </span>
      <template #actions>
        <span class="collection-mobile-record-row__open">
          {{ openLabel }}
          <ScIcon name="arrow-right" :size="16" aria-hidden="true" />
        </span>
      </template>
    </ScMobileRecordCard>
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import ScIcon from '../design-system/ScIcon.vue';
import ScMobileRecordCard from '../design-system/ScMobileRecordCard.vue';
import ScStatusBadge from '../design-system/ScStatusBadge.vue';
import CollectionSelectionControl from './CollectionSelectionControl.vue';

export type CollectionMobileRecordFact = {
  key: string;
  label: string;
  value: string;
};

const props = withDefaults(defineProps<{
  recordKey: string;
  identity: string;
  facts?: CollectionMobileRecordFact[];
  statusValue?: string;
  statusLabel?: string;
  statusSemantic?: 'default' | 'info' | 'success' | 'warning' | 'danger';
  selected?: boolean;
  selectionEnabled?: boolean;
  selectionDisabled?: boolean;
  selectionLabel?: string;
  openLabel: string;
}>(), {
  facts: () => [],
  statusValue: '',
  statusLabel: '',
  statusSemantic: 'default',
  selected: false,
  selectionEnabled: false,
  selectionDisabled: false,
  selectionLabel: '',
});

const emit = defineEmits<{
  open: [];
  'selection-change': [checked: boolean];
}>();

const openAriaLabel = computed(() => `${props.openLabel}：${props.identity}`);
</script>

<style scoped src="./CollectionMobileRecordRow.css"></style>
