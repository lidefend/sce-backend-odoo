<template>
  <nav
    class="navigation-breadcrumb"
    :class="{ 'navigation-breadcrumb--minimal': minimal, 'navigation-breadcrumb--compact': compact }"
    aria-label="页面路径"
    data-semantic-component="NavigationBreadcrumb"
  >
    <TDesignBreadcrumb :max-item-width="MAX_ITEM_WIDTH">
      <TDesignBreadcrumbItem
        v-for="(item, index) in items"
        :key="`${item.label}-${index}`"
        :to="item.to || undefined"
        :aria-current="index === items.length - 1 ? 'page' : undefined"
      >
        {{ item.label }}
      </TDesignBreadcrumbItem>
    </TDesignBreadcrumb>
  </nav>
</template>

<script setup lang="ts">
import type { PageBreadcrumb } from '../../app/pageIdentity';
import { TDesignBreadcrumb, TDesignBreadcrumbItem } from '../design-system/tdesignPrimitiveBridge';

// Matches the official reference starter (@aeed5707) breadcrumb width cap.
const MAX_ITEM_WIDTH = '150';

withDefaults(defineProps<{ items: PageBreadcrumb[]; minimal?: boolean; compact?: boolean }>(), {
  minimal: false,
  compact: false,
});
</script>

<style scoped>
/* Presentation is owned by the vendored `t-breadcrumb` driver, exactly like the
 * official reference starter (no local typography or separator overrides). The
 * wrapper only reserves the header slot. */
.navigation-breadcrumb {
  display: flex;
  flex-wrap: wrap;
  min-width: 0;
  flex: 0 1 auto;
}

.navigation-breadcrumb--compact {
  display: none;
}
</style>
