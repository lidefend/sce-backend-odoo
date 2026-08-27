<script setup lang="ts">
import { computed, ref } from 'vue';
import type { SceneActivityTab } from '../../contracts/sceneObjectPage';
import { useSceneUiKit } from '../../kits/context';

const props = defineProps<{ tabs: SceneActivityTab[] }>();
const { runtime } = useSceneUiKit();
const componentModel = computed(() => runtime.value?.componentModel || 'native');
const driverTabs = computed(() => runtime.value?.components.tabs);
const driverTabPanel = computed(() => runtime.value?.components['tab-panel']);
const activeId = ref(props.tabs[0]?.id || '');

function activate(id: string): void {
  activeId.value = id;
}
</script>

<template>
  <component
    :is="driverTabs"
    v-else-if="componentModel === 'vue' && driverTabs && driverTabPanel"
    class="scene-primitive-tabs scene-driver-tabs"
    :value="activeId"
    @change="activate"
  >
    <component
      :is="driverTabPanel"
      v-for="tab in tabs"
      :key="tab.id"
      :value="tab.id"
      :label="tab.count === undefined ? tab.label : `${tab.label} ${tab.count}`"
      :data-activity-tab="tab.id"
    >
      <div v-if="tab.items.length" class="scene-activity-list">
        <article v-for="item in tab.items" :key="item.id" class="scene-activity-item">
          <span class="scene-activity-dot" :data-tone="item.tone || 'Neutral'"></span>
          <div>
            <div class="scene-activity-item__title"><strong>{{ item.title }}</strong><span>{{ item.meta }}</span></div>
            <p>{{ item.detail }}</p>
          </div>
        </article>
      </div>
      <div v-else class="scene-empty-activity">{{ tab.emptyText || '暂无记录' }}</div>
    </component>
  </component>

  <div v-else class="scene-primitive-tabs scene-native-tabs">
    <div class="scene-native-tabs__bar" role="tablist">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        type="button"
        role="tab"
        :aria-selected="tab.id === activeId"
        :data-activity-tab="tab.id"
        @click="activate(tab.id)"
      >
        {{ tab.label }}<span v-if="tab.count !== undefined">{{ tab.count }}</span>
      </button>
    </div>
    <template v-for="tab in tabs" :key="tab.id">
      <div v-if="tab.id === activeId && tab.items.length" class="scene-activity-list" role="tabpanel">
        <article v-for="item in tab.items" :key="item.id" class="scene-activity-item">
          <span class="scene-activity-dot" :data-tone="item.tone || 'Neutral'"></span>
          <div>
            <div class="scene-activity-item__title"><strong>{{ item.title }}</strong><span>{{ item.meta }}</span></div>
            <p>{{ item.detail }}</p>
          </div>
        </article>
      </div>
      <div v-else-if="tab.id === activeId" class="scene-empty-activity" role="tabpanel">
        {{ tab.emptyText || '暂无记录' }}
      </div>
    </template>
  </div>
</template>

<style scoped>
.scene-primitive-tabs {
  width: 100%;
}

.scene-native-tabs__bar {
  display: flex;
  gap: 6px;
  border-bottom: 1px solid #dfe5ec;
}

.scene-native-tabs__bar button {
  display: flex;
  gap: 6px;
  padding: 11px 14px 9px;
  border: 0;
  border-bottom: 3px solid transparent;
  background: transparent;
  color: #31475a;
  font: 600 13px/1 "Segoe UI", sans-serif;
}

.scene-native-tabs__bar button[aria-selected='true'] {
  border-bottom-color: #0a6ed1;
  color: #0a6ed1;
}

.scene-native-tabs__bar span {
  color: #6a7b8c;
}
</style>
