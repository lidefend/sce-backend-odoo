<template>
  <nav
    class="scenario-side-navigation"
    :class="{ 'scenario-side-navigation--collapsed': collapsed }"
    aria-label="业务场景导航"
    data-semantic-component="ProductScenarioNavigation"
  >
    <label v-if="!collapsed" class="scenario-side-navigation__search">
      <span class="sr-only">搜索业务入口</span>
      <ScInput
        :model-value="search"
        type="search"
        placeholder="搜索业务入口..."
        aria-label="搜索业务入口"
        clearable
        appearance="navigation-search"
        @update:model-value="emit('update:search', String($event))"
      >
        <template #prefix><ScIcon name="search" :size="16" /></template>
      </ScInput>
    </label>

    <div class="scenario-side-navigation__tree" tabindex="0" aria-label="业务场景树">
      <template v-if="searching">
        <section class="scenario-group scenario-group--results" aria-label="搜索结果">
          <h3 class="scenario-group__heading">搜索结果</h3>
          <p v-if="!searchHits.length" class="scenario-search__empty">没有匹配的业务入口</p>
          <ul v-else class="scenario-entries">
            <li v-for="hit in searchHits" :key="hit.entry.menu_xmlid">
              <ScButton
                type="button"
                variant="ghost"
                appearance="menu-item"
                class="scenario-entry"
                :class="{ active: hit.entry.menu_id === activeMenuId }"
                :aria-current="hit.entry.menu_id === activeMenuId ? 'true' : undefined"
                @click="emit('select', hit.entry)"
              >
                <span class="scenario-entry__label" :title="hit.entry.label">{{ hit.entry.label }}</span>
                <span class="scenario-entry__scenario" :title="hit.scenarioName || hit.centerName">{{ hit.scenarioName || hit.centerName }}</span>
              </ScButton>
            </li>
          </ul>
        </section>
      </template>

      <template v-else>
        <section
          v-for="center in model.centers"
          :key="center.key"
          class="scenario-group"
          :data-center-key="center.key"
        >
          <ScButton
            type="button"
            variant="ghost"
            appearance="tree-item"
            class="scenario-center__toggle"
            :aria-expanded="expandedCenters.includes(center.key)"
            @click="emit('toggle-center', center.key)"
          >
            <ScIcon name="chevron-right" :size="16" />
            <span>{{ center.name }}</span>
          </ScButton>

          <div v-if="expandedCenters.includes(center.key)" class="scenario-center__body">
            <ul v-if="center.entries.length" class="scenario-entries scenario-entries--direct">
              <li v-for="entry in center.entries" :key="`${entry.menu_id}-${entry.action_id}`">
                <ScButton
                  type="button"
                  variant="ghost"
                  appearance="menu-item"
                  class="scenario-entry"
                  :class="{ active: entry.menu_id === activeMenuId }"
                  :aria-current="entry.menu_id === activeMenuId ? 'true' : undefined"
                  @click="emit('select', entry)"
                >
                  <span class="scenario-entry__label" :title="entry.label">{{ entry.label }}</span>
                  <span class="scenario-entry__unconfigured">待配置</span>
                </ScButton>
              </li>
            </ul>

            <section
              v-for="scenario in center.scenarios"
              :key="scenario.key"
              class="scenario-scenario"
              :data-scenario-key="scenario.key"
            >
              <ScButton
                type="button"
                variant="ghost"
                appearance="tree-item"
                class="scenario-scenario__toggle"
                :aria-expanded="expandedScenarios.includes(scenario.key)"
                @click="emit('toggle-scenario', scenario.key)"
              >
                <span>{{ scenario.name }}</span>
              </ScButton>
              <ul v-if="expandedScenarios.includes(scenario.key)" class="scenario-entries">
                <li v-for="entry in scenario.entries" :key="`${entry.menu_id}-${entry.action_id}`">
                  <ScButton
                    type="button"
                    variant="ghost"
                    appearance="menu-item"
                    class="scenario-entry"
                    :class="{ active: entry.menu_id === activeMenuId }"
                    :aria-current="entry.menu_id === activeMenuId ? 'true' : undefined"
                    @click="emit('select', entry)"
                  >
                    <span class="scenario-entry__label" :title="entry.label">{{ entry.label }}</span>
                    <span v-if="entry.intent_label" class="scenario-entry__intent" :title="entry.intent_label">{{ entry.intent_label }}</span>
                  </ScButton>
                </li>
              </ul>
            </section>
          </div>
        </section>

        <p v-if="isEmpty" class="scenario-side-navigation__empty" role="status">
          当前没有可用的业务入口
        </p>
      </template>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue';
import {
  searchScenarioSurface,
  type ScenarioNavEntry,
  type ScenarioNavigationModel,
} from '../../app/scenarioSurface';
import ScIcon from '../design-system/ScIcon.vue';
import ScButton from '../design-system/ScButton.vue';
import ScInput from '../design-system/ScInput.vue';

const props = withDefaults(defineProps<{
  model: ScenarioNavigationModel;
  activeMenuId?: number;
  collapsed?: boolean;
  search: string;
  expandedCenters?: string[];
  expandedScenarios?: string[];
}>(), {
  activeMenuId: undefined,
  collapsed: false,
  search: '',
  expandedCenters: () => [],
  expandedScenarios: () => [],
});

const emit = defineEmits<{
  (event: 'select', entry: ScenarioNavEntry): void;
  (event: 'toggle-center', key: string): void;
  (event: 'toggle-scenario', key: string): void;
  (event: 'ensure-expanded', centerKey: string, scenarioKey: string): void;
  (event: 'update:search', value: string): void;
}>();

const searching = computed(() => Boolean(props.search.trim()));
const searchHits = computed(() => searchScenarioSurface(props.model, props.search));
const isEmpty = computed(() => !props.model.centers.length);

function centerForMenu(menuId: number): { center: string; scenario: string } | null {
  if (menuId <= 0) return null;
  for (const center of props.model.centers) {
    if (center.entries.some((entry) => entry.menu_id === menuId)) {
      return { center: center.key, scenario: '' };
    }
    for (const scenario of center.scenarios) {
      if (scenario.entries.some((entry) => entry.menu_id === menuId)) {
        return { center: center.key, scenario: scenario.key };
      }
    }
  }
  return null;
}

watch(
  () => props.activeMenuId,
  (menuId) => {
    const location = centerForMenu(Number(menuId || 0));
    if (!location) return;
    const missingCenter = !props.expandedCenters.includes(location.center);
    const missingScenario = location.scenario && !props.expandedScenarios.includes(location.scenario);
    if (missingCenter || missingScenario) {
      emit('ensure-expanded', location.center, location.scenario);
    }
  },
  { immediate: true },
);
</script>

<style scoped>
.scenario-side-navigation {
  display: grid;
  grid-template-rows: max-content minmax(0, 1fr);
  gap: var(--sc-nav-row-gap);
  min-height: 0;
  min-width: 0;
}

.scenario-side-navigation--collapsed {
  grid-template-rows: minmax(0, 1fr);
}

.scenario-side-navigation--collapsed .scenario-side-navigation__search {
  display: none;
}

.scenario-side-navigation__search {
  display: flex;
  align-items: center;
}

.scenario-side-navigation__search :deep(.sc-input) { width: 100%; }

.scenario-side-navigation__tree {
  min-height: 0;
  min-width: 0;
  overflow: auto;
  overflow-x: hidden;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
  padding: 0 var(--sc-nav-row-gap);
}

.scenario-group {
  margin: 0 0 var(--sc-nav-row-gap);
}

.scenario-group__heading {
  margin: 0 0 4px;
  font-size: 12px;
  color: var(--sc-semantic-text-muted);
  padding: 0 8px;
}

.scenario-center__toggle,
.scenario-scenario__toggle,
.scenario-entry {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  text-align: left;
  cursor: pointer;
  padding: 7px 8px;
}

.scenario-center__toggle {
  font-weight: 600;
}

.scenario-scenario__toggle {
  padding-left: 18px;
  font-weight: 500;
}

.scenario-entry {
  padding-left: 18px;
  justify-content: space-between;
  gap: 8px;
}

.scenario-entry__label {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.scenario-entry__intent,
.scenario-entry__unconfigured,
.scenario-entry__scenario {
  flex: none;
  max-width: 42%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 11px;
  color: var(--sc-semantic-text-muted);
}

.scenario-entry__intent {
  border: 1px solid var(--sc-semantic-border);
  border-radius: 999px;
  padding: 0 6px;
  line-height: 16px;
}

.scenario-entry__unconfigured {
  border: 1px dashed var(--sc-semantic-border);
  border-radius: 999px;
  padding: 0 6px;
  line-height: 16px;
}

.scenario-entries {
  list-style: none;
  margin: 0;
  padding: 0;
}

.scenario-entry.active {
  font-weight: 600;
}

.scenario-search__empty,
.scenario-side-navigation__empty {
  margin: 8px;
  font-size: 12px;
  color: var(--sc-semantic-text-muted);
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
</style>
