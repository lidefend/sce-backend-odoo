<template>
  <article
    class="collection-mobile-record-row"
    data-semantic-component="CollectionMobileRecordRow"
    :data-record-key="recordKey"
    :data-selection-state="selected ? 'selected' : 'unselected'"
    :data-state="selectionDisabled ? 'selection-disabled' : 'ready'"
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
      :title="selectionDisabled ? selectionDisabledReason : undefined"
      @click.stop
      @change="emit('selection-change', $event)"
    />
    <ScMobileRecordCard
      class="collection-mobile-record-row__card"
      as="article"
    >
      <template #identity>
        <strong class="collection-mobile-record-row__identity" :title="identity">{{ identity }}</strong>
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
        v-for="fact in visibleFacts"
        :key="fact.key"
        class="collection-mobile-record-row__fact"
        :data-fact-key="fact.key"
      >
        <small>{{ fact.label }}</small>
        <span
          v-if="fact.relationItems?.length"
          class="collection-mobile-record-row__relation-tags"
          data-semantic-cell-kind="relation-tags"
        >
          <b v-for="item in fact.relationItems" :key="item.id" class="collection-mobile-record-row__relation-tag">{{ item.label }}</b>
        </span>
        <b v-else>{{ fact.value }}</b>
      </span>
      <ScDisclosure v-if="additionalFacts.length" class="collection-mobile-record-row__disclosure" :title="`查看其余 ${additionalFacts.length} 项信息`">
        <span class="collection-mobile-record-row__additional-facts">
          <span v-for="fact in additionalFacts" :key="fact.key" class="collection-mobile-record-row__fact" :data-fact-key="fact.key">
            <small>{{ fact.label }}</small>
            <span v-if="fact.relationItems?.length" class="collection-mobile-record-row__relation-tags" data-semantic-cell-kind="relation-tags">
              <b v-for="item in fact.relationItems" :key="item.id" class="collection-mobile-record-row__relation-tag" :title="item.label">{{ item.label }}</b>
            </span>
            <b v-else>{{ fact.value }}</b>
          </span>
        </span>
      </ScDisclosure>
      <template #actions>
        <ScButton class="collection-mobile-record-row__open-action" appearance="auth-link" variant="ghost" size="small" :aria-label="openAriaLabel" @click="emit('open')"><span class="collection-mobile-record-row__open">
          {{ openLabel }}
          <ScIcon name="arrow-right" :size="16" aria-hidden="true" />
        </span></ScButton>
      </template>
    </ScMobileRecordCard>
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import ScButton from '../design-system/ScButton.vue';
import ScDisclosure from '../design-system/ScDisclosure.vue';
import ScIcon from '../design-system/ScIcon.vue';
import ScMobileRecordCard from '../design-system/ScMobileRecordCard.vue';
import ScStatusBadge from '../design-system/ScStatusBadge.vue';
import CollectionSelectionControl from './CollectionSelectionControl.vue';

export type CollectionMobileRecordFact = {
  key: string;
  label: string;
  value: string;
  relationItems?: Array<{ id: number; label: string }>;
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
  selectionDisabledReason?: string;
  selectionLabel?: string;
  openLabel: string;
  visibleFactLimit?: number;
}>(), {
  facts: () => [],
  statusValue: '',
  statusLabel: '',
  statusSemantic: 'default',
  selected: false,
  selectionEnabled: false,
  selectionDisabled: false,
  selectionDisabledReason: '',
  selectionLabel: '',
  visibleFactLimit: 3,
});

const emit = defineEmits<{
  open: [];
  'selection-change': [checked: boolean];
}>();

const openAriaLabel = computed(() => `${props.openLabel}：${props.identity}`);
const visibleFacts = computed(() => props.facts.slice(0, Math.max(1, props.visibleFactLimit)));
const additionalFacts = computed(() => props.facts.slice(visibleFacts.value.length));
</script>

<style scoped src="./CollectionMobileRecordRow.css"></style>
