<template>
  <div data-semantic-component="PaymentSettlementDetailCollectionControl">
    <X2ManyRelationRenderer :field="field" :adapter="adapter" @reload-requested="emit('reload-requested')">
      <template #collection-actions>
        <ScButton
          type="button"
          variant="secondary"
          size="small"
          :disabled="adapter.busy || introduceBusy"
          @click="dialogOpen = true"
        >
          <ScIcon name="clipboard" :size="14" />
          {{ introduceLabel }}
        </ScButton>
      </template>
    </X2ManyRelationRenderer>
    <PaymentSettlementIntroduceDialog
      :field="field"
      :adapter="adapter"
      :open="dialogOpen"
      @close="dialogOpen = false"
      @introduced="emit('reload-requested')"
      @busy-change="introduceBusy = $event"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import ScButton from '../design-system/ScButton.vue';
import ScIcon from '../design-system/ScIcon.vue';
import X2ManyRelationRenderer from '../template/X2ManyRelationRenderer.vue';
import type { FormSectionFieldSchema } from '../template/formSection.types';
import type { RelationFieldAdapter } from '../template/relationField.types';
import PaymentSettlementIntroduceDialog from './PaymentSettlementIntroduceDialog.vue';

const props = defineProps<{ field: FormSectionFieldSchema; adapter: RelationFieldAdapter }>();
const emit = defineEmits<{ 'reload-requested': [] }>();
const dialogOpen = ref(false);
const introduceBusy = ref(false);
const introduceLabel = computed(() => String(props.field.componentConfig?.introduceLabel || '引入明细'));
</script>
