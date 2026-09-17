<template>
  <section v-if="warnings.length && !isIntakeCreateMode" class="block warn" data-semantic-component="ContractFormActionBlocks" data-state="warning">
    <h3>提示信息</h3>
    <ul>
      <li v-for="item in warnings" :key="item">{{ item }}</li>
    </ul>
  </section>
  <section v-if="workflowEvidenceGateRows.length && !isIntakeCreateMode" class="block workflow-evidence-block">
    <h3>办理前置条件</h3>
    <ul class="workflow-evidence-list">
      <li
        v-for="item in workflowEvidenceGateRows"
        :key="item.reasonCode"
        :class="{ 'workflow-evidence-list__item--block': item.blocking }"
      >
        {{ item.message }}
      </li>
    </ul>
  </section>
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

  <section v-if="showSearchFilters && searchFilters.length && !isIntakeCreateMode && !suppressActionBlocks" class="block">
    <h3>快捷筛选</h3>
    <div class="chips">
      <ScButton
        v-for="item in searchFilters"
        :key="`flt-${item.key}`"
        variant="ghost"
        :class="{ active: activeFilterKey === item.key }"
        :disabled="busy || !item.key"
        @click="$emit('open-filter', item.key)"
      >
        {{ item.label }}
      </ScButton>
    </div>
  </section>

  <section v-if="bodyActions.length && !isIntakeCreateMode && !suppressBodyActionsGate" class="block">
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

type WorkflowEvidenceGateRow = {
  reasonCode: string;
  message: string;
  blocking: boolean;
};

type WorkflowTransitionRow = {
  key: string;
  label: string;
  notes: string;
  action: ContractAction | null;
};

type SearchFilterRow = {
  key: string;
  label: string;
};

const props = defineProps<{
  warnings: string[];
  workflowEvidenceGateRows: WorkflowEvidenceGateRow[];
  strictContractMissingSummary: string;
  strictContractDefaultsSummary: string;
  workflowTransitions: WorkflowTransitionRow[];
  showSearchFilters: boolean;
  searchFilters: SearchFilterRow[];
  activeFilterKey: string;
  bodyActions: ContractAction[];
  isIntakeCreateMode: boolean;
  useNativeFormTree: boolean;
  /** Record-list query presets never belong to a natively structured form body. */
  suppressActionBlocks: boolean;
  /** Workflow transitions close only when their actions have a proven carrier. */
  suppressWorkflowTransitions?: boolean;
  /** Body actions close only when their actions have a proven carrier. */
  suppressBodyActions?: boolean;
  busy: boolean;
  showHud: boolean;
}>();

// The placeholders keep their legacy switch as the default so an unset
// carrier proof never silently closes an action entry.
const suppressWorkflowTransitionsGate = computed(
  () => props.suppressWorkflowTransitions ?? props.suppressActionBlocks,
);
const suppressBodyActionsGate = computed(
  () => props.suppressBodyActions ?? props.suppressActionBlocks,
);

defineEmits<{
  'run-action': [action: ContractAction];
  'open-filter': [filterKey: string];
}>();
</script>

<style scoped src="./ContractFormActionBlocks.css"></style>
