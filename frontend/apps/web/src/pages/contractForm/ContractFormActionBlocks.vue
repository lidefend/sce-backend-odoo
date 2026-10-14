<template>
  <section v-if="strictContractMissingSummary && !isIntakeCreateMode" class="block contract-missing-block">
    <h3>配置状态提示</h3>
    <p class="contract-missing-summary">{{ strictContractMissingSummary }}</p>
    <p v-if="strictContractDefaultsSummary" class="contract-missing-defaults">{{ strictContractDefaultsSummary }}</p>
  </section>

  <section v-if="workflowTransitions.length && !isIntakeCreateMode && !suppressWorkflowTransitionsGate" class="block">
    <h3>流程操作</h3>
    <div class="chips">
      <ScButton
        v-for="item in workflowTransitions"
        :key="item.key"
        variant="secondary"
        :disabled="busy || !item.action"
        :title="item.notes || ''"
        @click="item.action && $emit('run-action', item.action)"
      >
        {{ item.label }}
      </ScButton>
    </div>
  </section>

  <section v-if="bodyActions.length && !isIntakeCreateMode && !suppressBodyActionsGate" class="block" data-form-body-action-block="body-actions">
    <h3>可执行操作</h3>
    <div class="chips">
      <ScButton
        v-for="action in bodyActions"
        :key="`body-${action.key}`"
        variant="secondary"
        :disabled="busy || !action.enabled"
        :title="action.hint"
        @click="$emit('run-action', action)"
      >
        {{ action.label }}<template v-if="showHud"> · {{ action.kind }}</template>
      </ScButton>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { ContractAction } from './types';
import ScButton from '../../components/design-system/ScButton.vue';

type WorkflowTransitionRow = {
  key: string;
  label: string;
  notes: string;
  action: ContractAction | null;
};

const props = defineProps<{
  strictContractMissingSummary: string;
  strictContractDefaultsSummary: string;
  workflowTransitions: WorkflowTransitionRow[];
  bodyActions: ContractAction[];
  isIntakeCreateMode: boolean;
  useNativeFormTree: boolean;
  /** Workflow transitions close only when their actions have a proven carrier. */
  suppressWorkflowTransitions?: boolean;
  /** Body actions close only when their actions have a proven carrier. */
  suppressBodyActions?: boolean;
  busy: boolean;
  showHud: boolean;
}>();

// The placeholders close only on an explicit carrier proof, so an unset proof
// never silently closes an action entry.
const suppressWorkflowTransitionsGate = computed(
  () => props.suppressWorkflowTransitions ?? false,
);
const suppressBodyActionsGate = computed(
  () => props.suppressBodyActions ?? false,
);

defineEmits<{
  'run-action': [action: ContractAction];
}>();
</script>

<style scoped src="./ContractFormActionBlocks.css"></style>
