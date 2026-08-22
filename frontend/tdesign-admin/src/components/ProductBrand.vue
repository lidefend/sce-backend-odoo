<template>
  <span class="product-brand" :class="{ 'product-brand--compact': compact }">
    <span class="product-brand__mark" aria-hidden="true">工</span>
    <span v-if="!compact" class="product-brand__name">{{ productBrand.appName }}</span>
  </span>
</template>
<script setup lang="ts">
import { productBrand } from '@/config/product';

withDefaults(defineProps<{ compact?: boolean }>(), {
  compact: false,
});
</script>
<style scoped>
.product-brand {
  display: inline-flex;
  align-items: center;
  min-width: 0;
  max-width: 100%;
  color: var(--td-text-color-primary);
  gap: 10px;
}

.product-brand__mark {
  display: inline-flex;
  flex: 0 0 30px;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  color: #fff;
  background: var(--td-brand-color);
  border-radius: 4px;
  font-size: 17px;
  font-weight: 700;
  line-height: 1;
}

.product-brand__name {
  overflow: hidden;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 0;
  line-height: 24px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.product-brand--compact {
  justify-content: center;
}
</style>
