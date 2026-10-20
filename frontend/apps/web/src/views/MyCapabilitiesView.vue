<template>
  <ScPage class="my-capabilities sc-product-main-surface" content-layout="data-grid" data-semantic-component="MyCapabilitiesView">
    <div class="my-capabilities-head">
      <div>
        <h1>我的能力</h1>
        <p>按当前账号展示可办理事项，以及不可用是无权限、无数据还是未发布。</p>
      </div>
      <ScButton type="button" variant="ghost" :disabled="loading" @click="load">重新读取</ScButton>
    </div>

    <ScInlineState v-if="loading" state="loading" label="正在加载能力清单。" />
    <ScInlineState v-else-if="error" state="error" :label="error">
      <template #actions><ScButton type="button" variant="secondary" @click="load">重试</ScButton></template>
    </ScInlineState>
    <ScInlineState v-else-if="gap" state="error" :label="gap" />

    <template v-else>
      <section v-for="entry in Array.from(byEntry.keys())" :key="entry" class="capability-group" :data-capability-entry="entry">
        <h2>{{ entry }}</h2>
        <div class="capability-grid">
          <article
            v-for="item in byEntry.get(entry) || []"
            :key="item.key"
            class="capability-card"
            :data-capability-key="item.key"
            :data-capability-status="item.status"
            :data-capability-available="item.available ? 'true' : 'false'"
          >
            <div class="capability-card-head">
              <strong>{{ item.label }}</strong>
              <span class="capability-status-badge" :data-capability-status="item.status">{{ capabilityStatusLabel(item.status) }}</span>
            </div>
            <p class="capability-description">{{ item.description }}</p>
            <p class="capability-authority">依据：{{ item.authority || '—' }}</p>
            <p v-if="!item.available" class="capability-reason">{{ item.reason === 'planned' ? '该能力尚未发布，暂不可用。' : item.reason }}</p>
          </article>
        </div>
      </section>
      <ScInlineState v-if="!capabilities.length" state="empty" label="当前账号没有声明可用能力。" />
    </template>
  </ScPage>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import ScPage from '../components/design-system/ScPage.vue';
import ScButton from '../components/design-system/ScButton.vue';
import ScInlineState from '../components/design-system/ScInlineState.vue';
import { capabilityStatusLabel } from '../app/productCapabilityCatalogProjection';
import { useMyCapabilities } from '../composables/myCapabilities/useMyCapabilities';

const { loading, error, gap, capabilities, byEntry, load } = useMyCapabilities();

onMounted(() => {
  void load();
});
</script>

<style scoped>
.my-capabilities-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.my-capabilities-head h1 { margin: 0; }
.my-capabilities-head p { margin: 4px 0 0; color: var(--sc-app-text-secondary); }
.capability-group { margin-top: 24px; }
.capability-group h2 { margin: 0 0 8px; font-size: 16px; }
.capability-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px; }
.capability-card { display: grid; gap: 8px; padding: 14px; border: 1px solid var(--sc-app-border); border-radius: var(--sc-radius-md); background: var(--sc-app-panel); min-width: 0; }
.capability-card-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.capability-card-head strong { overflow-wrap: anywhere; }
.capability-status-badge { flex: none; font-size: 12px; padding: 2px 8px; border-radius: 999px; color: var(--sc-app-text-secondary); background: var(--sc-app-border); }
.capability-description { margin: 0; color: var(--sc-app-text-primary); }
.capability-authority { margin: 0; color: var(--sc-app-text-secondary); font-size: 12px; overflow-wrap: anywhere; }
.capability-reason { margin: 0; color: var(--sc-app-text-muted); font-size: 12px; }
</style>
