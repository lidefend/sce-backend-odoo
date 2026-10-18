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
    <ul class="platform-duty__grid">
      <li
        v-for="duty in duties"
        :key="duty.key"
        class="platform-duty__card"
        :data-duty-key="duty.key"
        :data-duty-state="duty.state || 'available'"
        :data-duty-action="actionOf(duty).kind"
      >
        <h3 class="platform-duty__card-title">{{ duty.label || duty.key }}</h3>
        <p class="platform-duty__capabilities">{{ (duty.capabilities || []).join(' · ') }}</p>
        <ScButton
          v-if="actionOf(duty).kind === 'navigate'"
          type="button"
          class="platform-duty__action"
          appearance="outline-action"
          size="small"
          @click="open(duty)"
        >
          打开
        </ScButton>
        <span v-else-if="actionOf(duty).kind === 'inline'" class="platform-duty__pending">
          该职责需在官方页面打开
        </span>
        <span v-else-if="actionOf(duty).kind === 'intent'" class="platform-duty__pending">
          入口：{{ duty.intent }}
        </span>
        <span v-else class="platform-duty__pending">暂无入口</span>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRouter } from 'vue-router';
import { useSessionStore } from '../../stores/session';
import { resolveDutyAction, type DutyAction } from './dutyAction';
import ScButton from '../design-system/ScButton.vue';

interface PlatformDutyEntry {
  key?: string;
  label?: string;
  capabilities?: string[];
  state?: string;
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

function actionOf(duty: PlatformDutyEntry): DutyAction {
  return resolveDutyAction(duty);
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
.platform-duty__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(16rem, 1fr));
  gap: 0.75rem;
  margin: 0;
  padding: 0;
  list-style: none;
}
.platform-duty__card {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.875rem 1rem;
  border: 1px solid rgba(15, 23, 42, 0.12);
  border-radius: 0.75rem;
  background: #ffffff;
}
.platform-duty__card[data-duty-state='available_unverified'] {
  border-style: dashed;
}
.platform-duty__card-title {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 600;
}
.platform-duty__capabilities {
  margin: 0;
  font-size: 0.75rem;
  opacity: 0.7;
  word-break: break-all;
}
.platform-duty__action {
  align-self: flex-start;
}
.platform-duty__pending {
  font-size: 0.75rem;
  color: #64748b;
}
.platform-duty__inline {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.875rem 1rem;
  border: 1px solid rgba(15, 23, 42, 0.12);
  border-radius: 0.75rem;
  background: #ffffff;
}
.platform-duty__inline-header {
  display: flex;
  align-items: baseline;
  gap: 0.75rem;
}
.platform-duty__inline-title {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 600;
}
.platform-duty__inline-meta {
  margin: 0;
  font-size: 0.75rem;
  opacity: 0.65;
}
.platform-duty__muted {
  opacity: 0.65;
}
.platform-duty__empty,
.platform-duty__error {
  margin: 0;
  font-size: 0.8rem;
  color: #64748b;
}
.platform-duty__error {
  color: #b91c1c;
}
.platform-duty__payload {
  margin: 0;
  max-height: 18rem;
  overflow: auto;
  font-size: 0.75rem;
  background: #f8fafc;
  padding: 0.5rem;
  border-radius: 0.5rem;
}
</style>
