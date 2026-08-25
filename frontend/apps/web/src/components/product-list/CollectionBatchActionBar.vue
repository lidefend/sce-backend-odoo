<template>
  <section
    class="batch-bar sc-product-feedback-layer"
    data-semantic-component="CollectionBatchActionBar"
    :data-action-count="String(settlement.actionKeys.length)"
    :data-direct-action-keys="settlement.direct.map((action) => action.key).join(',')"
    :data-overflow-action-keys="settlement.overflow.map((action) => action.key).join(',')"
  >
    <span>{{ selectedCountLabel }}</span>
    <ScButton
      v-for="action in settlement.direct"
      :key="`selection-action-${action.key}`"
      class="batch-action"
      size="small"
      :data-action-key="action.key"
      :disabled="loading || !selectedCount || !action.enabled"
      :title="action.hint || ''"
      @click="runAction(action.key)"
    >
      {{ action.label }}
    </ScButton>
    <div v-if="settlement.overflow.length" ref="batchOverflowRoot" class="batch-overflow">
      <span ref="batchOverflowToggle" class="batch-overflow-toggle-root">
        <ScButton
          class="batch-overflow-toggle"
          size="small"
          variant="secondary"
          :disabled="loading"
          :aria-expanded="batchOverflowOpen"
          aria-controls="collection-batch-overflow"
          :aria-label="moreActionsLabel"
          :title="moreActionsLabel"
          @click.stop="toggleBatchOverflow"
        >
          <ScIcon name="menu" :size="18" />
        </ScButton>
      </span>
      <div
        v-if="batchOverflowOpen"
        id="collection-batch-overflow"
        class="batch-overflow-menu"
        data-collection-batch-layer="overflow"
        :aria-label="moreActionsLabel"
      >
        <ScButton
          v-for="action in settlement.overflow"
          :key="`selection-overflow-${action.key}`"
          size="small"
          variant="secondary"
          :data-action-key="action.key"
          :disabled="loading || !selectedCount || !action.enabled"
          :title="action.hint || ''"
          @click="runAction(action.key)"
        >
          {{ action.label }}
        </ScButton>
      </div>
    </div>
    <ScButton class="batch-clear" size="small" variant="ghost" :disabled="loading" @click="clearSelection">
      {{ clearLabel }}
    </ScButton>
    <span v-if="selectedCount > 0 && message" class="batch-message" aria-live="polite">{{ message }}</span>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { resolveCollectionBatchActionSettlement, type CollectionBatchAction } from '../../app/presentation/collectionActionSettlement';
import { useCollectionBatchOverflow } from '../../app/presentation/useCollectionBatchOverflow';
import ScButton from '../design-system/ScButton.vue';
import ScIcon from '../design-system/ScIcon.vue';

const props = defineProps<{
  actions: readonly CollectionBatchAction[];
  selectedCount: number;
  selectedCountLabel: string;
  moreActionsLabel: string;
  clearLabel: string;
  loading: boolean;
  message?: string;
}>();

const emit = defineEmits<{
  action: [key: string];
  clear: [];
}>();

const settlement = computed(() => resolveCollectionBatchActionSettlement(props.actions));
const { batchOverflowRoot, batchOverflowToggle, batchOverflowOpen, toggleBatchOverflow } = useCollectionBatchOverflow();

function runAction(key: string) {
  if (!key || props.selectedCount <= 0) return;
  batchOverflowOpen.value = false;
  emit('action', key);
}

function clearSelection() {
  batchOverflowOpen.value = false;
  emit('clear');
}
</script>

<style scoped src="./CollectionBatchActionBar.css"></style>
