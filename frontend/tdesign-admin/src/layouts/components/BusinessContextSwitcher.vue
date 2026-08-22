<template>
  <div v-if="enabled" class="context-switchers">
    <t-dropdown v-if="companyOptions.length" trigger="click" placement="bottom-right">
      <t-button theme="default" variant="text" class="context-button">
        <template #icon><t-icon name="company" /></template>
        {{ companyLabel }}
        <template #suffix><t-icon name="chevron-down" /></template>
      </t-button>
      <template #dropdown>
        <t-dropdown-item
          v-for="item in companyOptions"
          :key="item.company_id"
          @click="select({ company_id: item.company_id, current_project_id: null })"
        >
          {{ item.company_name || item.company_id }}
        </t-dropdown-item>
      </template>
    </t-dropdown>
    <t-dropdown v-if="projectOptions.length" trigger="click" placement="bottom-right">
      <t-button theme="default" variant="text" class="context-button">
        <template #icon><t-icon name="folder" /></template>
        {{ projectLabel }}
        <template #suffix><t-icon name="chevron-down" /></template>
      </t-button>
      <template #dropdown>
        <t-dropdown-item @click="select({ current_project_id: null })">全部项目</t-dropdown-item>
        <t-dropdown-item v-for="item in projectOptions" :key="item.id" @click="select({ current_project_id: item.id })">
          {{ item.name || item.display_name || item.code || item.id }}
        </t-dropdown-item>
      </template>
    </t-dropdown>
    <t-dropdown v-if="operationOptions.length" trigger="click" placement="bottom-right">
      <t-button theme="default" variant="text" class="context-button">
        <template #icon><t-icon name="flow" /></template>
        {{ operationLabel }}
        <template #suffix><t-icon name="chevron-down" /></template>
      </t-button>
      <template #dropdown>
        <t-dropdown-item
          v-for="item in operationOptions"
          :key="item.operation_strategy"
          @click="select({ operation_strategy: item.operation_strategy })"
        >
          {{ item.operation_strategy_label || item.operation_strategy || '全部经营方式' }}
        </t-dropdown-item>
      </template>
    </t-dropdown>
  </div>
</template>
<script setup lang="ts">
import { computed } from 'vue';

import { useUserStore } from '@/store';

type Dict = Record<string, any>;
const user = useUserStore();
const contract = computed(() => (user.recordContext || {}) as Dict);
const enabled = computed(
  () =>
    contract.value.enabled !== false &&
    Boolean(
      contract.value.company_options?.length ||
      contract.value.options?.length ||
      contract.value.operation_options?.length,
    ),
);
const companyOptions = computed(() => (contract.value.company_options || []) as Dict[]);
const projectOptions = computed(() => (contract.value.options || []) as Dict[]);
const operationOptions = computed(() => (contract.value.operation_options || []) as Dict[]);
const companyLabel = computed(() =>
  String(contract.value.company_name || companyOptions.value.find((item) => item.active)?.company_name || '公司'),
);
const projectLabel = computed(() =>
  String(contract.value.selected?.name || contract.value.selected?.display_name || '全部项目'),
);
const operationLabel = computed(() =>
  String(
    contract.value.operation_strategy_label ||
      operationOptions.value.find((item) => item.active)?.operation_strategy_label ||
      '经营方式',
  ),
);

async function select(change: Dict) {
  await user.switchBusinessContext({
    company_id: Object.hasOwn(change, 'company_id') ? change.company_id : contract.value.company_id,
    current_project_id: Object.hasOwn(change, 'current_project_id')
      ? change.current_project_id
      : contract.value.selected?.id,
    operation_strategy: Object.hasOwn(change, 'operation_strategy')
      ? change.operation_strategy
      : contract.value.operation_strategy,
  });
  window.location.reload();
}
</script>
<style scoped>
.context-switchers {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}

.context-button {
  max-width: 170px;
}

.context-button :deep(.t-button__text) {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
