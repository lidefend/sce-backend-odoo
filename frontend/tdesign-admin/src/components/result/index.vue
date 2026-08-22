<template>
  <div class="result-container">
    <div class="result-bg-img">
      <component :is="dynamicComponent"></component>
    </div>
    <div class="result-title">{{ title }}</div>
    <div class="result-tip">{{ tip }}</div>
    <div v-if="traceId" class="result-trace">
      <span>Trace ID：{{ traceId }}</span>
      <t-button size="small" variant="text" @click="copyTraceId">复制</t-button>
    </div>
    <slot />
  </div>
</template>
<script setup lang="ts">
import { MessagePlugin } from 'tdesign-vue-next';
import { computed } from 'vue';
import { useRoute } from 'vue-router';

import { getLastRequestMeta } from '@/api/odoo';
import Result403Icon from '@/assets/assets-result-403.svg?component';
import Result404Icon from '@/assets/assets-result-404.svg?component';
import Result500Icon from '@/assets/assets-result-500.svg?component';
import ResultIeIcon from '@/assets/assets-result-ie.svg?component';
import ResultMaintenanceIcon from '@/assets/assets-result-maintenance.svg?component';
import ResultWifiIcon from '@/assets/assets-result-wifi.svg?component';

const { type } = defineProps({
  bgUrl: {
    type: String,
    default: '',
  },
  title: {
    type: String,
    default: '',
  },
  tip: {
    type: String,
    default: '',
  },
  type: {
    type: String,
    default: '',
  },
});

const route = useRoute();
const traceId = computed(() =>
  String(route.query.trace_id || route.query.traceId || getLastRequestMeta().traceId || ''),
);

async function copyTraceId() {
  if (!traceId.value) return;
  await navigator.clipboard.writeText(traceId.value);
  MessagePlugin.success('Trace ID 已复制');
}

const dynamicComponent = computed(() => {
  switch (type) {
    case '403':
      return Result403Icon;
    case '404':
      return Result404Icon;
    case '500':
      return Result500Icon;
    case 'ie':
      return ResultIeIcon;
    case 'wifi':
      return ResultWifiIcon;
    case 'maintenance':
      return ResultMaintenanceIcon;
    default:
      return Result403Icon;
  }
});
</script>
<style lang="less" scoped>
.result {
  &-link {
    color: var(--td-brand-color);
    text-decoration: none;
    cursor: pointer;

    &:hover {
      color: var(--td-brand-color);
    }

    &:active {
      color: var(--td-brand-color);
    }

    &--active {
      color: var(--td-brand-color);
    }

    &:focus {
      text-decoration: none;
    }
  }

  &-container {
    min-height: 400px;
    height: 75vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
  }

  &-bg-img {
    width: 200px;
    color: var(--td-brand-color);
  }

  &-title {
    font: var(--td-font-title-large);
    font-style: normal;
    margin-top: var(--td-comp-margin-l);
    color: var(--td-text-color-primary);
  }

  &-tip {
    margin: var(--td-comp-margin-s) 0 var(--td-comp-margin-xxxl);
    font: var(--td-font-body-medium);
    color: var(--td-text-color-secondary);
  }

  &-trace {
    display: flex;
    align-items: center;
    gap: var(--td-comp-margin-xs);
    max-width: min(680px, calc(100vw - 48px));
    padding: 8px 12px;
    margin: calc(var(--td-comp-margin-xxxl) * -1 + var(--td-comp-margin-l)) 0 var(--td-comp-margin-l);
    border: 1px solid var(--td-border-level-1-color);
    border-radius: var(--td-radius-default);
    background: var(--td-bg-color-secondarycontainer);
    color: var(--td-text-color-secondary);
    font: var(--td-font-body-small);
  }

  &-trace span {
    min-width: 0;
    overflow-wrap: anywhere;
  }
}
</style>
