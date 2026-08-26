<template>
  <nav
    class="navigation-breadcrumb"
    :class="{ 'navigation-breadcrumb--minimal': minimal, 'navigation-breadcrumb--compact': compact }"
    aria-label="页面路径"
    data-semantic-component="NavigationBreadcrumb"
  >
    <ScButton
      v-for="(item, index) in items"
      :key="`${item.label}-${index}`"
      type="button"
      variant="ghost"
      size="small"
      class="navigation-breadcrumb__item"
      :class="{ active: index === items.length - 1 }"
      :disabled="!item.to"
      :aria-current="index === items.length - 1 ? 'page' : undefined"
      @click="item.to && emit('navigate', item.to)"
    >
      {{ item.label }}
    </ScButton>
  </nav>
</template>

<script setup lang="ts">
import type { PageBreadcrumb } from '../../app/pageIdentity';
import ScButton from '../design-system/ScButton.vue';

withDefaults(defineProps<{ items: PageBreadcrumb[]; minimal?: boolean; compact?: boolean }>(), {
  minimal: false,
  compact: false,
});
const emit = defineEmits<{ (event: 'navigate', target: string): void }>();
</script>

<style scoped>
.navigation-breadcrumb {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin: 0;
  min-width: 0;
  flex: 0 1 auto;
}

.navigation-breadcrumb--compact {
  display: none;
}

.navigation-breadcrumb__item {
  max-width: 100%;
  padding: 1px 5px;
  overflow-wrap: anywhere;
  border: 1px solid transparent;
  border-radius: 6px;
  background: transparent;
  color: var(--sc-app-text-secondary);
  font: inherit;
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0;
  text-transform: uppercase;
  cursor: pointer;
}

.navigation-breadcrumb__item.active {
  border-color: var(--sc-app-selected-border);
  background: var(--sc-app-selected-bg);
  color: var(--sc-app-selected-text);
  font-weight: 700;
}

.navigation-breadcrumb__item:disabled {
  cursor: default;
  opacity: 0.6;
}

.navigation-breadcrumb--minimal {
  gap: 6px;
}

.navigation-breadcrumb--minimal .navigation-breadcrumb__item {
  padding: 3px 0;
  border: 0;
  border-radius: 0;
  font-size: 13px;
  font-weight: 500;
  line-height: 20px;
  text-transform: none;
}

.navigation-breadcrumb--minimal .navigation-breadcrumb__item.active {
  background: transparent;
  color: var(--sc-app-text-primary);
}

.navigation-breadcrumb--minimal .navigation-breadcrumb__item:not(:last-child)::after {
  content: '/';
  margin-left: 6px;
  color: var(--sc-app-text-muted);
  font-weight: 400;
}

@media (max-width: 960px) {
  .navigation-breadcrumb__item:not(:nth-last-child(-n + 2)),
  .navigation-breadcrumb__item.active {
    display: none;
  }
}
</style>
