<template>
  <div data-semantic-component="PaymentSettlementDetailCollectionControl">
    <ProfessionalDetailCollectionControl :field="field" :adapter="adapter">
      <template #default="{ adapter: detailAdapter }">
        <X2ManyRelationRenderer :field="field" :adapter="detailAdapter" @reload-requested="emit('reload-requested')">
          <template #collection-actions>
            <ScButton
              v-if="introduceReady"
              type="button"
              variant="secondary"
              size="small"
              :disabled="adapter.busy || introduceBusy"
              :data-contract-entry-label="introduceContract.buttonLabel"
              @click="dialogOpen = true"
            >
              <ScIcon name="clipboard" :size="14" />
              {{ introduceContract.buttonLabel }}
            </ScButton>
            <ScButton
              v-else
              type="button"
              variant="secondary"
              size="small"
              disabled
              data-contract-semantic-gap
              :data-contract-semantic-missing="introduceMissing.join(',')"
            >
              <ScIcon name="clipboard" :size="14" />
              {{ field.label }}
            </ScButton>
          </template>
        </X2ManyRelationRenderer>
      </template>
    </ProfessionalDetailCollectionControl>
    <PaymentSettlementIntroduceDialog
      v-if="introduceContract"
      :contract="introduceContract"
      :adapter="adapter"
      :open="dialogOpen"
      @close="dialogOpen = false"
      @introduced="emit('reload-requested')"
      @busy-change="introduceBusy = $event"
    />
    <ScInlineState
      v-else
      state="error"
      data-contract-semantic-gap
      :label="settlementIntroduceContractGapLabel(introduceMissing)"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import ScButton from '../design-system/ScButton.vue';
import ScIcon from '../design-system/ScIcon.vue';
import ScInlineState from '../design-system/ScInlineState.vue';
import X2ManyRelationRenderer from '../template/X2ManyRelationRenderer.vue';
import type { FormSectionFieldSchema } from '../template/formSection.types';
import type { RelationFieldAdapter } from '../template/relationField.types';
import ProfessionalDetailCollectionControl from './ProfessionalDetailCollectionControl.vue';
import PaymentSettlementIntroduceDialog from './PaymentSettlementIntroduceDialog.vue';
import {
  resolveSettlementIntroduceContract,
  settlementIntroduceContractGapLabel,
} from './paymentSettlementIntroduceDialogModel';
import type { SettlementIntroduceContract } from './paymentSettlementIntroduceDialogModel';

const props = defineProps<{ field: FormSectionFieldSchema; adapter: RelationFieldAdapter }>();
const emit = defineEmits<{ 'reload-requested': [] }>();
const dialogOpen = ref(false);
const introduceBusy = ref(false);
// The entry action is only offered when the effective contract declares the
// whole introduce vocabulary.  A gap keeps the record intact and surfaces the
// missing semantics instead of opening a dialog built from guesses.
const introduceResolution = computed(() => resolveSettlementIntroduceContract(props.field));
// The default web typecheck runs without strictNullChecks, where a boolean
// discriminant cannot narrow a union.  Resolve the variant here with an `in`
// check so neither the template nor the script depends on that narrowing.
const introduceContract = computed<SettlementIntroduceContract | null>(() =>
  'contract' in introduceResolution.value ? introduceResolution.value.contract : null,
);
const introduceMissing = computed<readonly string[]>(() =>
  'missing' in introduceResolution.value ? introduceResolution.value.missing : [],
);
const introduceReady = computed(() => introduceContract.value !== null);
</script>
