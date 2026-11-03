<template>
  <nav
    class="scenario-side-navigation"
    :class="{ 'scenario-side-navigation--collapsed': collapsed }"
    aria-label="业务场景导航"
    data-semantic-component="ProductScenarioNavigation"
  >
    <div class="scenario-side-navigation__tree" tabindex="0" aria-label="业务场景树">
      <section v-if="model.horizontal.length" class="scenario-group scenario-group--horizontal">
        <h3 class="scenario-group__heading">我的工作</h3>
        <ul class="scenario-entries">
          <li v-for="entry in model.horizontal" :key="entry.menu_xmlid">
            <ScButton
              type="button"
              variant="ghost"
              appearance="menu-item"
              class="scenario-entry"
              :class="{ active: entry.menu_id === activeMenuId }"
              :aria-current="entry.menu_id === activeMenuId ? 'true' : undefined"
              @click="emit('select', entry)"
            >{{ entry.label }}</ScButton>
          </li>
        </ul>
      </section>

      <section
        v-for="domain in model.domains"
        :key="domain.key"
        class="scenario-group"
        :data-domain-key="domain.key"
      >
        <ScButton
          type="button"
          variant="ghost"
          appearance="tree-item"
          class="scenario-domain__toggle"
          :aria-expanded="isDomainOpen(domain.key)"
          @click="toggleDomain(domain.key)"
        >
          <ScIcon name="chevron-right" :size="16" />
          <span>{{ domain.name }}</span>
        </ScButton>

        <div v-if="isDomainOpen(domain.key)" class="scenario-scenarios">
          <section
            v-for="scenario in domain.scenarios"
            :key="scenario.key"
            class="scenario-scenario"
            :data-scenario-key="scenario.key"
          >
            <ScButton
              type="button"
              variant="ghost"
              appearance="tree-item"
              class="scenario-scenario__toggle"
              :aria-expanded="isScenarioOpen(scenario.key)"
              @click="toggleScenario(scenario.key)"
            >
              <span>{{ scenario.name }}</span>
            </ScButton>
            <div v-if="isScenarioOpen(scenario.key)" class="scenario-intents">
              <section v-for="intent in scenario.intents" :key="intent.intent" class="scenario-intent">
                <h4 class="scenario-intent__label">{{ intent.label }}</h4>
                <ul class="scenario-entries">
                  <li v-for="entry in intent.entries" :key="`${entry.menu_id}-${entry.action_id}`">
                    <ScButton
                      type="button"
                      variant="ghost"
                      appearance="menu-item"
                      class="scenario-entry"
                      :class="{ active: entry.menu_id === activeMenuId }"
                      :aria-current="entry.menu_id === activeMenuId ? 'true' : undefined"
                      @click="emit('select', entry)"
                    >{{ entry.label }}</ScButton>
                  </li>
                </ul>
              </section>
            </div>
          </section>
        </div>
      </section>
      <section v-if="model.platform.length" class="scenario-group scenario-group--management" data-management-navigation="true">
        <h3 class="scenario-group__heading">{{ model.platformLabel }}</h3>
        <ul class="scenario-entries">
          <li v-for="entry in model.platform" :key="entry.menu_xmlid">
            <ScButton type="button" variant="ghost" appearance="menu-item" class="scenario-entry"
              :class="{ active: entry.menu_id === activeMenuId }"
              :aria-current="entry.menu_id === activeMenuId ? 'page' : undefined"
              @click="emit('select', entry)">{{ entry.label }}</ScButton>
          </li>
        </ul>
      </section>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import type { ScenarioNavEntry, ScenarioNavigationModel } from '../../app/scenarioSurface';
import ScIcon from '../design-system/ScIcon.vue';
import ScButton from '../design-system/ScButton.vue';

const props = withDefaults(defineProps<{
  model: ScenarioNavigationModel;
  activeMenuId?: number;
  collapsed?: boolean;
}>(), {
  activeMenuId: undefined,
  collapsed: false,
});

const emit = defineEmits<{
  (event: 'select', entry: ScenarioNavEntry): void;
}>();

const expandedDomains = ref<string[]>([]);
const expandedScenarios = ref<string[]>([]);

function domainForMenu(menuId: number): { domain: string; scenario: string } | null {
  if (menuId <= 0) return null;
  for (const domain of props.model.domains) {
    for (const scenario of domain.scenarios) {
      for (const intent of scenario.intents) {
        if (intent.entries.some((entry) => entry.menu_id === menuId)) {
          return { domain: domain.key, scenario: scenario.key };
        }
      }
    }
  }
  return null;
}

watch(
  () => props.activeMenuId,
  (menuId) => {
    const location = domainForMenu(Number(menuId || 0));
    if (!location) return;
    if (!expandedDomains.value.includes(location.domain)) expandedDomains.value.push(location.domain);
    if (!expandedScenarios.value.includes(location.scenario)) expandedScenarios.value.push(location.scenario);
  },
  { immediate: true },
);

function isDomainOpen(key: string): boolean {
  return expandedDomains.value.includes(key);
}

function isScenarioOpen(key: string): boolean {
  return expandedScenarios.value.includes(key);
}

function toggleDomain(key: string): void {
  expandedDomains.value = isDomainOpen(key)
    ? expandedDomains.value.filter((item) => item !== key)
    : [...expandedDomains.value, key];
}

function toggleScenario(key: string): void {
  expandedScenarios.value = isScenarioOpen(key)
    ? expandedScenarios.value.filter((item) => item !== key)
    : [...expandedScenarios.value, key];
}
</script>

<style scoped>
.scenario-side-navigation {
  min-height: 0;
  min-width: 0;
}

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

.scenario-domain__toggle,
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

.scenario-domain__toggle {
  font-weight: 600;
}

.scenario-scenario__toggle {
  padding-left: 18px;
  font-weight: 500;
}

.scenario-entry {
  padding-left: 18px;
}

.scenario-intent__label {
  margin: 4px 0 2px;
  padding: 0 18px;
  font-size: 11px;
  font-weight: 600;
  color: var(--sc-semantic-text-muted);
}

.scenario-entries {
  list-style: none;
  margin: 0;
  padding: 0;
}

.scenario-entry.active {
  font-weight: 600;
}
</style>
