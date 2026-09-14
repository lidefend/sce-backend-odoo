<template>
  <div
    class="professional-detail-collection"
    data-semantic-component="ProfessionalDetailCollectionControl"
    data-professional-field-family="detail-collection"
    :data-relation-model="authority.relationModel"
    :data-row-count="authority.rowCount"
    :data-column-count="authority.columnCount"
    :data-can-create="authority.canCreate"
    :data-can-inline-edit="authority.canInlineEdit"
    :data-removed-row-count="authority.removedRowCount"
    :data-validation-visible="authority.validationVisible"
    :data-summary-present="Boolean(authority.summary)"
    :data-presentation-mode="field.presentationMode"
    :data-render-profile="field.renderProfile"
    :data-control-state="field.readonly ? 'readonly' : 'editable'"
    :data-amount-binding-mode="amountBinding?.mode"
    :data-amount-binding-source="amountBinding?.sourceField"
    :data-amount-binding-target="amountBinding?.targetField"
    :data-amount-binding-active="amountUsesDetails"
    :data-amount-binding-empty-behavior="amountBinding?.emptyBehavior"
  >
    <ScDisclosure
      v-if="optionalPresentation?.render"
      class="professional-detail-collection__optional"
      :title="optionalPresentation.title"
      :open="optionalPresentation.open"
      destroy-on-collapse
    >
      <ScInlineState
        v-if="optionalPresentation.linkedAmountMessage"
        class="professional-detail-collection__linkage"
        state="info"
        density="compact"
        :label="optionalPresentation.linkedAmountMessage"
      />
      <slot :adapter="guardedAdapter" />
    </ScDisclosure>
    <slot v-else-if="!optionalDetails" :adapter="guardedAdapter" />
    <IntentConfirmationDialog ref="confirmationRef" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import type { FormSectionFieldSchema } from '../template/formSection.types';
import type { RelationFieldAdapter } from '../template/relationField.types';
import IntentConfirmationDialog from '../business/IntentConfirmationDialog.vue';
import ScDisclosure from '../design-system/ScDisclosure.vue';
import ScInlineState from '../design-system/ScInlineState.vue';
import {
  detailAmountBindingConfig,
  detailCollectionAuthority,
  optionalDetailCollectionPresentation,
  optionalDetailCollectionRemovalConfirmation,
} from './professionalDetailCollectionModel';

const props = defineProps<{ field: FormSectionFieldSchema; adapter: RelationFieldAdapter }>();
const confirmationRef = ref<InstanceType<typeof IntentConfirmationDialog> | null>(null);
const authority = computed(() => detailCollectionAuthority(props.field, props.adapter));
const amountBinding = computed(() => detailAmountBindingConfig(props.field));
const amountUsesDetails = computed(() => {
  const stateField = amountBinding.value?.stateField;
  if (!stateField) return false;
  return ['true', '1'].includes(props.adapter.inputFieldValue(stateField).trim().toLowerCase());
});
const optionalPresentation = computed(() => (
  optionalDetailCollectionPresentation(
    props.field,
    authority.value.rowCount,
    amountUsesDetails.value,
    authority.value.removedRowCount,
  )
));

async function removeOne2manyRow(name: string, rowKey: string) {
  const confirmation = optionalDetailCollectionRemovalConfirmation(
    props.field,
    authority.value.rowCount,
  );
  if (confirmation) {
    const confirmed = await confirmationRef.value?.confirm({
      actionLabel: confirmation.actionLabel,
      message: confirmation.message,
    });
    if (!confirmed) return;
  }
  props.adapter.removeOne2manyRow(name, rowKey);
}

const guardedAdapter = computed<RelationFieldAdapter>(() => ({
  ...props.adapter,
  removeOne2manyRow: (name, rowKey) => { void removeOne2manyRow(name, rowKey); },
}));
</script>

<style scoped>
.professional-detail-collection { min-width: 0; width: 100%; }
.professional-detail-collection__optional { width: 100%; }
.professional-detail-collection__linkage { margin-bottom: var(--sc-product-space-3); }
</style>
