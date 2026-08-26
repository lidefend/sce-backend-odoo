<template>
  <div class="brand" data-semantic-component="ProductIdentity" data-state="ready">
    <div v-if="showLogo" class="logo">{{ logoText }}</div>
    <div><p class="title">{{ title }}</p><p class="subtitle">{{ subtitle }}</p></div>
    <ScButton v-if="showClose" class="mobile-sidebar-close" appearance="outline-action" type="button" variant="ghost" :aria-label="closeLabel" @click="$emit('close')"><ScIcon name="close" :size="20" /></ScButton>
  </div>
</template>
<script setup lang="ts">import ScButton from '../design-system/ScButton.vue'; import ScIcon from '../design-system/ScIcon.vue'; withDefaults(defineProps<{ logoText:string; title:string; subtitle:string; showLogo?:boolean; showClose?:boolean; closeLabel?:string }>(),{showLogo:true,closeLabel:'关闭主导航'}); defineEmits<{close:[]}>();</script>
<style scoped>
.brand{display:flex;gap:var(--sc-product-space-1);align-items:center;padding:1px 2px 6px}.logo{width:32px;height:32px;border-radius:var(--sc-product-radius-panel);background:var(--sc-semantic-surface-interactive);color:var(--sc-semantic-text-on-interactive);display:grid;place-items:center;font-size:var(--sc-product-text-sm);font-weight:700;letter-spacing:.6px}.title{font-weight:700;font-size:var(--sc-product-text-section);line-height:1.1;margin:0;color:var(--sc-app-text-primary)}.subtitle{margin:0;font-size:11px;color:var(--sc-app-text-secondary)}.mobile-sidebar-close{display:none;margin-left:auto;width:36px;height:36px;font-size:22px}@media(max-width:960px){.mobile-sidebar-close{display:grid;place-items:center}}
</style>
