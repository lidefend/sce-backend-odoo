<template>
  <section
    v-if="duties.length"
    class="platform-duty"
    data-semantic-component="PlatformDutyPanel"
    :data-platform-audience="audience"
  >
    <header class="platform-duty__header">
      <p class="platform-duty__eyebrow">平台管理职责</p>
      <h2 class="platform-duty__title">{{ audienceLabel }}</h2>
      <p class="platform-duty__meta">契约 {{ contractVersion }} · 来源 {{ source }}</p>
    </header>
    <ScTable
      class="platform-duty__table"
      :label="`${audienceLabel}职责列表`"
      :data="duties"
      :columns="columns"
      row-key="key"
      size="small"
      :row-attributes="rowAttributes"
    >
      <template #action="{ row }">
        <ScButton
          v-if="actionOf(row).kind === 'navigate'"
          type="button"
          variant="secondary"
          size="small"
          @click="open(row)"
        >
          打开
        </ScButton>
        <span v-else class="platform-duty__pending">{{ actionHint(row) }}</span>
      </template>
    </ScTable>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRouter } from 'vue-router';
import { useSessionStore } from '../../stores/session';
import { resolveDutyAction, type DutyAction } from './dutyAction';
import ScButton from '../design-system/ScButton.vue';
import ScTable from '../design-system/ScTable.vue';

interface PlatformDutyEntry extends Record<string, unknown> {
  key: string;
  label?: string;
  description?: string;
  state?: string;
  state_label?: string;
  route?: string | null;
  intent?: string | null;
  scene_key?: string;
}

const router = useRouter();
const session = useSessionStore();

const surface = computed(() => session.user?.platform_duty);
const audience = computed(() => surface.value?.audience || 'none');
const duties = computed(() =>
  ((surface.value?.duties || []) as PlatformDutyEntry[]).filter((duty) => Boolean(duty?.key)),
);
const audienceLabel = computed(() => (audience.value === 'platform-admin' ? '平台控制台' : '租户配置'));
const contractVersion = computed(() => surface.value?.contract_version || '-');
const source = computed(() => surface.value?.source || '-');

const columns = [
  { colKey: 'label', title: '职责', width: 180 },
  { colKey: 'description', title: '说明', ellipsis: true },
  { colKey: 'state_label', title: '状态', width: 100 },
  { colKey: 'action', title: '操作', width: 120, align: 'right' },
];

function actionOf(duty: PlatformDutyEntry): DutyAction {
  return resolveDutyAction(duty);
}

function actionHint(duty: PlatformDutyEntry): string {
  const action = actionOf(duty);
  if (action.kind === 'inline') return '需在官方页面打开';
  if (action.kind === 'intent') return `入口：${action.intent}`;
  return '暂无入口';
}

function rowAttributes(context: unknown) {
  const candidate = context && typeof context === 'object' ? context as Record<string, unknown> : {};
  const row = (candidate.row && typeof candidate.row === 'object' ? candidate.row : candidate) as PlatformDutyEntry;
  return {
    'data-duty-key': row.key,
    'data-duty-state': row.state || 'available',
    'data-duty-action': actionOf(row).kind,
  };
}

function open(duty: PlatformDutyEntry) {
  const action = actionOf(duty);
  if (action.kind !== 'navigate') return;
  void router.push(action.route);
}
</script>

<style scoped>
.platform-duty {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1rem 0;
}
.platform-duty__header {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.platform-duty__eyebrow {
  margin: 0;
  font-size: 0.75rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  opacity: 0.7;
}
.platform-duty__title {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
}
.platform-duty__meta {
  margin: 0;
  font-size: 0.75rem;
  opacity: 0.65;
}
.platform-duty__table {
  min-width: 0;
}
.platform-duty__pending {
  font-size: 0.75rem;
  color: var(--sc-app-text-muted);
}
</style>
