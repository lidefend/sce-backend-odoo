<script setup lang="ts">
import { computed } from 'vue';
import type { SceneReviewPanel } from '../../contracts/sceneObjectPage';
import { useSceneUiKit } from '../../kits/context';
import SceneButton from './SceneButton.vue';

const props = defineProps<{ panel: SceneReviewPanel; open: boolean }>();
const emit = defineEmits<{ 'update:open': [value: boolean] }>();
const { kit, runtime } = useSceneUiKit();
const componentModel = computed(() => runtime.value?.componentModel || 'native');
const driverDrawer = computed(() => runtime.value?.components.drawer);

function setOpen(next: boolean): void {
  emit('update:open', next);
}

</script>

<template>
  <div class="scene-review-control" :data-review-driver="kit">
    <SceneButton tier="transparent" data-review-trigger @click="setOpen(true)">
      {{ panel.triggerLabel }}
    </SceneButton>

    <component
      :is="driverDrawer"
      v-if="componentModel === 'vue' && driverDrawer && open"
      :visible="open"
      :header="panel.title"
      size="520px"
      :footer="false"
      data-review-panel
      @update:visible="setOpen"
    >
      <div class="scene-review-body">
        <p>{{ panel.description }}</p>
        <div v-for="group in panel.groups" :key="group.id" class="scene-review-group">
          <h3>{{ group.title }}</h3>
          <dl>
            <div v-for="fact in group.facts" :key="fact.id">
              <dt>{{ fact.label }}</dt><dd>{{ fact.value }}</dd>
            </div>
          </dl>
        </div>
        <ul class="scene-review-checklist">
          <li v-for="fact in panel.checklist" :key="fact.id" :data-tone="fact.tone || 'Neutral'">
            <span aria-hidden="true">✓</span><strong>{{ fact.label }}</strong><small>{{ fact.value }}</small>
          </li>
        </ul>
      </div>
    </component>

    <div v-else-if="open" class="scene-native-overlay" data-review-panel role="dialog" aria-modal="true" :aria-label="panel.title">
      <button type="button" class="scene-native-overlay__backdrop" aria-label="关闭核对面板" @click="setOpen(false)"></button>
      <aside>
        <header><h2>{{ panel.title }}</h2><button type="button" @click="setOpen(false)">×</button></header>
        <div class="scene-review-body">
          <p>{{ panel.description }}</p>
          <div v-for="group in panel.groups" :key="group.id" class="scene-review-group">
            <h3>{{ group.title }}</h3>
            <dl>
              <div v-for="fact in group.facts" :key="fact.id">
                <dt>{{ fact.label }}</dt><dd>{{ fact.value }}</dd>
              </div>
            </dl>
          </div>
          <ul class="scene-review-checklist">
            <li v-for="fact in panel.checklist" :key="fact.id" :data-tone="fact.tone || 'Neutral'">
              <span aria-hidden="true">✓</span><strong>{{ fact.label }}</strong><small>{{ fact.value }}</small>
            </li>
          </ul>
        </div>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.scene-review-control {
  display: flex;
  justify-content: flex-end;
}

.scene-review-body {
  min-width: min(460px, 80vw);
  padding: 4px 2px 14px;
  color: var(--sc-scene-text);
}

.scene-review-body > p {
  margin: 0 0 16px;
  color: var(--sc-scene-muted);
  font-size: 13px;
  line-height: 1.5;
}

.scene-review-group {
  padding: 12px 0;
  border-top: 1px solid var(--sc-scene-border);
}

.scene-review-group h3,
.scene-review-group dl {
  margin: 0;
}

.scene-review-group h3 {
  margin-bottom: 8px;
  font-size: 14px;
}

.scene-review-group dl div {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  padding: 4px 0;
  font-size: 12px;
}

.scene-review-group dt {
  color: var(--sc-scene-muted);
}

.scene-review-group dd {
  margin: 0;
  font-weight: 600;
  text-align: right;
}

.scene-review-checklist {
  display: grid;
  gap: 8px;
  margin: 4px 0 0;
  padding: 0;
  list-style: none;
}

.scene-review-checklist li {
  display: grid;
  grid-template-columns: 18px minmax(0, 1fr) auto;
  gap: 7px;
  align-items: center;
  padding: 9px 10px;
  border-radius: 7px;
  background: #f3f7fa;
  font-size: 12px;
}

.scene-review-checklist li > span {
  color: var(--sc-scene-success);
}

.scene-review-checklist li[data-tone='Critical'] > span {
  color: var(--sc-scene-warning);
}

.scene-review-checklist small {
  color: var(--sc-scene-muted);
}

.scene-native-overlay {
  position: fixed;
  z-index: 100;
  inset: 0;
}

.scene-native-overlay__backdrop {
  position: absolute;
  inset: 0;
  width: 100%;
  border: 0;
  background: rgba(21, 35, 49, 0.38);
}

.scene-native-overlay > aside {
  position: absolute;
  top: 0;
  right: 0;
  width: min(520px, 92vw);
  height: 100%;
  overflow-y: auto;
  padding: 20px;
  background: white;
  box-shadow: -14px 0 34px rgba(22, 42, 63, 0.18);
}

.scene-native-overlay > aside > header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--sc-scene-border);
}

.scene-native-overlay h2 {
  font-size: 18px;
}

.scene-native-overlay header button {
  border: 0;
  background: transparent;
  font-size: 24px;
}

@media (max-width: 640px) {
  .scene-review-body {
    min-width: 0;
  }

  .scene-review-checklist li {
    grid-template-columns: 18px minmax(0, 1fr);
  }

  .scene-review-checklist small {
    grid-column: 2;
  }
}
</style>
